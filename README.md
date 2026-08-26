# USENIX Security Artifact: Complete Reproduction Guide

This artifact contains the code, frozen inputs and outputs, experiment protocols, model-serving scripts, analysis code, and paper-figure producers used for the accompanying USENIX Security submission.

This README explains **what the artifact reproduces, how the pieces fit together, how to run every experiment, what each stage produces, and how to interpret the outputs**. A reader should not need to reconstruct the project history or guess which scripts matter.

The artifact supports two different but complementary forms of reproduction:

1. **Exact reproduction of the paper's reported numbers from the frozen execution record.** This is deterministic, requires no new model calls, and is the fastest way to audit the submitted results.
2. **A fresh end-to-end rerun of the experiments.** This reruns the model/API procedures using OpenRouter, pinned Hugging Face models, and vLLM-capable NVIDIA GPUs. Because hosted model services can change over time, a fresh rerun tests the procedure but is not expected to reproduce every hosted response byte-for-byte.

The frozen evidence shipped here remains the execution record for the numbers in the paper. Fresh reruns are written to a separate directory and never overwrite it.

---

## 1. What this paper tests

The paper studies a specific security problem in tool-using LLM agents: **a legitimate tool can provide information that an authorized action needs, but causal or influence-based security evidence may react to that tool dependence even when the user's authorization, the action, and the intended effect do not change.**

The experiments follow that problem through the complete decision path:

1. **Natural relevance.** Do benign benchmark tasks actually contain privileged actions that need legitimate tool-provided information?
2. **Controlled source relocation.** If the same required value is moved from the user request to a legitimate tool result while authorization and action stay fixed, does the causal-support signal change?
3. **Matched unauthorized control.** Does the signal still respond to a real authorization violation, and how does that response compare with the harmless source relocation?
4. **Thresholding.** Can a single scalar threshold recover the authorized/unauthorized distinction?
5. **Architecture behavior.** What happens when that imperfect evidence is turned into decisions by AgentWatcher or AttriGuard?
6. **Live execution.** What happens after a guardrail intervenes? Does the final protected effect match what the user authorized?
7. **Evaluation fidelity.** Can ordinary task success hide a change in the privileged action or effect?

The artifact mirrors this evidence chain. It is not intended to be read as a chronological archive of every exploratory experiment performed during the project.

### Main paper-bearing results reproduced by the artifact

The deterministic verification path checks the manuscript-bearing quantities, including:

- **Natural cohort:** 29 valid privileged decisions across 25 tasks; user-side dominance is 0.7500 for explicitly specified values and 0.1667 for delegated values, difference +0.5833 with 95% CI [+0.1555,+0.9394].
- **Controlled source relocation (A14):** all 24/24 matched bases move in the more attack-like direction under both Llama and Gemma scorers; mean changes are -1.1797 and -1.0112.
- **Matched unauthorized comparison (N3):** the unauthorized endpoint is more attack-like overall, while the harmless source relocation produces the larger average displacement; the case-level authorization-changing pattern remains heterogeneous.
- **Threshold frontier (R2B):** with no tested authorized case flagged, Llama catches 12/48 matched unauthorized alternatives and Gemma catches 18/48; the complete tested scalar frontier is retained and no preferred threshold is selected.
- **AgentWatcher:** in the paired gate study, ALIGNED context produces 4/24 authorized versus 21/24 unauthorized flags, while the tested CONFLICT context produces 24/24 flags for both. A separate 200-input evaluation has 16% attack success and 60% utility without the defense versus 0% and 28% with it.
- **AttriGuard architecture (N6):** 113/240 authorized actions and 87/240 unauthorized actions are blocked overall; the matched confidence interval spans zero. Route exposure differs before the later check.
- **Live execution:** 14 natural tasks x 3 contexts x 2 defense states x 5 repeats = 420 executions. Under CONFLICT, the selected unauthorized outcome changes from 17/70 with defense off to 2/70 with defense on. Direct PAEF changes from 38/70 to 47/70, but its 95% CI includes zero. After blocking, 12/13 selected-unauthorized proposals later recover an authorization-equivalent protected effect, while all 9/9 blocked authorization-equivalent proposals end with PAEF=0.
- **Audit coverage:** 44/210 defended runs open the qualifying state, 22/210 later execute a tool batch while it is active, 18/168 defended privileged calls execute without the ordinary audit, and all 18/18 immediately follow the qualifying predecessor. These are different denominators and are checked separately.
- **Replay:** across 78 model-decision pairs and 390 generations, 23/78 pairs pass the downstream majority check while failing the immediate action/effect check; 22/23 still use the intended tool.

