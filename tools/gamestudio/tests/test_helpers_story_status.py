import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]


class StoryStatusTest(RepoCase):
    def test_none(self):
        self.with_toml()
        self.assertEqual(self.run_cli("story-status")[1].strip(), "STORIES      none")

    def test_order_and_complete_count(self):
        self.with_toml({"production/epics/a/story-001.md": story("Ready"),
                        "production/epics/a/story-002.md": story("In Review"),
                        "production/epics/a/story-003.md": story("In Progress"),
                        "production/epics/a/story-004.md": story("Blocked — BLOCKED: x"),
                        "production/epics/a/story-005.md": story("Done"),
                        "production/epics/a/story-006.md": story("Not Done")})
        _, out, _ = self.run_cli("story-status")
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("IN_REVIEW    production/epics/a/story-002.md"))
        self.assertTrue(lines[1].startswith("IN_PROGRESS  production/epics/a/story-003.md"))
        self.assertTrue(lines[2].startswith("TODO         production/epics/a/story-001.md  (Ready)"))
        self.assertTrue(lines[3].startswith("BLOCKED      production/epics/a/story-004.md"))
        self.assertTrue(lines[4].startswith("OTHER        production/epics/a/story-006.md"))
        self.assertEqual(lines[-1], "COMPLETE     1 of 6")


if __name__ == "__main__":
    unittest.main()
