"""The project facts several skills work out by hand: engine, code root, counts, stage, inferred phase."""
import os

from .. import config as cfgmod
from .. import engines
from . import _util

HELP = """Usage: python tools/studio.py project-state [--stage] [--root DIR]
  --stage     print only the stage rows
Output: TSV rows key<TAB>value<TAB>source, "-" means no value:
  root, engine, code_root, source_files, concept, systems_index, gdd_files,
  adr, story, prototype, sprint, milestone, origin_url,
  stage_toml, stage, phase, phase_inferred
Observations, not a verdict: phase_inferred is the artifact ladder applied to the counts.
source_files is "unknown" when the code root is unset: unknown is not zero."""

PHASES = {"Concept": "concept", "Systems Design": "systems-design", "Technical Setup": "technical-setup",
          "Pre-Production": "pre-production", "Production": "production", "Polish": "polish", "Release": "release"}
SRC_EXT = (".gd", ".cs", ".cpp", ".c", ".h", ".hpp", ".rs", ".py", ".js", ".ts")
NAME_ROOTS = {"godot": "src", "unity": "Assets", "unreal": "Source"}


def _count(root, sub, depth_one=True, prefix=None, suffix=None, dirs=False):
    d = os.path.join(root, sub)
    if not os.path.isdir(d):
        return 0
    n = 0
    for dirpath, dirnames, filenames in os.walk(d):
        if dirs:
            n += len(dirnames)
        else:
            n += sum(1 for f in filenames if (not prefix or f.startswith(prefix)) and (not suffix or f.endswith(suffix)))
        if depth_one:
            break
    return n


def stage_rows(cfg):
    v = cfg.project.get("project", {}).get("stage") if isinstance(cfg.project.get("project"), dict) else None
    stage = cfgmod.lookup(cfg.project, "project.stage") or ""
    valid = stage if stage in PHASES else ""
    present = os.path.isfile(os.path.join(cfg.root, "project.toml"))
    _util.row("stage_toml", stage, "project.toml" if present else "absent")
    _util.row("stage", valid, "project.toml" if valid else "unset")
    _util.row("phase", PHASES.get(valid, ""), "stage" if valid else "unset")


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    if rest and rest[0] in ("-h", "--help"):
        print(HELP)
        return 0
    unknown = [a for a in rest if a != "--stage"]
    if unknown:
        return _util.usage_error("project-state", "unknown argument: " + unknown[0])
    if not os.path.isdir(root):
        import sys
        sys.stderr.write("project-state: cannot read root %s\n" % root)
        return 1
    cfg = cfgmod.load(root)
    if "--stage" in rest:
        stage_rows(cfg)
        return 0
    ctx = engines.Ctx(root, cfg)
    engine = cfg.value("engine.name") or ""
    _, esrc = cfg.get("engine.name")
    code_root, csrc = "", ""
    if engine and engine.lower() in NAME_ROOTS:
        code_root, csrc = NAME_ROOTS[engine.lower()], "engine.name"
    if not code_root and ctx.engine_toml.get("code_root"):
        code_root, csrc = ctx.engine_toml["code_root"], "engine.toml"
    if not code_root:
        present = [d for d in ("src", "Assets", "Source") if d in os.listdir(root)]
        if len(present) == 1:
            code_root, csrc = present[0], "detected"
    if code_root:
        n = 0
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, code_root)):
            n += sum(1 for f in filenames if f.endswith(SRC_EXT))
        src_files, ssrc = n, code_root
    else:
        src_files, ssrc = "unknown", "code_root unset"
    concept = ""
    for f in ("design/gdd/game-concept.md", "design/game-brief.md"):
        if os.path.isfile(os.path.join(root, f)):
            concept = f
            break
    sysidx = "design/gdd/systems-index.md" if os.path.isfile(os.path.join(root, "design/gdd/systems-index.md")) else ""
    gdd = _count(root, "design/gdd", suffix=".md")
    adr = _count(root, "docs/architecture", prefix="adr-", suffix=".md")
    stories = 0
    d = os.path.join(root, "production", "epics")
    if os.path.isdir(d):
        for dirpath, _, filenames in os.walk(d):
            stories += sum(1 for f in filenames if f.startswith("story-") and f.endswith(".md"))
    proto = _count(root, "prototypes", dirs=True)
    sprint = _count(root, "production/sprints", suffix=".md")
    mile = _count(root, "production/milestones", suffix=".md")
    from ..common import git
    code, url = git(root, "remote", "get-url", "origin")
    origin = url.strip() if code == 0 else ""
    _util.row("root", root.replace(os.sep, "/"), "-")
    _util.row("engine", engine, esrc if engine else "unset")
    _util.row("code_root", code_root, csrc or "unset")
    _util.row("source_files", src_files, ssrc)
    _util.row("concept", concept, "found" if concept else "absent")
    _util.row("systems_index", sysidx, "found" if sysidx else "absent")
    _util.row("gdd_files", gdd, "design/gdd/*.md")
    _util.row("adr", adr, "docs/architecture/adr-*.md")
    _util.row("story", stories, "production/epics/**/story-*.md")
    _util.row("prototype", proto, "prototypes/*/")
    _util.row("sprint", sprint, "production/sprints/*.md")
    _util.row("milestone", mile, "production/milestones/*.md")
    _util.row("origin_url", origin, "git remote origin" if origin else "absent")
    stage_rows(cfg)
    note = ";source_files unknown" if src_files == "unknown" else ""
    if src_files != "unknown" and src_files >= 10:
        _util.row("phase_inferred", "production", "source_files>=10")
    elif stories >= 1:
        _util.row("phase_inferred", "pre-production", "story>=1" + note)
    elif adr >= 1:
        _util.row("phase_inferred", "technical-setup", "adr>=1" + note)
    elif sysidx:
        _util.row("phase_inferred", "systems-design", "systems_index" + note)
    elif concept:
        _util.row("phase_inferred", "concept", "concept" + note)
    else:
        _util.row("phase_inferred", "concept", "nothing" + note)
    return 0
