import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]

import os


class ReviewReceiptsTest(RepoCase):
    def p(self, rel):
        return os.path.join(self.root, rel)

    def run_rr(self, *args):
        # run from the repo root so paths stay relative
        import subprocess, sys
        from ._util import STUDIO
        r = subprocess.run([sys.executable, STUDIO, "--root", self.root] + list(args), capture_output=True, text=True,
                           encoding="utf-8", cwd=self.root)
        return r.returncode, r.stdout, r.stderr

    def test_hash_matches_git_hash_object(self):
        self.add({"a.txt": "hello\n"})
        code, out, _ = self.run_rr("review-receipts", "hash", "a.txt")
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), "Reviewed-Content-Hash: a.txt ce013625030ba8dba906f756967f9e9ca394464a")

    def test_check_unchanged_changed_new_gone(self):
        self.add({"a.txt": "one\n", "b.txt": "two\n", "c.txt": "three\n"})
        _, stamp, _ = self.run_rr("review-receipts", "hash", "a.txt", "c.txt")
        self.add({"receipt.txt": stamp})
        self.add({"a.txt": "changed\n"})
        os.remove(self.p("c.txt"))
        code, out, _ = self.run_rr("review-receipts", "check", "receipt.txt", "a.txt", "b.txt", "nothere.txt")
        lines = out.splitlines()
        self.assertEqual(lines[0], "RECEIPT: receipt.txt")
        self.assertIn("CHANGED: a.txt", lines)
        self.assertIn("NEW: b.txt", lines)
        self.assertIn("GONE: c.txt", lines)
        self.assertNotIn("nothere", out)

    def test_check_unchanged_and_none_and_glob(self):
        self.add({"a.txt": "one\n"})
        _, stamp, _ = self.run_rr("review-receipts", "hash", "a.txt")
        self.add({"receipt.txt": stamp})
        self.assertIn("UNCHANGED: a.txt", self.run_rr("review-receipts", "check", "receipt.txt", "a.txt")[1])
        out = self.run_rr("review-receipts", "check", "missing-receipt.txt", "a.txt", "gdd/*.md")[1]
        self.assertIn("RECEIPT: NONE", out)
        self.assertIn("NEW: a.txt", out)
        self.assertIn("UNRESOLVED: gdd/*.md", out)

    def test_hash_unexpanded_glob_exits_2(self):
        self.add({"a.txt": "x\n"})
        self.assertEqual(self.run_rr("review-receipts", "hash", "zz/*.md")[0], 2)

    def test_sections_hash_and_check(self):
        self.add({"d.md": "pre\n\n## A\n\none\n\n## B\n\ntwo\n"})
        _, stamp, _ = self.run_rr("review-receipts", "sections-hash", "d.md")
        self.assertIn("d.md#__preamble__", stamp)
        self.assertIn("d.md#A", stamp)
        self.add({"receipt.txt": stamp, "d.md": "pre\n\n## A\n\nONE\n\n## C\n\nnew\n"})
        out = self.run_rr("review-receipts", "sections-check", "receipt.txt", "d.md")[1]
        self.assertIn("SECTION-UNCHANGED: __preamble__", out)
        self.assertIn("SECTION-CHANGED: A", out)
        self.assertIn("SECTION-NEW: C", out)
        self.assertIn("SECTION-REMOVED: B", out)


if __name__ == "__main__":
    unittest.main()
