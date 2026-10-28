"""`claude-sync` and `claude-hook`: the Claude Code add-on. Everything is generated under .claude/."""
import json
import os
import shutil

from . import config as cfgmod
from . import frontmatter
from .common import read_text, walk

DENY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "claude-deny.json")
MARKER = ".studio-generated.json"
TOOL_MAP = [("read", ["Read", "Glob", "Grep"]), ("write", ["Write", "Edit"]), ("shell", ["Bash"]),
            ("web", ["WebSearch"]), ("delegate", ["Agent"])]
MODEL = {"strong": "opus", "standard": "sonnet", "inherit": "inherit"}
MAX_TURNS = {"strong": 30, "standard": 20, "inherit": 20}


def _q(s):
    return '"' + str(s).replace("\\", "\\\\").replace('"', '\\"') + '"'


def agent_file(data, body):
    can = data.get("can") or []
    tools = []
    for key, names in TOOL_MAP:
        if key in can:
            tools.extend(names)
    tier = data.get("tier", "inherit")
    lines = ["---", "name: " + str(data["name"]), "description: " + _q(data.get("description", "")),
             "tools: " + ", ".join(tools)]
    if "shell" not in can:
        lines.append("disallowedTools: Bash")
    lines.append("model: " + MODEL.get(tier, "inherit"))
    lines.append("maxTurns: %d" % MAX_TURNS.get(tier, 20))
    if data.get("memory") is True or data.get("memory") == "true":
        lines.append("memory: project")
    if data.get("skills"):
        lines.append("skills:")
        lines.extend("  - " + s for s in data["skills"])
    lines.append("---")
    return "\n".join(lines) + "\n" + body.lstrip("\n")


def settings_data():
    with open(DENY_FILE, "r", encoding="utf-8") as fh:
        deny = json.load(fh)
    return {
        "_generatedBy": "tools/studio.py claude-sync",
        "permissions": {"deny": deny},
        "hooks": {
            "SessionStart": [{"hooks": [{"type": "command", "command": "python tools/studio.py status"}]}],
            "PreToolUse": [{"matcher": "Bash", "hooks": [
                {"type": "command", "command": "python tools/studio.py claude-hook pre-bash"}]}],
        },
    }


def sync(root):
    """Returns (exit_code, lines)."""
    cfg = cfgmod.load(root)
    if cfg.value("claude.sync") is False:
        return 0, []
    lines = []
    cdir = os.path.join(root, ".claude")
    os.makedirs(cdir, exist_ok=True)
    marker_path = os.path.join(cdir, MARKER)
    old = {"skills": [], "agents": []}
    if os.path.isfile(marker_path):
        try:
            old = json.loads(read_text(marker_path))
        except ValueError:
            pass
    skills_src = os.path.join(root, ".agents", "skills")
    skills = sorted(d for d in os.listdir(skills_src) if os.path.isfile(os.path.join(skills_src, d, "SKILL.md"))) \
        if os.path.isdir(skills_src) else []
    for name in skills:
        dest = os.path.join(cdir, "skills", name)
        if os.path.isdir(dest):
            shutil.rmtree(dest)
        shutil.copytree(os.path.join(skills_src, name), dest)
    for name in old.get("skills", []):
        if name not in skills:
            shutil.rmtree(os.path.join(cdir, "skills", name), ignore_errors=True)
    agents = []
    for rel in walk(root, "roles", ".md"):
        if os.path.basename(rel) == "README.md":
            continue
        text = read_text(os.path.join(root, rel))
        try:
            data, body = frontmatter.parse(text)
        except frontmatter.FrontmatterError as exc:
            lines.append("WARN claude-sync %s:%d: %s" % (rel, exc.line, exc.message))
            continue
        if not data or "name" not in data:
            lines.append("WARN claude-sync %s: no frontmatter name" % rel)
            continue
        os.makedirs(os.path.join(cdir, "agents"), exist_ok=True)
        with open(os.path.join(cdir, "agents", data["name"] + ".md"), "w", encoding="utf-8", newline="\n") as fh:
            fh.write(agent_file(data, body))
        agents.append(data["name"])
    for name in old.get("agents", []):
        if name not in agents:
            try:
                os.remove(os.path.join(cdir, "agents", name + ".md"))
            except OSError:
                pass
    settings = os.path.join(cdir, "settings.json")
    write_settings = True
    if os.path.isfile(settings):
        try:
            existing = json.loads(read_text(settings))
        except ValueError:
            existing = {}
        if not isinstance(existing, dict) or "_generatedBy" not in existing:
            write_settings = False
            lines.append("WARN claude-sync: .claude/settings.json is user-owned; put overrides in .claude/settings.local.json")
    if write_settings:
        with open(settings, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(settings_data(), fh, indent=2)
            fh.write("\n")
    with open(marker_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"skills": skills, "agents": agents}, fh)
    lines.append("claude-sync: %d skills, %d agents" % (len(skills), len(agents)))
    return 0, lines
