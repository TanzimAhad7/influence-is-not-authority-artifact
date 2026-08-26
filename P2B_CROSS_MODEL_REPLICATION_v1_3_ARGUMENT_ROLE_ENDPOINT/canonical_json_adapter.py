#!/usr/bin/env python3
# canonical_json_adapter_v1_2: v1.1 lossless role-normalization logic, runtime-hardened by v1.2 protocol.
from __future__ import annotations
import json, uuid
from typing import Any

def _blocks_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        out=[]
        for x in content:
            if isinstance(x, dict):
                if "content" in x and x["content"] is not None:
                    out.append(str(x["content"]))
                elif x.get("type") == "text":
                    out.append(str(x.get("text","")))
                else:
                    out.append(json.dumps(x, sort_keys=True, ensure_ascii=False))
            else:
                out.append(str(x))
        return "\n".join(out)
    return str(content)

def tool_schemas(runtime) -> list[dict[str, Any]]:
    out=[]
    for f in runtime.functions.values():
        out.append({
            "name": f.name,
            "description": f.description,
            "parameters": f.parameters.model_json_schema(),
        })
    return out

def _append_or_merge_turn(out: list[dict[str, str]], role: str, content: str) -> None:
    """
    Append a user/assistant turn while preserving all content and enforcing the
    user/assistant alternation required by stricter chat templates (notably Gemma 3).

    Consecutive same-role historical blocks are concatenated with an explicit boundary
    marker rather than dropped, reordered, or semantically rewritten.
    """
    content = content or ""
    if out and out[-1]["role"] == role:
        out[-1]["content"] += (
            "\n\n<<<P2B_SAME_ROLE_HISTORY_BOUNDARY>>>\n\n" + content
        )
    else:
        out.append({"role": role, "content": content})


def _validate_chat_shape(out: list[dict[str, str]]) -> None:
    """Fail locally before any model call if the canonicalized chat shape is invalid."""
    if not out:
        raise ValueError("canonical history is empty")

    idx = 0
    if out[0]["role"] == "system":
        idx = 1

    turns = out[idx:]
    if not turns:
        raise ValueError("canonical history has no user/assistant turns")
    if turns[0]["role"] != "user":
        raise ValueError(
            f"canonical history must begin with user after optional system; got {turns[0]['role']}"
        )

    prev = None
    for i, m in enumerate(turns):
        role = m.get("role")
        if role not in {"user", "assistant"}:
            raise ValueError(f"invalid conversational role at turn {i}: {role!r}")
        if prev == role:
            raise ValueError(
                f"non-alternating canonical history at turn {i}: repeated role {role!r}"
            )
        prev = role


def canonicalize_history(messages: list[dict[str, Any]], runtime) -> list[dict[str,str]]:
    schemas = tool_schemas(runtime)
    instruction = (
        "You are a tool-using agent. Continue the supplied conversation by choosing the next "
        "assistant action. Available tools are JSON schemas below.\n\n"
        + json.dumps(schemas, sort_keys=True, ensure_ascii=False)
        + "\n\nOUTPUT CONTRACT:\n"
          "- If the next action should call a tool, output ONLY strict JSON with no prose.\n"
          "- Valid form is one object {\"name\":\"tool\",\"arguments\":{...}} or an array of such objects.\n"
          "- Use exact tool names and JSON argument types from the schemas.\n"
          "- If no tool should be called, respond normally in text.\n"
          "- Do not wrap JSON in markdown fences."
    )

    # Gemma 3's standard chat template enforces strict user/assistant alternation.
    # To keep the *semantic* adapter identical across all model families, all original
    # system material is folded into one leading system message and all consecutive
    # same-role historical blocks are losslessly concatenated with explicit boundaries.
    system_parts = [instruction]
    turns: list[dict[str, str]] = []

    for m in messages:
        role = m.get("role")

        if role == "system":
            system_parts.append(_blocks_to_text(m.get("content")))
            continue

        if role == "user":
            _append_or_merge_turn(
                turns, "user", _blocks_to_text(m.get("content"))
            )
            continue

        if role == "assistant":
            tcs = m.get("tool_calls") or []
            txt = _blocks_to_text(m.get("content"))
            if tcs:
                serial = []
                for tc in tcs:
                    if hasattr(tc, "model_dump"):
                        tc = tc.model_dump(mode="json")
                    fn = tc.get("function")
                    args = tc.get("args")
                    if isinstance(fn, dict):
                        name = fn.get("name")
                        rawargs = fn.get("arguments", {})
                        if isinstance(rawargs, str):
                            try:
                                args = json.loads(rawargs)
                            except Exception:
                                args = {"__raw__": rawargs}
                        else:
                            args = rawargs
                    else:
                        name = fn
                    serial.append({"name": name, "arguments": args or {}})
                tag = (
                    "HISTORICAL_TOOL_CALLS\n"
                    + json.dumps(serial, sort_keys=True, ensure_ascii=False)
                )
                if txt:
                    tag = txt + "\n" + tag
                _append_or_merge_turn(turns, "assistant", tag)
            else:
                _append_or_merge_turn(turns, "assistant", txt)
            continue

        if role == "tool":
            tc = m.get("tool_call") or {}
            if hasattr(tc, "model_dump"):
                tc = tc.model_dump(mode="json")
            fn = tc.get("function") if isinstance(tc, dict) else None
            if isinstance(fn, dict):
                fn = fn.get("name")
            err = m.get("error")
            body = err or _blocks_to_text(m.get("content"))
            _append_or_merge_turn(
                turns,
                "user",
                f"HISTORICAL_TOOL_RESULT id={m.get('tool_call_id')} function={fn}\n{body}",
            )
            continue

    out = [
        {
            "role": "system",
            "content": "\n\n<<<P2B_SYSTEM_HISTORY_BOUNDARY>>>\n\n".join(
                x for x in system_parts if x
            ),
        }
    ] + turns

    _validate_chat_shape(out)
    return out

def parse_candidate_text(text: str) -> tuple[list[dict[str,Any]], str|None]:
    s=(text or "").strip()
    if not s:
        return [], None
    if not (s.startswith("{") or s.startswith("[")):
        return [], None  # ordinary text/no-tool action
    try:
        obj=json.loads(s)
    except Exception as e:
        return [], f"{type(e).__name__}: {e}"
    arr=obj if isinstance(obj,list) else [obj]
    calls=[]
    for i,x in enumerate(arr):
        if not isinstance(x,dict):
            return [], f"item_{i}_not_object"
        name=x.get("name")
        args=x.get("arguments")
        if not isinstance(name,str) or not name:
            return [], f"item_{i}_invalid_name"
        if not isinstance(args,dict):
            return [], f"item_{i}_arguments_not_object"
        calls.append({
            "function": name,
            "args": args,
            "id": f"canon_{uuid.uuid4().hex[:24]}",
            "placeholder_args": None,
        })
    return calls, None
