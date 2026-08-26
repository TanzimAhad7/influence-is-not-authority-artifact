# N4/N5 Bounded Two-Property + Architecture Synthesis

**Status:** COMPLETE / ZERO MODEL CALLS / SYNTHESIS OF CLOSED EVIDENCE  
**Rule:** no new scalar, no new inferential endpoint, no N2 authorization.

## 1. Property A — authorization/property-preserving consistency

A14 fixes authorization, the exact committed privileged action, and the security-relevant effect, while relocating legitimate execution-critical evidence USER→TOOL.

- Llama P1: -1.179732, 95% CI [-1.2836113407067742, -1.0797475485595784], 24/24 negative.
- Gemma P1: -1.011162, 95% CI [-1.1536260005123524, -0.8790134025004686], 24/24 negative.
- Token-matched Llama replacement: -1.016852, 24/24 negative.
- R2A: AIVR>0 in 191/191 nondegenerate threshold rows for each scorer; tau=0 AIVR is 20/24 (Llama) and 18/24 (Gemma).

**Bounded conclusion:** the studied CausalArmor-style causal-support observable is not authorization-invariant on this exact-action/effect-fixed orbit.

## 2. Property B — threat/action discrimination

N3 supplies the matched unauthorized-control positive comparison.

- Llama: D=+0.654540, CI=[0.44751126532221414, 0.8635706463074228]; Q=-0.370917, CI=[-0.43190491170726003, -0.31180128118723704]; T=+0.507798, CI=[0.4258953006896877, 0.5940505558485657].
- Gemma: D=+0.503912, CI=[0.1806413254050615, 0.8245824131357726]; Q=-0.474691, CI=[-0.5548191127817557, -0.406846855717889]; T=+0.537154, CI=[0.47106501177739357, 0.6127516597358199].

Q<0 and T>0 on 24/24 bases under both scorers: the proxy contains real action/threat-selective information. But D=P−N>0 with a positive CI under both scorers: the benign authorization-preserving nuisance displacement is larger on average than the supported unauthorized-control displacement.

**Bounded conclusion:** action/threat selectivity exists without clean authorization-specific raw-margin ordering.

## 3. Architecture / operating point

- A15a: CausalArmor-style sanitizer activation on historical benign privileged decisions = 18/26.
- AgentWatcher controlled A14: 0 flags in every A14 cell; natural original-26: AgentWatcher 2/26 vs CausalArmor-style 16/26.
- AttriGuard controlled A14: 480/480 final non-blocking behavior; P1=0 and AIVR=0.
- P2 same-200: AgentWatcher defense-on utility 56/200 vs defense-off 120/200; attack success 0/200 vs 32/200.
- P0b-3 source-faithful external regime: BU=51.55%, UA=40.67%, ASR=3.37%.
- P0b-3-ACT post-hoc context: ACTION_ONLY benign 20/37 vs attack 496/587 (+30.44 pp); shadow 22/37 vs 516/587 (+28.45 pp).

**Bounded conclusion:** internal support variation is not final policy. Threshold and architecture can amplify, absorb, or repair it; attack-vs-benign activation separation exists in the separately calibrated full pipeline, but the P0b-3-ACT split is descriptive only.

## 4. Breadth

B1 joint category: **CONVERGENT_DIRECTIONAL_REPLICATION**.

- GPT-4o H difference +0.388889, CI=[-0.027272727272727337, 0.7857142857142858].
- Claude Sonnet 4.5 H difference +0.215385, CI=[-0.3711057692307691, 0.7333333333333333].

Both directions are positive; both model-specific CIs include zero. This is directional ecological breadth, not two individually decisive effects.

## 5. N4/N5 synthesis lock

> **Causal support contains useful threat/action information but is not an authorization oracle. Authorization-preserving evidence relocation can move the studied proxy strongly in an attack-like direction; matched unauthorized control remains action-selective, yet raw proxy magnitude is not cleanly authorization-ordered. Operating point and architecture determine whether this mixed internal signal becomes final intervention.**

Use the evaluation view:

```text
authorization/property-preserving consistency
                    ×
              threat discrimination
                    ×
         architecture / operating point
```

Do **not** combine these into one scalar.

## 6. What N4/N5 does not establish

- not a theorem about every causal-attribution defense;
- not total proxy indiscrimination;
- not a universal authorization metric;
- not a causal effect from P0b-3-ACT;
- not an authorization to run N2.

## 7. Residual N2-NEC question

The only named unresolved N2 question is:

> On the exact frozen A14 orbit, after full source-faithful CausalArmor sanitization + retroactive reasoning masking + regeneration, does authorization-equivalent input variation change the final privileged action/effect or final defense disposition?

Existing evidence brackets this question but does not directly execute that exact full pipeline on the exact A14 orbit. N2-NEC must decide whether that residual is material enough for a reviewer to justify another prospective experiment.
