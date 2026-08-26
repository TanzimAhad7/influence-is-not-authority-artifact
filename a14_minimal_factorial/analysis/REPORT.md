# A14 Minimal P1×P3 Factorial — Primary Analysis

Protocol: `94bb3c7e0ca174aa8be69b8c0949e7d93a567d960a9ba06016ba4d08f8503ee1`

## Primary Llama estimands

- P1 provenance main effect on CA_MARGIN: **-1.179732**, 95% paired-base bootstrap CI **[-1.283611, -1.079748]**
- P3 descendant main effect on CA_MARGIN: **-0.855730**, 95% paired-base bootstrap CI **[-1.082978, -0.606038]**
- P1×P3 interaction (secondary mechanistic): **+0.143308**, 95% CI **[+0.064341, +0.229169]**

Predicted directions: P1 < 0 and P3 < 0. Interaction direction was intentionally left open.

## Binary guardrail transitions (tau=0)

- P1_SHAM: flip 2/24 (0.083); safe→flag 2, flag→safe 0
- P1_ECHO: flip 17/24 (0.708); safe→flag 17, flag→safe 0
- P3_USER: flip 3/24 (0.125); safe→flag 3, flag→safe 0
- P3_TOOL: flip 18/24 (0.750); safe→flag 18, flag→safe 0

## Interpretation boundaries

- Similar P1 and P3 effect sizes do not prove the same mechanism.
- The interaction diagnoses redundancy/additivity/synergy but is not a proof of mechanistic identity.
- A14M is controlled synthetic causal evidence; A13 supplies ecological evidence and A15a supplies measured operational consequence.
- Gemma, if run, is secondary source-fidelity replication.
