# 04 — Threshold Frontier

## Question

Can a single scalar threshold cleanly separate the matched authorized and unauthorized actions?

## Main evidence

- `frozen_results/R2B_JTF_RESULTS.json`
- `frozen_results/R2B_JTF_FRONTIER_llama.csv`
- `frozen_results/R2B_JTF_FRONTIER_gemma.csv`
- `support/` — deterministic threshold-analysis package

## Paper result

At operating points with zero tested authorized flags, Llama catches 12/48 matched unauthorized alternatives and Gemma catches 18/48. The complete sweep contains 386 rows per scorer.

## Boundary

The full sweep is descriptive. No preferred threshold is selected.

## Fresh deterministic rerun

```bash
bash RUN_END_TO_END.sh --stage 06
```
