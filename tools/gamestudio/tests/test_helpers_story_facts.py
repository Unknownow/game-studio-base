import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]


class StoryFactsTest(RepoCase):
    def test_columns_and_counts(self):
        self.with_toml({"production/epics/core/story-001.md": story("Ready", "Logic")})
        code, out, _ = self.run_cli("story-facts")
        self.assertEqual(code, 0)
        r = rows(out)
        self.assertEqual(r[0], ["stories", "1", "production/epics/**/story-*.md"])
        s = [x for x in r if x[0] == "STORY"][0]
        self.assertEqual(s[1:6], ["production/epics/core/story-001.md", "TODO", "Ready", "Logic", "Core"])
        self.assertEqual(s[7], "TR-core-001")
        self.assertEqual(s[9], "2")

    def test_lint_no_ac_section(self):
        text = story().replace("## Acceptance Criteria", "## Criteria")
        self.with_toml({"production/epics/core/story-001.md": text})
        _, out, _ = self.run_cli("story-facts", "--lint")
        self.assertIn("LINT\tproduction/epics/core/story-001.md\tno_ac_section\t-", out)

    def test_lint_ac_below_min_follows_granularity(self):
        self.with_toml({"production/epics/core/story-001.md": story()})
        _, out, _ = self.run_cli("story-facts", "--lint")
        self.assertIn("ac_below_min\t2 < 3 (Logic)", out)
        _, out, _ = self.run_cli("story-facts", "--lint", "--granularity", "fine")
        self.assertNotIn("ac_below_min", out)

    def test_lint_type_unknown_and_marker_and_unfilled(self):
        text = story(type="Weird").replace("> **Estimate**: S", "> **Estimate**: [S | M]") + "\nTODO later\n"
        self.with_toml({"production/epics/core/story-001.md": text})
        _, out, _ = self.run_cli("story-facts", "--lint")
        self.assertIn("type_unknown\tWeird", out)
        self.assertIn("unfilled\tEstimate", out)
        self.assertIn("marker\tTODO line", out)

    def test_not_found_exits_3(self):
        self.with_toml()
        code, out, _ = self.run_cli("story-facts", "production/epics/x/story-9.md")
        self.assertEqual(code, 3)
        self.assertIn("NOT_FOUND\tproduction/epics/x/story-9.md", out)

    def test_sprint_scope(self):
        self.with_toml({"production/epics/core/story-001.md": story(),
                        "production/sprint-status.yaml": "stories:\n  - file: production/epics/core/story-001.md\n    status: in-progress\n"})
        code, out, _ = self.run_cli("story-facts", "--sprint")
        self.assertEqual(code, 0)
        self.assertIn("in-progress", out)
        self.assertEqual(self.run_cli("story-facts", "--sprint", root=self.root + "-missing")[0], 1)


if __name__ == "__main__":
    unittest.main()
