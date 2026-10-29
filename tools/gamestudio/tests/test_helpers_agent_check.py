import unittest

from ._util import RepoCase

ROLE = """---
name: {name}
description: "{desc}"
tier: standard
can: [{can}]
memory: true
skills: [{skills}]
---

**Allowed actions:** read files.

{body}
"""


class AgentCheckTest(RepoCase):
    def role(self, name, desc="Plans sprints and tracks risk", can="read", skills="", body="Plan things."):
        self.add({"roles/%s.md" % name: ROLE.format(name=name, desc=desc, can=can, skills=skills, body=body)})

    def test_can_mismatch_and_asks_user(self):
        self.role("tester", can="read", body="Run `git status` first.\nThen ask the user for approval before you go on.")
        code, out, _ = self.run_cli("agent-check")
        self.assertEqual(code, 0)
        self.assertIn("AGENTS: 1", out)
        self.assertIn("AGENT: tester frontmatter=ok tier=standard memory=true", out)
        self.assertIn("NOTE: can-mismatch can: lacks shell but line", out)
        self.assertIn("NOTE: asks-user line", out)
        self.assertIn("DELEGATION: no-delegations found in the files read", out)

    def test_preload_missing_and_delegation_block(self):
        self.role("lead", skills="ghost, off", desc="Leads the code")
        self.role("helper-bot", desc="Writes fixtures")
        self.add({".agents/skills/off/SKILL.md": "---\nname: off\ndescription: d\ndisable-model-invocation: true\n---\n",
                  ".agents/skills/work/SKILL.md": "---\nname: work\ndescription: d\n---\n\n## Phase 1\n\nAct as `helper-bot` (read `roles/helper-bot.md`) to write the fixtures. Return the path. Do not touch other files.\n"})
        code, out, _ = self.run_cli("agent-check")
        self.assertIn("preload-missing skills: lists ghost, which is not a skill", out)
        self.assertIn("preload-missing skills: lists off, which sets disable-model-invocation: true", out)
        self.assertIn('DELEGATION: work .agents/skills/work/SKILL.md:6 "Phase 1" agents=helper-bot', out)
        code, out, _ = self.run_cli("agent-check", "--skill", "work")
        self.assertNotIn("AGENT:", out)
        self.assertIn("DELEGATION: work", out)

    def test_overlap_and_missing_folder(self):
        self.role("a-one", desc="balance combat economy progression curves tuning")
        self.role("b-two", desc="balance combat economy progression curves rewards")
        self.role("c-three", desc="audio pipeline middleware")
        code, out, _ = self.run_cli("agent-check")
        self.assertIn("OVERLAP: a-one b-two jaccard=", out)
        code, _, err = self.run_cli("agent-check", root=self.root + "/nowhere")
        self.assertEqual(code, 1)
