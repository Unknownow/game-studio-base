<!-- pi-workflow plan v1 flow=20261029-1513-add-a-unity-landing-page-to-game-studio-c109 -->
## Plan: Add a Unity landing page to game-studio-unity

### 1. Goal and non-goals
**Goal:** the fork `Unknownow/game-studio-unity` gets one new file, `.github/README.md`, with the exact text in §4. GitHub shows that file on the repo page instead of the root `README.md` that comes from base. It ships as one commit pushed straight to the fork's `main`, and CI on it is green.

**Non-goals:**
- No change to any file that base owns. That includes the root `README.md`, `AGENTS.md`, `files.manifest` and the existing `.github/` files.
- `.github/README.md` is not added to `files.manifest.d/unity.manifest`.
- The `v0.1.0` tag doesn't move.
- The agent doesn't create the GitHub Release or make GitHub API calls.
- No code changes and no Unity runs.

### 2. User decisions
- D1: The landing page is a new `.github/README.md` in the fork, with exactly the text the user approved (§4).
- D2: The page tells new games to delete it (Quick start step 2). It isn't listed in the manifest, so `update` never brings it back.
- D3: The user creates the `v0.1.0` GitHub Release by hand on GitHub, from the text they were given in the discussion. The agent doesn't recreate `/tmp/ghcfg-unknownow` and makes no `gh` calls for it.
- D4: The change is one commit, `docs: Unity landing page`, pushed straight to the fork's `main` after a judge pass. There's no PR.
- D5: The handoff rules stand:
  - Use the `github-personal` SSH alias only.
  - Don't touch `~/.ssh`, `~/.gitconfig*` or `hosts.yml`. Never run `gh auth switch`.
  - Never commit `.claude/`, `Library/`, `project.local.toml`, `production/qa/` or anything from `D:/scratch/**`.
  - Keep Godot and Unreal wording out of Unity files.

### 3. Facts the executor needs
- **Fork state:**
  - The fork is at `D:/personal/game-studio-unity`, on `main` at `866b043` (`feat(package): com.unknownow.studio-tools 0.1.0`). That's the pushed tip, and it carries the tag `v0.1.0`.
  - The working tree is clean apart from ignored files.
  - `origin` is `git@github-personal:Unknownow/game-studio-unity.git`.
- **Existing `.github/` files:** the fork tracks `workflows/check.yml`, `ISSUE_TEMPLATE/bug_report.md`, `ISSUE_TEMPLATE/feature_request.md` and `PULL_REQUEST_TEMPLATE.md`. All four are owned by base (`files.manifest:18-20`). There's no `.github/README.md` in base or in the fork, so adding one touches nothing base owns.
- **`files.manifest.d/unity.manifest`:** 8 lines, none of them covering `.github/**`. Don't change it.
- **Facts the README text relies on (already checked):**
  - The editor pin is `ProjectSettings/ProjectVersion.txt:1` `m_EditorVersion: 6000.3.25f1`.
  - `engine.toml` sets `code_root = "Assets"` and `tests_root = "Assets/Tests"`.
  - `tools/gamestudio/engines/unity.py:140-175` (`setup()`) replaces the embedded package with the git URL at `#v<version>`.
  - `Packages/com.unknownow.studio-tools/README.md` exists.
  - The root `README.md:30-36` tells games to update from game-studio-base. The new page points them to game-studio-unity instead.
- **Python 3.12:** `/c/Users/IEC-WW/AppData/Local/Programs/Python/Python312/python.exe`. The default `python` is 3.9, so don't use it.
- **CI:** `.github/workflows/check.yml:16,18` runs `python tools/studio.py check` and `python -m unittest discover -s tools/gamestudio/tests -t tools -q` on every push.
- **Tool rules:** a push to `main` must be its own command, with nothing chained in front of it like `cd`. Use `git -C D:/personal/game-studio-unity push origin main`.

### 4. Design: exact file content (contract)
`.github/README.md` is UTF-8 with LF line endings and ends with one newline. Write it exactly as below. The "Updating a game" code block is indented 4 spaces.

