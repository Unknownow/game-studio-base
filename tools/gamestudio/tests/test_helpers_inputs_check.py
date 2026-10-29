import unittest

from ._util import RepoCase


class InputsCheckTest(RepoCase):
    def test_found_empty_absent(self):
        self.add({"design/a.md": "# A\n", "design/blank.md": "  \n", "docs/x/one.md": "x", "docs/x/y/two.md": "y"})
        code, out, _ = self.run_cli("inputs-check", "design/a.md", "design/blank.md", "design/nope.md", "docs/**/*.md", "docs/")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[:4], ["inputs\t5", "found\t3", "empty\t1", "absent\t1"])
        self.assertIn("FOUND\tdesign/a.md\t1\tdesign/a.md", lines)
        self.assertIn("EMPTY\tdesign/blank.md\t1\tdesign/blank.md", lines)
        self.assertIn("ABSENT\tdesign/nope.md\t0\t-", lines)
        self.assertIn("FOUND\tdocs/**/*.md\t2\tdocs/x/one.md", lines)

    def test_from_file_and_usage_errors(self):
        self.add({"specs.txt": "# c\ndesign/a.md\n", "design/a.md": "x"})
        code, out, _ = self.run_cli("inputs-check", "--from", self.root + "/specs.txt")
        self.assertEqual(code, 0)
        self.assertIn("FOUND\tdesign/a.md", out)
        self.assertEqual(self.run_cli("inputs-check")[0], 2)
        self.assertEqual(self.run_cli("inputs-check", "/abs/path")[0], 2)
        self.assertEqual(self.run_cli("inputs-check", "--bogus")[0], 2)
