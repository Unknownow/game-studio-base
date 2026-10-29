import unittest

from ._util import RepoCase

ENTITIES = """# registry
entities:
  - name: Goblin
    status: active
    source: design/gdd/goblin.md
  - name: Goblin
    status: weird
    source: design/gdd/missing.md
items: []
"""

TR = """requirements:
- id: TR-combat-001
  gdd: design/gdd/goblin.md
  status: active
- id: TR-combat-004
  gdd: design/gdd/goblin.md
  status: deprecated
- id: TR-ui-001
  gdd: design/gdd/goblin.md
  status: active
"""


class RegistryTest(RepoCase):
    def setUp(self):
        RepoCase.setUp(self)
        self.add({"design/registry/entities.yaml": ENTITIES, "docs/architecture/tr-registry.yaml": TR,
                  "design/gdd/goblin.md": "# G\n", "production/epics/core/story-001.md": "Covers TR-combat-001 and TR-combat-099\n"})

    def test_list_and_get(self):
        code, out, _ = self.run_cli("registry", "list", "tr", "--system", "combat")
        self.assertEqual(code, 0)
        self.assertIn("registry\ttr\tdocs/architecture/tr-registry.yaml\t3", out)
        self.assertIn("ENTRY\ttr\trequirements\tid\tTR-combat-001\tactive\tdesign/gdd/goblin.md\t2", out)
        self.assertNotIn("TR-ui-001", out)
        code, out, _ = self.run_cli("registry", "get", "TR-combat-004", "NOPE")
        self.assertEqual(code, 3)
        self.assertIn("NOT_FOUND\tNOPE", out)
        self.assertIn("  status: deprecated", out)

    def test_refs_and_slice(self):
        code, out, _ = self.run_cli("registry", "refs", "TR-combat-001")
        self.assertIn("REF\ttr\tTR-combat-001\tgdd\tdesign/gdd/goblin.md\t3", out)
        self.assertIn("REF\ttr\tTR-combat-001\tcited\tproduction/epics/core/story-001.md\t1", out)
        code, out, _ = self.run_cli("registry", "slice", "design/gdd/goblin.md")
        self.assertEqual(out.count("ENTRY\ttr"), 3)

    def test_validate_reports_rows(self):
        code, out, _ = self.run_cli("registry", "validate")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertIn("duplicate\t1", lines)
        self.assertIn("tr_unknown\t1", lines)
        self.assertIn("path_missing\t1", lines)
        self.assertIn("status\t1", lines)
        self.assertIn("TR_UNKNOWN\tTR-combat-099\tproduction/epics/core/story-001.md\t1", lines)
        self.assertTrue(any(l.startswith("STATUS\tentities\tGoblin\tweird\t") for l in lines))

    def test_next_id_variants(self):
        code, out, _ = self.run_cli("registry", "next-id", "tr", "combat")
        self.assertEqual(out.strip(), "next\ttr\tcombat\tTR-combat-005\tTR-combat-004\t2")
        self.add({"docs/architecture/adr-0003-x.md": "x", "production/qa/bugs/BUG-0007.md": "x"})
        self.assertEqual(self.run_cli("registry", "next-id", "adr")[1].strip(), "next\tadr\t-\tADR-0004\tADR-0003\t1")
        self.assertEqual(self.run_cli("registry", "next-id", "bug")[1].strip(), "next\tbug\t-\tBUG-0008\tBUG-0007\t1")
        self.assertEqual(self.run_cli("registry", "next-id", "sprint")[1].strip(), "next\tsprint\t-\tsprint-001\t-\t0")
        self.assertEqual(self.run_cli("registry", "next-id", "nope")[0], 2)

    def test_bad_layout_is_a_row_not_a_traceback(self):
        self.add({"docs/architecture/tr-registry.yaml": "requirements:\n- id: TR-a-001\n  note: x: y\n  \tbad\n"})
        code, out, err = self.run_cli("registry", "list", "tr")
        self.assertEqual(code, 4)
        self.assertIn("registry\ttr\tdocs/architecture/tr-registry.yaml\tlayout", out)
        self.assertIn("LAYOUT\ttr\t", out)
        self.assertNotIn("Traceback", err)
        code, out, _ = self.run_cli("registry", "validate")
        self.assertEqual(code, 0)
        self.assertIn("layout\t", out)

    def test_compare(self):
        self.add({"old.yaml": TR, "new.yaml": TR.replace("- id: TR-ui-001\n  gdd: design/gdd/goblin.md\n  status: active\n", "")})
        code, out, _ = self.run_cli("registry", "compare", "tr", self.root + "/old.yaml", self.root + "/new.yaml")
        self.assertEqual(code, 0)
        self.assertIn("removed\t1", out)
        self.assertIn("REMOVED\ttr\trequirements\tTR-ui-001\t8", out)
