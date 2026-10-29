## Summary

Brief description of what this PR does.

## Type of Change

- [ ] New role
- [ ] New skill
- [ ] New rule, gate or template
- [ ] New or changed CLI command or helper
- [ ] Bug fix
- [ ] Documentation improvement
- [ ] Other:

## Changes

-
-
-

## Checklist

- [ ] `python tools/studio.py check` reports 0 errors
- [ ] `python -m unittest discover -s tools/gamestudio/tests -t tools -q` passes
- [ ] New roles carry the Collaboration Protocol section and valid `tier:` / `can:` frontmatter
- [ ] New skills use the folder format (`.agents/skills/<name>/SKILL.md`) and only portable frontmatter keys
- [ ] Reference docs are updated (agent-roster, skills-reference, rules-reference)
- [ ] `UPSTREAM.toml` maps or ignores every new upstream file
- [ ] No hardcoded paths or platform-specific assumptions
