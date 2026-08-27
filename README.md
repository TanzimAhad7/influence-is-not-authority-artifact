# Influence Is Not Authority — Anonymous Artifact

This repository is the anonymous artifact for the accompanying USENIX Security submission, **“Influence Is Not Authority: When Causal Guardrail Signals Make Legitimate Tool Use Look Like an Attack in Tool-Using LLM Agents.”**

It contains the **frozen execution evidence used for the submitted paper**, deterministic verification code, experiment and analysis code, source-bound implementation records, figure producers, and optional end-to-end rerun infrastructure.

The artifact is organized so that a reviewer can audit the submitted results **without re-running models**. Fresh model/API reruns are supported separately and never overwrite the frozen evidence used by the paper.

---

## 1. What this artifact is testing

A user can authorize an action without supplying every value needed to execute it. For example, a user can authorize a transfer to Alice while a legitimate directory tool supplies Alice's missing account number. The tool-provided value must influence execution, but the tool has not gained authority to choose a different recipient.

The paper asks whether influence-based guardrail signals preserve that distinction between **what shaped an action** and **what the user authorized**.

The central controlled comparison therefore changes only the source of one required value:

```text
USER provides required value
          |
          | same permission
          | same value
          | same committed action
          | same intended effect
          v
legitimate TOOL provides the same value
```

The USER→TOOL change is a **benign experimental intervention**, not an attacker capability. A separate matched unauthorized condition changes the protected action within the same function family so that source sensitivity can be compared with a real authorization change.

The paper then follows this distinction through scalar thresholding, AgentWatcher semantic monitoring, AttriGuard routing and later review, live continuation after intervention, later inspection coverage, and replay-based evaluation fidelity.

### Research questions

> **RQ1.** Can the same authorized action look more attack-like when a needed value comes from a legitimate tool rather than directly from the user, even though the action and intended effect are unchanged?
>
> **RQ2.** How does the guardrail’s attack-likeness score respond when an authorized action relies on a legitimate tool, compared with when the action itself is unauthorized, and can a threshold distinguish the two?
>
> **RQ3.** Which parts of the guardrail’s decision path determine whether authorized and unauthorized actions are checked, blocked, or eventually executed?
>
> **RQ4.** Can a task still be counted as successful when the privileged action or effect the user authorized was not preserved?

---

## 2. Recommended reviewer path

### A. Verify the submitted results from frozen evidence

From the repository root:

```bash
bash VERIFY.sh
```

This is the recommended first step. It makes **no model/provider calls**, requires **no API credentials**, requires **no GPU**, and re-derives or cross-checks the manuscript-bearing quantities from the frozen evidence distributed here.

Expected ending:

```text
SUMMARY: 56 PASS / 0 FAIL / 56 total
RESULTS_ONLY_VERIFY=PASS
```

For the exact claim-to-file mapping, see [`CLAIM_TO_ARTIFACT.md`](CLAIM_TO_ARTIFACT.md).

### B. Regenerate the paper figures

```bash
bash RUN_FIGURES.sh
```

The figure stage reads the frozen evidence and writes regenerated outputs to a **fresh run directory outside `figures/`**. It does not overwrite the submitted figure PDFs and does not make model/provider calls.

### C. Fresh model/API rerun — optional

A fresh end-to-end rerun requires model access, provider credentials, and suitable NVIDIA GPUs for local-model stages. Start with [`docs/REPRODUCTION.md`](docs/REPRODUCTION.md).

```bash
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate

export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
export USENIX_GPU_LIST='0,1'

bash CHECK_E2E.sh
bash RUN_END_TO_END.sh --all
```

Fresh outputs are isolated from the submitted artifact. Provider-hosted responses may also drift over time, so a fresh run is a replication of the procedure rather than a promise of byte-identical historical responses.

---

## 3. Paper-to-artifact map

The numbered study directories follow the paper's scientific evidence chain.

