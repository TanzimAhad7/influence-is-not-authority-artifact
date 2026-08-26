# A13-R2 Full Llama Agent + Boundary-Safe Llama Scorer — Result

- Protocol hash: `c857e8988cd1412c439116cb941a26a256227e97650778c82894b37068419b28`
- Source SHA256: `a1df5014a2e1ebb4f4216ed5287b71c46d0f5cd37edca601ed6d54bd94e814a4`
- AgentDojo: `0.1.35`
- Agent model: `meta-llama/Llama-3.3-70B-Instruct`
- Scorer model: `meta-llama/Llama-3.3-70B-Instruct`
- Scientific status: **prospective cross-agent replication frozen after A13/R1/R1B but before any R2 AgentDojo outcome.**

## Primary hypothesis

`P(H_mean=1 | SPECIFIED) > P(H_mean=1 | DELEGATED)`, where `H_mean = I[ΔU_del > mean(ΔS_del)]`.

| quantity | SPECIFIED | DELEGATED | difference | task-bootstrap 95% CI |
|---|---:|---:|---:|---:|
| H_mean rate | 0.500 | 0.250 | 0.250 | [-0.429, 0.833] |
| M = ΔU − mean(ΔS) | 0.578 | -0.597 | 1.174 | [-0.022, 2.721] |

Primary tasks represented: SPECIFIED=6, DELEGATED=4.

## Decision-level descriptive table

| label | tasks | decisions | mean-order hold | max-order hold | M mean | max fails given mean+ |
|---|---:|---:|---:|---:|---:|---:|
| SPECIFIED | 6 | 7 | 57.1% | 57.1% | 0.564 | 0.0% |
| DELEGATED | 4 | 6 | 50.0% | 33.3% | -0.346 | 33.3% |
| PARTIAL | 9 | 9 | 55.6% | 44.4% | 0.031 | 20.0% |

## Per-suite descriptives

| suite | tasks | decisions | mean-order hold | max-order hold | M mean |
|---|---:|---:|---:|---:|---:|
| workspace | 4 | 4 | 25.0% | 25.0% | -0.154 |
| slack | 9 | 13 | 69.2% | 53.8% | 0.068 |
| travel | 2 | 2 | 50.0% | 50.0% | 0.238 |
| banking | 3 | 3 | 33.3% | 33.3% | 0.468 |

## Continuous prompt-coverage relationship

Across 18 confirmatory tasks, task-level specified_fraction vs M_del: Pearson=0.388, Spearman=0.200.

## Qwen/Llama common support under the same boundary-safe Llama scorer

Common primary population: 7 decisions / 7 tasks.

| agent trajectories | H SPEC | H DEL | H diff | M SPEC | M DEL | M diff |
|---|---:|---:|---:|---:|---:|---:|
| Qwen (R1B) | 0.800 | 0.000 | 0.800 | 0.920 | -0.624 | 1.544 |
| Llama (R2) | 0.400 | 0.000 | 0.400 | 0.597 | -1.195 | 1.791 |
Decision-level H agreement=0.714; M Pearson=0.991; M Spearman=0.821.

## Frozen sensitivity grid

| specified ≥ | delegated ≤ | Δ H_mean | 95% CI | Δ M | 95% CI |
|---:|---:|---:|---:|---:|---:|
| 0.90 | 0.10 | 0.250 | [-0.429, 0.833] | 1.174 | [-0.022, 2.721] |
| 0.80 **PRIMARY** | 0.20 | 0.250 | [-0.429, 0.833] | 1.174 | [-0.022, 2.721] |
| 0.70 | 0.30 | 0.250 | [-0.429, 0.833] | 1.174 | [-0.022, 2.721] |

## Exclusions / completeness

- `agentdojo_utility_false`: 31
- `ground_truth_privileged_call_not_executed_or_not_mappable`: 14
- `no_eligible_tool_span`: 2
- `valid`: 22

## Interpretation guardrails

- A positive contrast supports association between the frozen prompt-coverage operationalization and attribution ordering.
- A13 does not by itself prove causality; A14 is the matched causal test.
- R is secondary/descriptive and must not define delegation.
- Mean-based attribution is diagnostic, not yet a production defense.
- Max-vs-mean discrepancies are observational in A13/A12; causal N claims require controlled A14 manipulation.

## What this experiment can establish

If the frozen SPECIFIED group has a clearly higher mean-order rate and upward-shifted M distribution than the DELEGATED group on untouched tasks, A13 provides prospective generalization evidence that task/action information provenance predicts the underlying attribution regime.

It still does **not** prove the provenance mechanism causally. That is A14's role. It also does not establish that replacing max with mean is a safe defense; that must be evaluated with malicious and benign cases in A15.

