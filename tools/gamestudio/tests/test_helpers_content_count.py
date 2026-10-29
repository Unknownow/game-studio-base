import unittest

from ._util import RepoCase

ENTITIES = """entities:
  - name: Goblin
    status: active
    source: design/gdd/goblin.md
  - name: Troll
    status: deprecated
    source: design/gdd/troll.md
items:
  - name: Potion
    source: design/gdd/potion.md
"""


class ContentCountTest(RepoCase):
    def test_band(self):
        code, out, _ = self.run_cli("content-count", "band", "99", "200")
        self.assertEqual(out.strip(), "band\t99/200\tEARLY\t49.5\t0 < found/specified < 50%")
        self.assertIn("COMPLETE", self.run_cli("content-count", "band", "5", "4")[1])
        self.assertIn("NOT STARTED", self.run_cli("content-count", "band", "0", "4")[1])
        self.assertIn("band\t0/0\t-\t-", self.run_cli("content-count", "band", "0", "0")[1])
        self.assertEqual(self.run_cli("content-count", "band", "x", "4")[0], 2)

    def test_gap_table(self):
        rows = "combat\tenemies\t10\t5\nui\tlevels\t2\t3\nbad\tquests\tn/a\t1\n"
        code, out, _ = self.run_cli("content-count", "gap", stdin=rows)
        self.assertEqual(code, 0)
        self.assertIn("rows\t2\t3", out)
        self.assertIn("total_specified\t12", out)
        self.assertIn("total_gap\t4", out)
        self.assertIn("unbuilt\t5", out)
        self.assertIn("ROW\tcombat\tenemies\t10\t5\t5\t50.0\tIN PROGRESS\tno", out)
        self.assertIn("EXCLUDED\tbad\tquests\tspecified is not a number: n/a", out)
        self.assertEqual(self.run_cli("content-count", "gap", stdin="")[0], 3)

    def test_registry(self):
        self.add({"design/registry/entities.yaml": ENTITIES})
        code, out, _ = self.run_cli("content-count", "registry")
        self.assertEqual(code, 0)
        self.assertIn("planned\tentities\t1", out)
        self.assertIn("planned\titems\t1", out)
        self.assertIn("deprecated_skipped\t1", out)
        self.assertIn("no_status\t1", out)
        self.assertIn("PLANNED\tentities\tGoblin\tdesign/gdd/goblin.md", out)
        self.assertIn("SKIPPED\tentities\tTroll\tdesign/gdd/troll.md\tdeprecated", out)

    def test_found_neutral_and_unity(self):
        self.add({"Assets/data/enemies/orc.json": "{}", "Assets/data/items/sword.json": "{}", "Assets/data/levels/one.json": "{}"})
        code, out, _ = self.run_cli("content-count", "found")
        self.assertEqual(code, 0)
        self.assertIn("engine\tnone\tdefault", out)
        self.assertIn("found\tcharacters\t1", out)
        self.assertIn("found\tlevels\t1", out)

    def test_found_legacy_lowercase_root(self):
        self.add({"assets/data/enemies/orc.json": "{}"})
        code, out, err = self.run_cli("content-count", "found")
        self.assertEqual(code, 0)
        self.assertIn("root\tassets\tpresent", out)
        self.assertIn("found\tcharacters\t1", out)
        self.assertIn("old asset root", err)

    def test_found_unity(self):
        self.add({"Assets/Prefabs/Enemies/Orc.prefab": "x", "Assets/Scenes/Levels/Main.unity": "x"})
        code, out, _ = self.run_cli("content-count", "found", "--engine", "unity", "--files")
        self.assertIn("found	characters	1", out)
        self.assertIn("found	levels	1", out)
        self.assertIn("FILE	levels	Assets/Scenes/Levels/Main.unity", out)

    def test_found_unsupported_engine(self):
        code, _, err = self.run_cli("content-count", "found", "--engine", "unreal")
        self.assertEqual(code, 2)
        self.assertIn("use unity or none", err)
