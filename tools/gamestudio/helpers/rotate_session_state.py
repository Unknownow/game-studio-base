"""Move active.md's narrative into a dated session log, leaving the checkpoint behind."""
import datetime
import os
import re
import sys

HELP = """Usage: python tools/studio.py rotate-session-state [--dry-run] [--root DIR]
Moves the free-form narrative of production/session-state/active.md (everything after the
<!-- /CHECKPOINT --> line) into production/session-logs/session-state-<date>.md and starts a fresh Notes
section. The checkpoint stays. Nothing is deleted.
Explicit invocation only: the user decides whether to run it. Observations, never verdicts.
Exit codes: 0 done (or nothing to rotate); 1 could not write; 2 usage error; 3 the file has no
<!-- /CHECKPOINT --> marker, so the checkpoint cannot be told from the narrative (nothing is moved)."""

STATE = "production/session-state/active.md"
LOGDIR = "production/session-logs"
MARKER = re.compile(r"^[ \t]*<!-- /CHECKPOINT -->[ \t]*$")


def main(root, argv):
    from . import _util
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    dry = False
    for a in rest:
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a == "--dry-run":
            dry = True
        else:
            sys.stderr.write("unknown argument: %s (try --help)\n" % a)
            return 2
    state = os.path.join(root, STATE)
    if not os.path.isfile(state):
        print("no session state at %s — nothing to rotate" % STATE)
        return 0
    lines = _util.read(state).split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    split = next((i + 1 for i, l in enumerate(lines) if MARKER.match(l.rstrip("\r"))), 0)
    if not split:
        print("REFUSED: %s has no <!-- /CHECKPOINT --> marker." % STATE)
        print("  Rotation splits the file at that marker, so without it this script")
        print("  cannot tell the checkpoint from the narrative and would move both.")
        print("  Re-create the file from templates/session-state.md first.")
        return 3
    total = len(lines)
    narrative = total - split
    if narrative <= 5:
        print("narrative is %d lines — nothing worth rotating" % narrative)
        return 0
    stamp = datetime.date.today().isoformat()
    archive = "%s/session-state-%s.md" % (LOGDIR, stamp)
    if dry:
        print("DRY RUN — no changes written")
        print("  checkpoint kept : lines 1-%d" % split)
        print("  narrative moved : lines %d-%d (%d lines)" % (split + 1, total, narrative))
        print("  destination     : " + archive)
        return 0
    os.makedirs(os.path.join(root, LOGDIR), exist_ok=True)
    try:
        with open(os.path.join(root, archive), "a", encoding="utf-8", newline="\n") as fh:
            fh.write("\n---\n\n## Rotated from active.md on %s (%d lines)\n\n%s\n" % (stamp, narrative, "\n".join(lines[split:])))
        new = lines[:split] + ["", "---", "", "## Notes", "", "_Narrative through %s rotated to `%s`._" % (stamp, archive), ""]
        with open(state, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(new) + "\n")
    except OSError as exc:
        sys.stderr.write("rotate-session-state: FAILED — %s\n" % exc)
        return 1
    print("rotated %d lines -> %s" % (narrative, archive))
    print("%s is now %d lines" % (STATE, len(new)))
    return 0