Run `bash VERIFY.sh` to recompute these checks from the frozen evidence.

---

## 2. Choose the reproduction path

### Path A: audit the exact submitted results

Use this first if the goal is to verify the paper's numbers without spending model/API resources.

```bash
bash VERIFY.sh
```

This path uses the frozen execution record distributed in the artifact. It performs no new provider calls and does not require a GPU.

Expected scientific result:

```text
56 PASS
0 FAIL
```

A failure means either the artifact has changed, a required evidence file is missing, or a reported quantity no longer re-derives from the distributed evidence. It should not be ignored.

### Path B: regenerate the paper figures

```bash
bash RUN_FIGURES.sh
```

This creates a new timestamped run directory outside the frozen artifact and writes regenerated figures under:

```text
<run-root>/results/12_figures/
```

The frozen PDFs in `figures/` remain unchanged.

### Path C: rerun the full experimental program

Use this when OpenRouter credentials, Hugging Face access, and suitable NVIDIA GPUs are available.

```bash
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate

export OPENROUTER_API_KEY='YOUR_OPENROUTER_KEY'
export HF_TOKEN='YOUR_HUGGINGFACE_TOKEN'
export USENIX_GPU_LIST='0,1'

bash CHECK_E2E.sh
bash RUN_END_TO_END.sh --all
```

A complete run executes every stage listed in Section 8. New outputs are captured under a fresh run directory. The distributed frozen evidence is never overwritten.

---

## 3. Artifact layout

The top-level files are the supported entry points:

```text
README.md                         this guide
SETUP_E2E.sh                     create the full rerun environment
CHECK_E2E.sh                     verify dependencies, keys, model access, and GPUs
RUN_END_TO_END.sh                run all experiments or selected stages
VERIFY.sh                        recompute the exact submitted results from frozen evidence
RUN_FIGURES.sh                   regenerate paper figures
CHECK_ANONYMITY.sh               deep anonymity/hygiene scan
VERIFY_HASHES.sh                 verify distributed files against SHA256SUMS.txt
SELF_TEST.sh                     local structural/deterministic artifact test
requirements-e2e-core.txt        pinned Python dependencies for full rerun
SHA256SUMS.txt                   integrity manifest
SOURCE_ARTIFACT_COVERAGE.tsv     disposition of the original artifacts/ files
CLAIM_TO_ARTIFACT.md             claim-to-evidence map
```

Important directories:

```text
reproduction/                    orchestration and per-stage shell scripts
artifact_tools/                  deterministic verification/adaptation utilities
artifact_support/                compact support records used by verification
figures/                         final paper PDFs and Python producers only
A13*, a13*/                      natural-cohort experiments and frozen records
a14_minimal_factorial/           controlled source-relocation evidence
N3*/                             matched unauthorized comparison
R2B*/                            deterministic threshold frontier
AW_N3*, P2_AGENTWATCHER*/        AgentWatcher studies
N6*, n6_attriguard*/             AttriGuard architecture experiment
P0B3*/                           CausalArmor reconstruction/calibration
E2E_ATTR_AUTH*/                  live protected-effect experiment
P2B_XM_CI*/                      corrected replay experiments
external/                        source-bound third-party integrations required by experiments
```

The package preserves the complete scientific/reproduction content of the project's `artifacts/` tree except identity-bearing Git metadata. The exact disposition of every original file is recorded in `SOURCE_ARTIFACT_COVERAGE.tsv`.

---

## 4. What is frozen and what a fresh rerun changes

This distinction is important.

### Frozen execution record

The distributed raw/model outputs, protocol freezes, analysis outputs, and final figure PDFs correspond to the submitted paper. `VERIFY.sh` uses these files to reproduce the exact manuscript numbers.

### Fresh rerun

`RUN_END_TO_END.sh` executes the experiment procedures again. Local Hugging Face models are requested at the pinned revisions used by the protocols. Hosted models are called through OpenRouter using the configured model names.

