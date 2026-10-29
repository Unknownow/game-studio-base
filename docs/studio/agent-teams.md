# Parallel Sessions (experimental — opt-in)

> On-demand reference. Read this when you are actually considering running several sessions at once, not on every turn.

Multiple independent agent *sessions* running side by side, each with its own context window and token budget, coordinated through files on disk. This is a tool feature, not part of this template: the template works the same with one session acting as each role in turn.

## Use parallel sessions when

- Work spans multiple subsystems that will not touch the same files
- Each workstream would take more than 30 minutes and benefits from true parallelism
- A senior role (`technical-director`, `producer`) needs to coordinate three or more specialist sessions working on different epics

## Do not use them when

- One session's output is required as input for another (hand off one role at a time, as the `team-*` skills do)
- The task fits in a single session's context
- Cost is a concern — each session burns tokens independently

## How to coordinate

- Give each session its own branch or worktree, so two sessions never edit the same file.
- Coordinate through files: each session reads and writes its own `production/session-state/active.md` section and leaves its output at a path you named in advance.
- Merge in one place, and run `python tools/studio.py check` after each merge.

## Current status

Opt-in and unused by default. Record the first real use here when you adopt it.
