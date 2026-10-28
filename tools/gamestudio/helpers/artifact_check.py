"""Evaluate every workflow-catalog step's artifact spec against what is on disk."""
import glob as globmod
import os
import re
import sys

HELP = """Usage: python tools/studio.py artifact-check [--phase <id> | --path <id>] [project-root]
  --phase <id>  restrict output to one phase (concept, systems-design, ...)
  --path <id>   report one tier path instead of the phase ladder (`minimal`)
  project-root  defaults to the repo root
Output: CATALOG, ROOT, PHASES (or PATHS), STEPS, NO_CHECK, then per phase
  STEP: <id> required=<bool> repeatable=<bool> check=<kind> status=<status> ...
Status values (observations only, never a verdict): PRESENT, ABSENT, SHORT, PATTERN_MISS, NO_CHECK
(the step declares no artifact: completion is not detectable from disk, which is not ABSENT).
Reads docs/studio/workflow-catalog.yaml. STEPS and NO_CHECK are printed before any step line so a
caller can tell a catalog that failed to parse from a project with nothing incomplete."""

_POSIX = {"alpha": "A-Za-z", "digit": "0-9", "alnum": "A-Za-z0-9", "upper": "A-Z", "lower": "a-z",
          "space": r"\s", "blank": r" 	", "punct": r"!-/:-@\[-`{-~", "xdigit": "0-9A-Fa-f"}


def _compile_ere(pattern):
    p = re.sub(r"\[:([a-z]+):\]", lambda m: _POSIX.get(m.group(1), m.group(0)), pattern)
    try:
        return re.compile(p)
    except re.error:
        return re.compile(re.escape(pattern))


