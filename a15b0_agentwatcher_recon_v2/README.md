# A15b-0C AgentWatcher reconstruction v2 — vLLM

This package is a **source-faithful AgentWatcher reconstruction**, not an exact
reproduction.

The public AgentWatcher artifact imports
`src.defenses.monitor_llm_module.core`, but does not ship `core.py`. This
package reconstructs only the missing monitor-runner glue and deliberately
reuses the same local vLLM monitor-serving pathway already used by this
project's successful benign A15b AgentWatcher runs.

## Frozen identities

- AgentWatcher HEAD:
  `f6ce2c8e0b3ecfdc04e81cd45d8818581c7ee037`
- Attribution revision:
  `0e9e39f249a16976918f6564b8830bc894c89659`
- Monitor adapter revision:
  `5d19a2f5c23e377a242eda9708e6f9cf430699be`
- Monitor base revision:
  `cdbee75f17c01a7cc42f958dc650907174af0554`
- Frozen 200-pair sample SHA:
  `b7c7846baeb5481ef93023d64d0b0ca110dc12f0563d52bb728e7f4ee958b26a`

## Reconstruction choices frozen before repaired attack outcomes

- released `messages.py` remains unchanged;
- benchmark explicitly bound to `agentdojo`;
- exact frozen Qwen base + released AgentWatcher LoRA served via local vLLM;
- temperature 0;
- max_tokens 256;
- generated-text-only parsing of the released strict verdict format;
- parse failures abort;
- AgentWatcher runtime failures abort rather than silently continuing without defense;
- unrelated bundled defenses are not imported.

The 256-token cap matches the released monitor model-card example. Because the
upstream `core.py` is missing, this is disclosed as a reconstruction choice,
not claimed as the authors' exact original setting.

## Apply only to the separate runtime worktree

```bash
python3 apply_reconstruction.py \
  ~/ratchet/phase0_pilot/external/AgentWatcher_armc_runtime_v1
```

## Start the frozen monitor endpoint

```bash
nohup bash start_monitor_vllm.sh \
  > ~/ratchet/phase0_pilot/logs/a15b0_recon_v2_monitor_8120.log 2>&1 &
echo $! > ~/ratchet/phase0_pilot/logs/a15b0_recon_v2_monitor_8120.pid
```

## Environment

```bash
export AGENTWATCHER_BENCHMARK=agentdojo
export AGENTWATCHER_REQUIRE_AGENTDOJO=1
export AGENTWATCHER_MONITOR_BASE_URL=http://127.0.0.1:8120/v1
export AGENTWATCHER_MONITOR_API_KEY=x
export AGENTWATCHER_MONITOR_MODEL=SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507
export AGENTWATCHER_MONITOR_MAX_TOKENS=256

export PIARENA_MONITOR_LLM="$HOME/.cache/huggingface/hub/models--SecureLLMSys--AgentWatcher-Qwen3-4B-Instruct-2507/snapshots/5d19a2f5c23e377a242eda9708e6f9cf430699be"
```

## Verify

```bash
python3 /path/to/verify_reconstruction.py
```

## Synthetic smoke

```bash
python3 /path/to/smoke_monitor.py
```

This smoke uses no frozen 200-pair scientific inputs.

## Paper/artifact disclosure

> The AgentWatcher public artifact references a monitor-runner module
> (`monitor_llm_module/core.py`) that is absent from the released repository.
> For our architecture-boundary attack sanity check, we therefore use a
> source-faithful reconstruction of this missing glue layer. The reconstruction
> uses the authors' released AgentWatcher attribution code, unmodified
> AgentDojo monitor prompt/rules, frozen released Qwen monitor adapter, and
> frozen base model, and reuses the same local vLLM monitor-serving pathway as
> our benign AgentWatcher evaluation. We freeze and publish the reconstruction
> and hashes before repaired attack outcomes and do not describe this arm as an
> exact reproduction of the original AgentWatcher evaluation.

After preflight + smoke pass, rerun `important_instructions` from scratch on
the unchanged frozen 200 pairs.
