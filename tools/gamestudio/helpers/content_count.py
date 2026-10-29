"""The counts /content-audit works out by hand: planned content, content files on disk, status bands."""
import os
import re
import sys

from .. import config as cfgmod
from . import _util, registry as regmod

HELP = """Usage: python tools/studio.py content-count [--root DIR] COMMAND [ARGS]
The counts /content-audit works out by hand: the named content the entity registry plans (deprecated ones
left out), the content files found on disk per content type, and a specified / found pair's percentage
and status band, with the gap table's totals. Observations, not a verdict.
  registry        the planned named content: the entries of design/registry/entities.yaml's entities and
                  items sections, deprecated ones left out
  found [--engine E] [--files]
                  content files on disk (E is unity or none; default: engine.name from project.toml,
                  anything but unity uses the neutral assets/ layout)
  band FOUND SPECIFIED
                  the percentage and status band of one pair
  gap             rows `system<TAB>type<TAB>specified<TAB>found` on stdin: the gap table, with totals
The status bands (found / specified compared exactly; percentages truncated to one decimal):
  found = 0 NOT STARTED; 0 < found/specified < 50% EARLY; 50% <= found/specified < 100% IN PROGRESS;
  found >= specified COMPLETE. A specified of 0 has no percentage and no band: `-`.
Where `found` looks: neutral layout: assets/ (data types need a data/ folder first, as the skill's
assets/data/** globs do); unity: Assets/ (every type, no data/ segment needed) and assets/. Types:
  levels      scene files (unity: .unity; neutral: .scene, .level, .map, .json, .yaml) in folders named
              levels, areas, maps, worlds or stages
  characters  folders enemies, characters, npcs
  items       folders items, equipment, loot (unity also *Item*.asset)
  abilities   folders abilities, skills, spells
  quests      folders quests, missions, objectives
  dialogue    .dialogue, .csv, .ink files under any root
Folder names compare in any case. Data files are json, yaml, asset and, on unity, prefab.
Output: TSV.
  registry: registry <path> <entries | missing | layout>, planned entities / items, planned_total,
            deprecated_skipped, no_status, status_other, duplicate_names, source rows, then PLANNED and
            SKIPPED rows
  found:    engine <name> <source>, root <dir> <present|absent>, found <type> <n>, by <type> <folder> <n>,
            and with --files FILE <type> <path>
  band:     band <F>/<S> <name | -> <percent | -> <rule>
  gap:      rows <counted> <read>, excluded <n>, total_specified, total_found, total_gap, gap_pct, unbuilt,
            unbuilt_pct, systems <n>, ROW <system> <type> <specified> <found> <gap> <percent> <status> <low>,
            EXCLUDED <system> <type> <reason>
Exit codes: 0 answered; 1 the root cannot be read; 2 usage error; 3 gap: no row with numbers; 4 registry: the
layout is unsupported, or found: none of the roots exists. Reads only."""

TYPES = ["levels", "characters", "items", "abilities", "dialogue", "quests"]
FOLDERS = {"levels": ["levels", "areas", "maps", "worlds", "stages"],
           "characters": ["enemies", "characters", "npcs"],
           "items": ["items", "equipment", "loot"],
           "abilities": ["abilities", "skills", "spells"],
           "dialogue": [".dialogue", ".csv", ".ink"],
           "quests": ["quests", "missions", "objectives"]}


