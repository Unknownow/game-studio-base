"""Build the ADR dependency graph, detect cycles, and give the order to implement ADRs in."""
import os
import re
import sys

from . import _util

HELP = """Usage: python tools/studio.py adr-dep-graph [adr-dir] [--root DIR]
Builds the ADR dependency graph, detects cycles, and gives the order to implement the ADRs in.
adr-dir defaults to docs/architecture. Observations, not a verdict: the caller decides FAIL vs CONCERNS.
Output:
  ADRS: <n>
  EDGES:                        one "adr-A -> adr-B" per Depends-On reference (or "  (none)")
  NO_DEPS_SECTION: adr-X, ...   ADRs with no `## ADR Dependencies` / no Depends On
  UNFILLED_DEPS: adr-X, ...     ADRs whose Depends On row is still the template's [bracketed] placeholder
  CYCLE: adr-A -> adr-B         one line per ADR on a dependency cycle, with its edges to ADRs on that cycle
  BLOCKED_BY_CYCLE: adr-X, ...  ADRs on no cycle that depend on one, directly or through others
  ORDER: adr-A, adr-B, ...      every other ADR, dependencies first, by id within each step
CYCLE and BLOCKED_BY_CYCLE are absent when there are none; ORDER is "(none)" when every ADR is on or
behind a cycle. IDs are normalised to lowercase `adr-NNNN`.
Exit codes: 0 done."""

ID_RE = re.compile(r"adr-[0-9]+", re.I)


def adr_id(s):
    m = ID_RE.search(s)
    return m.group(0).lower() if m else ""


def read_deps(text):
    """(depends_on_rows, first_value_cell) of the `## ADR Dependencies` section, or (None, None)."""
    rows, cell = [], None
    insec = False
    for ln in text.split("\n"):
        if ln.startswith("## "):
            insec = "## ADR Dependencies" in ln
        if insec and "**Depends On**" in ln:
            rows.append(ln)
            if cell is None:
                parts = ln.split("|")
                c = parts[2].strip() if len(parts) >= 3 else ""
                cell = c or ln
    if not rows:
        return None, None
    return rows, cell


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    if any(a in ("-h", "--help") for a in rest):
        print(HELP)
        return 0
    adr_dir = rest[0] if rest else os.path.join(root, "docs", "architecture")
    files = []
    if os.path.isdir(adr_dir):
        files = sorted(n for n in os.listdir(adr_dir)
                       if re.match(r"^adr-.*\.md$", n) and os.path.isfile(os.path.join(adr_dir, n)))
    if not files:
        print("ADRS: 0")
        print("EDGES:")
        print("  (none — no ADRs in %s)" % (rest[0] if rest else "docs/architecture"))
        return 0
    nodes, edges, no_deps, unfilled = [], [], [], []
    for f in files:
        src = adr_id(f)
        if src:
            nodes.append(src)
        rows, cell = read_deps(_util.read(os.path.join(adr_dir, f)))
        if rows is None:
            no_deps.append(src)
            continue
        targets = sorted({m.group(0).lower() for ln in rows for m in ID_RE.finditer(ln)})
        if not targets:
            if cell.startswith("["):
                unfilled.append(src)
            continue
        for t in targets:
            if t != src:
                edges.append((src, t))
    print("ADRS: %d" % len(files))
    print("EDGES:")
    if not edges:
        print("  (none)")
    for a, b in edges:
        print("  %s -> %s" % (a, b))
    if no_deps:
        print("NO_DEPS_SECTION: " + ", ".join(no_deps))
    if unfilled:
        print("UNFILLED_DEPS: " + ", ".join(unfilled))
    node = sorted(set(nodes) | {x for e in edges for x in e})
    adj = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
    reach = {}
    for s in node:
        seen, q = set(), list(adj.get(s, []))
        while q:
            u = q.pop(0)
            if u in seen:
                continue
            seen.add(u)
            q.extend(adj.get(u, []))
        reach[s] = seen
    on = {x for x in node if x in reach[x]}
    blocked = []
    for x in node:
        if x in on:
            line = "CYCLE: " + x
            for a, b in edges:
                if a == x and b in on and x in reach[b]:
                    line += " -> " + b
            print(line)
    for x in node:
        if x not in on and any(y in reach[x] for y in on):
            blocked.append(x)
    if blocked:
        print("BLOCKED_BY_CYCLE: " + ", ".join(blocked))
    rest_nodes = [x for x in node if x not in on and x not in blocked]
    od = {x: 0 for x in rest_nodes}
    for a, b in edges:
        if a in od:
            od[a] += 1
    order, placed = [], set()
    while True:
        layer = [x for x in rest_nodes if x not in placed and od[x] == 0]
        if not layer:
            break
        for x in layer:
            placed.add(x)
            order.append(x)
        for x in layer:
            for a, b in edges:
                if b == x and a in od:
                    od[a] -= 1
    print("ORDER: " + (", ".join(order) if order else "(none)"))
    return 0
