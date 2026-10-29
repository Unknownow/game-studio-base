# /test-setup — Phase 3: Create Directory Structure

> Part of `/test-setup`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 3: Create Directory Structure

**In this file:**

- `tests/README.md`
- `production/qa/evidence/.gitkeep`
- Engine-specific files (the engine step)

After approval, create the following files:

### `tests/README.md`

````markdown
# Test Infrastructure

**Engine**: [engine name + version]
**Test Framework**: [the engine's test framework]
**CI**: `.github/workflows/tests.yml`
**Setup date**: [date]

## Directory Layout

```
tests/
  unit/           # Isolated unit tests (formulas, state machines, logic)
  integration/    # Cross-system and save/load tests
  smoke/          # Critical path test list for /smoke-check gate
```

[When the engine's runner only compiles tests in particular places (`tests_root`
in `engine.toml`), replace the unit/integration lines: unit and integration
tests live under that test root; `tests/` keeps this README and `smoke/`.
Every `tests/unit/` path below means that test root.]

```
production/qa/
  evidence/       # Screenshot logs and manual test sign-off records
```

> **Manual evidence lives under `production/qa/evidence/`, not `tests/`** — that
> is where every consumer reads it.

## Running Tests

[Engine-specific command — see below]

## Test Naming

Follow the engine's test naming convention, as `rules/test-standards.md` and the engine step below give it, for the file, the class or suite, and the test function. Names say the scenario and the expected result.

## Story Type → Test Evidence

| Story Type | Required Evidence | Location |
|---|---|---|
| Logic | Automated unit test — must pass | `tests/unit/[system]/` |
| Integration | Integration test OR playtest doc | `tests/integration/[system]/` |
| Visual/Feel | Screenshot + lead sign-off | `production/qa/evidence/` |
| UI | Retained screenshot of each screen touched | `production/qa/evidence/` |
| Config/Data | Smoke check pass | `production/qa/smoke-*.md` |

## CI

Tests run automatically on every push to `main` and on every pull request.
A failed test suite blocks merging.
````

The README and this skill's completion summary name the same evidence path —
`production/qa/evidence/` is where `/smoke-check`, `/test-evidence-review`,
`/qa-plan` and the evidence table in `docs/studio/coding-standards.md` read,
so a `tests/evidence/` would be a directory nothing reads.

### `production/qa/evidence/.gitkeep`

Create it empty. Git does not keep an empty directory, and this is where
`/story-done`, `/smoke-check` and `/test-evidence-review` look for screenshots and
sign-off records — the completion summary lists it, so it must exist.

### Engine-specific files

Engine step `hook: test-setup/engine-files`: if `ENGINE.md` exists, follow its section `## hook: test-setup/engine-files`; otherwise ask the user how their engine does this and record the answer in `ENGINE.md` under that heading.

It must give the engine's test framework install step, its test root layout and assembly or project files, the exact `testing.command` to write into `project.toml` (with the flags the engine needs so a run neither hangs nor opens an interactive window), and how to read the result: exit codes, and the zero-tests case, which is `NOT ASSESSED`, never a pass. Do not write a runner script when the framework ships its own command-line runner. Without an engine layer, ask the user for these and record the answers in `ENGINE.md`.