A fresh hosted-model response may differ from the historical response because the provider is external. That does **not** modify the frozen record. It produces a replication run under a new run directory.

### Why stages are kept scientifically separate

Several studies use independently frozen populations or protocols. The master runner therefore executes each study according to its own frozen inputs rather than silently feeding a newly generated stochastic population from one study into a different study whose population was separately fixed. This preserves the experimental design.

The run directory nevertheless captures every newly produced branch so it can be inspected and compared with the frozen record.

---

## 5. Requirements for a full rerun

### Operating system

Linux is expected. The shell scripts use standard Linux tooling.

Required command-line tools:

```text
bash
python3
curl
tar
sha256sum
```

For local model execution:

```text
nvidia-smi
vllm
```

### Python

The supported full-rerun environment requires:

```text
Python >= 3.10
```

`SETUP_E2E.sh` creates `.venv-e2e/` and installs the packages in `requirements-e2e-core.txt`.

Important pinned dependencies include:

```text
agentdojo==0.1.35
openai==2.49.0
huggingface-hub==1.25.1
transformers==5.14.1
numpy==2.3.5
PyYAML==6.0.3
requests==2.34.2
jsonschema==4.26.0
vllm==0.26.0
```

The corrected replay branch requires `vllm==0.26.0`; `CHECK_E2E.sh` verifies this exact version.

### GPUs

The default configuration expects at least two visible NVIDIA GPU indices:

```bash
export USENIX_GPU_LIST='0,1'
```

The 70B/72B local-model stages use tensor parallelism across two GPUs. The actual GPU model is not hard-coded; the selected GPUs must have enough aggregate memory for the model and serving parameters.

The artifact does not claim that a specific consumer GPU configuration is sufficient. If a model does not fit, use larger vLLM-capable GPUs while preserving the model revision and serving parameters encoded by the stage.

### Disk space

The distributed artifact is several hundred MB uncompressed. A full run creates a complete disposable working copy and new raw outputs, model logs, and analysis outputs. Keep substantially more free space than the artifact size itself.

---

## 6. Credentials and model access

Set the two credentials in the shell environment:

```bash
export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
```

`HUGGING_FACE_HUB_TOKEN` may be used instead of `HF_TOKEN`.

Do **not** write real credentials into `.env` files inside this repository.

Hosted model paths used by the frozen protocols include:

```text
openai/gpt-4o
anthropic/claude-sonnet-4.5
openai/gpt-4.1-mini
google/gemini-2.5-flash
```

Local Hugging Face/vLLM model repositories include pinned revisions of:

```text
Qwen/Qwen2.5-72B-Instruct
meta-llama/Llama-3.3-70B-Instruct
google/gemma-3-12b-it
Qwen/Qwen3-4B-Instruct-2507
SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507
```

The preflight checks access to the exact revisions required by the orchestrated stages.

---

## 7. Install and validate the environment

### Step 1: create the environment

From the artifact root:

```bash
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate
```

The setup script:

1. checks Python >= 3.10;
2. creates `.venv-e2e/` using system GPU packages when available;
3. installs `requirements-e2e-core.txt`;
4. installs `vllm==0.26.0` when `--install-vllm` is supplied.

Installing vLLM may install or replace CUDA/PyTorch packages inside the virtual environment. On managed GPU systems, it is reasonable to create the equivalent pinned environment manually and then run the preflight.

### Step 2: export credentials and GPU selection

```bash
export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
export USENIX_GPU_LIST='0,1'
```

### Step 3: run the full preflight

```bash
bash CHECK_E2E.sh
```

The preflight checks:

- Python version;
- required Python imports;
- `agentdojo==0.1.35`;
- `vllm==0.26.0`;
- `OPENROUTER_API_KEY` presence and OpenRouter network/API access;
- Hugging Face token presence and access to the pinned model revisions;
- NVIDIA GPU visibility;
- validity of `USENIX_GPU_LIST`;
- presence of all experiment entry points required by the master runner.

Expected final line:

```text
E2E_PREFLIGHT=PASS
```

If this fails, do not start the expensive model run. Fix the reported dependency, access, or hardware issue first.

### Structural preflight without keys or GPUs

