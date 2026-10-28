# Run and Observe

Shared procedure for any skill that closes a story which changes something a
player can see. Used by `/dev-story` (Phase 6) and `/story-done` (Phase 3).
**A parse check is not a run, and a story nobody looked at does not close.**
This file explains how to look.

`docs/studio/coding-standards.md` is the authority for *what* evidence a story
needs. This file is the procedure for *producing* the visual half of it.

## The rule

Every story that changes something player-observable is **launched and observed
before it closes**, and the observation is a **retained screenshot** in
`production/qa/evidence/`. Compiling proves the code loads. Tests prove the
logic. Neither proves the text fits in the box.

The agent can see images: most agent tools can open a PNG and describe it. The whole
problem is getting a picture out of the engine unattended, and every engine has a native way.

## The procedure

1. **Launch windowed** at a fixed resolution — `1280x720` unless the project
   says otherwise — using `commands.run` from `project.toml`. Never the
   headless / batch / null-RHI flag: those exist to *skip* rendering.
2. **Launch straight into the scene or map the story touched.** A feature that
   is only reachable through the main menu and three clicks is a feature the
   run will not reach. Stories should be written so their surface is reachable
   from a launch argument (a scene path, a map URL, a `--scene` flag).
3. **Wait, capture, quit.** Let the engine render real frames — 60 is a safe
   floor — capture one, and exit. Each engine's mechanism is below.
4. **Look.** Open the PNG. Compare what is on screen to the acceptance
   criteria. Clipped text, an overflowing panel, a missing element, the wrong
   colour — these are defects, and this is the only step that finds them.
5. **Retain.** Capture straight into the story's evidence folder, so nothing
   needs copying: `mkdir -p production/qa/evidence/[story-slug]`, then pass
   `production/qa/evidence/[story-slug]/[NN]-[what-it-shows].png` as the capture
   path. `[story-slug]` is the story
   file's name without `.md`: `story-003-light-pickup` for
   `production/epics/core/story-003-light-pickup.md`. Reference the image from
   the evidence doc. A screenshot that was taken and discarded is an
   assertion, not evidence. Beside it, stamp the files it proves:
   `python tools/studio.py review-receipts hash <each file the story changed> > production/qa/evidence/[story-slug]/stamp.txt`.
   A later edit to one of them then shows the evidence as older than the code.
6. **Report** one `Run result:` line in the implementation summary — vocabulary
   below.

## Per engine

Engine step `hook: run-and-observe/capture`: if `ENGINE.md` exists, follow its section `## hook: run-and-observe/capture`; otherwise ask the user how their engine launches a scene windowed at a fixed resolution and captures a screenshot unattended, and record the answer in `ENGINE.md` under that heading. The section gives, for the engine: the launch command, the capture command, where the output lands, the flags never to use (the ones that skip rendering) and any scaffold the capture needs.

### Any engine — OS capture fallback

On Windows, PowerShell with `System.Drawing` can `CopyFromScreen` into a bitmap
and save it. It needs a visible desktop and the game window on top, and it
captures whatever is there — it cannot be told "the shop panel". Use it when the
engine-native path is unavailable, and say so in the run result. Linux CI with
no display needs `xvfb-run` in front of the launch; `--headless` is not a
substitute.

## The `Run result:` line

Exactly one of three shapes, in the implementation summary:

- **`Run result: OBSERVED — <what was on screen, one line>`** with the retained
  path. *"Shop panel renders, all 6 slots inside the frame, prices legible at
  720p — `production/qa/evidence/shop-panel/01-shop-open.png`."*
- **`Run result: NOT VERIFIED — <reason>`**. Engine binary not found,
  `commands.run` unset, launch crashed, screenshot empty. This is a **blocker**
  at the default gate level for Visual/Feel and UI stories, not a note — a
  story nobody looked at does not close. Under an explicit
  `testing.strict.visual`/`.ui: false` it is recorded and the story may close
  with the gap in `## Completion Notes`.
- **`Run result: N/A — <reason>`**, only for a story with genuinely nothing
  observable — a pure data migration, a save-format change with no surface.
  Say why. "It's a Logic story" is not a reason: a damage formula has a number
  on screen somewhere.

The run is **not waived at `qa.level: minimal`**. Tests are waived there; the
look is not. It is the cheapest verification in the pipeline and the one
whose absence produces a well-tested game that looks wrong.

## What a still can and cannot show

**Can:** layout, clipping, overflow, presence, alignment, colour, legibility,
that the right screen appeared at all. This is where shipped visual defects
actually live.

**Cannot:** timing, responsiveness, weight, animation curves, audio sync — the
"feel" half of Visual/Feel. A frame sequence or OS video capture can show motion. Feel stays a human check in `/team-qa`.
Say which half the screenshot covered.

## Reaching the state

A screenshot of the title screen verifies nothing about depth 2. Either launch
the scene/map directly (a scene argument, a map URL, a `--scene` flag) or
give the bootstrap a debug argument that sets state (`--gold=500 --depth=2`).
Write stories so their surface is reachable one of those ways; a story that is
not is a story that will be marked `NOT VERIFIED` every time.

## Finding the engine

Most engines do not install onto `PATH` on Windows. `engine.editor_path` in `project.local.toml` (or the engine's
setup hook) is where the editor lives; resolve it before concluding "no engine on this machine".
Absence of a path is not absence of an engine.

---

*Engine-specific commands live in the engine layer's `ENGINE.md`; `engine-reference/<engine>/` is the project's pinned authority. Check it before trusting a version-qualified claim.*
