"""The three registries read one way, and the next ID of every kind the skills number."""
import os
import re
import sys

from . import _registry as R
from . import _util

HELP = """Usage: python tools/studio.py registry [--root DIR] COMMAND [ARGS]
The three registries read one way: the entity registry (design/registry/entities.yaml), the TR-ID registry
(docs/architecture/tr-registry.yaml) and the architecture registry (docs/registry/architecture.yaml), and
the next ID of every kind the skills number. Observations, not a verdict.
  list [REGISTRY] [--system SLUG]   one row per entry; REGISTRY is entities, tr or architecture (all three
                      when left out); --system keeps the TR-IDs of one system slug
  get NAME ...        each entry named NAME: its row, then its lines as the file has them
  refs NAME|PATH      for a NAME, each path its entry names, and for a TR-ID each story or epic line under
                      production/epics/ that cites it; for a PATH (it holds a /), every entry that names it
  slice PATH          every entry that names PATH as its source, gdd or adr or in referenced_by
  validate            duplicate names, TR-IDs cited under production/epics/ that the registry lacks, paths that
                      do not exist, status values outside the allowed list, and unsupported layout
  compare REGISTRY OLD [NEW]   one registry before and after a change: each entry OLD has that NEW lacks
                      (registries are append-only), each status the change sets outside the allowed list,
                      and NEW's unsupported layout
  next-id KIND [SCOPE]  the next ID: the highest seen plus one. KIND and SCOPE:
                      tr SLUG   TR-SLUG-NNN       adr     ADR-NNNN        bug     BUG-NNNN
                      asset     ASSET-NNN         td      TD-NNN          story EPIC  story-NNN
                      sprint    sprint-NNN        season  SN
Layout read: a section is a key at column 0 holding a block list, or [] while empty; an entry starts
"- KEY: VALUE" (dash at column 0 or 2); its fields sit two columns past the dash; a value holding ": " is
quoted. Anything else is reported as LAYOUT and that registry's entries are left out.
Output: TSV, `-` where a value is not there.
  registry <name> <path> <entries | missing | layout>
  ENTRY <registry> <section> <key> <name> <status> <source> <line>
  REF <registry> <name> <how> <path> <line>
  LAYOUT <registry> <path> <found> <expected> <line>
  UNQUOTED <registry> <path> <value> <line as it should read> <line>
  NOT_FOUND <name>
  validate: checked production/epics <n>, duplicate, tr_unknown, path_missing, status, layout, then rows
  compare: removed, status, layout, then rows
  next-id: next <kind> <scope | -> <id> <highest | -> <ids seen>
Exit codes: 0 answered; 1 the root cannot be read; 2 usage error; 3 a NAME matched no entry; 4 a registry the
command reads has an unsupported layout. validate and compare exit 0 whenever they ran. Reads only."""

REGS = ["entities", "tr", "architecture"]
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class Usage(Exception):
    pass


def tsv(s):
    s = str(s).replace("\t", " ")
    return s if s else "-"


def load(root, name, path=None, shown=None):
    rel = path or R.REG_PATHS[name]
    full = rel if os.path.isabs(rel) else os.path.join(root, rel)
    reg = R.Registry(name, rel, shown or rel)
    if not os.path.isfile(full):
        reg.missing = True
        return reg
    return R.read_registry(reg, _util.read(full))


def entry_row(e):
    print("\t".join(["ENTRY", e.reg, tsv(e.section), tsv(e.key), tsv(e.name), tsv(e.status) if e.status_set else "-",
                     tsv(e.source), str(e.line)]))


def block(reg, e):
    entry_row(e)
    for i in range(e.line, e.end + 1):
        print(reg.raw.get(i, ""))


def layout_rows(regs):
    for reg in regs:
        for found, exp, ln in reg.layout:
            print("\t".join(["LAYOUT", reg.name, reg.shown, found, exp, str(ln)]))


def unquoted_rows(regs):
    for reg in regs:
        for v, ln in reg.unquoted:
            print("\t".join(["UNQUOTED", reg.name, reg.shown, tsv(v), 'status: "%s"' % tsv(v), str(ln)]))


