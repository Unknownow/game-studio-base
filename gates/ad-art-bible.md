---
id: AD-ART-BIBLE
role: art-director
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# AD-ART-BIBLE — Art Bible Sign-Off

Role: `art-director` | Model tier: session (inherit) | Domain: Visual identity, art bible, visual production readiness

**Trigger**: After the art bible is drafted (`/art-bible`), before asset production begins

**Context to pass**:
- Art bible path (`design/art/art-bible.md`)
- Game pillars and core fantasy
- Platform and performance constraints (`platform.*` and `performance.*` from `project.toml`, falling back to `docs/technical-preferences.md`)
- Visual identity anchor chosen during brainstorm (from `design/gdd/game-concept.md`; if there is no `design/gdd/game-concept.md`, pass the "Art & audio direction" line of `design/game-brief.md` instead)

**Prompt**:
> "Review this art bible for completeness and internal consistency. Does the color
> system match the mood targets? Does the shape language follow from the visual
> identity statement? Are the asset standards achievable within the platform
> constraints? Does the character design direction give artists enough to work from
> without over-specifying? Are there contradictions between sections? Would an
> outsourcing team be able to produce assets from this document without additional
> briefing? Return APPROVE (art bible is production-ready), CONCERNS [specific
> sections needing clarification], or REJECT [fundamental inconsistencies that must
> be resolved before asset production begins]."

**Verdicts**: APPROVE / CONCERNS / REJECT
