"""`upstream-diff`: map changes in the CCGS repo onto this repo. Read-only."""
import os
import tomllib

from .common import git, glob_to_regex, read_text


def load_maps(root):
    maps, ignores, tag, repo = [], [], None, None
    names = sorted(n for n in os.listdir(root) if n.startswith("UPSTREAM") and n.endswith(".toml"))
    for name in names:
        with open(os.path.join(root, name), "rb") as fh:
            data = tomllib.load(fh)
        up = data.get("upstream", {})
        if name == "UPSTREAM.toml" or tag is None:
            tag = up.get("tag") or tag
            repo = up.get("repo") or repo
        maps.extend(dict(m, _layer=name != "UPSTREAM.toml") for m in data.get("map", []))
        ignores.extend(data.get("ignore", []))
    return maps, ignores, tag, repo


def _mapped(entry, path):
    pat = entry["from"]
    to = entry["to"]
    if not to.endswith("/"):
        return to
    prefix = pat.split("*", 1)[0]
    return to + path[len(prefix):]


def classify(maps, ignores, path):
    def hit(ig):
        return glob_to_regex(ig["path"]).match(path)

    def layer(ig):
        return ig.get("reason", "").startswith("engine-layer:")

    for ig in ignores:
        if not layer(ig) and hit(ig):
            return "IGNORED (%s)" % ig.get("reason", "")
    for mp in maps:
        if mp.get("_layer") and glob_to_regex(mp["from"]).match(path):
            return "-> " + _mapped(mp, path)
    for ig in ignores:
        if layer(ig) and hit(ig):
            return "IGNORED (%s)" % ig.get("reason", "")
    for mp in maps:
        if not mp.get("_layer") and glob_to_regex(mp["from"]).match(path):
            return "-> " + _mapped(mp, path)
    return "UNMAPPED"


def run(root, clone, to_tag, coverage):
    maps, ignores, tag, _ = load_maps(root)
    if not tag:
        return 2, ["studio: no [upstream] tag in UPSTREAM.toml"]
    if not os.path.isdir(clone):
        return 2, ["studio: clone directory %s not found" % clone]
    if coverage:
        code, out = git(clone, "ls-tree", "-r", "--name-only", tag)
        if code != 0:
            return 2, ["studio: tag %s not found in %s" % (tag, clone)]
        files = [f for f in out.splitlines() if f]
        missing = [f for f in files if classify(maps, ignores, f) == "UNMAPPED"]
        lines = ["UNCOVERED " + f for f in missing]
        lines.append("coverage: %d of %d upstream files accounted for at %s" % (len(files) - len(missing), len(files), tag))
        return (1 if missing else 0), lines
    if not to_tag:
        return 2, ["studio: --to <tag> is required"]
    code, out = git(clone, "diff", "--name-status", tag, to_tag)
    if code != 0:
        return 2, ["studio: git diff %s %s failed in %s" % (tag, to_tag, clone)]
    lines = []
    for row in out.splitlines():
        parts = row.split("\t")
        if len(parts) < 2:
            continue
        path = parts[-1]
        lines.append("%s %s %s" % (parts[0], path, classify(maps, ignores, path)))
    return 0, lines
