---
paths: ["src/core/**"]
---

# Engine Code Rules

- ZERO allocations in hot paths (update loops, rendering, physics) — pre-allocate, pool, reuse
- All engine APIs must be thread-safe OR explicitly documented as single-thread-only
- Profile before AND after every optimization — document the measured numbers
- Engine code must NEVER depend on gameplay code (strict dependency direction: engine <- gameplay)
- Every public API must have usage examples in its doc comment
- Changes to public interfaces require a deprecation period and migration guide
- Use RAII / deterministic cleanup for all resources
- All engine systems must support graceful degradation
- Before writing engine API code, consult `engine-reference/` for the current engine version and verify APIs against the reference docs

## Examples

**Correct** (zero-alloc hot path):

```text
// buffer allocated once, reused every frame
nearby_cache = allocate_array(64)

function fixed_update():
    count = physics_query_radius(position, radius, nearby_cache)   // fills the buffer
```

**Incorrect** (allocating in hot path):

```text
function fixed_update():
    nearby = new_array()                      // VIOLATION: allocates every frame
    nearby = find_all_in_group("enemies")    // VIOLATION: scene query every frame
```
