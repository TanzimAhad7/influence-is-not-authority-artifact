# Reproduction Guide

## 1. Full experiment rerun from model/provider calls

```bash
bash SETUP_E2E.sh --install-vllm
source .venv-e2e/bin/activate
export OPENROUTER_API_KEY='...'
export HF_TOKEN='...'
export USENIX_GPU_LIST='0,1'
bash CHECK_E2E.sh
bash RUN_END_TO_END.sh --all
```

This is the end-to-end path for users who have OpenRouter access, Hugging Face model access,
and suitable vLLM GPUs. It creates a fresh working copy, executes the paper-bearing experiment
pipelines, re-runs analyses, and regenerates figures. The distributed frozen evidence is never overwritten.
See `FULL_RERUN.md` for the stage map and exact scope.

## 2. Fast offline verification of the reported paper numbers

```bash
bash VERIFY.sh
```

This requires no API keys, model downloads, or GPU. It re-derives/cross-checks the manuscript-bearing
quantities from the frozen outputs distributed with the artifact.

## 3. Figures only

```bash
bash RUN_FIGURES.sh
```

The submission-facing `figures/` directory intentionally contains only `.py` and `.pdf` files.
Figure 1 is distributed as a frozen PDF because the supplied final bundle did not include a Python
producer for it. Figures 2--6 include Python producers.

## 4. Integrity / anonymity

```bash
bash CHECK_ANONYMITY.sh
bash VERIFY_HASHES.sh
```

`SOURCE_ARTIFACT_COVERAGE.tsv` accounts for the files copied from the original artifact
`artifacts/` tree. Git metadata from a bundled third-party repository is excluded because it can contain
identity/email/local-machine information; that exclusion is documented rather than silent.
