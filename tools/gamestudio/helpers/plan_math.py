"""Date and percentage arithmetic for planning skills."""
import datetime
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from . import _util

HELP = """Usage: python tools/studio.py plan-math <command> [args] [--root DIR] [--today YYYY-MM-DD]
The date and percentage arithmetic planning skills do by hand.
  days START END          whole days from START to END (negative if END is earlier)
  pct PART WHOLE [--places N]
                          PART / WHOLE * 100, rounded half up to N places (default 0);
                          a WHOLE of 0 prints - and says so
  sprint N|latest         the production/sprints/ file for sprint N, written 3, 03, 003 or sprint-3;
                          latest is the highest number
  progress                the current sprint, from production/sprint-status.yaml
  --today D               the date "today" means (default: today's date)
Dates are YYYY-MM-DD and must exist (2026-02-29 is a bad date).
Output: TSV.
  days     days <n> <START>..<END>
  pct      pct <value> <PART>/<WHOLE>
  sprint   sprint <n> <path>
  progress sprint, start, end, today; days_total, days_elapsed, days_left; time_pct; stories, done, one
           status row per yaml status; done_pct; gap (time_pct - done_pct, in points); band <name> <rule>
           (On Track gap <= 10, At Risk 10 < gap <= 25, Behind gap > 25); must_have and must_have_done;
           time_left_pct; updated_days_ago. Percentages are whole numbers; a value that cannot be worked
           out is `-`. Observations, not a verdict.
Exit codes: 0 done; 1 the root cannot be read; 2 usage error (bad date or number, unknown command);
3 no such sprint file, or no sprint-status.yaml for progress; 4 two files hold the same sprint number.
Reads only."""


class Usage(Exception):
    pass


