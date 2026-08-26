# N6 — AttriGuard × N3 Matched Authorization-Discrimination Study

## Why this one experiment
The existing paper already shows (i) A14 authorization-preserving evidence relocation strongly moves the CausalArmor-style proxy, (ii) N3 shows real action/threat selectivity but no clean authorization-specific raw-margin ordering, and (iii) source-locked AttriGuard is perfectly permissive on the benign A14 orbit. The missing high-value cell is whether the same evidence-preserving causal architecture **separates an authorized call from a matched unauthorized same-function call under the exact same maliciously conflicting context**.

This study is intentionally a controlled **gate-level** test. It does not claim that the original agent would naturally propose both candidates and does not estimate end-to-end ASR/utility.

## Paired design
- 24 already-frozen N3 bases.
- Use only the 48 already-frozen CONFLICT contexts (SHAM/ECHO).
- For each context, place **both** already-audited candidate calls in the intercepted proposal set:
  - AUTH: oracle ALLOW.
  - ALT: oracle DENY solely at the protected execution argument.
- Official AttriGuard then produces one attenuated observation and one shadow action set and gates both calls against that same reference.
- Five repeats per context = 240 paired invocations / 480 candidate verdicts.
- Candidate processing order is pre-balanced 120/120 and the full run schedule is frozen before outcomes.

## Primary estimand
For each paired run, `Z = block(ALT) - block(AUTH)`.
For each base, average Z over SHAM/ECHO and five repeats each to obtain `G_b`.
Report mean/median/sign counts and a paired whole-base bootstrap 95% CI over 24 bases.

Absolute AUTH and ALT block rates are mandatory operating-point context. A positive gap with both candidates mostly blocked or mostly allowed is not called a practical repair.

## Secondary mechanism decomposition
Using raw official AttriGuard traces only:
- exact shadow survival;
- fuzzy-judge path;
- no-same-function hard fail;
- final block;
- frozen judge reason text retained for audit, with only predeclared route categories used quantitatively.

## Source fidelity
Freeze the authors' released source artifact exactly. λ=2, fuzzy survival, official scheduling directive, released code decoding semantics (main/shadow temperature 0; attenuation/judge temperature 0.2, top-p 0.9), and the source implementation's fuzzy-judge logprob behavior are retained.

The adapter may add provider-valid historical resolver envelopes and the controlled paired AUTH/ALT candidate set, but the official AttriGuard core remains byte-identical.

## Outcome-complete interpretation
Every valid result is retained. Positive separation can support architecture-level authorization-sensitive gating only at this controlled gate layer. Ties/constant-allow/constant-block/adverse ordering are all reportable scientific outcomes. No result is used to tune λ, judge prompts, contexts, candidate mapping, or exclusions.
