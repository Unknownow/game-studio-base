"""Shared helpers: repo root, git, globbing, findings."""
import os
import re
import subprocess

SKIP_DIRS = {".git", ".claude", "node_modules", "__pycache__", "Library", "Temp", "Logs", "UserSettings", "obj"}


def default_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def git(root, *args, check_output=True):
    """Run git in root. Returns (returncode, stdout). Never raises for a missing git."""
    try:
        p = subprocess.run(["git", "-C", root] + list(args), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
    except OSError:
        return 127, ""
    return p.returncode, p.stdout


def read_text(path):
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        return fh.read().replace("\r\n", "\n")


def walk(root, subdir="", suffix=None):
    """Relative posix paths of files below root/subdir, skipping generated folders."""
    base = os.path.join(root, subdir) if subdir else root
    out = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for name in sorted(filenames):
            if suffix and not name.endswith(suffix):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
            out.append(rel)
    return out


def glob_to_regex(pattern):
    pattern = pattern.strip().lstrip("/")
    anywhere = "/" not in pattern.rstrip("/")
    trailing = pattern.endswith("/")
    if trailing:
        pattern = pattern[:-1]
    i = 0
    out = []
    while i < len(pattern):
        c = pattern[i]
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
            continue
        if pattern.startswith("**", i):
            out.append(".*")
            i += 2
            continue
        if c == "*":
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    body = "".join(out)
    if anywhere:
        body = "(?:.*/)?" + body
    if trailing:
        body += "/.*"
    return re.compile("^" + body + "$")


def match_any(patterns, path):
    return any(glob_to_regex(p).match(path) for p in patterns)


class Report(object):
    def __init__(self):
        self.items = []

    def error(self, id_, path, msg):
        self.items.append(("ERROR", id_, path, msg))

    def warn(self, id_, path, msg):
        self.items.append(("WARN", id_, path, msg))

    @property
    def errors(self):
        return sum(1 for i in self.items if i[0] == "ERROR")

    @property
    def warnings(self):
        return sum(1 for i in self.items if i[0] == "WARN")

    def lines(self):
        out = ["%s %s %s: %s" % (lvl, id_, path or "-", msg) for lvl, id_, path, msg in self.items]
        out.append("check: %d errors, %d warnings" % (self.errors, self.warnings))
        return out