To check only that the package contains the required entry points:

```bash
bash CHECK_E2E.sh --structural
```

Expected:

```text
E2E_PREFLIGHT=STRUCTURAL_PASS
```

---

## 8. End-to-end stages

List the stages at any time with:

```bash
bash RUN_END_TO_END.sh --list
```

The complete run is:

```bash
bash RUN_END_TO_END.sh --all
```

Each stage writes a log to:

```text
<run-root>/results/logs/
```

and a successful stage creates:

```text
<run-root>/results/<stage>.DONE
```

### Stage 01: natural benign cohort

**Command**

```bash
bash RUN_END_TO_END.sh --stage 01
```

**Purpose**  
Re-execute the original benign natural-cohort procedure using Qwen2.5-72B through local vLLM.

**Primary code**

```text
A13.py
```

**Main reproduced material**

```text
<run-root>/results/01_a13_natural/a13/
```

**What it means**  
This branch establishes the natural benchmark context for the controlled experiment. It supports ecological relevance, not deployment prevalence.

### Stage 02: A13-C0 extension and census

**Command**

```bash
bash RUN_END_TO_END.sh --stage 02
```

**Purpose**  
Re-run the C0 extension under its frozen input bundles and combine it with the historical A13 population needed for the corrected natural census.

**Inputs/provenance**

```text
A13_C0_INPUT_BUNDLE_v1.zip
A13_C0_HISTORICAL_A13_COMPLETE_v1.zip
A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz
A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz
```

The orchestration creates an anonymous-path-compatible copy of the frozen runner; it does not change the scientific protocol.

**Main reproduced material**

```text
<run-root>/results/02_a13_c0_extension/
```

**What it means**  
This branch produces the corrected natural-population inputs used by the natural relevance result.

### Stage 03: GPT-4o / Claude trajectory-generator breadth

**Command**

```bash
bash RUN_END_TO_END.sh --stage 03
```

**Purpose**  
Generate prospective trajectories with GPT-4o and Claude and score both sets with the same fixed Llama attribution scorer.

**External/local dependencies**

- OpenRouter for the trajectory generators.
- local pinned Llama-3.3-70B scorer through vLLM.

**Main reproduced material**

```text
<run-root>/results/03_b1_generator_breadth/b1_a12_backbone_replication_c0_v2/
```

**What it means**  
This tests breadth across trajectory generators. It is not a GPT-4o-native or Claude-native attribution replication.

### Stage 04: controlled source relocation (A14)

**Command**

```bash
bash RUN_END_TO_END.sh --stage 04
```

**Purpose**  
Re-score the 24 matched bases under Llama and Gemma while holding authorization, protected value, exact action, and intended effect fixed and changing only where the required value is supplied.

**Models**

```text
meta-llama/Llama-3.3-70B-Instruct
google/gemma-3-12b-it
```

at the revisions checked by `CHECK_E2E.sh` and requested by the stage launcher.

**Main reproduced material**

```text
<run-root>/results/04_a14_controlled_source/a14_minimal_factorial/
```

**Frozen-paper expectation**  
The submitted execution record has 24/24 attack-like movement for both scorers, with mean source-relocation changes of -1.1797 for Llama and -1.0112 for Gemma.

**What it means**  
The causal-support signal follows where execution-critical evidence resides even when authorization and the action remain unchanged.

### Stage 05: matched unauthorized control (N3)

**Command**

```bash
bash RUN_END_TO_END.sh --stage 05
```

**Purpose**  
Re-score the same-function unauthorized comparison under the pinned Llama and Gemma scorers and run the frozen N3 analysis.

**Main reproduced material**

```text
<run-root>/results/05_n3_unauthorized_control/N3_PREFREEZE_AUTHOR_v1_1/
```

**Frozen-paper expectation**  
The unauthorized endpoint is more attack-like overall under both scorers, but the harmless source relocation has the larger mean displacement. Case-level authorization-changing signs are heterogeneous.

**What it means**  
The observable contains real threat information, but its response magnitude is not itself an authorization label.

### Stage 06: complete scalar threshold frontier (R2B)

**Command**

```bash
bash RUN_END_TO_END.sh --stage 06
```

**Purpose**  
Run the deterministic threshold analysis over the frozen A14/N3 score evidence.

