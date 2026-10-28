# Active Session State — [project or branch]

<!--
  HOW THIS FILE WORKS. Read this before editing it.

  This file has TWO regions and they are not interchangeable:

    1. The CHECKPOINT region below (STATUS + CHECKPOINT blocks) is the part
       machines read. `python tools/studio.py status` shows its first lines and a returning
       agent reads it whole at the start of a session, so it is
       BOUNDED BY CONSTRUCTION: keep it under ~25 lines. It is OVERWRITTEN on
       every update, never appended to.

    2. Everything after `<!-- /CHECKPOINT -->` is free-form narrative for humans
       and for a returning agent that wants detail. Nothing injects it automatically, so
       it may grow — but see Rotation below.

  Why the split exists: one append-only file doing both jobs grows without
  bound, and every consumer then reads a different slice of it: the top, the
  bottom, or a block nothing writes. They disagree because there is no contract
  to agree on. With the named regions, every consumer reads the same part.

  ROTATION. When the narrative below grows past ~200 lines, move it to
  `production/session-logs/` and start it fresh:
      python tools/studio.py rotate-session-state
  Nothing is lost — and the commit history already records most of what the
  narrative repeats.
-->

<!-- STATUS -->
Epic:
Feature:
Task:
<!-- /STATUS -->

<!-- CHECKPOINT -->
**Updated:** [YYYY-MM-DD]
**Branch:** `[branch]`
**Current task:** [one line — what is actively being worked on]
**Next step:** [one line — the very next action, concrete enough to resume cold]
**Blocked on:** [one line, or `nothing`]
**Files in progress:** [paths, comma-separated, or `none`]
**Run result:** [`/dev-story` writes its `Run result:` line here, verbatim, for `/story-done` to read; other writers leave this line out]
**Open questions:** [one line each, or `none`]
<!-- /CHECKPOINT -->

---

## Notes

[Free-form. Decisions and their rationale, what was tried and rejected, context
that would be expensive to reconstruct. Not machine-read — write for the person
or agent picking this up cold.]

<!--
  FIELD NOTES

  STATUS block
    A breadcrumb for the current focus (`Combat System > Melee > Hitboxes`), used at
    Production / Polish / Release stage. All three fields are optional —
    leave a field blank when it does not apply, and blank all three when there is
    no active focus. Do not delete the markers themselves — `python tools/studio.py session-state`
    expects them to exist.

  CHECKPOINT block
    The recovery payload. A new session, or one resumed after a compaction, reads it first
    (`python tools/studio.py session-state show`).
    It reads THIS region and nothing else, which is what keeps the cost fixed
    no matter how long the narrative gets.

    Keep `Branch` current. This file is not committed, so it stays put when you
    switch branches; a reader compares `Branch` with the branch it is
    on and notes when they differ.

    Write it so a cold reader can resume without reading anything else. "Current
    task: fixing the thing" is useless; "Current task: adding wall-jump to
    player_movement.gd" is not.
-->
