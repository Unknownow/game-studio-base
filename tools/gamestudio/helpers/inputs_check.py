"""FOUND / EMPTY / ABSENT for each input a skill declares."""
import os
import re
import sys

from . import _util

HELP = """Usage: python tools/studio.py inputs-check [--root DIR] [--from FILE|-] [SPEC...]
FOUND / EMPTY / ABSENT for each input a skill declares, so "check this before producing any report"
is one call. Observations, not a verdict: which inputs are required is the calling skill's call.
  SPEC        a path relative to the root: a file, a folder, or a glob. `*` and `?` stay inside one
              folder, `**/` spans folders, a trailing `/` matches folders instead of files. A backslash
              is read as `/`; the row keeps the spec as given.
  --from F    read more specs from F, one per line (`-` is stdin); blank lines and `#` lines are skipped
Output: TSV. Four count rows, then one row per spec in the order given:
  inputs <n> / found <n> / empty <n> / absent <n>
  <STATUS> <spec> <matches> <first match, or ->
STATUS: FOUND (a match holds something other than whitespace), EMPTY (matches exist but every one is
blank; a folder with no such file counts), ABSENT (nothing matched).
Exit codes: 0 checked every spec; 1 the root or the --from file cannot be read; 2 usage error (no spec,
an absolute path, a tab in a spec, an unknown flag). Reads only."""


def glob_re(g):
    out, i, n = "^", 0, len(g)
    while i < n:
        c = g[i]
        if c == "*":
            if g[i + 1:i + 2] == "*":
                if g[i + 2:i + 3] == "/":
                    out += "(.*/)?"
                    i += 3
                    continue
                out += ".*"
                i += 2
                continue
            out += "[^/]*"
        elif c == "?":
            out += "[^/]"
        elif c == "[" and g.find("]", i + 2) > 0:
            j = g.find("]", i + 2)
            cls = g[i + 1:j]
            if cls.startswith("!"):
                cls = "^" + cls[1:]
            out += "[" + cls + "]"
            i = j + 1
            continue
        else:
            out += re.escape(c)
        i += 1
    return re.compile(out + "$")


def glob_matches(root, g):
    typ = "f"
    if g.endswith("/"):
        typ, g = "d", g[:-1]
    parts = g.split("/")
    base = []
    for p in parts[:-1]:
        if any(ch in p for ch in "*?["):
            break
        base.append(p)
    start = os.path.join(root, *base) if base else root
    if not os.path.isdir(start):
        return []
    rx = glob_re(g)
    prefix = "/".join(base)
    found = []
    for dp, dn, fn in os.walk(start):
        names = dn if typ == "d" else fn
        for n in names:
            full = os.path.join(dp, n)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rx.match(rel):
                found.append(rel)
    return sorted(found)


def has_content(path):
    if os.path.isfile(path):
        try:
            return bool(_util.read(path).strip())
        except OSError:
            return False
    if os.path.isdir(path):
        for dp, _, fn in os.walk(path):
            for f in fn:
                if has_content(os.path.join(dp, f)):
                    return True
    return False


def main(root, argv):
    specs = []
    frm = None
    rest = list(argv)
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a in ("--root", "--from"):
            if i + 1 >= len(rest):
                sys.stderr.write("inputs-check: %s needs a value\n" % a)
                return 2
            if a == "--root":
                root = os.path.abspath(rest[i + 1])
            else:
                frm = rest[i + 1]
            i += 2
            continue
        if a.startswith("--root="):
            root = os.path.abspath(a[7:])
        elif a.startswith("--from="):
            frm = a[7:]
        elif a == "--":
            specs.extend(rest[i + 1:])
            break
        elif a.startswith("-") and len(a) > 1:
            sys.stderr.write("inputs-check: unknown argument: %s (try --help)\n" % a)
            return 2
        else:
            specs.append(a)
        i += 1
    if frm is not None:
        try:
            text = sys.stdin.read() if frm == "-" else _util.read(frm)
        except OSError:
            sys.stderr.write("inputs-check: cannot read --from file %s\n" % frm)
            return 1
        for ln in text.split("\n"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                specs.append(ln)
    specs = [s for s in specs if s]
    if not specs:
        sys.stderr.write("inputs-check: no input spec given (try --help)\n")
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("inputs-check: cannot read root %s\n" % root)
        return 1
    for s in specs:
        p = s.replace("\\", "/")
        if p.startswith("/") or re.match(r"^[A-Za-z]:", p):
            sys.stderr.write("inputs-check: specs are relative to the root, got %s\n" % s)
            return 2
        if "\t" in s:
            sys.stderr.write("inputs-check: a spec cannot contain a tab (the output is TSV)\n")
            return 2
    rows, nf, ne, na = [], 0, 0, 0
    for spec in specs:
        pat = spec.replace("\\", "/")
        if pat.startswith("./"):
            pat = pat[2:]
        shown = spec[2:] if spec.startswith("./") or spec.startswith(".\\") else spec
        if any(ch in pat for ch in "*?["):
            matches = glob_matches(root, pat)
        else:
            q = pat.rstrip("/")
            matches = [q] if os.path.exists(os.path.join(root, q)) else []
        if not matches:
            na += 1
            rows.append(("ABSENT", shown, 0, "-"))
            continue
        count, first, status = len(matches), matches[0], "EMPTY"
        for m in matches:
            if status == "EMPTY" and has_content(os.path.join(root, m)):
                status = "FOUND"
        if len(matches) == 1 and os.path.isdir(os.path.join(root, matches[0])) and matches[0] == pat.rstrip("/"):
            files = []
            for dp, _, fn in os.walk(os.path.join(root, matches[0])):
                for f in fn:
                    files.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
            files.sort()
            count = len(files)
            first = files[0] if files else "-"
        if status == "FOUND":
            nf += 1
        else:
            ne += 1
        rows.append((status, shown, count, first))
    print("inputs\t%d" % len(specs))
    print("found\t%d" % nf)
    print("empty\t%d" % ne)
    print("absent\t%d" % na)
    for r in rows:
        print("\t".join(str(c) for c in r))
    return 0
