# P2B CROSS-MODEL REPLICATION v1.3

This package is a fresh, controlled replay-stability replication following the Qwen-native
P2b-v1 baseline gate failure.

Run order is frozen:
1. Llama
2. Gemma
3. Qwen canonical-adapter anchor

For EACH arm:
1. start its plain vLLM server;
2. run `P2b_XM_00_adapter_smoke.py` (3 technical calls; 3/3 required);
3. run `P2b_XM_01_freeze_model.py`;
4. run `P2b_XM_02_run_baseline.py` (130 scientific generations);
5. run `P2b_XM_03_check_gate.py`;
6. preserve PASS or FAIL exactly; never lower the gate.

No intervention script exists in this package intentionally. The purpose is to decide
whether the Qwen replay-stability failure is cross-model before any downstream redesign.

All exact server and run commands are provided in the accompanying ChatGPT handoff.


## Why v1.1 exists

The first Gemma scientific request in v1 was rejected by the Gemma chat template before
generation because the serialized conversation could contain consecutive `user` roles.
v1.1 applies the same deterministic role-normalization to all three fresh model families
and reruns all three so the joint comparison remains common-adapter.

Do not resume or pool a v1 baseline into v1.1.


## Authoritative v1.2 order

Run once before any v1.2 server:
1. `P2b_XM_00_resolve_revision_lock.py`

For each arm (Llama → Gemma → fresh Qwen):
1. start the v1.2 server helper;
2. `P2b_XM_00a_render_preflight.py` — must pass 26/26, zero generation;
3. `P2b_XM_00_adapter_smoke.py` — must pass 3/3;
4. `P2b_XM_01_freeze_model.py` — must print FREEZE PASS;
5. `P2b_XM_02_run_baseline.py` — 130 scientific generations;
6. `P2b_XM_03_check_gate.py`.

Do not mix v1/v1.1 results into v1.2.


## v1.3 secondary analysis after each 130-call baseline

Regardless of whether the primary baseline gate PASSes or FAILs, after the 130 rows exist
run:

`python -u P2b_XM_03a_argument_volatility.py --run-dir <MODEL_RUN_DIR>`

This does zero model calls. It writes:
- `P2B_ARGUMENT_VOLATILITY.json`
- `P2B_ARGUMENT_VOLATILITY.md`
- `P2B_ARGUMENT_SLOT_ROWS.csv`
- `P2B_ACTION_STRUCTURE_ROWS.csv`

Run it for all three arms before `P2b_XM_04_joint_compare.py`.

The primary 90% / 23-of-26 gate remains unchanged and cannot be overridden by the
secondary endpoint.
