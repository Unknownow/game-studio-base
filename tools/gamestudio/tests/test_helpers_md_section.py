import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]

import os

DOC = """# Title

> **Status**: Ready
> **Type**: Logic

## One

text here

```
## not a heading
```

### Sub

more

## Two

<!-- only a comment -->

## Three

[TBD]
"""


class MdSectionTest(RepoCase):
    def doc(self, text=DOC):
        self.add({"d.md": text})
        return os.path.join(self.root, "d.md")

    def test_list_skips_fences(self):
        _, out, _ = self.run_cli("md-section", "list", self.doc())
        r = rows(out)
        self.assertEqual(r[0], ["headings", "5"])
        self.assertEqual([x[3] for x in r[1:]], ["Title", "One", "Sub", "Two", "Three"])

    def test_status(self):
        _, out, _ = self.run_cli("md-section", "status", self.doc(), "One", "Two", "Three", "Nope")
        self.assertIn("COMPLETE\t", out)
        self.assertIn("EMPTY\t", out)
        self.assertIn("PLACEHOLDER\t", out)
        self.assertIn("NOT_FOUND\t-\tNope", out)
        self.assertIn("not_found\t1", out)

    def test_extract_includes_subsection_and_body_flag(self):
        p = self.doc()
        _, out, _ = self.run_cli("md-section", "extract", p, "One")
        self.assertIn("### Sub", out)
        self.assertNotIn("## Two", out)
        _, out, _ = self.run_cli("md-section", "extract", p, "One", "--body")
        self.assertNotIn("## One\n", out)

    def test_heading_match_ignores_case_number_and_emphasis(self):
        p = self.doc("## 1. **Overview**\n\nx\n")
        code, out, _ = self.run_cli("md-section", "extract", p, "overview")
        self.assertEqual(code, 0)

    def test_not_found_3_and_ambiguous_4(self):
        p = self.doc("## A\n\nx\n\n## A\n\ny\n")
        self.assertEqual(self.run_cli("md-section", "extract", p, "Zzz")[0], 3)
        self.assertEqual(self.run_cli("md-section", "extract", p, "A")[0], 4)

    def test_replace(self):
        p = self.doc()
        code, out, _ = self.run_cli("md-section", "replace", p, "Two", stdin="new body\n")
        self.assertEqual(code, 0)
        self.assertIn("file\t", out)
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("## Two\n\nnew body\n\n## Three", text)
        self.assertNotIn("only a comment", text)

    def test_replace_without_stdin_is_usage_error(self):
        p = self.doc()
        self.assertEqual(self.run_cli("md-section", "replace", p, "Two", stdin="")[0], 2)

    def test_set_field_and_add_after(self):
        p = self.doc()
        code, out, _ = self.run_cli("md-section", "set-field", p, "Status", "Done")
        self.assertIn("\tset", out)
        code, out, _ = self.run_cli("md-section", "set-field", p, "Last Updated", "2026-01-01", "--after", "Status")
        self.assertIn("\tadded", out)
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("> **Status**: Done\n> **Last Updated**: 2026-01-01\n", text)
        code, out, _ = self.run_cli("md-section", "set-field", p, "Status", "Done")
        self.assertIn("\tunchanged", out)

    def test_set_field_missing_exits_3(self):
        p = self.doc()
        self.assertEqual(self.run_cli("md-section", "set-field", p, "Nope", "x")[0], 3)

    def test_insert_before(self):
        p = self.doc()
        code, _, _ = self.run_cli("md-section", "insert-before", p, "Two", stdin="inserted\n")
        self.assertEqual(code, 0)
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("more\n\ninserted\n\n## Two", text)
        code, out, _ = self.run_cli("md-section", "insert-before", p, "Two", stdin="inserted\n")
        self.assertIn("unchanged", out)

    def test_crlf_kept(self):
        p = os.path.join(self.root, "c.md")
        with open(p, "wb") as fh:
            fh.write(b"## A\r\n\r\nx\r\n")
        self.run_cli("md-section", "replace", p, "A", stdin="y\n")
        with open(p, "rb") as fh:
            self.assertEqual(fh.read(), b"## A\r\n\r\ny\r\n")


if __name__ == "__main__":
    unittest.main()
