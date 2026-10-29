"""The technical-debt register's arithmetic: next TD ID, scores, stats, and matching entries."""
import datetime
import os
import re
import sys

from . import _util

HELP = """Usage: python tools/studio.py debt-register [--root DIR] COMMAND [ARGS]
The technical-debt register's arithmetic: the next TD ID, the impact / effort score, open items per
category, items added and resolved in a window, item ages, and the Open entries that already cover a file
and a category, read from docs/tech-debt-register.md. Observations, not a verdict.
  next-id                 the next TD ID: the registry module's `next-id td`, unchanged
  score IMPACT EFFORT     the score of one pair: Low, Med (Medium), High or Critical over S, M, L or XL, any
                          case; - or an em dash means not judged and gives no score
  score                   every item of the register scored from its own columns, in the order /tech-debt
                          prioritize writes
  stats [--today D] [--since D] [--until D] [--older-than N]
                          open items per category, added and resolved in the window --since..--until (both
                          days included; --until defaults to --today), and the age of each open item
  match --file PATH [--category CAT]
                          the Open entries whose Files list PATH, and whose category is CAT when given
  --register PATH         the register, relative to the root or absolute (default
                          docs/tech-debt-register.md); not for next-id
  --today D               the date ages count to (default: today)
Dates are YYYY-MM-DD.
Reads the Markdown table whose header row starts with ID; columns are found by header name (ID, Category,
Description, Files, Effort, Impact, Priority, Status, Added, Sprint); a missing column reads as -. A row
starting TD-n whose cell count is not the header's is MALFORMED and left out. A \\| inside a cell is a pipe.
Status: Open, Resolved YYYY-MM-DD, Accepted - reason (anything else is other_status).
Score: impact / effort, Impact Low 1, Med 2, High 3, Critical 4; Effort S 1, M 2, L 3, XL 4, rounded to one
decimal with a half rounding UP: tenths = floor((20 * impact + effort) / (2 * effort)).
Output: TSV. Every register command starts: register <path> <items>, columns, items, duplicate_ids, malformed,
then MALFORMED and DUPLICATE_ID rows. score: `score <value | -> <Impact>/<Effort> <i/e | reason>`; register
mode: scored, not_scored, open_ranked, then ROW rows. stats: open, resolved, accepted, other_status, today,
window, added_in_window, resolved_in_window, net_in_window, undated, older_than, category rows, effort_open,
OPEN rows. match: matches <n> file=<path> category=<cat|any>, MATCH rows. `-` means not there.
Exit codes: 0 answered; 1 the root cannot be read, or the registry module failed to import; 2 usage error;
3 no register file. next-id passes the registry module's own codes through. Reads only."""

SIX = ["Architecture", "Code Quality", "Test", "Documentation", "Dependency", "Performance"]
DASHES = ("", "-", "--", "\u2014", "\u2013")
IMPACT = {"low": 1, "med": 2, "medium": 2, "high": 3, "critical": 4}
IMPACT_NAME = {1: "Low", 2: "Med", 3: "High", 4: "Critical"}
EFFORT = {"s": 1, "m": 2, "l": 3, "xl": 4}
EFFORT_NAME = {1: "S", 2: "M", 3: "L", 4: "XL"}


class Usage(Exception):
    pass


def isdash(s):
    return s in DASHES


def v(s):
    s = s.replace("\t", " ")
    return "-" if isdash(s) else s


def score10(i, e):
    return (20 * i + e) // (2 * e)


