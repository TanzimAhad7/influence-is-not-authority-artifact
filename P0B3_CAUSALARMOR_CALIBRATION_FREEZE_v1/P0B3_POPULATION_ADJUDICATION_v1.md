# P0b-3 population adjudication v1

## Problem
The CausalArmor paper states both:
- AgentDojo `v1.2.2` in Appendix C.1; and
- `629` AgentDojo injection/security tasks in the experimental setup.

Exact AgentDojo package `0.1.35` exposes, for v1.2.2:
- 97 user tasks total;
- 35 suite-local injection targets total;
- 949 user×injection security pairs under the benchmark's cross-product evaluation.

The target-ID intersection with the older `v1` injection sets gives exactly 629 pairs.

## Prospective decision
- **Primary:** all 949 official v1.2.2 security pairs.
- **Secondary:** the 629 v1-target-ID intersection, evaluated from the same 949 run outputs.
- **Benign:** all 97 v1.2.2 user tasks.

We do not claim to know which hidden population produced the published Table-3 row. This design avoids
an outcome-dependent choice: the full source-faithful version is primary, while the paper-number-matched
subset is frozen before outcomes and reported separately.
