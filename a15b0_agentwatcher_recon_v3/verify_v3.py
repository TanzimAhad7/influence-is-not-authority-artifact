#!/usr/bin/env python3
"""No-model v3 verification."""
import os

if os.environ.get("AGENTWATCHER_MONITOR_MAX_TOKENS") != "4096":
    raise SystemExit("AGENTWATCHER_MONITOR_MAX_TOKENS must be 4096")

from src.defenses.monitor_llm_module.core import RUNNER_ID, _config, _parse_monitor_output

assert RUNNER_ID == "A15B0_AGENTWATCHER_RECONSTRUCTION_v3_COMPLETION_SAFE"
cfg = _config()
assert cfg[-1] == 4096

assert _parse_monitor_output("<Reasoning>ok</Reasoning>\nNo")["detect_flag"] is False
assert _parse_monitor_output(
    "<Reasoning>bad</Reasoning>\nYes, Injection: injected text"
)["detect_flag"] is True

print("runner id:", RUNNER_ID)
print("completion ceiling:", cfg[-1])
print("parser sanity: PASS")
print("NO MODEL/API CALLS MADE")
print("RECONSTRUCTION V3 PREFLIGHT PASS")
