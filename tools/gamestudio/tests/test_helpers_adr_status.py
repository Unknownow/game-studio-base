import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]


TEMPLATE = """# ADR-NNNN: [Title]

## Status

[Proposed | Accepted]

## Date

[YYYY-MM-DD]

## Last Verified

[YYYY-MM-DD]

## Decision

[text]

## ADR Dependencies

| **Depends On** | [ADR-NNNN] |
"""

ADR = """# ADR-0003: Use ECS

## Status

Accepted

## Date

2026-02-03

## Decision

Use it.

## ADR Dependencies

| **Depends On** | ADR-0001, ADR-0003 |
"""


class AdrStatusTest(RepoCase):
    def setUp(self):
        RepoCase.setUp(self)
        self.with_toml({"templates/architecture-decision-record.md": TEMPLATE,
                        "docs/architecture/adr-0003-ecs.md": ADR,
                        "docs/architecture/adr-0004-x.md": "# ADR-0004\n\n## Status\n\n[Proposed | Accepted]\n"})

    def test_counts_and_row(self):
        code, out, _ = self.run_cli("adr-status")
        self.assertEqual(code, 0)
        r = rows(out)
        self.assertEqual(r[0][:2], ["adrs", "2"])
        self.assertEqual(r[1][:2], ["template_sections", "5"])
        d = {x[0]: x[1] for x in r[2:9]}
        self.assertEqual((d["accepted"], d["unfilled"]), ("1", "1"))
        row = [x for x in r if x[0] == "ADR" and x[1] == "adr-0003"][0]
        # ADR id path status layer date last_verified version depends_on superseded_by missing unfilled
        self.assertEqual(row[3], "Accepted")
        self.assertEqual(row[5:8], ["2026-02-03", "UNFILLED" if False else "-", "2026-02-03"])
        self.assertEqual(row[8], "adr-0001")
        self.assertEqual(row[10], "Last Verified")

    def test_lookup_by_id_and_not_found(self):
        code, out, _ = self.run_cli("adr-status", "ADR-0003", "0004", "adr-0099")
        self.assertEqual(code, 3)
        self.assertIn("NOT_FOUND\tadr-0099", out)
        self.assertEqual(rows(out)[0][1], "2")


if __name__ == "__main__":
    unittest.main()
