import os
import unittest
from unittest import mock

from gamestudio import engines
from gamestudio.helpers import test_scaffold

from ._util import RepoCase


class FakePlugin(object):
    @staticmethod
    def scaffold_files(ctx):
        return {"Fake/Tests/Sample.txt": "sample\n"}


class TestScaffoldTest(RepoCase):
    def test_no_plugin(self):
        code, _, err = self.run_cli("test-scaffold", "nosuchengine")
        self.assertEqual(code, 2)
        self.assertIn("studio: no test scaffold for engine nosuchengine", err)

    def run_scaffold(self, *args):
        with mock.patch.object(engines, "load_by_name", return_value=FakePlugin):
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = test_scaffold.main(self.root, list(args))
            return code, buf.getvalue()

    def test_plugin_files_written_and_never_overwritten(self):
        self.with_toml()
        code, out = self.run_scaffold("fake", "--date", "2026-01-02")
        self.assertEqual(code, 0)
        for p in ("tests/README.md", "production/qa/evidence/.gitkeep", "Fake/Tests/Sample.txt", "tests/smoke/critical-paths.md"):
            self.assertIn("CREATED\t" + p, out)
            self.assertTrue(os.path.exists(os.path.join(self.root, p)))
        with open(os.path.join(self.root, "tests/README.md"), encoding="utf-8") as fh:
            self.assertIn("2026-01-02", fh.read())
        self.add({"Fake/Tests/Sample.txt": "mine\n"})
        os.remove(os.path.join(self.root, "tests/README.md"))
        code, out = self.run_scaffold("fake")
        self.assertIn("CREATED\ttests/README.md", out)
        self.assertIn("EXISTS\tFake/Tests/Sample.txt", out)
        with open(os.path.join(self.root, "Fake/Tests/Sample.txt"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "mine\n")

    def test_dry_run_and_list(self):
        code, out = self.run_scaffold("fake", "--dry-run")
        self.assertIn("WOULD_CREATE\tFake/Tests/Sample.txt", out)
        self.assertFalse(os.path.exists(os.path.join(self.root, "Fake")))
        code, out = self.run_scaffold("fake", "--list")
        self.assertEqual(out.splitlines(), ["tests/README.md", "production/qa/evidence/.gitkeep", "Fake/Tests/Sample.txt", "tests/smoke/critical-paths.md"])
