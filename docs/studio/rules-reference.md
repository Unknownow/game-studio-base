# Path-Specific Rules

Rules in `rules/` carry `paths:` frontmatter: the globs of the files the rule governs. A rule with `extends:` also applies the rule it names.

**Before you edit a file, read every `rules/**/*.md` whose `paths:` match it, plus the file named in its `extends:`.** Most tools do not load rules by themselves, so this step is yours. A rule is guidance you weigh, the same as `AGENTS.md`; anything that must hold no matter what the model decides belongs in a check (`python tools/studio.py check`) or a git hook.

Three consequences:

1. **Reading, not editing.** Read the matching rules when you create a file too, not only when you open an existing one. Most work here creates files.
2. **Context, not enforcement.** A rule can be ignored; `check` cannot.
3. **Agree with the role.** Where a rule duplicates guidance a role file carries, the two must say the same thing. Contradicting instructions are resolved arbitrarily.

An engine layer (for example `game-studio-unity`) adds rules under `rules/<engine>/` with `extends:` pointing at the base rule and engine-specific `paths:`. Read both.

| Rule File | Path Pattern | Enforces |
| ---- | ---- | ---- |
| `gameplay-code.md` | `src/gameplay/**` | Data-driven values, delta time, no UI references |
| `engine-code.md` | `src/core/**` | Zero allocs in hot paths, thread safety, API stability |
| `ai-code.md` | `src/ai/**` | Performance budgets, debuggability, data-driven params |
| `network-code.md` | `src/networking/**` | Server-authoritative, versioned messages, security |
| `ui-code.md` | `src/ui/**` | No game state ownership, localization-ready, accessibility |
| `design-docs.md` | `design/gdd/**` | Required sections per `modes.workflow` (8 at `full`, 5 at `standard`), formula format, edge cases |
| `narrative.md` | `design/narrative/**` | Lore consistency, character voice, canon levels |
| `data-files.md` | `assets/data/**/*.json` | JSON validity, naming conventions, schema rules |
| `test-standards.md` | `tests/**` | Test naming, coverage requirements, fixture patterns |
| `prototype-code.md` | `prototypes/**` | Relaxed standards, README required, hypothesis documented |
| `shader-code.md` | `assets/shaders/**` | Naming conventions, performance targets, cross-platform rules |
| `agent-memory.md` | `.agents/memory/**` | The one place an agent may write unasked — and why a temporary absence must never be recorded as a durable fact |
| `skill-authoring.md` | `.agents/skills/**`, `roles/**` | A check must be able to report that it did not run — the five obligations for verdicts, defaults, skips, sourcing and derived coverage |

`scene-files` (hand-edit limits for editor-written scene and asset files) is engine-specific and lives in the engine layer.

## Adding a rule

1. Write `rules/<name>.md` with a non-empty `paths: [...]` in its frontmatter (and `extends:` when it refines another rule).
2. Keep it short, and include one correct and one incorrect example.
3. Add it to the table above and run `python tools/studio.py check`; a rule with bad frontmatter blocks it.
