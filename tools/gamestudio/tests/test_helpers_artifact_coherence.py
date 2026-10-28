import unittest

from ._util import RepoCase, story


def rows(out):
    return [l.split("\t") for l in out.splitlines() if l]


CATALOG = """phases:
  concept:
    label: "Concept"
    steps:
      - id: game-brief
        name: "Brief"
        command: /brainstorm
        required: true
        artifact:
          glob: "design/game-brief.md"
      - id: engine
        name: "Engine"
        command: /setup-engine
        required: true
        artifact:
          any_of:
            - glob: "project.toml"
              pattern: '^name[[:space:]]*=[[:space:]]*"(unity)"'
            - glob: "engine.toml"
              pattern: '^name'
      - id: manual
        name: "Manual"
        command: /x
        required: false
"""


class ArtifactCheckTest(RepoCase):
    def test_statuses(self):
        self.with_toml({"docs/studio/workflow-catalog.yaml": CATALOG, "design/game-brief.md": "x\n"})
        code, out, _ = self.run_cli("artifact-check", "--phase", "concept")
        self.assertEqual(code, 0)
        self.assertIn("STEPS: 3", out)
        self.assertIn("NO_CHECK: 1", out)
        self.assertIn("STEP: game-brief required=true repeatable=false check=glob status=PRESENT", out)
        self.assertIn("STEP: engine required=true repeatable=false check=any_of status=ABSENT", out)
        self.assertIn("status=NO_CHECK", out)

    def test_any_of_pattern(self):
        self.with_toml({"docs/studio/workflow-catalog.yaml": CATALOG,
                        "engine.toml": '[engine]\nname = "x"\n'})
        _, out, _ = self.run_cli("artifact-check", "--phase", "concept")
        self.assertIn("status=PRESENT alt=2", out)

    def test_unknown_phase_and_missing_catalog(self):
        self.with_toml({"docs/studio/workflow-catalog.yaml": CATALOG})
        self.assertEqual(self.run_cli("artifact-check", "--phase", "zzz")[0], 2)
        self.assertEqual(self.run_cli("artifact-check", "--phase", "concept", root=self.root + "-none")[0], 1)

    def test_real_catalog_parses(self):
        import os
        from ._util import REPO
        code, out, _ = self.run_cli("artifact-check", "--phase", "concept", root=REPO)
        self.assertEqual(code, 0)
        self.assertRegex(out, r"STEPS: [1-9]")


class CoherenceTest(RepoCase):
    def test_no_engine_is_not_checked(self):
        self.with_toml()
        code, out, _ = self.run_cli("project-coherence")
        self.assertEqual(code, 0)
        self.assertIn("[NOT CHECKED] every engine check", out)

    def test_version_rows(self):
        version = "| Field | Value |\n|---|---|\n| **Engine Version** | Unity 6.3 LTS |\n| **Installed at pin time** | 6000.3.25f1 |\n"
        self.add({"project.toml": 'schema_version = 1\n[engine]\nname = "unity"\nversion = "6000.3.25f1"\n',
                  "engine-reference/unity/VERSION.md": version})
        _, out, _ = self.run_cli("project-coherence")
        self.assertIn("[MATCH]       VERSION.md records the installed version at pin time: 6000.3.25f1", out)
        self.assertIn("[MATCH]       engine.version (6000.3.25f1) agrees with engine-reference/unity/VERSION.md (Unity 6.3 LTS)", out)

    def test_missing_installed_row_differs(self):
        self.add({"project.toml": 'schema_version = 1\n[engine]\nname = "unity"\nversion = "6.2"\n',
                  "engine-reference/unity/VERSION.md": "| **Engine Version** | Unity 6.3 LTS |\n"})
        _, out, _ = self.run_cli("project-coherence")
        self.assertIn("[DIFFERS]     engine-reference/unity/VERSION.md has no 'Installed at pin time' row", out)
        self.assertIn("[DIFFERS]     engine.version is '6.2'", out)

    def test_test_runner_missing(self):
        self.add({"project.toml": 'schema_version = 1\n[engine]\nname = "x"\n[testing]\ncommand = "python run_tests.py"\n'})
        _, out, _ = self.run_cli("project-coherence")
        self.assertIn("[DIFFERS]     testing.command is 'python run_tests.py' but 'run_tests.py' does not exist", out)


if __name__ == "__main__":
    unittest.main()
