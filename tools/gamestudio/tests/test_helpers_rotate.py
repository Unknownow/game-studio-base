import os
import unittest

from ._util import RepoCase

STATE = """# Active
<!-- CHECKPOINT -->
**Updated:** x
<!-- /CHECKPOINT -->

## Notes

""" + "\n".join("line %d" % i for i in range(10)) + "\n"


class RotateTest(RepoCase):
    def test_dry_run_changes_nothing(self):
        self.add({"production/session-state/active.md": STATE})
        code, out, _ = self.run_cli("rotate-session-state", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("DRY RUN", out)
        with open(os.path.join(self.root, "production/session-state/active.md"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), STATE)

    def test_rotates_narrative_keeps_checkpoint(self):
        self.add({"production/session-state/active.md": STATE})
        code, out, _ = self.run_cli("rotate-session-state")
        self.assertEqual(code, 0)
        self.assertIn("rotated", out)
        with open(os.path.join(self.root, "production/session-state/active.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("**Updated:** x", text)
        self.assertNotIn("line 5", text)
        logs = os.listdir(os.path.join(self.root, "production/session-logs"))
        self.assertEqual(len(logs), 1)
        with open(os.path.join(self.root, "production/session-logs", logs[0]), encoding="utf-8") as fh:
            self.assertIn("line 5", fh.read())

    def test_refuses_without_marker(self):
        self.add({"production/session-state/active.md": "just notes\n"})
        code, out, _ = self.run_cli("rotate-session-state")
        self.assertEqual(code, 3)
        self.assertIn("REFUSED", out)

    def test_short_narrative_and_missing_file(self):
        self.add({"production/session-state/active.md": "<!-- /CHECKPOINT -->\nonly\n"})
        self.assertIn("nothing worth rotating", self.run_cli("rotate-session-state")[1])
        self.assertIn("nothing to rotate", self.run_cli("rotate-session-state", root=self.root + "-x")[1])


if __name__ == "__main__":
    unittest.main()
