"""Per-test runs, passes, fails, skips and fail percentage across several test runs."""
import os
import re
import sys

from . import _util

HELP = """Usage: python tools/studio.py flaky-stats [--root DIR] [--format F] [--runs] [--all] [FILE ...]
Per-test runs, passes, fails, skips, fail percentage and pass/fail pattern across several test runs, with
the threshold row each test's rate fell in, read from the result files and logs /test-flakiness parses.
Observations, not a verdict: whether to quarantine stays in the skill.
  FILE        one test run per file, in run order (the order of the pattern); relative to the root. With
              none, the files under test-results/ and reports/ named *.xml, *.log or *.txt, sorted by path:
              pass the files yourself when their names do not sort in run order
  --format F  auto (default: found per file), junit, nunit or text
  --runs      also print one RUN row per file
  --all       also list tests with no fail and no skip (default: only tests with a fail or skip)
What it parses (one result per test case, in file order):
  junit   JUnit XML: each <testcase>; id is classname.name (name alone when none); a <failure> or <error>
          inside it is a fail, else <skipped> is a skip, else a pass
  nunit   NUnit XML: each <test-case>; id is its fullname (name when none); result Passed is a pass, Failed
          a fail, every other value a skip, so only Passed and Failed enter the history
  text    a line with PASSED or FAILED as a whole word, or "Test passed" / "Test failed": the id is the line
          without the marker, a leading ISO timestamp, ANSI colour codes, timing words like 12ms or (0.5s),
          and the punctuation [](): > | * - , around it. A line with more than one marker is not a result
CDATA sections and comments are skipped, XML entities in ids are decoded, a tag may run over several lines.
Output: TSV. Counts first, then rows:
  scan <dir> <present|absent>, runs <analysed> <read>, tests <n>, clean, flaky, tier <name> <n> <rule>,
  always_fail, no_result, data_note ("fewer than 5 runs" when analysed < 5), no_id, unrecognised <format>
  <word> <n>, RUN rows (--runs), then TEST <id> <runs> <pass> <fail> <skip> <fail_pct> <pattern> <flaky>
  <tier> <rule>, sorted by fail rate, highest first, then by id. pattern = P, F or S per result.
Tiers (every edge in exactly one): always-fail (no pass, a fail); suspected (a pass and a fail, fewer than 3
runs); high fail_pct > 25; moderate 5 <= fail_pct <= 25; low 1 <= fail_pct < 5; below-low 0 < fail_pct < 1.
Exit codes: 0 parsed at least one result; 1 the root cannot be read; 2 usage error; 3 no files to read;
4 files were read and held no result. Reads only."""

CDATA = "<![CDATA["
ENT = [("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&apos;", "'"), ("&amp;", "&")]


def xd(s):
    for a, b in ENT:
        s = s.replace(a, b)
    return s


def attr(tag, name):
    m = re.search(r"[ \t]" + re.escape(name) + r"[ \t]*=[ \t]*([\"'])", tag)
    if not m:
        return ""
    q = m.group(1)
    rest = tag[m.end():]
    e = rest.find(q)
    return xd(rest[:e] if e >= 0 else rest).strip()


def detect(text):
    nu = ju = False
    for l in text.split("\n"):
        if "<test-case" in l:
            nu = True
        elif "<testcase" in l:
            ju = True
    return "nunit" if nu else ("junit" if ju else "text")


def tag_end(s):
    qc = ""
    for i in range(1, len(s)):
        c = s[i]
        if qc:
            if c == qc:
                qc = ""
            continue
        if c in "\"'":
            qc = c
        elif c == ">":
            return i + 1
    return 0


def xml_tags(text):
    """Yield every tag string, skipping CDATA sections and comments; tags may span lines."""
    s = text.replace("\r", "")
    while s:
        p = s.find("<")
        if p < 0:
            return
        s = s[p:]
        if s.startswith(CDATA):
            e = s.find("]]>")
            if e < 0:
                return
            s = s[e + 3:]
            continue
        if s.startswith("<!--"):
            e = s.find("-->")
            if e < 0:
                return
            s = s[e + 3:]
            continue
        q = tag_end(s)
        if not q:
            return
        yield s[:q].replace("\n", " ")
        s = s[q:]


