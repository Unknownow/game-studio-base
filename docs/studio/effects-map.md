# project.toml — Effects Map

> ## READ ONE SECTION, NEVER THIS WHOLE FILE
>
> This document is very large, far more than any one lookup needs. It is
> organised as one section per setting, headed `## <key>`, so a reader can take
> only the section it wants.
>
> **So opening it whole costs many times what you need.** To look up a setting:
>
> ```
> Grep pattern="^## modes.review_mode" path="docs/studio/effects-map.md" -A 40
> ```
>
> Read the section for your key and stop. The same rule the skills already apply
> to their own reference files — `/gate-check` loads only the row for the target
> phase and says "never load the others" — applies here, and this is the largest
> file in the framework.
>
> Cite a section of this document, never the whole file. A pointer such as "see
> effects-map.md for full schema" invites a full read of a file this size, and
> the cost of accepting that invitation is silent. Name the `## <key>` section
> you need instead.

This document defines what each `project.toml` setting actually does across
every skill that reads it. It is the tracked, authoritative reference.

**Purpose:** When a skill reads a setting, this document is the authoritative
source for what each value means for that skill's behavior. Implementers update
this file when adding a new setting or changing how a skill responds to one.

**Format per setting:**
- Priority chain — which source wins when multiple are present
- Per-value intent — what the value means in plain terms
- Skill behavior table — exactly what changes per skill per value

**Coverage scope:** This document covers the skills most affected by each setting.
Skills not listed (e.g. `ux-review`, `balance-check`, `test-flakiness`, `test-helpers`,
`test-setup`, `soak-test`, `perf-profile`, `launch-checklist`, `release-checklist`,
`skill-test`, `skill-improve`, `vertical-slice`) are not meaningfully affected by
`project.toml` settings and do not need entries here. Add a skill only when its
behavior genuinely branches on a setting value.

**Local override pattern:** `project.toml` is committed to git as the shared team
config. Per-developer overrides live in `project.local.toml` (gitignored). Priority
chain across all settings: `project.local.toml` → `project.toml` → legacy mirror →
`modes.rigor` expansion → hardcoded default. The expansion step applies only to the
six knobs `rigor` fronts (`modes.workflow`, `docs.density`, `qa.level`,
`modes.story_granularity`, `modes.review_mode`, `team.size`), which for that reason have **no** hardcoded default —
see the `modes.rigor` section.
**Secrets do NOT belong in either file — use environment variables.** See the
"Local Override Pattern" section below for full design including the whitelist of
which settings can be locally overridden.

---

## Local Override Pattern — `project.local.toml`

The `project.local.toml` file lets each developer override specific settings for
their own use without affecting the team. The file is gitignored and never
committed.

### How it works

Priority chain (every setting): `project.local.toml` → `project.toml` → hardcoded default

If a setting is present in `project.local.toml`, that value wins. If absent, the
value from `project.toml` is used. If absent there too, the hardcoded default
takes over.

---

### Deep merge semantics

When both files set a nested value, only the explicitly-set key is overridden.
Sibling keys in the same block are preserved.

Example:

`project.toml`:
```toml
[testing.strict]
logic = true
integration = true
visual = false
```

`project.local.toml` (sparse override):
```toml
[testing.strict]
logic = false
```

Effective config seen by skills: `logic: false, integration: true, visual: false`.
Only the explicitly-set `logic` key is overridden; sibling keys come through from
`project.toml`.

---

### Whitelist — which settings can be locally overridden

