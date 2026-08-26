# 01 — Natural Relevance

## Question

Do benign benchmark workflows contain privileged actions that legitimately depend on tool-provided information?

## Main evidence

- `corrected_natural_cohort/` — corrected natural cohort used for the paper result
- `generator_breadth/` — GPT-4o and Claude trajectory-generator breadth under the same fixed Llama scorer
- `original_natural_runs/` — original natural-run material
- `support/` — protocol freezes, extension inputs, logs, and historical supporting runs

## Paper result

The corrected cohort contains 29 valid privileged decisions across 25 tasks. User-side evidence dominates 75.0% of explicitly specified cases and 16.7% of delegated cases, a difference of +0.5833 with 95% CI [+0.1555,+0.9394].

The GPT-4o and Claude rows test generator breadth under one fixed attribution scorer; they are not native attribution replications.

## Boundary

This establishes ecological relevance in the audited benchmark, not deployment prevalence.

## Verify

```bash
bash VERIFY.sh
```

See `CLAIM_TO_ARTIFACT.md` entries `C1.*` and `B1.*`.
