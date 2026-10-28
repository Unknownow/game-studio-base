"""The facts skills read off story files, one row per story, and with --lint the rules each trips."""
import os
import re
import sys

from . import _util

HELP = """Usage: python tools/studio.py story-facts [--root DIR] [--all | --sprint | PATH ...] [--lint]
                                         [--granularity coarse|balanced|fine]
  --all       every production/epics/**/story-*.md (the default)
  --sprint    the stories production/sprint-status.yaml lists in its file: entries
  PATH ...    these story files, relative to the root
  --lint      also print the rules each story trips
  --granularity  the AC minimums --lint applies; default coarse
Output: TSV. Counts first (stories <n> <scope>, one count per state, lint <n> with --lint), then
  STORY <path> <state> <status> <type> <layer> <estimate> <tr_ids> <adrs> <ac> <qa_cases>
        <test_evidence> <depends_on> <sprint_status>
  LINT <path> <rule> <detail>
  NOT_FOUND <path>
State is story-status's grouping: COMPLETE, IN_REVIEW, IN_PROGRESS, TODO, BLOCKED, OTHER, NO_STATUS.
"-" means not there; UNFILLED means still the template's [bracket].
LINT rules: no_status, type_missing, type_unknown <value>, unfilled <field>, no_tr_id, no_ac_section,
  ac_below_min <count> < <minimum> (<type>), marker <TBD|TODO|UNRESOLVED> line <n>
AC minimums: coarse Logic 3, Integration 3, Visual/Feel 2, UI 2, Config/Data 1;
  balanced Logic 2, Integration 2, Visual/Feel 2, UI 2, Config/Data 1; fine 1 for every type.
Exit codes: 0 done; 1 root unreadable; 2 usage error; 3 --sprint with no sprint-status.yaml or a
missing file (its NOT_FOUND row is printed). Reads only."""

TYPES = ["Logic", "Integration", "Visual/Feel", "UI", "Config/Data"]
FIELDS = ["Type", "Layer", "Estimate", "Epic", "Manifest Version"]


def _fnorm(s):
    s = re.sub(r"^[ \t]+", "", s)
    s = re.sub(r"^> ", "", s)
    s = re.sub(r"^- ", "", s)
    return s.replace("*", "")


def _fval(s, name):
    t = _fnorm(s)
    if t[: len(name) + 1].lower() != name.lower() + ":":
        return None
    return t[len(name) + 1:].strip()


def _clean(s):
    s = (s or "").replace("\t", " ").strip()
    return s or "-"


def _bracketed(v):
    return v[:1] == "["


def _ids(existing, s, pat):
    out = list(existing)
    for m in re.finditer(pat, s):
        if m.group(0) not in out:
            out.append(m.group(0))
    return out


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


def _sprint_entries(text):
    out, in_s, f, st = [], False, "", ""

    def val(s):
        s = re.sub(r"^[^:]*:[ \t]*", "", s)
        if s[:1] in ('"', "'"):
            e = s.find(s[0], 1)
            return s[1:e] if e > 0 else s[1:]
        return re.sub(r"[ \t]+#.*$", "", s).strip()

    def emit():
        nonlocal f, st
        if f:
            out.append((f, st or "-"))
        f, st = "", ""

    for line in text.replace("\r", "").split("\n"):
        if line.startswith("stories:"):
            in_s = True
            continue
        if re.match(r"^[^ \t#-]", line):
            if in_s:
                emit()
            in_s = False
        if in_s and re.match(r"^[ \t]*- ", line):
            emit()
        if in_s and re.match(r"^[ \t]*(- )?file:", line):
            f = val(line)
        if in_s and re.match(r"^[ \t]*(- )?status:", line):
            st = val(line)
    if in_s:
        emit()
    return out


