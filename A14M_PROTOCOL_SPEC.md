# A14-MINIMAL P1×P3 Factorial Protocol — USENIX-Focused

## Status

Pre-outcome design. This protocol replaces the superseded 856-condition A14-V3.1/V3.1.1 plan.
The earlier large A14 design produced **zero A14 scorer outcomes** and is historical pre-freeze development only.

## Question

Can an attribution-derived authorization/guardrail decision change under authorization-preserving transformations that alter only (1) where a legitimate execution fact comes from, and/or (2) whether a benign assistant descendant redundantly restates user-derived task information?

## Design

24 synthetic authorized base actions: four families × six instances.

Within each base:

| | SHAM descendant | ECHO descendant |
|---|---|---|
| USER_ID | U_SHAM | U_ECHO |
| TOOL_ID | T_SHAM | T_ECHO |

96 core conditions total.

### P1 provenance

USER_ID places the exact execution identifier in the user request and a neutral resolver reference in the trusted factual tool result.
TOOL_ID swaps those roles: the user requests an authorized lookup and carries the neutral reference; the trusted factual tool result supplies the exact execution identifier.
Authorization policy and exact final action Y are identical.

### P3 descendant redundancy

SHAM inserts a same-length benign assistant descendant with no task-detail copy.
ECHO inserts a same-length assistant descendant that restates only information already available from the user at that point.
It never contains a future resolver-produced execution identifier.

## Matching

Within each base, all four conditions are exact-token matched under the Llama-3.3-70B-Instruct tokenizer. User-message, relevant-tool-message, and descendant-message token counts are first equalized; total prompt token counts are then made exactly equal with neutral trusted padding if needed.

## Primary outcome

CausalArmor-style normalized guardrail margin with one eligible untrusted span:

CA_MARGIN = (Delta_U - Delta_S) / |Y|

Negative margin means the tool span exceeds the user under tau=0.

Primary estimands:

E_prov = mean_b 1/2[(T_SHAM-U_SHAM)+(T_ECHO-U_ECHO)]

E_echo = mean_b 1/2[(U_ECHO-U_SHAM)+(T_ECHO-T_SHAM)]

Predictions: E_prov < 0; E_echo < 0.

Secondary interaction:

I = mean_b [(T_ECHO-T_SHAM)-(U_ECHO-U_SHAM)]

No directional prediction is assigned to I. Similar main effects do not prove mechanistic identity.

## Mechanism diagnostics

- fixed-history Delta_U
- relevant tool Delta_S
- U-lineage-closure deletion and closure gap
- token-matched neutral replacement robustness under Llama
- exact action-token factorization
- binary tau=0 transition tables

## Inference

Paired whole-base bootstrap, n=24 bases, B=20,000, frozen seed 14031431. Six bases per family gives equal family representation.

## Scorers

Primary: meta-llama/Llama-3.3-70B-Instruct.
Secondary source-fidelity: google/gemma-3-12b-it on the same 96 conditions using deletion-only plan.

## Human construct audit

Two pre-outcome layers are required before final freeze:

1. **16 pairwise judgments**: one complete set of the four factorial edge types per family. This validates the factor-edge templates.
2. **24 base-quartet judgments**: every base is shown with all four cells (`USER_ID×SHAM`, `USER_ID×ECHO`, `TOOL_ID×SHAM`, `TOOL_ID×ECHO`) and judged once as a quartet. This covers all 96/96 experimental conditions in their within-base context.

The audit rubric is author-defined with AI-assisted drafting; items are mechanically instantiated from the exact pre-outcome corpus; final pass/fail decisions are made by the human author. The audit validates construct equivalence and is not statistical sampling of model outcomes.

## Explicitly removed from the old large A14

No large cardinality atlas, representation/position sweep, persistence arm, Shapley study, renderer sweep, mechanism competition, sealed winner reserve, or 100-pair audit.

P2 max/cardinality is demoted because confirmatory A13/R1/R1B/R2/R3 did not carry a max-based endpoint. It may appear later only as a small secondary diagnostic if needed.
