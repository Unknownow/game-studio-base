import unittest

from ._util import RepoCase

REGISTER = """# Tech Debt Register

| ID | Category | Description | Files | Effort | Impact | Priority | Status | Added | Sprint |
|----|----------|-------------|-------|--------|--------|----------|--------|-------|--------|
| TD-001 | Code Quality Debt | messy | `src/a.py`, src/b.py | S | High | P1 | Open | 2026-01-01 | 1 |
| TD-002 | Test | no tests | src/c.py | XL | Low | P3 | Open | 2026-02-01 | 2 |
| TD-003 | Architecture | old | src/a.py | M | Med | P2 | Resolved 2026-02-10 | 2026-01-05 | 1 |
| TD-004 | Dependency | pin | - | - | High | P2 | Open | 2026-02-20 | 3 |
| TD-005 | broken row |
"""


class DebtRegisterTest(RepoCase):
    def setUp(self):
        RepoCase.setUp(self)
        self.add({"docs/tech-debt-register.md": REGISTER})

    def test_score_pair_rounds_half_up(self):
        self.assertEqual(self.run_cli("debt-register", "score", "Low", "XL")[1].strip(), "score\t0.3\tLow/XL\t1/4")
        self.assertEqual(self.run_cli("debt-register", "score", "high", "xl")[1].strip(), "score\t0.8\tHigh/XL\t3/4")
        self.assertIn("effort not judged", self.run_cli("debt-register", "score", "High", "-")[1])
        self.assertEqual(self.run_cli("debt-register", "score", "Huge", "S")[0], 2)

    def test_score_register_order(self):
        code, out, _ = self.run_cli("debt-register", "score")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertIn("items\t4", lines)
        self.assertIn("malformed\t1", lines)
        rows = [l.split("\t") for l in lines if l.startswith("ROW")]
        self.assertEqual(rows[0][1:4], ["1", "TD-001", "3.0"])
        self.assertEqual(rows[-1][2], "TD-004")
        self.assertEqual(rows[-1][1], "-")

    def test_stats_and_match(self):
        code, out, _ = self.run_cli("debt-register", "stats", "--today", "2026-03-01", "--since", "2026-02-01", "--older-than", "30")
        self.assertEqual(code, 0)
        self.assertIn("open\t3", out)
        self.assertIn("resolved\t1", out)
        self.assertIn("added_in_window\t2", out)
        self.assertIn("resolved_in_window\t1", out)
        self.assertIn("older_than\t30\t1", out)
        self.assertIn("category\tCode Quality\t1\t1\t0\t0\t0\t0\t0", out)
        self.assertIn("OPEN\tTD-001\tCode Quality\tS\tHigh\tP1\t2026-01-01\t59\t1\tyes", out)
        code, out, _ = self.run_cli("debt-register", "match", "--file", "./src/a.py")
        self.assertIn("matches\t1\tfile=src/a.py category=any", out)
        self.assertIn("MATCH\tTD-001", out)
        self.assertEqual(self.run_cli("debt-register", "match")[0], 2)

    def test_next_id_and_missing_register(self):
        code, out, _ = self.run_cli("debt-register", "next-id")
        self.assertEqual(out.strip(), "next\ttd\t-\tTD-006\tTD-005\t5")
        code, out, _ = self.run_cli("debt-register", "stats", "--register", "nope.md")
        self.assertEqual(code, 3)
        self.assertEqual(self.run_cli("debt-register", "stats", "--since", "2026-02-01", "--until", "2026-01-01")[0], 2)
