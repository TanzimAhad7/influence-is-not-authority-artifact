# P3 Zero-Call Hardening v1

Purpose: run the current v83 P3 hardening plan entirely from existing A13/A15a/corrected-P2b artifacts.

**Scientific status:** post-hoc falsification/sensitivity analysis. It does not replace any frozen primary endpoint or authorize any P2b intervention.

## Inputs expected under `--project-root`

- `a13/decisions.jsonl`
- `a13/results.json`
- `a15a_selectivity_consequence/decision_inventory.jsonl`
- `a15a_selectivity_consequence/results.json`
- `P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/P2B_ARGUMENT_ROLE_TAXONOMY.json`
- `P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/inputs/P2B_REPLAY_INVENTORY.jsonl`
- `P2B_XM_CI_{LLAMA,GEMMA,QWEN}_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl`
- the three `P2B_CI_ARGUMENT_SLOT_ROWS.csv` files

## Order

1. `P3_00_freeze_analysis.py` — hash/seal code + inputs; zero model calls.
2. `P3_01_run_hardening.py` — deterministic existing-data analysis.
3. `P3_02_hash_outputs.py` — hash final outputs.

No vLLM server, OpenRouter key, HF token, GPU, or model call is required.
