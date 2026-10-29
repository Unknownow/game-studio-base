---
id: CD-NARRATIVE
role: creative-director
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# CD-NARRATIVE — Narrative Consistency Check

Role: `creative-director` | Model tier: Opus | Domain: Vision, pillars, player experience

**Trigger**: Invoked directly, after narrative GDDs, lore documents, dialogue specs
or world-building documents are authored — no skill runs it; `/team-narrative`
runs its own review, ND-CONSISTENCY

**Context to pass**:
- Document file path(s)
- Game pillars
- Narrative direction brief or tone guide (if exists at `design/narrative/`)
- Any existing lore that the new document references

**Prompt**:
> "Review this narrative content for consistency with the game's pillars and
> established world rules. Does the tone match the game's established voice? Are
> there contradictions with existing lore or world-building? Does the content serve
> the player experience pillar? Return APPROVE, CONCERNS [specific inconsistencies],
> or REJECT [contradictions that break world coherence]."

**Verdicts**: APPROVE / CONCERNS / REJECT
