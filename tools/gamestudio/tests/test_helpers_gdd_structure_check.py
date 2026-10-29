import unittest

from ._util import RepoCase

GDD = """# Combat

## Overview
text

## Player Fantasy
[To be designed]

## 3. Detailed Design
rules

### Sub
more

## Edge Cases
[To be designed]

## Acceptance Criteria
- [ ] one
"""


class GddStructureTest(RepoCase):
    def test_present_absent_and_placeholder(self):
        self.add({"design/gdd/combat.md": GDD, "design/gdd/systems-index.md": "# Index\n"})
        code, out, _ = self.run_cli("gdd-structure-check")
        self.assertEqual(code, 0)
        self.assertIn("combat.md PRESENT: Overview,Player Fantasy,Detailed Rules,Edge Cases,Acceptance Criteria", out)
        self.assertIn("combat.md ABSENT:  Formulas,Dependencies,Tuning Knobs", out)
        self.assertIn("combat.md PLACEHOLDER: Player Fantasy,Edge Cases", out)
        self.assertNotIn("systems-index.md", out)

    def test_one_file_and_missing_file(self):
        self.add({"design/gdd/combat.md": GDD})
        code, out, _ = self.run_cli("gdd-structure-check", "design/gdd/combat.md")
        self.assertEqual(code, 0)
        self.assertIn("combat.md PRESENT", out)
        code, _, err = self.run_cli("gdd-structure-check", "design/gdd/nope.md")
        self.assertEqual(code, 1)
        self.assertIn("Not found", err)

    def test_no_gdds(self):
        code, out, _ = self.run_cli("gdd-structure-check")
        self.assertEqual(code, 0)
        self.assertIn("No system GDDs found", out)
