# Context Management

Context is the most critical resource in an agent session. Manage it actively.

## File-Backed State (Primary Strategy)

**The file is the memory, not the conversation.** Conversations are ephemeral and
will be compacted or lost. Files on disk persist across compactions and session crashes.

### Session State File

Maintain `production/session-state/active.md` as a living checkpoint. Update it
after each significant milestone:

- Design section approved and written to file
- Architecture decision made
- Implementation milestone reached
- Test results obtained

**Create it from `templates/session-state.md`** — the file has a
schema, and the CLI depends on it.

Two regions, and the distinction is load-bearing:

| Region | Who reads it | Rule |
|--------|--------------|------|
| `<!-- STATUS -->` … `<!-- /STATUS -->` | `python tools/studio.py status` (breadcrumb, Production+ only) | Keep the markers even when empty |
| `<!-- CHECKPOINT -->` … `<!-- /CHECKPOINT -->` | `python tools/studio.py session-state` (run it first in every session, including after a compaction) | **Overwrite, never append.** Under ~25 lines — shown verbatim |
| Everything after `<!-- /CHECKPOINT -->` | humans, and an agent that wants detail | Free-form; nothing injects it |

The checkpoint holds: current task, next step, what it is blocked on, files in
progress, open questions. Write it so a cold reader can resume without opening
anything else.

> **Why the split.** One append-only file doing both jobs grows without bound,
> and every consumer then reads a different slice of it: the top, the bottom, or
> a block nothing writes. None of them is wrong, because nothing defines where
> the recoverable state lives. With a named region, every consumer reads the
> same part, and the cost is fixed no matter how long the narrative grows.

**Rotation.** When the narrative passes ~200 lines, move it into
`production/session-logs/`:

```bash
python tools/studio.py rotate-session-state            # --dry-run to preview
```

The checkpoint stays, the narrative is appended to a dated log, nothing is
deleted. `python tools/studio.py session-state` reports when rotation is due but never performs it.

### Status Line Block (Production+ only)

When the project is in Production, Polish, or Release stage, include a structured
status block in `active.md` that `python tools/studio.py status` can parse. (The project
stage is resolved from `project.stage` in `project.toml`, falling back to
`production/stage.txt`.)

```markdown
<!-- STATUS -->
Epic: Combat System
Feature: Melee Combat
Task: Implement hitbox detection
<!-- /STATUS -->
```

- All three fields (Epic, Feature, Task) are optional — include only what applies
- Update this block when switching focus areas
- `status` shows it as a breadcrumb: `Combat System > Melee Combat > Hitboxes`
- Remove or empty the block when no active work focus exists

After any disruption (compaction, crash, a cleared conversation), read the state file first.

### Incremental File Writing

When creating multi-section documents (design docs, architecture docs, lore entries):

1. Ask to create the file ("May I create [path] with the section skeleton?"), then
   create it with every section header and empty bodies
2. Discuss and draft one section at a time in conversation
3. Write each section to the file as soon as it's approved (a skill that writes
   once at the end, such as `/create-architecture`, records approved sections in
   the session state instead)
4. Update the session state file after each section
5. After writing a section, previous discussion about that section can be safely
   compacted — the decisions are in the file

This keeps the context window holding only the *current* section's discussion
(~3-5k tokens) instead of the entire document's conversation history (~30-50k tokens).

## Proactive Compaction

- **Compact or restart proactively** at ~60-70% context usage, not reactively at the limit
- **Start a fresh conversation** between unrelated tasks, or after 2+ failed correction attempts
- **Natural compaction points:** after writing a section to file, after committing,
  after completing a task, before starting a new topic
- **Focused compaction:** tell the summary what to keep — "sections 1-3 are
  written to file, working on section 4"

## Context Budgets by Task Type

- Light (read/review): ~3k tokens startup
- Medium (implement feature): ~8k tokens
- Heavy (multi-system refactor): ~15k tokens

## Deterministic Helpers — `python tools/studio.py <helper>`

The cheapest context saving is not summarising a document, it is **not reading it
at all**. When a question has a deterministic answer, a helper should answer it
and the model should spend its budget on judgment instead. Every helper is a
subcommand of the one CLI; `python tools/studio.py --help` lists them all.

Current examples:

- **`gdd-structure-check`** — which of the 8 standard sections a GDD contains.
  Replaces a full-document read per GDD, and cannot hallucinate a missing
  section. Reports **presence only**; the caller applies the workflow tier.
- **`review-scope`** — which GDDs changed since the last cross-review, plus
  their declared dependencies. Replaces reasoning through git history.

One rule for helpers: **emit observations, not verdicts.** A helper that scores
or judges will eventually contradict a tier, mode, or per-system override it does
not know about. Report what is on disk and let the caller decide what it means.

## Delegating to a Fresh Session

When your tool can run a separate session (a sub-agent, a second chat), use it for
research and exploration to keep the main session clean. It returns only a summary:

- **Delegate** when investigating across multiple files, exploring unfamiliar code,
  or doing research that would consume >5k tokens of file reads
- **Read directly** when you know exactly which 1-2 files to check
- A fresh session does not inherit conversation history — provide full context in
  the prompt. Tools without this feature simply do the work in the main session.

## Compaction Instructions

When context is compacted, preserve the following in the summary:

- Reference to `production/session-state/active.md` (read it to recover state)
- List of files modified in this session and their purpose
- Any architectural decisions made and their rationale
- Active sprint tasks and their current status
- Role hand-offs and their outcomes (success/failure/blocked)
- Test results (pass/fail counts, specific failures)
- Unresolved blockers or questions awaiting user input
- The current task and what step we are on
- Which sections of the current document are written to file vs. still in progress

**After compaction:** Read `production/session-state/active.md` and any files being
actively worked on to recover full context. The files contain the decisions; the
conversation history is secondary.

## Recovery After Session Crash

If a session dies ("prompt too long") or you start a new session to continue work:

1. Run `python tools/studio.py session-state` to preview `active.md`
2. Read the full state file for context
3. Read the partially-completed file(s) listed in the state
4. Continue from the next incomplete section or task
