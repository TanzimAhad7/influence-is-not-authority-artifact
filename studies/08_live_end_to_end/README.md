# 08 — Live End-to-End Execution

## Question

After a guardrail intervenes, what protected effect actually occurs when the agent continues executing?

## Main evidence

- `frozen_results/scientific_v1/RUN_ROWS.jsonl` — 420 live executions
- `frozen_results/prefreeze/final_prescience_build/FREEZE.json` — sealed analysis parameters
- `frozen_results/prefreeze/final_prescience_build/PAEF_ORACLE_FREEZE/` — protected-effect oracle freeze
- `code_and_protocol/` — final prescience runner/analysis package

## Scale

```text
14 natural tasks x 3 contexts x 2 defense states x 5 repeats = 420 executions
```

## Paper result

Under CONFLICT, the selected unauthorized outcome changes from 17/70 with defense off to 2/70 with defense on. Direct PAEF changes from 38/70 to 47/70, but its 95% CI includes zero.

After blocking, 12/13 selected-unauthorized proposals later recover an authorization-equivalent protected effect; all 9/9 blocked authorization-equivalent proposals end with PAEF=0.

The implementation-specific later-inspection analysis uses separate denominators (44/210, 22/210, 18/168, 18/18) and is not an exploit-rate estimate.

## Boundary

The natural task is the inferential unit, not each repeated execution.

## Verify

See `CLAIM_TO_ARTIFACT.md` entries `E2E.*`.
