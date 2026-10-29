import unittest

from ._util import RepoCase

SKILL = """---
name: demo
description: "Review the thing and give a PASS or FAIL verdict."
metadata:
  argument-hint: "[thing]"
---

# Demo

## Parse Arguments

1. Read the argument.

## Phase 1: Check

1. Check it. May I write the report to production/report.md?
Engine step `hook: demo/step`: if `ENGINE.md` exists, follow its section `## hook: demo/step`; otherwise ask the user how their engine does this and record the answer in `ENGINE.md` under that heading.

## Phase 2: Next Steps

Recommended next: run /other.
"""


class SkillLintTest(RepoCase):
    def test_valid_skill(self):
        self.add({".agents/skills/demo/SKILL.md": SKILL, ".agents/skills/other/SKILL.md": "---\nname: other\ndescription: x\n---\n"})
        code, out, _ = self.run_cli("skill-lint", "demo")
        self.assertEqual(code, 0)
        lines = out.splitlines()
        self.assertEqual(lines[0], "skills\t1\t.agents/skills")
        self.assertIn("check1\tdemo\tframontmatter=ok".replace("framontmatter", "frontmatter") + "\tmissing=-\tunknown=-\tname=match", lines)
        self.assertIn("check2\tdemo\tphases=2\th2=3\th2_total=3", lines)
        self.assertTrue(any(l.startswith("check3\tdemo\tverdicts=PASS:1,FAIL:1") for l in lines))
        self.assertTrue(any(l.startswith("check4\tdemo\tmay_i_write=1") for l in lines))
        self.assertIn("check5\tdemo\tlast_section=Phase 2: Next Steps\tskills_named=other\tnext_phrases=2/2", lines)
        self.assertIn("check6\tdemo\thooks=1\tmalformed=0", lines)
        self.assertIn("check7\tdemo\thint=[thing]\targs_section=Parse Arguments@10", lines)
        self.assertEqual(lines[-1], "checked\t1 of 1")

    def test_unknown_key_and_not_read(self):
        self.add({".agents/skills/bad/SKILL.md": "---\nname: bad\nmodel: x\ndescription: d\n---\ntext\n", ".agents/skills/empty/notes.md": "x"})
        code, out, _ = self.run_cli("skill-lint", "all")
        self.assertEqual(code, 0)
        self.assertIn("unknown=model", out)
        self.assertIn("NOT_READ\tempty\tno SKILL.md", out)
        self.assertIn("checked\t1 of 2", out)

    def test_usage(self):
        self.assertEqual(self.run_cli("skill-lint")[0], 2)
        self.assertEqual(self.run_cli("skill-lint", "../x")[0], 2)
        self.add({".agents/skills/a/SKILL.md": "---\nname: a\ndescription: d\n---\n"})
        self.assertEqual(self.run_cli("skill-lint", "nope")[0], 3)
