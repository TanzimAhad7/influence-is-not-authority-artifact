# AttriGuard Adaptive Attack

This directory contains the AgentDojo adaptive attack pipeline for evaluating AttriGuard. The default entry point is `openevolve_for_agentdojo/run.sh`; the main configuration file is `openevolve_for_agentdojo/config.yaml`.

## Environment

Create the conda environment from this directory:

```bash
cd adaptive_attack
conda env create -f environment.yaml
conda activate adaptive
```

`environment.yaml` installs the public dependencies from their upstream distribution channels, including:

```yaml
- agentdojo==0.1.35
- openevolve==0.2.27
```

Alternatively, after activating a compatible Python 3.10 environment, install the two key packages manually:

```bash
pip install agentdojo==0.1.35 openevolve==0.2.27
```

## Configuration

Fill in `openevolve_for_agentdojo/config.yaml` before running the pipeline. The default config intentionally leaves model endpoints, model names, API keys, task lists, and target scores empty.

Important fields:

- `llm`: OpenEvolve's mutator model for rewriting candidate injections.
- `critic`: the scorer model used to evaluate candidate injections.
- `evaluator.extra_kwargs.agentdojo_cfg.model`: the target AgentDojo model provider.
- `evaluator.extra_kwargs.agentdojo_cfg.model_id`: the target model name exposed by the OpenAI-compatible service.
- `evaluator.extra_kwargs.agentdojo_cfg.task_pairs`: AgentDojo task pairs in the form `suite:user_task&injection_task`.
- `evaluator.extra_kwargs.agentdojo_cfg.initial_trigger`: the initial seed payload file.
- `evaluator.extra_kwargs.agentdojo_cfg.target_score`: the OpenEvolve early-stop target score.

AttriGuard's helper models for judging and attenuation are configured through environment variables:

```bash
export ATTRIGUARD_BASE_URL="http://localhost:8000/v1"
export ATTRIGUARD_API_KEY="EMPTY"
export ATTRIGUARD_MODEL_ID="llama_3.3_70b_instruct_local"
export ATTRIGUARD_LEVEL=2
export ATTRIGUARD_SURVIVAL="fuzzy"
export ATTRIGUARD_SKIP_EMPTY_AUDIT=1
export ATTRIGUARD_DEBUG=1
```

The local target model reads `LOCAL_LLM_PORT`. If it is not set, the default is `8000`.

## Run

After filling in `config.yaml` and starting the model services, run:

```bash
cd adaptive_attack/openevolve_for_agentdojo
bash run.sh
```

The equivalent direct command is:

```bash
python -m my_benchmark -ml main_attack --config config.yaml
```

## Example: Qwen3 Mutator/Scorer and Llama 3 Target

Assumptions:

- Qwen3 OpenAI-compatible service: `http://localhost:8001/v1`
- Llama 3 OpenAI-compatible service: `http://localhost:8000/v1`
- Qwen3 model name: `qwen3_32b_local`
- Llama 3 target model name: `llama_3.3_70b_instruct_local`

Set the target model and AttriGuard helper-model environment variables:

```bash
export LOCAL_LLM_PORT=8000
export ATTRIGUARD_BASE_URL="http://localhost:8000/v1"
export ATTRIGUARD_API_KEY="EMPTY"
export ATTRIGUARD_MODEL_ID="llama_3.3_70b_instruct_local"
```

Then fill the relevant fields in `openevolve_for_agentdojo/config.yaml`:

```yaml
llm:
  api_base: "http://localhost:8001/v1"
  models:
    - name: "qwen3_32b_local"
      api_key: "EMPTY"
      weight: 1.0
      reasoning_effort: "high"
  temperature: 0.4
  max_tokens: 20000
  timeout: 150
  retries: 3

critic:
  api_url: "http://localhost:8001/v1/chat/completions"
  model_name: "qwen3_32b_local"
  api_key: "EMPTY"
  reasoning_effort: "medium"

evaluator:
  extra_kwargs:
    agentdojo_cfg:
      benchmark_module: "my_benchmark"
      benchmark_version: "v1.2.2"
      suite_name: ""
      logdir: "log"
      model: "local"
      model_id: "llama_3.3_70b_instruct_local"
      attack: "main_evolve"
      defense: "attriguard"
      tool_delimiter: "tool"
      quiet: true
      user_tasks: []
      injection_tasks: []
      task_pairs:
        - "slack:user_task_0&injection_task_3"
        - "travel:user_task_0&injection_task_1"
      initial_trigger: "seed_attriguard.txt"
      target_score: 10
```

Finally, run:

```bash
cd adaptive_attack/openevolve_for_agentdojo
bash run.sh
```
