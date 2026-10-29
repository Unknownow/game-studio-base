import unittest

from ._util import RepoCase


def junit(results):
    cases = ""
    for name, r in results:
        inner = {"P": "", "F": "<failure message='x'/>", "S": "<skipped/>"}[r]
        cases += "<testcase classname='Suite' name='%s'>%s</testcase>\n" % (name, inner)
    return "<testsuite>\n%s</testsuite>\n" % cases


def nunit(results):
    cases = ""
    for name, r in results:
        res = {"P": "Passed", "F": "Failed", "S": "Skipped"}[r]
        cases += "<test-case name='%s' fullname='Suite.%s' result='%s'/>\n" % (name, name, res)
    return "<test-run>\n%s</test-run>\n" % cases


RUNS = [[("a", "P"), ("b", "F")], [("a", "P"), ("b", "P")], [("a", "P"), ("b", "F")]]


class FlakyStatsTest(RepoCase):
    def counts(self, out):
        lines = out.splitlines()
        return [l for l in lines if l.startswith(("runs\t", "tests\t", "clean\t", "flaky\t", "tier\tmoderate", "tier\thigh", "TEST\t"))]

    def test_junit_and_nunit_agree(self):
        self.add({"j/1.xml": junit(RUNS[0]), "j/2.xml": junit(RUNS[1]), "j/3.xml": junit(RUNS[2]),
                  "n/1.xml": nunit(RUNS[0]), "n/2.xml": nunit(RUNS[1]), "n/3.xml": nunit(RUNS[2])})
        code, jout, _ = self.run_cli("flaky-stats", "j/1.xml", "j/2.xml", "j/3.xml")
        self.assertEqual(code, 0)
        code, nout, _ = self.run_cli("flaky-stats", "n/1.xml", "n/2.xml", "n/3.xml")
        self.assertEqual(code, 0)
        self.assertIn("flaky\t1\ta pass and a fail in the counted results", jout)
        self.assertIn("tier\thigh\t1\tfail_pct > 25", jout)
        self.assertIn("TEST	Suite.b	3	1	2	0	66.6	FPF	yes	high	fail_pct > 25", jout)
        self.assertEqual([l.replace("Suite.", "") for l in self.counts(jout)], [l.replace("Suite.", "") for l in self.counts(nout)])

    def test_text_format_and_runs(self):
        self.add({"t/1.log": "[PASSED] test_a\n[FAILED] test_b\n", "t/2.log": "[PASSED] test_a\n[PASSED] test_b\n"})
        code, out, _ = self.run_cli("flaky-stats", "--runs", "t/1.log", "t/2.log")
        self.assertEqual(code, 0)
        self.assertIn("RUN\t1\tt/1.log\ttext\t2\t1\t1\t0\t0", out)
        self.assertIn("tier\tsuspected\t1\tflaky, fewer than 3 results", out)
        self.assertIn("data_note\tfewer than 5 runs", out)

    def test_errors(self):
        code, _, err = self.run_cli("flaky-stats", "--format", "unreal")
        self.assertEqual(code, 2)
        self.assertIn("auto, junit, nunit or text", err)
        self.assertEqual(self.run_cli("flaky-stats")[0], 3)
        self.assertEqual(self.run_cli("flaky-stats", "missing.xml")[0], 3)
        self.add({"empty.log": "nothing here\n"})
        self.assertEqual(self.run_cli("flaky-stats", "empty.log")[0], 4)
