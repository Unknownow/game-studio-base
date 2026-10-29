"""Line-based reader for the three registry YAML files (entities, tr, architecture).

It reads only the layout the shipped registries use and reports anything else as a layout finding,
leaving that registry's entries out rather than guessing.
"""
import re

SRC_FIELD = {"entities": "source", "tr": "gdd", "architecture": "adr"}
NAME_KEYS = {}
for _s in ("entities", "items", "formulas", "constants"):
    NAME_KEYS[("entities", _s)] = "name"
NAME_KEYS[("tr", "requirements")] = "id"
NAME_KEYS[("architecture", "state_ownership")] = "state"
NAME_KEYS[("architecture", "interfaces")] = "contract"
NAME_KEYS[("architecture", "performance_budgets")] = "system target_fps"
NAME_KEYS[("architecture", "api_decisions")] = "purpose"
NAME_KEYS[("architecture", "forbidden_patterns")] = "pattern"
ALLOWED = {"entities": "active|deprecated",
           "tr": 'active|deprecated|"superseded-by: TR-<system>-NNN"',
           "architecture": 'active|"superseded_by: ADR-NNNN"'}
TRID = r"TR-[a-z0-9]+(?:-[a-z0-9]+)*-[0-9]+"
REG_PATHS = {"entities": "design/registry/entities.yaml", "tr": "docs/architecture/tr-registry.yaml",
             "architecture": "docs/registry/architecture.yaml"}


class Entry(object):
    def __init__(self, reg, section, line):
        self.reg = reg
        self.section = section
        self.line = line
        self.end = line
        self.key = ""
        self.name = ""
        self.source = ""
        self.status = ""
        self.status_set = False
        self.status_line = 0
        self.refs = []   # (how, path, line)


class Registry(object):
    def __init__(self, name, path, shown=None, missing=False):
        self.name = name
        self.path = path
        self.shown = shown or path
        self.missing = missing
        self.bad = False
        self.entries = []
        self.layout = []     # (found, expected, line)
        self.unquoted = []   # (value, line)
        self.raw = {}


def qclose(s, q):
    i = 0
    while i < len(s):
        c = s[i]
        if q == '"' and c == "\\":
            i += 2
            continue
        if c == q:
            if q == "'" and s[i + 1:i + 2] == "'":
                i += 2
                continue
            return i + 1
        i += 1
    return 0


