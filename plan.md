<!-- pi-workflow plan v1 flow=20261029-1451-merge-base-pr-3-then-port-and-ship-game-4c65 -->
## Plan: Merge base PR #3, then port and ship game-studio-unity v0.1.0

### 1. Goal and non-goals
**Goal:**
- Base `Unknownow/game-studio-base` `main` has PR #3 merged with a merge commit, and its CI is green.
- Fork `Unknownow/game-studio-unity` `main` is base `main` plus four commits that only add files:
  - a minimal Unity 6.3 LTS project
  - the engine pin, `ENGINE.md` hooks, reference docs, roles and rules
  - the Unity engine plugin
  - the UPM package `com.unknownow.studio-tools` 0.1.0
- The fork passes every check in §6, its CI is green, it's tagged `v0.1.0`, and it's marked as a GitHub template.

**Non-goals:**
- No new code, tests or docs. All of the groundwork already exists, untracked, in the fork.
- No base file edits and no new base commits.
- `v0.1.0` in base doesn't move.
- No changes to `D:/projects/**`.

### 2. User decisions
- D1: The agent merges base PR #3 itself, with a merge commit, and deletes the PR branch.
- D2: Fallback: if the merge gate or `gh` refuses the merge even after a judge PASS, stop and ask the user to merge on GitHub. No other way around the gate.
- D3: The fork ships as four commits straight to fork `main`, with the subjects and file split in §9. There is no PR on the fork.
- D4: After the fork's CI is green, tag the fork `v0.1.0` and set `is_template=true`.
- D5: Delete `/tmp/ghcfg-unknownow` at the end.
- D6: The rules from the handoff stand, as listed in §8.
- D7: The user does the human checks: opening the fork in Unity on a case-sensitive checkout, and creating a game from the template and running `setup`.

### 3. Facts the executor needs
**Repos and refs**
- **Base** `D:/personal/game-studio-base`:
  - On `fix/assets-root-and-layer-tests` at HEAD `2dcc797`. `main` and `origin/main` are at `48ccc4c`, and `v0.1.0^{commit}` is `063372c`.
  - PR #3 is OPEN and MERGEABLE, with head `2dcc797` and 2 checks SUCCESS.
  - There is an untracked `assets/data/README.md` that blocks `git checkout main`. Never check out `main` there and never touch that file.
- **Fork** `D:/personal/game-studio-unity`:
  - On `main` at `48ccc4c`. The remotes are `base` and `origin`, both `git@github-personal:Unknownow/<repo>.git`.
  - Untracked: `ENGINE.md`, `Packages/` (`manifest.json`, `packages-lock.json`, `com.unknownow.studio-tools/`), `ProjectSettings/`, `UPSTREAM.unity.toml`, `engine-reference/`, `engine.toml`, `files.manifest.d/`, `roles/unity-{addressables,dots,shader,ui}-specialist.md`, `roles/unity-specialist.md`, `rules/unity/`, `studio-tests/agents/engine/`, `tools/gamestudio/engines/unity.py`, `tools/gamestudio/tests/test_engine_unity.py`.
  - Under lowercase `assets/`, the only tracked file is `assets/data/README.md`. The untracked files there are `assets/README.md`, `assets/README.md.meta`, `assets/data.meta` and `assets/data/README.md.meta`.
- **What the base PR changes:** it tracks only `Assets/data/README.md` under `Assets/`. None of the fork's untracked files exist in base (checked), so `stash pop` can't collide.

**Fork configuration**
- **Ignore rules** in the fork's `.gitignore`:
  - `project.local.toml` at `:13`, `.claude/` at `:18`, `Library/` at `:39`, `Temp/` at `:40`, `Logs/` at `:41`, `UserSettings/` at `:42`.
  - **`production/qa/` is not ignored**, so it must be deleted by hand.
- **CI:** `.github/workflows/check.yml:1-18` runs `python tools/studio.py check` and the unittest discover command on push, with Python 3.12.
- **Pins:**
  - `ProjectSettings/ProjectVersion.txt:1` is `m_EditorVersion: 6000.3.25f1`.
  - `engine.toml` has `name = "unity"`, `lts = "6.3"` and `code_root = "Assets"`.
  - `Packages/com.unknownow.studio-tools/package.json:2-3` has the name and `"version": "0.1.0"`.
  - `Packages/manifest.json:41` references the package.