def run(catalog_path, root, phase_filter, path_filter):
    import glob as globmod
    import os
    import sys


    # A gate's own output path is part of the gate: the catalog's `note:` fields
    # contain em-dashes, and on a cp1252 console an unreconfigured stdout raises
    # UnicodeEncodeError mid-report — dying after some rows have printed, which
    # reads as a short but successful run. Force UTF-8 and never crash on a glyph.


    def indent_of(line):
        return len(line) - len(line.lstrip(" "))


    def strip_val(v):
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        return v


    # --- parse ---------------------------------------------------------------
    # Hand-rolled on purpose: PyYAML is not a guaranteed dependency (yaml-helper.sh
    # promises "no external deps beyond a Python 3 interpreter"). The catalog's
    # shape is fixed and regular, so an indentation walk is sufficient and cannot
    # drag in an import that fails on a user's machine.
    with open(catalog_path, encoding="utf-8", errors="replace") as fh:
        lines = [ln.rstrip("\n").rstrip("\r") for ln in fh]

    phases = []            # [(phase_id, [step, ...])]
    paths = []             # [(path_id, [step, ...])] — same shape, top-level `paths:`
    cur_phase = None
    cur_step = None
    ctx = None             # None | "artifact" | "any_of"
    section = None         # the list the current top-level key feeds, or None

    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        ind = indent_of(raw)
        s = raw.strip()

        if ind == 0:
            section = {"phases:": phases, "paths:": paths}.get(s)
            cur_phase = cur_step = ctx = None
            continue
        if section is None:
            continue

        if ind == 2 and s.endswith(":"):
            cur_phase = (s[:-1].strip(), [])
            section.append(cur_phase)
            cur_step = None
            ctx = None
            continue
        if cur_phase is None:
            continue

        if ind == 6 and s.startswith("- id:"):
            cur_step = {"id": strip_val(s[len("- id:"):]), "required": False,
                        "repeatable": False, "artifact": None, "note": None}
            cur_phase[1].append(cur_step)
            ctx = None
            continue
        if cur_step is None:
            continue

        if ind == 8:
            ctx = None
            if s == "artifact:":
                cur_step["artifact"] = {"glob": None, "pattern": None,
                                        "min_count": 1, "any_of": [], "note": None}
                ctx = "artifact"
            elif s.startswith("required:"):
                cur_step["required"] = strip_val(s[len("required:"):]).lower() == "true"
            elif s.startswith("repeatable:"):
                cur_step["repeatable"] = strip_val(s[len("repeatable:"):]).lower() == "true"
            continue

        art = cur_step["artifact"]
        if art is None:
            continue

        if ind == 10:
            if s == "any_of:":
                ctx = "any_of"
            elif s.startswith("glob:"):
                art["glob"] = strip_val(s[len("glob:"):]); ctx = "artifact"
            elif s.startswith("pattern:"):
                art["pattern"] = strip_val(s[len("pattern:"):]); ctx = "artifact"
            elif s.startswith("min_count:"):
                try:
                    art["min_count"] = int(strip_val(s[len("min_count:"):]))
                except ValueError:
                    pass
                ctx = "artifact"
            elif s.startswith("note:"):
                art["note"] = strip_val(s[len("note:"):]); ctx = "artifact"
            continue

        if ind >= 12 and ctx == "any_of":
            if s.startswith("- glob:"):
                art["any_of"].append({"glob": strip_val(s[len("- glob:"):]), "pattern": None})
            elif s.startswith("pattern:") and art["any_of"]:
                art["any_of"][-1]["pattern"] = strip_val(s[len("pattern:"):])

    # --- evaluate ------------------------------------------------------------
    def match_files(pat):
        if not pat:
            return []
        full = os.path.join(root, pat.replace("/", os.sep))
        return sorted(p for p in globmod.glob(full, recursive=True) if os.path.isfile(p))


    def pattern_hits(files, pattern):
        """Files whose text has a line matching the POSIX ERE (POSIX classes translated to Python)."""
        if not pattern:
            return files
        rx = _compile_ere(pattern)
        hits = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8", errors="replace") as fh:
                    if any(rx.search(line.rstrip(chr(13) + chr(10))) for line in fh):
                        hits.append(f)
            except OSError:
                return None
        return hits
    def evaluate(art):
        """-> (status, kind, detail dict). Observation only; no verdict."""
        if art is None:
            return "NO_CHECK", "none", {}

        if art["any_of"]:
            for i, alt in enumerate(art["any_of"]):
                files = match_files(alt["glob"])
                if not files:
                    continue
                hits = pattern_hits(files, alt["pattern"])
                if hits is None:
                    return "UNKNOWN", "any_of", {"why": "grep-unavailable"}
                if hits:
                    return "PRESENT", "any_of", {"match": alt["glob"], "alt": str(i + 1)}
            return "ABSENT", "any_of", {"alts": str(len(art["any_of"]))}

        if not art["glob"]:
            return "NO_CHECK", "none", ({"note": art["note"]} if art["note"] else {})

        files = match_files(art["glob"])
        if not files:
            return "ABSENT", "glob", {"glob": art["glob"]}

        hits = pattern_hits(files, art["pattern"])
        if hits is None:
            return "UNKNOWN", "glob", {"why": "grep-unavailable"}
        if art["pattern"] and not hits:
            return "PATTERN_MISS", "glob", {"glob": art["glob"], "found": str(len(files))}

        counted = hits if art["pattern"] else files
        need = art["min_count"]
        if len(counted) < need:
            return "SHORT", "glob", {"glob": art["glob"], "count": str(len(counted)), "min": str(need)}
        d = {"count": str(len(counted))}
        if need > 1:
            d["min"] = str(need)
        return "PRESENT", "glob", d


    if path_filter:
        label, pool, flt = "PATH", paths, path_filter
    else:
        label, pool, flt = "PHASE", phases, phase_filter
    sel = [(pid, steps) for pid, steps in pool if not flt or pid == flt]

    if flt and not sel:
        known = ", ".join(pid for pid, _ in pool) or "(none parsed)"
        sys.stderr.write("artifact-check: unknown %s '%s' (known: %s)\n" % (label.lower(), flt, known))
        return 2

    total_steps = sum(len(s) for _, s in sel)
    print("CATALOG: %s" % os.path.relpath(catalog_path, root).replace(os.sep, "/"))
    print("ROOT: %s" % root.replace(os.sep, "/"))
    print("%sS: %d" % (label, len(sel)))
    print("STEPS: %d" % total_steps)

    no_check = 0
    rows = []
    for pid, steps in sel:
        rows.append("%s: %s" % (label, pid))
        for st in steps:
            status, kind, det = evaluate(st["artifact"])
            if status == "NO_CHECK":
                no_check += 1
            extra = "".join(" %s=%s" % (k, v) for k, v in sorted(det.items()) if v is not None)
            rows.append("  STEP: %s required=%s repeatable=%s check=%s status=%s%s"
                        % (st["id"], str(st["required"]).lower(),
                           str(st["repeatable"]).lower(), kind, status, extra))

    # Printed BEFORE the rows so a caller reading top-down knows how much of what
    # follows is undetectable-from-disk before it reads any of it.
    print("NO_CHECK: %d" % no_check)
    for r in rows:
        print(r)
    return 0


def main(root, argv):
    phase = path = ""
    root_arg = ""
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a in ("--phase", "--path"):
            if i + 1 >= len(argv):
                sys.stderr.write("artifact-check: %s needs a value\n" % a)
                return 2
            if a == "--phase":
                phase = argv[i + 1]
            else:
                path = argv[i + 1]
            i += 2
            continue
        if a.startswith("--phase="):
            phase = a[8:]
        elif a.startswith("--path="):
            path = a[7:]
        else:
            root_arg = a
        i += 1
    if phase and path:
        sys.stderr.write("artifact-check: --phase and --path are exclusive (a path is a tier's whole route, not a phase)\n")
        return 2
    r = os.path.abspath(root_arg) if root_arg else root
    catalog = os.path.join(r, "docs", "studio", "workflow-catalog.yaml")
    if not os.path.isfile(catalog):
        sys.stderr.write("artifact-check: catalog not found at %s\n" % catalog)
        return 1
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    return run(catalog, r, phase, path)
