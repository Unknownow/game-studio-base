---
paths: ["src/gameplay/**"]
---

# Gameplay Code Rules

- ALL gameplay values MUST come from external config/data files, NEVER hardcoded
- Use delta time for ALL time-dependent calculations (frame-rate independence)
- NO direct references to UI code — use events for cross-system communication
  (events, signals or delegates, whichever the engine provides)
- Every gameplay system must implement a clear interface
- State machines must have explicit transition tables with documented states
- Write unit tests for all gameplay logic — separate logic from presentation
- Document which design doc each feature implements in code comments
- No static singletons for game state — use dependency injection

## Examples

**Correct** (data-driven):

```text
damage = combat_config.base_damage
speed  = stats.movement_speed * delta_time
```

**Incorrect** (hardcoded):

```text
damage = 25.0   // VIOLATION: hardcoded gameplay value
speed  = 5.0    // VIOLATION: not from config, not using delta time
```