**Tools and paths**
- **Python 3.12:** `/c/Users/IEC-WW/AppData/Local/Programs/Python/Python312/python.exe`. The default `python` is 3.9, so don't use it.
- **CCGS clone:** `D:/scratch/ccgs-v1.2.0` exists. It's only read, through `upstream-diff`.
- **Unity:** `"C:/Program Files/Unity/Hub/Editor/6000.3.25f1/Editor/Unity.exe"`. The command lines are in the old plan at `D:/projects/pi-config/.git/pi/plans/20261029-1151-merge-base-pr-3-then-finish-and-ship-the-eca5/plan.md:71-74`. The suite order is at `:158-177` and the commit split at `:219-226`.
- **gh:** every `gh` call against Unknownow repos is prefixed with `GH_CONFIG_DIR=/tmp/ghcfg-unknownow`.
- **Judge:** the flow's review base for base is probably `2dcc797`, so a default judge would say "no changes". Judge base with `base=origin/main`.

### 4. Design
Not applicable. No components are added or reshaped. This is a merge, a case-correct fast-forward and delivery.

### 5. Steps

### Stage 1: Merge base PR #3
**S1.** In base, `git fetch origin`. Confirm that HEAD is `2dcc797`, the working tree is clean apart from the untracked `assets/data/README.md`, and `origin/main` is `48ccc4c`. If anything differs, stop and report.

**S2.** Call `judge` with `base=origin/main` and focus on "PR #3: asset root renamed to `Assets/`, legacy lowercase read with a warning, layer tests". Don't change any file to get a review. If the judge finds blocker or major issues, stop and report: base fixes are out of scope.

**S3.** Deliver: merge base PR #3, `Unknownow/game-studio-base`, with a merge commit, and delete the branch (D1). If the gate or `gh` refuses, stop and ask the user to merge on GitHub (D2).

**S4.** Verify base, read-only:
- `git fetch origin` and record `BASE_MAIN=$(git rev-parse origin/main)`.
- `git merge-base --is-ancestor 2dcc797 origin/main` exits 0.
- `git rev-parse 'v0.1.0^{commit}'` starts with `063372c`.
- Poll `gh run list --repo Unknownow/game-studio-base --branch main` every few seconds until the run for `BASE_MAIN` finishes. It must succeed.
- If CI is red, stop. The rollback is a revert PR of the merge commit, and that also needs the user's OK.

### Stage 2: Port and ship the fork
**S5.** In the fork:
- `git config core.ignorecase false`, then `git fetch base`, and confirm that `git rev-parse base/main` equals `BASE_MAIN`.
- `git stash -u` (not `--all`). Confirm that `git status --porcelain` is empty.
- `git merge --ff-only base/main`. If that fails, `git stash pop` and stop.
- `git stash pop`. If the restore conflicts or fails, stop and keep the stash. Never drop it.

**S6.** Fix the case on disk.
1. List the real folder names at the fork root.
2. If a lowercase `assets` folder exists, rename it in two steps, `assets` → `_assets_tmp` → `Assets`.
3. Then `git add -A` (the ignore rules keep `Library/` and the like out) and `git rm --cached` any leftover lowercase `assets/` path.
4. Unstage everything again with `git reset -q`, so the commits in S9 stage by explicit path.

Expected result:
- `git ls-files | grep '^assets/'` prints nothing.
- The tracked `Assets/data/README.md` is unchanged against `base/main`.
- `Assets/README.md`, `Assets/README.md.meta`, `Assets/data.meta` and `Assets/data/README.md.meta` are untracked.

If git or Unity writes lowercase paths back later, stop and report.

**S7.** Run the §6 commands 1–4 from the fork root with Python 3.12. If a check fails because of a fork-owned file, fix that file. If the fix needs a base-owned file, stop: that would need a separate base PR.

**S8.** Run the §6 commands 5–7, the Unity ones, which are slow. Then:
- `rm -rf production/qa`.
- Confirm that `git status` shows no `InitTestScene*` and no `production/qa`.
- Keep the `.meta` files and `Packages/packages-lock.json`.

A Unity licence error means stop and report.

**S9.** Make the four commits in §9, in order, on fork `main`. Stage each one by its explicit paths (`git add <paths>`), and check with `git diff --cached --name-only` before each commit. After the fourth:
- `git status --porcelain` is empty, apart from ignored files.
- `git diff --diff-filter=MDR base/main..main` prints nothing.
- `git ls-files | grep '^assets/'` prints nothing.
- None of these are tracked: `.claude/`, `Library/`, `project.local.toml`, `production/qa/`, `D:/scratch` content.

Before any push, the rollback is `git reset --soft "$BASE_MAIN"`.

**S10.** Call `judge` on the fork and fix any blocker or major findings with new commits on the same four-commit plan, amending the matching commit. If a fix touches `Packages/`, `ProjectSettings/` or `Assets/`, rerun S8.

