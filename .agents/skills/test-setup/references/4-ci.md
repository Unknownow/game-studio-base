# /test-setup — Phase 4: Create CI/CD Workflow

> Part of `/test-setup`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 4: Create CI/CD Workflow

**In this file:**

- The engine step

Engine step `hook: test-setup/ci-workflow`: if `ENGINE.md` exists, follow its section `## hook: test-setup/ci-workflow`; otherwise ask the user how their engine does this and record the answer in `ENGINE.md` under that heading.

It must give the contents of `.github/workflows/tests.yml` for the engine: the checkout, the engine install or container step, the test run with the same flags as `testing.command`, and the upload of the results as an artifact. Pin action versions to full release tags. If CI needs a licence secret or a self-hosted runner, say so in the plan the user approves. Without an engine layer, ask the user how CI builds and tests their engine.
