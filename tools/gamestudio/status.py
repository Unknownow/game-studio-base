"""`status`: a short orientation for an agent or person starting a session."""
import os
import re

from . import config as cfgmod
from . import engines
from .common import git, read_text, walk


def story_counts(root):
    counts = {}
    ready = None
    for rel in walk(root, "production/epics", ".md"):
        if os.path.basename(rel) in ("EPIC.md", "README.md"):
            continue
        m = re.search(r"^>\s*\*\*Status\*\*:\s*(.*)$", read_text(os.path.join(root, rel)), re.M)
        if not m:
            continue
        word = m.group(1).strip().strip("[]")
        key = re.split(r"\s*[—\-:|(]", word, 1)[0].strip() or "Unknown"
        counts[key] = counts.get(key, 0) + 1
        if key.lower() == "ready" and ready is None:
            ready = rel
    return counts, ready


def build(root):
    """Return (lines, ok). ok is False when the config cannot be read."""
    cfg = cfgmod.load(root)
    if cfg.project_err or cfg.local_err:
        return ["studio: config is unreadable: " + (cfg.project_err or cfg.local_err)], False
    ctx = engines.Ctx(root, cfg)
    plugin = engines.load_plugin(ctx)
    out = ["== Project =="]
    name = cfg.value("project.name") or "(unnamed)"
    eng = cfg.value("engine.name") or "(not set)"
    out.append("name: %s" % name)
    out.append("stage: %s" % cfg.value("project.stage"))
    out.append("rigor: %s" % cfg.value("rigor"))
    out.append("review_mode: %s" % cfg.value("review_mode"))
    out.append("engine: %s %s" % (eng, cfg.value("engine.version") or ""))
    out.append("")
    out.append("== Stories ==")
    counts, ready = story_counts(root)
    if counts:
        out.append(", ".join("%s: %d" % kv for kv in sorted(counts.items())))
        out.append("next: %s" % (ready or "(no Ready story)"))
    else:
        out.append("no stories yet")
    out.append("")
    out.append("== Session ==")
    active = os.path.join(root, "production", "session-state", "active.md")
    if os.path.isfile(active):
        out.extend(read_text(active).split("\n")[:15])
    else:
        out.append("no active session state")
    out.append("")
    out.append("== Git ==")
    code, branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if code == 0:
        out.append("branch: " + branch.strip())
        out.extend(("  " + l) for l in git(root, "log", "-5", "--oneline")[1].splitlines())
        out.append("uncommitted files: %d" % len(git(root, "status", "--porcelain")[1].splitlines()))
    elif git(root, "rev-parse", "--git-dir")[0] == 0:
        out.append("no commits yet")
    else:
        out.append("not a git repository")
    out.append("")
    out.append("== Gaps ==")
    gaps = []
    has_brief = os.path.isfile(os.path.join(root, "design", "game-brief.md"))
    gdds = [f for f in walk(root, "design/gdd", ".md")]
    if not has_brief and not gdds:
        gaps.append("no design/game-brief.md and no GDDs: run the start skill")
    croot = engines.code_root(ctx, plugin)
    if croot and not gdds and not has_brief and os.path.isdir(os.path.join(root, croot)):
        if any(not f.endswith("README.md") for f in walk(root, croot)):
            gaps.append("code exists under %s/ but there are no design docs: consider the reverse-document skill" % croot)
    out.extend(gaps or ["none"])
    extra = engines.call(plugin, "status", ctx, default=[]) or []
    if extra:
        out.append("")
        out.append("== Engine ==")
        out.extend(extra)
    return out, True
