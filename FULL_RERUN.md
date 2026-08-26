# Full End-to-End Model/Provider Rerun

The artifact includes a master runner for the original paper-bearing model/provider pipelines.
It is intentionally separate from `VERIFY.sh`, which checks the frozen evidence offline.

## Requirements

- Linux + Bash + Python >= 3.10
- an OpenRouter API key
- a Hugging Face token with access to the gated Llama/Gemma checkpoints
- NVIDIA GPUs capable of serving the listed models with vLLM; the default assumes two GPUs
- vLLM **0.26.0** for the corrected replay branch

The local models/checkpoints are pinned where the frozen protocols specify revisions. OpenRouter
requests use the model identities encoded by the original experiment code.

## Quick start

```bash
bash SETUP_E2E.sh --install-vllm       # omit --install-vllm if your exact GPU stack already has vLLM 0.26.0
source .venv-e2e/bin/activate

export OPENROUTER_API_KEY='YOUR_KEY'
export HF_TOKEN='YOUR_HF_TOKEN'
export USENIX_GPU_LIST='0,1'            # change to the two GPUs you want to use

bash CHECK_E2E.sh
bash RUN_END_TO_END.sh --all
```

The master runner creates a **fresh sibling worktree** and never overwrites the frozen evidence in
the distributed artifact. Logs and reproduced results are placed under `USENIX27_RERUN_<timestamp>/results/`.
Set `USENIX_RUN_ROOT=/path/to/run` if you want a different location.

## Stages

```text
01_a13_natural                 natural benign cohort
02_a13_c0_extension            confirmatory natural coverage extension
03_b1_generator_breadth        GPT-4o + Claude trajectories, fixed Llama scorer
04_a14_controlled_source       controlled USER→TOOL relocation, Llama + Gemma
05_n3_unauthorized_control     matched unauthorized alternative, Llama + Gemma
06_r2b_threshold_frontier      deterministic complete scalar frontier
07_agentwatcher                AW-N3 matched gate + separate 200-input ON/OFF operational anchor
08_n6_attriguard_architecture  AttriGuard N6 route/block study
09_causalarmor_calibration     reconstructed CausalArmor calibration/live regime
10_live_e2e_attriguard         420-run protected-effect live study
11_replay                      corrected Llama/Gemma/Qwen replay
12_figures                     paper figure regeneration from frozen artifact evidence
```

List stages or run one stage:

```bash
bash RUN_END_TO_END.sh --list
bash RUN_END_TO_END.sh --stage 04
bash RUN_END_TO_END.sh --stage 10_live_e2e_attriguard
```

### Why stages restore frozen inputs

The studies were separately frozen. A later study must not silently consume a newly regenerated
output from an earlier study if its protocol originally depended on the frozen historical input.
Each stage therefore captures its new outputs under the rerun directory and restores the corresponding
frozen artifact inside the disposable worktree before the next stage.

### Provider nondeterminism

A live re-execution is a replication of the frozen protocol, not a promise that third-party hosted
models return byte-identical responses years or days later. The distributed frozen outputs remain the
record for the paper's reported numbers; `VERIFY.sh` deterministically checks those numbers. The full
rerun is provided so users with the external resources can execute the same pipelines themselves.
