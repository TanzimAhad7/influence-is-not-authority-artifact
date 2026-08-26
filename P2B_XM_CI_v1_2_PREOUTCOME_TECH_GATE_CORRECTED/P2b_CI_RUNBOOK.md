# P2b-XM-CI v1.1 runbook

This runbook is intentionally two-stage: **technical validation first, scientific freeze second**.

## 0. Set paths

Assume you copy this package into the existing project tree, for example:

```bash
export PROJECT_ROOT=/home/anon_/ratchet/phase0_pilot
export PKG_ROOT="$PROJECT_ROOT/P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED"
export P2B_CUDA_DEVICES=2,3
export P2B_API_KEY=EMPTY
cd "$PKG_ROOT"
```

The scientific inventory references the existing frozen A13/A15a raw logs under `PROJECT_ROOT`; do not edit those paths/files.

Check the exact environment first:

```bash
python - <<'PY'
import importlib.metadata
print('agentdojo', importlib.metadata.version('agentdojo'))
print('vllm', importlib.metadata.version('vllm'))
print('openai', importlib.metadata.version('openai'))
print('jsonschema', importlib.metadata.version('jsonschema'))
PY
```

Required scientific pins checked by code: AgentDojo `0.1.35`, vLLM `0.26.0`.

---

# PHASE A — EXCLUDED TECHNICAL VALIDATION (NO SCIENTIFIC CASE GENERATIONS)

## A1. Static audit

```bash
cd "$PKG_ROOT"
python P2b_CI_00_static_audit.py
cat P2B_CI_STATIC_AUDIT.json
```

Expected before proceeding: `STATIC AUDIT PASS`.

## A2. Llama technical stress preflight

Use a technical server directory separate from final science runs:

```bash
export TECH_LLAMA="$PKG_ROOT/technical_server/llama"
./serve_model.sh llama "$TECH_LLAMA"
tail -f "$TECH_LLAMA/vllm_server.log"
```

In another terminal, after `/v1/models` is responsive:

```bash
cd "$PKG_ROOT"
python P2b_CI_01_stress_preflight.py \
  --model-key llama \
  --base-url http://localhost:8100/v1 \
  --server-run-dir "$TECH_LLAMA" \
  --out-dir "$PKG_ROOT/technical_preflight/llama"
./stop_server.sh "$TECH_LLAMA"
```

## A3. Gemma technical stress preflight

```bash
export TECH_GEMMA="$PKG_ROOT/technical_server/gemma"
./serve_model.sh gemma "$TECH_GEMMA"
# after server ready:
python P2b_CI_01_stress_preflight.py \
  --model-key gemma \
  --base-url http://localhost:8100/v1 \
  --server-run-dir "$TECH_GEMMA" \
  --out-dir "$PKG_ROOT/technical_preflight/gemma"
./stop_server.sh "$TECH_GEMMA"
```

## A4. Qwen technical stress preflight

```bash
export TECH_QWEN="$PKG_ROOT/technical_server/qwen_canonical"
./serve_model.sh qwen_canonical "$TECH_QWEN"
# after server ready:
python P2b_CI_01_stress_preflight.py \
  --model-key qwen_canonical \
  --base-url http://localhost:8100/v1 \
  --server-run-dir "$TECH_QWEN" \
  --out-dir "$PKG_ROOT/technical_preflight/qwen_canonical"
./stop_server.sh "$TECH_QWEN"
```

## A5. Technical gate

All three files must say `"pass": true`:

```bash
python - <<'PY'
import json, pathlib
root=pathlib.Path('technical_preflight')
for k in ['llama','gemma','qwen_canonical']:
    p=root/k/'P2B_CI_STRESS_PREFLIGHT.json'
    d=json.load(open(p))
    print(k, d['pass'], sum(x['pass'] for x in d['results']), '/', len(d['results']))
PY
```

If **any** excluded technical preflight fails, **do not freeze and do not touch the 26 scientific cases with model generation**. Debug only using excluded technical cases, produce a new package revision if code/interface changes, and rerun Phase A.

**v1.2 gate meaning:** `pass=True` is a technical instrument result: parsed common envelope + correct expected branch/tool path + valid synthetic tool schema. `exact_expected_match` is retained as a semantic replay diagnostic and may be false without invalidating the interface. Do not reinterpret this technical phase as scientific replay evidence.

---

# PHASE B — GLOBAL SCIENTIFIC FREEZE

Only after all three technical stress suites PASS:

```bash
cd "$PKG_ROOT"
python P2b_CI_02_freeze_global.py
cat P2B_XM_CI_GLOBAL_FREEZE.json
sha256sum P2B_XM_CI_GLOBAL_FREEZE.json
```

