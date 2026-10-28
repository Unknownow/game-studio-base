---
id: CD-PILLARS
role: creative-director
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# CD-PILLARS — Pillar Stress Test

Role: `creative-director` | Model tier: strong | Domain: Vision, pillars, player experience

**Trigger**: After game pillars and anti-pillars are defined (brainstorm Phase 4,
or any time pillars are revised)

**Context to pass**:
- Full pillar set with names, definitions, and design tests
- Anti-pillars list
- Core fantasy statement
- Unique hook ("Like X, AND ALSO Y")

**Prompt**:
> "Review these game pillars. Are they falsifiable — could a real design decision
> actually fail this pillar? Do they create meaningful tension with each other? Do
> they differentiate this game from its closest comparables? Would they help resolve
> a design disagreement in practice, or are they too vague to be useful? Return
> specific feedback for each pillar and an overall verdict: APPROVE (strong), CONCERNS
> [list] (needs sharpening), or REJECT (weak — pillars do not carry weight)."

**Verdicts**: APPROVE / CONCERNS / REJECT
