# /setup-engine — Section 11: Upgrade Subcommand

> Part of `/setup-engine`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## 11. Upgrade Subcommand

**In this file:**

- Step 1 — Read Current Version State
- Step 2 — Fetch Migration Guide
- Step 3 — Pre-Upgrade Audit
- Step 4 — Confirm Before Updating
- Step 5 — Update VERSION.md
- Step 6 — Post-Upgrade Reminder

If invoked as `/setup-engine upgrade [old-version] [new-version]`:

### Step 1 — Read Current Version State

Read `engine-reference/<engine>/VERSION.md` to confirm the current pinned
version, risk level, and any migration note URLs already recorded. If
`old-version` was not provided as an argument, use the pinned version from this
file.

### Step 2 — Fetch Migration Guide

Use web search and page fetching to locate the official migration guide between
`old-version` and `new-version`:

- Search: `"[engine] [old-version] to [new-version] migration guide"`
- Search: `"[engine] [new-version] breaking changes changelog"`
- Fetch the migration guide URL from VERSION.md if one is already recorded,
  or use the URL found via search.

Extract: renamed APIs, removed APIs, changed defaults, behavior changes, and
any "must migrate" items.

### Step 3 — Pre-Upgrade Audit

Scan the **code root** (resolve per `docs/studio/code-root-resolution.md`) for code that uses APIs known to be deprecated or changed in the
target version:

- Search the code for deprecated API names extracted from the migration
  guide (e.g., old function names, removed types, changed property names)
- List each file that matches, with the specific API reference found
- Engine step `hook: setup-engine/upgrade`: if `ENGINE.md` exists, follow its section `## hook: setup-engine/upgrade`
  (engine-specific places to scan, such as project settings or package versions); otherwise ask the user
  how their engine does this and record the answer in `ENGINE.md` under that heading.

Present the audit results as a table:

```
Pre-Upgrade Audit: [engine] [old-version] → [new-version]
==========================================================

Files requiring changes:
  File                              | Deprecated API Found       | Effort
  --------------------------------- | -------------------------- | ------
  src/gameplay/player_movement.cs   | old_api_name               | Low
  src/ui/hud.cs                     | removed_node_type          | Medium

Breaking changes to watch for:
  - [change description from migration guide]
  - [change description from migration guide]

Recommended migration order (dependency-sorted):
  1. [system/layer with fewest dependencies first]
  2. [next system]
  ...
```

If no deprecated APIs are found in the code root, report: "No deprecated API usage
found in the code root — upgrade may be low-risk."

### Step 4 — Confirm Before Updating

Ask the user before making any changes:

> "Pre-upgrade audit complete. Found [N] files using deprecated APIs.
> Proceed with upgrading VERSION.md to [new-version]?
> (This will update the pinned version in `engine.toml` and `project.toml`, refresh the engine reference
> docs and add migration notes — it does NOT change any source files. Source migration is done manually
> or via stories.)"

Wait for explicit confirmation before continuing.

### Step 5 — Update VERSION.md

After confirmation:

1. Update `engine-reference/<engine>/VERSION.md`:
   - `Engine Version` → `[new-version]`
   - `Project Pinned` → today's date
   - `Last Docs Verified` → today's date
   - Re-evaluate and update the `Risk Level` and `Post-Cutoff Version Timeline`
     table if the new version falls beyond the model knowledge cutoff
   - Add a `## Migration Notes — [old-version] → [new-version]` section
     containing: migration guide URL, key breaking changes, deprecated APIs
     found in this project, and recommended migration order from the audit

2. Refresh the other reference files in `engine-reference/<engine>/`: append the new version's changes to
   `breaking-changes.md`, `deprecated-apis.md` and `current-best-practices.md` (when they exist), under a
   heading naming the version span (`## <old> → <new>`). Never truncate the older spans. Every claim comes
   from a page fetched this run (Section 7's sourcing rule).

3. Move the pin. When `engine.toml` exists at the repo root, set its `lts` and `editor_line` to the new
   version's line (for example `lts = "6.4"`, `editor_line = "6000.4"`), and update the
   `| **Engine Version** |` row of VERSION.md to match: `python tools/studio.py check` fails when they
   disagree. Then run `python tools/studio.py config-set engine.version "[new-version]"` so the primary
   config store stays in sync with VERSION.md.

### Step 6 — Post-Upgrade Reminder

After updating VERSION.md, output:

```
VERSION.md updated: [engine] [old-version] → [new-version]

Next steps:
1. Migrate deprecated API usages in the [N] files listed above
2. Run /setup-engine refresh after upgrading the actual engine binary to
   verify no new deprecations were missed
3. Run /architecture-review — the engine upgrade may invalidate ADRs that
   reference specific APIs or engine capabilities
4. If any ADRs are invalidated, run /propagate-design-change to update
   downstream stories
```

---
