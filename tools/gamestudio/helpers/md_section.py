"""Find, read and edit sections of a Markdown file by heading."""
import os
import re
import sys

HELP = """Usage: python tools/studio.py md-section <command> FILE [args]
  list FILE                       every heading: level, first and last line, title
  status FILE [HEADING ...]       COMPLETE / EMPTY / PLACEHOLDER per section
  extract FILE HEADING [--body]   the section's lines (--body: without its heading)
  replace FILE HEADING            the section's body, subsections included, becomes stdin
  insert-before FILE HEADING      stdin goes in just above the heading
  set-field FILE FIELD VALUE [--after FIELD2]
                                  a header field line (`> **Status**: Ready`) gets VALUE;
                                  when missing, --after adds it below FIELD2 in its style
HEADING is the title as written, matched without regard to case, extra spaces, a leading
number, an HTML comment or emphasis. Prefix it with #s ('## Status') to match one level.
A section runs from its heading to the line before the next heading of the same or a
higher level. Lines inside code fences and HTML comments are never headings.
Status: PLACEHOLDER when a line holds [To be designed], [TBD], [To be written] or starts
with TODO/_TODO; EMPTY when no line holds text; COMPLETE otherwise.
Output is TSV. Exit codes: 0 done; 1 cannot read or write FILE; 2 usage error;
3 HEADING or FIELD not found; 4 HEADING matches more than one heading (nothing written)."""


def _trim(s):
    return s.strip(" \t")


def _norm(s):
    while True:
        p = s.find("<!--")
        if p < 0:
            break
        e = s.find("-->", p + 4)
        s = s[:p] + " " if e < 0 else s[:p] + " " + s[e + 3:]
    s = re.sub(r"\*+", "", s)
    s = " " + s + " "
    s = re.sub(r"[ \t]_+", " ", s)
    s = re.sub(r"_+[ \t]", " ", s)
    s = re.sub(r"[ \t]+", " ", _trim(s).lower())
    return re.sub(r"^[0-9]+[.)]? ", "", s)


def _span_end(t, k):
    i = 0
    while i < len(t):
        if t[i] != "`":
            i += 1
            continue
        j = i
        while j < len(t) and t[j] == "`":
            j += 1
        if j - i == k:
            return i + 1
        i = j
    return 0


def _fence_of(s):
    m = re.match(r" {0,3}(`{3,}|~{3,})", s)
    return m.group(1) if m else ""


def _closes(s, f):
    m = re.match(r" {0,3}(" + re.escape(f[0]) + r"+)\s*$", s)
    return bool(m) and len(m.group(1)) >= len(f)


class Doc(object):
    def __init__(self, text):
        raw = text.split("\n")
        self.crlf = bool(raw) and raw[0].endswith("\r")
        raw = [l[:-1] if l.endswith("\r") else l for l in raw]
        if raw and raw[-1] == "" and len(raw) > 1:
            self.trailing_nl = True
            raw = raw[:-1]
        else:
            self.trailing_nl = False
        self.raw = raw
        n = len(raw)
        self.lvl = [0] * (n + 1)
        self.title = [""] * (n + 1)
        self.text = [False] * (n + 1)
        self.mark = [False] * (n + 1)
        self.heads = []
        infence = ""
        incomment = False
        for i, rawline in enumerate(raw, 1):
            line = rawline.rstrip("\r")
            if infence:
                if _closes(line, infence):
                    infence = ""
                continue
            f = _fence_of(line)
            if f:
                infence = f
                self.text[i] = True
                continue
            cstart = incomment
            rest, s = "", line
            while s != "":
                if incomment:
                    p = s.find("-->")
                    if p < 0:
                        s = ""
                        break
                    s = s[p + 3:]
                    incomment = False
                else:
                    p = s.find("<!--")
                    b = s.find("`")
                    if b >= 0 and (p < 0 or b < p):
                        k = 0
                        while b + k < len(s) and s[b + k] == "`":
                            k += 1
                        e = _span_end(s[b + k:], k)
                        q = b + k + e - 1 + k if e > 0 else b + k
                        rest += s[:q]
                        s = s[q:]
                        continue
                    if p < 0:
                        rest += s
                        s = ""
                        break
                    rest += s[:p]
                    s = s[p + 4:]
                    incomment = True
            startcomment = bool(re.match(r"^[ \t]*<!--", line))
            m = re.match(r" {0,3}(#{1,6})(?:[ \t]|$)(.*)$", line)
            if not cstart and not startcomment and m:
                t = _trim(m.group(2))
                if re.search(r"(^| )#+$", t):
                    t = _trim(re.sub(r"#+$", "", t))
                self.lvl[i] = len(m.group(1))
                self.title[i] = t
                self.heads.append(i)
                continue
            r = _trim(rest)
            if r and not re.match(r"^(---+|\*\*\*+|___+)$", r):
                self.text[i] = True
            if re.search(r"\[To be designed\]|\[TBD\]|\[To be written\]", rest) or re.match(r"^_?TODO", line):
                self.mark[i] = True
        self.n = n

    def last_of(self, h):
        for j in self.heads:
            if j > h and self.lvl[j] <= self.lvl[h]:
                return j - 1
        return self.n

    def status_of(self, h):
        anyt = False
        for L in range(h + 1, self.last_of(h) + 1):
            if self.mark[L]:
                return "PLACEHOLDER"
            if self.text[L]:
                anyt = True
        return "COMPLETE" if anyt else "EMPTY"

    def find(self, arg):
        want = _trim(arg)
        wl = 0
        while wl < len(want) and want[wl] == "#":
            wl += 1
        want = _norm(want[wl:])
        return [h for h in self.heads if _norm(self.title[h]) == want and (wl == 0 or self.lvl[h] == wl)]

    def out(self, lines):
        nl = "\r\n" if self.crlf else "\n"
        s = nl.join(lines)
        return s + (nl if self.trailing_nl else "")