def cited_ids(root):
    out, n = [], 0
    base = os.path.join(root, "production", "epics")
    if not os.path.isdir(base):
        return out, 0
    rx = re.compile(R.TRID)
    for dp, _, fn in sorted(os.walk(base)):
        for f in sorted(fn):
            if not f.endswith(".md"):
                continue
            n += 1
            rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/")
            for ln, line in enumerate(_util.read(os.path.join(dp, f)).split("\n"), 1):
                base_i = 0
                while True:
                    m = rx.search(line, base_i)
                    if not m:
                        break
                    pre = line[m.start() - 1] if m.start() > 0 else ""
                    aft = line[m.end()] if m.end() < len(line) else ""
                    if not re.match(r"[A-Za-z0-9-]", pre or " ") and not re.match(r"[A-Za-z0-9]", aft or " "):
                        out.append((m.group(0), rel, ln))
                    base_i = m.end()
    return out, n


def on_slug(id_, s):
    return bool(re.match("^TR-" + re.escape(s) + "-[0-9]+$", id_))


def next_seen(kind, scope, fmt, mode, pat, files, root):
    seen = set()
    mx = -1
    rx = re.compile(pat)
    for f in files:
        if mode == "names":
            m = rx.match(os.path.basename(f))
            if m:
                d = int(re.search(r"[0-9]+", m.group(0)).group(0))
                seen.add(d)
                mx = max(mx, d)
        else:
            for line in _util.read(os.path.join(root, f)).split("\n"):
                for m in rx.finditer(line):
                    pre = line[m.start() - 1] if m.start() > 0 else ""
                    aft = line[m.end()] if m.end() < len(line) else ""
                    if not re.match(r"[A-Za-z0-9-]", pre or " ") and not re.match(r"[A-Za-z0-9]", aft or " "):
                        d = int(re.search(r"[0-9]+", m.group(0)).group(0))
                        seen.add(d)
                        mx = max(mx, d)
    nxt = fmt % (mx + 1 if mx >= 0 else 1)
    print("next\t%s\t%s\t%s\t%s\t%d" % (kind, scope or "-", nxt, (fmt % mx) if mx >= 0 else "-", len(seen)))


def files_in(root, d, pat, ci=False):
    p = os.path.join(root, d)
    if not os.path.isdir(p):
        return []
    import fnmatch
    out = []
    for n in sorted(os.listdir(p)):
        if os.path.isfile(os.path.join(p, n)):
            ok = fnmatch.fnmatch(n.lower(), pat.lower()) if ci else fnmatch.fnmatchcase(n, pat)
            if ok:
                out.append(d + "/" + n)
    return out


