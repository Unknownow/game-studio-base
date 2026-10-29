"""Counts and hygiene of the real repository, not a temporary one."""
import os
import re
import tomllib
import unittest

from gamestudio import helpers
from gamestudio.common import SKIP_DIRS as COMMON_SKIP

from ._util import REPO, STUDIO

import subprocess
import sys

ADDON_OK = ("README.md", "AGENTS.md", "CLAUDE.md", "docs/studio/settings-guidance.md", "docs/studio/setup-requirements.md", "studio-tests/skills/utility/upstream-sync.md", "docs/studio/WORKFLOW-GUIDE.md", ".agents/skills/upstream-sync/SKILL.md", "tools/gamestudio/claude_sync.py",
            "tools/gamestudio/check.py", "tools/gamestudio/cli.py", "tools/gamestudio/data/claude-deny.json", "UPSTREAM.toml",
            "NOTICE", ".gitignore", ".gitattributes", "hooks/post-merge", "hooks/post-checkout", "hooks/pre-commit")
SKIP_DIRS = set(COMMON_SKIP) | {".git", ".claude", "__pycache__"}
ENGINES = sorted(f[:-3] for f in os.listdir(os.path.join(REPO, "tools", "gamestudio", "engines")) if f.endswith(".py") and f != "__init__.py")


def engine_layer(rel):
    parts = rel.split("/")
    for e in ENGINES:
        if parts[0] == "roles" and parts[-1].startswith(e + "-"):
            return True
        if parts[0] == "rules" and len(parts) > 2 and parts[1] == e:
            return True
        if parts[:2] == [".agents", "skills"] and len(parts) > 2 and parts[2].startswith(e + "-"):
            return True
    return rel.startswith("studio-tests/agents/engine/")


def count(sub, pred):
    base = os.path.join(REPO, sub)
    n = 0
    for dp, dn, fn in os.walk(base):
        for f in fn:
            p = os.path.join(dp, f)
            if not engine_layer(os.path.relpath(p, REPO).replace(os.sep, "/")) and pred(p):
                n += 1
    return n


class RepoContentTest(unittest.TestCase):
    def test_counts(self):
        self.assertEqual(count(".agents/skills", lambda p: p.endswith("SKILL.md")), 75)
        self.assertEqual(count("roles", lambda p: p.endswith(".md") and not p.endswith("README.md")), 34)
        self.assertEqual(count("gates", lambda p: p.endswith(".md")), 28)
        self.assertEqual(count("rules", lambda p: p.endswith(".md")), 13)
        self.assertEqual(count("templates", lambda p: True), 71)
        self.assertEqual(len(helpers.NAMES), 28)

    def test_catalog_matches_the_repo(self):
        with open(os.path.join(REPO, "studio-tests", "catalog.toml"), "rb") as fh:
            cat = tomllib.load(fh)
        self.assertEqual(len(cat["skill"]), 75)
        self.assertEqual(len(cat["role"]), 34)
        for e in cat["skill"] + cat["role"]:
            self.assertTrue(os.path.isfile(os.path.join(REPO, e["spec"])), e["spec"])
        self.assertEqual(sorted(e["name"] for e in cat["skill"]), sorted(os.listdir(os.path.join(REPO, ".agents", "skills"))))

    def test_every_helper_answers_help(self):
        for name in helpers.NAMES:
            r = subprocess.run([sys.executable, STUDIO, name, "--help"], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(r.returncode, 0, name + r.stderr)
            self.assertIn("Usage", r.stdout + r.stderr, name)

    def test_no_claude_runtime_leftovers(self):
        bad = re.compile(r"\.claude/|Task(Create|Update)\b|AskUserQuestion|allowed-tools")
        hits = []
        for dp, dn, fn in os.walk(REPO):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                rel = os.path.relpath(os.path.join(dp, f), REPO).replace(os.sep, "/")
                if rel in ADDON_OK or rel.startswith("tools/gamestudio/tests/") or not f.endswith((".md", ".py", ".toml", ".yaml", ".yml", ".json", ".sh")):
                    continue
                with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                    for n, line in enumerate(fh, 1):
                        if bad.search(line) and "upstream: .claude/" not in line:
                            hits.append("%s:%d" % (rel, n))
        self.assertEqual(hits[:10], [], "%d hits" % len(hits))

    def test_no_other_engine_leftovers(self):
        bad = re.compile(r"[Gg]odot|GDScript|[Uu]nreal|gdshader|Blueprint")
        allow = {".agents/skills/upstream-sync/SKILL.md"}
        roots = [".agents", "docs", "roles", "rules", "gates", "templates", "AGENTS.md", "README.md"]
        hits = []
        for r in roots:
            top = os.path.join(REPO, r)
            walker = [(os.path.dirname(top), [], [os.path.basename(top)])] if os.path.isfile(top) else os.walk(top)
            for dp, dn, fn in walker:
                dn[:] = [d for d in dn if d not in SKIP_DIRS and d != "engine-reference"]
                for f in fn:
                    rel = os.path.relpath(os.path.join(dp, f), REPO).replace(os.sep, "/")
                    if rel in allow or engine_layer(rel) or not f.endswith((".md", ".yaml", ".toml")):
                        continue
                    with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                        for n, line in enumerate(fh, 1):
                            if bad.search(line):
                                hits.append("%s:%d" % (rel, n))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
