# /setup-engine — Sections 8 and 8.5: Verify and Read Back

> Part of `/setup-engine`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## 8. Verify the AGENTS.md Engine Lines

**These lines were already written in Section 4 — do not edit them again and do not ask again.**
This step only confirms the result.

Read `AGENTS.md` and confirm the line under the `<!-- ENGINE-REFERENCE -->` marker reads:

```markdown
Engine reference: engine-reference/<engine>/VERSION.md
```

with `<engine>` the engine just configured. If it still points at a different engine, Section 4 did not
complete — go back and finish it rather than patching the line here.

> **Why this is a check and not a second write.** Repeating the edit here with its own approval prompt
> would ask the user twice for one change. Locate the line by its marker, never by its heading.

---

## 8.5 Read Back What You Just Wrote

Section 3's `Installed at pin time` row is easy to drop silently, because a missing row leaves no
trace. Catch it by verifying the files after writing them:

```bash
python tools/studio.py project-coherence
```

It compares `project.toml` against `engine-reference/<engine>/VERSION.md` and against the engine
binary when the engine's setup can probe one, and it checks that the runner `testing.command` names exists.

**Report every `[DIFFERS]` line to the user and resolve it before finishing.** Each one means two files
this skill just wrote disagree, or describe something that is not there. A `[DIFFERS]` line about a test
runner that a later skill installs (`/test-setup`) is expected: report it as expected, name the skill that
clears it, and never edit `testing.command` to make it go away. Every other `[DIFFERS]` line is resolved here.

**`[NOT CHECKED]` is not a pass.** Each such line names why a comparison could not be made — an absent
binary, a missing project file. Say which ones applied. A comparison that could not run has not
established agreement.

The helper emits observations and never a verdict. The judgement is yours and the user's.

---