Only personal-experience settings can be locally overridden. Project-wide facts
(engine, stage, naming conventions, what's required on disk) are locked to
`project.toml` because divergence between developers would break team coordination.

The rule for deciding which side a setting belongs on:

> **If a setting affects what artifacts exist or what they look like on disk,
> it must be locked to `project.toml`. If a setting only changes your personal
> experience (which agents run for you, whether you get prompts, your local
> CI bypass), it can be locally overridden.**

**Locally overridable** (personal experience only — no effect on artifacts on disk):

| Setting | Why local override makes sense |
|---------|-------------------------------|
| `modes.review_mode` | How much AI review you personally want |
| `modes.automation` | How often the AI prompts you |
| `modes.automation_always_ask` | Your personal safety categories |
| `team.size` | Which agents run for your reviews (review depth differs, artifacts don't) |
| `testing.strict.*` (each type) | Whether failures block your local work (CI still enforces project.toml defaults) |
| `performance.enforce` | Whether budget violations block your local work (CI enforces project defaults) |
| `features.session_state` | Your session tracking preference |
| `features.token_budget_warn_at` | Your personal cost threshold |
| `features.read_guard` | Whether your whole-file reads of large design docs are refused |
| `features.read_guard_kb` | The size over which they are |
| `updates.check` | Whether you see the new-release line; turning it off for you leaves it on for teammates |

**Locked to `project.toml`** (project-wide — would create artifact divergence if local):

| Setting | Why it must be project-wide |
|---------|----------------------------|
| `schema_version`, `framework.*` | File metadata, not preferences — **exempt from the report below**, since a `project.local.toml` carrying `schema_version: 1` is correct as written |
| `project.name`, `version`, `genre`, `kind`, `stage` | Project identity |
| `engine.*`, `specialists.*` | Whole team must use same engine |
| `naming.*` | Code conventions must be consistent across team |
| `platform.*` | Game facts (what platforms it ships on) |
| `performance.target_framerate`, `frame_budget_ms`, `draw_call_limit`, `memory_ceiling_mb` | Game budgets, shared targets |
| `accessibility.target` | Game commitment, project-wide |
| `cadence.*` | Sprint/milestone length affects team coordination |
| `modes.rigor` | Fronts the four below — locked for the same reason they are |
| `modes.workflow` and `workflow_overrides` | Affects which sections are required in authored docs |
| `modes.story_granularity` | Affects how big stories are in repo — team must be consistent |
| `docs.density` | Affects how deep authored docs are — team must produce consistent docs |
| `qa.level` | Affects what test evidence stories must include on disk |
| `qa.coverage_minimum` | Project quality bar |
| `strict_gate_checks` | Affects whether `project.stage` advances — a project-wide write |
| `commands.*` | Build/test commands are project facts |
| `testing.framework` | Whole project uses one framework |

> **A locked key written into `project.local.toml` by hand is reported, not
> swallowed.** `/settings --local` refuses to write one, but the
> file is meant to be hand-edited and that path had no guard: `modes.rigor: full`
> there is a real key with a legal value, so enum validation passes it, and then
> resolution never consults the local file for that path — the setting vanishes
> and the user sees the default they were trying to override, with no error
> anywhere. Every check validated the **value**; nothing validated the
> **location**. `python tools/studio.py config` names such keys on
> its `notes:` line. It **warns and never reconciles**: it does not
> edit the file, does not begin honouring the key, and does not change
> resolution — a locked setting decides which artifacts exist on disk, so
> applying one quietly would produce exactly the divergence this table prevents.
> A clean file stays silent — you are only told when a key is actually in the
> wrong place.

---

### `/settings --local` flag behavior

```
/settings workflow=minimal               → writes to project.toml (team-wide)
/settings --local automation=autonomous  → writes to project.local.toml (just you)
```

**Behavior rules:**

- Default (no flag): writes to `project.toml`
- `--local` flag: writes to `project.local.toml` (creates it if absent)
- `--local` on a locked setting → error:
  > *"`<setting>` cannot be locally overridden — it's a project-wide setting.
  > Use `/settings <setting>=<value>` (no `--local`) to change it for the whole team."*
- Writing to `project.toml` when the same setting is currently locally overridden → warning:
  > *"This setting is currently locally overridden in `project.local.toml`.
  > Writing to `project.toml` will not affect your effective value."*

---

### Schema validation on read

When skills or the CLI read either file:

| Issue | Behavior |
|-------|----------|
| Unknown key (typo or stale setting) | Session-start warning: *"`project.local.toml` has unknown key `modes.automaton` — typo? Ignored."* Does NOT block (forwards-compat with future settings). |
| Invalid value not in enum (e.g. `automation: chaotic`) | Hard error: skill exits with explanation of valid values. |
| Type mismatch (e.g. integer field set to a string) | Hard error: skill exits with type expected. |

---

### Creation and error handling

| Scenario | Behavior |
|----------|----------|
| `/start` on fresh project | Creates `project.toml` only. Does NOT create `project.local.toml`. |
| `/settings --local <x>=<y>` when `project.local.toml` doesn't exist | Creates `project.local.toml` containing just that setting. |
| `project.local.toml` exists but `project.toml` doesn't | Hard error: *"`project.toml` missing — run `/start` to create one. Local overrides require a base."* |
| Both files exist | Read `project.toml` first, deep-merge `project.local.toml` on top. Normal operation. |
| Both files set the same key | `project.local.toml` wins. No prompting. |

---

### Two-developer clash scenarios — and why the whitelist prevents them

**File-level conflict (`project.toml`):**
Standard git merge conflict. Each developer's `project.local.toml` is gitignored
and never collides with another developer's. Normal git workflow handles team-wide
changes.

**Logical inconsistency (prevented by whitelist):**

Example of what the whitelist prevents:

> Sarah sets `modes.workflow: minimal` locally to skip GDD requirements. She
> doesn't write GDDs because her local mode doesn't require them. Mike runs
> `/gate-check` with the team's `project.toml` value, `standard`; gate-check sees missing
> GDDs and fails.

This can't happen because `modes.workflow` is locked to `project.toml`. Same
for `qa.level`, `docs.density`, `strict_gate_checks`, `naming.*`, and every
other setting that affects what artifacts exist on disk.

Personal experience settings (`automation`, `review_mode`, `team.size`,
`testing.strict.*`, `performance.enforce`) can diverge freely without affecting
anyone else.

---

### Stricter reviewer reviewing a looser reviewer's work

A common worry: "what if my teammate has stricter review settings than me?
Will their `/gate-check` or `/design-review` flag things in my work?"

The answer depends on which kind of difference you're talking about:

**Different review depth, same project requirements (HEALTHY):**

- Teammate A: local `review_mode: full`, `automation: collaborative`, `testing.strict.logic: true`
- Teammate B: local `review_mode: solo`, `automation: autonomous`, `testing.strict.logic: false`
- Both bound by the same project.toml-locked settings (e.g. `workflow: standard`, `qa.level: standard`)

B writes a GDD that meets `workflow: standard` (all 5 required sections present).
B's `/design-review` runs with `review_mode: solo` — fast advisory check, no
specialists run. B moves on.

Later A reviews the same GDD with `review_mode: full` — runs 5–15 specialists,
finds polish opportunities and edge cases B's lighter review missed. A files
findings as PR comments or follow-up issues. B addresses the ones that matter.

**This is normal team collaboration.** Different reviewers catching different
things is the value of having multiple reviewers. The artifacts on disk are the
same; only review depth differs. Nothing about this scenario creates project-state
divergence.

**Different requirements (PREVENTED by the whitelist):**

If `qa.level` were locally overridable:

- B sets `qa.level: minimal` locally. B's stories don't include test evidence.
- B's `/story-done` accepts the story without evidence. Story marked Complete on disk.
- A pulls. A's `qa.level: standard` requires evidence. A's `/story-done` would have rejected it.
- A's next `/gate-check` fails because evidence is missing across multiple of B's "Complete" stories.

This is the artifact divergence problem. To prevent it, `qa.level` is locked to
`project.toml`. The team agrees together on what's required; individuals override
only their personal experience, never the team's standards.

**The pattern to remember:**

| Difference type | Outcome |
|----------------|---------|
| Different review depth (review_mode, team.size) | Stricter reviewer surfaces more findings — healthy. Artifacts unchanged. |
| Different local strictness on failures (testing.strict.*, performance.enforce) | Stricter dev's local /story-done blocks earlier — they fix it locally. CI uses project.toml defaults so team-wide quality bar stays. |
| Different artifact requirements (workflow, qa.level, docs.density, etc.) | **Can't happen — these are locked.** Team agrees once in project.toml. |

---

### CI behavior

CI environments have no `project.local.toml` — the file is gitignored and never
present in a fresh clone. CI therefore always runs against `project.toml`
defaults: strict project standards, no developer-specific overrides.

This is intentional and important:

| Setting | Local default for fast iteration | CI default (`project.toml`) |
|---------|----------------------------------|------------------------------|
| `modes.review_mode` (locally overridable) | `solo` for one developer | `lean` (a team's usual choice — phase gates always run) |
| `testing.strict.logic` (locally overridable) | `false` for fast WIP commits | `true` (failing tests block CI) |
| `modes.automation` (locally overridable) | `autonomous` for solo flow | `collaborative` (the team's collab protocol, but CI doesn't ask questions anyway — this is mostly a no-op on CI) |

A developer can iterate locally with relaxed gates, but CI catches issues using
the strict project defaults. The team's quality bar is enforced at the CI level
regardless of any individual developer's local config.

---

### Secrets — never in either file

`project.toml` and `project.local.toml` are for **preferences and configuration**,
never for **secrets**. API keys, tokens, and credentials belong in:

- **Environment variables** (preferred for production/CI)
- **`.env` file** (gitignored, local dev)
- **OS keychain** (when integrating with services that support it)

When a skill needs an API key (e.g. `/asset-spec` calling Midjourney), it reads
from the environment, not from `project.toml`. `project.toml` only stores **which**
generator is used (`art.generator: midjourney`), not the API key for it.

CI environments typically have no `project.local.toml` (gitignored, not in the
clone) — so CI always runs against `project.toml` defaults. This is correct
behavior: strict project defaults for CI, looser developer overrides for local work.

---

## modes.review_mode

**Controls:** How many specialist and director agents are run during skill execution  
**Values:** `full` | `lean` | `solo`  
**Default:** *none* — supplied by `modes.rigor` (`minimal`, the default, yields `solo`; `standard` yields `lean`; `full` yields `full`)  
**Set by:** `/settings`. `/start` and `/adopt` never write it themselves — unset, it follows `modes.rigor`  
**Read by:** See skill table below

**Priority chain (all skills):** inline argument flag → `modes.review_mode` in `project.toml` → `production/review-mode.txt` (legacy fallback) → `modes.rigor` expansion (no terminal default; `minimal`→`solo`, `standard`→`lean`, `full`→`full`)

> **design-review follows the standard chain.** `modes.review_mode` controls
> design-review depth, its inline flag is `--review` for consistency with every
> other review-mode-aware skill, and with nothing set it follows `modes.rigor` like
> them: `solo` at `minimal` (the default), `lean` at `standard`.

> **Hotfix / day-one-patch exception:** These skills are emergency or release-critical
> pipelines. They are never gated by `review_mode` — all agents always run.

> **`review_mode` in the nine `team-*` orchestrators.** `review_mode` sets
> director-gate depth: `full` runs every director gate a pipeline names, `lean`
> skips director gates unless they are PHASE-GATE type, and `solo` skips gate
> running entirely. No team pipeline runs a PHASE-GATE (`/gate-check` is the
> only skill that runs them), so in the orchestrators
> `lean` and `solo` behave the same, and `full` adds two things:
> `/team-release`'s technical-director release sign-off, and, at
> `team.size: small`, `/team-narrative`'s `localization-lead` and `world-builder`.
>
> Outside the orchestrators, the skills in the *Core skills* table below read
> `review_mode` as that table documents.

---

### Value intent

| Value | Intent |
|-------|--------|
| `full` | All director and specialist gates active. Best for teams, learning, or anyone who wants thorough AI feedback on every decision. |
| `lean` | Phase gates only — per-skill director sign-offs skipped. The `rigor: standard` value. Balances quality with token cost. |
| `solo` | No gates, no director runs (a pipeline's own review, such as `/team-narrative`'s ND-CONSISTENCY, still runs). Fastest. For confident solo iteration. The default, from `rigor: minimal`. |

---

### Core skills (currently review-mode aware)

| Skill | full | lean | solo |
|-------|------|------|------|
| **design-review** | 5–15 specialist agents run in Phase 3b | No specialist agents — single-session analysis only | Phases 1–4 only, no delegation, no next-steps prompt |
| **gate-check** | Director panel runs in turn — **width set by `modes.workflow`**, not by this axis | Director panel runs in turn — same width rule; phase gates always run | Artifact existence checks only, no directors run |
| **design-system** | All section specialists + CD-GDD-ALIGN sign-off gate | Specialists for Sections D and H only (+ G when its knobs interact, + Visual/Audio when visual feedback is central); CD-GDD-ALIGN skipped | No section specialists; CD-GDD-ALIGN skipped |
| **art-bible** | All section specialists + AD-ART-BIBLE sign-off gate | All section specialists, AD-ART-BIBLE skipped | All section specialists, AD-ART-BIBLE skipped |
| **architecture-decision** | Engine specialist + TD-ADR gate | Engine specialist; TD-ADR skipped | Engine specialist; TD-ADR skipped |
| **create-architecture** | TD-ARCHITECTURE + LP-FEASIBILITY agents, in turn | Both skipped | Both skipped |
| **brainstorm** | CD-PILLARS, AD-CONCEPT-VISUAL, TD-FEASIBILITY, PR-SCOPE | All skipped | All skipped |
| **map-systems** | TD-SYSTEM-BOUNDARY, PR-SCOPE, CD-SYSTEMS | All skipped | All skipped |
| **story-done** | QL-TEST-COVERAGE + LP-CODE-REVIEW | Both skipped | Both skipped |
| **sprint-plan** | PR-SPRINT feasibility check | Skipped | Skipped |
| **create-epics** | PR-EPIC scope check | Skipped | Skipped |
| **create-stories** | QL-STORY-READY + test case specs | Skipped | Skipped |
| **prototype** | CD-PLAYTEST review — APPROVE keeps the recommendation; CONCERNS and REJECT go to the user, who decides | Skipped — the recommendation stands unreviewed | Skipped — the recommendation stands unreviewed |
| **milestone-review** | PR-MILESTONE feasibility check | Skipped — no producer verdict | Skipped — no producer verdict |
| **playtest-report** | CD-PLAYTEST creative assessment | Skipped | Skipped |
| **story-readiness** | QL-STORY-READY acceptance criteria check | Skipped | Skipped |
| **create-control-manifest** | TD-MANIFEST (technical-director) review | Skipped | Skipped |
| **propagate-design-change** | TD-CHANGE-IMPACT (technical-director) review | Skipped | Skipped |

---

### Skills that do not read `modes.review_mode`

These skills run the same way at `full`, `lean` and `solo`. None of them takes a
`--review` flag.

| Skill | What runs at every level |
|-------|--------------------------|
| **review-all-gdds** | Phase 2 consistency pass and Phase 3 design-theory pass, in turn |
| **architecture-review** | The primary engine specialist is consulted after the engine audit (recorded as NOT ASSESSED when no engine is configured) |
| **dev-story** | Core programmer routing, plus the engine specialist's check of every code story |
| **code-review** | Language, shader and UI specialists when an engine is configured, plus `qa-tester` for Logic and Integration stories |
| **security-audit** | `security-engineer` is run to run the audit |

---

### Team orchestration skills (pipeline behavior — different relationship)

Team skills are execution pipelines, not review gates. In them `review_mode` sets
only director-gate depth; `team.size` picks the agents (see `## team.size`), and a
pipeline's own review steps run in every mode.

| Skill | full | lean | solo |
|-------|------|------|------|
| **All nine `team-*`** | Every director gate the pipeline names | PHASE-GATE-type gates only | No director gates |
| **team-release** | + technical-director release sign-off before the go/no-go call | Sign-off not run — recorded as `not run (review_mode: lean)` | Sign-off not run — recorded as `not run (review_mode: solo)` |
| **team-narrative** | ND-CONSISTENCY; at `team.size: small`, + `localization-lead` and `world-builder` | ND-CONSISTENCY; at `small`, `narrative-director` + `writer` only | ND-CONSISTENCY still runs when `narrative-director` is active |

---

### Special cases and notes

- **gate-check** is the only skill where `full` and `lean` behave identically —
  phase gates always run. Only `solo` skips them. This is intentional: phase
  gates are the minimum quality bar, not optional extras. **How many directors
  run is a separate axis** — `modes.workflow` sets panel width (`minimal` → PR
  only, `standard` → TD + PR, `full` → all four), because directors are
  `strong`-tier roles and a small project should not pay for the same four-director panel
  as a large one. Width never softens a verdict: the strictest verdict from
  whoever ran still wins, and `/gate-check` names the perspectives it skipped.
- **art-bible** always runs its section specialists regardless of mode — only
  the final sign-off gate is controlled by `review_mode`. Specialist delegation is
  mandatory for the authoring output to be useful, and that has not changed.
  **design-system** is different: `lean` keeps the specialists for its high-risk
  sections only (D and H, plus G and Visual/Audio when they matter) and `solo`
  drafts every section without one, and each skipped run is announced by name.
  What sets `art-bible`'s **run count** is therefore not `review_mode`
  but (a) `modes.workflow`, via how many sections get authored at all — `standard`
  requires sections 1–4, not all 9, and Phase 1 recommends the tier's set — and
  (b) batching consecutive sections that call the *same* agent with the *same*
  input into one delegation (2–4, and 5–6). Unbatched, sections 5 and 6 run
  `art-director` twice with the identical `sections 1–4` brief. Every section is
  still specialist-authored; per-section approval and write-to-file are unchanged.
- **dev-story** core programmer routing (gameplay-programmer, ui-programmer, etc.)
  always runs regardless of mode — only the optional engine-specialist escalation
  for HIGH risk stories is gated.
- **hotfix** and **day-one-patch** are exempt — all agents always run.
- When a gate is skipped, skills emit: `"[GATE-ID] skipped — [mode] mode."` before
  proceeding. This is consistent across all skills.

---

## modes.rigor

**Controls:** How much process the project carries overall — the single question
`/start` asks that sets the six knobs below
**Values:** `minimal` | `standard` | `full`
**Default:** `minimal` — the rationale is the shipped default in `tools/gamestudio/config.py`. Short version: the heavier tier costs more to
reach working code without producing a better result.
**Set by:** `/start` (Phase 4: inferred from the user's description, shown, saved on a yes), `/settings`
**Read by:** nothing directly — it is read *through* the six knobs it supplies

**Priority chain:** `modes.rigor` in `project.toml` → hardcoded default `minimal`
(**locked** — not overridable from `project.local.toml`, like the four *on-disk*
knobs it fronts — `modes.workflow`, `docs.density`, `qa.level`,
`modes.story_granularity` — because those five change what artifacts exist on
disk. The two personal-experience knobs it also fronts, `modes.review_mode` and
`team.size`, stay locally overridable.)

---

### Expansion table

| `modes.rigor` | `modes.workflow` | `docs.density` | `qa.level` | `modes.story_granularity` | `modes.review_mode` | `team.size` |
|---|---|---|---|---|---|---|
| `minimal` *(default)* | `minimal` | `terse` | `minimal` | `coarse` | `solo` | `individual` |
| `standard` | `standard` | `balanced` | `standard` | `balanced` | `lean` | `individual` |
| `full` | `full` | `thorough` | `full` | `fine` | `full` | `studio` |

### It fronts, it does not replace

The expansion sits **below every explicit source and above the terminal
default**:

```
project.local.toml → project.toml → legacy file → rigor expansion → default
```

That ordering is the back-compat guarantee, and it is what makes the migration
free. Three consequences worth stating plainly:

- **An existing `project.toml` behaves identically.** If it already sets
  `docs.density: terse`, step 2 answers before the expansion is consulted — so
  the value and its reported source (`project.toml`) are unchanged whether or not
  `rigor` is present. No migration, no `schema_version` bump.
- **Overrides go both ways.** Unlike the `workflow_overrides` **boolean flags** —
  which are additive and stricter-only — an explicit knob may be *looser* than
  the rigor level implies.
  (`workflow_overrides.system_overrides` is also two-directional — it replaces a tier; only the flags are stricter-only.)
  Inheriting the stricter-only rule would make "comprehensive but compact"
  inexpressible, which is the one off-diagonal the docs have always cited.
- **`modes.workflow` keeps `workflow_overrides.system_overrides`.** Per-system
  tiers still beat the rigor-derived project tier. `workflow` was fronted rather
  than folded away precisely because it drives ~5 distinct behaviors and owns the
  only per-system override mechanism.

The six fronted knobs therefore have **no hardcoded default in `tools/gamestudio/config.py`**. A
terminal default there would answer before the expansion and make `rigor` a no-op
for anyone who had not also set the sub-knob.

### Provenance

Derived values report their source as `rigor:<level>`, so the vocabulary is
`{project.local.toml, project.toml, <legacy path>, rigor:<level>, default,
unset}`. `/settings` renders this as `(derived from rigor: standard)` and
force-appends the five to its view-all list — none of them is a leaf of either
TOML file, so enumerating file leaves alone would hide exactly the settings the
user just chose.

---

## modes.workflow

**Controls:** How much design documentation is required before code can begin —
the tradeoff between token/time cost of documentation and speed of reaching
working code  
**Values:** `full` | `standard` | `minimal`  
**Default:** *none* — supplied by `modes.rigor` (`minimal`, the default, yields `minimal`; `standard` yields `standard`; `full` yields `full`)  
**Set by:** `/start` (via `modes.rigor`), `/settings`  
**Read by:** See skill tables below

**Priority chain:** `modes.workflow` in `project.toml` → `modes.rigor` expansion → *(no hardcoded default)*

> **Why the middle level is `standard`, not `indie`.** A developer-type label
> would conflate "type of developer" with "level of process". `standard`
> describes the *amount of process*, not the user, and pairs cleanly with
> `minimal` and `full`.

> **Permissive, not restrictive:** `workflow` controls what is REQUIRED —
> not what is ALLOWED. Any skill can be run at any workflow level. The
> setting changes what gate-check enforces and what completeness checks
> validate, not what the user can invoke.

> **`minimal` floor:** Even in minimal mode, engine choice and a filled
> **`design/game-brief.md`** are required before code starts — the brief's
> build-order field is the plan, so there is no separate `sprint-plan` step.
> Both take minutes and prevent real problems downstream. Everything else can
> be skipped.

> **Escape hatches via `workflow_overrides`:** Users who want *almost* the
> standard set with one extra requirement (e.g. always force Edge Cases) use
> `workflow_overrides` rather than escalating to `full`. See next section.

---

### Value intent

| Value | Token/time cost | Required before code | Best for |
|-------|----------------|---------------------|----------|
| `full` | High | All 8 GDD sections per system, full architecture, all ADRs, art bible, UX specs per screen | Projects where design correctness matters more than speed — teams, commercial titles, learning the full pipeline |
| `standard` | Balanced | 5 GDD sections per system, one architecture doc, critical ADRs, game concept, systems index | Projects that have outgrown a brief — several interacting systems, or a design someone else has to implement |
| `minimal` | Low | One-page `design/game-brief.md` + engine choice (build order in the brief = the plan; no separate sprint plan) | **Default.** Get to code fast — small scope, jam projects, or the design already in your head. Raise it when the project grows |

**standard required GDD sections:** Overview, Detailed Rules, Edge Cases, Dependencies,
Acceptance Criteria.
**standard conditional:** Formulas — required when the system **defines numeric
rules**: rates, curves, thresholds, costs, damage, drop weights, or any value a
balance pass would tune. Optional only when the system defines no such value.

> **The test is what the system defines, not what it is called.** The `Category`
> column in `systems-index.md` is a *hint* — `Gameplay`, `Economy` and
> `Progression` systems almost always qualify — but it is not the test, and a
> `Core`, `UI` or `Persistence` system that defines a numeric rule qualifies too.
>
> Do not restate it as "required when system category is combat, economy,
> progression, or AI". Those four tokens are not the vocabulary `/map-systems`
> writes: `templates/systems-index.md` defines the categories as `Core ·
> Gameplay · Progression · Economy · Persistence · UI · Audio · Narrative ·
> Meta`, and lists **combat and AI as example systems under `Gameplay`**. A
> combat system categorised exactly as the template instructs therefore matched
> none of the four, and Formulas was silently dropped for the system most likely
> to need it. `coding-standards.md` and `rules/design-docs.md` already stated the
> "has math" test; the skills are reconciled to them rather than the other way
> round.

> **Edge Cases is required at `standard`.** Skipping it consistently produces
> "wait, what happens if X is null?" debt during implementation. These 5
> required sections are the minimum that produces implementable code.

> **Art bible is conditional in `standard`.** It is required only if visual
> asset stories exist in the project. Code-focused projects can skip it
> entirely at `standard` level.

---

### Authoring skills

| Skill | full | standard | minimal |
|-------|------|----------|---------|
| **design-system** | All 8 sections required | 5 required sections + conditional Formulas; Player Fantasy, Tuning Knobs skipped | Not required — game brief replaces GDDs. Can still be run voluntarily. |
| **art-bible** | All 9 sections required | Required only if visual asset stories exist; sections 1–4 minimum when required | Not required. Can still be run voluntarily. |
| **create-architecture** | Full architecture — all layers, module ownership, data flow, API boundaries, full ADR audit | Simplified — system layer map + critical ADR list only | Not required. Can still be run voluntarily. |
| **ux-design** | UX spec required per screen | Core screens only (main menu, HUD, primary game loop) | Not required. Can still be run voluntarily. |
| **map-systems** | Required before design-system | Required before design-system | Not required |
| **architecture-decision** | All ADRs on required ADR list must be completed | Critical ADRs only — Foundation layer systems | Not required |

---

### Review and validation skills

| Skill | full | standard | minimal |
|-------|------|----------|---------|
| **design-review** | All 8 sections validated — any missing section blocks approval | 5 required sections validated; missing optional sections warned but do not block | Not applicable — no GDDs to review |
| **review-all-gdds** | Validates all 8 sections across all GDDs | Validates 5 required sections across all GDDs; optional sections surfaced as advisory only | Not applicable |
| **architecture-review** | Full traceability matrix — all GDDs, all ADRs | Reduced scope — architecture doc + critical ADRs only | Not applicable |
| **consistency-check** | Full entity registry cross-check against all GDD sections | Entity registry check against required sections only | Not meaningful — no GDDs to check |
| **content-audit** | Full content count audit against all GDD specs | Limited audit — only specs in required sections counted | Cannot run — no systems index exists |

---

### Phase gate enforcement (gate-check)

`gate-check` is where workflow has the most visible impact — the artifact
checklists differ per phase per mode.

| Gate | full | standard | minimal |
|------|------|----------|---------|
| Concept → Systems Design | game-concept.md, pillars, Visual Identity Anchor | game-concept.md only | `design/game-brief.md` only (content check, not section check) |
| Systems Design → Technical Setup | systems-index, all MVP GDDs reviewed (8 sections), cross-GDD review | systems-index, 5-section GDDs reviewed, cross-GDD review optional | Not applicable — no gates between brief and code; the gate PASSes with that note |
| Technical Setup → Pre-Production | engine, art bible sections 1–4+, 3+ ADRs, architecture, UX specs started | engine, art bible only if visual assets, critical ADRs, architecture | engine configured (required floor) |
| Pre-Production → Production | sprint plan, complete art bible, epics, UX specs, control manifest; Vertical Slice + its playtest recommended (absent → CONCERNS) | epics, sprint plan; complete art bible, UX specs, control manifest recommended; Vertical Slice recommended | the brief's Build order + stories under `production/epics/`; the Vertical Slice items drop — the core loop is fun and runs end to end, checked on the current build |
| Production → Polish | core mechanics, tests, smoke check, QA sign-off, 3+ playtests | core mechanics, smoke check, playable end to end, 1+ playtest, no open S1 bugs | smoke check, playable end to end, no open S1 bugs |
| Polish → Release | all features, content complete, localization (`/localize qa` per locale), QA, smoke, no open S1–S3 bugs, newest `/security-audit` with no open CRITICAL/HIGH | all features, smoke, no open S1 bugs, the security audit | smoke, no open S1 bugs |

<!-- gate-check reconciliation: at `full` and `standard` the Vertical Slice
     keeps its long-standing "recommended, not blocking → CONCERNS if absent;
     FAIL if built-and-broken" status — the tier table never upgrades it to a
     hard blocker. At `minimal` its items drop, and two checks on the current
     build replace them. The genuinely-required floor item at this gate is the
     sprint plan at `standard`/`full`; at `minimal` there is no separate
     sprint-plan step — the brief's Build order plus stories is the floor at
     `minimal`. -->

**Director panel width** (`/gate-check` Section 4b) is workflow's second effect
here. Directors are `strong`-tier, so the panel is sized to the project rather than
fixed at four:

| `workflow` | Panel | Directors |
|---|---|---|
| `full` | 4 | `creative-director`, `technical-director`, `producer`, `art-director` |
| `standard` | 2 | `technical-director`, `producer` |
| `minimal` | 1 | `producer` |

`review_mode` remains the axis that decides *whether* the panel runs at all
(`solo` skips it entirely); workflow decides only how wide it is. Narrowing
never softens a verdict — the strictest verdict from whoever ran still wins, and
`/gate-check` names the perspectives that did not run.

---

### Planning and implementation skills

| Skill | full | standard | minimal |
|-------|------|----------|---------|
| **create-epics** | Requires all GDDs approved (8 sections) | Requires 5-section GDDs approved | **Skipped** (Option A) — no separate epic doc. `/create-stories` reads `design/game-brief.md` directly and synthesizes the implicit epic container itself. |
| **create-stories** | Requires all ADRs on required list present | Requires critical ADRs present | No ADR requirement |
| **dev-story** | Requires TR registry + governing ADR — blocks without them, and on a `Proposed`, `Deprecated` or `Superseded` ADR; a missing control manifest warns | TR registry optional; blocks only on a referenced ADR that is missing, `Proposed`, `Deprecated` or `Superseded` | No TR registry or ADR required — implements against `design/game-brief.md`; a referenced ADR that is missing, `Proposed`, `Deprecated` or `Superseded` still blocks |
| **story-readiness** | Full TR registry + ADR + control manifest validation; any referenced ADR that is missing, `Proposed`, `Deprecated` or `Superseded` BLOCKS | TR registry optional; critical ADR check, and any referenced ADR that is missing, `Proposed`, `Deprecated` or `Superseded` BLOCKS | Acceptance-criteria check (the brief stands in for the GDD); any referenced ADR that is missing, `Proposed`, `Deprecated` or `Superseded` still BLOCKS |
| **story-done** | Full GDD traceability + ADR consistency check | 5-section GDD traceability check | Acceptance criteria check only |
| **qa-plan** | Full test plan derived from all 8 GDD sections | Test plan from 5 required sections | Test plan from acceptance criteria only |
| **regression-suite** | Critical paths mapped from all sections including Edge Cases | Critical paths from required sections (including Edge Cases) | Smoke test coverage only |
| **release-checklist** | Open S1, S2 or S3 bug in `production/qa/bugs/` fails its Quality Gates item | Open S1 fails; open S2/S3 listed as risks | Open S1 fails; open S2/S3 listed as risks |
| **launch-checklist** | Zero open S1–S3 bugs, no exceptions | Zero open S1; S2 or a documented exception | Zero open S1; S2 or a documented exception |
| **team-release** | qa-lead verifies no open S1–S3 bugs | qa-lead verifies no open S1 bugs | qa-lead verifies no open S1 bugs |

---

### Support skills

| Skill | full | standard | minimal |
|-------|------|----------|---------|
| **project-stage-detect** | Checks for all doc types; missing art bible or UX specs flagged as gaps | Adjusts expectations — art bible only flagged if visual-asset stories exist; non-core UX specs not flagged | `design/game-brief.md` + engine present = normal state; no gaps flagged for absent GDDs |
| **adopt** | Full format compliance audit across all doc types | Audit scope reduced to required docs only | `design/game-brief.md` format check only |
| **reverse-document** | Generates full 8-section GDD from code | Generates 5-section GDD from code | Generates `design/game-brief.md` from code |
| **propagate-design-change** | Full cascading impact analysis across all ADRs | Checks critical ADRs for references only | Not applicable |
| **help** | Full artifact detection — surfaces all missing docs as next steps | Adjusts "what's missing" to required docs only — optional docs not surfaced as gaps | `design/game-brief.md` + engine present = next step is code |

---

### Workflow change mid-project

When `workflow` changes via `/settings`, the skill emits an informational note:

> "Workflow changed from [old] to [new]. Run `/content-audit` to see what's now
> required or extra. No automatic migration — existing files stay in place."

No documents are auto-deleted, auto-generated, or blocked. The setting only affects
*new* enforcement going forward.

---

## workflow_overrides

**Controls:** Opt-in granular requirements that override the chosen workflow level
**Location:** **top level of `project.toml`** — a sibling of `modes:`, *not* a child of it
**Values:** object with sub-flags (see below)
**Default:** all false / empty
**Set by:** `/settings`
**Read by:** `/design-system`, `/design-review`, `/art-bible`, `/gate-check`, `/review-all-gdds`, `/qa-plan`

> **Why the location is called out.** `python tools/studio.py config` reads
> `workflow_overrides.system_overrides.*` from the top-level `[workflow_overrides]`
> table, and every consuming skill uses the same top-level path. Nested under
> `[modes]` it is still valid TOML, so nothing errors — the setting is simply
> never read. It belongs at the top level, never under `[modes]`.

**Priority chain:** the three `workflow_overrides` **boolean flags**
(`edge_cases`, `tuning_knobs`, `art_bible_strict`) are *additive* on top of the
chosen `workflow` level — they make things stricter, never looser. None of them
has a value that opts out of a requirement the workflow level imposes.

> **`workflow_overrides.system_overrides` is not a flag and is not additive — it replaces a tier in both directions.**
> This rule does not extend to it. On a
> `full` project, `system_overrides.inventory: minimal` really does drop that
> system's required sections to zero. Intended — see
> `docs/studio/workflow-modes.md § workflow_overrides`. Stating the additive
> rule over the whole key is wrong: the guarantee never held for
> `system_overrides`, so do not rely on it as a safety net.

---

### Fields

```toml
[workflow_overrides]
edge_cases = false          # force Edge Cases section required (no-op at standard since already required; relevant at minimal)
tuning_knobs = false        # force Tuning Knobs section required (relevant at standard, no-op at full)
art_bible_strict = false    # force all 9 art bible sections required regardless of asset stories
# system_overrides: per-system tier overrides — see below
```

### Per-system overrides

```toml
[workflow_overrides.system_overrides]
combat = "full"              # combat-system GDD requires full (8 sections) regardless of project workflow
boss-encounters = "full"
inventory = "minimal"        # inventory needs no GDD — the game brief covers it (minimal = no required sections)
```

`system_overrides` is a map of `system_name: workflow_level`. The named system uses the override; all other systems use the project-level `workflow`.

---

### Affected skills

| Skill | How workflow_overrides changes behavior |
|-------|----------------------------------------|
| **design-system** | Reads `system_overrides[system_name]` first; falls back to project `workflow`. Applies override-specific section requirements. |
| **design-review** | Same lookup — validates against the override tier, not the project default, for the named system. |
| **art-bible** | If `art_bible_strict: true`, requires all 9 sections regardless of `workflow` level. |
| **gate-check** | Considers `system_overrides` when validating that all required GDDs are complete. A system at `system_overrides.combat: full` blocks the gate until all 8 sections exist for combat. |
| **review-all-gdds** | Validates each GDD against its effective tier (project workflow + any system override). |

---

## modes.automation

**Controls:** Whether skills ask for decisions and approval before acting, or
recommend and proceed — the tradeoff between user control and speed  
**Values:** `collaborative` | `guided` | `autonomous`  
**Default:** `collaborative`  
**Set by:** `/start`, `/settings`  
**Read by:** All 68 skills that use a question to the user or write files

**Priority chain:** `modes.automation` in `project.toml` → hardcoded default

> **Unlike review_mode and workflow, this setting is not a per-skill table.**
> It defines universal interaction rules that apply across all skills. A
> per-skill breakdown would repeat the same answer 68 times.

> **Overrides COLLABORATIVE-DESIGN-PRINCIPLE.md:** `guided` and `autonomous`
> modes intentionally relax the Q→O→D→Draft→Approval protocol defined in that
> document. This is opt-in. `collaborative` preserves the protocol exactly.

> **Safety net — `automation_always_ask`:** Even in `autonomous` mode, certain
> categories of decision can be configured to always prompt. See next section.

---

### Value intent

| Value | Speed | Control | What changes |
|-------|-------|---------|--------------|
| `collaborative` | Slowest | Full — every decision is the user's | Current behavior. Q→O→D→Draft→Approval strictly followed. |
| `guided` | Balanced | High — major decisions are the user's, minor ones proceed automatically | AI states recommendation and proceeds for minor decisions. a question to the user reserved for major/irreversible decisions. |
| `autonomous` | Fastest | Low — AI decides, logs, and proceeds | No a question to the user (except categories in `automation_always_ask`). No draft review. No write approval. All decisions logged to decision log. |

---

### Universal rules per mode

#### collaborative (current behavior — no change)

- Asks the user for every multi-option decision
- 2–4 options presented with pros/cons for every design choice
- Full draft shown and approved before every file write
- "May I write this to [filepath]?" asked before every write
- "May I create [filepath] with skeleton?" asked before skeleton creation
- Section-by-section approval in multi-section authoring skills
- Multi-file changes require explicit approval of the full changeset

#### guided

- Asks the user for **major decisions only** (see classification below)
- Minor decisions: AI states recommendation inline and proceeds — e.g.
  *"Going with a static utility pattern here — it fits the existing architecture.
  Continuing unless you want to change direction."*
- Updates to existing files: draft shown briefly before writing — proceeds after a
  short summary, does not wait for explicit "yes"
- "May I write?" asked for **new files only**, and a new file waits for the answer
  — updates to existing files proceed directly
- Still presents options for major decisions but caps at 2 choices with a clear
  recommendation
- Multi-section authoring: writes each approved section immediately, no per-section
  confirmation prompt

#### autonomous

- No questions to the user **except** for categories listed in `automation_always_ask`
- No draft review
- No "May I write?" prompts — writes directly
- Picks the recommended option for every decision without presenting alternatives
- All decisions logged immediately to `production/session-logs/decision-log.md`
  with: timestamp, skill, decision point, option chosen, reasoning
- User reviews decision log post-session to audit choices made

#### every mode — a question with no answer

- A question that comes back skipped, dismissed or empty is **not an answer**, in
  every mode and on every tool (a closed question, a headless run that returns
  every question as skipped, a reply that picks nothing)
- Nothing is written, no mode or setting changes and no option is picked on its
  behalf; the question is asked again in plain text, naming what waits on it
- `autonomous`: a question the mode did not require is decided and logged as
  usual; an `automation_always_ask` category or an exempt skill asks again
- Where nobody can answer (CI, headless), the skill stops and reports what is
  waiting rather than choosing

---

### Major vs minor decision classification (guided mode)

**Major — always use a question to the user in guided mode:**

| Decision type | Example |
|---------------|---------|
| Choosing a system name or document path | "What should we call this system?" |
| Mutually exclusive design directions | "Real-time or turn-based?" |
| Any choice that gates downstream work | Engine choice, architecture approach |
| Scope changes | "Cut this feature or slip the deadline?" |
| Any decision that can't be changed without significant rework | Core loop mechanic |

**Minor — AI recommends and proceeds in guided mode:**

| Decision type | Example |
|---------------|---------|
| Which section to work on next | "Moving to Edge Cases next" |
| Optional section inclusion | "Adding a Visual Notes section — fits the system" |
| Formatting and structure choices | Heading levels, table vs prose |
| Adding detail to an already-decided direction | Sub-options within an approved approach |
| Next-step routing after a phase completes | "Running design-review now" |

---

### Affected skills by category

**Authoring skills — highest impact.** Each pauses 10–15 times per document in
`collaborative`. Drops to 2–3 in `guided`, zero in `autonomous`.

`brainstorm`, `design-system`, `art-bible`, `create-architecture`, `ux-design`,
`map-systems`, `architecture-decision`, `create-epics`, `create-stories`,
`sprint-plan`, `prototype`

**Review skills — medium impact.** Pause after presenting findings to ask what
to do next. In `guided` routing decisions proceed automatically. In `autonomous`
the recommended path is taken and logged.

`design-review`, `architecture-review`, `gate-check`, `review-all-gdds`,
`story-readiness`, `story-done`, `milestone-review`, `playtest-report`

**Team orchestration skills — medium impact.** Pause between phases for
check-in. In `guided` the pipeline advances automatically unless BLOCKED. In
`autonomous` the full pipeline runs end to end.

`team-combat`, `team-ui`, `team-audio`, `team-qa`, `team-release`,
`team-narrative`, `team-polish`, `team-level`, `team-live-ops`

**Implementation skills — lower impact.** Pause for architectural questions
before writing code. In `guided` only genuinely ambiguous decisions stop. In
`autonomous` the conventional approach is picked and logged.

`dev-story`, `code-review`

**Setup and utility skills — lowest impact.** Pause for initial configuration
or routing questions. In `guided` defaults are applied automatically. In
`autonomous` recommended defaults are taken without prompting.

`start`, `adopt`, `setup-engine`, `retrospective`, `localize`, `propagate-design-change`,
`asset-spec`, `smoke-check`, `qa-plan`, `story-readiness`

---

### Exemptions — skills that ignore the automation setting

These skills always behave as `collaborative` regardless of the setting.
The reasons are noted.

| Skill | Why always collaborative |
|-------|--------------------------|
| **hotfix** | Emergency decisions — user must approve scope and risk before any action |
| **gate-check** | Results must be reviewed — a gate verdict without user acknowledgement defeats the purpose |
| **day-one-patch** | Release-critical — every action needs explicit sign-off |
| **setup-engine** | One-time irreversible choice that affects the entire project |

---

### Decision log format (autonomous mode)

Written to `production/session-logs/decision-log.md` — append-only.

```markdown
## [timestamp] — [skill-name]

**Decision point:** [what was being decided]
**Options considered:** [list of options that would have been presented]
**Chosen:** [what was picked]
**Reason:** [one-line rationale]
**Category:** [scope_changes | file_deletions | schema_changes | etc., or "minor"]
```

If the file does not exist, it is created. It is never truncated — each session
appends to the existing log.

---

## modes.automation_always_ask

**Controls:** Decision categories that ALWAYS trigger a question to the user regardless of automation mode
**Values:** list of category names
**Default:** `[scope_changes, file_deletions, schema_changes]`
**Set by:** `/settings`
**Read by:** All skills that respect `modes.automation`

> **Makes `autonomous` safe.** Without this, `autonomous` is "AI does literally
> everything, no questions asked." With it, AI does most things but stops on
> destructive or irreversible decisions you specifically named.

---

### Recognized categories

| Category | Examples of decisions in this category |
|----------|----------------------------------------|
| `scope_changes` | Cutting a feature, slipping a deadline, splitting/merging an epic, removing acceptance criteria |
| `file_deletions` | Removing a story, deleting a GDD, removing a system, removing a test file |
| `schema_changes` | Changes to project.toml, story template, control manifest, ADR template, GDD template |
| `architecture_decisions` | New ADR creation, ADR replacement, system boundary changes |
| `version_bumps` | Engine version change, framework version bump, dependency major version change |
| `external_calls` | Invoking external APIs (asset gen, AI services) when in autonomous mode |

The list is a TOML array of these strings. Skills check whether the current decision falls into one of the configured categories and prompt regardless of `automation` value.

---

### Affected skills

| Skill | Categories typically triggered |
|-------|--------------------------------|
| **scope-check** | `scope_changes` |
| **propagate-design-change** | `schema_changes`, `architecture_decisions` |
| **architecture-decision** | `architecture_decisions` |
| **setup-engine** | `version_bumps`, `schema_changes` |
| **story-done** | `file_deletions` (when removing/replacing test files) |
| **asset-spec** | `external_calls` (when calling external generators) |

---

## modes.story_granularity

**Controls:** How big each story is and how many stories per epic/sprint
**Values:** `coarse` | `balanced` | `fine`
**Default:** *none* — supplied by `modes.rigor` (`minimal`, the default, yields `coarse`; `standard` yields `balanced`; `full` yields `fine`)
**Set by:** `/start` (via `modes.rigor`), `/settings`
**Read by:** `/create-stories`, `/sprint-plan`, `/sprint-status`, `/story-readiness`

**Priority chain:** `modes.story_granularity` in `project.toml` → `modes.rigor` expansion → *(no hardcoded default)*

---

### Value intent

| Value | Story shape | Stories per sprint | Best for |
|-------|-------------|-------------------|----------|
| `coarse` | 1 story = 1 feature. 3–5 days work each. 5–10 ACs per story. The default, from `rigor: minimal`. | 2–4 | Solo devs, prototyping, "I know what I'm building" |
| `balanced` | 1 story = 1 task. 1–2 days work each. 2–4 ACs per story. The `rigor: standard` value. | 6–10 | Most projects |
| `fine` | 1 story = 1 AC. Hours of work each. Easy code review. Frequent /story-done. | 15–25 | Teams, learning, anything needing fine handoffs |

---

### Affected skills

| Skill | coarse | balanced | fine |
|-------|--------|----------|------|
| **create-stories** | Each story carries 5–10 ACs covering an entire feature | Each story carries 2–4 ACs covering one task | Each story carries 1 AC; story name = AC restatement |
| **sprint-plan** | Allocates 2–4 stories per sprint based on velocity. | Allocates 6–10 stories per sprint. | Allocates 15–25 stories per sprint. |
| **sprint-status** | Burn-down reads in feature-sized chunks. | Burn-down reads in task-sized chunks. | Burn-down reads in AC-sized chunks. |

---

## docs.density

**Controls:** How deep each section in authored docs goes — independent of which sections are required
**Values:** `terse` | `balanced` | `thorough`
**Default:** *none* — supplied by `modes.rigor` (`minimal`, the default, yields `terse`; `standard` yields `balanced`; `full` yields `thorough`)
**Set by:** `/start` (via `modes.rigor`), `/settings`
**Read by:** `/design-system`, `/art-bible`, `/create-architecture`, `/ux-design`, `/map-systems`, `/brainstorm`

**Priority chain:** `docs.density` in `project.toml` → `modes.rigor` expansion → *(no hardcoded default)*

> **Distinct from `workflow`, but not independent by default.** `workflow`
> controls which sections exist; `density` controls how deep each section goes.
> `modes.rigor` sets both together, so the diagonal (`rigor: full` → 8
> sections *and* thorough prose) is what you get without asking. The off-diagonal
> is still reachable and is the reason `rigor` overrides both ways: `rigor: full`
> + an explicit `docs.density: terse` gives "all sections but each is compact" —
> the "comprehensive but tight" mode, which neither knob expresses alone.

---

### Value intent

| Value | Per-section output style |
|-------|--------------------------|
| `terse` | Bullet points. 2–5 lines per section. Skip rationale and narrative framing. Skip preambles like "In this game..." Just facts needed to implement. The default, from `rigor: minimal`. |
| `balanced` | Paragraphs with light rationale. Examples where helpful. The `rigor: standard` value. |
| `thorough` | Full prose. Rationale for every decision. Examples, alternatives considered, design history. |

---

### Combination matrix with workflow

|  | docs.density: terse | balanced | thorough |
|---|---|---|---|
| **workflow: minimal** | Game brief in bullets *(default)* | Game brief in prose | Game brief + rationale |
| **workflow: standard** | 5 sections, bullets | 5 sections, paragraphs | 5 sections + examples |
| **workflow: full** | 8 sections, bullets *(comprehensive but compact)* | 8 sections, paragraphs *(current full)* | 8 sections + rationale + examples |

---

### Affected skills

| Skill | terse | balanced | thorough |
|-------|-------|----------|----------|
| **design-system** | Each GDD section is 2–5 bullets. Skip Player Fantasy preambles. | Paragraphs with key decisions explained. | Full prose, decision history, alternatives considered. |
| **art-bible** | Each art bible section is a bulleted list of constraints + references. | Paragraphs explaining each visual choice. | Full prose including style explorations, references, rationale per choice. |
| **create-architecture** | Layer diagrams + decision bullets. No essays. | Diagrams + paragraph explanations of layer choices. | Full prose with rationale, trade-offs, alternatives considered per layer. |
| **ux-design** | Wireframe descriptions + interaction bullets. | Wireframes + paragraph descriptions of flows. | Full prose including user research summaries, alternative flow considerations. |
| **map-systems** | One-line system descriptions. | Brief paragraph per system + dependency notes. | Full system-by-system rationale + relationship analysis. |
| **brainstorm** | Pillar bullets + concept bullets. | Pillars + concept with brief rationale. | Pillars + concept + extensive rationale + alternatives. |

---

## testing.framework

**Controls:** Which test framework the project uses — drives test-runner commands and per-engine assumptions in CI
**Values:** engine-specific (see table)
**Default:** auto-populated by `/setup-engine` based on engine choice
**Set by:** `/setup-engine`, `/settings`
**Read by:** `/test-helpers` — the only skill that references it. `/qa-plan`, `/dev-story`, `/regression-suite`, `/test-setup` and `/smoke-check` do **not** name the key, despite being plausible readers.
  *(Derived by grep. A helper-based read such as `session_state_enabled()` would not show up, so treat this list as the verified floor, not a ceiling.)*

**Priority chain:** `testing.framework` in `project.toml` → engine default

> **Migrated from `technical-preferences.md`.**

---

### Engine defaults

| Engine | Default test framework | Alternatives |
|--------|------------------------|--------------|
| Unity | `unity-test-framework` | `nunit`, custom |

---

### Affected skills

| Skill | How `testing.framework` is used |
|-------|--------------------------------|
| **qa-plan** | Test plan tailored to framework's idioms (assertion style, fixture pattern, parameterized tests) |
| **dev-story** | Test framework name passed to programmer role pass in implementation brief |
| **regression-suite** | Test file naming and discovery patterns match framework conventions |
| **test-setup** | Scaffolds the right test layout for the engine (the engine's test root and project files, from the engine step) |
| **smoke-check** | Invokes framework-appropriate test runner |

---

## testing.strict

**Controls:** Whether failing or missing test evidence blocks a story from
closing, or produces a warning and lets work continue — per test type
**Values:** map of `{logic, integration, visual, ui, config}` → `true | false`
**Default:** `{logic: true, integration: true, visual: true, ui: true, config: false}`
**Set by:** `/settings`
**Read by:** `story-done`, `story-readiness`, `gate-check`, `smoke-check`, `dev-story`, `test-evidence-review`

> **Per-type, not a single bool.** A global `testing.strict: true|false` forces
> all-or-nothing: either all test failures block or none do. Per-type matches how
> most teams actually work — strict logic and visual gates, an advisory smoke check.

> **Composes with `qa.level`:** `qa.level` controls whether evidence is REQUIRED.
> `testing.strict` controls whether failures BLOCK when evidence exists. If
> `qa.level: minimal`, the strict map is effectively ignored (no evidence required
> means nothing to be strict about).

---

### Value intent per type

| Type | `true` | `false` |
|------|--------|---------|
| `logic` (formulas, AI, state machines) | Unit test failures BLOCK — story cannot close | Failures WARN — story can close with warning |
| `integration` (multi-system) | Integration test failures BLOCK | Failures WARN |
| `visual` (animation, VFX, feel) | Missing/failing screenshot evidence BLOCKS (default) | Advisory only — story can close |
| `ui` (menus, HUD, screens) | Missing screenshot of the screen BLOCKS (default) | Advisory only — story can close |
| `config` (balance tuning) | Failing smoke check BLOCKS | Advisory only — story can close (default) |

---

### Affected skills

| Skill | strict.[type]: true | strict.[type]: false |
|-------|---------------------|----------------------|
| **story-done** | Story of that type cannot close on test/evidence failure | Story can close; warning logged in story file |
| **story-readiness** | Validates test requirements exist before implementation — blocks if absent | Validates but does not block — surfaces as warnings |
| **gate-check** | CI failures of that type block phase transition | CI failures of that type surfaced as concerns, not blockers |
| **smoke-check** | Failing smoke (config strict) blocks QA handoff | Failing smoke flagged but handoff proceeds |
| **dev-story** | References test requirements — flags story as unverifiable if absent | References test requirements — advisory only |
| **test-evidence-review** | A gap in that type's evidence is a BLOCKING item (the run ends CONCERNS) | The gap is ADVISORY |

> **Unset-key resolution.** Each skill reads `testing.strict.<type>`; if absent
> it reads `testing.strict` as a plain boolean (legacy form); if still absent it
> falls back to a hardcoded default. For `story-done`, `story-readiness`,
> `gate-check`, and `dev-story` the hardcoded default is the per-type default map
> above (logic/integration/visual/ui strict, config advisory). **`smoke-check` is
> the exception**: it is a build-health gate, so an unset `testing.strict.config`
> defaults to *strict* (a FAIL blocks QA hand-off) — preserving its v1.0 behavior.
> Only an explicit `testing.strict.config: false` makes a failing smoke advisory.

---

## qa.level

**Controls:** What test evidence is required to mark stories Done
**Values:** `minimal` | `standard` | `full`
**Default:** *none* — supplied by `modes.rigor` (`minimal`, the default, yields `minimal`; `standard` yields `standard`; `full` yields `full`)
**Set by:** `/start` (via `modes.rigor`), `/settings`
**Read by:** `/story-done`, `/story-readiness`, `/dev-story`, `/smoke-check`, `/gate-check`, `/qa-plan`, `/regression-suite`, `/team-qa`, `/test-evidence-review`, `/create-stories`, `/retrospective`, `/test-setup`

**Priority chain:** `qa.level` in `project.toml` → `modes.rigor` expansion → *(no hardcoded default)*

> **Different axis from `testing.strict`.** `qa.level` = what evidence is required.
> `testing.strict` = do failures block. A user wanting "minimal QA" sets
> `qa.level: minimal` and the strict map becomes effectively a no-op.

---

### Value intent

| Aspect | minimal | standard | full |
|--------|---------|----------|------|
| Logic stories | No test required, no gap flagged | Unit test required (strict.logic controls block) | Unit test, and every acceptance criterion covered |
| Integration stories | No test required | Integration test or playtest doc required | Same + regression coverage |
| Visual stories | Screenshot + lead sign-off required — the look is never waived (strict.visual controls block) | Same | Same |
| UI stories | Screenshot of each screen touched required — never waived (strict.ui controls block) | Same | Same |
| Config/Data stories | No evidence required | Smoke check advisory | Smoke check required (blocking unless `testing.strict.config: false`) |
| /story-done test gate | Acceptance criteria only, except the UI and Visual/Feel screenshot, which is never waived | Enforced per story type | Enforced for every story type |
| /gate-check phase enforcement | No test gates | Logic + integration must pass | Full coverage + regression suite |
| /dev-story routing prompt | No "Test required: ..." line | Per-type test requirement included | Per-type, and every criterion must be covered |
| Regression suite required by | Never | Polish stage | Production stage |
| Best for | Jam games, throwaway prototypes, fast iteration | Most projects | Commercial, console cert, learning, paranoid teams |

---

### Affected skills

| Skill | minimal | standard | full |
|-------|---------|----------|------|
| **story-done** | Acceptance criteria check only — no test evidence required, except the UI and Visual/Feel screenshot, which is never waived | Per-type evidence required; strictness from `testing.strict`; more than half the criteria untested blocks | Per-type evidence required; a Config/Data smoke report blocks by default; any untested criterion blocks |
| **story-readiness** | No test requirement validated, except the UI and Visual/Feel screenshot requirement | Test requirement per story type validated | Test requirement + coverage target validated |
| **dev-story** | Routing prompt has no "Test required" line | Per-type test requirement passed to programmer agent | Per-type requirement, and every criterion must be covered by a test |
| **smoke-check** | Optional; with no game tests (WAIVED), `commands.smoke` (else `commands.build`) when set and the launch and critical-path checks carry the verdict; a build nobody launched is NOT ASSESSED | Required before phase transition | Required before every commit |
| **gate-check** | No test enforcement at phase transitions | Logic + integration tests must pass | Full coverage check + regression suite |
| **qa-plan** | Skipped entirely or minimal smoke plan | Full plan per story type | Full plan + coverage targets per system |
| **regression-suite** | Not generated | Generated at Polish stage entry | Generated at Production stage entry |
| **team-qa** | A Logic, Integration or Config/Data story without a test is WAIVED; its acceptance-criteria walk in manual QA is its evidence | The automated test is the evidence for those types | Same |
| **test-evidence-review** | A story with no test evidence is WAIVED, not MISSING; gaps in existing tests are ADVISORY; screenshots never waived | Per-type evidence reviewed; BLOCKING/ADVISORY from `testing.strict` | Same |

---

## qa.coverage_minimum

**Controls:** Minimum code coverage percentage enforced at `qa.level: full`
**Values:** integer 0–100, or `null` for unset
**Default:** `null`
**Set by:** `/settings`
**Read by:** `/gate-check` only. `/story-done` does not reference the key, and no CI runner reads it.
  *(Derived by grep. A helper-based read such as `session_state_enabled()` would not show up, so treat this list as the verified floor, not a ceiling.)*

**Priority chain:** `qa.coverage_minimum` in `project.toml` → no enforcement if `null`

> **Only meaningful at `qa.level: full`.** Ignored at minimal and standard. A
> non-null value at standard or minimal level emits a warning at session-start:
> *"coverage_minimum is set but qa.level is not full — value will not be enforced."*

> **Implementation is engine-specific.** Coverage measurement differs per engine and test framework. This template does not unify them — gate-check reads the report the engine layer names.

---

## strict_gate_checks

> ### RESERVED - NOT IMPLEMENTED
>
> **No skill or helper reads this setting. Setting it has no effect.** Everything
> below describes the intended design, not current behaviour.
>
> The value is not checked when you set it, and nothing reads it.

**Controls:** Whether phase gate failures block stage transition or just warn
**Values:** `true` | `false`
**Default:** `true`
**Set by:** `/settings`
**Read by:** nothing yet (intended reader: `/gate-check`)

**Priority chain:** `strict_gate_checks` in `project.toml` → hardcoded default of `true`

> **Different from `review_mode: solo`.** `review_mode: solo` skips the gate
> *entirely* — directors don't even run. `strict_gate_checks: false` runs the
> gate normally but treats the verdict as advisory.

---

### Value intent

| Value | Behavior |
|-------|----------|
| `true` | Default. FAIL or BLOCKING-CONCERNS verdict stops the stage transition. `project.stage` is not advanced. User must address findings and re-run gate. |
| `false` | All gate verdicts are advisory. `/gate-check` still runs and reports findings. `project.stage` advances on user confirmation regardless of verdict. |

---

### Affected skills

| Skill | true | false |
|-------|------|-------|
| **gate-check** | FAIL verdict stops execution before writing new stage; CONCERNS verdict prompts user but defaults to "stay at current stage." | All verdicts surfaced as informational; user is asked "advance anyway?" with default Yes. |

---

## team.size

**Controls:** Which agents are active by default — solo devs shouldn't get studio-grade gating on every change
**Values:** `individual` | `small` | `studio`
**Default:** *none* — supplied by `modes.rigor` (`minimal`/`standard` yield `individual`, `full` yields `studio`)
**Set by:** `/start` (via `modes.rigor`), `/settings`
**Read by:** All `team-*` skills, `/gate-check`, all skills that run agents

**Priority chain:** `team.size` in `project.local.toml` → `project.toml` → the `modes.rigor` expansion (`full` → `studio`, else `individual`) → no terminal default. Locally overridable — it is a personal-experience knob, not an on-disk artifact.

> **`individual` at `minimal`/`standard`, `studio` at `full`.** this template's audience is
> overwhelmingly solo indie developers, so the two lighter rigor tiers resolve
> `team.size` to `individual` — a `minimal` (default) or `standard` project gets one active agent
> per role, not 15 (directors and leads included). Only `rigor: full` opts into the
> full `studio` roster; a smaller team on a big project sets `team.size: small`
> explicitly, which wins over the rigor-derived value.

> **Different axis from `workflow`.** `workflow` controls *what docs are required.*
> `team.size` controls *which agents exist to make them.* A solo dev on
> `workflow: full` still doesn't need all 49 agents — they need the same coverage
> from a smaller active set.

---

### Active agent set per value

| Value | Active set | Notes |
|-------|-----------|-------|
| `individual` | Core 8: `producer`, `game-designer`, `gameplay-programmer`, engine-specialist (engine-driven), `technical-artist`, `sound-designer`, `qa-tester`, `writer`. **Default.** | Directors and lead-* run only on explicit invocation (e.g. via `/architecture-decision`). Specialists outside the core 8 routed through their nearest core agent. Each `team-*` skill names its own set per value, which can sit outside the core 8 (`team-release` runs `release-manager`); each skill's own `team.size` list is authoritative, and the Affected skills table below mirrors it. |
| `small` | Core 15: directors (CD, TD, PR) + leads (LP, AD, QL, ND) + game-designer + systems-designer + engine-specialist + technical-artist + sound-designer + qa-tester + ux-designer + writer | `team-*` skills add their `small` set (below); most reach their full pipeline only at `studio`. |
| `studio` | All 49 agents available. Engine sub-specialists (e.g. `unity-dots-specialist` separate from `unity-specialist`) routed when relevant. The adversarial review pass in `team-combat`, `team-ui` and `team-polish`. | Commercial titles, learning the full org chart, large teams with parallel work. |

---

### Affected skills

| Skill | individual | small | studio |
|-------|------|-------|--------|
| **team-combat** | Single agent (gameplay-programmer) runs the pipeline; ai-programmer escalated only if AI work flagged | Default pipeline as documented | Default + the primary engine specialist may use its sub-specialists + adversarial review pass (Phase 5's qa-tester looks for how it breaks) |
| **team-narrative** | writer only; narrative-director invoked only on explicit pillar conflict | narrative-director + writer, + localization-lead and world-builder at `review_mode: full` | All six narrative agents, whatever the review mode |
| **team-ui** | ui-programmer + ux-designer | + accessibility-specialist + art-director | + engine UI specialist + adversarial review pass (Phase 4's reviewers look for where it fails its spec) |
| **team-audio** | sound-designer only | + audio-director + technical-artist + gameplay-programmer | + accessibility-specialist + the primary engine specialist |
| **team-level** | level-designer only | + systems-designer + art-director + qa-tester | + narrative-director + world-builder + accessibility-specialist |
| **team-qa** | qa-tester only; qa-lead invoked at phase gates only | qa-lead + qa-tester pipeline | qa-lead + per-story qa-tester run + sign-off |
| **team-release** | release-manager only | + producer + devops-engineer + qa-lead + community-manager | + security-engineer + analytics-engineer + localization-lead + performance-analyst, and network-programmer when the game is multiplayer |
| **team-polish** | performance-analyst + technical-artist; no programmer is active, so Phase 2's optimisation list is handed to `/dev-story` | + sound-designer + qa-tester + engine-programmer (implements Phase 2's optimisation list), and tools-programmer when Phase 1 traces a cause to a content authoring tool | engine-programmer, as at small, + adversarial review pass (Phase 5's qa-tester looks for how it breaks) |
| **team-live-ops** | live-ops-designer + economy-designer | + analytics-engineer + community-manager | + writer + narrative-director |
| **gate-check** | Panel width is `modes.workflow`'s axis, not this one (gates always run) — `team.size` affects only specialist depth within each director's review | Same as individual for directors; specialists within directors' reviews use small set | Same plus engine sub-specialists |
| **architecture-decision** | TD-ADR (in `full` review mode) + the primary engine specialist | Same | Same — no sub-specialist or adversarial reviewer at any size |

---

### Special cases

- `team.size` does not decide whether directors run: `/gate-check`'s panel follows `review_mode` and `modes.workflow`, and no `team-*` pipeline runs a director phase gate. In a team skill, a "phase gate" is one of the decision points its own pipeline lists, whatever the `automation` mode.
- `individual` does not disable agents — it just changes which are active by default. Any agent can still be invoked by name.
- When `team.size: individual` and a non-core agent is needed (e.g. `network-programmer` for a multiplayer story), the skill emits an informational note and routes through the nearest active core agent.

---

## platform.multiplayer

**Controls:** Whether the project includes real-time online multiplayer — determines
which specialists are routed and which architecture sections are required  
**Values:** `true` | `false`  
**Default:** none — unset is not `false`  
**Set by:** `/settings`  
**Read by:** `security-audit`, `team-release` (and the `security-engineer` agent)

**Priority chain:** `platform.multiplayer` in `project.toml` → unset (`platform.*` is locked to `project.toml`, so `project.local.toml` cannot set it). Nothing writes it except `/settings`, so on most projects it is unset: `/security-audit` and `/team-release` ask whether the game is multiplayer rather than reading unset as `false`.

> **Distinct from `platform.online`.** `multiplayer` is *real-time multiplayer
> specifically* (network specialist, netcode review, replication architecture).
> `platform.online` covers everything else online (cloud saves, leaderboards,
> telemetry). See next section.

> **This is a project attribute, not a mode.** It describes what the game is,
> not how the pipeline operates. It lives in `platform` alongside `targets`,
> `primary_input`, and `gamepad_support` — not in `modes`.

---

### Value intent

| Value | Meaning |
|-------|---------|
| `true` | Game has real-time online multiplayer. `/security-audit` runs its netcode category and rates a HIGH finding as release-blocking; `/team-release` adds `network-programmer`'s sign-off. |
| `false` | No real-time multiplayer. `/security-audit` skips the netcode category and says so; `/team-release` does not act as `network-programmer` (read `roles/network-programmer.md`). |

---

### Affected skills

| Skill | multiplayer: true | multiplayer: false |
|-------|------------------|-------------------|
| **security-audit** | Includes netcode review — authentication, replication, cheat vectors | Netcode review skipped, and the report says so |
| **team-release** | `network-programmer` included in release sign-off pipeline | `network-programmer` excluded |

No other skill reads this key: `/dev-story`, `/create-architecture` and `/gate-check`
decide networking scope from the story, GDD or architecture in front of them.

---

## platform.online

**Controls:** Whether the project has any online features (leaderboards, cloud saves, telemetry, IAP)
**Values:** `true` | `false`
**Default:** none — unset is not `false`
**Set by:** `/settings`
**Read by:** `security-audit`, `team-release` (and the `security-engineer` agent)

**Priority chain:** `platform.online` in `project.toml` → unset (`platform.*` is locked to `project.toml`, so `project.local.toml` cannot set it). Nothing writes it except `/settings`: `/security-audit` and `/team-release` ask rather than reading unset as `false`.

> **Independent of `platform.multiplayer`.** A single-player game with Steam
> Cloud and leaderboards is `online: true, multiplayer: false`. The two settings
> have different specialist routing implications.

---

### Value intent

| Value | Meaning |
|-------|---------|
| `true` | Project includes online services (cloud saves, leaderboards, achievements, telemetry, IAP, anything calling external APIs at runtime). `/security-audit` runs Category 2 (network and multiplayer — including a plaintext-token check) when this or `platform.multiplayer` is true or unset; `/team-release` adds a `security-engineer` sign-off. |
| `false` | Project is fully offline. `/security-audit` skips Category 2 only when `platform.multiplayer` is also false. |

---

### Affected skills

| Skill | online: true | online: false |
|-------|--------------|---------------|
| **security-audit** | Category 2 (network) runs — server authority, packet validation, rate limits, plaintext tokens | Category 2 skipped only when `platform.multiplayer` is also false |
| **team-release** | `security-engineer` sign-off when the game is online or stores player data | No online-driven security sign-off |

No other skill reads this key: `/create-architecture`, `/dev-story`, `/team-live-ops`
and `/gate-check` decide online scope from the documents in front of them.

---

## platform.cert_tier

> ### WIRED — this setting is live
>
> `/launch-checklist` and `/release-checklist` both resolve it and branch on its
> four values — `none` emits no certification section, `itch` and `steam` their
> storefront's requirements, `console` full platform certification — and ask which
> platforms are in scope when it is unset.

**Controls:** Certification target — scopes what `/launch-checklist` asks for
**Values:** `none` | `itch` | `steam` | `console`
**Default:** *none* — unset stays unset, so the skills ask
**Set by:** `/settings` — nothing else writes it, so it stays unset (and the skills ask) until you set it
**Read by:** `/launch-checklist`, `/release-checklist`

**Priority chain:** `platform.cert_tier` in `project.toml` → unset (no default is
substituted: unset is a missing decision, `none` is a made one, and the skills
must tell them apart)

---

### Value intent

| Value | Required compliance | Best for |
|-------|---------------------|----------|
| `none` | No certification | Internal releases, alphas, jam games (an explicit choice — unset is not `none`) |
| `itch` | itch.io upload requirements (build size, page setup, age tags) | Indie web/desktop releases |
| `steam` | Steamworks integration, store page, achievements, depot build, system requirements, common content rules | Commercial PC releases |
| `console` | Platform certification (PlayStation/Xbox/Switch) — heavy compliance: TRC/XR/Lotcheck, save data rules, controller mapping rules, age rating boards | Console releases |

---

### Affected skills

| Skill | none | itch | steam | console |
|-------|------|------|-------|---------|
| **launch-checklist** | Internal launch only — no external requirements | + itch.io page setup, butler upload, build size | + Steamworks integration, store page, achievements depot, common content checks | + Platform-specific TRC, certification submission, console save format compliance |
| **release-checklist** | Smoke pass + version bump only | + itch.io page live, build uploaded to butler | + Steam store page live, depot pushed, achievements live | + Platform submission accepted, age rating boards cleared |

---

## accessibility.target

> ### RESERVED - NOT IMPLEMENTED
>
> **No skill or helper reads this setting. Setting it has no effect.** Everything
> below describes the intended design, not current behaviour.
>
> The value is checked for valid spelling when you set it, and then ignored.
> The accessibility-specialist routing and the Polish-stage audit described
> below **do not happen at any level** — `/team-ui`, `/team-level`,
> `/team-polish` and `/gate-check` do not read this setting, and `/start`
> does not ask for it.

**Controls:** Accessibility commitment level — routes accessibility specialist and gates audit requirements
**Values:** `none` | `standard` | `aaa`
**Default:** `none`
**Set by:** `/settings`
**Read by:** nothing yet (intended readers: `/team-ui`, `/team-level`, `/team-polish`, `/gate-check`)

**Priority chain:** `accessibility.target` in `project.toml` → hardcoded default of `none`

> **Default is `none`, not `standard`.** Most users are solo devs and jam-game
> makers — defaulting to `standard` would auto-run the accessibility specialist
> for projects where it's overhead. `/start` does not ask about it; you set it with
> `/settings`.

---

### Value intent

| Value | Required features | Specialist routing |
|-------|-------------------|--------------------|
| `none` | None enforced | `accessibility-specialist` not run |
| `standard` | Colorblind-safe palette, subtitles for any voice content, key remapping | `accessibility-specialist` runs in team-ui, team-level |
| `aaa` | Full Game Accessibility Guidelines: motor, vision, hearing, cognitive categories | `accessibility-specialist` runs in all team-* skills; mandatory audit at Polish stage |

---

### Affected skills

| Skill | none | standard | aaa |
|-------|------|----------|-----|
| **team-ui** | accessibility-specialist not run | accessibility-specialist included for HUD/menu reviews | accessibility-specialist included for every screen + accessibility audit pass |
| **team-level** | accessibility-specialist not run | accessibility-specialist reviews level for colorblind safety and signposting | accessibility-specialist reviews for full mobility/audio/cognitive considerations |
| **team-polish** | No accessibility pass | Final accessibility pass added | Full accessibility audit required before completion |
| **gate-check** | No accessibility check at any stage | Polish gate checks for the standard required features | Polish gate requires full Game Accessibility Guidelines compliance audit |

---

## cadence.sprint_length and cadence.milestone_length

> ### RESERVED - NOT IMPLEMENTED
>
> **No skill or helper reads this setting. Setting it has no effect.** Everything
> below describes the intended design, not current behaviour.
>
> No reference anywhere outside this file.

**Controls:** Default sprint and milestone durations for planning
**Values:**
- `sprint_length`: `1w` | `2w` | `3w` | `4w` | `none`
- `milestone_length`: `4w` | `6w` | `8w` | `12w`
**Defaults:** `sprint_length: 2w`, `milestone_length: 8w`
**Set by:** `/settings`
**Read by:** nothing yet (intended readers: `/sprint-plan`, `/milestone-review`, `/sprint-status`, future velocity tracking)

**Priority chain:** `cadence.*` in `project.toml` → hardcoded defaults

> **`none` for `sprint_length`** means continuous-flow / kanban-style — no sprint boundaries.
> `/sprint-plan` is then invoked manually as needed. Velocity tracking
> is per-week rather than per-sprint.

---

### Affected skills

| Skill | What changes |
|-------|--------------|
| **sprint-plan** | Capacity calculated as `sprint_length × team.size velocity baseline`. `none` makes the skill emit a continuous-flow plan instead. |
| **milestone-review** | Milestone window for retrospective scope = `milestone_length`. |
| **sprint-status** | Burn-down chart x-axis spans `sprint_length`. |
| **retrospective** | Sprint retro fires at `sprint_length` cadence (or weekly when sprint_length is `none`). |

---

## performance.target_framerate and performance.frame_budget_ms

**Controls:** The frame-rate target and its per-frame millisecond budget
**Values:** integers (e.g. `60`, `16.67`)
**Default:** none — unset means no budget was ever committed to
**Set by:** the user, by hand or via `/settings`
**Read by:** `/perf-profile`, `/gate-check`, `/team-polish`

## performance.draw_call_limit and performance.memory_ceiling_mb

**Controls:** Per-frame draw-call ceiling and total memory ceiling
**Values:** integers
**Default:** none — unset means no budget was ever committed to
**Set by:** the user, by hand or via `/settings`
**Read by:** `/perf-profile`, `/gate-check`, `/team-polish`

> **Every setting needs its own `## ` heading in this file, not just a table
> row.** The dead-settings audit derives what it checks from those headings, so
> a setting mentioned only inside a table is invisible to it — it can neither be
> reported DEAD if it loses its reader, nor caught if it gains one. A setting
> outside the audit's field of view is exactly how a documented-but-dead entry,
> or a working-but-listed-as-dead one, survives unnoticed.
>
> **Unset is not zero and not a default.** A budget nobody set is not a budget
> that was met — `/perf-profile` must report `NOT ASSESSED` for a metric with no
> committed target rather than measuring against a placeholder. A headroom figure
> computed against an invented budget, with no profiler data behind it, reads as
> a pass and is not one; see obligations 1 and 2 in `rules/skill-authoring.md`.

## performance.enforce

**Controls:** Whether performance budget violations warn or block
**Values:** `warn` | `block` | `off`
**Default:** `warn`
**Set by:** `/settings`
**Read by:** `/perf-profile`, `/gate-check`, CI runner

**Priority chain:** `performance.enforce` in `project.local.toml` → `project.toml` → hardcoded default of `warn`, resolved by `resolve_config --keys performance.enforce`

> **Read it from the resolved block, never from `project.toml` directly.** The key is on the `/settings --local` whitelist. `/perf-profile` Phase 0 and `/gate-check` Section 3 are the two readers the table above promises — a key that is enum-validated, accepted and displayed while nothing reads it is exactly the failure this warning guards against.

> **Mirrors the `testing.strict` pattern.** Defines what happens when a budget
> defined in `performance.target_framerate`, `frame_budget_ms`, `draw_call_limit`,
> or `memory_ceiling_mb` is exceeded.

---

### Value intent

| Value | Behavior |
|-------|----------|
| `warn` | Default. Profile runs flag violations as findings. CI logs them but doesn't fail. `/gate-check` surfaces them as concerns, not blockers. |
| `block` | Profile failures block CI. `/gate-check` treats violations as FAIL verdict (Polish stage onward). |
| `off` | Performance budgets are informational only — no profile runs gated, no findings surfaced. |

---

## project.stage

**Controls:** The current development phase — determines which gate-check
validates and what artifacts are expected to exist  
**Values:** `Concept` | `Systems Design` | `Technical Setup` | `Pre-Production` | `Production` | `Polish` | `Release`  
**Default:** `Concept`  
**Set by:** `/gate-check` on a PASS, or on a CONCERNS the user explicitly accepts (the accepted risks are recorded); a FAIL never advances it — never set manually  
**Read by:** `gate-check`, `project-stage-detect`, `help`, `day-one-patch`, `team-release`, `launch-checklist`, `release-checklist`, `map-systems`, `team-qa`, `adopt`

> **Stage count:** This document uses the
> 7-stage reality implemented by gate-check:
> `Concept | Systems Design | Technical Setup | Pre-Production | Production | Polish | Release`

> **This is a project attribute, not a mode.** It records where the project is
> in its lifecycle. Only `/start` (at onboarding) and `/gate-check` write it —
> `/gate-check` on a PASS verdict with user confirmation, or on a CONCERNS
> verdict whose risks the user explicitly accepts (they are recorded); a FAIL never advances it.
> Never write it manually mid-session except to correct an incorrect auto-detect.

> **Fallback.** Stage is read from `project.stage` in
> `project.toml` first, then `production/stage.txt`, then artifact
> auto-detection. `/gate-check` and `/start` write the stage with
> `python tools/studio.py set-stage`, which keeps both in step.

---

### Stage progression and gate requirements

Each row is the gate that must be passed to advance FROM that stage.

| From stage | Key artifacts required to pass | gate-check writes |
|------------|-------------------------------|-------------------|
| **Concept** | `game-concept.md`, design pillars, Visual Identity Anchor | `Systems Design` |
| **Systems Design** | `systems-index.md`, all MVP GDDs reviewed, cross-GDD consistency check | `Technical Setup` |
| **Technical Setup** | Engine configured, art bible sections 1–4 (at `standard`, only if visual stories exist), 3+ ADRs, architecture doc, traceability index, test framework, accessibility and interaction-pattern docs | `Pre-Production` |
| **Pre-Production** | Epics defined, first sprint plan, UX specs, control manifest (a Vertical Slice is recommended, not required) | `Production` |
| **Production** | Core mechanics implemented, main path playable, smoke check passes, QA sign-off | `Polish` |
| **Polish** | All features complete, content complete, localization, security audit, no open S1–S3 bugs | `Release` |

Gates adjust per `modes.workflow` — see `modes.workflow` section for what is
required at `standard` and `minimal` levels.

---

### Affected skills

| Skill | How it uses stage |
|-------|------------------|
| **gate-check** | Reads current stage to determine which gate to validate. Writes next stage on PASS, or on a CONCERNS the user explicitly accepts. |
| **project-stage-detect** | Reads `project.stage` first — if set, uses it as authoritative. Falls back to heuristic detection only if absent. |
| **help** | Uses stage to determine "where are you in the pipeline" and surfaces the correct next steps. |
| **sprint-status** | Displays current stage in status summary. |
| **day-one-patch** | Proceeds only when the stage is `Release` or `Polish`; otherwise says it is not appropriate yet. |
| **team-release** | Stops before Phase 1 unless the stage is `Release` ("run `/gate-check release` first"); proceeding takes an explicit override, recorded in the go/no-go record and the report. Never writes the stage. |

---

## project.kind

> ### RESERVED - NOT IMPLEMENTED
>
> **No skill or helper reads this setting. Setting it has no effect.** Everything
> below describes the intended design, not current behaviour.
>
> No reference anywhere outside this file.

**Controls:** What type of project this is — routes skill subsets
**Values:** `game` | `tool` | `engine` | `mod` | `library`
**Default:** `game`
**Set by:** `/start`, `/setup-engine`
**Read by:** Many skills (advisory routing — see below)

**Priority chain:** `project.kind` in `project.toml` → hardcoded default of `game`

---

### Value intent

| Value | Meaning | What's deactivated |
|-------|---------|-------------------|
| `game` | Default. Full framework applies. | Nothing |
| `tool` | Developer tool, not a game | Skip art bible, narrative, level design, playtesting |
| `engine` | Custom engine or library underneath games | Skip game-specific concerns entirely (narrative, art, playtest) |
| `mod` | Mod for an existing game | Skip engine setup; assume parent engine; reduce architecture scope |
| `library` | Reusable library | Emphasize tests + API design; design docs lighter; no asset pipeline |

---

### Affected skills

| Skill | game | tool | engine | mod | library |
|-------|------|------|--------|-----|---------|
| **brainstorm** | Full game-concept output | Tool concept output (user, problem, solution) | Engine concept (target use cases, scope) | Mod concept (what changes) | Library concept (API surface, target consumers) |
| **art-bible** | Required at appropriate workflow level | Skipped | Skipped | Optional (depends on visual scope) | Skipped |
| **map-systems** | Full game systems decomposition | Tool subsystems | Engine subsystems | Modified-system map | Library module map |
| **playtest-report** | Required at appropriate stages | Skipped or replaced with user testing | Skipped | Required (compatibility testing) | Skipped or replaced with API usage testing |
| **setup-engine** | Game engine setup | Skipped or replaced with build tool setup | Self-referential — engine IS the project | Parent engine assumed | Skipped or replaced with library scaffolding |

---

## engine.name and specialists

**Values:** the engine's name, lower case (for example `unity`). Empty until `/setup-engine` sets it.

**Written by:** `/setup-engine`. **Read by:** every skill that resolves an engine specialist (`<engine>-specialist`), the code-root resolution in `docs/studio/code-root-resolution.md`, and the engine layer (`engine.toml`, `ENGINE.md`).

Base ships no engine specialists. An engine fork adds `roles/<engine>-*.md`; a skill that wants one resolves it from `engine.name` and, when no such role exists, says so and goes on without it.

---

## commands

**Written by:** `/setup-engine`, `/settings`. **Read by:** `/smoke-check`, `/hotfix` (narrowed to the affected suite), `/bug-report` (verify mode) and `/dev-story` (the parse or build check) through `testing.command` and `commands.build`, `commands.run`, `commands.smoke`.

```toml
[commands]
build = ""   # the engine's build or export command; ask the user, never guess
run   = ""   # launches the game windowed
smoke = ""   # boots the game headless for a few seconds
```

```toml
[testing]
command = ""   # the test runner command CI also runs
```

A value may be a map of operating system to command (`default`, `windows`, `macos`), and the skill reads the current OS and picks the matching key.

An empty value means "not configured": the skill reports `NOT RUN — <key> unset` and never invents a command. The engine layer (`ENGINE.md`) gives the commands to write.

---

## naming

**Written by:** `/setup-engine`. **Read by:** nothing enforces it; the coding standards (`docs/studio/coding-standards.md`) and `/code-review` read it as guidance.

| Field | Values | Meaning |
|---|---|---|
| `files` | `snake_case` \| `PascalCase` \| `kebab-case` | Source file names |
| `classes` | `PascalCase` | Type names |
| `variables` | `camelCase` \| `snake_case` | Variable names |
| `events` | `past_tense` \| `on_event_name` | Event or signal names |

No skill or helper validates code *against* these conventions.

---

## features.session_state

**Type:** `on` | `off`. **Default:** `on`. **Local override:** yes.

**Controls:** whether the session checkpoint file `production/session-state/active.md` is kept and previewed.

**Read by:** `python tools/studio.py session-state` (the checkpoint preview, capped at 25 lines) and `python tools/studio.py rotate-session-state`. No skill branches on it.

| Value | Behavior |
|---|---|
| `off` | `session-state` prints nothing about the checkpoint. Recovery relies on skeleton-first output files: long-form skills write a complete skeleton (all section headers, empty bodies) before starting. |
| `on` | `session-state` previews the checkpoint at the start of a session, and reports when the narrative below it is long enough to rotate. |

The checkpoint format is in `docs/studio/context-management.md`.

---

## features.token_budget_warn_at

**Status:** accepted and validated, not read by anything in this template.

No skill or helper reads this key; `python tools/studio.py config` accepts it so a `project.toml` written for the upstream project keeps validating. Setting it has no effect.

---

## features.read_guard

**Status:** accepted and validated, not read by anything in this template.

No skill or helper reads this key; `python tools/studio.py config` accepts it so a `project.toml` written for the upstream project keeps validating. Setting it has no effect.

---

## features.read_guard_kb

**Status:** accepted and validated, not read by anything in this template.

No skill or helper reads this key; `python tools/studio.py config` accepts it so a `project.toml` written for the upstream project keeps validating. Setting it has no effect.

---

## updates.check

**Status:** accepted and validated, not read by anything in this template.

No skill or helper reads this key; `python tools/studio.py config` accepts it so a `project.toml` written for the upstream project keeps validating. Setting it has no effect.

---

## schema_version

**Controls:** Which version of the project.toml schema this file conforms to
**Values:** integer
**Default:** `1`
**Set by:** the template
**Read by:** `python tools/studio.py config` and `check`, which reject a schema they do not know

> Lets future template versions detect and migrate old project.toml files. The
> migration logic compares `schema_version` in the file against the current
> the template's expected version. If newer, warn. If older, run migrations.

---

### Migration behavior

| project.toml schema_version | Current template expects | Behavior |
|----------------------------|---------------------|----------|
| Matches expected | — | Normal operation |
| Lower than expected | — | `/adopt` warns and offers migration; skills run with deprecation warnings |
| Higher than expected | — | All skills warn: "This project.toml was created by a newer template version. Some settings may be ignored." |
| Missing | — | Treated as legacy (pre-v1.1); migration prompted on next `/start` or `/adopt` |

---

## framework

**Controls:** Records which template version the project came from
**Values:** `framework.source` (the template it came from) and `framework.version` (the version)
**Default:** empty in the template; set by `python tools/studio.py update`
**Set by:** `python tools/studio.py update`
**Read by:** `python tools/studio.py status` and `update`; no skill branches on it.

---

### Fields

```toml
[framework]
source = "../game-studio-base"
version = "0.1.0"
```

| Field | Purpose |
|-------|---------|
| `source` | The template the project was last updated from. |
| `version` | The template version it was updated to. |

---

### Affected skills

None. No skill reads `framework.*`. They record which template version the project came from; `python tools/studio.py update` is the upgrade path.

---

## Complete example `project.toml`

A fully populated file for a small Unity project. Use this as the reference shape when authoring one.

```toml
schema_version = 1

[framework]
source = "../game-studio-base"
version = "0.1.0"

[project]
name = "My Game"
stage = "Concept"            # Concept | Systems Design | Technical Setup | Pre-Production | Production | Polish | Release

[modes]
rigor = "minimal"            # minimal | standard | full — fronts the six knobs below
# review_mode = "solo"       # full | lean | solo (derived from rigor when unset)
# workflow = "minimal"
automation = "collaborative" # collaborative | guided | autonomous
automation_always_ask = ["scope_changes", "file_deletions", "schema_changes"]

[workflow_overrides]
edge_cases = false
tuning_knobs = false
art_bible_strict = false

[workflow_overrides.system_overrides]
# combat = "full"

[engine]
name = "unity"
version = "6.3 LTS"
language = "C#"

[testing]
command = ""                 # the runner command CI also runs

[testing.strict]
logic = true
integration = true
visual = true
ui = true
config = false

[commands]
build = ""
run = ""
smoke = ""

[performance]
enforce = "warn"
target_framerate = 60
frame_budget_ms = 16.6
draw_call_limit = 2000
memory_ceiling_mb = 2048

[docs]
density = "terse"

[qa]
level = "minimal"

[team]
size = "individual"

[claude]
sync = true                  # Claude Code add-on files; false turns it off
```

Machine-local overrides go in `project.local.toml` (gitignored), limited to the whitelist in "Local Override Pattern".