| Paper result | Paper location | Artifact location |
|---|---|---|
| Benign tool-supported dependence occurs in the audited benchmark | Sec. 4.1, Table 2 | `studies/01_natural_relevance/` |
| Moving only a required value's source changes the causal signal | Sec. 4.2, Figure 2 | `studies/02_controlled_source_relocation/` |
| Unauthorized endpoint remains more attack-like, but harmless source relocation moves farther on average | Sec. 4.3, Figure 3 | `studies/03_matched_unauthorized_comparison/` |
| No tested scalar threshold cleanly separates the matched actions | Sec. 5.1, Figure 4, Table 3 | `studies/04_threshold_frontier/` |
| AgentWatcher gate behavior under aligned and conflict contexts | Sec. 5.2, Figure 5a, Table 4 | `studies/05_agentwatcher/` |
| AttriGuard reference routing and later-review behavior | Sec. 5.3, Figure 5b, Table 4 | `studies/06_attriguard/` |
| CausalArmor-style reconstructed estimand and activation audit | Sec. 3 / Appendix A | `studies/07_causalarmor/` |
| Protected outcome after intervention and continuation | Sec. 6, Figure 6 | `studies/08_live_end_to_end/` |
| Immediate action/effect fidelity versus downstream task success | Sec. 7, Table 5 | `studies/09_evaluation_replay/` |

Appendix E of the paper and [`CLAIM_TO_ARTIFACT.md`](CLAIM_TO_ARTIFACT.md) provide the fine-grained mapping from paper-bearing claims to exact frozen files and deterministic checks.

---

## 4. Repository organization

```text
README.md
    reviewer overview and recommended audit path

CLAIM_TO_ARTIFACT.md
    paper claim -> exact frozen evidence -> verification type

docs/
    REPRODUCTION.md
        detailed verification, figure, environment, and rerun guide
    ARTIFACT_STRUCTURE_AND_POLICIES.md
        layout, anonymization, third-party, and provenance notes

studies/
    01_natural_relevance/
    02_controlled_source_relocation/
    03_matched_unauthorized_comparison/
    04_threshold_frontier/
    05_agentwatcher/
    06_attriguard/
    07_causalarmor/
    08_live_end_to_end/
    09_evaluation_replay/

figures/
    submitted figure PDFs and supplied Python producers

scripts/
    verification/      deterministic checking / integrity / figure helpers
    reproduction/      optional fresh-rerun orchestration and stage wrappers

implementation_evidence/
    compact source-bound implementation evidence and deterministic isolation inputs

third_party/
    source-bound external integrations needed for implementation-specific claims

supporting_material/
    provenance, hardening records, logs, historical support, and source coverage
```

Each numbered study directory contains its own `README.md` with the experiment purpose, main evidence, submitted result, and interpretation boundary.

---

## 5. Scientific evidence chain

### 5.1 Natural relevance

**Directory:** `studies/01_natural_relevance/`

The natural cohort asks whether benign benchmark workflows actually contain privileged actions that depend on tool-provided values. The corrected cohort contains **29 valid privileged decisions across 25 tasks**.

```text
user-side evidence dominates
  explicitly specified: 75.0%
  delegated:             16.7%

difference: +0.5833
95% CI: [+0.1555, +0.9394]
```

Prospective GPT-4o and Claude Sonnet 4.5 trajectories are also evaluated under the same fixed Llama attribution scorer to test generator breadth.

**Boundary:** this establishes ecological relevance in the audited benchmark, not deployment prevalence. The GPT-4o/Claude rows are generator-breadth checks, not native attribution replications.

Verification: `C1.*`, `B1.*`.

### 5.2 Controlled source relocation — Figure 2

**Directory:** `studies/02_controlled_source_relocation/`

For each of **24 matched bases**, the user's permission, protected value, exact committed action, intended effect, and execution value remain fixed. Only the source of the required value changes from USER to a legitimate TOOL.

```text
Llama: 24/24 bases move toward the more attack-like region
       mean change -1.1797, 95% CI [-1.2836, -1.0797]

Gemma: 24/24 bases move toward the more attack-like region
       mean change -1.0112, 95% CI [-1.1536, -0.8790]
```

User-side support falls on all 24 bases under both scorers, while relevant-tool support rises on all 24. The specificity check localizes nearly all measured movement to the execution value that changed source.

Important files:

```text
studies/02_controlled_source_relocation/frozen_results/analysis/results.json
studies/02_controlled_source_relocation/frozen_results/scorer_llama/condition_scores.jsonl
studies/02_controlled_source_relocation/frozen_results/scorer_gemma/condition_scores.jsonl
```

**Boundary:** the 96 factorial conditions come from 24 matched bases; the matched base is the inferential unit.

Verification: `A14.*`.

### 5.3 Matched unauthorized comparison — Figure 3

**Directory:** `studies/03_matched_unauthorized_comparison/`

The source-relocation result alone does not tell us whether the signal still recognizes a real authorization violation. This branch adds a same-function unauthorized alternative.