**Model calls**  
None.

**Main reproduced material**

```text
<run-root>/results/06_r2b_threshold_frontier/R2B_JTF_AUTHOR_v1/
```

**Frozen-paper expectation**

- Llama zero-benign operating point catches 12/48 unauthorized alternatives.
- Gemma zero-benign operating point catches 18/48.
- The complete sweep has 386 rows per scorer.
- No threshold is selected as a recommended operating point.

**What it means**  
Thresholding recovers some separation but does not provide a clean scalar authorization separator over the tested frontier.

### Stage 07: AgentWatcher

**Command**

```bash
bash RUN_END_TO_END.sh --stage 07
```

**Purpose**  
Reproduce both AgentWatcher evidence classes kept in the paper:

1. the paired AUTH/ALT gate study under ALIGNED and CONFLICT context;
2. the separate 200-input defense-ON/OFF operational anchor.

**Local models**  
The stage retrieves the pinned Qwen3 base, AgentWatcher LoRA adapter, and attribution model, then runs the monitor through vLLM.

**Hosted path**  
The separate operational evaluation uses the hosted agent path through OpenRouter.

**Main reproduced material**

```text
<run-root>/results/07_agentwatcher/
```

**Frozen-paper expectation**

```text
ALIGNED:  authorized 4/24 flagged, unauthorized 21/24 flagged
CONFLICT: authorized 24/24 flagged, unauthorized 24/24 flagged
```

Separate 200-input anchor:

```text
defense OFF: 16% attack success, 60% utility
defense ON:   0% attack success, 28% utility
```

**What it means**  
Semantic monitoring separates the actions in the aligned context but saturates in the tested conflict context. The 200-input ON/OFF result is a separate population and should not be merged with the paired gate study.

### Stage 08: AttriGuard architecture / reference routing (N6)

**Command**

```bash
bash RUN_END_TO_END.sh --stage 08
```

**Purpose**  
Run the frozen AttriGuard N6 experiment and analyze the aggregate block endpoint before the reference-route localization.

**Main reproduced material**

```text
<run-root>/results/08_n6_attriguard_architecture/n6_attriguard_n3_v1/scientific_v1/
```

**Frozen-paper expectation**

```text
authorized blocked:   113/240
unauthorized blocked:  87/240
```

with a matched confidence interval spanning zero. The route analysis then records automatic exact-reference survival versus later fuzzy review.

**What it means**  
A stricter later check does not determine the aggregate policy if the two action classes reach that check at different rates.

### Stage 09: CausalArmor-style reconstruction/calibration

**Command**

```bash
bash RUN_END_TO_END.sh --stage 09
```

**Purpose**  
Execute the calibrated reconstruction path used to audit the published causal-support estimand and its operational activation behavior.

**Dependencies**

- local pinned Gemma scorer;
- hosted Gemini agent/sanitizer path used by the frozen protocol.

**Main reproduced material**

```text
<run-root>/results/09_causalarmor_calibration/P0B3_CAUSALARMOR_LIVE_RUN_v1/
```

**What it means**  
This is a reconstruction/calibration of the published estimand, not a claim of implementation-identical reproduction of unreleased code.

### Stage 10: live AttriGuard protected-effect study

**Command**

```bash
bash RUN_END_TO_END.sh --stage 10
```

**Purpose**  
Re-run the final live study over 14 prospectively selected natural tasks under CLEAN, ALIGNED, and CONFLICT context with defense OFF and ON and five repeats per cell.

**Scale**

```text
14 tasks x 3 contexts x 2 defense states x 5 repeats = 420 executions
```

**Hosted model path**

```text
openai/gpt-4.1-mini
```

through the frozen OpenRouter configuration.

**Main reproduced material**

```text
<run-root>/results/10_live_e2e_attriguard/E2E_ATTR_AUTH_v1/scientific_v1/
```

**Frozen-paper expectation**

```text
selected unauthorized outcome under CONFLICT:
  OFF 17/70 (24.3%)
  ON   2/70 (2.9%)

direct PAEF under CONFLICT:
  OFF 38/70 (54.3%)
  ON  47/70 (67.1%)
  95% CI for the direct difference includes zero

continuation diagnostics:
  blocked selected unauthorized proposals -> 12/13 later AUTH-equivalent PAEF success
  blocked AUTH-equivalent proposals        -> 9/9 PAEF loss
```

