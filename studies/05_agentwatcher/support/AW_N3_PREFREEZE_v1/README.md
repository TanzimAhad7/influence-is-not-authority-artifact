# AW_N3_PREFREEZE_v1

Source-locked AgentWatcher × frozen N3 matched authorization-discrimination package.

## Files

- `AWN3_00_build_inputs.py` — zero-call builder; establishes denominator and SHAM/ECHO static-input identity.
- `AWN3_01_freeze_protocol.py` — freezes the accepted author-side denominator, full 2×2 secondary, estimands, parser gate, and outcome framing.
- `AWN3_02_preflight.py` — synthetic-only monitor + attribution preflight.
- `AWN3_03_run_science.py` — one complete source-locked run over frozen unique inputs.
- `AWN3_04_analyze.py` — maps unique outputs to frozen N3 conditions and computes 24-base primary/secondary endpoints.
- `AWN3_05_verify.py` — independent deterministic integrity/result re-derivation.
- `start_AWN3_monitor_vllm.sh` — starts the exact frozen Qwen3 monitor adapter on a dedicated GPU.

## Intended project layout

```text
phase0_pilot/
├── AW_N3_PREFREEZE_v1/
├── AW_N3_AUTHOR_v1/
├── N3_PREFREEZE_AUTHOR_v1_1/
├── a15b0_architecture_boundary/
├── external/AgentWatcher/
├── logs/
└── artifacts/                 # untouched during run
```

## Run order

1. Run `build_AWN3_v1.sh` and **stop**. Review the author-side denominator before freeze.
2. Run `freeze_AWN3_v1.sh` after approval.
3. Start the exact frozen monitor endpoint in the background.
4. Run `preflight_AWN3_v1.sh` on synthetic text only.
5. Run `run_AWN3_v1.sh` once in the background. It executes science → analysis → verifier.
6. Stop before CV2. Reconcile raw outputs → canonical → buried-result audit → blueprint.

No AW-N3 file should be promoted into `artifacts/` before final integrity/science reconciliation.
