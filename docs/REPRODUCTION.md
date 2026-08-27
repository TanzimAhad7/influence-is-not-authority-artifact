# Reproduction and Verification

This reviewer-facing guide consolidates the former reproduction, full-rerun, figure-reproduction, orchestration, and verification README files. The material is preserved here in one place; only repository paths were updated to match the reorganized distribution.

## Reviewer shortcuts

- Verify submitted numbers: `bash VERIFY.sh`
- Regenerate figures: `bash RUN_FIGURES.sh`
- Check package hashes: `bash VERIFY_HASHES.sh`
- Check anonymization: `bash CHECK_ANONYMITY.sh`
- Fresh rerun setup and stages: continue below.


<!-- merged from: REPRODUCE.md -->
## Reproduction Guide

### Fast path: verify the paper from frozen evidence

From the repository root:

```bash
bash VERIFY.sh
```

No API keys, model downloads, network access, or GPU are required.

Expected ending:

```text
SUMMARY: 56 PASS / 0 FAIL / 56 total
RESULTS_ONLY_VERIFY=PASS
```

The exact claim-to-file mapping is in `CLAIM_TO_ARTIFACT.md`.

### Regenerate the figures

```bash
bash RUN_FIGURES.sh
```

The regenerated files are written to a fresh run directory outside the frozen `figures/` directory.

### Full fresh rerun

#### Requirements

- Linux
- Python >= 3.10
- `bash`, `curl`, `tar`, `sha256sum`
- OpenRouter API access
- Hugging Face access to the required model revisions
- NVIDIA GPUs suitable for the local vLLM stages
- `vllm==0.26.0` for the corrected replay branch

#### Setup

```bash
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate

export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
export USENIX_GPU_LIST='0,1'

bash CHECK_E2E.sh
```

A successful preflight ends with:

```text
E2E_PREFLIGHT=PASS
```

#### Run all stages

```bash
bash RUN_END_TO_END.sh --all
```

#### List stages

```bash
bash RUN_END_TO_END.sh --list
```

#### Run one stage

```bash
bash RUN_END_TO_END.sh --stage 04
```

#### Run deterministic stages only

```bash
bash RUN_END_TO_END.sh --stage 06
bash RUN_END_TO_END.sh --stage 12
```

Stages 06 and 12 do not require model/provider calls.

### Output isolation

Fresh execution never overwrites the frozen submitted evidence.

The master runner creates a new sibling run directory containing:

```text
RUN_METADATA.txt
worktree/
results/
results/logs/
servers/
```

The repository uses descriptive study folders, while frozen experiment scripts retain historical identifiers. The runner therefore reconstructs those historical paths only inside the disposable worktree using `LEGACY_PATH_MAP.tsv`.

### Hosted-model drift

OpenRouter and upstream providers are external systems. A fresh hosted response may differ from the historical response. Keep fresh outputs as replication results; do not replace the distributed frozen execution record.

### Credentials

Do not store credentials in this repository. Set them only in the shell environment:

```bash
export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
```

### Integrity and anonymity

```bash
bash VERIFY_HASHES.sh
bash CHECK_ANONYMITY.sh
```

Source-tree coverage is recorded in `supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv`.


<!-- merged from: FULL_RERUN.md -->
## Full Rerun Stage Map

The full rerun follows the paper's evidence chain. Run:

```bash
bash RUN_END_TO_END.sh --list
```

Stages:

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
12_figures                      regenerate Figures 1--6
```

Stages 06 and 12 are deterministic and require no provider/model calls. All other stages require the dependencies documented in `docs/REPRODUCTION.md`.

The stage wrappers preserve the original scientific entry points. Because the repository is now organized into descriptive study folders, the master runner reconstructs the historical path layout only inside the disposable execution worktree.


<!-- merged from: FIGURE_REPRODUCTION.md -->
## Figure Reproduction

Run from the repository root:

```bash
bash RUN_FIGURES.sh
```

The figure stage reads the frozen evidence under the numbered `studies/` folders and writes regenerated outputs to a fresh run directory.

The frozen `figures/` directory contains the submitted PDFs and supplied figure sources. Figure 1 is PDF-only because the supplied final source was TeX. Figures 2--5 regenerate directly from their supplied Python producers. The supplied `Figure6.py` is retained for provenance with its pre-anonymization hash locks; `scripts/verification/render_figure6.py` is the reviewer-safe adapter used by the artifact pipeline for Figure 6.

PDF byte identity is not required across environments because creation metadata, font subsetting, and serialization can differ. The regenerated scientific values and rendered content are the relevant target.


<!-- merged from: reproduction/README.md -->
## Reproduction Orchestration

This directory contains the stage wrappers used for fresh experiment reruns.

For normal use, start from the repository root:

```bash
bash CHECK_E2E.sh --structural
bash RUN_END_TO_END.sh --list
```

The numbered wrappers are under `stages/`. They follow the paper's evidence chain from natural relevance through figure regeneration.

The original frozen experiment scripts use historical top-level run identifiers. `materialize_legacy_worktree.py`, `resolve_legacy_path.py`, and `LEGACY_PATH_MAP.tsv` provide a compatibility layer inside a disposable rerun worktree. They do not restore the flat historical hierarchy in the distributed repository.

See the Reproduction Guide and Full Rerun Stage Map above for requirements and commands.


<!-- merged from: verification/README.md -->
## Verification

The supported deterministic verification entry point is at the repository root:

```bash
bash VERIFY.sh
```

It re-derives and cross-checks the manuscript-bearing quantities from the frozen evidence and then checks package integrity and source-tree coverage.

Expected scientific summary:

```text
SUMMARY: 56 PASS / 0 FAIL / 56 total
RESULTS_ONLY_VERIFY=PASS
```

The machine-readable output produced by a run is written to `artifact_outputs/verification/` and is intentionally not part of the frozen package.

An older 45-claim packaging-time suite is preserved only for provenance under `supporting_material/legacy_verification/`; it is not the supported verification interface for this release.


<!-- merged from: artifact_tools/README.md -->
## Artifact Tools

Deterministic utilities used by the root verification, integrity, anonymity, and figure-regeneration entry points.

Most users should run the root commands (`VERIFY.sh`, `VERIFY_HASHES.sh`, `CHECK_ANONYMITY.sh`, and `RUN_FIGURES.sh`) rather than invoking these helpers directly.
