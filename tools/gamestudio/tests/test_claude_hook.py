import json
import unittest

from ._util import RepoCase, git, story


class ClaudeHookTest(RepoCase):
    def setUp(self):
        RepoCase.setUp(self)
        self.with_toml({"production/epics/core/story-001.md": story(type="Bogus")})
        self.git_init()
        git(self.root, "add", "-A")

    def hook(self, command):
        return self.run_cli("claude-hook", "pre-bash", stdin=json.dumps({"tool_input": {"command": command}}))

    def test_commit_with_bad_staged_story_blocks(self):
        code, out, err = self.hook("git commit -m x")
        self.assertEqual(code, 2)
        self.assertIn("ERROR story-sections", err)

    def test_other_command_passes(self):
        code, out, err = self.hook("ls")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")

    def test_commit_with_clean_stage_passes(self):
        git(self.root, "rm", "-q", "--cached", "production/epics/core/story-001.md")
        self.assertEqual(self.hook("git commit -m x")[0], 0)

    def test_bad_stdin_passes(self):
        code, _, _ = self.run_cli("claude-hook", "pre-bash", stdin="not json")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
