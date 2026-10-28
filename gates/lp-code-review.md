---
id: LP-CODE-REVIEW
role: lead-programmer
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# LP-CODE-REVIEW — Lead Programmer Code Review

Role: `lead-programmer` | Model tier: standard

**Trigger**: After a dev story is implemented (`/dev-story`, `/story-done`), or
as part of `/code-review`

**Context to pass**:
- Implementation file paths
- Story file path (for acceptance criteria)
- Relevant GDD section
- ADR that governs this system

**Prompt**:
> "Review this implementation against the story acceptance criteria and governing
> ADR. Does the code match the architecture boundary definitions? Are there
> violations of the coding standards or forbidden patterns? Is the public API
> testable and documented? Are there any correctness issues against the GDD rules?
> Return APPROVE, CONCERNS [specific issues], or REJECT [must be revised before merge]."

**Verdicts**: APPROVE / CONCERNS / REJECT
