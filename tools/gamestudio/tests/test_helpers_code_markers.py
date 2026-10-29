import unittest

from ._util import RepoCase


class CodeMarkersTest(RepoCase):
    def test_counts_and_rows(self):
        self.add({"src/a.py": "# TODO: one\nprint('x')\nx = 'placeholder'\n# FIXME and HACK\n",
                  "src/b.cs": "Debug.Log(1);\n" + "// filler\n" * 5,
                  "src/readme.txt": "TODO ignored\n"})
        code, out, _ = self.run_cli("code-markers", "--long", "4")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertTrue(lines[0].startswith("scanned_files\t2\t"))
        for want in ("todo\t1", "fixme\t1", "hack\t1", "debug\t2", "placeholder\t1", "long_files\t1\tmore than 4 lines"):
            self.assertIn(want, lines)
        self.assertIn("MARK\tTODO\tsrc/a.py\t1", lines)
        self.assertIn("DEBUG\tDebug.Log\tsrc/b.cs\t1", lines)
        self.assertIn("LONG\tsrc/b.cs\t6", lines)

    def test_exclude(self):
        self.add({"src/a.py": "# TODO\n", "src/gen/b.py": "# TODO\n"})
        code, out, _ = self.run_cli("code-markers", "--exclude", "src/gen/*")
        self.assertIn("todo\t1", out)

    def test_code_root_unset(self):
        code, out, err = self.run_cli("code-markers")
        self.assertEqual(code, 3)
        self.assertIn("scanned_files\t0\tcode_root unset", out)

    def test_usage(self):
        self.assertEqual(self.run_cli("code-markers", "--long", "x")[0], 2)
