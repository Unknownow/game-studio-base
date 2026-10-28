"""Each ADR's status, layer, dates, dependencies and missing sections, in one pass."""
import os
import re
import sys

HELP = """Usage: python tools/studio.py adr-status [--root DIR] [ID|PATH ...]
  ID          ADR-0003, adr-0003 or 0003: the ADR whose file name carries it
  PATH        an ADR file, relative to the root or absolute
  (none)      every docs/architecture/adr-*.md
Output: TSV. Counts first, then one row per ADR:
  adrs <n> <scope>, template_sections <n> <template path>, then the number of ADRs in each
  status: accepted, proposed, deprecated, superseded, unfilled, other, no_status
  ADR <id> <path> <status> <layer> <date> <last_verified> <version> <depends_on>
      <superseded_by> <missing> <unfilled>
  NOT_FOUND <ID or PATH>          for an argument that names no ADR
Columns ("-" means not there): status is Accepted | Proposed | Deprecated | Superseded (the first
word under `## Status`), UNFILLED while it is the template's [bracket], OTHER for anything else;
layer is the `**Layer**` row's value; date and last_verified are the first YYYY-MM-DD under
`## Date` and `## Last Verified`; version is last_verified, else date, else `unversioned`;
depends_on lists every ADR-N on the `**Depends On**` row as adr-NNNN (`none` when empty);
missing lists the template's `##` sections the ADR lacks; unfilled counts lines that are still
a [bracketed] line of the template.
Exit codes: 0 done; 1 root unreadable; 2 usage error; 3 an ID or PATH named no ADR."""

ADR_DIR = "docs/architecture"
TEMPLATE = "templates/architecture-decision-record.md"


def _norm(s):
    s = re.sub(r"\s+", " ", s.strip().lower())
    return re.sub(r"^[0-9]+[.)]? ", "", s)


def _adr_ids(s):
    out = []
    for m in re.finditer(r"adr-[0-9]+", s, re.I):
        i = m.group(0).lower()
        if i not in out:
            out.append(i)
    return out


def _first_date(s):
    m = re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s)
    return m.group(0) if m else ""


def _cell2(s):
    parts = s.split("|")
    return parts[2].strip() if len(parts) >= 3 else ""


def _scan(text):
    """Yield (kind, payload) in file order: ('h', (level, title)) or ('t', text-line)."""
    infence = ""
    incomment = False
    for raw in text.replace("\r\n", "\n").split("\n"):
        line = raw
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
            else:
                p = s.find("<!--")
                if p < 0:
                    rest += s
                    break
                rest += s[:p]
                s = s[p + 4:]
                incomment = True
        h = re.match(r" {0,3}(#{1,6})(?:[ \t]|$)(.*)$", line)
        if h and not cstart and not re.match(r"^[ \t]*<!--", line):
            t = h.group(2).strip()
            if re.search(r"(^| )#+$", t):
                t = re.sub(r"#+$", "", t).strip()
            yield "h", (len(h.group(1)), t)
            continue
        yield "t", rest.strip()


def _read(path):
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        return fh.read()


def _id_of(path):
    m = re.search(r"adr-[0-9]+", os.path.basename(path).lower())
    return m.group(0) if m else "-"