**S11.** Deliver: push fork `main` to `origin`, `Unknownow/game-studio-unity`. Then poll `gh run list --repo Unknownow/game-studio-unity --branch main` until the run for the pushed HEAD finishes. It must succeed. If it's red, stop: no tag and no template flag. Report what happened, and don't rewrite the pushed history.

**S12.** Deliver: tag `v0.1.0` on fork `main` HEAD and push the tag (D4). Check with `git ls-remote --exit-code --tags origin v0.1.0`.

**S13.** Run `GH_CONFIG_DIR=/tmp/ghcfg-unknownow gh api -X PATCH repos/Unknownow/game-studio-unity -F is_template=true` (D4). Check that `GH_CONFIG_DIR=/tmp/ghcfg-unknownow gh api repos/Unknownow/game-studio-unity --jq .is_template` prints `true`.

**S14.** `rm -rf /tmp/ghcfg-unknownow` (D5), and confirm the path is gone.

**S15.** Verify: open `D:/personal/game-studio-unity`, or a fresh clone on a case-sensitive checkout, in Unity 6000.3.25f1 — look for: the project opens without errors, `Assets/` is the root, and the `com.unknownow.studio-tools` package resolves (D7).

**S16.** Verify: create a game repo from the `Unknownow/game-studio-unity` template and run `python tools/studio.py setup` in it — look for: setup finishes and the embedded package copy turns into the `#v0.1.0` git URL (D7).

### 6. Tests
No new or changed tests. Run everything from `D:/personal/game-studio-unity`, with `PY=/c/Users/IEC-WW/AppData/Local/Programs/Python/Python312/python.exe`, in this order:

1. `$PY -m unittest discover -s tools/gamestudio/tests -t tools -q` → ends with `OK`. This includes `test_engine_unity` (19 tests) and base's layer tests. It takes about 40–60 s.
2. `$PY tools/studio.py check` → `check: 0 errors`, with no `engine-hooks`, `engine-pin`, `legacy-assets` or `data-json` lines.
3. `$PY tools/studio.py upstream-diff --clone D:/scratch/ccgs-v1.2.0 --to v1.2.0 --coverage` → exit 0.
4. `$PY tools/studio.py claude-sync` → `75 skills, 39 agents`, then `rm -rf .claude`.
5. **Slow (3–6 min):** the EditMode run. Use `Unity.exe -batchmode -nographics -projectPath D:/personal/game-studio-unity -runTests -testPlatform EditMode -testResults D:/scratch/unity-results/editmode.xml -logFile D:/scratch/unity-results/editmode.log`.
   - Expected: exit 0, and `editmode.xml` has `total="45" passed="45" failed="0"`.
   - While fixing, add `-testFilter Unknownow.StudioTools.Tests.<Class>`. Run the full command once at the end.
6. **Slow (1–2 min each):** the batch checks, `Unity.exe -batchmode -nographics -quit -projectPath D:/personal/game-studio-unity -executeMethod Unknownow.StudioTools.Editor.ProjectSettingsCheck.RunBatch -logFile -`, and the same with `Unknownow.StudioTools.Editor.MissingReferenceAudit.RunBatch`. Each exits 0, and the audit reports 0 findings.
7. **Slow:** `$PY tools/studio.py test-run --timeout 1200 --log D:/scratch/unity-results/testrun.log` → exit 0 and `tests total=41 passed=41 failed=0`. Then delete `production/qa`.

Run the Unity commands in the foreground with a timeout of at least 1500 s. Don't use fixed sleeps.

### 7. Done when
- Base `main` contains `2dcc797` through a merge commit, its CI is green on `BASE_MAIN`, `v0.1.0` is still at `063372c`, and the PR branch is deleted.
- Fork `main` is `BASE_MAIN` plus exactly the four commits in §9:
  - `git diff --diff-filter=MDR base/main..main` is empty.
  - `git ls-files | grep '^assets/'` is empty.
  - `Assets/` and its `.meta` files are tracked, and so is `Packages/packages-lock.json`.
  - None of these are tracked: `.claude/`, `Library/`, `project.local.toml`, `production/qa/`.
- Every command in §6 passed on the committed tree.
- The fork's CI is green on the pushed `main`.
- `git ls-remote --exit-code --tags origin v0.1.0` succeeds in the fork.
- `.is_template` is `true`.
- `/tmp/ghcfg-unknownow` no longer exists.
- S15 and S16 are listed for the user.

