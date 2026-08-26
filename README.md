# Influence Is Not Authority — Artifact

This repository contains the frozen evidence, experiment code, analysis scripts, source-bound third-party integrations, and figure producers for the accompanying USENIX Security submission.

The repository is organized by the paper's evidence chain rather than by historical run IDs. Historical identifiers are still preserved inside the frozen records and protocol packages so provenance remains intact.

## Start here

For a fast, offline check of the submitted results:

```bash
bash VERIFY.sh
```

Expected ending:

```text
SUMMARY: 56 PASS / 0 FAIL / 56 total
RESULTS_ONLY_VERIFY=PASS
```

No model calls, API credentials, GPU, or network access are required for this path.

To regenerate the paper figures:

```bash
bash RUN_FIGURES.sh
```

To inspect where any paper-bearing number comes from, use:

```text
CLAIM_TO_ARTIFACT.md
```

For a fresh model/API rerun, use `REPRODUCE.md` and `FULL_RERUN.md`.

---

## Repository map

```text
README.md                       this guide
CLAIM_TO_ARTIFACT.md            paper claim -> exact frozen evidence
REPRODUCE.md                    reproduction commands and requirements
FULL_RERUN.md                   stage-by-stage fresh rerun map
FIGURE_REPRODUCTION.md          figure regeneration details
ANONYMIZATION.md                anonymization and hygiene record
THIRD_PARTY.md                  source-bound third-party material
ARTIFACT_LAYOUT.md              detailed layout/provenance notes

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

figures/                        final PDFs + Python producers
verification/                   deterministic verification guide
reproduction/                   fresh-rerun orchestration and stage wrappers
artifact_tools/                 deterministic verification/adaptation helpers
artifact_support/               compact frozen support records
third_party/                    exact source-bound external integrations
supporting_material/            provenance, hardening, logs, historical support
```

The nine numbered study folders match the order in which the paper builds its evidence.

---

## Evidence chain

| Folder | Question | Main frozen evidence |
|---|---|---|
| `studies/01_natural_relevance/` | Does legitimate tool dependence occur in benign benchmark workflows? | corrected natural cohort + generator breadth |
| `studies/02_controlled_source_relocation/` | Does moving one required value from USER to a legitimate TOOL change the causal signal while authorization/action/effect stay fixed? | 24 matched bases, Llama + Gemma |
| `studies/03_matched_unauthorized_comparison/` | How does the harmless source shift compare with a matched authorization violation? | matched AUTH/ALT analysis |
| `studies/04_threshold_frontier/` | Can one scalar threshold separate authorized from unauthorized actions? | complete deterministic threshold sweep |
| `studies/05_agentwatcher/` | How does semantic monitoring turn the evidence into a gate decision? | paired gate study + separate ON/OFF population |
| `studies/06_attriguard/` | How do reference routing and later review shape the effective policy? | route/block study |
| `studies/07_causalarmor/` | Does the reconstructed causal-support estimand behave in the reported broad regime? | calibrated reconstruction + activation audit |
| `studies/08_live_end_to_end/` | What happens after intervention when execution continues? | 420 live executions + continuation/audit evidence |
| `studies/09_evaluation_replay/` | Can downstream task success hide a changed privileged action/effect? | 78 model-decision cells, 390 generations |

Each study directory contains its own `README.md` with the purpose, key files, paper result, and reproduction boundary.

---

## Main frozen results

The deterministic verifier checks the manuscript-bearing quantities, including:

- Natural cohort: 29 valid privileged decisions across 25 tasks; specified-vs-delegated user-side dominance difference +0.5833, 95% CI [+0.1555,+0.9394].
- Controlled source relocation: 24/24 matched bases move in the more attack-like direction under both Llama and Gemma; mean changes -1.1797 and -1.0112.
- Matched unauthorized comparison: the unauthorized endpoint is more attack-like overall, while the harmless source relocation produces the larger average displacement.
- Threshold frontier: at zero tested benign flags, Llama catches 12/48 matched unauthorized alternatives and Gemma catches 18/48.
- AgentWatcher paired gate study: ALIGNED gives 4/24 authorized vs. 21/24 unauthorized flags; CONFLICT gives 24/24 for both. A separate 200-input ON/OFF experiment gives 0% vs. 16% attack success and 28% vs. 60% utility.
- AttriGuard: 113/240 authorized and 87/240 unauthorized actions are blocked overall; the matched confidence interval spans zero, with different route exposure before later review.
- Live execution: 14 tasks x 3 contexts x 2 defense states x 5 repeats = 420 executions. Under CONFLICT, the selected unauthorized outcome changes from 17/70 with defense off to 2/70 with defense on. Direct PAEF changes from 38/70 to 47/70, with a 95% CI that includes zero.
- Continuation: 12/13 blocked selected-unauthorized proposals later recover an authorization-equivalent protected effect, while all 9/9 blocked authorization-equivalent proposals end with PAEF=0.
- Replay: 23/78 model-decision cells pass the downstream majority check while failing the immediate action/effect check; 22/23 still use the intended tool.