def next_id(root, kind, scope):
    if kind == "adr":
        next_seen("adr", "", "ADR-%04d", "names", r"^adr-[0-9]+", files_in(root, "docs/architecture", "adr-*.md"), root)
    elif kind == "bug":
        next_seen("bug", "", "BUG-%04d", "names", r"^[Bb][Uu][Gg]-[0-9]+", files_in(root, "production/qa/bugs", "bug-*.md", True), root)
    elif kind == "asset":
        fl = (["design/assets/asset-manifest.md"] if os.path.isfile(os.path.join(root, "design/assets/asset-manifest.md")) else [])
        next_seen("asset", "", "ASSET-%03d", "text", r"ASSET-[0-9]+", fl + files_in(root, "design/assets/specs", "*.md"), root)
    elif kind == "td":
        fl = (["docs/tech-debt-register.md"] if os.path.isfile(os.path.join(root, "docs/tech-debt-register.md")) else [])
        next_seen("td", "", "TD-%03d", "text", r"TD-[0-9]+", fl, root)
    elif kind == "story":
        next_seen("story", scope, "story-%03d", "names", r"^story-[0-9]+", files_in(root, "production/epics/" + scope, "story-*.md"), root)
    elif kind == "sprint":
        next_seen("sprint", "", "sprint-%03d", "names", r"^sprint-[0-9]+\.md$", files_in(root, "production/sprints", "sprint-*.md"), root)
    elif kind == "season":
        next_seen("season", "", "S%d", "names", r"^S[0-9]+_", files_in(root, "design/live-ops/seasons", "S*_*"), root)


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    try:
        if not rest:
            raise Usage("no command")
        if rest[0] in ("-h", "--help"):
            print(HELP)
            return 0
        cmd, args = rest[0], rest[1:]
        read, reg_arg, sys_arg, names, arg = list(REGS), "", "", [], ""
        scan = False
        cmp_old = cmp_new = None
        kind = scope = ""
        if cmd == "list":
            i = 0
            while i < len(args):
                a = args[i]
                if a == "--system":
                    if i + 1 >= len(args):
                        raise Usage("--system needs a slug")
                    i += 1
                    sys_arg = args[i]
                    if not SLUG.match(sys_arg):
                        raise Usage("not a system slug: " + sys_arg)
                elif a in REGS:
                    if reg_arg:
                        raise Usage("one registry at most")
                    reg_arg = a
                else:
                    raise Usage("unknown argument to list: " + a)
                i += 1
            if sys_arg:
                if reg_arg and reg_arg != "tr":
                    raise Usage("--system reads the tr registry only")
                reg_arg = "tr"
            if reg_arg:
                read = [reg_arg]
        elif cmd == "get":
            if not args:
                raise Usage("get needs a name")
            names = args
        elif cmd == "refs":
            if len(args) != 1:
                raise Usage("refs takes one name or path")
            arg = args[0]
            if "/" in arg:
                arg = arg[2:] if arg.startswith("./") else arg
            else:
                scan = True
        elif cmd == "slice":
            if len(args) != 1:
                raise Usage("slice takes one path")
            arg = args[0][2:] if args[0].startswith("./") else args[0]
        elif cmd == "validate":
            if args:
                raise Usage("validate takes no arguments")
            scan = True
        elif cmd == "compare":
            if not 2 <= len(args) <= 3:
                raise Usage("compare takes a registry, the old file and optionally the new one")
            reg_arg = args[0]
            if reg_arg not in REGS:
                raise Usage("not a registry: " + reg_arg)
            cmp_old = (os.path.abspath(args[1]), args[1])
            cmp_new = (os.path.abspath(args[2]), args[2]) if len(args) == 3 else None
            if cmp_new and cmp_old[0] == cmp_new[0]:
                raise Usage("the old and new files are the same path")
            read = []
        elif cmd == "next-id":
            if not args:
                raise Usage("next-id needs a kind")
            kind = args[0]
            if kind in ("tr", "story"):
                if len(args) != 2:
                    raise Usage("next-id %s takes one slug" % kind)
                if not SLUG.match(args[1]):
                    raise Usage("not a slug: " + args[1])
                scope = args[1]
            elif kind in ("adr", "bug", "asset", "td", "sprint", "season"):
                if len(args) != 1:
                    raise Usage("next-id %s takes no scope" % kind)
            else:
                raise Usage("unknown ID kind: " + kind)
            read = ["tr"]
        else:
            raise Usage("unknown command: " + cmd)
    except Usage as e:
        sys.stderr.write("registry: %s (try --help)\n" % e)
        return 2
    if not os.path.isdir(root):
        sys.stderr.write("registry: cannot read root %s\n" % root)
        return 1
    if cmd == "next-id" and kind != "tr":
        next_id(root, kind, scope)
        return 0
    regs = [load(root, n) for n in read]
    if cmd == "compare":
        regs = [load(cmp_old[0], reg_arg, cmp_old[0], cmp_old[1])]
        if cmp_new:
            regs.append(load(cmp_new[0], reg_arg, cmp_new[0], cmp_new[1]))
        else:
            regs.append(load(root, reg_arg))
        for g in regs:
            g.path = g.shown
    cites, nscan = ([], 0)
    if scan:
        cites, nscan = cited_ids(root)
    entries = [(g, e) for g in regs for e in g.entries]
    ok = lambda g: not g.bad
    if cmd != "next-id":
        for g in regs:
            print("registry\t%s\t%s\t%s" % (g.name, g.shown, "missing" if g.missing else ("layout" if g.bad else len(g.entries))))
    rc = 0
    miss = []
    if cmd == "list":
        for g, e in entries:
            if ok(g) and (not sys_arg or on_slug(e.name, sys_arg)):
                entry_row(e)
    elif cmd == "get":
        for n in names:
            hit = False
            for g, e in entries:
                if ok(g) and e.name == n:
                    block(g, e)
                    hit = True
            if not hit:
                miss.append(n)
    elif cmd == "refs":
        if "/" in arg:
            for g, e in entries:
                if ok(g):
                    for how, p, ln in e.refs:
                        if p == arg:
                            print("REF\t%s\t%s\t%s\t%s\t%d" % (e.reg, tsv(e.name), how, p, ln))
        else:
            hit = False
            for g, e in entries:
                if ok(g) and e.name == arg:
                    hit = True
                    for how, p, ln in e.refs:
                        print("REF\t%s\t%s\t%s\t%s\t%d" % (e.reg, tsv(e.name), how, p, ln))
                    if e.reg == "tr":
                        for cid, f, ln in cites:
                            if cid == arg:
                                print("REF\ttr\t%s\tcited\t%s\t%d" % (arg, f, ln))
            if not hit:
                miss.append(arg)
    elif cmd == "slice":
        for g, e in entries:
            if ok(g) and any(p == arg for _, p, _ in e.refs):
                block(g, e)
    elif cmd == "validate":
        dups = {}
        order = []
        for g, e in entries:
            if not ok(g) or not e.name:
                continue
            k = (g.name, e.section, e.name)
            if k in dups:
                dups[k].append(e.line)
            else:
                dups[k] = [e.line]
                order.append(k)
        drows = ["DUPLICATE\t%s\t%s\t%s\t%s" % (k[0], k[1], tsv(k[2]), ",".join(str(x) for x in dups[k])) for k in order if len(dups[k]) > 1]
        trg = next((g for g in regs if g.name == "tr"), None)
        trows = []
        if not (trg and trg.bad):
            known = {e.name for g, e in entries if e.reg == "tr"}
            trows = ["TR_UNKNOWN\t%s\t%s\t%d" % (c, f, ln) for c, f, ln in cites if c not in known]
        prows = []
        for g, e in entries:
            if ok(g):
                for how, p, ln in e.refs:
                    if not os.path.exists(os.path.join(root, p)):
                        prows.append("PATH_MISSING\t%s\t%s\t%s\t%s\t%d" % (e.reg, tsv(e.name), how, p, ln))
        srows = []
        for g, e in entries:
            if ok(g) and e.status_set and not R.status_ok(e.reg, e.status):
                srows.append("STATUS\t%s\t%s\t%s\t%s\t%d" % (e.reg, tsv(e.name), e.status if e.status else '""', R.ALLOWED[e.reg], e.status_line))
        nlay = sum(len(g.layout) for g in regs)
        print("checked\tproduction/epics\t%d" % nscan)
        print("duplicate\t%d\ntr_unknown\t%d\npath_missing\t%d\nstatus\t%d\nlayout\t%d" % (len(drows), len(trows), len(prows), len(srows), nlay))
        for ln in drows + trows + prows + srows:
            print(ln)
        layout_rows(regs)
        unquoted_rows(regs)
        return 0
    elif cmd == "compare":
        old, new = regs[0], regs[1]
        newk = {(e.section, e.name) for e in new.entries}
        oldst = {}
        for e in old.entries:
            if e.status_set:
                oldst.setdefault((e.section, e.name), e.status)
        rrows = []
        if old.missing:
            removed = "0"
        elif new.missing or old.bad or new.bad:
            removed = "-"
        else:
            gone = set()
            for e in old.entries:
                k = (e.section, e.name)
                if e.name and k not in newk and k not in gone:
                    gone.add(k)
                    rrows.append("REMOVED\t%s\t%s\t%s\t%d" % (old.name, tsv(e.section), tsv(e.name), e.line))
            removed = str(len(rrows))
        srows = []
        if not new.bad:
            for e in new.entries:
                if e.status_set and not R.status_ok(new.name, e.status):
                    if oldst.get((e.section, e.name)) == e.status:
                        continue
                    srows.append("STATUS\t%s\t%s\t%s\t%s\t%d" % (new.name, tsv(e.name), e.status if e.status else '""', R.ALLOWED[new.name], e.status_line))
        print("removed\t%s\nstatus\t%d\nlayout\t%d" % (removed, len(srows), sum(len(g.layout) for g in regs)))
        for ln in rrows + srows:
            print(ln)
        layout_rows(regs)
        unquoted_rows(regs)
        return 0
    elif cmd == "next-id":
        if any(g.bad for g in regs):
            layout_rows(regs)
            sys.stderr.write("registry: unsupported layout; the LAYOUT rows give each line and the layout expected there\n")
            return 4
        mx, seen = -1, set()
        for g, e in entries:
            if on_slug(e.name, scope):
                d = int(e.name[len(scope) + 4:])
                seen.add(d)
                mx = max(mx, d)
        print("next\ttr\t%s\tTR-%s-%03d\t%s\t%d" % (scope, scope, mx + 1 if mx >= 0 else 1, ("TR-%s-%03d" % (scope, mx)) if mx >= 0 else "-", len(seen)))
        return 0
    if any(g.bad for g in regs):
        layout_rows(regs)
        rc = 4
    unquoted_rows(regs)
    for n in miss:
        print("NOT_FOUND\t%s" % n)
    if not rc and miss:
        rc = 3
    if rc == 4:
        sys.stderr.write("registry: unsupported layout; the LAYOUT rows give each line and the layout expected there\n")
    return rc
