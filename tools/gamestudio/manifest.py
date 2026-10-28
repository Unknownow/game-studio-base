"""`update`: copy template-owned files from a template checkout into this game."""
import os
import shutil

from . import toml_edit
from .check import manifest_patterns
from .common import git, glob_to_regex, walk


def _select(patterns, paths):
    inc = [glob_to_regex(p) for p in patterns if not p.startswith("!")]
    exc = [glob_to_regex(p[1:]) for p in patterns if p.startswith("!")]
    return {p for p in paths if any(r.match(p) for r in inc) and not any(r.match(p) for r in exc)}


def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def run(root, src, dry_run=False, delete=False):
    """Returns (exit_code, lines)."""
    src = os.path.abspath(src)
    if not os.path.isfile(os.path.join(src, "files.manifest")):
        return 2, ["studio: %s has no files.manifest" % src]
    new_patterns = [p for _, p in manifest_patterns(src)]
    old_patterns = [p for _, p in manifest_patterns(root)]
    src_files = _select(new_patterns, walk(src))
    local_files = walk(root)
    old_local = _select(old_patterns + new_patterns, local_files)
    code, out = git(root, "status", "--porcelain")
    if code == 0:
        dirty = []
        for line in out.splitlines():
            path = line[3:].strip().strip('"').replace("\\", "/")
            if " -> " in path:
                path = path.split(" -> ")[-1]
            dirty.append(path)
        hit = sorted(_select(old_patterns + new_patterns, dirty))
        if hit:
            return 2, ["studio: uncommitted changes to template-owned files; commit or stash first:"] + ["  " + h for h in hit]
    lines = []
    changes = []
    for rel in sorted(src_files):
        dest = os.path.join(root, rel)
        if not os.path.isfile(dest):
            lines.append("A " + rel)
            changes.append(rel)
        elif _read(dest) != _read(os.path.join(src, rel)):
            lines.append("M " + rel)
            changes.append(rel)
    removed = sorted(old_local - src_files)
    for rel in removed:
        lines.append("D " + rel)
    if dry_run:
        return 0, lines
    for rel in changes:
        dest = os.path.join(root, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(os.path.join(src, rel), dest)
    if delete:
        for rel in removed:
            os.remove(os.path.join(root, rel))
    _record(root, src)
    return 0, lines


def _record(root, src):
    code, url = git(src, "remote", "get-url", "origin")
    source = url.strip() if code == 0 and url.strip() else src.replace("\\", "/")
    code, ver = git(src, "describe", "--tags", "--always")
    version = ver.strip() if code == 0 else ""
    path = os.path.join(root, "project.toml")
    text = ""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", newline="") as fh:
            text = fh.read()
    text = toml_edit.set_value(text, "framework.source", source)
    text = toml_edit.set_value(text, "framework.version", version)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)
