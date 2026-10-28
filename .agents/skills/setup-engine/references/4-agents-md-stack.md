# /setup-engine — Section 4: Update AGENTS.md Technology Stack

> Part of `/setup-engine`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## 4. Update AGENTS.md Technology Stack

### Language selection

Engine step `hook: setup-engine/language`: if `ENGINE.md` exists, follow its section `## hook: setup-engine/language`; otherwise ask the user how their engine does this and record the answer in `ENGINE.md` under that heading.
The section says whether the engine has more than one primary language and what to ask.
Record the answer. It decides the technology stack lines, the naming conventions and
which specialist role handles code files for the rest of the project. An engine with a
single language needs no question.

---

Read `AGENTS.md` and show the user the proposed Technology Stack changes.
Ask: "May I write these engine settings to `AGENTS.md`?"

Wait for confirmation before making any edits.

Update the `## Technology Stack` section (add it after `## Where things live` if it is
missing), replacing any `[CHOOSE]` placeholders with the actual values:

```markdown
- **Engine**: [name] [version]
- **Language**: [language]
- **Build System**: [from the engine's stack section]
- **Asset Pipeline**: [from the engine's stack section]
```

Engine step `hook: setup-engine/stack`: if `ENGINE.md` exists, follow its section `## hook: setup-engine/stack`; otherwise ask the user how their engine does this and record the answer in `ENGINE.md` under that heading.
The section gives the Build System and Asset Pipeline lines for the engine.

### Engine reference line

In the same AGENTS.md write, set the engine reference line under `## Engine hooks` to
`Engine reference: engine-reference/<engine>/VERSION.md` for the chosen engine. Find the
line by its marker comment `<!-- ENGINE-REFERENCE -->`, never by its heading. It is
idempotent: re-running `/setup-engine` for a different engine rewrites the same line.
(`engine-reference/<engine>/` is created in Section 7 if it does not yet exist.)

---