def _field_prefix(line, name):
    norm_line = re.sub(r"^[ \t]*", "", line)
    norm_line = re.sub(r"^> ?", "", norm_line)
    norm_line = re.sub(r"^- ", "", norm_line).replace("*", "")
    if not norm_line.lower().startswith(name.lower() + ":"):
        return ""
    p = line.lower().find(name.lower())
    if p < 0:
        return ""
    q = p + len(name)
    while q < len(line) and line[q] == "*":
        q += 1
    if q >= len(line) or line[q] != ":":
        return ""
    q += 1
    while q < len(line) and line[q] == "*":
        q += 1
    while q < len(line) and line[q] in " \t":
        q += 1
    return line[:q]


def _err(msg):
    sys.stderr.write("md-section: %s\n" % msg)


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        return fh.read()


def _one(doc, arg):
    m = doc.find(arg)
    if not m:
        _err('no heading "%s" in the file' % arg)
        return None, 3
    if len(m) > 1:
        _err('"%s" matches %d headings (lines %s); add a level ("## %s") or a longer title. Nothing was written.'
             % (arg, len(m), ", ".join(map(str, m)), _trim(arg)))
        return None, 4
    return m[0], 0


def main(root, argv):
    if not argv or argv[0] in ("-h", "--help"):
        if not argv:
            sys.stderr.write("md-section: no command (try --help)\n")
            return 2
        print(HELP)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd not in ("list", "status", "extract", "replace", "insert-before", "set-field"):
        _err("unknown command: %s (try --help)" % cmd)
        return 2
    if not rest:
        _err("%s needs a FILE (try --help)" % cmd)
        return 2
    path, rest = rest[0], rest[1:]
    if not os.path.isfile(path):
        _err("cannot read %s" % path)
        return 1
    body_only, field, value, after, heads = False, "", "", "", []
    if cmd == "list":
        if rest:
            _err("list takes only FILE (try --help)")
            return 2
    elif cmd == "status":
        heads = rest
    elif cmd in ("extract", "replace", "insert-before"):
        if not rest:
            _err("%s needs a HEADING (try --help)" % cmd)
            return 2
        heads = [rest[0]]
        rest = rest[1:]
        if cmd == "extract" and rest[:1] == ["--body"]:
            body_only, rest = True, rest[1:]
        if rest:
            _err("unexpected argument: %s (try --help)" % rest[0])
            return 2
    else:
        if len(rest) < 2:
            _err("set-field needs FIELD and VALUE (try --help)")
            return 2
        field, value, rest = rest[0], rest[1], rest[2:]
        if rest[:1] == ["--after"]:
            if len(rest) < 2:
                _err("--after needs a FIELD (try --help)")
                return 2
            after, rest = rest[1], rest[2:]
        if rest:
            _err("unexpected argument: %s (try --help)" % rest[0])
            return 2
        if "\n" in value:
            _err("VALUE cannot hold a newline (try --help)")
            return 2
    body = []
    if cmd in ("replace", "insert-before"):
        lines = sys.stdin.read().replace("\r\n", "\n").split("\n")
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines:
            _err("nothing on stdin to write (try --help)")
            return 2
        body = lines
    doc = Doc(_read(path))
    raw = doc.raw
    if cmd == "list":
        print("headings\t%d" % len(doc.heads))
        for h in doc.heads:
            print("%d\t%d\t%d\t%s" % (doc.lvl[h], h, doc.last_of(h), doc.title[h].replace("\t", " ")))
        return 0
    if cmd == "status":
        picks = []
        if not heads:
            picks = [(h, None) for h in doc.heads]
        else:
            for a in heads:
                m = doc.find(a)
                picks.extend([(h, None) for h in m] if m else [(0, a)])
        c = e = p = nf = 0
        lines = []
        for h, miss in picks:
            if h == 0:
                nf += 1
                lines.append("NOT_FOUND\t-\t" + miss)
                continue
            st = doc.status_of(h)
            c += st == "COMPLETE"
            e += st == "EMPTY"
            p += st == "PLACEHOLDER"
            lines.append("%s\t%d-%d\t%s" % (st, h, doc.last_of(h), doc.title[h].replace("\t", " ")))
        print("sections\t%d\ncomplete\t%d\nempty\t%d\nplaceholder\t%d\nnot_found\t%d" % (len(picks) - nf, c, e, p, nf))
        for l in lines:
            print(l)
        return 0
    if cmd == "extract":
        h, code = _one(doc, heads[0])
        if code:
            return code
        a = h + (1 if body_only else 0)
        for L in range(a, doc.last_of(h) + 1):
            print(raw[L - 1].rstrip("\r"))
        return 0
    old_text = _read(path)
    if cmd in ("replace", "insert-before"):
        h, code = _one(doc, heads[0])
        if code:
            return code
        a, b = h, doc.last_of(h)
        if cmd == "replace":
            new = raw[:a] + [""] + body + ([""] if b < doc.n else []) + raw[b:]
            action, line = "replaced", a
        else:
            nb = len(body)
            same = a - nb - 1 >= 1
            for k in range(nb if same else 0):
                if raw[a - nb - 2 + k].rstrip("\r") != body[k]:
                    same = False
            if same and raw[a - 2].strip():
                same = False
            sep = 0
            if not same and a > 1 and raw[a - 2].rstrip("\r").strip():
                sep = 1
            if same:
                new, action, line = list(raw), "unchanged", a - nb - 1
            else:
                new = raw[:a - 1] + ([""] if sep else []) + body + [""] + raw[a - 1:]
                action, line = "inserted", a + sep
    else:
        at = aft = 0
        pre = apre = cur = ""
        for L in range(1, doc.n + 1):
            if doc.lvl[L] > 0 or not doc.text[L]:
                continue
            s = raw[L - 1].rstrip("\r")
            if not at:
                p = _field_prefix(s, field)
                if p:
                    at, pre, cur = L, p, s[len(p):]
            if after and not aft:
                p = _field_prefix(s, after)
                if p:
                    aft, apre = L, p
        cr = "\r" if doc.crlf else ""
        if at:
            if cur == value:
                new, action, line = list(raw), "unchanged", at
            else:
                new = list(raw)
                new[at - 1] = pre + value + cr
                action, line = "set", at
        else:
            if not after:
                _err('no "%s" field in the file (add --after FIELD to add it)' % field)
                return 3
            if not aft:
                _err('no "%s" field, and no "%s" field to add it after' % (field, after))
                return 3
            p = apre.lower().find(after.lower())
            npre = apre[:p] + field + apre[p + len(after):]
            new = raw[:aft] + [npre + value + cr] + raw[aft:]
            action, line = "added", aft + 1
    out = doc.out(new)
    if action != "unchanged" and out == old_text:
        action = "unchanged"
    if action != "unchanged":
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(out)
        except OSError:
            _err("could not write %s" % path)
            return 1
    print("file\t%s\t%s" % (path, action))
    print("line\t%s\t-" % line)
    return 0
