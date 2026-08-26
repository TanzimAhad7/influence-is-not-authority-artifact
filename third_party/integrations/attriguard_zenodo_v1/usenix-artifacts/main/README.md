# AttriGuard

This repository contains the AttriGuard evaluation pipeline built on the official AgentDojo package. It also includes the ASB adaptation under `asb_attriguard/`.

## Environment

Create the conda environment from the provided file:

```bash
conda env create -f environment.yml
conda activate attriguard
```

The environment installs AgentDojo from PyPI. To install it manually:

```bash
pip install agentdojo==0.1.35
```

Install or expose any additional local model serving stack separately when using `--model local`.

## Configuration

Optionally create `pipeline/.env` from the example file if you prefer file-based configuration:

```bash
cd pipeline
cp .env.example .env
```

AttriGuard uses these environment variables:

- `ATTRIGUARD_BACKEND`: `openai` or `local`. Defaults to `openai`.
- `ATTRIGUARD_API_KEY`: optional API key for the AttriGuard attenuation and judge models.
- `ATTRIGUARD_MODEL_ID`: model used by the AttriGuard attenuation pipeline. Defaults to `gpt-4.1-mini`.
- `ATTRIGUARD_JUDGE_MODEL_ID`: model used by the AttriGuard judge. Defaults to `ATTRIGUARD_MODEL_ID`.
- `ATTRIGUARD_LOCAL_PORT`: local OpenAI-compatible server port for the AttriGuard attenuation pipeline when `ATTRIGUARD_BACKEND=local`. Defaults to `8001`.
- `ATTRIGUARD_LOCAL_JUDGE_PORT`: local OpenAI-compatible server port for the AttriGuard judge when `ATTRIGUARD_BACKEND=local`. Defaults to `ATTRIGUARD_LOCAL_PORT`.
- `ATTRIGUARD_LEVEL`: attenuation level. Defaults to `2`.
- `ATTRIGUARD_SURVIVAL`: survival mode. Defaults to `fuzzy`.
- `ATTRIGUARD_SKIP_EMPTY_AUDIT`: `1` to skip empty tool-result audits, `0` to audit them. Defaults to `1`.
- `ATTRIGUARD_DEBUG`: `1` to enable debug output, `0` to disable it. Defaults to `1`.

## Run

From `pipeline`, run a benchmark with no defense:

```bash
SUITE=workspace MODEL=gpt-4.1-mini DEFENSE= bash run.sh
```

Run with AttriGuard:

```bash
SUITE=workspace MODEL=gpt-4.1-mini bash run.sh
```

`run.sh` defaults to `DEFENSE=attriguard`. `SUITE`, `MODEL`, `MODEL_ID`, and `ATTACK` are intentionally left blank in the script and can be filled in directly or passed as environment variables.

## Local Example

This example assumes two local OpenAI-compatible servers are already running:

- Llama 3.3 target model on `localhost:8000`
- Qwen3 auxiliary model for AttriGuard on `localhost:8001`

Run one slack benchmark with local Llama 3.3 as the target agent and local Qwen3 as the AttriGuard attenuation/judge model:

```bash
cd pipeline
LOCAL_LLM_PORT=8000 \
SUITE=slack \
MODEL=local \
MODEL_ID=llama_3.3_70b_instruct_local \
ATTACK=tool_knowledge \
ATTRIGUARD_BACKEND=local \
ATTRIGUARD_MODEL_ID=qwen3_32b_local \
ATTRIGUARD_JUDGE_MODEL_ID=qwen3_32b_local \
ATTRIGUARD_LOCAL_PORT=8001 \
ATTRIGUARD_LEVEL=2 \
ATTRIGUARD_SURVIVAL=fuzzy \
bash run.sh
```

## ASB Adaptation

The ASB release materials live in `asb_attriguard/`. That directory intentionally contains only the minimal AttriGuard overlay for the original ASB repository:

```bash
cd asb_attriguard
cat README.md
```

Use `asb_attriguard/environment.yml` for the ASB conda environment named `ASB`. The original ASB repository should be cloned separately, then adapted with `asb_attriguard/setup_asb_attriguard.sh`.