class Collector(object):
    def __init__(self, nfiles):
        self.order = []
        self.seen = {}
        self.noid = 0
        self.res = [0] * nfiles
        self.rp = [0] * nfiles
        self.rf = [0] * nfiles
        self.rs = [0] * nfiles
        self.rnoid = [0] * nfiles
        self.unrec = {}
        self.unrec_order = []

    def record(self, j, ident, code):
        if ident == "":
            self.noid += 1
            self.rnoid[j] += 1
            return
        ident = ident.replace("\t", " ")
        if ident not in self.seen:
            self.seen[ident] = {"P": 0, "F": 0, "S": 0, "pat": ""}
            self.order.append(ident)
        d = self.seen[ident]
        d[code] += 1
        d["pat"] += code
        {"P": self.rp, "F": self.rf, "S": self.rs}[code][j] += 1
        self.res[j] += 1

    def note_unrec(self, fmt, word):
        k = (fmt, word)
        if k not in self.unrec:
            self.unrec_order.append(k)
        self.unrec[k] = self.unrec.get(k, 0) + 1


def parse_xml(col, j, text, fmt):
    jopen, jid, jcode = False, "", "P"
    for t in xml_tags(text):
        c2 = t[1:2]
        if c2 in ("?", "!"):
            continue
        closing = c2 == "/"
        name = re.split(r"[ \t/>]", t[2:] if closing else t[1:], 1)[0]
        selfc = t[-2:-1] == "/"
        if fmt == "nunit":
            if not closing and name == "test-case":
                ident = attr(t, "fullname") or attr(t, "name")
                r = attr(t, "result")
                if r == "Passed":
                    col.record(j, ident, "P")
                elif r == "Failed":
                    col.record(j, ident, "F")
                else:
                    col.record(j, ident, "S")
                    if r not in ("Inconclusive", "Skipped"):
                        col.note_unrec("nunit", r or "(none)")
            continue
        if closing:
            if name == "testcase" and jopen:
                col.record(j, jid, jcode)
                jopen = False
            continue
        if name == "testcase":
            if jopen:
                col.record(j, jid, jcode)
                jopen = False
            ident, cn = attr(t, "name"), attr(t, "classname")
            jid = cn + "." + ident if cn else ident
            jcode = "P"
            if selfc:
                col.record(j, jid, "P")
            else:
                jopen = True
            continue
        if jopen:
            if name in ("failure", "error"):
                jcode = "F"
            elif name == "skipped" and jcode != "F":
                jcode = "S"
    if jopen:
        col.record(j, jid, jcode)


def parse_text(col, j, text):
    for line in text.replace("\r", "").split("\n"):
        s = re.sub(r"\x1b\[[0-9;]*m", "", line)
        hp = bool(re.search(r"(^|[^A-Za-z0-9_])PASSED([^A-Za-z0-9_]|$)", s))
        hf = bool(re.search(r"(^|[^A-Za-z0-9_])FAILED([^A-Za-z0-9_]|$)", s))
        tpz = "Test passed" in s
        tfl = "Test failed" in s
        if hp + hf + tpz + tfl != 1:
            continue
        if hp:
            code, marker = "P", "PASSED"
        elif hf:
            code, marker = "F", "FAILED"
        elif tpz:
            code, marker = "P", "Test passed"
        else:
            code, marker = "F", "Test failed"
        p = s.find(marker)
        t = s[:p] + " " + s[p + len(marker):]
        t = re.sub(r"^[ \t]*[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9:.]+Z?[ \t]*", "", t)
        out = " ".join(w for w in t.split() if not re.match(r"^\(?[0-9][0-9.]*(ms|s)\)?$", w))
        out = out.strip(" []():>|*-,")
        col.record(j, out, code)


def classify(p, f):
    n = p + f
    if n == 0:
        return "no-result", "only skipped results"
    if f == 0:
        return "none", "no fail in the counted results"
    if p == 0:
        return "always-fail", "no pass in the counted results"
    if n < 3:
        return "suspected", "flaky, fewer than 3 results"
    if f * 100 > 25 * n:
        return "high", "fail_pct > 25"
    if f * 100 >= 5 * n:
        return "moderate", "5 <= fail_pct <= 25"
    if f * 100 >= n:
        return "low", "1 <= fail_pct < 5"
    return "below-low", "0 < fail_pct < 1"


