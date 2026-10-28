import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]


class SetStageTest(RepoCase):
    def test_sets_and_reads_back(self):
        self.with_toml()
        code, out, _ = self.run_cli("set-stage", "Systems Design")
        self.assertEqual(code, 0)
        self.assertIn("project.toml\tinserted\t-", out)
        self.assertIn("stage_toml\tSystems Design\tproject.toml", out)
        code, out, _ = self.run_cli("set-stage", "Systems Design")
        self.assertIn("unchanged", out)

    def test_invalid_stage_exits_3_and_writes_nothing(self):
        self.with_toml()
        before = open(self.root + "/project.toml", encoding="utf-8").read()
        self.assertEqual(self.run_cli("set-stage", "Beta")[0], 3)
        self.assertEqual(open(self.root + "/project.toml", encoding="utf-8").read(), before)

    def test_dry_run(self):
        self.with_toml()
        code, out, _ = self.run_cli("set-stage", "Polish", "--dry-run")
        self.assertEqual(code, 0)
        self.assertNotIn("Polish", open(self.root + "/project.toml", encoding="utf-8").read())


class ConfigSetTest(RepoCase):
    def test_dry_run_rows(self):
        self.with_toml()
        code, out, _ = self.run_cli("config-set", "--dry-run", "modes.rigor", "standard")
        self.assertEqual(code, 0)
        r = [x[0] for x in rows(out)]
        self.assertEqual(r, ["file", "enum", "known", "shadow", "current", "edit"])

    def test_write_and_readback(self):
        self.with_toml()
        code, out, _ = self.run_cli("config-set", "modes.rigor=full")
        self.assertEqual(code, 0)
        self.assertIn("readback\tfull\tproject.toml", out)

    def test_invalid_enum_exits_3(self):
        self.with_toml()
        code, out, _ = self.run_cli("config-set", "modes.rigor", "max")
        self.assertEqual(code, 3)
        self.assertIn("enum\tinvalid", out)

    def test_shadow_row(self):
        self.with_toml({"project.local.toml": '[modes]\nrigor = "full"\n'})
        _, out, _ = self.run_cli("config-set", "--dry-run", "modes.rigor", "standard")
        self.assertIn("shadow\tyes\tfull", out)

    def test_local_write(self):
        self.with_toml()
        code, out, _ = self.run_cli("config-set", "--local", "automation", "autonomous")
        self.assertEqual(code, 0)
        self.assertIn("readback\tautonomous\tproject.local.toml", out)

    def test_unknown_key_exits_2(self):
        self.with_toml()
        self.assertEqual(self.run_cli("config-set", "nope.key", "x")[0], 2)

    def test_empty_value_is_usage_error(self):
        self.with_toml()
        self.assertEqual(self.run_cli("config-set", "modes.rigor=")[0], 2)


if __name__ == "__main__":
    unittest.main()
