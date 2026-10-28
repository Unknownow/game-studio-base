import json
import os
import unittest

from ._util import RepoCase


ROLE = "---\nname: designer\ndescription: \"Designs things\"\ntier: strong\ncan: [read, write, web]\nmemory: true\nskills: [alpha]\n---\n\nYou design.\n"


def skill(name):
    return {".agents/skills/%s/SKILL.md" % name: "---\nname: %s\ndescription: x\n---\n1. s\n" % name,
            ".agents/skills/%s/references/r.md" % name: "ref\n"}


class ClaudeSyncTest(RepoCase):
    def read(self, rel):
        with open(os.path.join(self.root, rel), encoding="utf-8") as fh:
            return fh.read()

    def test_agent_file_mapping(self):
        files = {"roles/designer.md": ROLE}
        files.update(skill("alpha"))
        self.with_toml(files)
        code, out, _ = self.run_cli("claude-sync")
        self.assertEqual(code, 0)
        text = self.read(".claude/agents/designer.md")
        self.assertIn("tools: Read, Glob, Grep, Write, Edit, WebSearch", text)
        self.assertIn("disallowedTools: Bash", text)
        self.assertIn("model: opus", text)
        self.assertIn("maxTurns: 30", text)
        self.assertIn("memory: project", text)
        self.assertIn("  - alpha", text)
        self.assertTrue(text.rstrip().endswith("You design."))

    def test_skills_copied_and_stale_removed(self):
        files = skill("alpha")
        files.update(skill("beta"))
        self.with_toml(files)
        self.run_cli("claude-sync")
        self.assertTrue(os.path.isfile(os.path.join(self.root, ".claude/skills/beta/references/r.md")))
        import shutil
        shutil.rmtree(os.path.join(self.root, ".agents/skills/beta"))
        self.run_cli("claude-sync")
        self.assertFalse(os.path.exists(os.path.join(self.root, ".claude/skills/beta")))
        self.assertTrue(os.path.exists(os.path.join(self.root, ".claude/skills/alpha")))

    def test_settings_generated(self):
        self.with_toml()
        self.run_cli("claude-sync")
        data = json.loads(self.read(".claude/settings.json"))
        self.assertEqual(data["_generatedBy"], "tools/studio.py claude-sync")
        self.assertEqual(len(data["permissions"]["deny"]), 130)
        self.assertIn("claude-hook pre-bash", json.dumps(data["hooks"]["PreToolUse"]))
        self.assertIn("studio.py status", json.dumps(data["hooks"]["SessionStart"]))

    def test_user_owned_settings_untouched(self):
        self.with_toml({".claude/settings.json": '{"mine": true}'})
        code, out, _ = self.run_cli("claude-sync")
        self.assertEqual(code, 0)
        self.assertIn("WARN claude-sync: .claude/settings.json is user-owned", out)
        self.assertEqual(self.read(".claude/settings.json"), '{"mine": true}')

    def test_disabled(self):
        self.add({"project.toml": "schema_version = 1\n[claude]\nsync = false\n", "roles/designer.md": ROLE})
        code, out, _ = self.run_cli("claude-sync")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(os.path.join(self.root, ".claude")))

    def test_setup_sets_hooks_path(self):
        self.with_toml()
        self.git_init()
        code, out, _ = self.run_cli("setup")
        self.assertEqual(code, 0)
        self.assertIn("core.hooksPath = hooks", out)
        from ._util import git
        self.assertEqual(git(self.root, "config", "core.hooksPath").stdout.strip(), "hooks")
        self.assertEqual(self.run_cli("setup")[0], 0)  # idempotent


if __name__ == "__main__":
    unittest.main()