def fmt10(t):
    return "%d.%d" % (t // 10, t % 10)


def canon_cat(s):
    low = s.strip().lower()
    low = re.sub(r" debt$", "", low)
    for name in SIX:
        if low == name.lower():
            return name
    s = s.strip()
    return s or "-"


def firstdate(s):
    m = re.search(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", s)
    return m.group(0) if m else ""


def normpath(s):
    s = s.replace("`", "").strip()
    return s[2:] if s.startswith("./") else s


def to_date(s):
    return datetime.date.fromisoformat(s)


def is_date(s):
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", s))


def read_register(text):
    KEYS = ["id", "category", "description", "files", "effort", "impact", "priority", "status", "added", "sprint"]
    NAMES = ["ID", "Category", "Description", "Files", "Effort", "Impact", "Priority", "Status", "Added", "Sprint"]
    name_of = dict(zip(KEYS, NAMES))
    ci, ncol, hdr, colslist = {}, 0, False, []
    items, malformed, idc, idl, dupo = [], [], {}, {}, []
    for fnr, line in enumerate(text.split("\n"), 1):
        if fnr == 1 and line.startswith("\ufeff"):
            line = line[1:]
        if not re.match(r"^[ \t]*\|", line):
            continue
        t = line.replace("\\|", "\x01")
        t = re.sub(r"^[ \t]*\|", "", t)
        t = re.sub(r"\|[ \t]*$", "", t)
        c = [x.strip().replace("\x01", "|") for x in t.split("|")]
        if all(re.match(r"^:?-+:?$", x) for x in c):
            continue
        if c[0].lower() == "id":
            ncol, hdr = len(c), True
            ci, colslist = {}, []
            for i, h in enumerate(c):
                if h.lower() in name_of:
                    ci[h.lower()] = i
                    colslist.append(name_of[h.lower()])
            continue
        if not re.match(r"^TD-[0-9]+$", c[0]):
            continue
        if not hdr:
            ncol, hdr = 10, True
            ci = {k: i for i, k in enumerate(KEYS)}
            colslist = list(NAMES)
        if len(c) != ncol:
            malformed.append("%d\t%d\t%d\t%s" % (fnr, len(c), ncol, c[0]))
            continue

        def get(k):
            return c[ci[k]] if k in ci else ""
        it = {"id": c[0], "ln": fnr, "cat": canon_cat(get("category")), "eff": get("effort"), "imp": get("impact"),
              "pri": get("priority"), "sta": get("status"), "add": get("added"), "spr": get("sprint"), "fil": get("files")}
        low = it["sta"].lower()
        it["st"] = ("OPEN" if re.match(r"^open([^a-z]|$)", low) else "RESOLVED" if re.match(r"^resolved([^a-z]|$)", low)
                    else "ACCEPTED" if re.match(r"^accepted([^a-z]|$)", low) else "OTHER")
        it["ad"] = firstdate(it["add"])
        it["rd"] = firstdate(it["sta"]) if it["st"] == "RESOLVED" else ""
        items.append(it)
        idc[c[0]] = idc.get(c[0], 0) + 1
        idl[c[0]] = idl.get(c[0], "") + ("," if c[0] in idl else "") + str(fnr)
        if idc[c[0]] == 2:
            dupo.append(c[0])
    return items, colslist, malformed, dupo, idl


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    cmd, reg, reg_set, today_s, since, until, older, filearg, catarg, pos = "", "docs/tech-debt-register.md", False, "", "", "", "", "", "", []
    try:
        i = 0
        while i < len(rest):
            a = rest[i]
            if a in ("-h", "--help"):
                print(HELP)
                return 0
            m = re.match(r"^(--[a-z-]+)=(.*)$", a)
            if m and m.group(1) in ("--today",):
                today_s = m.group(2)
                i += 1
                continue
            if a in ("--register", "--today", "--since", "--until", "--older-than", "--file", "--category"):
                if i + 1 >= len(rest):
                    raise Usage("%s needs a value" % a)
                val = rest[i + 1]
                if a == "--register":
                    reg, reg_set = val, True
                elif a == "--today":
                    today_s = val
                elif a == "--since":
                    since = val
                elif a == "--until":
                    until = val
                elif a == "--older-than":
                    older = val
                elif a == "--file":
                    filearg = val
                else:
                    catarg = val
                i += 2
                continue
            if a.startswith("-") and len(a) > 1:
                raise Usage("unknown argument: %s" % a)
            if not cmd:
                cmd = a
            else:
                pos.append(a)
            i += 1
        if cmd == "next-id":
            if pos:
                raise Usage("next-id takes no arguments")
            if reg_set:
                raise Usage("next-id reads the register the registry module knows; --register does not apply")
        elif cmd == "score":
            if len(pos) not in (0, 2):
                raise Usage("score takes IMPACT and EFFORT, or nothing")
        elif cmd in ("stats", "match"):
            if pos:
                raise Usage("%s takes no arguments" % cmd)
        else:
            raise Usage("no command" if not cmd else "unknown command: " + cmd)
        today_d = datetime.date.today().isoformat() if not today_s else today_s
        if not is_date(today_d):
            raise Usage("--today must be YYYY-MM-DD, got %s" % today_d)
        if since or until:
            if cmd != "stats":
                raise Usage("--since and --until belong to stats")
            if not since:
                raise Usage("--until needs --since")
            if not is_date(since):
                raise Usage("--since must be YYYY-MM-DD, got %s" % since)
            until = until or today_d
            if not is_date(until):
                raise Usage("--until must be YYYY-MM-DD, got %s" % until)
            if since > until:
                raise Usage("--since %s is after --until %s" % (since, until))
        if older:
            if cmd != "stats":
                raise Usage("--older-than belongs to stats")
            if not re.match(r"^[0-9]+$", older):
                raise Usage("--older-than takes a whole number of days")
        if cmd == "match":
            if not filearg:
                raise Usage("match needs --file")
        elif filearg or catarg:
            raise Usage("--file and --category belong to match")
        if cmd == "score" and len(pos) == 2:
            return score_pair(pos[0], pos[1])
    except Usage as e:
        sys.stderr.write("debt-register: %s (try --help)\n" % e)
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("debt-register: cannot read root %s\n" % root)
        return 1
    if cmd == "next-id":
        try:
            from . import registry
        except ImportError:
            sys.stderr.write("debt-register: the registry module failed to import\n")
            return 1
        registry.next_id(root, "td", "")
        return 0
    path = reg if os.path.isabs(reg) else os.path.join(root, reg)
    if not os.path.isfile(path):
        print("register\t%s\tmissing" % reg)
        sys.stderr.write("debt-register: no register at %s\n" % reg)
        return 3
    items, cols, malformed, dupo, idl = read_register(_util.read(path))
    if cmd != "match" or True:
        print("register\t%s\t%d" % (reg, len(items)))
    if cmd != "match":
        print("columns\t%s" % (",".join(cols) if cols else "-"))
        print("items\t%d\nduplicate_ids\t%d\nmalformed\t%d" % (len(items), len(dupo), len(malformed)))
        for m in malformed:
            print("MALFORMED\t" + m)
        for d in dupo:
            print("DUPLICATE_ID\t%s\t%s" % (d, idl[d]))
    if cmd == "score":
        return score_all(items)
    if cmd == "stats":
        return stats(items, today_d, since, until, older)
    return match(items, filearg, catarg)


def score_pair(p1, p2):
    ij, ej, iname, ename, inn, en = 1, 1, "-", "-", 0, 0
    if isdash(p1):
        ij = 0
    else:
        inn = IMPACT.get(p1.lower(), 0)
        if not inn:
            raise Usage("not an impact (Low, Med, High, Critical): %s" % p1)
        iname = IMPACT_NAME[inn]
    if isdash(p2):
        ej = 0
    else:
        en = EFFORT.get(p2.lower(), 0)
        if not en:
            raise Usage("not an effort (S, M, L, XL): %s" % p2)
        ename = EFFORT_NAME[en]
    if ij and ej:
        print("score\t%s\t%s/%s\t%d/%d" % (fmt10(score10(inn, en)), iname, ename, inn, en))
    elif not ij and not ej:
        print("score\t-\t%s/%s\timpact and effort not judged" % (iname, ename))
    elif not ij:
        print("score\t-\t%s/%s\timpact not judged" % (iname, ename))
    else:
        print("score\t-\t%s/%s\teffort not judged" % (iname, ename))
    return 0


def score_all(items):
    for k, it in enumerate(items):
        ij = 0 if isdash(it["imp"]) else 1
        ej = 0 if isdash(it["eff"]) else 1
        inn = IMPACT.get(it["imp"].lower(), 0) if ij else 0
        en = EFFORT.get(it["eff"].lower(), 0) if ej else 0
        rs = ""
        if not ij and not ej:
            rs = "impact and effort not judged"
        else:
            if not ij:
                rs = "impact not judged"
            elif inn == 0:
                rs = "impact unrecognised: " + v(it["imp"])
            if not ej:
                rs += ("; " if rs else "") + "effort not judged"
            elif en == 0:
                rs += ("; " if rs else "") + "effort unrecognised: " + v(it["eff"])
        it["reason"] = rs or "-"
        it["sc"] = score10(inn, en) if not rs else -1
        it["iname"] = (IMPACT_NAME[inn] if inn else v(it["imp"])) if ij else "-"
        it["ename"] = (EFFORT_NAME[en] if en else v(it["eff"])) if ej else "-"
        it["idx"] = k

    def key(it):
        scored = it["sc"] >= 0
        return (0 if scored else 1, -it["sc"] if scored else 0, (it["ad"] or "9999-99-99") if scored else "", it["idx"])
    srt = sorted(items, key=key)
    rank, n = {}, 0
    for it in srt:
        if it["st"] == "OPEN" and it["sc"] >= 0:
            n += 1
            rank[it["idx"]] = n
    nscored = sum(1 for it in items if it["sc"] >= 0)
    print("scored\t%d\nnot_scored\t%d\nopen_ranked\t%d" % (nscored, len(items) - nscored, n))
    for it in srt:
        print("ROW\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
            rank.get(it["idx"], "-"), it["id"], fmt10(it["sc"]) if it["sc"] >= 0 else "-", it["iname"], it["ename"],
            v(it["pri"]), it["ad"] or v(it["add"]), it["st"], it["reason"]))
    return 0


def stats(items, today, since, until, older):
    cnt = {"OPEN": 0, "RESOLVED": 0, "ACCEPTED": 0, "OTHER": 0}
    undadd = undres = nadd = nresw = 0
    for it in items:
        cnt[it["st"]] += 1
        if not it["ad"]:
            undadd += 1
        if it["st"] == "RESOLVED" and not it["rd"]:
            undres += 1
        if since:
            if it["ad"] and since <= it["ad"] <= until:
                nadd += 1
            if it["rd"] and since <= it["rd"] <= until:
                nresw += 1
    print("open\t%d\nresolved\t%d\naccepted\t%d\nother_status\t%d\ntoday\t%s" % (cnt["OPEN"], cnt["RESOLVED"], cnt["ACCEPTED"], cnt["OTHER"], today))
    if since:
        print("window\t%s\t%s\nadded_in_window\t%d\nresolved_in_window\t%d\nnet_in_window\t%d" % (since, until, nadd, nresw, nadd - nresw))
    else:
        print("window\t-\t-\nadded_in_window\t-\nresolved_in_window\t-\nnet_in_window\t-")
    print("undated\t%d\t%d" % (undadd, undres))
    td = to_date(today)
    nold = 0
    for it in items:
        it["age"] = (td - to_date(it["ad"])).days if it["ad"] else "-"
        it["old"] = ("yes" if it["age"] > int(older) else "no") if older and it["age"] != "-" else "-"
        if it["old"] == "yes" and it["st"] == "OPEN":
            nold += 1
    print("older_than\t%s\t%d" % (older, nold) if older else "older_than\t-\t-")
    extra = sorted({it["cat"] for it in items if it["cat"] not in SIX})
    names = SIX + extra
    bk = ["S", "M", "L", "XL", "none", "other"]
    co, cb, tb = {}, {}, {}
    for it in items:
        if it["st"] != "OPEN":
            continue
        co[it["cat"]] = co.get(it["cat"], 0) + 1
        e = 0 if isdash(it["eff"]) else EFFORT.get(it["eff"].lower(), 0)
        b = EFFORT_NAME[e] if e else ("none" if isdash(it["eff"]) else "other")
        cb[(it["cat"], b)] = cb.get((it["cat"], b), 0) + 1
        tb[b] = tb.get(b, 0) + 1
    for n in names:
        print("category\t%s\t%d\t%s" % (n, co.get(n, 0), "\t".join(str(cb.get((n, b), 0)) for b in bk)))
    print("effort_open\t" + "\t".join(str(tb.get(b, 0)) for b in bk))
    for it in items:
        if it["st"] != "OPEN":
            continue
        e = 0 if isdash(it["eff"]) else EFFORT.get(it["eff"].lower(), 0)
        ii = 0 if isdash(it["imp"]) else IMPACT.get(it["imp"].lower(), 0)
        print("OPEN\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s" % (
            it["id"], it["cat"], EFFORT_NAME[e] if e else v(it["eff"]), IMPACT_NAME[ii] if ii else v(it["imp"]), v(it["pri"]),
            it["ad"] or v(it["add"]), it["age"], v(it["spr"]), it["old"]))
    return 0


def match(items, filearg, catarg):
    want = normpath(filearg)
    wc = canon_cat(catarg) if catarg else ""
    rows = []
    for it in items:
        if it["st"] != "OPEN":
            continue
        if wc and it["cat"] != wc:
            continue
        if any(normpath(p) == want for p in it["fil"].split(",")):
            rows.append("MATCH\t%s\t%d\t%s\t%s\t%s" % (it["id"], it["ln"], it["cat"], v(it["sta"]), v(it["fil"])))
    print("matches\t%d\tfile=%s category=%s" % (len(rows), want, wc or "any"))
    for r in rows:
        print(r)
    return 0
