# /adopt — Phase 2: Format Audit

> Part of `/adopt`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## Phase 2: Format Audit

**In this file:**

- 2a: GDD Format Audit
- 2b: ADR Format Audit
- 2c: systems-index.md Format Audit
- 2d: Story Format Audit
- 2e: Infrastructure Audit
- 2f: Project Config Audit
- 2g: Missing Config Check

For each artifact type in scope (based on argument mode **and the resolved
workflow tier**), check not just that the file exists but that it contains the
internal structure the template requires. At `minimal`, scope the audit to
`design/game-brief.md` — do not audit for GDDs, ADRs, or UX specs (they are not expected).
Steps 2e (the Engine reference row only), 2f (project config) and 2g (missing
config check) run at every tier.

### 2a: GDD Format Audit

**Gather section presence deterministically — do not read the GDDs to count
headings.** For each GDD discovered in Phase 1, pass its path explicitly to the
structure-check script:

```
Bash: python tools/studio.py gdd-structure-check [path-to-gdd]
```

**Pass paths one at a time; do not invoke it bare.** The no-argument form sweeps
`design/gdd/` only, and a brownfield project's GDDs are not guaranteed to live
there — pass whatever paths Phase 1 found. The script prints a `PRESENT:` list
and, when applicable, an `ABSENT:` list per file. It reports **presence only**
and makes no REQUIRED/ADVISORY judgment (that is the tier logic below), and it
already accepts `## Detailed Design` as satisfying the `Detailed Rules`
requirement, so do not flag that alias as missing.

If the script prints `Not found:` for a path or errors, that is a **discovery
failure, not a format gap** — report it as "could not audit [path]" and do not
count it as a missing-sections finding.

**Then apply the workflow tier** resolved above to each file's PRESENT/ABSENT
lists. Which sections are **required** (a miss = gap) vs **advisory** (a miss =
informational):
- **`full`** — all 8 sections are required.
- **`standard`** — the 5 required (Overview, Detailed Rules, Edge Cases,
  Dependencies, Acceptance Criteria) + Formulas for any system that defines
  numeric rules (rates, curves, thresholds, costs — the system's `Category` is a
  hint, not the test); Player Fantasy and Tuning Knobs are advisory.
- **`minimal`** — GDDs are not expected; audit `design/game-brief.md` instead,
  against `templates/game-brief.md`: each of the six required fields
  present and not a placeholder; the three one-liners advisory. Any GDD that
  does exist is checked at the `standard` bar, advisorily.

The script's 8 canonical labels are: Overview, Player Fantasy, Detailed Rules,
Formulas, Edge Cases, Dependencies, Tuning Knobs, Acceptance Criteria.

A section reported PRESENT can still be an empty heading. For each GDD, also
record with a targeted grep (not a full read):
- Placeholder-only sections — the script's `PLACEHOLDER:` line names the
  present sections that hold only `[To be designed]` or nothing; a
  single-line stub body is the same in effect, so spot-check short sections.
- The `**Status**:` header field — `Grep pattern="^>?[[:space:]]*\*\*Status\*\*:"`.
  Valid values: `Draft`, `In Design`, `Designed`, `In Review`, `Approved`,
  `Implemented`, `Needs Revision`.

> **The `>?` is load-bearing, and so are `Draft`/`Implemented`.** Both emitters
> write this field inside a blockquote — `templates/game-design-document.md`
> and `/design-system` produce `> **Status**: …` — so an anchor of
> `^\*\*Status\*\*:` matches nothing and reports *every* template-compliant GDD
> as missing its Status. The template's own value list offers `Draft` and
> `Implemented`, so both must count as valid.

### 2b: ADR Format Audit

For each ADR file found, check for these critical sections:

