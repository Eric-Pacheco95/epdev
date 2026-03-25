# Self-Heal Tests

Verification that the system can detect, diagnose, and fix its own failures.

## Self-Heal Protocol

When any test or operation fails:

1. **DETECT** — Identify the failure (exit code, error message, assertion failure)
2. **DIAGNOSE** — Analyze root cause (read logs, check state, trace dependencies)
3. **PROPOSE** — Generate a fix (code change, config update, rollback)
4. **APPLY** — Implement the fix
5. **VERIFY** — Re-run the original test + regression suite
6. **LEARN** — Log to `memory/learning/failures/` with prevention strategy

## Escalation

- **Attempt 1**: Auto-fix and verify
- **Attempt 2**: Try alternative fix approach
- **Attempt 3**: Escalate to owner with full diagnosis

## Test Structure

Each self-heal test validates a specific recovery scenario:

```bash
# test_selfheal_{scenario}.sh
# 1. Introduce a controlled failure
# 2. Run the self-heal protocol
# 3. Verify recovery
# 4. Verify no regressions
```

## Metrics

Track per-scenario:
- Mean time to detect (MTTD)
- Mean time to recover (MTTR)
- Auto-fix success rate
- Regression introduction rate
