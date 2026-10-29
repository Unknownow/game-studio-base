---
name: setup-engine
description: "Configure the engine and its version. Pins it in AGENTS.md and project.toml, and fills engine reference docs from the web when the version is beyond the model's training data. Use when starting a project, changing engine, refreshing reference docs or upgrading the engine version."
metadata:
  upstream: .claude/skills/setup-engine/SKILL.md
  argument-hint: "[engine] | [engine version] | refresh | upgrade [old-version] [new-version] | no args for guided selection"
  core: "true"
---

# Engine Setup

When this skill is invoked:

Run `python tools/studio.py config --keys workflow` first.

**Tier awareness.** The `workflow` tier printed above governs which design
artifact this skill expects and the finish path it recommends in §12:
- **`minimal`** — the design artifact is the one-page `design/game-brief.md`
  (no GDDs, systems decomposition, or per-system design at this tier).
  `/setup-engine` runs *first* in the minimal path, so a missing brief here is
  normal, not a gap. The finish path is the 4-step floor.
- **`standard` / `full`** — the design artifact is `design/gdd/game-concept.md`
  and the finish path is the full pipeline.

If the command cannot run, assume `minimal` (the default).

## 1. Parse Arguments

Four modes:

- **Full spec**: `/setup-engine unity 6.3` — engine and version provided
- **Engine only**: `/setup-engine unity` — engine provided, version will be looked up
- **No args**: `/setup-engine` — fully guided mode (engine recommendation + version)
- **Refresh**: `/setup-engine refresh` — update reference docs (see Section 10)
- **Upgrade**: `/setup-engine upgrade [old-version] [new-version]` — migrate to a new engine version (see Section 11)

---

## 2. Guided Mode (No Arguments)

**Read `references/2-guided-mode.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 3. Look Up Current Version

**Read `references/3-version.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 4. Update AGENTS.md Technology Stack

**Read `references/4-agents-md-stack.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 5. Populate Technical Preferences

**Read `references/5-technical-preferences.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 5.5 Populate `project.toml` (Primary Config Store)

**Read `references/5.5-project-toml.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 6. Determine Knowledge Gap

**Read `references/6-knowledge-gap.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 7. Populate Engine Reference Docs

**Read `references/7-reference-docs.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 7.5 Scaffold the Engine Project

**Read `references/7.5-scaffold.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 8. Verify the AGENTS.md Engine Lines

**Read `references/8-verify.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 9. Update Agent Instructions

Ask: "May I add a Version Awareness section to the engine specialist role files?" before making any edits.

For the chosen engine's specialist roles (the ones `ENGINE.md` names in `hook: setup-engine/specialists`),
verify they have a "Version Awareness" section. If not, add one.

The section should instruct the role to:
1. Read `engine-reference/<engine>/VERSION.md`
2. Check deprecated APIs before suggesting code
3. Check breaking changes for relevant version transitions
4. Search the web to verify uncertain APIs

---

## 10. Refresh Subcommand

If invoked as `/setup-engine refresh`:

1. Read the existing `engine-reference/<engine>/VERSION.md` to get
   the current engine and version
2. Search the web for:
   - New engine releases since last verification
   - Updated migration guides
   - Newly deprecated APIs
3. Update all reference docs with new findings
4. Update "Last verified" dates on all modified files
5. Report what changed

---

## 11. Upgrade Subcommand

**Read `references/11-upgrade.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## 12. Output Summary

**Read `references/12-output-summary.md` now and follow it** — this phase's steps are in that file, not here. Read it again if the conversation was compacted or resumed during this phase.

## Guardrails

- NEVER guess an engine version — always verify with a web search or user confirmation
- `project.toml` is the primary config store. Always dual-write engine
  config to BOTH `project.toml` (primary) and `docs/technical-preferences.md` (human-readable
  mirror). If the two ever diverge, `project.toml` is authoritative.
- NEVER overwrite existing reference docs without asking — append or update
- If reference docs already exist for a different engine, ask before replacing
- Always show the user what you're about to change before making AGENTS.md edits
- If a web search returns ambiguous results, show the user and let them decide