**What it means**  
A guardrail block is a state transition, not the final security outcome. The execution path after intervention determines whether the user-authorized effect survives.

The same branch contains the exploratory, source-bound audit-coverage analysis. The 44/210, 22/210, 18/168, and 18/18 quantities use different denominators and must not be collapsed into one rate.

### Stage 11: corrected three-model replay

**Command**

```bash
bash RUN_END_TO_END.sh --stage 11
```

**Purpose**  
Run the corrected replay protocol for Llama, Gemma, and Qwen, then compare immediate privileged action/effect fidelity with downstream task success.

**Local models**

```text
Llama
Gemma
Qwen
```

served according to the frozen replay registry and `vllm==0.26.0` environment.

**Main reproduced material**

```text
<run-root>/results/11_replay/
```

**Frozen-paper expectation**

```text
78 model-decision pairs
5 repeats per pair
390 generations total
23/78 downstream-majority-pass cells fail the immediate action/effect check
22/23 still use the intended tool
```

**What it means**  
Tool-name equality and downstream task success can both hide an argument/effect change at the privileged decision.

### Stage 12: paper figures

**Command**

```bash
bash RUN_END_TO_END.sh --stage 12
```

or:

```bash
bash RUN_FIGURES.sh
```

**Purpose**  
Regenerate the paper figures from the distributed evidence without modifying the frozen PDFs.

**Output**

```text
<run-root>/results/12_figures/
```

The output includes Figures 1--6 plus a regeneration report.

**Interpretation**  
Figure 1 is copied from the frozen final PDF because the supplied final source was TeX and the distribution rule for `figures/` keeps only Python and PDF files. Figures 2--6 are regenerated from the distributed scientific evidence. PDF byte identity is not required because PDF metadata/font serialization can differ across environments; the frozen PDFs remain the submission record.

---

## 9. Running selected stages

The complete stage names are:

```bash
bash RUN_END_TO_END.sh --list
```

A stage may be selected by number or name:

```bash
bash RUN_END_TO_END.sh --stage 04
bash RUN_END_TO_END.sh --stage 04_a14_controlled_source
bash RUN_END_TO_END.sh --stage 10
```

Multiple stages may be requested:

```bash
bash RUN_END_TO_END.sh --stage 04 --stage 05 --stage 06
```

The runner creates one disposable worktree for that invocation and captures the output of each selected stage under the same run root.

---

## 10. Where a run writes its outputs

By default the master runner creates a sibling directory such as:

```text
USENIX27_RERUN_YYYYMMDDTHHMMSSZ/
```

To choose a location:

```bash
export USENIX_RUN_ROOT='/path/to/my-rerun'
```

The run directory contains:

```text
RUN_METADATA.txt              start/completion metadata and selected GPU list
worktree/                     disposable execution copy of the artifact
results/                      reproduced stage outputs
results/logs/                 stdout/stderr captured per stage
servers/                      vLLM logs, PID files, and model probes
```

A successful stage creates:

```text
results/<stage>.DONE
```

A complete successful invocation ends with:

```text
END_TO_END_RERUN=PASS
```

If a stage fails, the runner stops, prints the failing stage, returns a non-zero status, and leaves the partial run directory intact for diagnosis.

---

## 11. Exact-result verification

Run:

```bash
bash VERIFY.sh
```

This is the authoritative fast audit of the paper's frozen numerical record. It checks the natural result, A14, N3, R2B, AgentWatcher, N6, CausalArmor calibration, live study, continuation, audit-coverage mechanism evidence, replay, source identity, and artifact coverage.

Expected ending:

```text
SUMMARY: 56 PASS / 0 FAIL / 56 total
RESULTS_ONLY_VERIFY=PASS
```

If a fresh model rerun differs but `VERIFY.sh` still passes, that means the distributed historical record remains internally reproducible while a current external/model execution produced a different replication output. Preserve both; do not overwrite the frozen record.

---

## 12. Figure files

The submission-facing `figures/` directory intentionally contains only `.py` and `.pdf` files:

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

There is no invented `Figure1.py`. The supplied final Figure 1 source was TeX, so the artifact keeps the frozen Figure 1 PDF under the requested Python/PDF-only rule.

