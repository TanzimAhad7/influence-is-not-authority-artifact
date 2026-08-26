# B1 — anthropic/claude-sonnet-4.5 prospective replication

- B1 protocol: `d17e7252c7c390257b5cdb9f88af770804a503127e4180ea90094aa78eaef550`
- Agent: `anthropic/claude-sonnet-4.5` via OpenRouter
- Temperature: `0.0`
- Attribution scorer: `meta-llama/Llama-3.3-70B-Instruct` (boundary-safe fixed completion)
- Population: C0-corrected frozen A13 census (55 tasks / 73 decisions)

## Primary H_mean_del

- SPECIFIED: `0.6153846153846154`
- DELEGATED: `0.4`
- Difference: `0.2153846153846154`
- 95% task-bootstrap CI: `[-0.3711057692307691, 0.7333333333333333]`
- Replication category: **DIRECTIONAL_POSITIVE_CI_INCLUDES_ZERO_OR_UNAVAILABLE**

## Continuous M_del

- SPECIFIED: `0.4483237589769508`
- DELEGATED: `-0.5261674184301038`
- Difference: `0.9744911774070546`
- 95% task-bootstrap CI: `[-0.06434624776899199, 2.2378314126842827]`

## Guardrails

This is a post-A14 prospective replication of an A12 discovery backbone. It is not part of the original A13 preregistration.
No model-specific task selection, relabeling, mapper tuning, or endpoint tuning is permitted from this output.
