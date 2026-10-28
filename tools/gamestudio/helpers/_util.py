"""Shared bits for helper commands."""
import os
import re
import sys

from .. import config as cfgmod

STATUS_RE = re.compile(r"^[>\-\s]*\**Status:?\**:?\s*(.*)$")


def row(*cols):
    sys.stdout.write("\t".join(("-" if c in (None, "") else str(c)) for c in cols) + "\n")


def usage_error(name, msg):
    sys.stderr.write("%s: %s (try --help)\n" % (name, msg))
    return 2


def split_root(argv):
    """Pull --root DIR out of argv. Returns (root_or_None, rest)."""
    rest, root, i = [], None, 0
    while i < len(argv):
        if argv[i] == "--root" and i + 1 < len(argv):
            root = argv[i + 1]
            i += 2
        elif argv[i].startswith("--root="):
            root = argv[i][7:]
            i += 1
        else:
            rest.append(argv[i])
            i += 1
    return root, rest


def read(path):
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        return fh.read().replace("\r\n", "\n")


def story_status_of(text):
    """The Status value as written (any of the CCGS formats), or None."""
    for line in text.split("\n"):
        s = line.strip()
        s = re.sub(r"^>\s*", "", s)
        s = re.sub(r"^-\s+", "", s)
        s = s.replace("*", "")
        if s.startswith("Status:"):
            return s[7:].strip()
    return None


def is_done(status):
    return bool(re.match(r"^(complete|done)([^a-z]|$)", status.lower()))


def story_files(root):
    base = os.path.join(root, "production", "epics")
    out = []
    if os.path.isdir(base):
        for epic in sorted(os.listdir(base)):
            d = os.path.join(base, epic)
            if os.path.isdir(d):
                for n in sorted(os.listdir(d)):
                    if re.match(r"^story-.*\.md$", n):
                        out.append("production/epics/%s/%s" % (epic, n))
    return out