Regeneration:

```bash
bash RUN_FIGURES.sh
```

The script writes regenerated outputs outside `figures/`; it never replaces the frozen final PDFs.

---

## 13. Integrity and anonymity

### File integrity

Run:

```bash
bash VERIFY_HASHES.sh
```

Expected:

```text
INTEGRITY=PASS
```

This checks files against `SHA256SUMS.txt`.

### Source-tree coverage

`SOURCE_ARTIFACT_COVERAGE.tsv` records every source file from the original project `artifacts/` tree and whether it was retained, anonymized in place, renamed for distribution, or excluded as identity-bearing Git metadata.

The associated verifier is included in the normal deterministic verification path.

### Deep anonymity/hygiene scan

Run:

```bash
bash CHECK_ANONYMITY.sh
```

This is intentionally deeper and slower than the numerical verifier. It checks distributed names/content and recursively inspects supported nested ZIP/TAR archives for known identity strings and high-confidence credential patterns, and it rejects `.git` metadata and symlinks.

Expected:

```text
ANONYMITY=PASS
```

No real API keys are included in the artifact.

---

## 14. Artifact self-test

Before starting expensive model runs, run:

```bash
bash SELF_TEST.sh
```

This checks shell syntax, package structure, all 12 stage entry points through the master runner's dry-run mode, and the complete frozen numerical verification. It does not perform provider/model calls or copy the entire artifact into a disposable run directory.

A passing self-test means the packaged deterministic verification path and stage orchestration are internally consistent. It does **not** prove that a remote provider account has access or that a particular GPU can fit every model; `CHECK_E2E.sh` handles those external requirements. The deterministic threshold and figure stages were also exercised during package validation; their outputs are described in Section 20.

---

## 15. Reproducibility boundaries and interpretation

### Hosted models are external dependencies

OpenRouter and its upstream providers are external systems. The artifact preserves model identifiers, request paths, frozen protocols, output handling, and historical outputs, but cannot force a hosted provider to return the exact historical response in the future.

Therefore:

- a fresh hosted run is a replication of the procedure;
- the frozen outputs distributed here are the execution record for the paper;
- `VERIFY.sh` reproduces the exact paper numbers from that record.

### Local models are revision-pinned where the protocol requires it

The vLLM launchers request the Hugging Face revisions used by the experiment protocols. `CHECK_E2E.sh` verifies that those revisions are accessible before the expensive run begins.

### Different experiments have different inferential units

Do not treat every row/model call as an independent sample. The relevant units differ by study and are recorded in the paper and frozen analysis artifacts. Examples include 24 matched bases for A14/N3 and 14 natural tasks for the live experiment.

### Null and mixed results are part of the reproduced record

The artifact is not designed to return only favorable outcomes. In particular, the direct CONFLICT PAEF interval includes zero, N6 does not establish positive aggregate matched authorization separation, and N3 has case-level heterogeneity. Those boundaries are checked rather than hidden.

---

## 16. Troubleshooting

### `OPENROUTER_API_KEY` is missing

```bash
export OPENROUTER_API_KEY='...'
```

Then rerun:

```bash
bash CHECK_E2E.sh
```

### Hugging Face access fails

```bash
export HF_TOKEN='...'
```

Confirm that the account has access to the gated repositories listed by the preflight failure.

### `vllm` has the wrong version

The corrected replay environment expects:

```text
vllm==0.26.0
```

Recreate the artifact environment:

```bash
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate
```

### A model does not fit on the selected GPUs

Inspect visible GPUs:

```bash
nvidia-smi
```

Choose different valid indices:

```bash
export USENIX_GPU_LIST='2,3'
```

Do not change model revisions or frozen experiment parameters merely to make the model fit; use hardware with sufficient capacity.

### A vLLM port is already occupied

The launchers intentionally fail instead of silently connecting to an unknown server. Stop the process that owns the port, then rerun the stage.

### A run stops midway

Inspect:

```text
<run-root>/results/logs/
<run-root>/servers/
<run-root>/RUN_METADATA.txt
```

Then run the failed stage independently, for example:

```bash
bash RUN_END_TO_END.sh --stage 08
```

### A hosted rerun differs from the frozen result