def parse_date(s):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return None
    try:
        return datetime.date(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except ValueError:
        return None


def is_num(s):
    return bool(re.match(r"^[0-9]*\.?[0-9]*$", s)) and s not in ("", ".")


def pct(part, whole, places):
    try:
        w = Decimal(whole)
        p = Decimal(part)
    except InvalidOperation:
        return "-"
    if w == 0:
        return "-"
    v = (p * 100 / w).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    return format(v, "f")


def _val(line):
    s = re.sub(r"^[^:]*:[ \t]*", "", line)
    if s[:1] in ('"', "'"):
        c = s[0]
        e = s[1:].find(c)
        return s[1:1 + e] if e >= 0 else s[1:]
    s = re.sub(r"[ \t]+#.*$", "", s)
    return s.rstrip()


def progress(root, today):
    path = os.path.join(root, "production", "sprint-status.yaml")
    if not os.path.isfile(path):
        sys.stderr.write("plan-math: no production/sprint-status.yaml\n")
        return 3
    sprint = start = end = upd = ""
    stories = []
    ins = False
    for ln in _util.read(path).split("\n"):
        if re.match(r"^sprint:", ln):
            sprint = _val(ln)
        elif re.match(r"^start:", ln):
            start = _val(ln)
        elif re.match(r"^end:", ln):
            end = _val(ln)
        elif re.match(r"^updated:", ln):
            upd = _val(ln)
        if re.match(r"^stories:", ln):
            ins = True
            continue
        if re.match(r"^[^ \t#-]", ln):
            ins = False
        if ins:
            if re.match(r"^[ \t]*- ", ln):
                stories.append({"status": "", "priority": ""})
            if re.match(r"^[ \t]*(?:- )?status:", ln) and stories:
                stories[-1]["status"] = _val(ln)
            if re.match(r"^[ \t]*(?:- )?priority:", ln) and stories:
                stories[-1]["priority"] = _val(ln)
    ds, de, du = parse_date(start), parse_date(end), parse_date(upd)
    row = _util.row
    row("sprint", sprint)
    row("start", start if ds else "")
    row("end", end if de else "")
    row("today", today.isoformat())
    total = elapsed = left = tp = "-"
    if ds and de:
        total = (de - ds).days
        elapsed = (today - ds).days
        left = (de - today).days
        tp = pct(str(elapsed), str(total), 0)
    row("days_total", total)
    row("days_elapsed", elapsed)
    row("days_left", left)
    row("time_pct", tp)
    names = ["backlog", "ready-for-dev", "in-progress", "review", "done", "blocked"]
    counts = {}
    mh = mhd = 0
    for s in stories:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
        if s["priority"] == "must-have":
            mh += 1
            if s["status"] == "done":
                mhd += 1
    ns = len(stories)
    row("stories", ns)
    row("done", counts.get("done", 0))
    for n in names:
        row("status", n, counts.get(n, 0))
    row("status", "other", ns - sum(counts.get(n, 0) for n in names))
    dp = pct(str(counts.get("done", 0)), str(ns), 0)
    row("done_pct", dp)
    if tp != "-" and dp != "-":
        gap = int(tp) - int(dp)
        row("gap", gap)
        if gap <= 10:
            row("band", "On Track", "gap <= 10")
        elif gap <= 25:
            row("band", "At Risk", "10 < gap <= 25")
        else:
            row("band", "Behind", "gap > 25")
    else:
        row("gap", "-")
        row("band", "-", "no dates or no stories")
    row("must_have", mh)
    row("must_have_done", mhd)
    row("time_left_pct", "-" if tp == "-" else 100 - int(tp))
    row("updated_days_ago", "-" if not du else (today - du).days)
    return 0


def _sprint(root, args):
    if len(args) != 1:
        raise Usage("sprint needs a number or latest")
    want = re.sub(r"^sprint-?", "", args[0].lower())
    if want != "latest" and not re.match(r"^[0-9]+$", want):
        raise Usage("sprint takes a number (3, 03, 003, sprint-3) or latest")
    d = os.path.join(root, "production", "sprints")
    found = {}
    if os.path.isdir(d):
        for n in sorted(os.listdir(d)):
            m = re.match(r"^sprint-([0-9]+)\.md$", n)
            if m and os.path.isfile(os.path.join(d, n)):
                found.setdefault(int(m.group(1)), []).append("production/sprints/" + n)
    if not found:
        sys.stderr.write("plan-math: no production/sprints/sprint-N.md files\n")
        return 3
    num = max(found) if want == "latest" else int(want)
    hits = found.get(num, [])
    if not hits:
        sys.stderr.write("plan-math: no sprint file for sprint %d\n" % num)
        return 3
    if len(hits) > 1:
        sys.stderr.write("plan-math: sprint %d has %d files: %s\n" % (num, len(hits), " ".join(hits)))
        return 4
    _util.row("sprint", num, hits[0])
    return 0


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    cmd, args, today_s, places = "", [], "", "0"
    i = 0
    try:
        while i < len(rest):
            a = rest[i]
            if a in ("-h", "--help"):
                print(HELP)
                return 0
            if a in ("--today", "--places"):
                if i + 1 >= len(rest):
                    raise Usage("%s needs a value" % a)
                if a == "--today":
                    today_s = rest[i + 1]
                else:
                    places = rest[i + 1]
                i += 2
                continue
            if a.startswith("--today="):
                today_s = a[8:]
            elif a.startswith("--places="):
                places = a[9:]
            elif a.startswith("-") and len(a) > 1 and not is_num(a[1:]):
                raise Usage("unknown argument: %s" % a)
            elif not cmd:
                cmd = a
            else:
                args.append(a)
            i += 1
        today = parse_date(today_s) if today_s else datetime.date.today()
        if today is None:
            raise Usage("--today must be a real YYYY-MM-DD date, got %s" % today_s)
        if not re.match(r"^[0-9]$", places):
            raise Usage("--places takes 0-9")
        if cmd == "days":
            if len(args) != 2:
                raise Usage("days needs START and END")
            a, b = parse_date(args[0]), parse_date(args[1])
            if not a or not b:
                raise Usage("dates are real YYYY-MM-DD dates")
            _util.row("days", (b - a).days, "%s..%s" % (args[0], args[1]))
            return 0
        if cmd == "pct":
            if len(args) != 2:
                raise Usage("pct needs PART and WHOLE")
            if not (is_num(args[0]) and is_num(args[1])):
                raise Usage("PART and WHOLE are numbers")
            v = pct(args[0], args[1], int(places))
            _util.row("pct", v, "zero denominator" if v == "-" else "%s/%s" % (args[0], args[1]))
            return 0
        if cmd not in ("sprint", "progress"):
            raise Usage("no command" if not cmd else "unknown command: %s" % cmd)
        if not os.path.isdir(root):
            sys.stderr.write("plan-math: cannot read root %s\n" % root)
            return 1
        if cmd == "progress":
            return progress(root, today)
        return _sprint(root, args)
    except Usage as e:
        sys.stderr.write("plan-math: %s (try --help)\n" % e)
        return 2
