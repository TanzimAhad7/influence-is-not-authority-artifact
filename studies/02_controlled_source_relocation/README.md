# 02 — Controlled Source Relocation

## Question

Does the causal-support signal change when one required value moves from the user request to a legitimate tool result while authorization, the protected value, the exact action, and the intended effect stay fixed?

## Main evidence

- `frozen_results/analysis/results.json` — primary matched analysis
- `frozen_results/scorer_llama/condition_scores.jsonl` — Llama condition-level scores
- `frozen_results/scorer_gemma/condition_scores.jsonl` — Gemma condition-level scores
- `support/` — protocol, scoring, analysis, and prefreeze material

## Paper result

All 24/24 matched bases move in the more attack-like direction under both scorers. Mean score changes are -1.1797 for Llama and -1.0112 for Gemma.

## Boundary

The 96 factorial conditions come from 24 matched bases. The matched base is the inferential unit.

## Verify

See `CLAIM_TO_ARTIFACT.md` entries `A14.*`.
