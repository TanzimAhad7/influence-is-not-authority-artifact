# B1 — openai/gpt-4o prospective replication

- B1 protocol: `d17e7252c7c390257b5cdb9f88af770804a503127e4180ea90094aa78eaef550`
- Agent: `openai/gpt-4o` via OpenRouter
- Temperature: `0.0`
- Attribution scorer: `meta-llama/Llama-3.3-70B-Instruct` (boundary-safe fixed completion)
- Population: C0-corrected frozen A13 census (55 tasks / 73 decisions)

## Primary H_mean_del

- SPECIFIED: `0.8333333333333334`
- DELEGATED: `0.4444444444444444`
- Difference: `0.38888888888888895`
- 95% task-bootstrap CI: `[-0.027272727272727337, 0.7857142857142858]`
- Replication category: **DIRECTIONAL_POSITIVE_CI_INCLUDES_ZERO_OR_UNAVAILABLE**

## Continuous M_del

- SPECIFIED: `0.8210491189140993`
- DELEGATED: `-0.08967670352675006`
- Difference: `0.9107258224408493`
- 95% task-bootstrap CI: `[0.10366639991148151, 1.778493563819895]`

## Guardrails

This is a post-A14 prospective replication of an A12 discovery backbone. It is not part of the original A13 preregistration.
No model-specific task selection, relabeling, mapper tuning, or endpoint tuning is permitted from this output.
