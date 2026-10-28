# Role Coordination Rules

These rules apply when work is split across roles (see `roles/`), whether one agent plays each role in
turn or your tool runs several agents.

1. **Vertical Delegation**: Leadership roles delegate to department leads, who
   delegate to specialists. Never skip a tier for complex decisions.
2. **Horizontal Consultation**: Roles at the same tier may consult each other
   but must not make binding decisions outside their domain.
3. **Conflict Resolution**: When two roles disagree, escalate to the shared
   parent. If no shared parent, escalate to `creative-director` for design
   conflicts or `technical-director` for technical conflicts.
4. **Change Propagation**: When a design change affects multiple domains, the
   `producer` role coordinates the propagation.
5. **No Unilateral Cross-Domain Changes**: A role must never modify files
   outside its designated directories without explicit delegation.
6. **Read Design Docs by Section**: A brief names the sections a role needs
   by heading. Find a heading in a GDD, ADR or the art bible (`python tools/studio.py md-section list <file>`)
   and read that range; read a doc whole only when the task needs all of it, and say why. Docs over
   about 40 KB are never read whole.
7. **Nothing Goes Upstream**: Never file, open or comment on an issue or pull
   request in an engine, plugin or vendor repository, even when asked. Write a
   draft (`/bug-report` drafts only) and the user submits it.

## Working as a role

A skill that says **Act as `<role>`** means: read `roles/<role>.md`, then do that step with that role's
perspective, domain and limits (its `can:` list and its "must not do" section). Hand the result to the
next step in the form the skill names. If your tool can run a separate sub-agent, you may hand the step to
one: give it the role file path, the brief and the output path. Otherwise do the step yourself, in turn.
Either way the role's output goes to the file the skill names; a step whose named file is not on disk did not run
(`docs/studio/error-recovery-protocol.md`).

## Parallel steps

When a skill lists steps as independent (neither needs the other's output), do them in either order, or in
parallel when your tool can. Collect every result before the dependent phase. If any step is BLOCKED, surface
it immediately; never skip it silently. Always produce a partial report if some steps complete and others block.

## Model tiers

A role's `tier:` (`strong`, `standard` or `inherit`) says how capable a model it deserves. Tools that let
you pick a model per role should use the strongest for `strong` roles. Tools that do not can ignore it.
`python tools/studio.py claude-sync` maps the tiers to Claude Code models.