def main(root, argv):
    from . import _util
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    args = []
    for a in rest:
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a.startswith("-") and len(a) > 1:
            return _util.usage_error("adr-status", "unknown argument: " + a)
        args.append(a)
    if not os.path.isdir(root):
        sys.stderr.write("adr-status: cannot read root %s\n" % root)
        return 1
    adr_dir = os.path.join(root, ADR_DIR)
    allf = sorted(os.path.join(ADR_DIR, n) for n in os.listdir(adr_dir) if re.match(r"^adr-.*\.md$", n)) \
        if os.path.isdir(adr_dir) else []
    files, missed, scope = [], [], ADR_DIR + "/adr-*.md"
    if not args:
        files = allf
    else:
        scope = "arguments"
        for a in args:
            a = a.replace("\\", "/")
            cand = a if os.path.isabs(a) else os.path.join(root, a)
            if os.path.isfile(cand):
                rel = os.path.relpath(cand, root).replace(os.sep, "/") if not os.path.isabs(a) else a
                if not any(os.path.samefile(os.path.join(root, f) if not os.path.isabs(f) else f, cand) for f in files):
                    files.append(rel)
                continue
            want = re.sub(r"^adr-", "", a.lower())
            hit = None
            if want.isdigit():
                for f in allf:
                    n = _id_of(f)[4:]
                    if n.isdigit() and int(n) == int(want):
                        hit = f
                        break
            if hit:
                if hit not in files:
                    files.append(hit)
            else:
                missed.append(a)
    tpl_path = os.path.join(root, TEMPLATE)
    tsec, ttitle = [], []
    tbr = set()
    if os.path.isfile(tpl_path):
        for kind, p in _scan(_read(tpl_path)):
            if kind == "h":
                if p[0] == 2 and _norm(p[1]) not in tsec:
                    tsec.append(_norm(p[1]))
                    ttitle.append(p[1])
            elif "[" in p:
                tbr.add(p)
    cnt = dict.fromkeys(["accepted", "proposed", "deprecated", "superseded", "unfilled", "other", "no_status"], 0)
    rows = []
    for f in files:
        path = os.path.join(root, f) if not os.path.isabs(f) else f
        has, sec = set(), ""
        status_line = date_line = lv_line = ""
        dep_seen = layer_seen = False
        dep_cell = dep_row = layer_cell = ""
        unfilled = 0
        for kind, p in _scan(_read(path)):
            if kind == "h":
                lvl, title = p
                if lvl <= 2:
                    sec = _norm(title) if lvl == 2 else ""
                if lvl == 2:
                    has.add(_norm(title))
                continue
            if not p:
                continue
            if p in tbr:
                unfilled += 1
            if not p.startswith(">"):
                if sec == "status" and not status_line:
                    status_line = p
                if sec == "date" and not date_line:
                    date_line = p
                if sec == "last verified" and not lv_line:
                    lv_line = p
            if not layer_seen and re.match(r"^\|[ \t]*\*\*Layer\*\*[ \t]*\|", p):
                layer_seen, layer_cell = True, _cell2(p)
            if sec == "adr dependencies" and not dep_seen and "**Depends On**" in p:
                dep_seen, dep_row = True, p
                dep_cell = _cell2(p) or p
        st, sb = "-", "-"
        if status_line:
            w = re.sub(r"[*_`]", "", status_line).strip().lower()
            w = re.sub(r"[^a-z].*$", "", w)
            if w in ("accepted", "proposed", "deprecated"):
                st = w.capitalize()
            elif w == "superseded":
                st = "Superseded"
                ids = _adr_ids(status_line)
                sb = ids[0] if ids else "-"
            elif status_line.strip().startswith("["):
                st = "UNFILLED"
            else:
                st = "OTHER"
        elif "status" in has:
            st = "OTHER"
        cnt["no_status" if st == "-" else st.lower()] += 1
        d = ("UNFILLED" if "date" in has else "-") if not date_line else (_first_date(date_line) or "UNFILLED")
        lv = ("UNFILLED" if "last verified" in has else "-") if not lv_line else (_first_date(lv_line) or "UNFILLED")
        ver = lv if lv[:1].isdigit() else (d if d[:1].isdigit() else "unversioned")
        cid = _id_of(f)
        if dep_seen:
            dep = ",".join(i for i in _adr_ids(dep_row) if i != cid)
            if not dep:
                dep = "UNFILLED" if dep_cell.startswith("[") else "none"
        else:
            dep = "-"
        if layer_seen:
            lay = "UNFILLED" if layer_cell.startswith("[") else (layer_cell or "-")
        else:
            lay = "-"
        miss = ",".join(t for s, t in zip(tsec, ttitle) if s not in has)
        rows.append("ADR\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%d" % (
            cid, f.replace("\t", " "), st, lay.replace("\t", " "), d, lv, ver, dep, sb, miss or "-", unfilled))
    print("adrs\t%d\t%s" % (len(rows), scope))
    print("template_sections\t%d\t%s" % (len(tsec), TEMPLATE if os.path.isfile(tpl_path) else "-"))
    for k in ["accepted", "proposed", "deprecated", "superseded", "unfilled", "other", "no_status"]:
        print("%s\t%d" % (k, cnt[k]))
    for rw in rows:
        print(rw)
    for m in missed:
        print("NOT_FOUND\t" + m)
    return 3 if missed else 0