def pct1(f, n):
    if n == 0:
        return "-"
    v = (f * 1000) // n
    return "%d.%d" % (v // 10, v % 10)


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    fmt_arg, showruns, show_all, files = "auto", False, False, []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a == "--format":
            if i + 1 >= len(rest):
                sys.stderr.write("flaky-stats: --format needs a value\n")
                return 2
            fmt_arg = rest[i + 1]
            i += 2
            continue
        if a.startswith("--format="):
            fmt_arg = a[9:]
        elif a == "--runs":
            showruns = True
        elif a == "--all":
            show_all = True
        elif a.startswith("-") and len(a) > 1:
            sys.stderr.write("flaky-stats: unknown argument: %s (try --help)\n" % a)
            return 2
        else:
            files.append(a[2:] if a.startswith("./") else a)
        i += 1
    if fmt_arg not in ("auto", "junit", "nunit", "text"):
        sys.stderr.write("flaky-stats: --format takes auto, junit, nunit or text, got %s\n" % fmt_arg)
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("flaky-stats: cannot read root %s\n" % root)
        return 1
    if not files:
        found = set()
        for d in ("test-results", "reports"):
            full = os.path.join(root, d)
            if os.path.isdir(full):
                print("scan\t%s\tpresent" % d)
                for dp, _, fn in os.walk(full):
                    for f in fn:
                        if f.endswith((".xml", ".log", ".txt")):
                            found.add(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
            else:
                print("scan\t%s\tabsent" % d)
        files = sorted(found)
        if not files:
            sys.stderr.write("flaky-stats: no test result files under test-results/ or reports/; name the files\n")
            return 3
    else:
        for f in files:
            if not os.path.isfile(os.path.join(root, f)):
                sys.stderr.write("flaky-stats: no such file: %s\n" % f)
                return 3
    col = Collector(len(files))
    fmts = []
    for j, f in enumerate(files):
        text = _util.read(os.path.join(root, f))
        fmt = detect(text) if fmt_arg == "auto" else fmt_arg
        fmts.append(fmt)
        if fmt in ("junit", "nunit"):
            parse_xml(col, j, text, fmt)
        else:
            parse_text(col, j, text)
    analysed = sum(1 for x in col.res if x > 0)
    tests = []
    tc = {}
    nclean = nflaky = 0
    for ident in col.order:
        d = col.seen[ident]
        p, f, s = d["P"], d["F"], d["S"]
        n = p + f
        tier, rule = classify(p, f)
        if n > 0 and f == 0:
            nclean += 1
        if p > 0 and f > 0:
            nflaky += 1
        tc[tier] = tc.get(tier, 0) + 1
        tests.append((ident, n, p, f, s, tier, rule, d["pat"]))
    print("runs\t%d\t%d" % (analysed, len(files)))
    print("tests\t%d" % len(tests))
    print("clean\t%d\tno fail in the counted results" % nclean)
    print("flaky\t%d\ta pass and a fail in the counted results" % nflaky)
    print("tier\thigh\t%d\tfail_pct > 25" % tc.get("high", 0))
    print("tier\tmoderate\t%d\t5 <= fail_pct <= 25" % tc.get("moderate", 0))
    print("tier\tlow\t%d\t1 <= fail_pct < 5" % tc.get("low", 0))
    print("tier\tbelow-low\t%d\t0 < fail_pct < 1" % tc.get("below-low", 0))
    print("tier\tsuspected\t%d\tflaky, fewer than 3 results" % tc.get("suspected", 0))
    print("always_fail\t%d\tno pass in the counted results" % tc.get("always-fail", 0))
    print("no_result\t%d\tonly skipped results" % tc.get("no-result", 0))
    print("data_note\t%s" % ("fewer than 5 runs" if analysed < 5 else "-"))
    print("no_id\t%d" % col.noid)
    for k in col.unrec_order:
        print("unrecognised\t%s\t%s\t%d" % (k[0], k[1], col.unrec[k]))
    if showruns:
        for j, f in enumerate(files):
            print("RUN\t%d\t%s\t%s\t%d\t%d\t%d\t%d\t%d" % (j + 1, f, fmts[j], col.res[j], col.rp[j], col.rf[j], col.rs[j], col.rnoid[j]))
    listed = [t for t in tests if show_all or t[3] > 0 or t[4] > 0]

    import functools

    def cmp(a, b):
        if a[1] == 0 or b[1] == 0:
            if a[1] == 0 and b[1] == 0:
                return (a[0] > b[0]) - (a[0] < b[0])
            return 1 if a[1] == 0 else -1
        l, rr = a[3] * b[1], b[3] * a[1]
        if l != rr:
            return -1 if l > rr else 1
        return (a[0] > b[0]) - (a[0] < b[0])
    listed.sort(key=functools.cmp_to_key(cmp))
    for ident, n, p, f, s, tier, rule, pat in listed:
        print("TEST\t%s\t%d\t%d\t%d\t%d\t%s\t%s\t%s\t%s\t%s" % (ident, n, p, f, s, pct1(f, n), pat, "yes" if p > 0 and f > 0 else "no", tier, rule))
    return 4 if analysed == 0 else 0