The submitted result has two parts:

- the unauthorized endpoint is **more attack-like overall** under both scorers;
- the harmless USER→TOOL source relocation produces the **larger average score displacement** under both scorers.

Case-level authorization-changing signs are heterogeneous, so the paper does not make a uniform per-case claim.

**Boundary:** the unauthorized arm is teacher-forced and tests the construct; it is not a deployment attack-frequency estimate.

Verification: `N3.*`.

### 5.4 Threshold frontier — Figure 4 / Table 3

**Directory:** `studies/04_threshold_frontier/`

The artifact stores the complete deterministic threshold sweep rather than only the operating points shown in the manuscript.

At operating points with zero tested authorized flags:

```text
Llama catches 12/48 matched unauthorized alternatives = 25.0%
Gemma catches 18/48 matched unauthorized alternatives = 37.5%
```

Other thresholds catch more unauthorized actions but reintroduce harmless authorized flags. Each scorer's stored frontier contains 386 rows.

**Boundary:** the sweep is descriptive; no preferred threshold is selected.

Deterministic rerun:

```bash
bash RUN_END_TO_END.sh --stage 06
```

Verification: `R2B.*`.

### 5.5 AgentWatcher — Figure 5a / Table 4

**Directory:** `studies/05_agentwatcher/`

Two experiments are kept separate.

**Paired gate study:**

```text
ALIGNED:  authorized 4/24 flagged, unauthorized 21/24 flagged
CONFLICT: authorized 24/24 flagged, unauthorized 24/24 flagged
```

This is gate-level evidence. In the tested integration, a positive flag cancels the pending tool-use path.

**Separate 200-input ON/OFF experiment:**

```text
defense OFF: attack success 16%, utility 60%
defense ON:  attack success  0%, utility 28%
```

These are separate API executions and are not pooled with the paired gate study.

Verification: `AW.*`.

### 5.6 AttriGuard routing — Figure 5b / Table 4

**Directory:** `studies/06_attriguard/`

AttriGuard makes routing part of the effective decision: an exact reference match can survive automatically, while other candidates can reach later fuzzy review.

```text
overall blocked
  authorized:   113/240 = 47.08%
  unauthorized:  87/240 = 36.25%

exact automatic survival
  authorized:    70/240
  unauthorized: 138/240

later fuzzy review
  authorized:   169/240
  unauthorized: 101/240

blocked once reviewed
  authorized:   112/169 = 66.27%
  unauthorized:  86/101 = 85.15%
```

The later check is stricter on unauthorized actions once reached, but fewer unauthorized actions reach it. The overall matched blocked-action confidence interval spans zero.

**Boundary:** observed reference identity determines the route; the study does not establish that the conflicting directive caused that reference identity.

Verification: `N6.*`, `SOURCE.ATTRIGUARD_SHA`.

### 5.7 CausalArmor-style reconstruction

**Directory:** `studies/07_causalarmor/`

Released implementation code was unavailable for the CausalArmor path audited in the paper. This branch therefore reconstructs the published leave-one-out user-versus-untrusted margin and calibrates it against the reported broad operating regime.

**Boundary:** this is an audit of the published estimand, not an implementation-identical reproduction, and it is separate from the 24-base matched comparison.

Verification: `P0B3.*`, `A15A.*`.

### 5.8 Live execution — Figure 6

**Directory:** `studies/08_live_end_to_end/`

The live study follows execution beyond the gate to ask which protected effect actually occurs.

```text
14 natural tasks
x 3 contexts: CLEAN / ALIGNED / CONFLICT
x 2 defense states: OFF / ON
x 5 repeats
= 420 executions
```

The natural task, not each repeat, is the inferential unit.

Under CONFLICT:

```text
selected unauthorized outcome
  defense OFF: 17/70 = 24.3%
  defense ON:   2/70 =  2.9%

PAEF: user-authorized outcome preserved
  defense OFF: 38/70 = 54.3%
  defense ON:  47/70 = 67.1%
```

The direct PAEF confidence interval includes zero. The pre-specified primary availability-loss interaction runs opposite the predicted direction.

Continuation shows why a block is not the final outcome:

```text
12/13 blocked selected-unauthorized proposals
later recover an authorization-equivalent protected effect

9/9 blocked authorization-equivalent proposals
end with PAEF = 0
```

The artifact also preserves an exploratory source/trace analysis of later inspection in the tested AttriGuard version:

