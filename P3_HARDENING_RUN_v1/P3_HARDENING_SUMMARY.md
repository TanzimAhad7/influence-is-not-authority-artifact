# P3 — zero-model-call natural + estimand hardening

**Status:** completed post-hoc falsification/sensitivity analysis; not a new prospective endpoint.

## 1. A13 natural-result hardening

- Recomputed task-weighted H contrast: SPECIFIED `0.8571` vs DELEGATED `0.2222`; difference **+0.6349**, 95% task-bootstrap CI **[+0.1667, +1.0000]**.
- Original frozen result: difference `+0.6349`, CI `[0.16666666666666669, 1.0]`. The recomputation should match modulo deterministic bootstrap implementation details.
- Leave-one-suite-out H differences span **[+0.4444, +0.7905]**.
- Leave-one-task-out H differences span **[+0.5905, +0.7905]**.
- Eligible-span count vs task-level H: Pearson `-0.22026341569156213`, Spearman `-0.14883380393384213`.

## 2. A15a selectivity hardening

- Frozen activation: **18/26 = 69.2%**.
- See `P3_A15A_SUITE_SUMMARY.csv` and `P3_A15A_LEAVE_ONE_SUITE_OUT.csv` for suite composition/influence.

## 3. Corrected P2b: action-local vs downstream estimand separation

- Analysis unit: **78 model×decision cells across 26 decisions**; five repeats are stability repetitions, not independent mass-sample units.
- Action-local: activated **37.0%** vs controls **33.3%**; difference **+3.7 pp**, decision-cluster bootstrap CI **[-29.2, +36.1] pp**.
- Downstream: activated **74.1%** vs controls **45.8%**; difference **+28.2 pp**, clustered CI **[-4.6, +60.2] pp**.
- Downstream-PASS/action-local-FAIL masking: activated **37.0%** vs controls **12.5%**; difference **+24.5 pp**, clustered CI **[-7.9, +51.9] pp**.
- Masking gap after leaving out one suite spans **[+6.0, +61.1] pp**.
- After leaving out one function spans **[+15.6, +40.3] pp**.
- After leaving out one decision spans **[+20.8, +37.0] pp**.

## 4. Argument-role / decision-structure hardening

- OPEN_TEXT-present decisions action-local rate **14.6%** vs no-OPEN_TEXT **70.0%**; difference **-55.4 pp**, decision-cluster CI **[-80.0, -27.5] pp**.
- Cross-model action-local unanimity: **6 ALL_PASS + 14 ALL_FAIL = 20/26 unanimous**, mixed `6/26`; exploratory Fleiss κ = **0.666**.
- Original Qwen-native weak-decision recurrence is in `P3_P2B_ORIGINAL_QWEN_WEAK_RECURRENCE.csv`.

## 5. Masked-row anatomy

- Total downstream-PASS/action-local-FAIL generations: **115**.
- Candidate action structures: `{'UNIQUE_TARGET_ONLY': 110, 'MULTIPLE_TARGET_FUNCTION_CALLS': 5}`.
- Mismatch-class presence among rows with a uniquely located target call: `{'OPEN_TEXT': 105, 'REFERENCE_IDENTITY': 15, 'STRUCTURED_SCALAR': 5}`.

## 6. Conditional actual-tool validity

- llama: parsed-tool `120`, schema-valid `120/120`, execution-valid `100/120`.
- gemma: parsed-tool `110`, schema-valid `110/110`, execution-valid `90/110`.
- qwen: parsed-tool `130`, schema-valid `125/130`, execution-valid `110/130`.
- joint: parsed-tool `360`, schema-valid `355/360`, execution-valid `300/360`.

## 7. Interpretation rules

- This is an existing-data post-hoc falsification/sensitivity analysis, not a new prospective confirmatory endpoint.
- Do not infer that A15a activation causally creates replay divergence or estimand masking.
- Do not reinterpret or replace any frozen P2b gate.
- Do not treat 390 generations as 390 independent statistical units; primary P2b sensitivity uses model-by-decision cells and decision clustering.
- Do not claim a class-wide replay-defense error floor from this analysis.
- No P2b intervention is authorized by this analysis.

### Decision rule for the paper

- If A13 direction and the key P2b descriptive patterns remain sign-stable under aggressive suite/function/decision deletion, report them as robust **sensitivity/descriptive** evidence.
- If a pattern flips under one small subgroup, demote it to a limitation and do not build the paper story around it.
- Regardless of outcome, preserve the frozen A13/A15a/P2b primary results unchanged.
