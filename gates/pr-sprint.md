---
id: PR-SPRINT
role: producer
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# PR-SPRINT — Sprint Feasibility Review

Role: `producer` | Model tier: Opus | Domain: Scope, timeline, dependencies, production risk

**Trigger**: Before finalising a sprint plan (`/sprint-plan`), and after any
mid-sprint scope change

**Context to pass**:
- Proposed sprint story list (titles, estimates, dependencies)
- Team capacity (hours available)
- Current sprint backlog debt (if any)
- Milestone constraints

**Prompt**:
> "Review this sprint plan for feasibility. Is the story load realistic for the
> available capacity? Are stories correctly ordered by dependency? Are there hidden
> dependencies between stories that could block the sprint mid-way? Are any stories
> underestimated given their technical complexity? Return REALISTIC (plan is
> achievable), CONCERNS [specific risks], or UNREALISTIC [sprint must be
> descoped — identify which stories to defer]."

**Verdicts**: REALISTIC / CONCERNS / UNREALISTIC
