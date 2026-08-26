# A15a — Benign Selectivity / Sanitizer Consequence

Protocol: `eed2cf8a7ff858f686b258cac3fd88802311305aa86a89f8a6b760a21dac3e50`

- Eligible successful benign decisions: **26**
- Activated at tau=0: **18/26 = 0.692**
- Flagged tool spans: **53/96 = 0.552**
- Sanitizer calls: **53**
- Calls per eligible decision: **2.038**
- Calls per activated decision: **2.944**

## Frozen A13 label breakdown

- DELEGATED: 8/9 activated (0.889)
- PARTIAL: 9/10 activated (0.900)
- SPECIFIED: 1/7 activated (0.143)

## Sanitizer wall-clock (this deployment)

- mean per call: 0.803 s
- median per call: 0.647 s
- p95 per call: 1.369 s
- mean serial sanitizer time per activated decision: 2.364 s

This excludes attribution time, CoT masking, agent regeneration, and execution, so it is a lower bound
on the full defense path. Absolute latency is deployment-specific because Gemini-2.5-Flash is accessed
through OpenRouter here rather than the paper's Vertex AI route.

## Preservation diagnostics (descriptive only)

- numeric token recall mean: 0.9857142857142858
- lexical token recall mean: 0.9553390378597764
- sanitized/original char ratio mean: 0.9624985585984833

Do not interpret lexical preservation as task utility. Full end-to-end utility/regeneration belongs in A15b or a dedicated follow-up.