```markdown
# Game Studio Unity

The Unity 6.3 LTS edition of [Game Studio Base](https://github.com/Unknownow/game-studio-base): a starter template for game projects worked on by AI agents and people together. It adds a ready Unity project, the Unity engine layer and the `com.unknownow.studio-tools` editor package to the base's skills, roles, review gates, rules and command line. Adapted from [Claude Code Game Studios](https://github.com/Donchitos/Claude-Code-Game-Studios) v1.2.0 (MIT); see `NOTICE`.

## Requirements

- Unity 6000.3.25f1 (6.3 LTS) through Unity Hub. The pin is in `ProjectSettings/ProjectVersion.txt`.
- Python 3.11 or newer on your PATH as `python`, git, and bash (Git Bash on Windows).

## Quick start

1. Create a repository from this template.
2. Delete `.github/README.md` (this file) and write your game's own `README.md`. GitHub shows this file instead of yours while it exists.
3. Run `python tools/studio.py setup`. It sets the git hooks, syncs the Claude Code add-on and replaces the embedded `Packages/com.unknownow.studio-tools` with a git dependency on the matching release tag.
4. Open the project in Unity Hub.
5. Run `python tools/studio.py status`, then ask your agent to follow the `start` skill (`.agents/skills/start/SKILL.md`). The `setup-engine` skill fills the engine placeholders in `AGENTS.md`.

## What this fork adds

| Path | What it is |
|---|---|
| `ENGINE.md` | The Unity steps every skill's "engine step" points to: tests, CI, naming, specialists, audits. |
| `engine.toml` | The engine pin. Code and assets live in `Assets/`, tests in `Assets/Tests/`. |
| `engine-reference/unity/` | Version notes for Unity 6.3, breaking changes, deprecated APIs and best practices. Start with `VERSION.md`. |
| `roles/unity-*.md`, `rules/unity/` | Unity specialist roles and path rules. |
| `Packages/com.unknownow.studio-tools/` | Editor tools: evidence capture, batch tests, a missing-reference audit and a project settings check. See its [README](../Packages/com.unknownow.studio-tools/README.md). |
| `tools/gamestudio/engines/unity.py` | The Unity plugin for `tools/studio.py`. |

`src/` and `tests/` come from the base and aren't used in Unity: put your code in `Assets/` and your tests in `Assets/Tests/`.

## Updating a game

Take updates from this repo, not from the base:

    git clone --branch <tag> https://github.com/Unknownow/game-studio-unity.git ../game-studio-unity
    python tools/studio.py update --from ../game-studio-unity --dry-run
    python tools/studio.py update --from ../game-studio-unity

## More

The root [`README.md`](../README.md) and `docs/studio/` cover the framework: skills, settings, pi and Claude Code, checks.

## Licence

MIT. See `LICENSE` and `NOTICE`.
```

No other design applies: no components, interfaces or data change.

### 5. Steps
**S1.** In `D:/personal/game-studio-unity`:
- Confirm that `git branch --show-current` is `main`.
- Confirm that `git status --porcelain` is empty.
- Confirm that `git rev-parse --short HEAD` is `866b043`.
- Run `git fetch origin`, then confirm that `git rev-parse --short origin/main` is also `866b043`.

If anything differs, stop and report. Don't change anything.

**S2.** Create `.github/README.md` with exactly the content in §4. Don't edit, add or delete any other file.

Check the result:
- `git status --porcelain` shows only `?? .github/README.md`.
- The file has no CRLF line endings (`grep -c $'\r' .github/README.md` prints `0`).

**S3.** Run the two commands in §6. If one fails because of the new file, change only the new file, and keep its wording to the approved text. If a fix would need a change to a base-owned file, stop and report.

**S4.** Make the commit:
- Stage only `.github/README.md`, by explicit path.
- Confirm that `git diff --cached --name-only` prints exactly `.github/README.md`.
- Commit with the message `docs: Unity landing page`.

After the commit, check that:
- `git status --porcelain` is empty.
- `git diff --name-status 866b043..HEAD` prints only `A	.github/README.md`.
- `git rev-parse 'v0.1.0^{commit}'` still starts with `866b043`.

**S5.** Call `judge` with focus "Add a Unity landing page to game-studio-unity". Fix any blocker or major finding by amending the single commit, still touching only `.github/README.md`. Then rerun §6 and call `judge` again. Minor findings that would change the approved text: put them in `disputes` instead of changing the text.

