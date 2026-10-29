# /smoke-check — Phase 2: Run Automated Tests

> Part of `/smoke-check`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 2: Run Automated Tests

**In this file:**

- `testing.command` first
- The engine step
- Unknown engine / not configured
- Test runner not available here
- Build check (the WAIVED path only)

**Run `testing.command` from `project.toml` when it is set** — it is the
project's own test command, the one `/setup-engine` wrote and CI runs. Use the
per-engine default below only when `testing.command` is absent, and say in the
report which of the two you ran. Wrap it in a timeout (`timeout 900 …`): **a
timeout (exit 124) is a gate FAILURE, never a pass** — the run never completed
and nothing was verified. macOS has no `timeout`: use `gtimeout 900 …` from
Homebrew's `coreutils` (same exit 124), or, with nothing installed,
`perl -e 'alarm shift; exec @ARGV' 900 …`, which exits 142 when time runs out —
a FAILURE the same way. Then read the result as the engine step says. On every engine
one outcome looks like success and is not; the engine step names them.

Engine step `hook: smoke-check/run-tests`: if `ENGINE.md` exists, follow its section `## hook: smoke-check/run-tests`; otherwise ask the user how their engine does this and record the answer in `ENGINE.md` under that heading.

It must give, for the engine: how to check that the test framework is installed (a missing framework is `NOT ASSESSED — <framework> not installed`, never a pass), the default test command when `testing.command` is unset, any build step that must run first, and how to read the result — the exit codes and the output lines that mean pass, fail, or no tests. Delete a stale results file before each run: left in place, the last run's pass is read as this run's. Report each test type (unit, integration) on its own line. A type that could not be run is reported by name (`<type>: NOT RUN — [reason]`) and cannot make the automated-test row a PASS.

**Zero tests is never a pass.** A run that matched no tests, whatever its exit code, is `NOT ASSESSED — no tests found`.

**Unknown engine / not configured:**
"Engine not configured in `project.toml` or
`docs/technical-preferences.md`. Run `/setup-engine` to specify the
engine, then re-run `/smoke-check`."

**If the test runner is not available in this environment** (no editor
executable resolved in Phase 1 step 3, runner script not found, etc.), report
clearly:

"Automated tests could not be executed — engine executable not found (checked
`testing.command`, `engine.path` and `PATH`; set `engine.path`, or put the
editor's full path in `testing.command`). Status will be recorded as NOT RUN.
Confirm test results from your local IDE
or CI pipeline. Until you do, the verdict is NOT ASSESSED — not FAIL, and not
a pass either: nothing has been observed about this build yet."

Do not treat NOT RUN as an automatic FAIL. Record it, and let the developer's
manual confirmation in Phase 4 resolve it. Until that confirmation arrives the
verdict is **NOT ASSESSED** (see the verdict rules in Phase 5), which ranks
above both pass values and below FAIL. An unrun suite is not a healthy build; it
is an unknown one, and the two need different follow-ups.

Parse runner output and extract:
- Total tests run
- Passing count
- Failing count
- Names of any failing tests (up to 10; if more, note the count)
- Any crash or error output from the runner itself

**Build check — the WAIVED path only** (`qa.level: minimal`, no game tests;
Phase 1 step 1). With no suite to run, run the project's own boot check:
`commands.smoke` when set, else `commands.build` when set, with the executable
Phase 1 step 3 resolved, under the same timeout rules (`timeout 900`, or
`timeout 1800` for `commands.build`; a timeout is a FAIL). Read the result as
`/setup-engine` documents it for the engine: a compile or script error in the
output is a FAIL even when the exit code is 0; any non-zero exit is a FAIL. Record `Build check: PASS — [command] exit 0`,
`FAIL — [reason]`, or `NOT RUN — [commands.smoke and commands.build unset |
executable not found]`. A build check that did not run is named in the report
and leaves the launch in Batch 1 to carry the verdict; it never passes on its
own.

---
