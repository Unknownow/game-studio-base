import os
import subprocess
import sys
import unittest

from ._util import REPO, STUDIO


class GuardTest(unittest.TestCase):
    def test_old_python_exits_2_with_message(self):
        code = (
            "import sys, runpy\n"
            "sys.version_info = (3, 9, 0, 'final', 0)\n"
            "sys.argv = [%r]\n"
            "runpy.run_path(%r, run_name='__main__')\n" % (STUDIO, STUDIO)
        )
        r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("studio: Python 3.11+ is required (running 3.9.0 at", r.stderr)
        self.assertIn("Windows Store", r.stderr)

    def test_help_lists_commands(self):
        r = subprocess.run([sys.executable, STUDIO, "--help"], capture_output=True, text=True, cwd=REPO)
        self.assertEqual(r.returncode, 0)
        for name in ("setup", "status", "config", "check", "update", "upstream-diff", "claude-sync", "story-facts"):
            self.assertIn(name, r.stdout)


if __name__ == "__main__":
    unittest.main()
