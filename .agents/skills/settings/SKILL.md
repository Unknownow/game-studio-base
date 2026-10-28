---
name: settings
description: "View or change project config: effective merged values with where each came from, or set a value in project.toml or project.local.toml. Use when the user asks what a setting is, wants to change rigor, review mode, automation or testing strictness, or asks why a skill behaves a certain way."
metadata:
  upstream: .claude/skills/settings/SKILL.md
  argument-hint: "[key | key=value | --local key=value]"
  core: "true"
---

# /settings — view or change project config

Manages `project.toml` (team-wide config, committed) and `project.local.toml`
(per-developer overrides, gitignored). Use this skill to inspect current
settings or change them without editing TOML by hand. The chain, the defaults and the
rigor table are in `docs/studio/config-resolution.md`.

**Automation mode**: take `modes.automation` from `python tools/studio.py config --keys automation,automation_always_ask`.
The approval gates in Phase 4 and Phase 5 follow the pattern in `docs/studio/automation-modes.md`.
**Note**: writing to `project.toml` is a `schema_changes` decision (a default
`automation_always_ask` category), so `/settings` confirms config writes even
in `autonomous` mode unless the user has removed `schema_changes` from their
always-ask list.

Ask by listing the options numbered, then end your turn to wait. A skipped or dismissed
question is not an answer: ask again in plain text.

Checklist (copy it and tick as you go):

```
- [ ] Phase 0: form of the request identified
- [ ] Phase 2-3: values shown, or Phase 4-5: change checked, asked, written and read back
```

## Phase 0: Parse Arguments

Determine which of the four forms the user invoked:

| Form | Mode |
|------|------|
| `/settings` (no args) | **View-all** (Phase 2) |
| `/settings <key>` (single arg, no `=`) | **View-one** (Phase 3) |
| `/settings <key>=<value>` (single arg with `=`) | **Set** (Phase 4) |
| `/settings --local <key>=<value>` (`--local` prefix) | **Set-local** (Phase 5) |

For Set and Set-local, `<key>` is a dotted TOML path (for example
`modes.review_mode`, `testing.strict.logic`) or a display name (`review_mode`), and `<value>` is the new value.

**Empty-operand validation:** after splitting the `key=value` operand on
`=`, if either `<key>` or `<value>` is empty, this is malformed — go to
Phase 6 (usage) rather than attempting the write. For `--local`, strip the `--local` token
first, then check the remaining operand the same way.

Anything else that doesn't match the four forms above → Phase 6 (usage).

## Phase 1: The commands

Every phase below uses `python tools/studio.py` and nothing else. Run each as its own plain command from the project root:

| Need | Command |
|---|---|
| Effective values with their source | `python tools/studio.py config` (all) or `config --keys a,b` |
| Schema and enum errors in both files | `python tools/studio.py check` (the `ERROR config` lines) |
| Pre-write checks (file, enum, known key, shadow, current value) | `python tools/studio.py config-set [--local] <key> <value> --dry-run` |
| The write, with a read-back | `python tools/studio.py config-set [--local] <key> <value>` |

If a command cannot run (no Python 3.11+), say so and stop: this skill does not edit TOML by hand.

## Phase 2: View-all Mode

(when no arguments)

1. Confirm `project.toml` exists. If missing, report:
   > "No `project.toml` found — run `/start` to create one."
   And exit.

2. Check if `project.local.toml` exists.

3. Run `python tools/studio.py check` and keep its `ERROR config` lines. Each names the file it came from.

4. Run `python tools/studio.py config`. Each line is `<key>: <value> (<source>)`. Sources: `project.local.toml`,
   `project.toml`, `engine.toml`, `rigor:<level>`, `default`. A key with no source prints `unset`.

5. **Print**, grouped by top-level section (`modes`, `engine`, `testing`, and so on) in the order the keys came out. Skip `unset`
   keys. Annotate each line from its source:

   | Source | Annotation |
   |---|---|
   | `project.local.toml` and `project.toml` also sets it | `(LOCAL OVERRIDE — project.toml has: <value>)` (read `project.toml` for the value) |
   | `project.local.toml` only | `(project.local.toml)` |
   | `project.toml` | `(project.toml)` |
   | `engine.toml` | `(engine.toml)` |
   | `rigor:<level>` | `(derived from rigor: <level>)` |
   | `default` | `(default)` |

   Example output:

```
project.toml: present
project.local.toml: present

Schema validation: ok

Effective config:

modes:
  review_mode: lean         (project.toml)
  automation: autonomous    (LOCAL OVERRIDE — project.toml has: collaborative)
  rigor: full               (project.toml)
  workflow: full            (derived from rigor: full)
  story_granularity: fine   (derived from rigor: full)

docs:
  density: terse            (project.toml)

qa:
  level: full               (derived from rigor: full)

engine:
  name: unity               (engine.toml)

testing:
  strict:
    logic: false            (LOCAL OVERRIDE — project.toml has: true)
    integration: true       (project.toml)

A derived value can still be set explicitly with /settings <key>=<value>;
an explicit value wins over rigor.
```

   The `docs.density` line above is the precedence rule made visible: an explicit `project.toml` value keeps winning over
   the level `rigor` would otherwise derive, so "comprehensive but compact" stays expressible.

   If schema errors exist, print them in this form before the effective config block:

```
Schema validation: ERRORS
  [project.toml] modes.review_mode: invalid value 'chaotic' for modes.review_mode (allowed: full, lean, solo)
```

## Phase 3: View-one Mode

(when single arg, no `=`)

Run `python tools/studio.py config --keys <key>`, and read `project.toml` and `project.local.toml` (when it exists) for the
key's own value in each file. Print:

```
<key>

  Effective value: <effective-value or "(not set)" if the source is unset>
  Source: <project.toml | project.local.toml | project.local.toml (overrides project.toml) | engine.toml | derived from rigor: <level> | default>
  Locally overridden: <yes | no>
```

When both files set the key (the LOCAL OVERRIDE case), add two more lines under Source:

```
  project.toml value: <value>
  project.local.toml value: <localvalue>
```

When the source is `rigor:<level>`, add one line under Source so the user knows the value is settable and how:

```
  Set explicitly with: /settings <key>=<value>   (an explicit value wins over rigor)
```

When the effective value is unset, print just:

```
<key>

  Effective value: (not set)
  Locally overridden: no
```

## Phase 4: Set Mode

(when `<key>=<value>`, no `--local`)

1. **Checks**: run `python tools/studio.py config-set <key> <value> --dry-run` from the project root and read its rows:
   - `enum` row `invalid`: show the allowed values from the row and exit without writing (the command exits 3).
   - `known` row `no`: nothing reads that key, so writing it changes nothing; it is most often a typo. Do not write yet: say so,
     and ask with the options `Write <key> anyway`, `Cancel`. Continue only on an explicit choice. A skipped or empty answer
     cancels. (`config-set` refuses unknown keys outright; the user adds a new key to the schema by editing
     `tools/gamestudio/config.py`, which is outside this skill.)
   - `shadow` row `yes`: print BEFORE the approval prompt:
     > "Note: this setting is currently locally overridden in `project.local.toml` (value: `<localvalue>`). Writing to `project.toml` will not change your effective value."
   - `current` row: show the old value.

2. **Approval gate**: Ask:
   - Prompt: ``Set `<key>=<value>` in `project.toml`?``
   - Options: `[A] Yes, write` / `[B] No, cancel`

3. **Write**: run `python tools/studio.py config-set <key> <value>`. It keeps the file's comments and key order, creates a missing
   table, and reads the value back. Check the `readback` row equals the value asked for (the command exits 7 when it does not).
   A key it refuses (exit 5: a list or nested table) is edited by hand: STOP and ask:
   > "`<key>` cannot be written by `/settings`. Show me what to do."

4. Confirm: ``Set `<key>=<value>` in `project.toml`.``

   **When `<key>` is `modes.rigor`**, the write also moves six other knobs, so print what they resolve to now — re-read each with
   `python tools/studio.py config --keys workflow,docs.density,qa.level,story_granularity,review_mode,team.size` rather than reciting
   the expansion table, since any of them may carry an explicit value that still wins:

   ```
   Set modes.rigor=full in project.toml. It now supplies:
     workflow: full            (derived from rigor: full)
     docs.density: terse       (project.toml — explicit, unchanged)
     qa.level: full            (derived from rigor: full)
     story_granularity: fine   (derived from rigor: full)
     review_mode: full         (derived from rigor: full)
     team.size: studio         (derived from rigor: full)
   ```

## Phase 5: Set-local Mode

(when `--local <key>=<value>`)

1. **Base check**: if `project.toml` doesn't exist:
   > "Cannot create `project.local.toml` — `project.toml` is missing. Run `/start` to create one first."
   Exit. (Local overrides require a base.)

2. **Checks**: run `python tools/studio.py config-set --local <key> <value> --dry-run` and read its rows exactly as in Phase 4 step 1
   (`enum`, `known`).

3. **Approval gate**: Ask:
   - Prompt: ``Set `<key>=<value>` in `project.local.toml` (your personal override, gitignored)?``
   - Options: `[A] Yes, write` / `[B] No, cancel`

4. **Write**: run `python tools/studio.py config-set --local <key> <value>`. A missing `project.local.toml` is created. Check the
   `readback` row as in Phase 4.

5. Confirm: ``Set `<key>=<value>` in `project.local.toml` (your override).``

## Phase 6: Usage

When the argument doesn't match any of the four valid forms (or has empty operands), print:

```
Usage:
  /settings                          — view all effective config
  /settings <key>                    — view a single setting
  /settings <key>=<value>            — change a setting (project.toml)
  /settings --local <key>=<value>    — change a setting locally
                                       (project.local.toml, gitignored)

Examples:
  /settings modes.review_mode
  /settings modes.review_mode=full
  /settings --local modes.automation=autonomous
```

## Notes

- All writes go through `python tools/studio.py config-set`. The skill edits no TOML by hand and depends on no external TOML library.
- **Derived values are not stored anywhere.** `workflow`, `docs.density`, `qa.level`, `story_granularity`, `review_mode` and `team.size`
  have no terminal default; when no file sets them their value comes from the `modes.rigor` expansion. Report them from
  `config` output: reading the file returns empty and would render them "(not set)" while every skill is in fact acting on a real value.
- The schema and the enum values are in `tools/gamestudio/config.py` and `docs/studio/config-resolution.md`.
- `project.local.toml` is gitignored. These overrides never propagate to teammates.
- To choose a value for a given game type, see `/start` (which infers rigor from the user's words) and the rigor table in
  `docs/studio/config-resolution.md`.
