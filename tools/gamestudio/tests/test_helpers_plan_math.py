import unittest

from ._util import RepoCase


class PlanMathTest(RepoCase):
    def test_days_and_bad_date(self):
        code, out, _ = self.run_cli("plan-math", "days", "2026-01-30", "2026-02-02")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "days\t3\t2026-01-30..2026-02-02")
        code, _, err = self.run_cli("plan-math", "days", "2026-02-29", "2026-03-01")
        self.assertEqual(code, 2)
        self.assertIn("real YYYY-MM-DD", err)

    def test_pct_rounds_half_up(self):
        code, out, _ = self.run_cli("plan-math", "pct", "23", "40")
        self.assertEqual(out.strip(), "pct\t58\t23/40")
        code, out, _ = self.run_cli("plan-math", "pct", "1", "8", "--places", "1")
        self.assertEqual(out.strip(), "pct\t12.5\t1/8")
        code, out, _ = self.run_cli("plan-math", "pct", "3", "0")
        self.assertEqual(out.strip(), "pct\t-\tzero denominator")

    def test_sprint_lookup(self):
        self.add({"production/sprints/sprint-2.md": "x", "production/sprints/sprint-10.md": "x",
                  "production/sprints/sprint-2-retrospective.md": "x"})
        code, out, _ = self.run_cli("plan-math", "sprint", "latest")
        self.assertEqual(out.strip(), "sprint\t10\tproduction/sprints/sprint-10.md")
        code, out, _ = self.run_cli("plan-math", "sprint", "sprint-02")
        self.assertEqual(out.strip(), "sprint\t2\tproduction/sprints/sprint-2.md")
        code, _, _ = self.run_cli("plan-math", "sprint", "7")
        self.assertEqual(code, 3)

    def test_progress(self):
        self.add({"production/sprint-status.yaml": "sprint: 1\nstart: 2026-03-01\nend: 2026-03-11\nupdated: 2026-03-05\n"
                  "stories:\n  - id: a\n    status: done\n    priority: must-have\n"
                  "  - id: b\n    status: in-progress\n    priority: must-have\n"})
        code, out, _ = self.run_cli("plan-math", "progress", "--today", "2026-03-06")
        self.assertEqual(code, 0)
        self.assertIn("days_total\t10", out)
        self.assertIn("time_pct\t50", out)
        self.assertIn("done_pct\t50", out)
        self.assertIn("band\tOn Track", out)
        self.assertIn("must_have_done\t1", out)
        self.assertIn("updated_days_ago\t1", out)

    def test_usage(self):
        self.assertEqual(self.run_cli("plan-math")[0], 2)
        self.assertEqual(self.run_cli("plan-math", "nope")[0], 2)
