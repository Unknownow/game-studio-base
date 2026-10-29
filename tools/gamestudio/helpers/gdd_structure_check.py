"""Deterministic section-presence check for system GDDs."""
import os
import re
import sys

from . import _gdd, _util

HELP = """Usage: python tools/studio.py gdd-structure-check [design/gdd/foo.md] [--root DIR]
Deterministic section-presence check for system GDDs. REPORTS PRESENCE ONLY: which sections are
required depends on the workflow tier, so the caller applies the tier; this only says what is on disk.
With no argument it checks every system GDD directly under design/gdd/.
Output per GDD (ABSENT and PLACEHOLDER lines are omitted when empty):
  combat.md PRESENT: Overview,Player Fantasy,Detailed Rules,...
  loot.md   ABSENT:  Player Fantasy,Formulas,Tuning Knobs
  loot.md   PLACEHOLDER: Edge Cases
A section is a PLACEHOLDER when its body holds only `[To be designed]`, blank lines and sub-headings.
"Detailed Rules" is also accepted as "Detailed Design".
Exit codes: 0 done; 1 the named file was not found."""

SECTIONS = [("Overview", "Overview"), ("Player Fantasy", "Player Fantasy"),
            ("Detailed (Rules|Design)", "Detailed Rules"), ("Formulas", "Formulas"),
            ("Edge Cases", "Edge Cases"), ("Dependencies", "Dependencies"),
            ("Tuning Knobs", "Tuning Knobs"), ("Acceptance Criteria", "Acceptance Criteria")]


def _heading_re(pat):
    return re.compile(r"^##+[ \t]+([0-9]+[.)]?[ \t]*)?" + pat, re.I)


def check_text(text):
    lines = text.split("\n")
    present, absent, held = [], [], []
    for pat, label in SECTIONS:
        rx = _heading_re(pat)
        h = next((i for i, ln in enumerate(lines) if rx.match(ln)), None)
        if h is None:
            absent.append(label)
            continue
        present.append(label)
        lvl = len(re.match(r"#+", lines[h]).group(0))
        only = True
        for ln in lines[h + 1:]:
            m = re.match(r"(#+)[ \t]", ln)
            if m:
                if len(m.group(1)) <= lvl:
                    break
                continue
            t = ln.strip()
            if t and t != "[To be designed]":
                only = False
                break
        if only:
            held.append(label)
    return present, absent, held


def _report(path, text):
    b = os.path.basename(path)
    present, absent, held = check_text(text)
    print("%s PRESENT: %s" % (b, ",".join(present)))
    if absent:
        print("%s ABSENT:  %s" % (b, ",".join(absent)))
    if held:
        print("%s PLACEHOLDER: %s" % (b, ",".join(held)))


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    if any(a in ("-h", "--help") for a in rest):
        print(HELP)
        return 0
    if rest and rest[0]:
        p = rest[0] if os.path.isabs(rest[0]) else os.path.join(root, rest[0])
        if not os.path.isfile(p):
            sys.stderr.write("Not found: %s\n" % rest[0])
            return 1
        _report(p, _util.read(p))
        return 0
    files = _gdd.system_gdds(root)
    for f in files:
        _report(f, _util.read(os.path.join(root, f)))
    if not files:
        print("No system GDDs found in design/gdd/.")
    return 0
