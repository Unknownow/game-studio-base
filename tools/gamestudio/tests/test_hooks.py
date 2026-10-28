import os
import shutil
import stat
import subprocess
import tempfile
import unittest

from ._util import REPO, write_files

BASH = shutil.which("bash")


@unittest.skipUnless(BASH, "bash is not on PATH")
class HooksTest(unittest.TestCase):
    def run_python_sh(self, fake_version, name="python"):
        d = tempfile.mkdtemp(prefix="studio-fake-")
        self.addCleanup(shutil.rmtree, d, True)
        script = os.path.join(d, name)
        with open(script, "w", newline="\n") as fh:
            fh.write("#!/bin/sh\necho 'Python %s'\n" % fake_version)
        os.chmod(script, os.stat(script).st_mode | stat.S_IEXEC)
        env = dict(os.environ, PATH=d + os.pathsep + "/usr/bin" + os.pathsep + "/bin")
        return subprocess.run([BASH, os.path.join(REPO, "hooks", "_python.sh")], capture_output=True, text=True, env=env)

    def test_old_python_is_rejected_with_message(self):
        r = self.run_python_sh("3.9.0")
        self.assertEqual(r.returncode, 1)
        self.assertIn("game-studio hook: Python 3.11+ not found (python=3.9", r.stderr)
        self.assertIn("Install Python 3.11+ from python.org.", r.stderr)

    def test_new_python_is_accepted(self):
        r = self.run_python_sh("3.12.1")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(r.stdout.strip(), "python")

    def test_pre_push_warns_on_protected_branch(self):
        r = subprocess.run([BASH, os.path.join(REPO, "hooks", "pre-push")], capture_output=True, text=True,
                           input="refs/heads/x abc refs/heads/main def\n")
        self.assertEqual(r.returncode, 0)
        self.assertIn("WARN pushing to protected branch main", r.stderr)
        r = subprocess.run([BASH, os.path.join(REPO, "hooks", "pre-push")], capture_output=True, text=True,
                           input="refs/heads/x abc refs/heads/feature def\n")
        self.assertNotIn("WARN", r.stderr)

    def test_pre_commit_blocks_on_bad_staged_story(self):
        root = tempfile.mkdtemp(prefix="studio-hook-")
        self.addCleanup(shutil.rmtree, root, True)
        shutil.copytree(os.path.join(REPO, "tools"), os.path.join(root, "tools"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(os.path.join(REPO, "hooks"), os.path.join(root, "hooks"))
        write_files(root, {"project.toml": "schema_version = 1\n", "production/epics/c/story-001.md": "# Story 1\n"})
        subprocess.run(["git", "-C", root, "init", "-q"], check=True)
        subprocess.run(["git", "-C", root, "add", "production"], check=True)
        r = subprocess.run([BASH, os.path.join(root, "hooks", "pre-commit")], capture_output=True, text=True)
        if "Python 3.11+ not found" in r.stderr:
            self.skipTest("no Python 3.11+ visible to the hook on this machine")
        self.assertEqual(r.returncode, 1)
        self.assertIn("story-sections", r.stdout)


if __name__ == "__main__":
    unittest.main()
