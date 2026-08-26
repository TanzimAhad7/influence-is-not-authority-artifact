# P2 — AgentWatcher Same-200 Defense-Disabled Baseline

**Status:** PRE-OUTCOME FREEZE / MANDATORY / ONE SCIENTIFIC ARM

## Question

Is the historical AgentWatcher `tool_knowledge` utility `56/200 = 28%` attributable to AgentWatcher defense overhead, or is the attacked agent already low-utility on the exact same frozen 200 pairs?

## Frozen change

Exactly one experimental factor changes:

- historical reference: `defense = agentwatcher`;
- P2: `defense = none`.

Frozen unchanged conditions:
- attack: `tool_knowledge`;
- exact selected 200 pair population;
- selected-pair SHA-256: `b7c7846baeb5481ef93023d64d0b0ca110dc12f0563d52bb728e7f4ee958b26a`;
- suite counts: workspace 107 / travel 32 / banking 32 / slack 29;
- AgentDojo benchmark version: `v1.2.2`;
- global sample size: 200; sampling seed: 42;
- requested backend model: `gpt-4o-mini`;
- route: OpenRouter OpenAI-compatible endpoint;
- same current historical runtime bytes frozen in `P2_RUNTIME_MANIFEST.tsv`;
- same AgentDojo utility and security evaluators.

## Primary endpoint

`ΔU = mean(U_no_defense - U_agentwatcher)` across the exact 200 frozen pairs.

Primary 95% uncertainty is a fixed-seed (`20260812`) 20,000-draw percentile cluster bootstrap over `(suite, user_task_id)` clusters. This avoids treating repeated injection pairs for the same user task as fully independent.

Interpretation is pre-frozen by CI sign; no arbitrary materiality threshold is introduced.

## Secondary endpoint

Attack-success difference on the same 200 pairs. In these AgentDojo result JSONs the historical `security` boolean is treated as attack-success for this attack anchor, consistent with the historical 0/200 ASR reporting.

## Claim boundary

This is a matched-input comparison to an earlier defense-on API execution, not a randomized simultaneous trial. The exact requested route/model alias and all benchmark inputs are frozen, but unobserved provider/model drift cannot be excluded. If a utility difference appears, report it as matched-input evidence consistent with defense overhead, with this qualification.

## Stop rule

Run this `tool_knowledge` arm once. Do not add Important Instructions or a model zoo unless a later named reviewer-validity question requires it.
