# Directory Structure

```text
/
├── AGENTS.md                    # Entry point for every agent and person
├── CLAUDE.md                    # One line: @AGENTS.md (Claude Code add-on)
├── project.toml                 # Project settings: engine, modes, stage (source of truth)
├── project.local.toml           # Your own overrides (gitignored)
├── engine.toml                  # Engine pin and code root (an engine layer adds this)
├── ENGINE.md                    # Engine hooks used by skills (an engine layer adds this)
├── .agents/skills/<name>/       # Skills (SKILL.md, references/, CONTRACT.md)
├── roles/                       # Role definitions (one file per role)
├── gates/                       # Director gate definitions (one file per gate)
├── rules/                       # Path-scoped coding and content rules
├── templates/                   # Document templates the skills write from
├── <code root>/                 # Game source code: THE PATH IS ENGINE-SPECIFIC, see below
├── Assets/                      # Game assets (art, audio, vfx, shaders, data)
│   └── data/                    # JSON data files (validated by `check`)
├── design/                      # Game design documents (gdd, narrative, levels, balance, registry)
├── docs/
│   ├── studio/                  # Framework docs (template-owned)
│   ├── architecture/            # Your ADRs, TR registry and control manifest
│   └── technical-preferences.md # Your engine and style preferences
├── engine-reference/            # Curated engine API snapshots (version-pinned; an engine layer ships them)
├── tests/                       # Game test suites (unit, integration, performance, playtest)
├── tools/                       # studio.py and its package
├── hooks/                       # Git hooks (pre-commit, pre-push, post-merge, post-checkout)
├── prototypes/                  # Throwaway prototypes (outside the code root)
├── production/                  # Production management (epics, sprints, milestones, QA, releases)
│   ├── session-state/           # Ephemeral session state (active.md: gitignored)
│   └── session-logs/            # Session audit trail (gitignored)
└── studio-tests/                # QA for the skills and roles themselves (skill-test, skill-improve)
```

Files matched by `files.manifest` are template-owned: `python tools/studio.py update` replaces them.
Everything else is yours.

## The code root is engine-specific

**Some engines will not build a project whose code sits in `src/`.** This is a hard constraint of the
engine's own toolchain:

| `engine.name` | Code root | Why it cannot be `src/` |
|---|---|---|
| **Other (default)** | `src/` | No constraint. |
| **Unity** | `Assets/` | Unity compiles **only** `Assets/` and `Packages/`. Code outside them is invisible to the compiler. |

**Resolve the code root from `engine.name` (or `code_root` in `engine.toml`) before writing any source file.** A
path shown as `src/…` alone is a default-row example: read it as *"the code root"* and substitute the row above.

**Tests follow the same rule**, because the same compilers decide what they see:

| `engine.name` | Test root | Anywhere else |
|---|---|---|
| **Other (default)** | `tests/unit/`, `tests/integration/` | none |
| **Unity** | `Assets/Tests/EditMode/`, `Assets/Tests/PlayMode/` | not compiled: "0 tests, Passed" |

Read `tests/unit/[system]/` (or `integration/`) anywhere as the test root plus `[System]/`.
