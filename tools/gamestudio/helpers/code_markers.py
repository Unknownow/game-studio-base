"""TODO/FIXME/HACK markers, debug calls, placeholder names and long files in the game's source."""
import fnmatch
import os
import re
import sys

from .. import config as cfgmod
from . import _util, project_state

HELP = """Usage: python tools/studio.py code-markers [--root DIR] [--long N] [--exclude PATTERN ...] [PATH ...]
TODO, FIXME and HACK markers, debug output calls, placeholder names and long files in the game's source,
with how many files were scanned. Observations, not a verdict.
  PATH          folders or files to scan, relative to the root or absolute; default: the code root
                project-state resolves (src/, Assets/ or Source/)
  --exclude P   skip paths matching the shell pattern P (relative to the root, * matching across
                folders), e.g. 'Assets/Plugins/*'
  --long N      a file of more than N lines is long (default 500)
What counts: source files (.gd .cs .cpp .cc .c .h .hpp .rs .py .js .ts .lua .java .kt); markers TODO,
FIXME, HACK as whole words in capitals; debug calls by language (print, Debug.Log*, UE_LOG, printf,
console.log/debug, debugger, println!, System.out.print*); placeholders (placeholder, temp_, wip_ in
any case); long files (function length is not measured).
Output: TSV. Counts first:
  scanned_files <n> <paths>, scanned_lines <n>, todo, fixme, hack, debug, placeholder <n>,
  long_files <n> <rule>
  MARK <TODO|FIXME|HACK> <path> <line>
  DEBUG <call> <path> <line>
  PLACEHOLDER <word> <path> <line>
  LONG <path> <lines>
Exit codes: 0 scanned (whatever it found); 1 the root cannot be read; 2 usage error; 3 no PATH given and the
code root is unset (prints scanned_files 0 code_root unset). Reads only."""

EXTS = {".gd", ".cs", ".cpp", ".cc", ".c", ".h", ".hpp", ".rs", ".py", ".js", ".ts", ".lua", ".java", ".kt"}
MARK_RE = re.compile(r"(?<![A-Za-z0-9_])(TODO|FIXME|HACK)(?![A-Za-z0-9_])")
PH_RE = re.compile(r"placeholder|temp_|wip_")
NB = r"(?<![A-Za-z0-9_.])"


def debug_call(line, ext):
    def first(pattern, strip=True):
        m = re.search(pattern, line)
        return m.group(1) if m else ""
    if ext == ".gd":
        return first(NB + r"(print_rich|print_debug|printraw|printt|prints|print)\(")
    if ext == ".cs":
        m = re.search(r"(Debug\.Log[A-Za-z]*)\(", line)
        return m.group(1) if m else first(NB + r"(print)\(")
    if ext in (".c", ".cc", ".cpp", ".h", ".hpp"):
        m = re.search(r"(UE_LOG|AddOnScreenDebugMessage)\(", line)
        return m.group(1) if m else first(NB + r"(printf)\(")
    if ext in (".js", ".ts"):
        m = re.search(r"(console\.(?:log|debug))\(", line)
        return m.group(1) if m else first(r"(?<![A-Za-z0-9_])(debugger)(?![A-Za-z0-9_])")
    if ext in (".py", ".lua"):
        return first(NB + r"(print)\(")
    if ext == ".rs":
        return first(r"((?:eprintln|println|dbg)!)\(")
    if ext in (".java", ".kt"):
        m = re.search(r"(System\.out\.print[a-z]*)\(", line)
        return m.group(1) if m else first(NB + r"(println)\(")
    return ""


def _files(root, p):
    full = p if os.path.isabs(p) else os.path.join(root, p)
    out = []
    if os.path.isfile(full):
        out.append(full)
    elif os.path.isdir(full):
        for dp, dn, fn in os.walk(full):
            for f in fn:
                if os.path.splitext(f)[1].lower() in EXTS:
                    out.append(os.path.join(dp, f))
    return out


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    long_n, paths, excl = 500, [], []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a in ("--long", "--exclude"):
            if i + 1 >= len(rest):
                sys.stderr.write("code-markers: %s needs a value\n" % a)
                return 2
            if a == "--long":
                if not re.match(r"^[0-9]+$", rest[i + 1]):
                    sys.stderr.write("code-markers: --long takes a whole number\n")
                    return 2
                long_n = int(rest[i + 1])
            else:
                excl.append(rest[i + 1])
            i += 2
            continue
        if a.startswith("-") and len(a) > 1:
            sys.stderr.write("code-markers: unknown argument: %s (try --help)\n" % a)
            return 2
        paths.append(a.rstrip("/\\") or a)
        i += 1
    if not os.path.isdir(root):
        sys.stderr.write("code-markers: cannot read root %s\n" % root)
        return 1
    if not paths:
        cr, _ = project_state.resolve_code_root(root, cfgmod.load(root))
        if not cr:
            print("scanned_files\t0\tcode_root unset")
            sys.stderr.write("code-markers: the code root is unset (no engine set and no single src/, Assets/ or Source/); pass a PATH\n")
            return 3
        paths = [cr]
    files = set()
    for p in paths:
        for f in _files(root, p.replace("\\", "/") if re.match(r"^[A-Za-z]:\\", p) else p):
            files.add(f)
    rels = {}
    for f in files:
        rel = os.path.relpath(f, root).replace(os.sep, "/") if not os.path.relpath(f, root).startswith("..") else f.replace(os.sep, "/")
        if any(fnmatch.fnmatchcase(rel, x) for x in excl):
            continue
        rels[rel] = f
    cnt = {"TODO": 0, "FIXME": 0, "HACK": 0}
    ndebug = nph = nlines = nlong = 0
    out = []
    for rel in sorted(rels):
        text = _util.read(rels[rel])
        lines = text.split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        ext = os.path.splitext(rel)[1].lower()
        nlines += len(lines)
        for n, ln in enumerate(lines, 1):
            for m in MARK_RE.finditer(ln):
                cnt[m.group(1)] += 1
                out.append("MARK\t%s\t%s\t%d" % (m.group(1), rel, n))
            c = debug_call(ln, ext)
            if c:
                ndebug += 1
                out.append("DEBUG\t%s\t%s\t%d" % (c, rel, n))
            m = PH_RE.search(ln.lower())
            if m:
                nph += 1
                out.append("PLACEHOLDER\t%s\t%s\t%d" % (m.group(0), rel, n))
        if len(lines) > long_n:
            nlong += 1
            out.append("LONG\t%s\t%d" % (rel, len(lines)))
    print("scanned_files\t%d\t%s" % (len(rels), ",".join(paths)))
    print("scanned_lines\t%d" % nlines)
    print("todo\t%d\nfixme\t%d\nhack\t%d\ndebug\t%d\nplaceholder\t%d" % (cnt["TODO"], cnt["FIXME"], cnt["HACK"], ndebug, nph))
    print("long_files\t%d\tmore than %d lines" % (nlong, long_n))
    for ln in out:
        print(ln)
    return 0
