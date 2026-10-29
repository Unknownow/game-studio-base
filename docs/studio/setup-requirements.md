# Setup Requirements

This template needs a few tools. The git hooks and CI stop with a clear message when a required tool is missing; they never skip a check silently.

## Required

| Tool | Purpose | Install |
| ---- | ---- | ---- |
| **Git** | Version control, branch management | [git-scm.com](https://git-scm.com/) |
| **Python 3.11 or newer** | Runs `python tools/studio.py` — config, checks, helpers. Standard library only. | [python.org](https://www.python.org/). The command must be `python` (or `py -3` on Windows). The Windows Store "python" alias does not count; the hooks reject it. |
| **Bash** | Runs the git hooks in `hooks/` | Built into macOS and Linux. On Windows, install [Git for Windows](https://git-scm.com/downloads/win), which brings Git Bash. |
| **An AI agent tool** | Runs the skills | Any tool that reads `AGENTS.md` and `.agents/skills/` — pi, Codex, Cursor, Claude Code and others. |

Check Python with `python -c "import sys; print(sys.version_info >= (3, 11))"`; it must print `True`. If `python` runs an older version, put the newer one first on `PATH`.

## First run

1. `python tools/studio.py setup` — sets `core.hooksPath` to `hooks/` and, when `[claude] sync` is on, generates the Claude Code add-on files.
2. `python tools/studio.py status` — shows the stage, config problems and what to do next.
3. `python tools/studio.py check` — runs the blocking checks; it must report 0 errors.

## Per tool

- **pi** — finds `.agents/skills/` and `AGENTS.md` by itself. On first open it asks whether to trust the project; accept, or project skills do not load. Run a skill with `/skill:<name>`.
- **Claude Code** — `CLAUDE.md` imports `AGENTS.md`. `python tools/studio.py claude-sync` generates `.claude/skills`, `.claude/agents` and `.claude/settings.json` (all gitignored) from the portable files; the `post-merge` and `post-checkout` hooks run it.
- **Other tools** — read `AGENTS.md` first; it is the entry point.

## Troubleshooting

- `studio: Python 3.11+ is required` — your `python` is too old. Install a newer one and fix `PATH`.
- `game-studio hook: Python 3.11+ not found` — the same problem, seen from a git hook.
- Hooks do not run on Windows — run them from Git Bash, and check that `git config core.hooksPath` prints `hooks`.
