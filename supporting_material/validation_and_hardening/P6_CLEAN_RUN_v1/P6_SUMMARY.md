# P6 — Consistency × Discrimination × Replay/Equivalence Packaging

**Status:** COMPLETE / ZERO MODEL CALLS / SYNTHESIS ONLY

## Reviewer-facing evaluation vector

1. **Authorization consistency / controlled benign:** at `tau=0`, AIVR is `20/24` (Llama) and `18/24` (Gemma). All `95/95` open nonconstant interval regimes retain AIVR>0 for each scorer; equivalently all `191/191` nondegenerate evaluated sweep rows (breakpoints + intervals + tau0) retain AIVR>0. This is benign threshold robustness, not an attack-sensitivity frontier.
2. **Benign operating point:** A15a activates on `18/26 = 69.2%` of the historical original-26 natural decisions; SPECIFIED `1/7`, DELEGATED `8/9`, PARTIAL `9/10`.
3. **Architecture boundary:** AgentWatcher flags `0/48` controlled A14 ECHO conditions and `2/26` natural benign decisions, while the paired CausalArmor-style natural operating point is `16/26`. AttriGuard produces `0/480` final blocks; `441/480` survive strict matching and `39/480` use fuzzy survival.
4. **Malicious discrimination anchors:** AgentWatcher ASR is `1/200` on `important_instructions` and `0/200` on `tool_knowledge`. Utility is `47/200` and `56/200`, respectively; **P2 no-defense baseline remains required before calling this utility loss defense overhead.**
5. **External calibration:** P0b-3 primary `BU=51.55%`, `UA=40.67%`, `ASR=3.37%` → `SAME_EXTERNAL_REGIME`. Nested629 ASR `5.09%` is secondary; serialization difference `3.53 pp` passes the frozen sensitivity gate.
6. **Replay/equivalence validity:** corrected P2b instruments are valid, but action-local preservation is `50/130`, `35/130`, `55/130` (Llama/Gemma/Qwen) while downstream utility is `85/130`, `75/130`, `95/130`. These are `78` model×decision cells with five stability repeats, not 390 independent samples.
7. **Argument-role localization:** OPEN_TEXT − REFERENCE_IDENTITY is negative in all three corrected H-SLOT arms: Llama `-0.2708` CI `[-0.6250,+0.1042]`; Gemma `-0.3667` CI `[-0.6667,-0.0333]`; Qwen `-0.3750` CI `[-0.6111,-0.1667]`.
8. **Selected-population behavior:** post-hoc P3 shows downstream-PASS/action-local-FAIL masking `20/54` among A15a-activated model×decision cells vs `3/24` controls. This is mechanism evidence, **not** a causal activation effect.

## Paper role

P6 does not add a fifth contribution and does not propose a universal scalar. It makes the existing systems story reviewer-usable:

`authorization consistency × benign operating point × malicious discrimination × replay/equivalence validity × selected-population behavior`.

The evaluation ladder is:

`interface → tool identity → typed argument equivalence → runtime/execution → deterministic effect → downstream utility → final security verdict`.

## Population lineage

The A15a, AgentWatcher-natural, and corrected P2b rows above are frozen studies of the **historical original-26 A13-valid subset**. A13-C0 later corrected the ecological census to 29 valid decisions; P6 does not retroactively relabel these completed downstream studies as corrected-29 prevalence.

## Hard claim boundaries

- Causal dependence is not authority; P6 packages evidence for that story but A14 remains the causal centerpiece.
- Do not infer that alternative thresholds preserve attack sensitivity from R2A alone.
- Do not call AttriGuard's 39 fuzzy-survival routes false positives.
- Do not call AgentWatcher attack utility loss defense overhead until P2 supplies the same-200 no-defense baseline.
- Do not turn P2b mismatch into a universal replay-defense error rate.
- Do not treat the selected-population masking contrast as confirmatory or causal.
- Do not claim P0b-3 is an exact reproduction of the published CausalArmor table.
