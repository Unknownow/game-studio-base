import unittest

from ._util import RepoCase

BUG = """# {id}

- **ID**: {id}
- **Title**: {title}
- **Severity**: {sev}
- **Status**: {status}
- **Reported**: {rep}
- **System**: {system}
"""


def bug(i, sev, status, rep="2026-03-01", system="combat", title="t"):
    return BUG.format(id="BUG-%04d" % i, sev=sev, status=status, rep=rep, system=system, title=title)


class BugStatsTest(RepoCase):
    def test_counts_and_oldest(self):
        self.add({"production/qa/bugs/BUG-0001.md": bug(1, "S1 - Critical", "Open"),
                  "production/qa/bugs/BUG-0002.md": bug(2, "S3", "Verified Fixed"),
                  "production/qa/bugs/BUG-0003.md": bug(3, "[S1-S4]", "In Progress", "2026-03-05", "ui"),
                  "production/qa/bugs/bug-triage-2026.md": "# triage\n"})
        code, out, _ = self.run_cli("bug-stats", "--today", "2026-03-11")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("bugs\t3\t"))
        for want in ("open\t2\tstatus other than Closed or Verified Fixed", "closed\t1", "open_s1\t1", "open_unrated\t1",
                     "status\tOpen\t1", "system\tcombat\t1\t1", "oldest_open\tBUG-0001\t10"):
            self.assertIn(want, lines)
        self.assertTrue(any(l.startswith("BUG\tBUG-0001\tproduction/qa/bugs/BUG-0001.md\tS1\t-\tOPEN") for l in lines))

    def test_no_bugs_and_usage(self):
        code, out, _ = self.run_cli("bug-stats")
        self.assertEqual(code, 0)
        self.assertIn("bugs\t0", out)
        self.assertEqual(self.run_cli("bug-stats", "--today", "tomorrow")[0], 2)
