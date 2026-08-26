# A15a Protocol Note — USENIX-Oriented Consequence Measurement

## Objective

Measure the operational consequence of attribution-triggered selective sanitization on the already
successful benign A13 decision corpus, before returning to the minimal P1×P3 A14 causal experiment.

## Primary endpoints

1. Decision-level sanitizer activation rate at tau=0 among A13 `primary_valid` benign decisions.
2. External sanitizer generation calls per eligible decision.
3. External sanitizer generation calls per activated decision.
4. Measured sanitizer wall-clock latency per call and per activated decision.

## Required breakdown

Reuse A13's frozen labels:
- SPECIFIED
- DELEGATED
- PARTIAL (descriptive)

## Why this is a consequence experiment rather than a new attribution confirmation

The A13 Qwen attribution values are already observed. A15a uses those fixed scores only to define
which previously successful benign decisions would enter CausalArmor's expensive sanitizer path.
The new prospective outcomes are the sanitizer executions and latency/preservation artifacts.

## CausalArmor fidelity

- tau=0 rule follows Eq.5.
- Sanitizer model identifier: `google/gemini-2.5-flash`.
- Sanitizer prompt: Appendix D.1 text.
- Provider route: OpenRouter for continuity/access; explicitly not claimed equivalent to Vertex AI.
- Stage-1 sanitizer timing is a lower bound on total defense path overhead.

## What this experiment does not claim

It is not full end-to-end benign utility.
It does not rerun AgentDojo under the complete defense.
It does not include CoT masking or regenerated action execution.
It does not make the old A13 activation rates newly preregistered.
It does not establish source-fidelity Gemma attribution.

Those can be added only if A15a's selectivity consequence is sufficiently important to justify the
extra implementation cost.
