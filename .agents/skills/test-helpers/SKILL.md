---
name: test-helpers
description: "Generate engine-specific test helper libraries — assertion utilities, factory functions, mocks in the engine's test folder. Reduces boilerplate."
metadata:
  upstream: .claude/skills/test-helpers/SKILL.md
  argument-hint: "[system-name | all | scaffold]"
---

Run `python tools/studio.py config --keys automation` first.

**Automation mode**: Resolve `modes.automation` (`project.local.toml` →
`project.toml` → default `collaborative`). Every question to the user and
every file write follows `docs/studio/automation-modes.md`
(collaborative asks always · guided major-only · autonomous logs and proceeds;
`automation_always_ask` categories always prompt).

# Test Helpers

Writing test cases is faster and more consistent when common setup, teardown,
and assertion patterns are abstracted into helpers. This skill generates a
`tests/helpers/` library tailored to the project's actual engine, language,
and systems — so every developer writes less boilerplate and more assertions.

**Output:** engine-specific helper files in the engine's **helper root** —
the only place its test runner compiles them (`docs/studio/directory-structure.md`):

Helper root: `tests/helpers/` by default; the engine layer (`ENGINE.md`) names the engine's own helper root when its test runner only compiles tests in particular places.

`tests/helpers/` below means the helper root for the project's engine.

**When to run:**
- After `/test-setup` scaffolds the framework (first time)
- When multiple test files repeat the same setup boilerplate
- When starting to write tests for a new system

---

## Assertions: use the project's test framework, never bare `assert()`

**Generated helpers must assert through the configured test framework's assertion
API**, resolved from `testing.framework` — not through the language's built-in
`assert()`.

Two things go wrong with a bare `assert()` in a helper, and both are silent:

1. **It aborts the run instead of failing the test.** A framework assertion
   records a failure and continues, so one broken expectation yields one red test.
   A bare `assert()` halts execution, so the first failure hides every result
   after it.
2. **It is stripped in release builds.** A helper library built on `assert()`
   stops asserting entirely in exactly the build you most want checked, and does
   so without any error — the tests still "pass".

**Look up the assertion form for the configured framework before generating
code.** Do not copy the forms in this file or in other skills' examples as
authoritative — they are illustrative and have drifted (`assert_eq`,
`assert_true` and `assert_that` all appear across the repo). If you cannot
confirm the correct API for the project's framework, say so and generate no
helper rather than guessing.

**Helpers must not extend the framework's test-suite base class.** A file in
`tests/helpers/` that extends the suite type is discovered by the runner as a
test suite containing zero tests. Helpers are plain classes; only real test files
extend the suite.

---

## 1. Parse Arguments

**Modes:**
- `/test-helpers [system-name]` — generate helpers for a specific system
  (e.g., `/test-helpers combat`)
- `/test-helpers all` — generate helpers for all systems with test files
- `/test-helpers scaffold` — generate only the base helper library (no
  system-specific helpers); use this on first run
- No argument — run `scaffold` if no helpers exist, else `all`

---

## 2. Detect Engine and Language

Read from `project.toml` first, falling back to `docs/technical-preferences.md` for any key that is absent or empty:
- `engine.name` (else the `Engine:` value)
- `engine.language` (else the `Language:` value)
- `testing.framework` (else `Framework:` from the Testing section)

If the engine is not configured in either source: "Engine not configured. Run `/setup-engine` first."

---

## 3. Load Existing Test Patterns

Scan the engine's test root (`tests_root` from `engine.toml`, default `tests/`) for the test files already in use, using the file naming `rules/test-standards.md` and the test framework define.

For a representative sample (up to 5 files), read the test files and extract:
- Setup patterns (how `before_each` / `setUp` / fixtures are written)
- Common assertion patterns (what is being asserted most often)
- Object creation patterns (how game objects or scenes are instantiated in tests)
- Mock/stub patterns (how dependencies are replaced)

This ensures generated helpers match the project's existing style, not a
generic template.

Also read:
- `design/gdd/systems-index.md` — to know which systems exist
- In-scope GDD(s) — to understand what data types and values need testing. Read
  them by section: find the headings you need with the Grep tool (pattern `^#`,
  content mode) and Read those ranges with offset and limit.
- `docs/architecture/tr-registry.yaml` — to map requirements to tested systems

---

## 4. Generate Engine-Specific Helpers

### Engine helpers

Engine step `hook: test-helpers/engine-helpers`: if `ENGINE.md` exists, follow its section `## hook: test-helpers/engine-helpers`; otherwise ask the user how their engine does this and record the answer in `ENGINE.md` under that heading.

Generate three helper files in the helper root, in the project's language and using only the configured test framework's assertion API (never invent one):

1. **Assertions** — game-specific assertion utilities: an inclusive range check for any formula output with GDD bounds, plus signal or event emitted / not emitted checks where the engine has them.
2. **Factory** — functions that build minimal game objects for unit tests without loading a scene (override fields as needed).
3. **Scene helper** — only when the engine has scenes: load a scene, wait for its setup to finish, and return the root. A plain class, never a suite.

## 5. Generate System-Specific Helpers

For `[system-name]` or `all` modes, generate a helper per system:

Read only the GDD sections this needs — `Grep pattern="^## ([0-9]+\. )?(Formulas|Edge Cases|Detailed Rules|Detailed Design)" path="design/gdd/[system].md" output_mode="content" -A 30` (the optional number matches a reverse-documented GDD's `## 4. Formulas`) — rather than a full read (every peer skill section-greps GDDs; in `all` mode a full read multiplies across each system's 400+-line GDD). Extract:
- Data types (entity types, component names)
- Formula variables and their bounds
- Common test scenarios mentioned in Edge Cases

Generate `tests/helpers/[system]_factory.[ext]` with factory functions
specific to that system's objects.

Example for a `combat` system: generate `tests/helpers/combat_factory.[ext]` with `make_attacker(attack, crit_chance)`, `make_target(defense, health)` and `assert_damage_in_bounds(damage)`, where the bounds constants come from the GDD's damage formula (for example `DAMAGE_MIN = 0`, `DAMAGE_MAX = 999`). Assert through the shared assertions helper.

---

## 6. Write Output

Present a summary of what will be created:

```
## Test Helpers to Create

Base helpers (engine: [engine], helper root: [helper root]):
- [helper root]/game_assertions.[ext]
- [helper root]/game_factory.[ext]
[engine-specific extras]

System helpers ([mode]):
- [helper root]/[system]_factory.[ext]  ← from [system] GDD
```

Ask: "May I write these helper files to `[helper root]`?"

**Never overwrite existing files.** If a file already exists, report:
"Skipping `[path]` — already exists. Remove the file manually if you want it
regenerated."

After writing: Verdict: **COMPLETE** — helper files created.

"Helper files created. To use them in a test:
- Unity: Add `using` directive or reference the test assembly

---

## Collaborative Protocol

- **Never overwrite existing helpers** — they may contain hand-written
  customisations. Only generate new files that don't exist yet
- **Generated code is a starting point** — the generated factory functions use
  metadata patterns for simplicity; adapt to the actual class structure once
  the code exists
- **Helpers should reflect the GDD** — bounds and constants in helpers should
  trace to GDD Formulas sections, not invented values
- **Ask before writing** — always confirm before creating files in `tests/`

## Next Steps

- Run `/test-setup` if the test framework has not been scaffolded yet.
- Use `/dev-story` to implement stories — helpers reduce boilerplate in new test files.
- Run `/skill-test` to validate other skills that may need helper coverage.
