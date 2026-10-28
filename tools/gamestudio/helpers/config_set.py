"""Set one key in project.toml or project.local.toml after the checks, and read the value back."""
import os
import sys

from .. import config as cfgmod
from . import _util

HELP = """Usage: python tools/studio.py config-set [--local] KEY VALUE [--dry-run] [--root DIR]
       python tools/studio.py config-set [--local] KEY=VALUE ...
  KEY         a dotted TOML path, for example modes.review_mode (display names such as review_mode work too)
  VALUE       the new value; quote one with spaces ("Systems Design"). KEY=VALUE splits at the first =
  --local     write project.local.toml (gitignored) instead of project.toml
  --dry-run   print every row; write nothing
The ask stays in the skill: run with --dry-run first to get the check rows, show the user the warnings,
ask, then run again without --dry-run. This helper never prompts and never judges.
The file keeps its comments and key order. Only scalar values can be written; lists are edited by hand.
Output: TSV, in this order
  file      <project.toml|project.local.toml>  <present|absent>
  enum      <ok|invalid|none>  <allowed values, or - when the key has no enum>
  known     <yes|no>  <why>
  shadow    <yes|no>  <the project.local.toml value>   (project.toml writes only)
  current   <value now in the file, or ->  <file>
  edit      <replaced|inserted|created|unchanged>  -
  readback  <value read back>  <file>
Exit codes: 0 done (or a dry run that would be); 1 cannot read or write; 2 usage error;
3 the value is not in the key's enum; 5 a layout it will not edit (a list or table); 7 the value read back
is not the one asked for. 3, 5 and 7 write nothing."""


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    local = dry = False
    pos = []
    for a in rest:
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a == "--local":
            local = True
        elif a == "--dry-run":
            dry = True
        elif a.startswith("-") and len(a) > 1 and "=" not in a:
            return _util.usage_error("config-set", "unknown argument: " + a)
        else:
            pos.append(a)
    if len(pos) == 1 and "=" in pos[0]:
        key, value = pos[0].split("=", 1)
    elif len(pos) == 2:
        key, value = pos
    else:
        return _util.usage_error("config-set", "expected KEY VALUE or KEY=VALUE")
    if not key or not value:
        return _util.usage_error("config-set", "KEY and VALUE must both be non-empty")
    if "\n" in value or value.startswith("#") or " #" in value:
        sys.stderr.write("config-set: a value with a newline or a # comment cannot be written safely\n")
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("config-set: cannot read root %s\n" % root)
        return 1
    path = cfgmod.normalize_key(key)
    fname = "project.local.toml" if local else "project.toml"
    fpath = os.path.join(root, fname)
    print("file\t%s\t%s" % (fname, "present" if os.path.exists(fpath) else "absent"))
    allowed = cfgmod.ENUMS.get(path)
    if path.startswith("workflow_overrides.system_overrides."):
        allowed = cfgmod.TIERS
    if allowed is None:
        print("enum\tnone\t-")
    else:
        val = value.lower() if value.lower() in ("true", "false") else value
        ok = val in allowed
        print("enum\t%s\t%s" % ("ok" if ok else "invalid", "|".join(allowed)))
        if not ok:
            return 3
    known = path in cfgmod.known_paths() or path.startswith("workflow_overrides.system_overrides.")
    print("known\t%s\t%s" % ("yes" if known else "no", "in the config schema" if known else "not a config key"))
    if not known:
        sys.stderr.write("config-set: unknown config key %s\n" % path)
        return 2
    cfg = cfgmod.load(root)
    if not local:
        lv = cfgmod.lookup(cfg.local, path)
        print("shadow\t%s\t%s" % ("yes" if lv not in (None, "") else "no", cfgmod.render_value(lv) if lv not in (None, "") else "-"))
    cur = cfgmod.lookup(cfg.local if local else cfg.project, path)
    print("current\t%s\t%s" % (cfgmod.render_value(cur) if cur is not None else "-", fname))
    if dry:
        print("edit\t%s\t-" % ("unchanged" if str(cur).lower() == value.lower() else "replaced" if cur is not None else "inserted"))
        return 0
    if not local and not os.path.exists(fpath):
        sys.stderr.write("config-set: no project.toml; run the start skill first\n")
        return 1
    code, msg = cfgmod.set_key(root, "%s=%s" % (path, value), local)
    if code:
        sys.stderr.write(msg + "\n")
        return 5 if "by hand" in msg else 1
    action = "unchanged" if cur is not None and str(cur).lower() == value.lower() else ("replaced" if cur is not None else "inserted")
    print("edit\t%s\t-" % action)
    back = cfgmod.lookup(cfgmod.load(root).local if local else cfgmod.load(root).project, path)
    print("readback\t%s\t%s" % (cfgmod.render_value(back), fname))
    return 0 if str(back).lower() == value.lower() else 7
