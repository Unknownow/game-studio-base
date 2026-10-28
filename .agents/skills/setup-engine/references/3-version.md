# /setup-engine — Section 3: Look Up Current Version

> Part of `/setup-engine`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## 3. Look Up Current Version

Once the engine is chosen:

1. If a version was provided, use it.
2. If no version was provided, search the web for the latest stable release:
   - Search: `"[engine] latest stable version [current year]"`
   - Confirm with the user: "The latest stable [engine] is [version]. Use this?"

### Check the chosen version against what is actually installed

A version found by web search is what exists, not what the developer has. Pinning
one they cannot run means every later instruction — build, test, smoke, the
engine reference docs — targets an engine that is not on the machine.

Probe for the binary and treat failure as unknown, never as absent.
Engine step `hook: setup-engine/version`: if `ENGINE.md` exists, follow its section `## hook: setup-engine/version`; otherwise ask the user how their engine does this and record the answer in `ENGINE.md` under that heading.
The section gives the probe (where the editor lives and how to ask it for its version).

Keep the executable the probe found: Section 5.5 writes it into `engine.editor_path`
(in `project.local.toml`, because the path differs per machine).

Then:

1. **Match** — say so in one line and continue.
2. **Mismatch** — state both versions and ask, offering three options: pin the
   installed version, pin the newer one and upgrade later, or pin the newer one
   deliberately. Record the answer; do not pick silently.
3. **Not found or probe failed** — report `installed version NOT DETERMINED` and
   continue with the chosen version. Do **not** report this as "no engine
   installed": a probe that could not run has not established absence.

Whatever the outcome, write it into Section 7's `VERSION.md` as an
`Installed at pin time` row, so a later reader can tell a deliberate
version-ahead pin from an accident.

---