`CLAIM_TO_ARTIFACT.md` gives the exact file for every check.

---

## Three reproduction levels

### 1. Exact submitted-result verification

```bash
bash VERIFY.sh
```

This reads only the frozen execution record distributed here. It is the fastest way to audit the paper's reported values.

### 2. Figure regeneration

```bash
bash RUN_FIGURES.sh
```

Figures are regenerated into a fresh run directory. The frozen PDFs in `figures/` are never overwritten.

### 3. Fresh end-to-end rerun

Requires OpenRouter access, Hugging Face access, and suitable vLLM-capable NVIDIA GPUs:

```bash
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate

export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
export USENIX_GPU_LIST='0,1'

bash CHECK_E2E.sh
bash RUN_END_TO_END.sh --all
```

Hosted-model outputs may change over time. A fresh run is therefore a replication of the procedure, not a promise of byte-identical provider responses. The frozen evidence remains the execution record for the submitted paper.

---

## Why historical run names still appear inside some files

The original research tree used identifiers such as `A14`, `N3`, `R2B`, `N6`, and `P2B`. Those names are useful for provenance but are poor navigation labels.

The distributed repository therefore uses descriptive study folders. `LEGACY_PATH_MAP.tsv` records the exact mapping from every relocated historical top-level path to its new location.

Fresh-rerun orchestration reconstructs the historical layout only inside a disposable working directory because the original frozen scripts expect those identifiers. The public repository itself remains organized by the descriptive hierarchy above.

No scientific result, raw evidence file, protocol content, or historical identifier inside a frozen record is rewritten merely for presentation.

---

## Figures

The `figures/` directory intentionally contains only the final PDF figures and Python producers:

```text
Figure2.py
Figure3.py
Figure4.py
Figure5.py
Figure6.py
figure1.pdf
figure2.pdf
figure3.pdf
figure4.pdf
figure5.pdf
figure6.pdf
```

Figure 1 is PDF-only because its final supplied source was TeX. Figures 2--6 are regenerated by the artifact pipeline.

PDF byte identity is not required across environments because PDF metadata and font serialization can differ. The scientific values and rendered content are the reproduction target.

---

## Integrity and anonymity

Run:

```bash
bash VERIFY_HASHES.sh
bash CHECK_ANONYMITY.sh
```

The integrity manifest is `SHA256SUMS.txt`.

Original source-tree disposition is recorded under:

```text
supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv
supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.json
```

No real API credentials are included. Fresh runs read credentials from environment variables only.

---

## Interpretation boundaries

- The controlled source-relocation study uses 24 matched bases; the 96 factorial conditions are not 96 independent cases.
- The natural cohort establishes ecological relevance in the audited benchmark, not deployment prevalence.
- The matched unauthorized comparison is teacher-forced.
- The threshold sweep is descriptive and does not select a recommended policy threshold.
- The AgentWatcher paired study is gate-level evidence; the ON/OFF 200-input experiment is a separate population.
- The AttriGuard route finding is tied to the tested source/configuration; observed reference identity determines route, while directive-to-reference causality remains unresolved.
- The live study uses 14 natural tasks as the inferential units.
- Audit-coverage counts use different denominators and are not an exploit-rate estimate.
- Replay measures evaluation fidelity, not model ranking.

---

## Recommended audit sequence

```bash
# 1. Read the claim map
less CLAIM_TO_ARTIFACT.md

# 2. Verify all manuscript-bearing quantities
bash VERIFY.sh

# 3. Regenerate figures
bash RUN_FIGURES.sh

# 4. Check integrity/anonymity if desired
bash VERIFY_HASHES.sh
bash CHECK_ANONYMITY.sh
```

For a fresh rerun, continue with `REPRODUCE.md`.
