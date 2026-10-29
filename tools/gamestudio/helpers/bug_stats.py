"""Bug counts by severity, status and system, with each bug's age."""
import datetime
import os
import re
import sys

from . import _util

HELP = """Usage: python tools/studio.py bug-stats [--root DIR] [--today YYYY-MM-DD] [DIR ...]
Bug counts by severity, status and system, with each bug's age, read from the bug files /bug-report writes.
Observations, not a verdict: every status is counted as written.
  DIR         folders to search for bug files at any depth, relative to the root or absolute;
              default production/qa/bugs/, one level
  --today D   the date ages count to (default: today)
A bug file is BUG-<number>.md (any case). It reads the header block as `**Field**:` lines: ID, Title,
Severity, Priority, Status, Reported, System. The FIRST Status line is the bug's status. Severity is the
first S1-S4 in its value, priority the first P1-P4; a value still in [brackets] is no severity.
Output: TSV. Counts first:
  bugs <n> <scope>
  open <n> <rule>        open = a status other than Closed or Verified Fixed (no Status line = open)
  closed <n>
  open_s1 .. open_s4 <n>, open_unrated <n>
  status <value as written> <n>     one row per status value, sorted
  system <system> <open> <open S1/S2>   open bugs per system, most first
  oldest_open <id> <days>
  BUG <id> <path> <severity> <priority> <state> <status> <reported> <age_days> <system> <title>
`-` means not there; state is OPEN or CLOSED.
Exit codes: 0 read every bug file found (none is fine); 1 the root cannot be read; 2 usage error. Reads only."""

BUG_RE = re.compile(r"^bug-[0-9].*\.md$", re.I)


def fval(line, name):
    u = line.lstrip(" \t")
    u = re.sub(r"^> ", "", u)
    u = re.sub(r"^- ", "", u)
    u = u.replace("*", "")
    if u[:len(name) + 1].lower() != (name + ":").lower():
        return None
    return u[len(name) + 1:].strip()


def clean(s):
    s = s.replace("\t", " ").strip()
    return s or "-"


def parse(text, path):
    vals = {}
    infence = False
    for line in text.split("\n"):
        if re.match(r"^[ \t]*(```|~~~)", line):
            infence = not infence
            continue
        if infence:
            continue
        for key in ("ID", "Title", "Severity", "Priority", "Status", "Reported", "System"):
            if key in vals:
                continue
            v = fval(line, key)
            if v is not None:
                vals[key] = v
    bug_id = os.path.splitext(os.path.basename(path))[0]
    m = re.match(r"^[A-Za-z]+-[0-9]+", vals.get("ID", ""))
    if m:
        bug_id = m.group(0).upper()
    return bug_id, vals


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    today_s, dirs = "", []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a == "--today":
            if i + 1 >= len(rest):
                sys.stderr.write("bug-stats: --today needs a date\n")
                return 2
            today_s = rest[i + 1]
            i += 2
            continue
        if a.startswith("--today="):
            today_s = a[8:]
        elif a.startswith("-") and len(a) > 1:
            sys.stderr.write("bug-stats: unknown argument: %s (try --help)\n" % a)
            return 2
        else:
            dirs.append(a)
        i += 1
    try:
        today = datetime.date.fromisoformat(today_s) if today_s else datetime.date.today()
        if today_s and not re.match(r"^\d{4}-\d{2}-\d{2}$", today_s):
            raise ValueError
    except ValueError:
        sys.stderr.write("bug-stats: --today must be YYYY-MM-DD, got %s\n" % today_s)
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("bug-stats: cannot read root %s\n" % root)
        return 1
    files = {}
    if not dirs:
        scope = "production/qa/bugs/BUG-*.md"
        d = os.path.join(root, "production", "qa", "bugs")
        if os.path.isdir(d):
            for n in os.listdir(d):
                if BUG_RE.match(n) and os.path.isfile(os.path.join(d, n)):
                    files["production/qa/bugs/" + n] = os.path.join(d, n)
    else:
        scope = ",".join(dirs)
        for dd in dirs:
            base = dd if os.path.isabs(dd) else os.path.join(root, dd)
            for dp, _, fn in os.walk(base.rstrip("/\\")):
                for n in fn:
                    if BUG_RE.match(n):
                        full = os.path.join(dp, n)
                        rel = os.path.relpath(full, root).replace(os.sep, "/") if not os.path.isabs(dd) else full.replace(os.sep, "/")
                        files[rel] = full
    bugs = []
    for rel in sorted(files):
        bid, v = parse(_util.read(files[rel]), rel)
        sev_v, pri_v = v.get("Severity", ""), v.get("Priority", "")
        m = None if sev_v.startswith("[") else re.search(r"[Ss][1-4]", sev_v)
        sev = m.group(0).upper() if m else "-"
        m = None if pri_v.startswith("[") else re.search(r"[Pp][1-4]", pri_v)
        pri = m.group(0).upper() if m else "-"
        stat = v.get("Status", "")
        sl = stat.lower()
        closed = bool(re.match(r"^closed([^a-z]|$)", sl) or re.match(r"^verified fixed([^a-z]|$)", sl))
        age, d = "-", "-"
        m = re.search(r"\d{4}-\d{2}-\d{2}", v.get("Reported", ""))
        if m:
            try:
                d = m.group(0)
                age = (today - datetime.date.fromisoformat(d)).days
            except ValueError:
                d, age = "-", "-"
        bugs.append({"id": bid, "path": rel, "sev": sev, "pri": pri, "closed": closed, "status": clean(stat) if stat else "-",
                     "reported": d, "age": age, "system": clean(v.get("System", "")), "title": clean(v.get("Title", ""))})
    nopen = [b for b in bugs if not b["closed"]]
    print("bugs\t%d\t%s" % (len(bugs), scope))
    print("open\t%d\tstatus other than Closed or Verified Fixed" % len(nopen))
    print("closed\t%d" % (len(bugs) - len(nopen)))
    for s in range(1, 5):
        print("open_s%d\t%d" % (s, sum(1 for b in nopen if b["sev"] == "S%d" % s)))
    print("open_unrated\t%d" % sum(1 for b in nopen if b["sev"] == "-"))
    stats = {}
    for b in bugs:
        stats[b["status"]] = stats.get(b["status"], 0) + 1
    for k in sorted(stats):
        print("status\t%s\t%d" % (k, stats[k]))
    sysopen, syshi = {}, {}
    for b in nopen:
        sysopen[b["system"]] = sysopen.get(b["system"], 0) + 1
        if b["sev"] in ("S1", "S2"):
            syshi[b["system"]] = syshi.get(b["system"], 0) + 1
    for k in sorted(sysopen, key=lambda x: (-sysopen[x], x)):
        print("system\t%s\t%d\t%d" % (k, sysopen[k], syshi.get(k, 0)))
    oldest = None
    for b in nopen:
        if b["age"] != "-" and (oldest is None or b["age"] > oldest["age"]):
            oldest = b
    if oldest:
        print("oldest_open\t%s\t%d" % (oldest["id"], oldest["age"]))
    else:
        print("oldest_open\t-\t-")
    for b in bugs:
        print("\t".join(str(x) for x in ("BUG", b["id"], b["path"], b["sev"], b["pri"], "CLOSED" if b["closed"] else "OPEN",
                                         b["status"], b["reported"], b["age"], b["system"], b["title"])))
    return 0
