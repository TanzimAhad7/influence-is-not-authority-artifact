# A15b-0 Runbook

## Phase 0 — do not run B1 outcomes

B1 is frozen at:

`61f47a7507f03b01931e6c5b3452dfe43ac9a9b67b52b3079b85214880c7827f`

Do **not** run `B1_01_run.py` yet.

## Phase 1 — install package in `~/ratchet/phase0_pilot`

Copy the package files into the project root, then:

```bash
cd ~/ratchet/phase0_pilot
source .venv/bin/activate

python3 -m py_compile \
  a15b0_common.py \
  A15B0_00_source_lock.py \
  A15B0_01_prepare_inputs.py \
  A15B0_02_freeze_protocol.py \
  A15B0_03_preflight.py \
  A15B0_04_run_agentwatcher.py \
  A15B0_04b_run_no_attribution.py \
  A15B0_05_rescore_natural_gemma.py \
  A15B0_06_analyze.py
```

## Phase 2 — lock the official AgentWatcher source/models

```bash
python3 A15B0_00_source_lock.py --clone
```

This creates `a15b0_architecture_boundary/source_lock.json`.

It may require:
- `git`,
- `huggingface_hub`,
- a valid `HF_TOKEN` for the gated Llama attribution model metadata.

It generates **no scientific outcomes**.

## Phase 3 — build exact controlled + natural manifests

```bash
python3 A15B0_01_prepare_inputs.py
```

Expected invariant counts:
- controlled: 96 conditions / 24 bases;
- natural: 26 decisions / 23 unique task clusters;
- SPECIFIED: 7 decisions / 7 clusters;
- DELEGATED: 9 decisions / 6 clusters;
- PARTIAL: 10 decisions / 10 clusters.

The script will also report whether the 48 within-provenance SHAM/ECHO pairs collapse to
identical AgentWatcher static inputs.

**Stop and send the full output to ChatGPT/Claude before freezing.**

## Phase 4 — freeze A15b-0

Only after the source lock and manifest audit are accepted:

```bash
python3 A15B0_02_freeze_protocol.py
```

This creates:
- `a15b0_architecture_boundary/protocol.json`
- `a15b0_architecture_boundary/FREEZE_COMPLETE.json`

No model outcomes are generated.

## Phase 5 — after freeze only

Start/serve the exact frozen AgentWatcher monitor adapter through an OpenAI-compatible endpoint.
The endpoint must advertise the model ID exactly as:

`SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507`

Then run synthetic preflight only:

```bash
python3 A15B0_03_preflight.py \
  --monitor-base-url http://localhost:8120/v1
```

Do not run scientific arms until this passes.

The preflight and full AgentWatcher runner resolve the attribution LLM from the **exact
Hugging Face revision recorded in `source_lock.json`**, rather than from a floating repo ID.

The official AgentWatcher attribution module is imported under an isolated package namespace
that preserves its relative imports while avoiding execution of the repository-wide
`src/defenses/__init__.py` defense aggregator. This is an import-harness fix only; the pinned
AgentWatcher attribution source itself is not modified.

## Phase 6 — scientific paired-trace runs

Controlled:
```bash
python3 A15B0_04_run_agentwatcher.py \
  --arm controlled \
  --monitor-base-url http://localhost:8120/v1
```

Natural:
```bash
python3 A15B0_04_run_agentwatcher.py \
  --arm natural \
  --monitor-base-url http://localhost:8120/v1
```

Predeclared monitor-without-localization ablation:

```bash
python3 A15B0_04b_run_no_attribution.py \
  --arm controlled \
  --monitor-base-url http://localhost:8120/v1

python3 A15B0_04b_run_no_attribution.py \
  --arm natural \
  --monitor-base-url http://localhost:8120/v1
```

This is **not** called an exact reproduction of AgentWatcher's Table-4 "No attribution" row unless
the pinned source audit confirms identical semantics.

Natural source-fidelity CausalArmor Gemma rescore:
```bash
python3 A15B0_05_rescore_natural_gemma.py \
  --base-url http://localhost:8111/v1
```

Then:
```bash
python3 A15B0_06_analyze.py
```

## Phase 7 — AgentWatcher source-fidelity Arm C

Run only after the paired-trace protocol is frozen. Use the pinned official repo in its own
PIArena/AgentDojo environment, explicitly setting K=3 and all paper hyperparameters.

Audit the official `sample_size=200` semantics before calling a run paper-scale or reproduction-like.
