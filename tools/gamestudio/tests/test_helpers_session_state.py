import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]

import os

TEMPLATE = """# Active Session State

<!-- STATUS -->
Epic: none
<!-- /STATUS -->

<!-- CHECKPOINT -->
**Updated:** never
<!-- /CHECKPOINT -->

## Notes
"""


class SessionStateTest(RepoCase):
    def state(self):
        with open(os.path.join(self.root, "production/session-state/active.md"), encoding="utf-8") as fh:
            return fh.read()

    def test_show_no_file_exits_4(self):
        self.with_toml()
        self.assertEqual(self.run_cli("session-state", "show")[0], 4)

    def test_checkpoint_creates_from_template_then_replaces(self):
        self.with_toml({"templates/session-state.md": TEMPLATE})
        code, out, _ = self.run_cli("session-state", "checkpoint", stdin="**Updated:** today\n**Next step:** go\n")
        self.assertEqual(code, 0)
        self.assertIn("file\tproduction/session-state/active.md\tcreated", out)
        self.assertIn("lines\t2", out)
        code, out, _ = self.run_cli("session-state", "checkpoint", stdin="**Updated:** later\n")
        self.assertIn("replaced", out)
        text = self.state()
        self.assertIn("**Updated:** later", text)
        self.assertNotIn("today", text)
        self.assertIn("## Notes", text)
        code, out, _ = self.run_cli("session-state", "show")
        self.assertIn("<!-- STATUS -->", out)
        self.assertIn("<!-- /CHECKPOINT -->", out)
        self.assertNotIn("## Notes", out)

    def test_checkpoint_idempotent(self):
        self.with_toml({"templates/session-state.md": TEMPLATE})
        self.run_cli("session-state", "checkpoint", stdin="x\n")
        code, out, _ = self.run_cli("session-state", "checkpoint", stdin="x\n")
        self.assertIn("unchanged", out)

    def test_broken_markers_exit_3_and_write_nothing(self):
        broken = "# A\n<!-- CHECKPOINT -->\nstuff\n"
        self.with_toml({"templates/session-state.md": TEMPLATE, "production/session-state/active.md": broken})
        code, _, err = self.run_cli("session-state", "checkpoint", stdin="x\n")
        self.assertEqual(code, 3)
        self.assertEqual(self.state(), broken)

    def test_no_markers_inserts_blocks_at_top(self):
        self.with_toml({"templates/session-state.md": TEMPLATE, "production/session-state/active.md": "old narrative\n"})
        code, out, _ = self.run_cli("session-state", "checkpoint", stdin="cp\n")
        self.assertIn("inserted", out)
        text = self.state()
        self.assertTrue(text.index("<!-- STATUS -->") < text.index("<!-- CHECKPOINT -->") < text.index("old narrative"))

    def test_append_and_skip_duplicate(self):
        self.with_toml({"templates/session-state.md": TEMPLATE})
        code, out, _ = self.run_cli("session-state", "append", stdin="appended line\n")
        self.assertIn("created", out)
        code, out, _ = self.run_cli("session-state", "append", stdin="another\n")
        self.assertIn("appended", out)
        code, out, _ = self.run_cli("session-state", "append", stdin="another\n")
        self.assertIn("unchanged", out)

    def test_no_stdin_exits_2(self):
        self.with_toml({"templates/session-state.md": TEMPLATE})
        self.assertEqual(self.run_cli("session-state", "append", stdin="")[0], 2)


if __name__ == "__main__":
    unittest.main()