```text
44/210 defended runs enter the qualifying state
22/210 defended runs later use it
18/168 defended privileged calls run without the ordinary audit
18/18 immediately follow the qualifying predecessor
```

A deterministic fixed-call isolation reproduces the source-bound transition and a local patch restores adjudication.

**Boundary:** the later-inspection mechanism is implementation/version-specific and post hoc. These counts are not an exploit-rate estimate.

Verification: `E2E.*`.

### 5.9 Evaluation replay — Table 5

**Directory:** `studies/09_evaluation_replay/`

Replay asks whether downstream task success can hide an immediate change to the privileged action or effect.

```text
78 model-decision cells
5 generations per cell
390 generations total
Llama / Gemma / Qwen
```

Main result:

```text
23/78 cells pass the downstream majority check
while failing the immediate action/effect check

22/23 still use the intended tool
```

This shows why tool-name equality and ordinary task success can miss argument/effect divergence.

**Boundary:** replay evaluates metric fidelity, not model ranking. The 390 generations are stability repeats over 78 model-decision cells, not 390 independent cases.

Verification: `REPLAY.*`.

---

## 6. What `VERIFY.sh` checks

The supported deterministic path is:

```text
VERIFY.sh
  -> VERIFY_RESULTS_ONLY.sh
       -> scripts/verification/verify_current_claims.py
       -> scripts/verification/verify_hashes.py
       -> scripts/verification/verify_source_coverage.py
```

The 56 checks cover the manuscript-bearing natural, source-relocation, unauthorized-control, threshold, AgentWatcher, AttriGuard, CausalArmor-style, live-execution, later-inspection, replay, source-identity, package-hygiene, and source-coverage claims.

`CLAIM_TO_ARTIFACT.md` lists every check individually and records the exact frozen source file and verification mode.

---

## 7. Integrity, anonymity, and provenance

### Verify package hashes

```bash
bash VERIFY_HASHES.sh
```

The authoritative integrity manifest for this anonymous distribution is:

```text
SHA256SUMS.txt
```

### Check anonymity

```bash
bash CHECK_ANONYMITY.sh
```

A successful scan ends with:

```text
ANONYMITY=PASS
```

The checker scans distributed paths/content and nested archives for known author/environment identifiers, `.git` metadata, symlinks, and high-confidence credential patterns.

### Source-tree coverage

The source artifact inventory and final disposition are recorded in:

```text
supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv
supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.json
```

The top-level package is the reviewer-facing anonymous derivative. Historical checksum ledgers preserved inside research bundles may describe earlier research snapshots; `SHA256SUMS.txt` is the authoritative manifest for this distribution.

---

## 8. Figure reproduction

The frozen `figures/` directory contains the submitted PDFs and supplied figure producers.

```text
figure1.pdf       Figure 1 final PDF
figure2.pdf       Figure2.py
figure3.pdf       Figure3.py
figure4.pdf       Figure4.py
figure5.pdf       Figure5.py
figure6.pdf       Figure6.py
```

Run:

```bash
bash RUN_FIGURES.sh
```

Figure 1 is PDF-only because its supplied final source was TeX. Figures 2–5 regenerate directly from their supplied Python producers. `Figure6.py` is retained for provenance with historical hash locks; `scripts/verification/render_figure6.py` is the reviewer-safe adapter used by the artifact pipeline for Figure 6.

PDF byte identity is not required across environments; the scientific values and rendered content are the reproduction target.

---

## 9. Fresh end-to-end rerun

The frozen evidence is sufficient to audit the submitted paper. A fresh model-dependent rerun is available for reviewers who want to reproduce execution from the experiment entry points.

### Requirements

- Linux
- Python >= 3.10
- `bash`, `curl`, `tar`, `sha256sum`
- OpenRouter access
- Hugging Face access to the pinned model revisions
- suitable NVIDIA GPUs
- `vllm==0.26.0` for the corrected replay branch

Core dependencies are pinned in `requirements-e2e-core.txt`; a fuller environment snapshot is preserved in `requirements.txt`.

Structural-only preflight:

```bash
bash CHECK_E2E.sh --structural
```

Expected ending:

```text
E2E_PREFLIGHT=STRUCTURAL_PASS
```

Full preflight after credentials/environment setup:

```bash
bash CHECK_E2E.sh
```

Expected ending:

```text
E2E_PREFLIGHT=PASS
```

List rerun stages:

