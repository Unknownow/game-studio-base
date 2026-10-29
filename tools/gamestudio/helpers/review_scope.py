"""GDD scope for an incremental cross-GDD review."""
import os
import re
import subprocess
import sys

from . import _gdd, _util

HELP = """Usage: python tools/studio.py review-scope [--root DIR]
Computes the GDD scope for an incremental cross-GDD review: finds the most recent cross-review report
(design/gdd/gdd-cross-review-*.md, ordered by the date in its name), lists the GDDs changed since it,
and lists the .md dependencies those GDDs declare.
Output:
  PRIOR_REVIEW: <path>          (or "NONE (full review required)")
  CHANGED:                      GDDs modified since that review
  DEPS ...:                     declared .md dependencies of the changed GDDs
Exit codes: 0 done."""


def _git(root, *args):
    try:
        p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True, errors="replace")
        return p.stdout if p.returncode == 0 else ""
    except OSError:
        return ""


def _changed(root, review):
    base = _git(root, "log", "-1", "--format=%H", "--", review).strip()
    names = set()
    if base:
        for ln in _git(root, "diff", "--name-only", base, "--", ":(glob)design/gdd/*.md").splitlines():
            names.add(ln.strip().replace("\\", "/"))
        out = _git(root, "status", "--porcelain", "-z", "--", ":(glob)design/gdd/*.md")
        parts = out.split("\0")
        i = 0
        while i < len(parts):
            e = parts[i]
            if len(e) > 3:
                names.add(e[3:].replace("\\", "/"))
                if e[0] in "RC":
                    i += 1
            i += 1
    else:
        mt = os.path.getmtime(os.path.join(root, review))
        d = os.path.join(root, "design", "gdd")
        for n in sorted(os.listdir(d)):
            p = os.path.join(d, n)
            if n.endswith(".md") and os.path.isfile(p) and os.path.getmtime(p) > mt:
                names.add("design/gdd/" + n)
    return sorted(names)


def _deps(text):
    dep = False
    found = set()
    for ln in text.split("\n"):
        if ln.startswith("## "):
            h = re.sub(r"^##[ \t]+", "", ln).lower()
            h = re.sub(r"^[0-9]+[.)]?[ \t]*", "", h)
            dep = h.startswith("dependencies")
        if dep:
            found.update(re.findall(r"[A-Za-z0-9_-]+\.md", ln))
    return sorted(found)


def main(root, argv):
    r, rest = _util.split_root(argv)
    if r:
        root = os.path.abspath(r)
    if any(a in ("-h", "--help") for a in rest):
        print(HELP)
        return 0
    d = os.path.join(root, "design", "gdd")
    reviews = []
    if os.path.isdir(d):
        reviews = sorted("design/gdd/" + n for n in os.listdir(d)
                         if re.match(r"^gdd-cross-review-.*\.md$", n) and os.path.isfile(os.path.join(d, n)))
    if not reviews:
        print("PRIOR_REVIEW: NONE (full review required)")
        print("CHANGED:")
        gd = _gdd.system_gdds(root)
        if gd:
            for f in gd:
                print("  " + f)
        else:
            print("  (no system GDDs found)")
        return 0
    last = reviews[-1]
    print("PRIOR_REVIEW: " + last)
    scope = [f for f in _changed(root, last) if _gdd.is_system_gdd(f) and os.path.isfile(os.path.join(root, f))]
    print("CHANGED:")
    if not scope:
        print("  (none — no GDDs modified since last review)")
        return 0
    for f in scope:
        print("  " + f)
    print("DEPS (declared in changed GDDs — include these in review scope too):")
    for f in scope:
        for dep in _deps(_util.read(os.path.join(root, f))):
            print("  %s -> %s" % (os.path.basename(f), dep))
    return 0
