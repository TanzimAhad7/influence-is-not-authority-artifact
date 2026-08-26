# P3 zero-call analysis freeze

**Status:** PASS

Freeze SHA-256: `55ebdefde3d461f93b4c39354d0d886865506fa8d8497dbccc228685259d7b3e`

This freeze records a **post-hoc falsification/sensitivity analysis** of already-observed data. It is not a prospective confirmatory endpoint.

- scientific model calls: **0**
- A13 decisions rows: **69**
- A15a inventory rows: **26**
- corrected P2b raw rows: **390**
- corrected P2b decision inventory: **26**

## Claim boundaries
- This is an existing-data post-hoc falsification/sensitivity analysis, not a new prospective confirmatory endpoint.
- Do not infer that A15a activation causally creates replay divergence or estimand masking.
- Do not reinterpret or replace any frozen P2b gate.
- Do not treat 390 generations as 390 independent statistical units; primary P2b sensitivity uses model-by-decision cells and decision clustering.
- Do not claim a class-wide replay-defense error floor from this analysis.
- No P2b intervention is authorized by this analysis.

## Frozen inputs
- `config`: `2cf0361d6987e8bdf119b5864881338cc9b960e3d6cfa43dff4a9f2bbad024cf` — `/home/anon_/ratchet/phase0_pilot/P3_ZERO_CALL_HARDENING_v1/P3_CONFIG.json`
- `analysis_script`: `75120489d3fad48dd7f103572efb2f08c7bf9a30df7d92d48bc288993d718fed` — `/home/anon_/ratchet/phase0_pilot/P3_ZERO_CALL_HARDENING_v1/P3_01_run_hardening.py`
- `a13_decisions`: `af6a62c5689e7d26180f0091a121839b645e1dcb54e5aaf87427f6e75c19dca9` — `/home/anon_/ratchet/phase0_pilot/a13/decisions.jsonl`
- `a13_results`: `6ced3fc14a60574f95881344ac3d6bb5b8cf7d88d59ac3c844cae35d4121646b` — `/home/anon_/ratchet/phase0_pilot/a13/results.json`
- `a15a_inventory`: `180a3767588932c160ca4de6fb18c6cd1e0331568814525d31663d416e3d5883` — `/home/anon_/ratchet/phase0_pilot/a15a_selectivity_consequence/decision_inventory.jsonl`
- `a15a_results`: `37ceca159e85c2bc3f8401f78e77ccde588373f8064a97f67b6bd19b54e303d2` — `/home/anon_/ratchet/phase0_pilot/a15a_selectivity_consequence/results.json`
- `taxonomy`: `66a1705d422a0a8e0b7630f099c806df646f9354f996648d659dbb4a2f519b90` — `/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/P2B_ARGUMENT_ROLE_TAXONOMY.json`
- `replay_inventory`: `9fc33a564480335aac2a91a87794a7aea737315ebd3d1c2b9facd07cd7afdded` — `/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/inputs/P2B_REPLAY_INVENTORY.jsonl`
- `llama_raw`: `d0bd22bc6fdf5adaab3cfcbdbaf95702d48cd1c8a52b28373113e772d6b66b79` — `/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_LLAMA_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl`
- `gemma_raw`: `172c43d3f7fc73a29f5d9b742eb506fab6051c00f5cbbe3e28fd180873f8375a` — `/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_GEMMA_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl`
- `qwen_raw`: `2024e9b370e78897a577fe5025a346ea9be074b262a2b3c6c05c02ae3e4095e2` — `/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_QWEN_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl`
- `llama_slots`: `41d98f552eb0b524f19c97d99fe5c6df3c85356388807b26d99ff8cb54078928` — `/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_LLAMA_RUN_v1_2/P2B_CI_ARGUMENT_SLOT_ROWS.csv`
- `gemma_slots`: `028b4da4a4e75aa1140298505f3d78ea16b62a1d6847a1d52ccb1e85c0a7200f` — `/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_GEMMA_RUN_v1_2/P2B_CI_ARGUMENT_SLOT_ROWS.csv`
- `qwen_slots`: `f27d753abf2d3fedeb7fd08743a1dac692791ed7bb75b3e619d4e2a97b108905` — `/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_QWEN_RUN_v1_2/P2B_CI_ARGUMENT_SLOT_ROWS.csv`
