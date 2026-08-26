# A15b-0C reconstruction v3 — completion-safe monitor runner

## Why v3 exists

The v2 reconstruction used a 256-token monitor completion ceiling because the
released AgentWatcher monitor model card contains a **usage example** with
`max_new_tokens=256`.

During the second pre-scientific rerun, the monitor produced a response that
ended mid-sentence before the required `No` / `Yes, Injection: ...` verdict.
The run was still inside AgentDojo's preliminary injection-task feasibility
stage; no sampled `(user_task, injection_task)` scientific pair had been
evaluated.

v3 therefore changes only the **maximum completion ceiling** from 256 to 4096.
It does not change the prompt, parser semantics, model, adapter, attribution,
temperature, benchmark sample, K/windows, attack, or analysis plan.

A larger `max_tokens` is a ceiling, not a requested output length: generations
that reach EOS earlier terminate normally. v3 also records `finish_reason` and
refuses to parse any response whose finish reason is `length`.

## Frozen v2 core SHA-256

`10d423221e57a3660feaa9e6f6ceec94721ab1e75ce860d114359585362125da`

## Apply

```bash
export AGENTWATCHER_MONITOR_MAX_TOKENS=4096

python3 patch_v2_to_v3.py   ~/ratchet/phase0_pilot/external/AgentWatcher_armc_runtime_v1
```

## Verify without API/model calls

From the AgentWatcher runtime repo:

```bash
PYTHONPATH="$PWD" python3 /path/to/verify_v3.py
```

Expected ending:

```text
RECONSTRUCTION V3 PREFLIGHT PASS
```

## Scientific provenance

Call this:
**source-faithful AgentWatcher reconstruction v3 (completion-safe)**

Do not call it an exact reproduction of the missing upstream `core.py`.
