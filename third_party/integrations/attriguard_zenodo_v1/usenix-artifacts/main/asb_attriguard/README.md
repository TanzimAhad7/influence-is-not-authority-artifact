# AttriGuard for ASB

This directory contains only the minimal AttriGuard adaptation for ASB.

## Get ASB

Clone the original ASB repository yourself, then run the installer:

```bash
git clone https://github.com/agiresearch/ASB.git ASB
bash /path/to/final_code/main/asb_attriguard/setup_asb_attriguard.sh ASB
```

## Contents

- `overlay/pyopenagi/defenses/attriguard.py`: ASB-native AttriGuard implementation. The core naming and attenuation flow are aligned with `final_code/main/pipeline/AttriGuard.py`.
- `overlay/pyopenagi/defenses/__init__.py`: defense package marker.
- `overlay/pyopenagi/agents/react_agent_attack.py`: minimal ASB agent integration that loads AttriGuard, audits tool calls, and returns blocked observations.
- `overlay/pyopenagi/tools/simulated_tool.py`: minimal tool schema compatibility update for no-argument tools.
- `setup_asb_attriguard.sh`: installer that validates an ASB checkout, backs up replaced files, and installs the overlay.
- `environment.yml`: conda environment definition for the ASB adaptation.

## Environment

```bash
conda env create -f environment.yml
conda activate ASB
```

If you run local GPU models with vLLM, install vLLM separately for your CUDA environment.

## Configuration

This ASB adaptation of AttriGuard is intended for clean and OPI (observation prompt injection) experiments.

AttriGuard uses environment variables:

- `ATTRIGUARD_MODEL`: attenuation and judge model. Falls back to `JUDGE_MODEL`, then `OPENAI_MODEL`, then `gpt-4.1-mini`.
- `ATTRIGUARD_BASE_URL`, `ATTRIGUARD_API_KEY`: optional dedicated AttriGuard endpoint. Falls back to `OPENAI_BASE_URL` / `OPENAI_API_KEY`.
- `ATTRIGUARD_LEVEL`: `1`, `2`, or `3`. Level 1 flattens high-risk syntax; level 2 also transposes directive text; level 3 inserts de-causal rewriting before transposition.
- `ATTRIGUARD_SURVIVAL`: `exact`, `fuzzy`, or `hyper_fuzzy`. Defaults to `hyper_fuzzy`.
- `ATTRIGUARD_DEBUG`: `1` for debug traces, `0` otherwise.

## Run

After installing the overlay, run ASB from the ASB repo root. For example, to run the original clean or observation prompt injection config with AttriGuard, edit `config/clean.yml` or `config/OPI.yml` so it contains:

```yaml
defense_type: attriguard
```

Then start the run:

```bash
python scripts/agent_attack.py --cfg_path config/OPI.yml
```

Equivalent direct command:

```bash
python main_attacker.py \
  --llm_name ollama/qwen2:72b \
  --use_backend ollama \
  --attack_type context_ignoring \
  --attacker_tools_path data/all_attack_tools.jsonl \
  --res_file logs/observation_prompt_injection/qwen2:72b/attriguard/context_ignoring-all_.csv \
  --database memory_db/direct_prompt_injection/context_ignoring_gpt-4o-mini \
  --defense_type attriguard \
  --observation_prompt_injection
```

The installer backs up replaced ASB files under `.attriguard_backup/`.
This adaptation replaces only `pyopenagi/agents/react_agent_attack.py` and `pyopenagi/tools/simulated_tool.py`.
Set `defense_type: attriguard` in an ASB config to enable AttriGuard.