### 8. Risks, rollback, and what not to touch
- **Merge gate refuses (S3):** stop and ask the user (D2). Don't push base `main` directly, don't change the tree to get a new judge round, and don't use another merge path.
- **Red base CI:** stop. The rollback is a revert PR of the merge commit, after the user's OK.
- **Case folding on Windows:** always rename in two steps with `core.ignorecase=false`. If a lowercase path comes back, stop.
- **Stash:** if the fast-forward fails or the restore conflicts, stop. Never `git stash drop` before a clean restore is confirmed.
- **Unity licence error:** stop and report.
- **Rollback before the push:** `git reset --soft "$BASE_MAIN"`, and only after a successful fast-forward. Before that, `main` is still `48ccc4c`.
- **Red fork CI after the push:** no tag and no template flag. Report what happened and don't force-push.
- **Credentials:**
  - Use only the `github-personal` SSH alias.
  - Every `gh` call carries `GH_CONFIG_DIR=/tmp/ghcfg-unknownow`.
  - Never `gh auth switch`.
  - Never print or edit `hosts.yml`, `~/.ssh` or `~/.gitconfig*`.
  - The git identity under `D:/personal/` is already Cuong Bui. Don't change it.
- **Do not touch:**
  - `D:/projects/**`
  - base `v0.1.0`
  - the base checkout's untracked `assets/data/README.md` and its `main` checkout
  - any base-owned file in the fork
  - `D:/scratch/**` (never commit it, and never run CCGS scripts from it)
- **Wording:** keep Godot and Unreal wording out of the Unity files.

### 9. Commits
**Base:** no new commits. PR #3 is merged as it is, with a merge commit.

**Fork**, on `main` after the fast-forward to `BASE_MAIN`:
1. `feat(unity): minimal Unity 6.3 LTS project`: `Assets/README.md`, `Assets/**/*.meta`, `Packages/manifest.json`, `Packages/packages-lock.json`, `ProjectSettings/**`.
2. `feat(unity): engine pin, ENGINE.md hooks, reference docs, roles and rules`: `engine.toml`, `ENGINE.md`, `engine-reference/unity/**`, `roles/unity-*.md`, `rules/unity/**`, `studio-tests/agents/engine/unity/**`, `files.manifest.d/unity.manifest`, `UPSTREAM.unity.toml`.
3. `feat(studio): Unity engine plugin`: `tools/gamestudio/engines/unity.py`, `tools/gamestudio/tests/test_engine_unity.py`.
4. `feat(package): com.unknownow.studio-tools 0.1.0`: `Packages/com.unknownow.studio-tools/**`.

<!-- pi-workflow:status -->
## Checklist
- [ ] S1 In base, `git fetch origin`. Confirm that HEAD is `2dcc797`, the working tree is clean apart from the untracked `assets/
- [ ] S2 Call `judge` with `base=origin/main` and focus on "PR #3: asset root renamed to `Assets/`, legacy lowercase read with a 
- [ ] S3 Deliver: merge base PR #3, `Unknownow/game-studio-base`, with a merge commit, and delete the branch (D1). If the gate or
- [ ] S4 Verify base, read-only:
- [ ] S5 In the fork:
- [ ] S6 Fix the case on disk.
- [ ] S7 Run the §6 commands 1–4 from the fork root with Python 3.12. If a check fails because of a fork-owned file, fix that fil
- [ ] S8 Run the §6 commands 5–7, the Unity ones, which are slow. Then:
- [ ] S9 Make the four commits in §9, in order, on fork `main`. Stage each one by its explicit paths (`git add <paths>`), and che
- [ ] S10 Call `judge` on the fork and fix any blocker or major findings with new commits on the same four-commit plan, amending t
- [ ] S11 Deliver: push fork `main` to `origin`, `Unknownow/game-studio-unity`. Then poll `gh run list --repo Unknownow/game-studi
- [ ] S12 Deliver: tag `v0.1.0` on fork `main` HEAD and push the tag (D4). Check with `git ls-remote --exit-code --tags origin v0.
- [ ] S13 Run `GH_CONFIG_DIR=/tmp/ghcfg-unknownow gh api -X PATCH repos/Unknownow/game-studio-unity -F is_template=true` (D4). Che
- [ ] S14 `rm -rf /tmp/ghcfg-unknownow` (D5), and confirm the path is gone.
## For you after the flow
- S15 Verify: open `D:/personal/game-studio-unity`, or a fresh clone on a case-sensitive checkout, in Unity 6000.3.25f1 — look
- S16 Verify: create a game repo from the `Unknownow/game-studio-unity` template and run `python tools/studio.py setup` in it 