| Section | Impact if missing |
|---|---|
| `## Status` | **BLOCKING** — `/story-readiness` ADR status check silently passes everything |
| `## ADR Dependencies` | HIGH — dependency ordering in `/architecture-review` breaks |
| `## Engine Compatibility` | HIGH — post-cutoff API risk is unknown |
| `## GDD Requirements Addressed` | MEDIUM — traceability matrix loses coverage |
| `## Performance Implications` | LOW — not pipeline-critical |

For each ADR, record: which sections present, which missing, current Status value
if the Status section exists.

### 2c: systems-index.md Format Audit

If `design/gdd/systems-index.md` exists:

1. **Parenthetical status values** — Grep for any Status cell containing
   parentheses: `"Needs Revision ("`, `"In Progress ("`, etc.
   These break exact-string matching in `/gate-check`, `/create-stories`,
   and `/architecture-review`. **BLOCKING.**

2. **Valid status values** — check that Status column values are only from:
   `Not Started`, `In Progress`, `In Review`, `Designed`, `Approved`, `Needs Revision`
   Flag any unrecognised values.

3. **Column structure** — check that the table has at minimum: System name,
   Layer, Priority, Status columns. Missing columns degrade skill functionality.

### 2d: Story Format Audit

For each story file found:

- **`Manifest Version:` field** — present in story header? (LOW — auto-passes if absent)
- **TR-ID reference** — does story contain `TR-[a-z]+-[0-9]+` pattern? (MEDIUM — no staleness tracking)
- **ADR reference** — does story reference at least one ADR? (check for `ADR-` pattern)
- **Status field** — present and readable?
- **Acceptance criteria** — does the story have a checkbox list (`- [ ]`)?

### 2e: Infrastructure Audit

| Artifact | Path | Impact if missing |
|---|---|---|
| TR registry | `docs/architecture/tr-registry.yaml` | HIGH — no stable requirement IDs |
| Control manifest | `docs/architecture/control-manifest.md` | HIGH — no layer rules for stories |
| Manifest version stamp | In manifest header: `Manifest Version:` | MEDIUM — staleness checks blind |
| Sprint status | `production/sprint-status.yaml` | MEDIUM — `/sprint-status` falls back to markdown |
| Stage file | `project.stage` in `project.toml` (fallback `production/stage.txt`) | MEDIUM — phase auto-detect unreliable |
| Engine reference | `engine-reference/[engine]/VERSION.md` | HIGH — ADR engine checks blind |
| Architecture traceability | `docs/architecture/requirements-traceability.md` | MEDIUM — no persistent matrix |

At `workflow: minimal` only the Engine reference row applies. The TR registry,
control manifest and its version stamp, sprint status, stage file and
traceability matrix are not on the minimal path, so their absence is not a gap.

### 2f: Project Config Audit

Read `project.toml` (the primary config store) and `docs/technical-preferences.md` (legacy mirror). A setting counts as configured if EITHER source has a real value (in technical-preferences.md, `[TO BE CONFIGURED]` means unconfigured):
- `engine.name`/`version`/`language`/`rendering`/`physics` (else the Engine/Language/Rendering/Physics fields) → HIGH if unconfigured in both (ADR skills fail)
- `naming.*` (else Naming conventions) → MEDIUM
- `performance.*` (else Performance budgets) → MEDIUM
- Forbidden Patterns, Allowed Libraries (technical-preferences.md only — not migrated to project.toml) → LOW (starts empty by design)

### 2g: Missing Config Check

A project **needs its config created** when `project.toml` does NOT exist at the
repo root. A project's engine, language and testing settings may then sit only in
a prose `docs/technical-preferences.md`, or in nothing at all.

Do not write `project.toml` during the audit — Phase 2 reads silently. Classify
it as **BLOCKING** in Phase 3: until `project.toml` exists, every skill reads
config through the `docs/technical-preferences.md` fallback and the settings in
`docs/studio/settings-guidance.md` are unavailable. Phase 7 offers
`python tools/studio.py setup` and `/setup-engine` as the first action, which
create it.

---
