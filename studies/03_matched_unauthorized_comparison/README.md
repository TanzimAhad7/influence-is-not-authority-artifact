# 03 — Matched Unauthorized Comparison

## Question

Does the signal still respond to a real authorization violation, and how does that response compare with the harmless source relocation?

## Main evidence

- `frozen_results/N3_ANALYSIS.json`
- `frozen_results/science_llama/SCIENCE_SCORES.jsonl`
- `frozen_results/science_gemma/SCIENCE_SCORES.jsonl`
- `support/` — frozen package, launchers, logs, and complete archive

## Paper result

The matched unauthorized endpoint is more attack-like overall under both scorers, but the harmless source relocation produces the larger average displacement. Case-level authorization-changing signs are heterogeneous.

## Boundary

The matched unauthorized arm is teacher-forced and tests the construct; it is not a deployment attack-frequency estimate.

## Verify

See `CLAIM_TO_ARTIFACT.md` entries `N3.*`.
