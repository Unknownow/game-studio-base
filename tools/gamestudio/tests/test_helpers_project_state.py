import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]


class ProjectStateTest(RepoCase):
    def test_rows_and_phase(self):
        self.add({"project.toml": 'schema_version = 1\n[project]\nstage = "Concept"\n', "design/game-brief.md": "# b\n", "src/a.gd": "x\n"})
        code, out, _ = self.run_cli("project-state")
        self.assertEqual(code, 0)
        d = {r[0]: r for r in rows(out)}
        self.assertEqual([r[0] for r in rows(out)][:3], ["root", "engine", "code_root"])
        self.assertEqual(d["concept"][1], "design/game-brief.md")
        self.assertEqual(d["code_root"][1:], ["src", "detected"])
        self.assertEqual(d["source_files"][1], "1")
        self.assertEqual(d["stage"][1:], ["Concept", "project.toml"])
        self.assertEqual(d["phase_inferred"][1], "concept")

    def test_unknown_code_root_is_unknown_not_zero(self):
        self.with_toml({"src/a.gd": "x\n", "Assets/b.cs": "y\n", "ProjectSettings/ProjectVersion.txt": "m_EditorVersion: 6000.3.25f1\n"})
        _, out, _ = self.run_cli("project-state")
        d = {r[0]: r for r in rows(out)}
        self.assertEqual(d["source_files"][1], "unknown")

    def test_src_beside_a_plain_asset_root_is_the_code_root(self):
        self.with_toml({"src/a.gd": "x\n", "Assets/data/x.json": "{}\n"})
        _, out, _ = self.run_cli("project-state")
        d = {r[0]: r for r in rows(out)}
        self.assertEqual(d["code_root"][1:], ["src", "detected"])
        self.assertEqual(d["source_files"][1], "1")

    def test_lone_unity_assets_is_the_code_root(self):
        self.with_toml({"Assets/a.cs": "x\n", "ProjectSettings/ProjectVersion.txt": "m_EditorVersion: 6000.3.25f1\n"})
        _, out, _ = self.run_cli("project-state")
        d = {r[0]: r for r in rows(out)}
        self.assertEqual(d["code_root"][1:], ["Assets", "detected"])

    def test_stage_only(self):
        self.with_toml()
        _, out, _ = self.run_cli("project-state", "--stage")
        self.assertEqual([r[0] for r in rows(out)], ["stage_toml", "stage", "phase"])

    def test_story_count_infers_pre_production(self):
        self.with_toml({"production/epics/a/story-001.md": story(), "src/x.gd": "x\n", "Source/y.cpp": "y\n"})
        _, out, _ = self.run_cli("project-state")
        d = {r[0]: r for r in rows(out)}
        self.assertEqual(d["phase_inferred"][1], "pre-production")

    def test_usage_error(self):
        self.with_toml()
        self.assertEqual(self.run_cli("project-state", "--nope")[0], 2)


if __name__ == "__main__":
    unittest.main()