**From this point onward, do not edit the package under this freeze.**

---

# PHASE C — LLAMA CORRECTED SCIENTIFIC ARM

```bash
export LLAMA_RUN="$PROJECT_ROOT/P2B_XM_CI_LLAMA_RUN_v1_2"
./serve_model.sh llama "$LLAMA_RUN"
```

After server ready:

```bash
python P2b_CI_03_render_preflight.py \
  --model-key llama --project-root "$PROJECT_ROOT" \
  --base-url http://localhost:8100/v1 --out-dir "$LLAMA_RUN"

python P2b_CI_04_freeze_arm.py \
  --model-key llama --project-root "$PROJECT_ROOT" \
  --base-url http://localhost:8100/v1 --run-dir "$LLAMA_RUN"

python P2b_CI_05_run_baseline.py \
  --project-root "$PROJECT_ROOT" --run-dir "$LLAMA_RUN"

python P2b_CI_06_analyze_arm.py --run-dir "$LLAMA_RUN"
python P2b_CI_07_argument_role.py --run-dir "$LLAMA_RUN"
./stop_server.sh "$LLAMA_RUN"
```

Record the arm disposition. **Continue to Gemma regardless of scientific PASS/FAIL.**

---

# PHASE D — GEMMA CORRECTED SCIENTIFIC ARM

```bash
export GEMMA_RUN="$PROJECT_ROOT/P2B_XM_CI_GEMMA_RUN_v1_2"
./serve_model.sh gemma "$GEMMA_RUN"
# after ready:
python P2b_CI_03_render_preflight.py --model-key gemma --project-root "$PROJECT_ROOT" --base-url http://localhost:8100/v1 --out-dir "$GEMMA_RUN"
python P2b_CI_04_freeze_arm.py --model-key gemma --project-root "$PROJECT_ROOT" --base-url http://localhost:8100/v1 --run-dir "$GEMMA_RUN"
python P2b_CI_05_run_baseline.py --project-root "$PROJECT_ROOT" --run-dir "$GEMMA_RUN"
python P2b_CI_06_analyze_arm.py --run-dir "$GEMMA_RUN"
python P2b_CI_07_argument_role.py --run-dir "$GEMMA_RUN"
./stop_server.sh "$GEMMA_RUN"
```

**Continue to Qwen regardless of scientific PASS/FAIL.**

---

# PHASE E — QWEN CORRECTED SCIENTIFIC ARM

```bash
export QWEN_RUN="$PROJECT_ROOT/P2B_XM_CI_QWEN_RUN_v1_2"
./serve_model.sh qwen_canonical "$QWEN_RUN"
# after ready:
python P2b_CI_03_render_preflight.py --model-key qwen_canonical --project-root "$PROJECT_ROOT" --base-url http://localhost:8100/v1 --out-dir "$QWEN_RUN"
python P2b_CI_04_freeze_arm.py --model-key qwen_canonical --project-root "$PROJECT_ROOT" --base-url http://localhost:8100/v1 --run-dir "$QWEN_RUN"
python P2b_CI_05_run_baseline.py --project-root "$PROJECT_ROOT" --run-dir "$QWEN_RUN"
python P2b_CI_06_analyze_arm.py --run-dir "$QWEN_RUN"
python P2b_CI_07_argument_role.py --run-dir "$QWEN_RUN"
./stop_server.sh "$QWEN_RUN"
```

---

# PHASE F — JOINT ANALYSIS

```bash
export JOINT="$PROJECT_ROOT/P2B_XM_CI_JOINT_v1_2"
python P2b_CI_08_joint_compare.py \
  --llama-run "$LLAMA_RUN" \
  --gemma-run "$GEMMA_RUN" \
  --qwen-run "$QWEN_RUN" \
  --out-dir "$JOINT"

cat "$JOINT/P2B_XM_CI_JOINT.md"
```

There is intentionally **no intervention command** here.

If one or more model arms are eligible after corrected baseline analysis, first adjudicate the complete three-arm result against v73 and then create a **separate prospective intervention freeze**. Do not bolt intervention onto this package after seeing baseline outcomes.

---

# Resume after infrastructure interruption

If `P2b_CI_05_run_baseline.py` stops because of a server/transport exception:

1. do not delete completed JSONL rows;
2. restart the same frozen model/revision/server configuration;
3. verify the same arm freeze remains intact;
4. rerun the same baseline command.

The script skips existing `(decision_id, repeat_index)` rows under that arm freeze and generates only missing rows. Never regenerate a completed scientific response because its result was unfavorable.


**Lossless-history invariant:** historical assistant prose is preserved inside the common action envelope even when the same historical turn contains tool calls; the corrected interface must not delete replay-context content.
