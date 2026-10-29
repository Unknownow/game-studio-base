# Role Tiers

Every role in `roles/` carries a `tier:` line in its frontmatter. The tier says how much reasoning the role's work needs. It is a hint for your agent tool, not a model ID: map each tier to whichever model your tool offers, so this page does not change when a new model ships.

| Tier | Meaning | When to use |
|------|---------|-------------|
| `strong` | The strongest model you have | Multi-document synthesis, high-stakes phase gate verdicts, cross-system holistic review |
| `standard` | A balanced model | Implementation, design authoring, analysis of individual systems — the default for most work |
| `inherit` | Whatever the session already runs | Roles that need no particular model |

## How to apply a tier

- **A tool that can pick a model per role** (a sub-agent feature): set the role's model from its tier. `python tools/studio.py claude-sync` does this for Claude Code when the add-on is on.
- **A tool that cannot**: ignore the tier and run the whole session on one model. Nothing breaks; high-stakes verdicts are just less likely to get the strongest model.
- When you act as a role yourself (`Act as <role>: read roles/<role>.md`), run that step on the model you would pick for the tier if you can switch, and say in your report if you could not.

## Which roles are `strong`

The three directors (`creative-director`, `technical-director`, `producer`) and the roles that give final verdicts at a gate. Run `grep -l "^tier: strong" roles/*.md` for the current list.

## Skills have no tier

Skills are plain checklists and run on whatever model the session uses. When a skill needs the strongest model for its verdict (`/architecture-review`, `/gate-check`, `/review-all-gdds`), say so to the user before starting rather than switching silently.

## When you add a role

Assign `standard` unless the role must synthesise five or more documents or give a final verdict that blocks the project; assign `strong` then. Use `inherit` only for a role whose work is mechanical.
