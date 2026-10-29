import sys
import unittest

from ._util import RepoCase


def toml(command):
    return 'schema_version = 1\n\n[testing]\ncommand = "%s"\n' % command.replace("\\", "\\\\").replace('"', '\\"')


def pycmd(code, out=""):
    return '%s -c "import sys; print(%r); sys.exit(%d)"' % (sys.executable, out, code)


class TestRunTest(RepoCase):
    def rule(self, out):
        return [l for l in out.splitlines() if l.startswith("rule\t")][0].split("\t")[1]

    def test_no_command(self):
        self.with_toml()
        code, _, err = self.run_cli("test-run")
        self.assertEqual(code, 2)
        self.assertIn("studio: no test command; set testing.command in project.toml or configure an engine", err)

    def test_ladder(self):
        for code_, out, want in ((0, "", "no-tests"), (0, "3 passed", "pass"), (1, "1 failed", "fail"), (3, "boom", "error")):
            self.add({"project.toml": toml(pycmd(code_, out))})
            code, o, _ = self.run_cli("test-run")
            self.assertEqual(code, 0, o)
            self.assertEqual(self.rule(o), want, o)
            self.assertIn("exit\t%d" % code_, o)

    def test_timeout_and_dry_run(self):
        self.add({"project.toml": toml('%s -c "import time; time.sleep(5)"' % sys.executable)})
        code, o, _ = self.run_cli("test-run", "--timeout", "1")
        self.assertEqual(self.rule(o), "timeout")
        self.assertIn("timed_out\tyes", o)
        code, o, _ = self.run_cli("test-run", "--dry-run")
        self.assertIn("ran\tno\t--dry-run", o)
        self.assertEqual(self.run_cli("test-run", "--timeout", "0")[0], 2)
