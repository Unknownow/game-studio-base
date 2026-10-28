import os
import unittest

from ._util import BASE_TOML, RepoCase


class ConfigTest(RepoCase):
    def test_empty_config_defaults(self):
        self.add({"project.toml": "schema_version = 1\n"})
        code, out, _ = self.run_cli("config", "--keys", "rigor,review_mode")
        self.assertEqual(code, 0)
        self.assertIn("rigor: minimal (default)", out)
        self.assertIn("review_mode: solo (rigor:minimal)", out)

    def test_local_overrides_project(self):
        self.add({"project.toml": BASE_TOML, "project.local.toml": '[modes]\nautomation = "autonomous"\n'})
        _, out, _ = self.run_cli("config", "--keys", "automation")
        self.assertIn("automation: autonomous (project.local.toml)", out)

    def test_engine_toml_defaults_source(self):
        self.add({"project.toml": BASE_TOML, "engine.toml": '[defaults]\n"engine.name" = "unity"\n'})
        _, out, _ = self.run_cli("config", "--keys", "engine.name")
        self.assertIn("engine.name: unity (engine.toml)", out)

    def test_rigor_standard_derives(self):
        self.add({"project.toml": 'schema_version = 1\n[modes]\nrigor = "standard"\n'})
        _, out, _ = self.run_cli("config", "--keys", "review_mode,qa.level")
        self.assertIn("review_mode: lean (rigor:standard)", out)
        self.assertIn("qa.level: standard (rigor:standard)", out)

    def test_explicit_value_beats_rigor(self):
        self.add({"project.toml": 'schema_version = 1\n[modes]\nrigor = "full"\n[docs]\ndensity = "terse"\n'})
        _, out, _ = self.run_cli("config", "--keys", "docs.density,qa.level")
        self.assertIn("docs.density: terse (project.toml)", out)
        self.assertIn("qa.level: full (rigor:full)", out)

    def test_bad_enum_is_check_error_and_falls_through(self):
        self.add({"project.toml": 'schema_version = 1\n[modes]\nrigor = "max"\n'})
        code, out, _ = self.run_cli("check")
        self.assertEqual(code, 1)
        self.assertIn("ERROR config", out)
        _, out, _ = self.run_cli("config", "--keys", "rigor")
        self.assertIn("rigor: minimal (default)", out)

    def test_set_keeps_comments_and_reads_back(self):
        self.add({"project.toml": 'schema_version = 1\n\n# my comment\n[modes]\nrigor = "minimal"  # inline\n'})
        code, out, _ = self.run_cli("config", "--set", "modes.rigor=standard")
        self.assertEqual(code, 0)
        self.assertIn("rigor: standard (project.toml)", out)
        text = open(os.path.join(self.root, "project.toml"), encoding="utf-8").read()
        self.assertIn("# my comment", text)
        self.assertIn('rigor = "standard"  # inline', text)

    def test_set_creates_missing_table(self):
        self.add({"project.toml": "schema_version = 1\n"})
        code, out, _ = self.run_cli("config", "--set", "review_mode=full")
        self.assertEqual(code, 0)
        self.assertIn("review_mode: full (project.toml)", out)

    def test_set_local_creates_file(self):
        self.add({"project.toml": BASE_TOML})
        code, out, _ = self.run_cli("config", "--set", "automation=guided", "--local")
        self.assertEqual(code, 0)
        self.assertIn("automation: guided (project.local.toml)", out)

    def test_set_rejects_bad_enum_and_list_key(self):
        self.add({"project.toml": BASE_TOML})
        code, _, err = self.run_cli("config", "--set", "modes.rigor=max")
        self.assertEqual(code, 2)
        self.assertIn("invalid value", err)
        code, _, err = self.run_cli("config", "--set", "modes.automation_always_ask=a")
        self.assertEqual(code, 2)
        self.assertIn("by hand", err)

    def test_derived_lines(self):
        self.add({"project.toml": 'schema_version = 1\n[testing.strict]\nintegration = false\n'})
        _, out, _ = self.run_cli("config", "--keys", "gate_level,review_gate")
        self.assertIn("integration=advisory(project.toml)", out)
        self.assertIn("visual=blocking(default)", out)
        self.assertIn("review_gate: skill-gates=skip phase-gates=skip", out)

    def test_json(self):
        self.add({"project.toml": BASE_TOML})
        _, out, _ = self.run_cli("config", "--keys", "rigor", "--json")
        self.assertIn('"source": "project.toml"', out)

    def test_unreadable_config_exits_2(self):
        self.add({"project.toml": "this is = = not toml"})
        code, _, err = self.run_cli("config")
        self.assertEqual(code, 2)
        self.assertIn("studio:", err)


class TomlEditTest(unittest.TestCase):
    def test_nested_table_and_insert(self):
        from gamestudio import toml_edit
        out = toml_edit.set_value('a = 1\n[testing.strict]\nlogic = true\n', "testing.strict.ui", False)
        self.assertIn("ui = false", out)
        with self.assertRaises(toml_edit.TomlEditError):
            toml_edit.set_value('[a]\nk = [1, 2]\n', "a.k", "x")


if __name__ == "__main__":
    unittest.main()
