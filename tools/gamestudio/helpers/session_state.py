"""Read and write production/session-state/active.md in the session-state template's layout."""
import os
import sys

from . import _util

HELP = """Usage: python tools/studio.py session-state <command> [--root DIR]
  show        print the STATUS block (when there is one) through the end of the CHECKPOINT block
  checkpoint  replace what is between the CHECKPOINT markers with stdin. No file: create it from the
              template first. A file with no markers: add the block after the STATUS block, or, with no
              STATUS block either, put the template's STATUS and CHECKPOINT blocks at the top.
  append      add stdin at the end of the file (after the narrative), unless the file already ends with
              exactly those lines. No file: create it from the template first.
A marker is a line holding only <!-- CHECKPOINT --> or <!-- /CHECKPOINT --> (spaces ignored).
Stdin may include or leave out the two marker lines; blank lines at its start and end are dropped.
Output (checkpoint, append): TSV
  file   production/session-state/active.md   <created|replaced|inserted|appended|unchanged>
  lines  <lines written from stdin>           -
Exit codes: 0 done; 1 cannot read the root, find the template or write the file; 2 usage error;
3 one CHECKPOINT marker without the other, or out of order (nothing written); 4 show found no active.md."""

STATE = "production/session-state/active.md"
TEMPLATE = "templates/session-state.md"
MAX_LINES = 25


def _locate(lines):
    so = sc = co = cc = stray = 0
    for i, l in enumerate(lines, 1):
        t = l.strip()
        if t == "<!-- STATUS -->" and not so:
            so = i
        if t == "<!-- /STATUS -->" and so and not sc:
            sc = i
        if t == "<!-- CHECKPOINT -->" and not co:
            co = i
        if t == "<!-- /CHECKPOINT -->":
            if co and not cc:
                cc = i
            elif not co:
                stray = i
    if stray and not co:
        cc = stray
    return so, sc, co, cc


def _split(text):
    """Return (lines, crlf, ends_with_newline)."""
    crlf = "\r\n" in text.split("\n", 1)[0] + ("\r\n" if text.split("\n", 1)[0].endswith("\r") else "")
    t = text.replace("\r\n", "\n")
    nl = t.endswith("\n")
    lines = t.split("\n")
    if nl:
        lines = lines[:-1]
    return lines, crlf, nl


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    cmd = ""
    for a in rest:
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a in ("show", "checkpoint", "append"):
            if cmd:
                sys.stderr.write("session-state: one command only\n")
                return 2
            cmd = a
        else:
            return _util.usage_error("session-state", "unknown argument: " + a)
    if not cmd:
        sys.stderr.write("session-state: no command; use show, checkpoint or append (try --help)\n")
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("session-state: cannot read root %s\n" % root)
        return 1
    state = os.path.join(root, STATE)
    tpl = os.path.join(root, TEMPLATE)
    if cmd == "show":
        if not os.path.isfile(state):
            sys.stderr.write("session-state: no %s\n" % STATE)
            return 4
        lines, _, _ = _split(_util.read(state))
        so, sc, co, cc = _locate(lines)
        if not co or not cc or cc < co:
            sys.stderr.write("session-state: %s has no complete CHECKPOINT block (<!-- CHECKPOINT --> ... <!-- /CHECKPOINT -->)\n" % STATE)
            return 3
        start = so if (so > 0 and sc > so and so < co) else co
        for l in lines[start - 1:cc]:
            print(l)
        return 0
    body = [l.rstrip("\r") for l in sys.stdin.read().replace("\r\n", "\n").split("\n")]
    body = [l for l in body if l.strip() not in ("<!-- CHECKPOINT -->", "<!-- /CHECKPOINT -->")]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    if not body:
        sys.stderr.write("session-state: nothing on stdin to write\n")
        return 2
    action = ""
    if not os.path.isfile(state):
        if not os.path.isfile(tpl):
            sys.stderr.write("session-state: no %s and no template at %s to create it from\n" % (STATE, TEMPLATE))
            return 1
        base_text, action = _util.read(tpl), "created"
    else:
        base_text = _util.read(state)
    base, crlf, _ = _split(base_text)
    so, sc, co, cc = _locate(base)
    if cmd == "checkpoint":
        if co > 0 and cc > co:
            action = action or "replaced"
            new = base[:co] + body + base[cc - 1:]
        elif co == 0 and cc == 0:
            action = action or "inserted"
            if so > 0 and sc > so:
                new = base[:sc] + ["", "<!-- CHECKPOINT -->"] + body + ["<!-- /CHECKPOINT -->"] + base[sc:]
            else:
                if not os.path.isfile(tpl):
                    sys.stderr.write("session-state: %s has no markers and there is no template at %s to take them from\n" % (STATE, TEMPLATE))
                    return 1
                tl, _, _ = _split(_util.read(tpl))
                tso, tsc, _, _ = _locate(tl)
                status = tl[tso - 1:tsc] if tso > 0 and tsc > tso else []
                new = (status + [""] if status else []) + ["<!-- CHECKPOINT -->"] + body + ["<!-- /CHECKPOINT -->", ""] + base
        else:
            why = ("<!-- CHECKPOINT --> at line %d has no <!-- /CHECKPOINT --> after it" % co) if cc == 0 else \
                  ("<!-- /CHECKPOINT --> at line %d has no <!-- CHECKPOINT --> before it" % cc)
            sys.stderr.write("session-state: %s: %s. Nothing was written.\n" % (STATE, why))
            sys.stderr.write("  Fix the markers by hand (layout: %s); guessing where the block ends could swallow the narrative.\n" % TEMPLATE)
            return 3
        if len(body) > MAX_LINES:
            sys.stderr.write("session-state: the checkpoint is %d lines; the template asks for under ~%d, because it is shown whole in every new session\n" % (len(body), MAX_LINES))
    else:
        e = len(base)
        while e > 0 and not base[e - 1].strip():
            e -= 1
        if action != "created" and e >= len(body) and base[e - len(body):e] == body:
            action, new = "unchanged", list(base)
        else:
            action = action or "appended"
            new = list(base)
            if new and new[-1].strip():
                new.append("")
            new += body
    out = ("\r\n" if crlf else "\n").join(new) + ("\r\n" if crlf else "\n")
    old = _util.read(state) if os.path.isfile(state) else None
    if old is not None and old.replace("\r\n", "\n") == out.replace("\r\n", "\n"):
        action = "unchanged"
    else:
        os.makedirs(os.path.dirname(state), exist_ok=True)
        with open(state, "w", encoding="utf-8", newline="") as fh:
            fh.write(out)
    print("file\t%s\t%s" % (STATE, action))
    print("lines\t%d\t-" % len(body))
    return 0
