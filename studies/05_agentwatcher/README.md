# 05 — AgentWatcher

Two separate experiments are kept distinct here.

## Paired gate study

`paired_gate_study/` contains the matched AUTH/ALT gate experiment.

Frozen result:

```text
ALIGNED:  authorized 4/24 flagged, unauthorized 21/24 flagged
CONFLICT: authorized 24/24 flagged, unauthorized 24/24 flagged
```

This is gate-level evidence.

## Separate ON/OFF population

`on_off_comparison/` contains the separate 200-input matched-input operational comparison.

Frozen result:

```text
defense OFF: attack success 16%, utility 60%
defense ON:  attack success 0%,  utility 28%
```

These are separate API executions and should not be merged with the paired gate study.

## Support

`support/` contains prefreeze packages, integration checks, and supporting AgentWatcher runs.

## Verify

See `CLAIM_TO_ARTIFACT.md` entries `AW.*`.