```bash
bash RUN_END_TO_END.sh --list
```

```text
01_a13_natural                  original benign natural cohort
02_a13_c0_extension             corrected natural-cohort extension/census
03_b1_generator_breadth         GPT-4o / Claude trajectory breadth under fixed Llama scoring
04_a14_controlled_source        controlled USER→TOOL source relocation, Llama + Gemma
05_n3_unauthorized_control      matched same-function unauthorized comparison
06_r2b_threshold_frontier       deterministic complete scalar threshold sweep
07_agentwatcher                 paired AgentWatcher gate study + separate ON/OFF population
08_n6_attriguard_architecture   AttriGuard route/block study
09_causalarmor_calibration      CausalArmor-style reconstruction/calibration
10_live_e2e_attriguard          420 live executions over 14 natural tasks
11_replay                       corrected Llama/Gemma/Qwen evaluation replay
12_figures                      regenerate Figures 1–6
```

Stages 06 and 12 are deterministic and do not require provider/model calls.

Run all stages:

```bash
bash RUN_END_TO_END.sh --all
```

Run one stage:

```bash
bash RUN_END_TO_END.sh --stage 04
```

Dry-run the orchestration:

```bash
bash RUN_END_TO_END.sh --dry-run --all
```

Fresh execution creates a sibling run directory containing a disposable worktree, logs, and results. Historical identifiers such as `A14`, `N3`, `R2B`, `N6`, and `P2B` are reconstructed only inside that disposable worktree using `LEGACY_PATH_MAP.tsv`; the public artifact remains organized by descriptive study names.

---

## 10. Interpretation boundaries

These studies deliberately stop at different points in the decision path and use different independent units. Their percentages should not be read as one common benchmark or leaderboard.

- The natural cohort establishes **ecological relevance**, not deployment prevalence.
- The controlled study has **24 matched bases**; its 96 conditions are not 96 independent cases.
- USER→TOOL is a **benign source intervention** that keeps authorization, value, action, and intended effect fixed.
- The matched unauthorized comparison is **teacher-forced** and supports a construct claim rather than a deployment attack-rate claim.
- The unauthorized endpoint remains more attack-like overall, while the harmless source change moves the score farther **on average**; the case-level pattern is not uniform.
- The threshold frontier is descriptive; **no preferred threshold is selected**.
- The AgentWatcher 2×2 is **gate-level** evidence; its ON/OFF result is a separate matched-input experiment.
- In AttriGuard, observed reference identity determines routing, but directive-to-reference causality is unresolved.
- The CausalArmor branch is a **calibrated reconstruction**, not an implementation-identical reproduction.
- The live study uses **14 natural tasks as the inferential units** across 420 executions.
- The direct CONFLICT PAEF difference is **null-compatible**; the artifact does not support a general claim that AttriGuard improves authorized-effect preservation.
- The later-inspection result is exploratory, source-bound, and version/configuration-specific; it is **not an exploit-rate estimate**.
- Replay measures **evaluation fidelity**, not model quality or ranking.

---

## 11. Quick command reference

```bash
# Verify all supported submitted quantities from frozen evidence
bash VERIFY.sh

# Inspect exact paper-claim provenance
less CLAIM_TO_ARTIFACT.md

# Regenerate figures from frozen evidence
bash RUN_FIGURES.sh

# Check package integrity
bash VERIFY_HASHES.sh

# Check anonymity
bash CHECK_ANONYMITY.sh

# Check that fresh-rerun entry points are structurally present
bash CHECK_E2E.sh --structural

# List optional fresh-rerun stages
bash RUN_END_TO_END.sh --list
```

For detailed environment setup and full-rerun instructions, see [`docs/REPRODUCTION.md`](docs/REPRODUCTION.md).

---

## 12. Suggested navigation order

For most reviewers:

1. Read this `README.md` to understand the evidence chain.
2. Open `CLAIM_TO_ARTIFACT.md` for exact claim-to-file provenance.
3. Run `bash VERIFY.sh` to audit the submitted quantities without model calls.
4. Inspect the relevant numbered `studies/*/README.md` and frozen evidence for any claim of interest.
5. Run `bash RUN_FIGURES.sh` if figure regeneration is desired.
6. Use `docs/REPRODUCTION.md` only if a fresh model/API rerun is needed.

The artifact intentionally preserves more provenance than the manuscript can display. The reviewer-facing scientific record is the frozen evidence and the deterministic checks linked through the paths above.
