"""Shared by gdd-structure-check and review-scope: which files in design/gdd/ are system GDDs."""
import fnmatch
import os

NOT_SYSTEM = ["game-concept.md", "systems-index.md", "game-pillars.md", "gdd-cross-review-*.md",
              "gameplay-tags.md", "fixture-swap-ledger.md", "entity-registry.md", "sound-bible.md"]


def is_system_gdd(name):
    base = os.path.basename(name)
    return not any(fnmatch.fnmatch(base, p) for p in NOT_SYSTEM)


def system_gdds(root):
    d = os.path.join(root, "design", "gdd")
    if not os.path.isdir(d):
        return []
    return ["design/gdd/" + n for n in sorted(os.listdir(d))
            if n.endswith(".md") and os.path.isfile(os.path.join(d, n)) and is_system_gdd(n)]
