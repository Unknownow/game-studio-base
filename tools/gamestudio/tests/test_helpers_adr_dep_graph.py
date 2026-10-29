import unittest

from ._util import RepoCase


def adr(deps):
    return "# ADR\n\n## ADR Dependencies\n\n| | |\n|---|---|\n| **Depends On** | %s |\n" % deps


class AdrDepGraphTest(RepoCase):
    def test_order_and_edges(self):
        self.add({"docs/architecture/adr-0001-a.md": adr("None"), "docs/architecture/adr-0002-b.md": adr("ADR-0001"),
                  "docs/architecture/adr-0003-c.md": adr("ADR-0002, ADR-0001")})
        code, out, _ = self.run_cli("adr-dep-graph")
        self.assertEqual(code, 0)
        self.assertIn("ADRS: 3", out)
        self.assertIn("  adr-0002 -> adr-0001", out)
        self.assertIn("ORDER: adr-0001, adr-0002, adr-0003", out)
        self.assertNotIn("CYCLE", out)

    def test_cycle_and_blocked(self):
        self.add({"docs/architecture/adr-0001-a.md": adr("ADR-0002"), "docs/architecture/adr-0002-b.md": adr("ADR-0001"),
                  "docs/architecture/adr-0003-c.md": adr("ADR-0001"), "docs/architecture/adr-0004-d.md": "# no section\n",
                  "docs/architecture/adr-0005-e.md": adr("[ADR-NNNN or None]")})
        code, out, _ = self.run_cli("adr-dep-graph")
        self.assertIn("CYCLE: adr-0001 -> adr-0002", out)
        self.assertIn("CYCLE: adr-0002 -> adr-0001", out)
        self.assertIn("BLOCKED_BY_CYCLE: adr-0003", out)
        self.assertIn("NO_DEPS_SECTION: adr-0004", out)
        self.assertIn("UNFILLED_DEPS: adr-0005", out)
        self.assertIn("ORDER: adr-0004, adr-0005", out)

    def test_no_adrs(self):
        code, out, _ = self.run_cli("adr-dep-graph")
        self.assertEqual(code, 0)
        self.assertIn("ADRS: 0", out)
