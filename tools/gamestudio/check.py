"""`check`: blocking checks (ERROR) and advice (WARN)."""
import json
import os
import re
import tomllib

from . import config as cfgmod
from . import engines, frontmatter
from .common import Report, git, match_any, read_text, walk
from .helpers import skill_lint

STORY_TYPES = ["Logic", "Integration", "Visual/Feel", "UI", "Config/Data"]
SKILL_KEYS = {"name", "description", "license", "compatibility", "metadata", "disable-model-invocation"}
TIERS = {"strong", "standard", "inherit"}
CAN = {"read", "write", "shell", "web", "delegate"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
HOOK_RE = re.compile(r"hook: ([a-z0-9-]+/[a-z0-9-]+)")
HOOK_HEADING_RE = re.compile(r"^## hook: ([a-z0-9-]+/[a-z0-9-]+)\s*$", re.M)
GAME_OWNED = ["project.toml", "project.local.toml", "design/", "production/", "assets/", "src/", "tests/",
              "prototypes/", "Assets/", "ProjectSettings/", "Packages/manifest.json", "UPSTREAM"]
CODE_EXT = (".gd", ".cs", ".cpp", ".cc", ".hpp", ".h", ".c", ".py", ".js", ".ts", ".rs", ".java", ".kt", ".lua")
HARDCODED_RE = re.compile(r"(damage|health|speed|rate|chance|cost|duration)\s*[:=]\s*[0-9]+")
TODO_RE = re.compile(r"(TODO|FIXME|HACK)[^(]")


class Source(object):
    """Files to check: everything in the working tree, or what is staged."""

    def __init__(self, root, staged):
        self.root = root
        self.staged = staged
        self._status = {}
        self._deleted = []
        if staged:
            code, out = git(root, "diff", "--cached", "--name-status", "-z", "--diff-filter=ACMRD")
            tokens = out.split("\0")
            i = 0
            while i < len(tokens):
                st = tokens[i]
                if not st:
                    i += 1
                    continue
                n = 2 if st[0] in "RC" else 1
                paths = tokens[i + 1:i + 1 + n]
                i += 1 + n
                if not paths:
                    break
                rel = paths[-1].replace("\\", "/")
                if st[0] in "RC":
                    # The old path counts too: moving a skill away changes what depends on it.
                    self._deleted.append(paths[0].replace("\\", "/"))
                if st[0] == "D":
                    self._deleted.append(rel)
                else:
                    self._status[rel] = st[0]
            self._files = sorted(self._status)
        else:
            self._files = walk(root)

    def files(self):
        return self._files

    def status(self, rel):
        return self._status.get(rel)

    def read(self, rel):
        if self.staged:
            code, out = git(self.root, "show", ":" + rel)
            if code == 0:
                return out.replace("\r\n", "\n")
        return read_text(os.path.join(self.root, rel))

    def _index_files(self, prefix):
        code, out = git(self.root, "ls-files", "-z", prefix)
        return sorted(f.replace("\\", "/") for f in out.split("\0") if f) if code == 0 else []

    def role_files(self):
        """Every role file: from the index when staged, else from the working tree."""
        names = self._index_files("roles/") if self.staged else self._files
        return [f for f in names if f.startswith("roles/") and f.endswith(".md") and os.path.basename(f) != "README.md"]

    def skill_exists(self, name):
        if self.staged:
            if not hasattr(self, "_index_skills"):
                self._index_skills = set(self._index_files(".agents/skills/"))
            return ".agents/skills/%s/SKILL.md" % name in self._index_skills
        return os.path.isfile(os.path.join(self.root, ".agents", "skills", str(name), "SKILL.md"))

    def any(self, *prefixes):
        return any(f == p or f.startswith(p) for f in self._files + self._deleted for p in prefixes)


def _fm(report, src, rel):
    """Parse frontmatter; report syntax errors. Returns dict or None."""
    text = src.read(rel)
    try:
        data, _ = frontmatter.parse(text)
    except frontmatter.FrontmatterError as exc:
        report.error("frontmatter-syntax", "%s:%d" % (rel, exc.line), exc.message)
        return None
    if data is None:
        report.error("frontmatter-syntax", rel + ":1", "missing frontmatter")
    return data


def check_config(report, cfg):
    for p in cfg.problems():
        report.error("config", "", p)


def check_stories(report, src):
    for rel in src.files():
        if not (rel.startswith("production/epics/") and rel.endswith(".md")):
            continue
        base = os.path.basename(rel)
        if base in ("EPIC.md", "README.md"):
            continue
        text = src.read(rel)
        if not re.search(r"^# Story\b", text, re.M):
            report.error("story-sections", rel, "missing `# Story` title line")
        status = re.search(r"^>\s*\*\*Status\*\*:\s*(.*)$", text, re.M)
        stype = re.search(r"^>\s*\*\*Type\*\*:\s*(.*)$", text, re.M)
        if not status:
            report.error("story-sections", rel, "missing `> **Status**:` line")
        if not stype:
            report.error("story-sections", rel, "missing `> **Type**:` line")
        elif stype.group(1).strip() not in STORY_TYPES:
            report.error("story-sections", rel, "Type %r is not one of: %s" % (stype.group(1).strip(), ", ".join(STORY_TYPES)))
        for section in ("## Acceptance Criteria", "## Test Evidence"):
            if not re.search(r"^" + re.escape(section) + r"\s*$", text, re.M):
                report.error("story-sections", rel, "missing section `%s`" % section)
        if status and stype:
            st = status.group(1).strip().lower()
            if st.startswith(("done", "complete")) and stype.group(1).strip() in ("Visual/Feel", "UI"):
                check_evidence(report, src.root, rel, stype.group(1).strip())


def check_evidence(report, root, rel, stype):
    slug = os.path.splitext(os.path.basename(rel))[0]
    folder = os.path.join(root, "production", "qa", "evidence", slug)
    pngs = [f for f in os.listdir(folder) if f.lower().endswith(".png")] if os.path.isdir(folder) else []
    if not pngs:
        report.error("evidence", rel, "Done %s story needs a .png in production/qa/evidence/%s/" % (stype, slug))
    if stype == "Visual/Feel" and not os.path.isfile(os.path.join(root, "production", "qa", "evidence", slug + "-evidence.md")):
        report.error("evidence", rel, "Done Visual/Feel story needs production/qa/evidence/%s-evidence.md" % slug)


def check_data_json(report, src, globs):
    patterns = ["assets/data/**/*.json"] + list(globs)
    for rel in src.files():
        if rel.endswith(".json") and match_any(patterns, rel):
            try:
                json.loads(src.read(rel))
            except ValueError as exc:
                report.error("data-json", rel, "invalid JSON: %s" % exc)


def check_skills(report, src):
    for rel in src.files():
        parts = rel.split("/")
        if not (len(parts) == 4 and parts[0] == ".agents" and parts[1] == "skills" and parts[3] == "SKILL.md"):
            continue
        folder = parts[2]
        data = _fm(report, src, rel)
        if data is None:
            continue
        name = data.get("name")
        if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > 64:
            report.error("skill-frontmatter", rel, "name must be lowercase letters, digits and hyphens, at most 64 characters")
        elif name != folder:
            report.error("skill-frontmatter", rel, "name %r does not match folder %r" % (name, folder))
        desc = data.get("description")
        if not isinstance(desc, str) or not desc.strip():
            report.error("skill-frontmatter", rel, "description is required")
        elif len(desc) > 1024:
            report.error("skill-frontmatter", rel, "description is %d characters (max 1024)" % len(desc))
        for key in data:
            if key not in SKILL_KEYS:
                report.error("skill-frontmatter", rel, "key %r is not portable (allowed: %s)" % (key, ", ".join(sorted(SKILL_KEYS))))
        for rule, message in skill_lint.advice(src.root, folder):
            report.warn("skill-lint", rel, "%s: %s" % (rule, message))


def check_roles(report, src):
    for rel in src.role_files():
        data = _fm(report, src, rel)
        if data is None:
            continue
        stem = os.path.splitext(os.path.basename(rel))[0]
        if data.get("name") != stem:
            report.error("role-frontmatter", rel, "name %r does not equal the file name %r" % (data.get("name"), stem))
        if data.get("tier") not in TIERS:
            report.error("role-frontmatter", rel, "tier must be one of: strong, standard, inherit")
        can = data.get("can")
        if not isinstance(can, list) or any(c not in CAN for c in can):
            report.error("role-frontmatter", rel, "can must be a list drawn from: %s" % ", ".join(sorted(CAN)))
        skills = data.get("skills", [])
        if not isinstance(skills, list):
            report.error("role-frontmatter", rel, "skills must be a list")
        else:
            for s in skills:
                if not src.skill_exists(s):
                    report.error("role-frontmatter", rel, "skill %r does not exist" % s)


def check_rules(report, src):
    for rel in src.files():
        if not (rel.startswith("rules/") and rel.endswith(".md")) or os.path.basename(rel) == "README.md":
            continue
        data = _fm(report, src, rel)
        if data is None:
            continue
        paths = data.get("paths")
        if not isinstance(paths, list) or not paths:
            report.error("rule-frontmatter", rel, "paths must be a non-empty list")
        ext = data.get("extends")
        if ext and not os.path.isfile(os.path.join(src.root, ext)):
            report.error("rule-frontmatter", rel, "extends target %r does not exist" % ext)


def check_engine_hooks(report, root):
    engine_md = os.path.join(root, "ENGINE.md")
    if not os.path.isfile(engine_md):
        return
    headings = set(HOOK_HEADING_RE.findall(read_text(engine_md)))
    used = {}
    for rel in walk(root, ".agents/skills") + walk(root, "docs/studio"):
        if rel.endswith(".md"):
            for h in HOOK_RE.findall(read_text(os.path.join(root, rel))):
                used.setdefault(h, rel)
    for h, rel in sorted(used.items()):
        if h not in headings:
            report.error("engine-hooks", rel, "ENGINE.md has no `## hook: %s` section" % h)
    for h in sorted(headings - set(used)):
        report.warn("engine-hooks", "ENGINE.md", "section `hook: %s` is not referenced by any skill" % h)


def manifest_patterns(root):
    out = []
    files = [os.path.join(root, "files.manifest")]
    d = os.path.join(root, "files.manifest.d")
    if os.path.isdir(d):
        files += [os.path.join(d, n) for n in sorted(os.listdir(d)) if n.endswith(".manifest")]
    for f in files:
        if not os.path.isfile(f):
            continue
        for line in read_text(f).split("\n"):
            line = line.split("#", 1)[0].strip() if not line.startswith("!") else line.strip()
            if line:
                out.append((os.path.relpath(f, root).replace(os.sep, "/"), line))
    return out


def check_manifest(report, root):
    for rel, pat in manifest_patterns(root):
        if pat.startswith("!"):
            continue
        norm = pat.lstrip("/")
        if any(norm.startswith(g) for g in GAME_OWNED):
            report.error("manifest-game-owned", rel, "pattern %r covers game-owned files" % pat)


def upstream_tags(root):
    tags = {}
    for name in sorted(os.listdir(root)):
        if name.startswith("UPSTREAM") and name.endswith(".toml"):
            try:
                with open(os.path.join(root, name), "rb") as fh:
                    tags[name] = tomllib.load(fh).get("upstream", {}).get("tag")
            except (OSError, tomllib.TOMLDecodeError):
                tags[name] = None
    return tags


def check_upstream_tag(report, root):
    tags = upstream_tags(root)
    if len(set(tags.values())) > 1:
        report.warn("upstream-tag", "", "UPSTREAM files disagree on the tag: " + ", ".join("%s=%s" % kv for kv in tags.items()))


def check_staged_advice(report, src, ctx, plugin):
    root = src.root
    marker = engines.call(plugin, "project_marker", ctx) or ctx.engine_toml.get("project_marker")
    for rel in src.files():
        if src.status(rel) == "M" and (os.path.basename(rel) == "EPIC.md" or (marker and rel == marker)):
            report.warn("never-overwrite", rel, "existing file modified; confirm this edit is intended")
    for rel in src.files():
        if rel in ("design/registry/entities.yaml", "docs/architecture/tr-registry.yaml") and src.status(rel) == "M":
            code, old = git(root, "show", "HEAD:" + rel)
            if code == 0:
                idre = re.compile(r"^\s*(?:-\s*)?(?:id|name):\s*\"?([^\"\s#]+)", re.M)
                gone = set(idre.findall(old)) - set(idre.findall(src.read(rel)))
                if gone:
                    report.warn("registry-renumber", rel, "IDs removed or renamed: " + ", ".join(sorted(gone)))
    croot = engines.code_root(ctx, plugin)
    if croot:
        for rel in src.files():
            if not rel.startswith(croot + "/"):
                continue
            text = src.read(rel)
            if rel.lower().endswith(CODE_EXT) and HARDCODED_RE.search(text):
                report.warn("hardcoded-values", rel, "may contain hardcoded gameplay values; use data files")
            if TODO_RE.search(text):
                report.warn("todo-format", rel, "TODO/FIXME without owner; use TODO(name)")
    elif any(f.startswith(("src/", "Assets/", "Source/")) for f in src.files()):
        report.warn("hardcoded-values", "", "code root unresolved; hardcoded-value and TODO scans did not run")


def run_check(root, staged=False):
    report = Report()
    cfg = cfgmod.load(root)
    ctx = engines.Ctx(root, cfg)
    plugin = engines.load_plugin(ctx)
    src = Source(root, staged)
    if cfg.value("engine.name") and plugin is None:
        report.warn("engine-plugin-missing", "", "no engine plugin for %r" % cfg.value("engine.name"))
    if not staged or src.any("project.toml", "project.local.toml", "engine.toml"):
        check_config(report, cfg)
    check_stories(report, src)
    check_data_json(report, src, engines.data_globs(ctx, plugin))
    if not staged or src.any(".agents/skills/"):
        check_skills(report, src)
    if not staged or src.any("roles/", ".agents/skills/"):
        # A role names skills, so a staged change to a skill (a deletion, a move) re-checks every role in the index.
        check_roles(report, src)
    if not staged or src.any("rules/"):
        check_rules(report, src)
    if not staged or src.any("ENGINE.md", ".agents/skills/", "docs/studio/"):
        check_engine_hooks(report, root)
    if not staged or src.any("files.manifest"):
        check_manifest(report, root)
    check_upstream_tag(report, root)
    engines.call(plugin, "check", ctx, report)
    if staged:
        check_staged_advice(report, src, ctx, plugin)
    return report
