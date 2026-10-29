# Studio Tests

Quality assurance infrastructure for the skills and roles themselves — not for any game built with them.

**This ships as part of the template, and it is meant to.** The template is something you customize: edit a skill, add your own, retune a role. This folder is how you check that what you changed still holds up. `catalog.toml` tracks all 75 skills and 34 roles, `quality-rubric.md` defines per-category pass/fail metrics, and `templates/` gives you the spec format for anything new you write. It is driven by `/skill-test` and `/skill-improve`.

> **If you remove it, two of the four `/skill-test` modes stop working.**
>
> | Mode | Without this folder |
> |------|---------------------|
> | `/skill-test static` | **Works** — the 7 structural checks read only the skill's own files |
> | `/skill-test audit` | **Degrades** — reports that no catalog exists |
> | `/skill-test spec` | **Breaks** — the behavioral specs live here |
> | `/skill-test category` | **Breaks** — reads `quality-rubric.md` from here |
> | `/skill-improve` | **Degrades** — its test-fix-retest loop loses the category pass |

---

## The four modes

Every mode reads files; none runs the skill. Run them through your agent tool (`/skill:skill-test ...` in pi, `/skill-test ...` in Claude Code).

1. **static** — `/skill-test static <name>|all`. The 7 structural checks. It starts from the facts `python tools/studio.py skill-lint <name>` prints, and for roles from `python tools/studio.py agent-check --agent <name>`. Writes nothing.
2. **spec** — `/skill-test spec <name>`. Evaluates the assertions in the skill's or role's spec file (the `spec` path in `catalog.toml`). Offers to write a results file under `studio-tests/results/` and to update the entry's `last_spec` and `last_spec_result` lines.
3. **category** — `/skill-test category <name>|all`. Checks the skill or role against its category's rubric in `quality-rubric.md`. Offers to update `last_category` and `last_category_result`.
4. **audit** — `/skill-test audit`. Coverage report: which skills and roles have specs, and when each was last checked.

`catalog.toml` is edited as text: change the `last_*` lines of the one `[[skill]]` or `[[role]]` entry. There is no command that writes it.

---

## What's in here

```
studio-tests/
├── README.md              ← you are here
├── AGENTS.md              ← how an agent uses this folder
├── catalog.toml           ← master registry: all 75 skills + 34 roles, coverage tracking
├── quality-rubric.md      ← category-specific pass/fail metrics for /skill-test category
├── skills/                ← behavioral spec files, one folder per category
├── agents/                ← behavioral spec files for roles, by group
└── templates/             ← skill-test-spec.md and agent-test-spec.md, the spec formats
```

Engine-specific role specs are not part of the base template; an engine fork adds its own.

---

## Adding a spec

1. Copy `templates/skill-test-spec.md` (or `agent-test-spec.md`) to the category folder.
2. Fill it in, with a fixture and assertions for each case.
3. Add a `[[skill]]` or `[[role]]` entry to `catalog.toml` with the spec path, `priority` and `category`.
4. Run `/skill-test spec <name>`.
