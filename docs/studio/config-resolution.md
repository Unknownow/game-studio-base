# Config Resolution

How a skill learns its effective settings. **One command, no prose chain.**

## The rule

A skill that needs config runs this near the top, before it does anything else:

```bash
python tools/studio.py config --keys a,b
```

and uses the printed values as given. It does **not** re-derive them. A skill that resolves a per-system
tier reads the `system_overrides` line (`--keys workflow,system_overrides`).

If the command cannot run (no Python 3.11+, a broken `project.toml`), the skill says so and falls back to the
defaults below. A missing block is never "config set in an interesting way": it means the settings were not
read.

## The output

```
=== Resolved Config ===
rigor: standard (project.toml)
review_mode: lean (rigor:standard)
automation: guided (project.local.toml)
workflow: standard (rigor:standard)
docs.density: balanced (rigor:standard)
story_granularity: balanced (rigor:standard)
qa.level: standard (rigor:standard)
team.size: individual (rigor:standard)
project.stage: Systems Design (project.toml)
automation_always_ask: scope_changes, file_deletions, schema_changes (default)
engine.name: unity (engine.toml)
testing.strict.logic: true (project.toml)
testing.strict.visual: unset (default)
system_overrides: combat=full inventory=minimal
=== end config ===
```

Every line ends with its **provenance** in parentheses. That is what makes a wrong value diagnosable —
`review_mode: solo (rigor:minimal)` when `project.toml` says `full` points straight at the problem.
`--json` prints `{"key": {"value": …, "source": …}}`. `unset` means no source set it: each skill applies its own
default for that key.

## Resolution chain

First source that has the key wins:

| Step | Source | Applies to |
|---|---|---|
| 1 | `project.local.toml` (gitignored) | any key: one developer's own preference |
| 2 | `project.toml` | all keys |
| 3 | `engine.toml` `[defaults]` (an engine layer adds it) | engine facts: `engine.name`, `engine.version` |
| 4 | **`modes.rigor` expansion** | the six knobs `rigor` fronts: `workflow`, `docs.density`, `qa.level`, `story_granularity`, `review_mode`, `team.size` |
| 5 | documented default | the table below |

An **enum-invalid value does not win**: the chain continues past it and the rejected value is named on the
`notes:` line. `python tools/studio.py check` reports it as ERROR `config`. A key with an empty value is unset.

> **Step 4 sits below every explicit source and above the terminal default.** A `project.toml` that already
> sets `docs.density = "terse"` resolves exactly that, because step 2 answers first. Invert steps 4 and 5 and
> `rigor` becomes a no-op; hoist step 4 above step 2 and it silently overrides settings people already have.
> Derived values report their provenance as **`rigor:<level>`**: `docs.density: balanced (rigor:standard)` says
> the value was never written down anywhere, and will move if that level moves.

## Defaults

| Knob | Default |
|---|---|
| `modes.automation` | `collaborative` |
| `modes.rigor` | `minimal` |
| `modes.automation_always_ask` | `scope_changes`, `file_deletions`, `schema_changes` |
| `project.stage` | `Concept` |
| `performance.enforce` | `warn` |
| `claude.sync` | `true` |

**The six knobs `rigor` fronts have no terminal default at all.** A default there would answer at step 5 before
the expansion at step 4 ever ran, making `rigor` a no-op for anyone who had not also set the sub-knob. Their
effective values come from the rigor level:

| `modes.rigor` | `workflow` | `docs.density` | `qa.level` | `story_granularity` | `review_mode` | `team.size` |
|---|---|---|---|---|---|---|
| `minimal` (default) | `minimal` | `terse` | `minimal` | `coarse` | `solo` | `individual` |
| `standard` | `standard` | `balanced` | `standard` | `balanced` | `lean` | `individual` |
| `full` | `full` | `thorough` | `full` | `fine` | `full` | `studio` |

Because `rigor` itself defaults to `minimal`, an unconfigured project resolves the six to the lean row. Raising
the tier is one question in `/start` or one `/settings` call. (`team.size` is the one knob `minimal` and
`standard` agree on: only `full` opts into the `studio` roster.)

`modes.workflow` is **fronted, not replaced**: `workflow_overrides.system_overrides` still beats the derived
value. Setting any of the six explicitly overrides just that one and leaves its siblings on the rigor level,
which is how "comprehensive but compact" (`rigor = "full"` + `docs.density = "terse"`) stays expressible.

**`testing.strict.*` has no central default on purpose.** Its unset default differs per skill by design:
`/smoke-check` treats unset as **blocking** (it is a build-health gate), while `/story-done` and `/dev-story`
apply the per-story-type table in `docs/studio/coding-standards.md`.

## Derived lines (named only)

These print **only when named** in `--keys`; the full block never includes them.

| Label | What it prints |
|---|---|
| `gate_level` | The gate level per story type: `testing.strict.<type>`, else the default table in `coding-standards.md`. `gate_level: logic=blocking(default) integration=advisory(project.toml) visual=blocking(default) ui=blocking(default) config=advisory(default; smoke-check: blocking)` |
| `engine_values` | `engine.name`, `.version` and `.language`, each with its source |
| `review_gate` | Whether a skill's own director gate and the PHASE-GATEs run at the resolved `review_mode`: `solo` none, `lean` the PHASE-GATEs only, `full` all. A `--review` flag overrides |
| `perf_budgets` | The four `performance.*` budgets (`target_framerate`, `frame_budget_ms`, `draw_call_limit`, `memory_ceiling_mb`) from `project.toml` |
| `system_overrides` | `workflow_overrides.system_overrides` as `system=tier` pairs, or `none` |

## Writing config

`python tools/studio.py config --set modes.rigor=standard` (add `--local` for `project.local.toml`) validates the
value against its enum, edits the one line in place (comments and order kept), and prints the new resolved line.
`python tools/studio.py config-set` does the same with the check rows `/settings` shows before it asks.
Lists and nested tables are edited by hand.

## Failure modes

| Condition | Behavior |
|---|---|
| `project.toml` absent | `check` reports ERROR `config`; `config` prints defaults |
| Malformed TOML | `config` exits 2 and names the parse error |
| Unknown table or key | `check` reports ERROR `config` |
| Enum-invalid value | the chain continues; the rejected value is named in `notes:` |
| Key present, value empty | treated as **unset**; falls through to the next source |
| `project.local.toml` without a base | allowed: the local file only adds overrides |
