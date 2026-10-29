---
paths: ["tests/**"]
---

# Test Standards

- Test naming follows the engine's test framework and language — every name says the scenario and
  the expected result (for example `test_[scenario]_[expected]` or `[Scenario]_[Expected]`). The
  engine layer names the exact convention.
- Every test must have a clear arrange/act/assert structure
- Unit tests must not depend on external state (filesystem, network, database)
- Integration tests must clean up after themselves
- Performance tests must specify acceptable thresholds and fail if exceeded
- Test data must be defined in the test or in dedicated fixtures, never shared mutable state
- Mock external dependencies — tests should be fast and deterministic
- Every bug fix must have a regression test that would have caught the original bug —
  and **you must watch it fail before you trust it.** Run the new test against the
  unfixed code, confirm it fails, then apply the fix and confirm it passes. A
  regression test that has only ever been seen passing is not known to test anything.

  > This is `rules/skill-authoring.md`'s "a gate you have not watched fail
  > is not a gate", applied to tests. It is written out here because stating the
  > *goal* is not enough. A regression test for an iteration-order defect can use
  > a fixture where no cell takes part in two transfers per tick — it then passes
  > against the very bug it was written for, and looks authoritative doing it. The
  > fixture, not the assertion, is what makes it useless, and only running it
  > against the unfixed code exposes that.

## Examples

**Correct** (proper naming + Arrange/Act/Assert):

```text
test take_damage_reduces_health:
    // Arrange
    health = new Health(max = 100)

    // Act
    health.take_damage(25)

    // Assert
    assert_equal(75, health.current)
```

**Incorrect**:

```text
test test1:                      // VIOLATION: no descriptive name
    h = new Health()
    h.take_damage(25)            // VIOLATION: no arrange step, no clear assert
    assert_true(h.current < 100) // VIOLATION: imprecise assertion
```
