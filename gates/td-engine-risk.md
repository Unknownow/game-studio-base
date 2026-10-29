---
id: TD-ENGINE-RISK
role: technical-director
---

> Gate definition. The role running this gate reads this file; see `docs/studio/director-gates.md`.

# TD-ENGINE-RISK — Engine Version Risk Review

Role: `technical-director` | Model tier: Opus | Domain: Architecture, engine risk, performance

**Trigger**: When making architecture decisions that touch post-cutoff engine APIs,
or before finalizing any engine-specific implementation approach

**Context to pass**:
- The specific API or feature being used
- Engine version and LLM knowledge cutoff (from `engine-reference/[engine]/VERSION.md`)
- Relevant excerpt from breaking-changes or deprecated-apis docs

**Prompt**:
> "Review this engine API usage against the version reference. Is this API present
> in [engine version]? Has its signature, behaviour, or namespace changed since the
> LLM knowledge cutoff? Are there known deprecations or post-cutoff alternatives?
> Return APPROVE (safe to use as described), CONCERNS [verify before implementing],
> or REJECT [API has changed — provide corrected approach]."

**Verdicts**: APPROVE / CONCERNS / REJECT
