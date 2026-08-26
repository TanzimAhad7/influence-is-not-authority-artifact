# A13 Prospective Benign Task/Provenance Survey — Result

- Protocol hash: `b4a140c7d8ef49149ac72e35e9e52405f614fa5361558c7b2ac0c56fe0063b80`
- Source SHA256: `f771850375b4f5af7bc2cec6a4e166057f33fab26d686320b8ef2d8d32557f05`
- AgentDojo: `0.1.35`
- Agent/scorer model: `Qwen/Qwen2.5-72B-Instruct`
- Scientific status: **prospective on tasks excluded from prior development; A12 remains exploratory/discovery.**

## Primary hypothesis

`P(H_mean=1 | SPECIFIED) > P(H_mean=1 | DELEGATED)`, where `H_mean = I[ΔU_del > mean(ΔS_del)]`.

| quantity | SPECIFIED | DELEGATED | difference | task-bootstrap 95% CI |
|---|---:|---:|---:|---:|
| H_mean rate | 0.857 | 0.222 | 0.635 | [0.167, 1.000] |
| M = ΔU − mean(ΔS) | 0.980 | -0.034 | 1.014 | [-0.068, 2.314] |

Primary tasks represented: SPECIFIED=7, DELEGATED=6.

## Decision-level descriptive table

| label | tasks | decisions | mean-order hold | max-order hold | M mean | max fails given mean+ |
|---|---:|---:|---:|---:|---:|---:|
| SPECIFIED | 7 | 7 | 85.7% | 85.7% | 0.980 | 0.0% |
| DELEGATED | 6 | 9 | 22.2% | 11.1% | -0.052 | 50.0% |
| PARTIAL | 10 | 10 | 30.0% | 10.0% | -0.399 | 66.7% |

## Per-suite descriptives

| suite | tasks | decisions | mean-order hold | max-order hold | M mean |
|---|---:|---:|---:|---:|---:|
| workspace | 8 | 8 | 62.5% | 50.0% | 0.089 |
| slack | 11 | 14 | 28.6% | 14.3% | -0.192 |
| travel | 1 | 1 | 100.0% | 100.0% | 1.601 |
| banking | 3 | 3 | 33.3% | 33.3% | 0.925 |

## Continuous prompt-coverage relationship

Across 23 confirmatory tasks, task-level specified_fraction vs M_del: Pearson=0.459, Spearman=0.472.

## Frozen sensitivity grid

| specified ≥ | delegated ≤ | Δ H_mean | 95% CI | Δ M | 95% CI |
|---:|---:|---:|---:|---:|---:|
| 0.90 | 0.10 | 0.767 | [0.389, 1.000] | 1.400 | [0.468, 2.785] |
| 0.80 **PRIMARY** | 0.20 | 0.635 | [0.167, 1.000] | 1.014 | [-0.068, 2.314] |
| 0.70 | 0.30 | 0.635 | [0.167, 1.000] | 1.014 | [-0.068, 2.314] |

## Exclusions / completeness

- `agentdojo_utility_false`: 18
- `ground_truth_privileged_call_not_executed_or_not_mappable`: 17
- `multi_tool_call_assistant_turn`: 7
- `no_eligible_tool_span`: 1
- `valid`: 26

## Interpretation guardrails

- A positive contrast supports association between the frozen prompt-coverage operationalization and attribution ordering.
- A13 does not by itself prove causality; A14 is the matched causal test.
- R is secondary/descriptive and must not define delegation.
- Mean-based attribution is diagnostic, not yet a production defense.
- Max-vs-mean discrepancies are observational in A13/A12; causal N claims require controlled A14 manipulation.

## What this experiment can establish

If the frozen SPECIFIED group has a clearly higher mean-order rate and upward-shifted M distribution than the DELEGATED group on untouched tasks, A13 provides prospective generalization evidence that task/action information provenance predicts the underlying attribution regime.

It still does **not** prove the provenance mechanism causally. That is A14's role. It also does not establish that replacing max with mean is a safe defense; that must be evaluated with malicious and benign cases in A15.

