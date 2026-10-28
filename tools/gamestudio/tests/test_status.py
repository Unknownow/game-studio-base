import unittest

from ._util import RepoCase, story


class StatusTest(RepoCase):
    def test_counts_and_next_story(self):
        self.with_toml({"production/epics/core/story-001.md": story("Done"),
                        "production/epics/core/story-002.md": story("Ready"),
                        "production/epics/core/story-003.md": story("Ready")})
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("Done: 1, Ready: 2", out)
        self.assertIn("next: production/epics/core/story-002.md", out)

    def test_gap_without_brief(self):
        self.with_toml()
        _, out, _ = self.run_cli("status")
        self.assertIn("run the start skill", out)

    def test_no_gap_with_brief(self):
        self.with_toml({"design/game-brief.md": "# Brief\n"})
        _, out, _ = self.run_cli("status")
        self.assertNotIn("run the start skill", out)

    def test_session_state_shown(self):
        self.with_toml({"production/session-state/active.md": "# Active\nline two\n"})
        _, out, _ = self.run_cli("status")
        self.assertIn("line two", out)

    def test_plugin_status_line(self):
        self.add({"project.toml": 'schema_version = 1\n[engine]\nname = "unity"\n'})
        # no unity plugin in base: status still works and prints an Engine-free report
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertIn("engine: unity", out)

    def test_unreadable_config_exits_2(self):
        self.add({"project.toml": "= broken"})
        self.assertEqual(self.run_cli("status")[0], 2)


class PluginTest(unittest.TestCase):
    def test_plugin_hooks_are_called(self):
        import os
        import tempfile
        import shutil
        from gamestudio import engines, status
        from gamestudio import config as cfgmod
        from ._util import write_files
        root = tempfile.mkdtemp(prefix="studio-plug-")
        self.addCleanup(shutil.rmtree, root, True)
        write_files(root, {"project.toml": 'schema_version = 1\n[engine]\nname = "fakeeng"\n'})
        plugin_path = os.path.join(os.path.dirname(engines.__file__), "fakeeng.py")
        with open(plugin_path, "w", encoding="utf-8") as fh:
            fh.write("def status(ctx):\n    return ['fake engine line']\n\ndef code_root(ctx):\n    return 'Fake'\n")
        self.addCleanup(os.remove, plugin_path)
        lines, ok = status.build(root)
        self.assertTrue(ok)
        self.assertIn("== Engine ==", lines)
        self.assertIn("fake engine line", lines)
        ctx = engines.Ctx(root, cfgmod.load(root))
        self.assertEqual(engines.code_root(ctx), "Fake")


if __name__ == "__main__":
    unittest.main()
