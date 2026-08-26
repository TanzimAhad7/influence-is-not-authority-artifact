# Reproduction Guide

## Fast path: verify the paper from frozen evidence

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

## Regenerate the figures

```bash
bash RUN_FIGURES.sh
```

The regenerated files are written to a fresh run directory outside the frozen `figures/` directory.

## Full fresh rerun

### Requirements

- Linux
- Python >= 3.10
- `bash`, `curl`, `tar`, `sha256sum`
- OpenRouter API access
- Hugging Face access to the required model revisions
- NVIDIA GPUs suitable for the local vLLM stages
- `vllm==0.26.0` for the corrected replay branch

### Setup

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

### Run all stages

```bash
bash RUN_END_TO_END.sh --all
```

### List stages

```bash
bash RUN_END_TO_END.sh --list
```

### Run one stage

```bash
bash RUN_END_TO_END.sh --stage 04
```

### Run deterministic stages only

```bash
bash RUN_END_TO_END.sh --stage 06
bash RUN_END_TO_END.sh --stage 12
```

Stages 06 and 12 do not require model/provider calls.

## Output isolation

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

## Hosted-model drift

OpenRouter and upstream providers are external systems. A fresh hosted response may differ from the historical response. Keep fresh outputs as replication results; do not replace the distributed frozen execution record.

## Credentials

Do not store credentials in this repository. Set them only in the shell environment:

```bash
export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
```

## Integrity and anonymity

```bash
bash VERIFY_HASHES.sh
bash CHECK_ANONYMITY.sh
```

Source-tree coverage is recorded in `supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv`.