**S6.** Deliver: the fork's `main` to `origin` (`Unknownow/game-studio-unity`), as a push on its own. Then:
- Confirm that `git ls-remote origin refs/heads/main` equals the local `git rev-parse HEAD`.
- For CI status there are no `gh` credentials (D3). Record the Actions URL `https://github.com/Unknownow/game-studio-unity/actions` in the report, and list the CI check for the user under S7.

If anyone reports CI as red, stop. Don't force-push.

**S7.** Verify: open https://github.com/Unknownow/game-studio-unity and its Actions tab. Look for:
- The repo page shows "Game Studio Unity", not "Game Studio Base".
- The links to the package README and the root `README.md` open the right files.
- The `check` run on the `docs: Unity landing page` commit is green.

**S8.** Verify: on https://github.com/Unknownow/game-studio-unity/releases/new, create the release from the text you were given in the discussion. Use the existing `v0.1.0` tag, title `Game Studio Unity v0.1.0`, and "Set as the latest release". Look for: the release appears on the existing `v0.1.0` tag and is marked as the latest release.

### 6. Tests
No tests are added or changed. Run these from `D:/personal/game-studio-unity`, with `PY=/c/Users/IEC-WW/AppData/Local/Programs/Python/Python312/python.exe`:
1. `$PY tools/studio.py check` prints `check: 0 errors` (warnings are fine).
2. `$PY -m unittest discover -s tools/gamestudio/tests -t tools -q` ends with `OK`. Last run: 243 tests in about 65 s, so it isn't slow.

No Unity suites need to run, because nothing under `Assets/`, `Packages/` or `ProjectSettings/` changes.

### 7. Done when
- The fork's `main` is `866b043` plus exactly one commit, `docs: Unity landing page`. That commit adds only `.github/README.md`, with exactly the content in §4.
- `files.manifest.d/unity.manifest` and every base-owned file are unchanged.
- Both §6 commands passed on the committed tree.
- The judge passed.
- The commit is on `origin/main`.
- `v0.1.0` still points to `866b043`.
- S7 (page, links and CI check) and S8 (release) are listed for the user.

### 8. Risks, rollback, and what not to touch
- **Hidden root README:** `.github/README.md` hides the root `README.md` on GitHub for the fork and for every game made from it. This is intended (D2), and Quick start step 2 tells games to delete it.
- **Rollback before the push:** `git reset --hard 866b043`, only after confirming that `git status --porcelain` shows nothing except the new file or commit.
- **Rollback after the push:** a new commit that deletes the file. Never force-push.
- **Do not touch:**
  - the base repo `D:/personal/game-studio-base` and every base-owned file in the fork
  - the `v0.1.0` tag
  - `files.manifest.d/unity.manifest`
  - `D:/projects/**` and `D:/scratch/**`
  - `~/.ssh`, `~/.gitconfig*` and `hosts.yml`
- **GitHub credentials:** don't recreate `/tmp/ghcfg-unknownow`, don't run `gh auth switch`, and make no `gh` calls.

### 9. Commits
1. `docs: Unity landing page`: adds `.github/README.md`.

## Amendment 1 (executor: verify)
Check the repo page, links and the green `check` run on https://github.com/Unknownow/game-studio-unity (Actions tab), then create the v0.1.0 Release by hand.


<!-- pi-workflow:status -->
## Checklist
- [x] S1 In `D:/personal/game-studio-unity`:
- [x] S2 Create `.github/README.md` with exactly the content in §4. Don't edit, add or delete any other file.
- [x] S3 Run the two commands in §6. If one fails because of the new file, change only the new file, and keep its wording to the 
- [x] S4 Make the commit:
- [x] S5 Call `judge` with focus "Add a Unity landing page to game-studio-unity". Fix any blocker or major finding by amending th
- [x] S6 Deliver: the fork's `main` to `origin` (`Unknownow/game-studio-unity`), as a push on its own. Then:
## For you after the flow
- S7 Verify: open https://github.com/Unknownow/game-studio-unity and its Actions tab. Look for:
- S8 Verify: on https://github.com/Unknownow/game-studio-unity/releases/new, create the release from the text you were given 
## Outcome
2026-10-29T08:15:59.821Z — ok: game-studio-base: fix/assets-root-and-layer-tests, 0 commits since the review base, PR #3 MERGED https://github.com/Unknownow/game-studio-base/pull/3; game-studio-unity: main, 1 commit since the review base · 3 human check(s) for you (see the card)
