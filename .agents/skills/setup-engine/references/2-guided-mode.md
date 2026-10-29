# /setup-engine — Section 2: Guided Mode

> Part of `/setup-engine`. `SKILL.md` names when to read this file; the settings it
> resolved and the rules under its later headings still apply here.

## 2. Guided Mode (No Arguments)

**In this file:**

- Check for existing game concept
- If the user wants to pick without a concept, ask in this order
- Produce a recommendation

If no engine is specified, run an interactive engine selection process:

### Check for existing game concept
Read the design artifact for the resolved tier (see **Tier awareness** above), by
section: find the headings you need with the Grep tool (pattern `^#`, content
mode) and Read those ranges with offset and limit:
- **`standard` / `full`**: read `design/gdd/game-concept.md` if it exists —
  extract genre, scope, platform targets, art style, team size, and the engine
  preference `/brainstorm` recorded (an engine the user named, or "undecided":
  `/brainstorm` never recommends one, so the recommendation is made here).
- **`minimal`**: read `design/game-brief.md` if it exists — extract genre,
  scope, platform, and art direction from its fields. Its absence is **expected**
  at `minimal` (the brief is authored *after* engine setup in the minimal path), so
  do not treat a missing brief as a gap — proceed straight to guided selection.
- If no concept **or** brief exists, inform the user:
  > "No game concept found. Consider running `/brainstorm` first to discover what
  > you want to build — it records your engine preference if you have one. Or
  > tell me about your game and I can help you pick."

  (At `minimal` this is optional, not a prerequisite — you can pick an engine now
  and write the brief next.)

### If the user wants to pick without a concept, ask in this order:

**Question 1 — Prior experience** (ask this first, always,):
- Prompt: "Have you worked in any of these engines before?"
- Options: `Unity` / `Another engine (you write its ENGINE.md)` / `Multiple — I'll explain` / `None of them`
- If they pick a specific engine → recommend that engine. Prior experience outweighs all other factors. Confirm with them and skip the matrix.
- If "None" or "Multiple" → continue to the questions below.

**Questions 2-6 — Decision matrix inputs** (only if no prior engine experience):

**Question 2 — Target platform** (ask this second, always, — platform eliminates or heavily weights engines before any other factor):
- Prompt: "What platforms are you targeting for this game?"
- Options: `PC (Steam / Epic)` / `Mobile (iOS / Android)` / `Console` / `Web / Browser` / `Multiple platforms`
- Platform rules that feed directly into the recommendation:
  - Mobile → Unity is a strong fit
  - Console → Unity has mature console support
  - Web → Unity WebGL is functional
  - PC only → all engines viable; other factors decide
  - Multiple → Unity is the most portable across PC/mobile/console

1. **What kind of game?** (2D, 3D, or both?)
2. **Primary input method?** (keyboard/mouse, gamepad, touch, or mixed?)
3. **Team size and experience?** (solo beginner, solo experienced, small team?)
4. **Any strong language preferences?** (C#, C++, visual scripting?)
5. **Budget for engine licensing?** (free only, or commercial licenses OK?)

### Produce a recommendation

Do NOT use a simple scoring matrix that eliminates engines. Instead, reason through the user's profile against the honest tradeoffs below, then present 1-2 recommendations with full context. Always end with the user choosing — never force a verdict.

**Engine honest tradeoffs:**

**Unity**
- Genuine strengths: Industry standard for mid-scope 3D and mobile; massive asset store and tutorial ecosystem; C# is a professional language; best console certification support for indie; strong community for almost every genre
- Real limitations: Licensing controversy in 2023 damaged trust (runtime fee was proposed then walked back — the risk of policy changes remains real); C# has a steeper initial curve than scripting languages; heavier editor for simple projects
- Licensing reality: Free under $200K revenue AND 200K installs (Unity Personal/Plus). Only becomes costly if the game is genuinely successful — most indie games never hit this threshold. The 2023 controversy is worth knowing about but the actual current terms are reasonable for most indie developers.
- Best fit: Mobile games; mid-scope 3D; games targeting console; developers with C# background; projects needing large asset store; teams of 2-5

**Genre-specific guidance** (factor this into the recommendation):
- Unity covers 2D and 3D, mobile, PC and console; match the choice to the team's C# experience and the target platform
- Another engine fits better → say so, and offer to write its `ENGINE.md` hooks together (this template ships a Unity layer only)

**Recommendation format:**
1. Show a comparison table with the user's specific factors as rows
2. Give a primary recommendation with honest reasoning
3. Name the best alternative and when to choose it instead
4. Explicitly state: "This is a starting point, not a verdict — you can always migrate engines, and many developers switch between projects."
5. Ask to confirm: "Does this recommendation feel right, or would you like to explore a different engine?"
   - Options: `[Primary engine] (Recommended)` / `[Alternative engine]` / `[Third engine]` / `Explore further` / `Type something`

**If the user picks "Explore further":**
Ask with concept-specific deep-dive topics. Always generate these options from the user's actual concept — do not use generic options. Always include at minimum:
- The primary engine's specific limitations for this concept (e.g., "How far can this engine go for [genre]?")
- The alternative engine's specific tradeoffs for this concept
- Language choice impact on this concept's technical challenges
- Any concept-specific technical concern (e.g., adaptive audio, open-world streaming, multiplayer netcode)

The user can select multiple topics. Answer each selected topic in depth before returning to the engine confirmation question.

---
