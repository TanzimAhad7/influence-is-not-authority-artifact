# P0b-3-ACT zero-call post-hoc descriptive split

Purpose: deterministically split the already-frozen P0b-3 Attempt-1 ACTION_ONLY activation count into benign versus attack privileged-decision denominators.

This package performs **zero model calls** and imports only Python standard-library modules.

## Input lock

Expected source:
`P0B3_CAUSALARMOR_LIVE_RUN_v1/P0B3_DEFENSE_EVENTS.jsonl`

Expected SHA-256:
`bc8c17c257b00a12295c54384c9ce7bc3490f8d6c1f1d3b89aee36641253746a`

Expected successful privileged-decision events: `624`.

ACTION_ONLY activation is `primary_any_flag`; the scripts require it to equal `intervened` on every event.

## Required two-stage author run

From the project root:

```bash
python3 P0B3_ACT_ZERO_CALL_v1/P0B3_ACT_00_freeze.py
python3 P0B3_ACT_ZERO_CALL_v1/P0B3_ACT_01_run.py
```

The freeze stage records source-code hashes, exact input hash, and benign/attack denominators **without aggregating activation outcomes**. The run stage refuses to execute if code, input, or denominators differ from the freeze.

Reporting is descriptive only: benign activation rate, attack activation rate, and the attack-minus-benign percentage-point difference. No CI, p-value, threshold tuning, model expansion, causal claim, ASR claim, or novelty claim is authorized.
