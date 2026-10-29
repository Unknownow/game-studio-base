import json
import os
import unittest

from ._util import RepoCase, git, story


def skill(name="demo", desc="Does a thing. Use when asked.", extra=""):
    return {".agents/skills/%s/SKILL.md" % name: "---\nname: %s\ndescription: %s\n%s---\n\n1. Step one\n" % (name, json.dumps(desc), extra)}


class CheckTest(RepoCase):
    def check(self, *args):
        return self.run_cli("check", *args)

    def test_clean_repo_passes(self):
        self.with_toml()
        code, out, _ = self.check()
        self.assertEqual(code, 0)
        self.assertIn("check: 0 errors, 0 warnings", out)

    def test_config_missing_schema_version_fails(self):
        self.add({"project.toml": '[modes]\nrigor = "minimal"\n'})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("schema_version", out)

    def test_config_unknown_key_fails(self):
        self.add({"project.toml": "schema_version = 1\n[nope]\nx = 1\n"})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("unknown table or key", out)

    def test_story_sections(self):
        self.with_toml({"production/epics/core/story-001.md": story()})
        self.assertEqual(self.check()[0], 0)
        self.add({"production/epics/core/story-002.md": story().replace("> **Type**: Logic\n", "")})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("missing `> **Type**:` line", out)

    def test_story_bad_type(self):
        self.with_toml({"production/epics/core/story-001.md": story(type="Visual")})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("Type 'Visual' is not one of", out)

    def test_story_missing_section(self):
        self.with_toml({"production/epics/core/story-001.md": story().replace("## Test Evidence", "## Other")})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("## Test Evidence", out)

    def test_epic_and_readme_are_skipped(self):
        self.with_toml({"production/epics/core/EPIC.md": "# Epic\n", "production/epics/README.md": "x\n"})
        self.assertEqual(self.check()[0], 0)

    def test_data_json(self):
        self.with_toml({"assets/data/a.json": '{"a": 1}'})
        self.assertEqual(self.check()[0], 0)
        self.add({"assets/data/b.json": '{"a": 1,}'})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("ERROR data-json assets/data/b.json", out)

    def test_data_json_engine_globs(self):
        self.with_toml({"engine.toml": '[engine]\nname = "x"\ndata_globs = ["Content/**/*.json"]\n', "Content/a/b.json": "{"})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("data-json Content/a/b.json", out)

    def test_evidence_ui_needs_png(self):
        self.with_toml({"production/epics/core/story-001.md": story("Done", "UI")})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("ERROR evidence", out)
        self.add({"production/qa/evidence/story-001/a.png": b"\x89PNG"})
        self.assertEqual(self.check()[0], 0)

    def test_evidence_visual_needs_doc(self):
        self.with_toml({"production/epics/core/story-001.md": story("Done", "Visual/Feel"),
                        "production/qa/evidence/story-001/a.png": b"\x89PNG"})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("story-001-evidence.md", out)
        self.add({"production/qa/evidence/story-001-evidence.md": "signed off\n"})
        self.assertEqual(self.check()[0], 0)

    def test_evidence_not_needed_before_done(self):
        self.with_toml({"production/epics/core/story-001.md": story("In Progress", "UI")})
        self.assertEqual(self.check()[0], 0)

    def test_skill_frontmatter_ok(self):
        self.with_toml(skill())
        self.assertEqual(self.check()[0], 0)

    def test_skill_bad_name_and_folder(self):
        self.with_toml(skill("Dev_Story"))
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("skill-frontmatter", out)

    def test_skill_name_must_match_folder(self):
        self.with_toml({".agents/skills/a/SKILL.md": "---\nname: b\ndescription: x\n---\n1. s\n"})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("does not match folder", out)

    def test_skill_long_description(self):
        self.with_toml(skill(desc="x" * 1025))
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("1025 characters", out)

    def test_skill_extra_key(self):
        self.with_toml(skill(extra="allowed-tools: Read\n"))
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("allowed-tools", out)

    def test_skill_syntax_error_has_line(self):
        self.with_toml({".agents/skills/a/SKILL.md": "---\nname: a\ndescription: |\n  x\n---\n"})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("ERROR frontmatter-syntax .agents/skills/a/SKILL.md:3", out)

    def test_role_frontmatter(self):
        good = "---\nname: qa\ndescription: x\ntier: standard\ncan: [read, write]\nmemory: true\n---\nbody\n"
        self.with_toml({"roles/qa.md": good})
        self.assertEqual(self.check()[0], 0)
        self.add({"roles/bad.md": good.replace("name: qa", "name: bad").replace("standard", "max")})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("tier must be one of", out)

    def test_role_unknown_skill(self):
        self.with_toml({"roles/qa.md": "---\nname: qa\ndescription: x\ntier: inherit\ncan: [read]\nskills: [ghost]\n---\n"})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("skill 'ghost' does not exist", out)

    def test_rule_frontmatter(self):
        self.with_toml({"rules/a.md": '---\npaths: ["src/**"]\n---\nx\n'})
        self.assertEqual(self.check()[0], 0)
        self.add({"rules/b.md": '---\npaths: ["src/**"]\nextends: rules/missing.md\n---\nx\n'})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("extends target", out)
        self.add({"rules/c.md": "---\npaths: []\n---\nx\n"})
        self.assertIn("paths must be a non-empty list", self.check()[1])

    def test_engine_hooks(self):
        files = skill()
        files[".agents/skills/demo/SKILL.md"] += "\nEngine step `hook: demo/point` here.\n"
        self.with_toml(files)
        self.assertEqual(self.check()[0], 0)  # no ENGINE.md: skipped
        self.add({"ENGINE.md": "---\nengine: x\n---\n\n## hook: other/thing\n"})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("no `## hook: demo/point` section", out)
        self.assertIn("WARN engine-hooks ENGINE.md", out)
        self.add({"ENGINE.md": "---\nengine: x\n---\n\n## hook: demo/point\n"})
        self.assertEqual(self.check()[0], 0)

    def test_manifest_game_owned(self):
        self.with_toml({"files.manifest": "# m\nAGENTS.md\n"})
        self.assertEqual(self.check()[0], 0)
        self.add({"files.manifest": "# m\nAGENTS.md\ndesign/**\n"})
        code, out, _ = self.check()
        self.assertEqual(code, 1)
        self.assertIn("manifest-game-owned", out)

    def test_upstream_tag_mismatch_warns(self):
        self.with_toml({"UPSTREAM.toml": '[upstream]\ntag = "v1"\n', "UPSTREAM.unity.toml": '[upstream]\ntag = "v2"\n'})
        code, out, _ = self.check()
        self.assertEqual(code, 0)
        self.assertIn("WARN upstream-tag", out)

    def test_missing_engine_plugin_warns(self):
        self.add({"project.toml": 'schema_version = 1\n[engine]\nname = "bevy"\n'})
        code, out, _ = self.check()
        self.assertEqual(code, 0)
        self.assertIn("WARN engine-plugin-missing", out)

    def test_staged_checks_only_staged_files(self):
        self.with_toml({"production/epics/core/story-001.md": story(type="Visual")})
        self.git_init()
        git(self.root, "add", "project.toml")
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 0)
        git(self.root, "add", "production/epics/core/story-001.md")
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 1)
        self.assertIn("story-sections", out)

    def test_staged_reads_index_not_worktree(self):
        self.with_toml({"production/epics/core/story-001.md": story()})
        self.git_init()
        git(self.root, "add", "-A")
        self.add({"production/epics/core/story-001.md": story(type="Bogus")})
        self.assertEqual(self.check("--staged")[0], 0)

    def test_staged_todo_and_hardcoded_advice(self):
        self.add({"project.toml": 'schema_version = 1\n[engine]\nname = "x"\n', "engine.toml": '[engine]\nname = "x"\ncode_root = "src"\n',
                  "src/a.py": "# TODO fix\ndamage = 10\n"})
        self.git_init()
        git(self.root, "add", "-A")
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 0)
        self.assertIn("WARN hardcoded-values src/a.py", out)
        self.assertIn("WARN todo-format src/a.py", out)

    def test_staged_never_overwrite_epic(self):
        self.with_toml({"production/epics/core/EPIC.md": "# Epic\n"})
        self.git_init()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "x")
        self.add({"production/epics/core/EPIC.md": "# Epic changed\n"})
        git(self.root, "add", "-A")
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 0)
        self.assertIn("WARN never-overwrite", out)

    def test_staged_non_ascii_path_is_checked(self):
        self.with_toml({"production/epics/e/caf\u00e9.md": story().replace("> **Type**: Logic\n", "")})
        self.git_init()
        git(self.root, "add", "-A")
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 1)
        self.assertIn("story-sections", out)

    def test_staged_deletion_reruns_repo_wide_checks(self):
        files = skill("tech-debt")
        files["roles/lead.md"] = "---\nname: lead\ndescription: x\ntier: inherit\ncan: [read]\nskills: [tech-debt]\n---\n"
        self.with_toml(files)
        self.git_init()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "x")
        git(self.root, "rm", "-q", "-r", ".agents/skills/tech-debt")
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 1)
        self.assertIn("skill 'tech-debt' does not exist", out)


    def lead_with_skill(self):
        files = skill("tech-debt")
        files["roles/lead.md"] = "---\nname: lead\ndescription: x\ntier: inherit\ncan: [read]\nskills: [tech-debt]\n---\n"
        self.with_toml(files)
        self.git_init()
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "x")

    def test_staged_move_out_of_skills_reruns_role_check(self):
        self.lead_with_skill()
        os.makedirs(os.path.join(self.root, "archive"))
        git(self.root, "mv", ".agents/skills/tech-debt", "archive/tech-debt")
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 1)
        self.assertIn("skill 'tech-debt' does not exist", out)

    def test_staged_cached_removal_uses_index(self):
        self.lead_with_skill()
        git(self.root, "rm", "-q", "-r", "--cached", ".agents/skills/tech-debt")
        self.assertTrue(os.path.exists(os.path.join(self.root, ".agents/skills/tech-debt/SKILL.md")))
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 1)
        self.assertIn("skill 'tech-debt' does not exist", out)

    def test_staged_ignores_untracked_bad_role(self):
        self.lead_with_skill()
        self.add({"roles/bad.md": "---\nname: bad\ndescription: x\ntier: max\ncan: [read]\n---\n"})
        self.add(skill("tech-debt", desc="Changed description. Use when asked."))
        git(self.root, "add", ".agents/skills/tech-debt/SKILL.md")
        code, out, _ = self.check("--staged")
        self.assertEqual(code, 0, out)
        self.assertNotIn("bad.md", out)

    def test_skill_lint_advice(self):
        self.with_toml({".agents/skills/plain/SKILL.md": "---\nname: plain\ndescription: Does a thing.\n---\n\nJust prose with no steps.\n"})
        code, out, _ = self.check()
        self.assertEqual(code, 0)
        self.assertIn("WARN skill-lint .agents/skills/plain/SKILL.md: no_steps", out)

    def test_skill_lint_accepts_phase_headings(self):
        self.with_toml({".agents/skills/phased/SKILL.md": "---\nname: phased\ndescription: Does a thing.\n---\n\n## Phase 1: A\n\ntext\n\n## Phase 2: B\n\ntext\n"})
        code, out, _ = self.check()
        self.assertEqual(code, 0)
        self.assertNotIn("skill-lint", out)


if __name__ == "__main__":
    unittest.main()
