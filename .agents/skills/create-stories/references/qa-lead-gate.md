# Phase 5: QA lead review (QL-STORY-READY)

Read only when the `review_gate` line says `skill-gates=run` (`review_mode: full`).
Run it after the stories are drafted and before the Phase 6 write ask.

**An existing QA plan first.** Look for the newest `production/qa/qa-plan-*.md`. If
its Automated Tests Required section holds specs for stories in this epic (match by
title or slug), they can stand in for the QA lead's specs. Where the two differ, ask:
"Which test specs should these stories carry?" Options: The QA plan's / The QA
lead's / None yet. "None yet" writes
`*Test cases not yet defined — run /qa-plan to generate them.*` This never adds a
second review.

**Act as `qa-lead`, once,** for gate **QL-STORY-READY**: read `roles/qa-lead.md` and
`gates/ql-story-ready.md`. One report carries both the
verdicts and the specs: never do a second pass for the specs.

Brief:
- **Objective:** judge each drafted story's acceptance criteria for testability, and
  write test specs for the ones that pass.
- **Inputs:** the full story list inline (no story file exists yet, so the stories
  stand in for the gate's paths), each with its acceptance criteria, type, and
  TR-IDs with their requirement text from `tr-registry.yaml`; and the epic GDD's
  acceptance criteria for reference.
- **Return:** per story, ADEQUATE, GAPS, INADEQUATE, or NOT ASSESSED naming a
  missing input. For each ADEQUATE story, its spec block in the formats below: one
  Given/When/Then per criterion for Logic and Integration, manual steps for
  Visual/Feel and UI.
- **Boundaries:** this review writes no file.

Act on each story's verdict:

- **ADEQUATE:** keep its specs.
- **GAPS:** ask: "How do you want to handle the flagged criteria?" Options: Revise
  them / Accept and go on / Discuss further. Revise nothing before the answer. On
  Revise: draft the new criteria, show them, and review just those stories again
  in one follow-up pass. On Accept: the criteria stay, and the story's
  QA Test Cases read `*Test cases not yet defined — run /qa-plan to generate them.*`
- **INADEQUATE:** the story is not written as it stands. Revise its criteria with
  the user (draft, show, confirm), then have the QA lead write its specs. If the user
  will not revise it, drop it from this run and name it as dropped in the Phase 6
  list.
- **NOT ASSESSED:** not an ADEQUATE. Name the missing input, then supply it and ask
  again, or write the story without specs (the `/qa-plan` line) and mark it
  `QL-STORY-READY: NOT ASSESSED — [input]` in the Phase 6 list.

A story carries specs only once it is ADEQUATE: untestable criteria cannot be built
correctly. The specs go in the story's `## QA Test Cases`; the user builds
against them and does not invent new ones.

Logic and Integration:

```
Test: [criterion text]
  Given: [precondition]
  When: [action]
  Then: [expected result]
  Edge cases: [boundary values or failure states]
```

Visual/Feel and UI:

```
Manual check: [criterion text]
  Setup: [how to reach the state]
  Verify: [what to look for]
  Pass condition: [an unambiguous pass]
```