def keysplit(s):
    p = s.find(": ")
    if p < 0 and s.endswith(":"):
        p = len(s) - 1
    if p <= 0:
        return None
    k, v = s[:p], s[p + 1:].strip(" \t")
    if not re.match(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$", k):
        return None
    return k, v


class PVal(object):
    pass


def pval(v):
    r = PVal()
    r.v, r.q, r.uncl, r.flow, r.flowopen, r.block, r.colon = "", "", False, False, False, False, False
    if v == "":
        return r
    c = v[0]
    if c == "#":
        return r
    if c in "\"'":
        r.q = c
        rest = v[1:]
        i = qclose(rest, c)
        if i == 0:
            r.uncl = True
            r.v = rest
            return r
        r.v = rest[:i - 1]
        r.v = r.v.replace("''", "'") if c == "'" else r.v.replace('\\"', '"')
        return r
    if c in "[{":
        r.flow = True
        h = v
        i = h.find(" #")
        if i >= 0:
            h = h[:i]
        h = h.rstrip(" \t")
        closer = "]" if c == "[" else "}"
        if not h.endswith(closer):
            r.flowopen = True
        r.v = h
        return r
    if re.match(r"^[|>][-+0-9]*([ \t]+#.*)?$", v):
        r.block = True
        return r
    i = v.find(" #")
    if i >= 0:
        v = v[:i]
    v = v.rstrip(" \t")
    r.v = v
    if ": " in v or v.endswith(":"):
        r.colon = True
    return r


def opens(s, n):
    r = s
    if r == "-" or r.startswith("- "):
        r = r[1:].lstrip(" ")
        if re.match(r"^[|>][-+0-9]*[ \t]*(#.*)?$", r):
            return n
        n = n + len(s) - len(r)
    if r == "" or r[0] in ": #\t":
        return -1
    p = r.find(":")
    if p < 0:
        return -1
    v = r[p + 1:].strip(" \t")
    return n if re.match(r"^[|>][-+0-9]*[ \t]*(#.*)?$", v) else -1


class Parser(object):
    def __init__(self, reg):
        self.r = reg
        self.sec = ""
        self.secempty = False
        self.dcol = -1
        self.fcol = -1
        self.inq = ""
        self.inq_line = 0
        self.blk = -1
        self.cur = None
        self.cf = ""
        self.cflist = False
        self.cfplain = False
        self.listcol = -1
        self.fnr = 0

    def layout(self, found, expected, ln=None):
        self.r.layout.append((found, expected, self.fnr if ln is None else ln))
        self.r.bad = True

    def close_entry(self):
        self.cur = None
        self.cf = ""
        self.cflist = False
        self.cfplain = False

    def addref(self, e, how, path, ln):
        if not path:
            return
        e.refs.append((how, path, ln))
        if how == SRC_FIELD.get(self.r.name) and not e.source:
            e.source = path

    def field(self, K, V, ln):
        e = self.cur
        p = pval(V)
        self.cf = K
        self.listcol = -1
        self.cflist = (p.v == "" and p.q == "" and not p.flow and not p.block)
        self.cfplain = (not self.cflist and not p.block and not p.uncl)
        e.end = ln
        if p.colon and self.legacy_status(K, p.v):
            self.r.unquoted.append((p.v, ln))
        elif p.colon:
            self.layout('an unquoted value holding ": "', "the value in quotes")
        if p.flowopen:
            self.layout("a flow list or map that runs past its line", "[a, b] on one line, or a block list")
        if p.uncl:
            self.inq, self.inq_line = p.q, ln
        if K == "status":
            e.status, e.status_line, e.status_set = p.v, ln, True
        if K == SRC_FIELD.get(self.r.name):
            self.addref(e, K, p.v, ln)
        if K == "referenced_by" and p.flow and not p.flowopen:
            for it in p.v[1:-1].split(","):
                q = pval(it.strip(" \t"))
                self.addref(e, "referenced_by", q.v, ln)

    def legacy_status(self, K, v):
        if self.r.name != "architecture" or K != "status" or not v.startswith("superseded_by: "):
            return False
        rest = v[15:]
        return rest != "" and ": " not in rest and not rest.endswith(":")

    def list_item(self, s, ln):
        if self.cf != "referenced_by":
            return
        q = pval(s[2:])
        self.addref(self.cur, "referenced_by", q.v, ln)

    def deeper(self, n, s):
        self.cur.end = self.fnr
        if self.cflist:
            if s == "-" or s.startswith("- "):
                if self.listcol == -1:
                    self.listcol = n
                if n == self.listcol:
                    self.list_item(s, self.fnr)
            return
        if self.cfplain and (": " in s or s.endswith(":")):
            self.layout("a key at column %d under the value of %s:" % (n, self.cf),
                        "a field at column %d, or the value in quotes" % self.fcol)

    def top_line(self, s):
        self.close_entry()
        self.sec = ""
        self.secempty = False
        self.dcol = -1
        if s in ("---", "..."):
            return
        ks = keysplit(s)
        if not ks:
            self.layout("text with no key", "key: value at column 0")
            return
        K, V = ks
        p = pval(V)
        if p.v == "" and p.q == "" and not p.flow and not p.block:
            self.sec = K
            return
        if p.flow and p.v == "[]":
            self.sec, self.secempty = K, True
            return
        if (self.r.name, K) in NAME_KEYS:
            self.layout("a value after %s:" % K, "[] or nothing after %s:, the entries below" % K)

    def dash_line(self, n, s):
        if not self.sec:
            self.close_entry()
            self.layout("a list item outside a section", "a section key at column 0 above it")
            return
        if self.secempty:
            self.layout("a list item under %s: []" % self.sec, "nothing after %s: when it has entries" % self.sec)
            return
        if self.cur is not None and n > self.dcol:
            if n > self.fcol:
                self.deeper(n, s)
                return
            if n == self.fcol and self.cflist and (self.listcol == -1 or self.listcol == self.fcol):
                self.listcol = self.fcol
                self.cur.end = self.fnr
                self.list_item(s, self.fnr)
                return
            if n == self.fcol:
                self.layout("a list item at column %d" % self.fcol, "a field at column %d, or a list under a field with no value" % self.fcol)
                return
            self.layout("a list item at column %d" % n, "column %d for the next entry, or deeper than column %d" % (self.dcol, self.fcol))
            return
        self.close_entry()
        if self.dcol == -1:
            if n not in (0, 2):
                self.layout("a list item at column %d" % n, "column 0 or 2")
            self.dcol, self.fcol = n, n + 2
        elif n != self.dcol:
            self.layout("a list item at column %d" % n, "column %d, like the first entry of %s" % (self.dcol, self.sec))
            return
        e = Entry(self.r.name, self.sec, self.fnr)
        self.r.entries.append(e)
        self.cur = e
        self.cf, self.cflist, self.cfplain, self.listcol = "", False, False, -1
        rest = "" if s == "-" else s[2:]
        ks = keysplit(rest)
        if not ks:
            self.layout("an entry with no key", "- key: value")
            return
        K, V = ks
        nk = NAME_KEYS.get((self.r.name, self.sec), "")
        if nk and (" " + K + " ") not in (" " + nk + " "):
            self.layout("an entry that starts with %s:" % K, "- %s: as the first line of each entry" % nk.split(" ")[0])
        p = pval(V)
        if p.v == "" and p.q == "" and not p.flow and not p.uncl:
            self.layout("an entry with an empty %s" % K, "- %s: <name>" % K)
        e.key, e.name = K, p.v
        self.field(K, V, self.fnr)

    def plain_line(self, n, s):
        if not self.sec:
            self.layout("an indented line outside a section", "a section key at column 0 above it")
            return
        if self.cur is None:
            self.layout("a line at column %d before any entry" % n, "- key: value at column 0 or 2")
            return
        if n > self.fcol:
            self.deeper(n, s)
            return
        if n < self.fcol:
            self.layout("a line at column %d" % n, "a field at column %d, two past the dash" % self.fcol)
            return
        ks = keysplit(s)
        if not ks:
            self.layout("text with no key at column %d" % self.fcol, "key: value")
            return
        self.field(ks[0], ks[1], self.fnr)

    def line(self, line):
        self.r.raw[self.fnr] = line
        if self.inq:
            if qclose(line, self.inq):
                self.inq = ""
            if self.cur is not None:
                self.cur.end = self.fnr
            return
        t = line.lstrip(" \t")
        if t == "" or t.startswith("#"):
            return
        n = len(line) - len(line.lstrip(" "))
        if self.blk >= 0:
            if n > self.blk:
                if self.cur is not None:
                    self.cur.end = self.fnr
                return
            self.blk = -1
        if re.match(r"^ *\t", line):
            self.layout("a tab in the indent", "spaces only")
            return
        s = line[n:]
        self.blk = opens(s, n)
        if s == "-" or s.startswith("- "):
            self.dash_line(n, s)
            return
        if n == 0:
            self.top_line(s)
            return
        self.plain_line(n, s)

    def end(self):
        if self.inq:
            self.layout("a quote that never closes", "the closing quote", self.inq_line)
        self.inq = ""


def read_registry(reg, text):
    p = Parser(reg)
    if text.startswith("\ufeff"):
        text = text[1:]
    for i, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
        p.fnr = i
        p.line(line)
    p.fnr = max(p.fnr, 1)
    p.end()
    return reg


def status_ok(reg, v):
    if v == "active":
        return True
    if reg == "entities":
        return v == "deprecated"
    if reg == "architecture":
        return bool(re.match(r"^superseded_by: ADR-[0-9]+$", v))
    if v == "deprecated":
        return True
    if not v.startswith("superseded-by: "):
        return False
    parts = [x.strip() for x in v[15:].split(",")]
    return bool(parts) and all(re.match("^" + TRID + "$", x) for x in parts)