That is possible for external hosted models. Keep the new run as a replication result. Do not replace the frozen evidence. Run:

```bash
bash VERIFY.sh
```

to confirm that the submitted paper numbers still re-derive from the historical execution record.

### `VERIFY_HASHES.sh` fails after local edits

The integrity manifest describes the distributed package. Editing a tracked file should make integrity verification fail. Restore the distributed file or intentionally rebuild the package and manifest; do not treat a modified tree as the original verified artifact.

---

## 17. Recommended complete sequence

### Fast audit first

```bash
bash CHECK_E2E.sh --structural
bash VERIFY.sh
bash VERIFY_HASHES.sh
bash RUN_FIGURES.sh
```

Optional deep hygiene check:

```bash
bash CHECK_ANONYMITY.sh
```

### Full rerun

```bash
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate

export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
export USENIX_GPU_LIST='0,1'

bash CHECK_E2E.sh
bash RUN_END_TO_END.sh --all
```

### Inspect results

```bash
cat <run-root>/RUN_METADATA.txt
find <run-root>/results -maxdepth 2 -type f | sort
ls <run-root>/results/logs
```

The presence of `END_TO_END_RERUN=PASS` means every selected stage exited successfully. Scientific agreement with the frozen paper record should be assessed using the corresponding stage outputs and the frozen-result checks described above, not merely from the shell exit status.

---

## 18. Files that should remain immutable

Treat the following as the distributed execution record or integrity metadata:

```text
SHA256SUMS.txt
SOURCE_ARTIFACT_COVERAGE.tsv
frozen protocol/freezes
frozen raw/model outputs
final paper figure PDFs
```

The master runner creates a disposable worktree specifically so fresh experiments cannot overwrite these files.

If the distributed artifact is modified, regenerate and re-verify the integrity manifest before treating the modified package as a new frozen release.

---

## 19. One-screen command reference

```bash
# Structural package check
bash CHECK_E2E.sh --structural

# Exact submitted numbers, no model calls
bash VERIFY.sh

# Regenerate figures
bash RUN_FIGURES.sh

# Deep anonymity scan
bash CHECK_ANONYMITY.sh

# File integrity
bash VERIFY_HASHES.sh

# Local deterministic self-test
bash SELF_TEST.sh

# Full environment
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate
export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
export USENIX_GPU_LIST='0,1'
bash CHECK_E2E.sh

# Show experiments
bash RUN_END_TO_END.sh --list

# Validate all stage wiring without model calls
bash RUN_END_TO_END.sh --dry-run --all

# Run everything
bash RUN_END_TO_END.sh --all

# Run one experiment
bash RUN_END_TO_END.sh --stage 10
```

---

## 20. Package validation performed before distribution

The distributed package was validated at three levels.

**Static/orchestration checks:** all distributed shell scripts pass `bash -n`; `CHECK_E2E.sh --structural` passes; and `RUN_END_TO_END.sh --dry-run --all` resolves and syntax-checks all 12 stage scripts.

**Deterministic scientific checks:** `VERIFY.sh` recomputes the frozen paper-bearing quantities and returns 56 PASS / 0 FAIL. SHA-256 integrity and original-source coverage also pass after the final package manifest is generated.

**Executed deterministic stages:** the threshold-frontier stage was run through `RUN_END_TO_END.sh --stage 06` and completed with `END_TO_END_RERUN=PASS`. The figure stage was run through `RUN_END_TO_END.sh --stage 12` and completed with `END_TO_END_RERUN=PASS`. At 150 dpi, Figures 1, 3, 4, 5, and 6 rendered identically to their frozen PDFs in the validation environment; Figure 2 regenerated successfully from the supplied producer and frozen A14 evidence but its raster differed from the frozen PDF because the final PDF was produced in a different font/rendering environment. The frozen `figure2.pdf` remains the submitted visual record.

The OpenRouter/Hugging Face/vLLM stages cannot be executed in this packaging environment because the artifact intentionally contains no private API credentials and this environment does not provide the required vLLM GPU setup. Those stages are therefore validated structurally here and are guarded by the full `CHECK_E2E.sh` preflight. A successful external `CHECK_E2E.sh` is required before `RUN_END_TO_END.sh --all` starts model/API execution.