def facts(root, rel, gran, lint, ystat):
    """Return (state, row, lints) for one story file."""
    text = _util.read(os.path.join(root, rel))
    acmin = {"logic": 3, "integration": 3, "visual/feel": 2, "ui": 2, "config/data": 1}
    if gran == "balanced":
        acmin["logic"] = acmin["integration"] = 2
    if gran == "fine":
        acmin = dict.fromkeys(acmin, 1)
    status, has_status = "", False
    vals = {}
    seen = set()
    unf = []
    trs, adr_line = [], ""
    ac = qa = 0
    has_ac = has_qa = False
    te = dep = ""
    marks = []
    infence = ""
    incomment = False
    sec = ""
    for fnr, raw in enumerate(text.split("\n"), 1):
        line = raw
        if not has_status:
            v = _fval(line, "Status")
            if v is not None and _fnorm(line)[:7] == "Status:":
                status, has_status = v, True
        if infence:
            m = re.match(r" {0,3}(" + re.escape(infence[0]) + r"+)\s*$", line)
            if m and len(m.group(1)) >= len(infence):
                infence = ""
            continue
        m = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if m:
            infence = m.group(1)
            continue
        cstart = incomment
        rest, s = "", line
        while s:
            if incomment:
                p = s.find("-->")
                if p < 0:
                    s = ""
                    break
                s = s[p + 3:]
                incomment = False
                continue
            p = s.find("<!--")
            bq = s.find("`")
            if bq >= 0 and (p < 0 or bq < p):
                bk = 0
                while bq + bk < len(s) and s[bq + bk] == "`":
                    bk += 1
                be = _span_end(s[bq + bk:], bk)
                bn = bq + bk + be - 1 + bk if be > 0 else bq + bk
                rest += s[:bn]
                s = s[bn:]
                continue
            if p < 0:
                rest += s
                s = ""
                break
            rest += s[:p]
            s = s[p + 4:]
            incomment = True
        hm = re.match(r" {0,3}(#+)[ \t]", line)
        if not cstart and hm and len(hm.group(1)) <= 6:
            k = len(hm.group(1))
            if k <= 2:
                t = line.lstrip(" ")[k:].lower().strip(" \t#")
                sec = t if k == 2 else ""
            continue
        r = rest.strip()
        if not r:
            continue
        for nm in FIELDS:
            if nm not in seen:
                v = _fval(r, nm)
                if v is not None:
                    seen.add(nm)
                    vals[nm] = v
                    if _bracketed(v):
                        unf.append(nm)
        if not adr_line:
            for key in ("ADR Governing Implementation", "Governing ADRs", "ADR"):
                v = _fval(r, key)
                if v is not None:
                    adr_line = v or "-"
                    break
        trs = _ids(trs, r, r"TR-[A-Za-z0-9][A-Za-z0-9-]*-[0-9]+")
        if sec == "acceptance criteria":
            has_ac = True
            if re.match(r"^[-*] \[[ xX]\]", r):
                ac += 1
        if sec == "qa test cases":
            has_qa = True
            if re.match(r"^[-*] \*\*AC-[0-9]+\*\*", r):
                qa += 1
        if sec == "test evidence" and not te:
            v = _fval(r, "Status")
            if v is not None:
                te = v
        if sec == "dependencies" and not dep:
            v = _fval(r, "Depends on")
            if v is not None:
                dep = v
        padded = " " + r + " "
        for mm in re.finditer(r"(?<![A-Za-z0-9_])(TBD|TODO|UNRESOLVED)(?![A-Za-z0-9_])", padded):
            marks.append("%s line %d" % (mm.group(1), fnr))
    s = status.lower()
    if not has_status:
        state = "NO_STATUS"
    elif _util.is_done(status):
        state = "COMPLETE"
    elif re.match(r"^in progress([^a-z]|$)", s):
        state = "IN_PROGRESS"
    elif re.match(r"^in review([^a-z]|$)", s):
        state = "IN_REVIEW"
    elif re.match(r"^(ready|not started)([^a-z]|$)", s):
        state = "TODO"
    elif re.match(r"^blocked([^a-z]|$)", s):
        state = "BLOCKED"
    else:
        state = "OTHER"
    typ = vals.get("Type", "")
    layer = vals.get("Layer", "")
    est = vals.get("Estimate", "")
    t = "-" if not typ else ("UNFILLED" if _bracketed(typ) else typ)
    adrv = "-"
    if adr_line:
        ids = _ids([], adr_line.lower(), r"adr-[0-9]+")
        adrv = ",".join(ids) if ids else ("n/a" if "n/a" in adr_line.lower() else ("UNFILLED" if _bracketed(adr_line) else "-"))
    row = "STORY\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
        rel, state, _clean(status), t, _clean("UNFILLED" if _bracketed(layer) else layer),
        _clean("UNFILLED" if _bracketed(est) else est), ",".join(trs) or "-", adrv,
        ac if has_ac else "-", qa if has_qa else "-", _clean(te), _clean(dep), ystat.get(rel, "-"))
    lints = []
    if lint:
        if not has_status:
            lints.append(("no_status", "-"))
        if not typ:
            lints.append(("type_missing", "-"))
        elif not _bracketed(typ):
            known = [x for x in TYPES if x.lower() == typ.lower()]
            if not known:
                lints.append(("type_unknown", _clean(typ)))
            elif has_ac and ac < acmin[known[0].lower()]:
                lints.append(("ac_below_min", "%d < %d (%s)" % (ac, acmin[known[0].lower()], typ)))
        for u in unf:
            lints.append(("unfilled", u))
        if not trs:
            lints.append(("no_tr_id", "-"))
        if not has_ac:
            lints.append(("no_ac_section", "-"))
        for m in marks:
            lints.append(("marker", m))
    return state, row, ["LINT\t%s\t%s\t%s" % (rel, a, b) for a, b in lints]


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    scope, lint, gran, paths = "all", False, "coarse", []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a == "--all":
            scope = "all"
        elif a == "--sprint":
            scope = "sprint"
        elif a == "--lint":
            lint = True
        elif a == "--granularity" and i + 1 < len(rest):
            gran = rest[i + 1]
            i += 1
        elif a.startswith("--granularity="):
            gran = a.split("=", 1)[1]
        elif a.startswith("-") and len(a) > 1:
            return _util.usage_error("story-facts", "unknown argument: " + a)
        else:
            paths.append(a)
            scope = "paths"
        i += 1
    if gran not in ("coarse", "balanced", "fine"):
        sys.stderr.write("story-facts: --granularity takes coarse, balanced or fine, not: %s\n" % gran)
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("story-facts: cannot read root %s\n" % root)
        return 1
    ystat = {}
    yaml_rel = "production/sprint-status.yaml"
    if scope == "all":
        lst = []
        base = os.path.join(root, "production", "epics")
        for dp, dn, fn in os.walk(base):
            dn.sort()
            lst += [os.path.relpath(os.path.join(dp, n), root).replace(os.sep, "/") for n in sorted(fn)
                    if re.match(r"^story-.*\.md$", n)]
        lst.sort()
        label = "production/epics/**/story-*.md"
    elif scope == "sprint":
        ypath = os.path.join(root, yaml_rel)
        if not os.path.isfile(ypath):
            sys.stderr.write("story-facts: no %s; --sprint has no story paths to read (try --all)\n" % yaml_rel)
            return 3
        ent = _sprint_entries(_util.read(ypath))
        ystat = {f.lstrip("./") if f.startswith("./") else f: s for f, s in ent}
        lst = [f[2:] if f.startswith("./") else f for f, _ in ent]
        label = yaml_rel
    else:
        lst = [p[2:] if p.startswith("./") else p for p in paths]
        label = "paths"
    files, missed = [], []
    for f in lst:
        (files if os.path.isfile(os.path.join(root, f)) else missed).append(f)
    cnt = dict.fromkeys(["COMPLETE", "IN_REVIEW", "IN_PROGRESS", "TODO", "BLOCKED", "OTHER", "NO_STATUS"], 0)
    rows, lints = [], []
    for f in files:
        state, row, lr = facts(root, f, gran, lint, ystat)
        cnt[state] += 1
        rows.append(row)
        lints.extend(lr)
    print("stories\t%d\t%s" % (len(rows), label))
    for k, v in cnt.items():
        print("%s\t%d" % (k.lower(), v))
    if lint:
        print("lint\t%d" % len(lints))
    for x in rows + lints:
        print(x)
    for m in missed:
        print("NOT_FOUND\t" + m)
    return 3 if missed else 0
