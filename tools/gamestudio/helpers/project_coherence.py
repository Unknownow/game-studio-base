"""Compare what project.toml declares about the engine against what the project actually is."""
import os
import re

from .. import config as cfgmod
from .. import engines
from . import _util

HELP = """Usage: python tools/studio.py project-coherence
Compares what project.toml DECLARES against what the project IS. Output lines:
  [MATCH]       <what agreed>
  [DIFFERS]     <what disagreed>
  [NOT CHECKED] <why a comparison could not be made; this is not agreement>
then a summary: checked N · differs N · not checked N.
Checks: engine-reference/<engine>/VERSION.md records an "Installed at pin time" row; engine.version
agrees with the pinned version; engine.version agrees with the installed binary (when the engine
plugin can probe one); testing.command names a runner file that exists.
Observations only: always exits 0. The reader decides."""


def _vmm(s):
    m = re.search(r"[0-9]+\.[0-9]+", s or "")
    return re.sub(r"^6000\.", "6.", m.group(0)) if m else ""


def _row(text, label):
    m = re.search(r"^\| \*\*%s\*\* \| *(.*?) *\|?$" % re.escape(label), text, re.M)
    return m.group(1).strip() if m else ""


def main(root, argv):
    if argv and argv[0] in ("-h", "--help"):
        print(HELP)
        return 0
    out = []
    counts = {"checked": 0, "differs": 0, "skipped": 0}

    def match(m):
        counts["checked"] += 1
        out.append("[MATCH]       " + m)

    def differs(m):
        counts["checked"] += 1
        counts["differs"] += 1
        out.append("[DIFFERS]     " + m)

    def skipped(m):
        counts["skipped"] += 1
        out.append("[NOT CHECKED] " + m)

    def summary():
        print("\n".join(out))
        print("")
        print("checked %d · differs %d · not checked %d" % (counts["checked"], counts["differs"], counts["skipped"]))
        print("")
        print("Observations only — no verdict. 'not checked' is not agreement:")
        print("each line above names why that comparison could not be made.")
        return 0

    out.append("=== project coherence ===")
    cfg = cfgmod.load(root)
    if not os.path.isfile(os.path.join(root, "project.toml")):
        skipped("everything — no project.toml at the repo root. Run the start skill.")
        return summary()
    engine = cfg.value("engine.name") or ""
    version = cfg.value("engine.version") or ""
    if not engine:
        skipped("every engine check — project.toml has no engine.name. Run the setup-engine skill.")
        return summary()
    verfile = "engine-reference/%s/VERSION.md" % engine.lower()
    vpath = os.path.join(root, verfile)
    if not os.path.isfile(vpath):
        skipped("pinned-reference checks — %s does not exist" % verfile)
    else:
        text = _util.read(vpath)
        pinned = _row(text, "Engine Version")
        installed = _row(text, "Installed at pin time")
        if not installed:
            differs("%s has no 'Installed at pin time' row. setup-engine is required to write one; its absence means the probe result was never recorded, not that the versions agree." % verfile)
        elif "NOT DETERMINED" in installed:
            skipped("pinned-vs-installed — %s records '%s'. A probe that did not run has not established a match." % (verfile, installed))
        else:
            match("VERSION.md records the installed version at pin time: " + installed)
        if not pinned:
            skipped("engine.version vs pinned reference — no Engine Version row in " + verfile)
        elif not version:
            skipped("engine.version vs pinned reference — project.toml has no engine.version")
        elif version in pinned or (_vmm(version) and _vmm(version) == _vmm(pinned)):
            match("engine.version (%s) agrees with %s (%s)" % (version, verfile, pinned))
        else:
            differs("engine.version is '%s' but %s pins '%s'. Agents consult the reference file, so they will answer for a version the project does not declare." % (version, verfile, pinned))
    ctx = engines.Ctx(root, cfg)
    plugin = engines.load_plugin(ctx)
    probe = engines.call(plugin, "installed_version", ctx)
    if not probe:
        skipped("engine.version vs installed binary — no engine plugin can probe an installed %s. A probe that could not run has not established absence." % engine)
    elif not version:
        skipped("engine.version vs installed binary — project.toml has no engine.version")
    elif _vmm(version) and _vmm(version) == _vmm(probe):
        match("engine.version %s matches the installed binary (%s)" % (version, probe))
    else:
        differs("engine.version is '%s' but the installed binary reports '%s'. Build, test and smoke commands all target the declared version." % (version, probe))
    test_cmd = cfg.value("testing.command") or ""
    if not test_cmd:
        skipped("command checks — project.toml declares no testing.command")
    else:
        m = re.search(r"(res://)?[A-Za-z0-9_/.-]+\.(gd|cs|py|sh)", test_cmd)
        runner = (m.group(0)[6:] if m and m.group(0).startswith("res://") else (m.group(0) if m else ""))
        if runner:
            if os.path.isfile(os.path.join(root, runner)):
                match("testing.command runner exists (%s)" % runner)
            else:
                differs("testing.command is '%s' but '%s' does not exist, so this command cannot run as written." % (test_cmd, runner))
    return summary()
