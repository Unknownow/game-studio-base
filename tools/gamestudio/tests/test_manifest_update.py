import os
import shutil
import tempfile
import unittest

from ._util import RepoCase, git, write_files

MANIFEST = "# game-studio template manifest v1\nAGENTS.md\ntools/**\n!tools/local-only.txt\nfiles.manifest\nfiles.manifest.d/**\n"


class UpdateTest(RepoCase):
    def setUp(self):
        RepoCase.setUp(self)
        self.src = tempfile.mkdtemp(prefix="studio-src-")
        self.addCleanup(shutil.rmtree, self.src, True)
        write_files(self.src, {"files.manifest": MANIFEST, "AGENTS.md": "new agents\n", "tools/a.py": "a2\n",
                               "tools/new.py": "n\n", "tools/local-only.txt": "x\n"})
        write_files(self.root, {"files.manifest": MANIFEST, "AGENTS.md": "old agents\n", "tools/a.py": "a1\n",
                                "tools/gone.py": "g\n", "design/mine.md": "mine\n",
                                "project.toml": "schema_version = 1\n"})

    def update(self, *args):
        return self.run_cli("update", "--from", self.src, *args)

    def test_dry_run_reports_a_m_d(self):
        code, out, _ = self.update("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("A tools/new.py", out)
        self.assertIn("M tools/a.py", out)
        self.assertIn("M AGENTS.md", out)
        self.assertIn("D tools/gone.py", out)
        self.assertNotIn("local-only", out)
        with open(os.path.join(self.root, "tools/a.py"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "a1\n")

    def test_apply_keeps_removed_without_delete(self):
        code, out, _ = self.update()
        self.assertEqual(code, 0)
        self.assertTrue(os.path.exists(os.path.join(self.root, "tools/gone.py")))
        with open(os.path.join(self.root, "tools/a.py"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "a2\n")
        self.assertTrue(os.path.exists(os.path.join(self.root, "tools/new.py")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "design/mine.md")))

    def test_delete_flag(self):
        self.update("--delete")
        self.assertFalse(os.path.exists(os.path.join(self.root, "tools/gone.py")))

    def test_writes_framework_version(self):
        self.git_init()
        git(self.src, "init", "-q", "-b", "main")
        git(self.src, "config", "user.email", "t@example.com")
        git(self.src, "config", "user.name", "T")
        git(self.src, "add", "-A")
        git(self.src, "commit", "-q", "-m", "x")
        git(self.src, "tag", "v9.9.9")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")
        code, _, _ = self.update()
        self.assertEqual(code, 0)
        with open(os.path.join(self.root, "project.toml"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn('version = "v9.9.9"', text)
        self.assertIn("source =", text)

    def test_dirty_manifest_path_refuses(self):
        self.git_init()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")
        with open(os.path.join(self.root, "tools/a.py"), "w", encoding="utf-8") as fh:
            fh.write("edited\n")
        code, _, err = self.update()
        self.assertEqual(code, 2)
        self.assertIn("uncommitted changes", err)
        self.assertIn("tools/a.py", err)

    def test_manifest_d_honoured(self):
        write_files(self.src, {"files.manifest.d/x.manifest": "ENGINE.md\n", "ENGINE.md": "engine\n"})
        self.update()
        self.assertTrue(os.path.exists(os.path.join(self.root, "ENGINE.md")))

    def test_source_without_manifest_exits_2(self):
        os.remove(os.path.join(self.src, "files.manifest"))
        self.assertEqual(self.update()[0], 2)


if __name__ == "__main__":
    unittest.main()
