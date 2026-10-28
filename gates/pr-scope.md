---
id: PR-SCOPE
role: producer
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# PR-SCOPE — Scope and Timeline Validation

Role: `producer` | Model tier: strong | Domain: Scope, timeline, dependencies, production risk

**Trigger**: After scope tiers are defined (brainstorm Phase 6, map-systems Phase
4, or any workflow that produces an MVP definition and timeline estimate)

**Context to pass**:
- Full vision scope description
- MVP definition
- Timeline estimate
- Team size (solo / small team / etc.)
- Scope tiers (what ships if time runs out)

**Prompt**:
> "Review this scope estimate. Is the MVP achievable in the stated timeline for
> the stated team size? Are the scope tiers correctly ordered by risk — does each
> tier deliver a shippable product if work stops there? What is the most likely
> cut point under time pressure, and is it a graceful fallback or a broken product?
> Return REALISTIC (scope matches capacity), OPTIMISTIC [specific adjustments
> recommended], or UNREALISTIC [blockers — timeline or MVP must be revised]."

**Verdicts**: REALISTIC / OPTIMISTIC / UNREALISTIC
