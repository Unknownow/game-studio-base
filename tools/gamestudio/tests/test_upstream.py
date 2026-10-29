import os
import shutil
import tempfile
import unittest

from gamestudio.upstream import classify, load_maps

from ._util import REPO, RepoCase, git, write_files


class UpstreamTest(RepoCase):
    def setUp(self):
        RepoCase.setUp(self)
        self.clone = tempfile.mkdtemp(prefix="studio-up-")
        self.addCleanup(shutil.rmtree, self.clone, True)
        git(self.clone, "init", "-q", "-b", "main")
        git(self.clone, "config", "user.email", "t@example.com")
        git(self.clone, "config", "user.name", "T")
        write_files(self.clone, {".claude/skills/a/SKILL.md": "1\n", ".claude/hooks/notify.sh": "n\n", "README.md": "r\n"})
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-q", "-m", "one")
        git(self.clone, "tag", "t1")
        write_files(self.clone, {".claude/skills/a/SKILL.md": "2\n", ".claude/skills/b/SKILL.md": "b\n",
                                 ".claude/hooks/notify.sh": "n2\n", "NEW.md": "x\n"})
        git(self.clone, "add", "-A")
        git(self.clone, "commit", "-q", "-m", "two")
        git(self.clone, "tag", "t2")
        self.add({"UPSTREAM.toml": '''[upstream]
repo = "x"
tag = "t1"

[[map]]
from = ".claude/skills/**"
to = ".agents/skills/"

[[ignore]]
path = ".claude/hooks/notify.sh"
reason = "claude-only: no event"
'''})

    def test_diff_lines(self):
        code, out, _ = self.run_cli("upstream-diff", "--clone", self.clone, "--to", "t2")
        self.assertEqual(code, 0)
        self.assertIn("M .claude/skills/a/SKILL.md -> .agents/skills/a/SKILL.md", out)
        self.assertIn("A .claude/skills/b/SKILL.md -> .agents/skills/b/SKILL.md", out)
        self.assertIn("M .claude/hooks/notify.sh IGNORED (claude-only: no event)", out)
        self.assertIn("A NEW.md UNMAPPED", out)

    def test_coverage_lists_uncovered(self):
        code, out, _ = self.run_cli("upstream-diff", "--clone", self.clone, "--coverage")
        self.assertEqual(code, 1)
        self.assertIn("UNCOVERED README.md", out)
        self.assertNotIn("UNCOVERED .claude", out)

    def test_coverage_passes_when_all_covered_and_multiple_files_merge(self):
        self.add({"UPSTREAM.unity.toml": '[[ignore]]\npath = "README.md"\nreason = "ccgs-meta: x"\n'})
        code, out, _ = self.run_cli("upstream-diff", "--clone", self.clone, "--coverage")
        self.assertEqual(code, 0)
        self.assertIn("coverage: 3 of 3", out)

    def test_missing_tag_or_clone(self):
        self.assertEqual(self.run_cli("upstream-diff", "--clone", self.clone + "-nope", "--to", "t2")[0], 2)
        self.assertEqual(self.run_cli("upstream-diff", "--clone", self.clone)[0], 2)


CCGS_CLONE = "D:/scratch/ccgs-v1.2.0"


class ClassifyPrecedenceTest(unittest.TestCase):
    def test_engine_layer_ignore_yields_to_map(self):
        maps = [{"from": "a/**", "to": "b/", "_layer": True}, {"from": "c/**", "to": "d/", "_layer": True}]
        ignores = [{"path": "a/**", "reason": "engine-layer: unity"}, {"path": "c/**", "reason": "other-engine: godot"}]
        self.assertEqual(classify(maps, ignores, "a/x.md"), "-> b/x.md")
        self.assertTrue(classify(maps, ignores, "c/x.md").startswith("IGNORED"))
        self.assertTrue(classify([], ignores, "a/x.md").startswith("IGNORED (engine-layer"))

    def test_base_wildcard_map_does_not_beat_engine_layer_ignore(self):
        maps = [{"from": "x/**", "to": "y/"}, {"from": "x/z.md", "to": "Z.md", "_layer": True}]
        ignores = [{"path": "x/q.md", "reason": "engine-layer: unity"}]
        self.assertTrue(classify(maps, ignores, "x/q.md").startswith("IGNORED (engine-layer"))
        self.assertEqual(classify(maps, ignores, "x/z.md"), "-> Z.md")
        self.assertEqual(classify(maps, ignores, "x/o.md"), "-> y/o.md")

    def test_real_base_engine_layer_paths_stay_ignored(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copy(os.path.join(REPO, "UPSTREAM.toml"), tmp)
        maps, ignores, _, _ = load_maps(tmp)
        for p in (".claude/skills/dev-story/references/engine-checks.md", "studio-tests/agents/engine/unity/x.md"):
            self.assertTrue(classify(maps, ignores, p).startswith("IGNORED (engine-layer"), p)


class RealCoverageTest(unittest.TestCase):
    def test_real_map_covers_the_pinned_release(self):
        from ._util import REPO, STUDIO
        import subprocess
        import sys
        if not os.path.isdir(CCGS_CLONE) or subprocess.run(["git", "-C", CCGS_CLONE, "rev-parse", "--verify", "-q", "v1.2.0"],
                                                          capture_output=True).returncode != 0:
            self.skipTest("the CCGS clone at %s with tag v1.2.0 is not available" % CCGS_CLONE)
        r = subprocess.run([sys.executable, STUDIO, "--root", REPO, "upstream-diff", "--clone", CCGS_CLONE, "--to", "v1.2.0", "--coverage"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout[-500:])


if __name__ == "__main__":
    unittest.main()
