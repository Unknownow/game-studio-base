# Game Studio Base

An engine-agnostic starter template for game projects worked on by AI agents and people together. It gives you skills (numbered checklists), roles, review gates, rules, templates and one Python command line that checks the project.

It works with pi, Codex, Cursor, Claude Code or plain editor and terminal. It is adapted from [Claude Code Game Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) v1.2.0 (MIT); see `NOTICE`.

## Requirements

- Python 3.11 or newer on your PATH as `python`. The Windows Store "python" alias does not count.
- git.
- bash (Git Bash on Windows) for the git hooks.

## Quick start

1. Create a repository from this template (or clone it).
2. Run `python tools/studio.py setup` (sets the git hooks, and syncs the Claude Code add-on).
3. Run `python tools/studio.py status`.
4. Ask your agent to follow the `start` skill (`.agents/skills/start/SKILL.md`).

## Layout

- `AGENTS.md`: the entry point every agent reads.
- `.agents/skills/<name>/SKILL.md`: skills. 75 skills in all; eight core skills are on at the default `minimal` rigor: `start`, `help`, `setup-engine`, `brainstorm`, `create-stories`, `dev-story`, `story-done`, `settings`.
- `roles/`, `gates/`, `rules/`, `templates/`, `docs/studio/`: roles, review gates, rules, document templates and reference docs.
- `project.toml`: project settings. `project.local.toml` (not committed) holds your own overrides.
- `tools/studio.py`: the command line. Run `python tools/studio.py --help`.

## pi

pi finds `.agents/skills/` and `AGENTS.md` by itself. On first open pi asks whether to trust the project; accept it so project skills load. Run a skill with `/skill:<name>`, for example `/skill:help`.

## Claude Code

`CLAUDE.md` only imports `AGENTS.md`. `python tools/studio.py claude-sync` generates `.claude/skills`, `.claude/agents` and `.claude/settings.json` from the portable files (the `post-merge` and `post-checkout` hooks run it). Turn it off with `[claude] sync = false` in `project.toml`.

## Updating a game

Games take template updates through `files.manifest`, not git merge:

```
git clone --branch <tag> https://github.com/Unknownow/game-studio-base.git ../game-studio-base
python tools/studio.py update --from ../game-studio-base --dry-run
python tools/studio.py update --from ../game-studio-base
```

Only files that match the manifest are replaced. Your `project.toml`, `design/`, `production/`, `src/`, `Assets/` and `tests/` are never touched.

## Upstream flow

CCGS release -> this repo -> engine forks (for example `game-studio-unity`, a fork that only adds files) -> games. `UPSTREAM.toml` maps every upstream file to its port or lists it as ignored with a reason. `python tools/studio.py upstream-diff --clone <ccgs checkout> --to <tag>` shows what changed.

## Checks

`python tools/studio.py check` blocks on: invalid config, story files missing required sections, invalid data JSON, missing screenshot evidence for finished Visual/Feel and UI stories, and invalid skill, role or rule frontmatter. Style problems are advice only. Git hooks in `hooks/` run `check --staged` before each commit.

## Licence

MIT. See `LICENSE` and `NOTICE`.
