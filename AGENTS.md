# Game Studio — Agent Instructions

An engine-agnostic game studio template for AI agents and people working together. Skills are
numbered checklists you follow; roles are the perspectives you take; one Python command line
checks the project. Any agent or human can use it. Adapted from Claude Code Game Studios (see
`NOTICE`).

In docs and skills, **`/name` means the skill `name`**: open `.agents/skills/name/SKILL.md` and
follow it (pi: `/skill:name`; other tools: ask for the skill by name).

## Start here

1. Run `python tools/studio.py status`. It shows the project, stage, stories, session notes,
   git state, gaps and engine state. Python 3.11+ is required.
2. First session, or no game concept yet? Follow the `start` skill.
3. Not sure what is next? Follow the `help` skill.
4. Read `production/session-state/active.md` first after any compaction, crash or restart: the
   file is the memory, not the conversation.

## Collaboration protocol

**User-driven collaboration, not autonomous execution.**
Every task follows: **Question -> Options -> Decision -> Draft -> Approval**

- Ask "May I write this to [filepath]?" before writing or editing any file. Exempt, and only these
  three: appends to `production/session-state/active.md`; agent memory under `.agents/memory/`; a
  sub-agent's new file at the path its orchestrating skill named
  (see `rules/agent-memory.md`).
- Show drafts or summaries before requesting approval.
- Multi-file changes need explicit approval for the full changeset.
- No commits without user instruction.
- A skipped or dismissed question is not an answer: act on nothing, re-ask in plain text and wait.
- Ask by listing numbered options and ending your turn. The question is the last thing in the reply.

See `docs/studio/COLLABORATIVE-DESIGN-PRINCIPLE.md` for the full protocol and examples, and
`docs/studio/automation-modes.md` for how `modes.automation` changes how often you ask.

## Where things live

- `project.toml` is the project's settings. `project.local.toml` (gitignored) holds one developer's
  overrides. `python tools/studio.py config` shows the resolved values and where each came from
  (`docs/studio/config-resolution.md`).
- `.agents/skills/<name>/SKILL.md`: skills (with `references/` and `CONTRACT.md` files). `roles/`: roles.
  `gates/`: director gates. `rules/`: path-scoped rules. `templates/`: document templates.
  `docs/studio/`: framework docs. `docs/architecture/`: your ADRs and control manifest.
  `docs/technical-preferences.md`: your engine and style preferences.
- `design/`, `production/`, `assets/`, `tests/`, `prototypes/` and the code root are yours. Full layout:
  `docs/studio/directory-structure.md`.
- Files listed in `files.manifest` belong to the template; `python tools/studio.py update` replaces
  them. Do not edit them in a game (propose the change upstream instead).

## Technology Stack

- **Engine**: [CHOOSE after running the `setup-engine` skill]
- **Language**: [CHOOSE]
- **Version Control**: Git with trunk-based development
- **Build System**: [SPECIFY after choosing engine]
- **Asset Pipeline**: [SPECIFY after choosing engine]

## Skills

Eight core skills run at the default `minimal` rigor: `start`, `help`, `setup-engine`, `brainstorm`,
`create-stories`, `dev-story`, `story-done`, `settings`. Every skill works at any rigor; rigor changes
what is required, not what is allowed. List them with `ls .agents/skills`. A skill is a numbered
checklist: follow its phases in order, copy its checklist and tick it as you go, and end with the
verdict it names. A skill's `references/` files are read only when the skill says so.

## Roles and gates

A role (`roles/<name>.md`) is a perspective with a domain, a tier and a limit on what it may do
(`can:`). When a skill says **Act as `<role>`**, read the role file and do that step in that role. A
director gate (`gates/<id>.md`) is a review a director role gives at a fixed point; which gates run
depends on `review_mode` (`docs/studio/director-gates.md`). If your tool can run sub-agents you may
delegate a role step to one; otherwise do it yourself, in turn.

## Rules

Before editing a file, read every `rules/**/*.md` whose `paths:` globs match that file, plus the file
named in its `extends:` line. Rules are short and prescriptive; follow them without being asked.

## Engine hooks

Skills keep engine-specific steps in an engine layer. A step reads: `hook: <skill>/<point>`: if
`ENGINE.md` exists, follow its section `## hook: <skill>/<point>`; otherwise ask the user how
their engine does this and record the answer in `ENGINE.md` under that heading. `python tools/studio.py check`
fails when a hook a skill names has no section in an existing `ENGINE.md`.

<!-- ENGINE-REFERENCE -->
Engine reference: not set yet (the `setup-engine` skill writes `engine-reference/<engine>/VERSION.md` here)

## Coordination rules

1. **Vertical delegation**: leadership roles delegate to department leads, who delegate to specialists.
2. **Horizontal consultation**: same-tier roles may consult but not decide outside their domain.
3. **Conflict resolution**: escalate to the shared parent; design conflicts to `creative-director`,
   technical conflicts to `technical-director`.
4. **Change propagation**: the `producer` role coordinates changes that touch several domains.
5. **No unilateral cross-domain changes**: never edit outside your role's directories without delegation.
6. **Read design docs by section**: find a heading, read that range; read a whole doc only when needed.
7. **Nothing goes upstream**: never file or comment on issues or pull requests in engine, plugin or
   vendor repositories. Draft it; the user submits it.

Full text and the "Working as a role" procedure: `docs/studio/coordination-rules.md`.

## Coding standards

`docs/studio/coding-standards.md`. Gameplay values are data-driven, public APIs have doc comments,
commit messages use Conventional Commits, and every story has the test evidence its type requires.

## Commands

Run from the project root. `python tools/studio.py --help` lists all of them.

| Command | What it does |
|---|---|
| `python tools/studio.py setup` | set the git hooks path, sync the Claude Code add-on, run engine setup |
| `python tools/studio.py status` | orientation: project, stories, session, git, gaps |
| `python tools/studio.py config [--keys a,b] [--set key=value [--local]]` | resolved settings with sources; write one value |
| `python tools/studio.py check [--staged]` | blocking checks and advice; run before committing |
| `python tools/studio.py update --from <template checkout>` | take template updates (files in `files.manifest`) |
| `python tools/studio.py upstream-diff --clone <ccgs checkout> --to <tag>` | map upstream changes to this repo |
| `python tools/studio.py claude-sync` | generate `.claude/` for Claude Code |

Helper commands used by skills (`story-facts`, `story-status`, `md-section`, `session-state`,
`project-state`, `set-stage`, `config-set`, `adr-status`, `artifact-check`, `project-coherence`,
`review-receipts`, and more) print tab-separated observations, never verdicts. Each has `--help`.
