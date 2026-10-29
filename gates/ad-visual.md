---
id: AD-VISUAL
role: art-director
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# AD-VISUAL — Art Director Visual Consistency Review

Role: `art-director` | Model tier: session (inherit)

**Trigger**: After art direction decisions are made, when new asset types are
introduced, or when a tech art decision affects visual style

**Context to pass**:
- Art bible path (if exists at `design/art/art-bible.md`)
- The specific asset type, style decision, or visual direction being reviewed
- Reference images or style descriptions
- Platform and performance constraints

**Prompt**:
> "Review this visual direction decision for consistency with the established art
> style and production constraints. Does it match the art bible? Is it achievable
> within the platform's performance budget? Are there asset pipeline implications
> that create technical risk? Return APPROVE, CONCERNS [specific adjustments], or
> REJECT [style violation or production risk that must be resolved first]."

**Verdicts**: APPROVE / CONCERNS / REJECT