def pct1(f, s):
    if s == 0:
        return "-"
    t = (f * 1000) // s
    return "%d.%d" % (t // 10, t % 10)


def band(f, s):
    if s == 0:
        return "-", "specified is 0: no percentage"
    if f == 0:
        return "NOT STARTED", "found = 0"
    if f >= s:
        return "COMPLETE", "found >= specified"
    if f * 2 >= s:
        return "IN PROGRESS", "50% <= found/specified < 100%"
    return "EARLY", "0 < found/specified < 50%"


def cmd_gap():
    nread = 0
    rows, ex = [], []
    ts = tf = ub = 0
    systems = set()
    import sys as _s
    for line in _s.stdin.read().replace("\r", "").split("\n"):
        if line == "":
            continue
        nread += 1
        c = line.split("\t")
        sy, ty = c[0].strip(), (c[1].strip() if len(c) > 1 else "")
        if len(c) < 4:
            ex.append("%s\t%s\tfewer than 4 columns" % (sy, ty))
            continue
        sp, fo = c[2].strip(), c[3].strip()
        if not re.match(r"^[0-9]+$", sp):
            ex.append("%s\t%s\tspecified is not a number: %s" % (sy, ty, sp))
            continue
        if not re.match(r"^[0-9]+$", fo):
            ex.append("%s\t%s\tfound is not a number: %s" % (sy, ty, fo))
            continue
        sp, fo = int(sp), int(fo)
        name, _ = band(fo, sp)
        sg = sp - fo if sp > fo else 0
        low = "-" if name == "-" else ("yes" if name in ("EARLY", "NOT STARTED") else "no")
        rows.append("ROW\t%s\t%s\t%d\t%d\t%d\t%s\t%s\t%s" % (sy, ty, sp, fo, sg, pct1(fo, sp), name, low))
        ts += sp
        tf += fo
        ub += sg
        systems.add(sy)
    print("rows\t%d\t%d\nexcluded\t%d" % (len(rows), nread, len(ex)))
    if not rows:
        print("total_specified\t-\ntotal_found\t-\ntotal_gap\t-\ngap_pct\t-\nunbuilt\t-\nunbuilt_pct\t-\nsystems\t0")
    else:
        d = ts - tf
        print("total_specified\t%d\ntotal_found\t%d\ntotal_gap\t%d" % (ts, tf, d))
        if ts == 0:
            print("gap_pct\t-")
        elif d < 0:
            print("gap_pct\t-%s" % pct1(-d, ts))
        else:
            print("gap_pct\t%s" % pct1(d, ts))
        print("unbuilt\t%d\nunbuilt_pct\t%s\nsystems\t%d" % (ub, pct1(ub, ts), len(systems)))
    for r in rows:
        print(r)
    for e in ex:
        print("EXCLUDED\t" + e)
    if not rows:
        sys.stderr.write("content-count: no row with a specified and a found number\n")
        return 3
    return 0


def cmd_registry(root):
    reg = regmod.load(root, "entities")
    if reg.missing:
        print("registry\t%s\tmissing" % reg.path)
        print("planned\tentities\t0\nplanned\titems\t0\nplanned_total\t0\ndeprecated_skipped\t0\nno_status\t0\nstatus_other\t0\t-\nduplicate_names\t0")
        return 0
    if reg.bad:
        print("registry\t%s\tlayout" % reg.path)
        regmod.layout_rows([reg])
        sys.stderr.write("content-count: unsupported registry layout; the LAYOUT rows give each line and the layout expected there\n")
        return 4
    planned, rows = {"entities": 0, "items": 0}, []
    total = nskip = nostat = nother = ndup = 0
    others, names, sources, order = [], {}, {}, []
    for e in reg.entries:
        if e.section not in ("entities", "items"):
            continue
        stt = e.status if e.status_set and e.status else "-"
        src = e.source or "-"
        if stt.lower() == "deprecated":
            nskip += 1
            rows.append("SKIPPED\t%s\t%s\t%s\tdeprecated" % (e.section, e.name or "-", src))
            continue
        planned[e.section] += 1
        total += 1
        rows.append("PLANNED\t%s\t%s\t%s" % (e.section, e.name or "-", src))
        if stt == "-":
            nostat += 1
        elif stt.lower() != "active":
            nother += 1
            if stt not in others:
                others.append(stt)
        k = (e.section, e.name)
        names[k] = names.get(k, 0) + 1
        if names[k] == 2:
            ndup += 1
        if src not in sources:
            order.append(src)
        sources[src] = sources.get(src, 0) + 1
    print("registry\t%s\t%d" % (reg.path, len(reg.entries)))
    print("planned\tentities\t%d\nplanned\titems\t%d\nplanned_total\t%d" % (planned["entities"], planned["items"], total))
    print("deprecated_skipped\t%d\nno_status\t%d\nstatus_other\t%d\t%s\nduplicate_names\t%d" % (nskip, nostat, nother, ",".join(others) or "-", ndup))
    for s in sorted(order):
        print("source\t%s\t%d" % (s, sources[s]))
    for r in rows:
        print(r)
    return 0


def cmd_found(root, engine_arg, showfiles):
    if engine_arg:
        if engine_arg.lower() not in ("unity", "none"):
            sys.stderr.write("studio: engine %s is not supported; use unity or none\n" % engine_arg)
            return 2
        eng, esrc = engine_arg.lower(), "flag"
    else:
        cfg = cfgmod.load(root)
        val, src = cfg.get("engine.name")
        eng = "unity" if str(val or "").lower() == "unity" else "none"
        esrc = src if val else "default"
    print("engine\t%s\t%s" % (eng, esrc))
    roots = ["assets", "Assets"] if eng == "unity" else ["assets"]
    present = []
    top = os.listdir(root)
    for r in roots:
        if r in top and os.path.isdir(os.path.join(root, r)):
            print("root\t%s\tpresent" % r)
            present.append(r)
        else:
            print("root\t%s\tabsent" % r)
    files = []
    for r in present:
        for dp, _, fn in os.walk(os.path.join(root, r)):
            for f in fn:
                files.append(os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/"))
    files.sort()
    scene_ext = ({"unity"} if eng == "unity" else {"scene", "level", "map", "json", "yaml", "yml"})

    def extok(g, e):
        if eng == "unity":
            return e in ("json", "yaml", "asset", "prefab")
        return e in ("json", "yaml", "yml", "asset")
    tot = {g: 0 for g in TYPES}
    by = {}
    frows = []
    folders = {g: list(FOLDERS[g]) for g in TYPES}
    for p in files:
        seg = p.split("/")
        n = len(seg)
        if n < 2:
            continue
        rt, fname = seg[0], seg[-1]
        ext = fname.rsplit(".", 1)[1].lower() if "." in fname else ""
        first = 1
        if rt == "assets":
            first = 2 if (n >= 3 and seg[1].lower() == "data") else n - 1
        for g in TYPES:
            hit, hn = False, []
            if g == "levels":
                if ext not in scene_ext:
                    continue
                for w in [s.lower() for s in seg[1:-1]]:
                    if w in FOLDERS[g] and w not in hn:
                        hn.append(w)
                if eng != "unity" and not hn:
                    continue
                hit = True
            elif g == "dialogue":
                if ext not in ("dialogue", "csv", "ink"):
                    continue
                hit, hn = True, ["." + ext]
            else:
                if extok(g, ext):
                    for w in [s.lower() for s in seg[first:-1]]:
                        if w in FOLDERS[g] and w not in hn:
                            hn.append(w)
                            hit = True
                if eng == "unity" and g == "items" and rt == "Assets" and ext == "asset" and "Item" in fname:
                    hit = True
                    hn.append("*Item*.asset")
            if hit:
                tot[g] += 1
                for h in hn:
                    by[(g, h)] = by.get((g, h), 0) + 1
                if showfiles:
                    frows.append("FILE\t%s\t%s" % (g, p))
    for g in TYPES:
        print("found\t%s\t%d" % (g, tot[g]))
    for g in TYPES:
        names = list(FOLDERS[g]) + (["*Item*.asset"] if eng == "unity" and g == "items" else [])
        for f in names:
            print("by\t%s\t%s\t%d" % (g, f, by.get((g, f), 0)))
    for r in frows:
        print(r)
    if not present:
        sys.stderr.write("content-count: none of the roots (%s) exists; nothing was scanned\n" % " ".join(roots))
        return 4
    return 0


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    cmd, pos, engine_arg, showfiles = "", [], "", False
    i = 0
    while i < len(rest):
        a = rest[i]
        if a in ("-h", "--help"):
            print(HELP)
            return 0
        if a == "--engine":
            if i + 1 >= len(rest):
                sys.stderr.write("content-count: --engine needs a name (try --help)\n")
                return 2
            engine_arg = rest[i + 1]
            i += 2
            continue
        if a.startswith("--engine="):
            engine_arg = a[9:]
        elif a == "--files":
            showfiles = True
        elif a.startswith("-") and len(a) > 1:
            sys.stderr.write("content-count: unknown argument: %s (try --help)\n" % a)
            return 2
        elif not cmd:
            cmd = a
        else:
            pos.append(a)
        i += 1

    def usage(msg):
        sys.stderr.write("content-count: %s (try --help)\n" % msg)
        return 2
    if cmd in ("registry", "gap", "found") and pos:
        return usage("%s takes no arguments" % cmd)
    if cmd == "band":
        if len(pos) != 2:
            return usage("band needs FOUND and SPECIFIED")
        if not all(re.match(r"^[0-9]+$", p) for p in pos):
            return usage("band takes whole numbers")
    elif cmd not in ("registry", "gap", "found"):
        return usage("no command" if not cmd else "unknown command: " + cmd)
    if cmd != "found" and engine_arg:
        return usage("--engine belongs to found")
    if cmd != "found" and showfiles:
        return usage("--files belongs to found")
    if cmd == "band":
        f, s = int(pos[0]), int(pos[1])
        name, rule = band(f, s)
        print("band\t%d/%d\t%s\t%s\t%s" % (f, s, name, pct1(f, s), rule))
        return 0
    if cmd == "gap":
        return cmd_gap()
    if not os.path.isdir(root):
        sys.stderr.write("content-count: cannot read root %s\n" % root)
        return 1
    if cmd == "registry":
        return cmd_registry(root)
    return cmd_found(root, engine_arg, showfiles)
