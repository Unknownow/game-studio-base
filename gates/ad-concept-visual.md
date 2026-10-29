---
id: AD-CONCEPT-VISUAL
role: art-director
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# AD-CONCEPT-VISUAL — Visual Identity Anchor

Role: `art-director` | Model tier: session (inherit) | Domain: Visual identity, art bible, visual production readiness

**Trigger**: After game pillars are locked (brainstorm Phase 4), in turn with CD-PILLARS

**Context to pass**:
- Game concept (elevator pitch, core fantasy, unique hook)
- Full pillar set with names, definitions, and design tests
- Target platform (if known)
- Any reference games or visual touchstones mentioned by the user

**Prompt**:
> "Based on these game pillars and core concept, propose 2-3 distinct visual identity
> directions. For each direction provide: (1) a one-line visual rule that could guide
> all visual decisions (e.g., 'everything must move', 'beauty is in the decay'), (2)
> mood and atmosphere targets, (3) shape language (sharp/rounded/organic/geometric
> emphasis), (4) color philosophy (palette direction, what colors mean in this world).
> Be specific — avoid generic descriptions. One direction should directly serve the
> primary design pillar. Name each direction. Recommend which best serves the stated
> pillars and explain why."

**Verdicts**: CONCEPTS (multiple valid options — user selects) / STRONG (one direction clearly dominant) / CONCERNS (pillars don't provide enough direction to differentiate visual identity yet — name each pillar that gives none, and which of the four elements above it leaves open)
