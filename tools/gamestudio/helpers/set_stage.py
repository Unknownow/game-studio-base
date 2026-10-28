"""Write the project stage to project.toml and read it back."""
import os
import sys

from .. import config as cfgmod
from . import _util

HELP = """Usage: python tools/studio.py set-stage <Stage> [--dry-run] [--root DIR]
  <Stage>     one of: Concept, Systems Design, Technical Setup, Pre-Production, Production, Polish,
              Release (quote the two-word names)
  --dry-run   say what would change; write nothing
The ask stays in the skill: a stage moves only on a gate-check PASS (or a CONCERNS whose risks the user
accepted) with the user's yes. This helper never decides that and never prompts: run it after the yes.
Output: TSV
  project.toml <replaced|inserted|created|unchanged> -
  stage_toml   <value read back> project.toml
Exit codes: 0 project.toml holds the stage; 1 cannot read the root or write the file; 2 usage error;
3 <Stage> is not a stage name (nothing written); 7 the value read back is not the one asked for."""


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    dry = False
    stage = None
    for a in rest:
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a == "--dry-run":
            dry = True
        elif a.startswith("-") and len(a) > 1:
            return _util.usage_error("set-stage", "unknown argument: " + a)
        elif stage is None:
            stage = a
        else:
            return _util.usage_error("set-stage", "one stage only")
    if stage is None:
        return _util.usage_error("set-stage", "no stage given")
    if stage not in cfgmod.STAGES:
        sys.stderr.write("set-stage: %r is not a stage (one of: %s)\n" % (stage, ", ".join(cfgmod.STAGES)))
        return 3
    if not os.path.isdir(root):
        sys.stderr.write("set-stage: cannot read root %s\n" % root)
        return 1
    path = os.path.join(root, "project.toml")
    before = cfgmod.lookup(cfgmod.load(root).project, "project.stage")
    if not os.path.exists(path):
        action = "created"
    elif before is None:
        action = "inserted"
    elif before == stage:
        action = "unchanged"
    else:
        action = "replaced"
    if dry or action == "unchanged":
        print("project.toml\t%s\t-" % action)
        print("stage_toml\t%s\tproject.toml" % (before or "-" if action == "unchanged" else stage + " (dry run)" if dry else stage))
        return 0
    code, msg = cfgmod.set_key(root, "project.stage=" + stage)
    if code:
        sys.stderr.write(msg + "\n")
        return 1
    back = cfgmod.lookup(cfgmod.load(root).project, "project.stage")
    print("project.toml\t%s\t-" % action)
    print("stage_toml\t%s\tproject.toml" % (back or "-"))
    return 0 if back == stage else 7
