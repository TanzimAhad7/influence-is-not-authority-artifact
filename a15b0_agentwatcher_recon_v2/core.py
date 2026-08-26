"""
A15b-0C source-faithful reconstruction of the missing public
AgentWatcher monitor_llm_module/core.py.

Scientific label: source-faithful AgentWatcher reconstruction.
This is NOT an exact reproduction of the missing upstream core.py.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI
from .messages import get_messages

RUNNER_ID = "A15B0_AGENTWATCHER_RECONSTRUCTION_v2_VLLM"


def _as_text(x: Any) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x
    if isinstance(x, (list, tuple)):
        return "\n".join(str(v) for v in x)
    return str(x)


def _benchmark(benchmark: str | None) -> str | None:
    value = benchmark or os.environ.get("AGENTWATCHER_BENCHMARK")
    return value.strip().lower() if value else None


def _config():
    base_url = os.environ.get(
        "AGENTWATCHER_MONITOR_BASE_URL",
        "http://127.0.0.1:8120/v1",
    ).rstrip("/")
    api_key = os.environ.get("AGENTWATCHER_MONITOR_API_KEY", "x")
    model = os.environ.get(
        "AGENTWATCHER_MONITOR_MODEL",
        "SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507",
    )
    max_tokens = int(os.environ.get("AGENTWATCHER_MONITOR_MAX_TOKENS", "256"))
    if max_tokens != 256:
        raise RuntimeError(
            "Frozen reconstruction requires AGENTWATCHER_MONITOR_MAX_TOKENS=256"
        )
    return base_url, api_key, model, max_tokens


def _validate_adapter_argument(monitor_llm):
    if not monitor_llm:
        raise RuntimeError("monitor_llm adapter path/id is required")
    text = str(monitor_llm)
    p = Path(text).expanduser()
    if p.exists():
        return str(p.resolve())
    return text


def _parse_monitor_output(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty AgentWatcher monitor output")

    verdict = (
        text.rsplit("</Reasoning>", 1)[-1].strip()
        if "</Reasoning>" in text
        else text
    )

    yes = re.match(
        r"^\s*Yes\s*,\s*Injection\s*:\s*(.+?)\s*$",
        verdict,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if yes:
        inj = yes.group(1).strip()
        if not inj:
            raise ValueError(f"Yes verdict without injection text: {raw!r}")
        return {
            "detect_flag": True,
            "potential_injection": inj,
            "parse_valid": True,
        }

    if re.match(r"^\s*No\.?\s*$", verdict, flags=re.IGNORECASE):
        return {
            "detect_flag": False,
            "potential_injection": None,
            "parse_valid": True,
        }

    m_yes = re.search(
        r"(?:^|\n)\s*Yes\s*,\s*Injection\s*:\s*(.+?)\s*$",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m_yes:
        inj = m_yes.group(1).strip()
        if inj:
            return {
                "detect_flag": True,
                "potential_injection": inj,
                "parse_valid": True,
            }

    if re.search(r"(?:^|\n)\s*No\.?\s*$", text, flags=re.IGNORECASE):
        return {
            "detect_flag": False,
            "potential_injection": None,
            "parse_valid": True,
        }

    raise ValueError(f"Unparseable AgentWatcher monitor output: {raw!r}")


def _query_monitor(messages: list[dict[str, str]]) -> tuple[str, dict]:
    base_url, api_key, model, max_tokens = _config()
    client = OpenAI(base_url=base_url, api_key=api_key)
    result = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=max_tokens,
    )
    if not result.choices:
        raise RuntimeError("Monitor endpoint returned no choices")
    raw = result.choices[0].message.content
    if raw is None:
        raise RuntimeError("Monitor endpoint returned empty message content")
    meta = {
        "base_url": base_url,
        "model_requested": model,
        "model_returned": getattr(result, "model", None),
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    return raw.strip(), meta


def monitor_llm(
    target_inst,
    context=None,
    response=None,
    system_prompt: str = "You are a helpful assistant.",
    llm=None,
    monitor_llm=None,
    benchmark: str | None = None,
    use_vllm: bool = False,
    **kwargs,
):
    del system_prompt, llm, use_vllm, kwargs

    adapter_arg = _validate_adapter_argument(monitor_llm)
    bench = _benchmark(benchmark)

    if os.environ.get("AGENTWATCHER_REQUIRE_AGENTDOJO", "0") == "1":
        if bench != "agentdojo":
            raise RuntimeError(
                f"Frozen attack anchor requires benchmark='agentdojo'; got {bench!r}"
            )

    full_msg = get_messages(
        _as_text(target_inst),
        _as_text(context),
        _as_text(response),
        benchmark=bench,
    )

    raw, endpoint_meta = _query_monitor(full_msg)
    parsed = _parse_monitor_output(raw)

    return {
        "potential_injection": parsed["potential_injection"],
        "detect_flag": parsed["detect_flag"],
        "parse_valid": parsed["parse_valid"],
        "monitor_llm_response": raw,
        "full_msg": full_msg,
        "reconstruction": {
            "runner": RUNNER_ID,
            "benchmark": bench,
            "adapter_argument": adapter_arg,
            "endpoint": endpoint_meta,
        },
    }


def monitor_llm_batch(
    target_insts,
    contexts=None,
    responses=None,
    system_prompt: str = "You are a helpful assistant.",
    llm=None,
    monitor_llm=None,
    benchmark: str | None = None,
    use_vllm: bool = False,
    **kwargs,
):
    del use_vllm

    n = len(target_insts)
    contexts = [""] * n if contexts is None else contexts
    responses = [""] * n if responses is None else responses

    if len(contexts) != n or len(responses) != n:
        raise ValueError("Batch inputs must have equal lengths")

    return [
        monitor_llm(
            target_inst=inst,
            context=ctx,
            response=resp,
            system_prompt=system_prompt,
            llm=llm,
            monitor_llm=monitor_llm,
            benchmark=benchmark,
            **kwargs,
        )
        for inst, ctx, resp in zip(target_insts, contexts, responses)
    ]
