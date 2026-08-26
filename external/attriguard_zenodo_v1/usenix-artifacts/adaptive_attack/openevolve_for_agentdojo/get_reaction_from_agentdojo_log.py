import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _normalize_for_match(text: str) -> str:
    """
    Fuzzy matching for injection text versus message text:
    - normalize \n / \\n
    - convert \\\" to "
    - remove all quotes and backslashes
    - collapse whitespace
    """
    if not isinstance(text, str):
        text = str(text)

    # Normalize escaped text into real text where possible.
    # Note: "\\n" here means two literal characters: backslash + n.
    text = text.replace("\\n", "\n")
    text = text.replace("\\\"", "\"")

    # Remove markdown code fences and backticks.
    text = text.replace("```", "")
    text = text.replace("`", "")

    # Finally remove all backslashes and quotes to avoid \\ / \" differences.
    text = text.replace("\\", "")
    text = text.replace("\"", "")

    # Collapse all whitespace to one space.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_reactions_after_injection(log_path: Path) -> List[Dict[str, Any]]:
    """
    Extract from a single AgentDojo log JSON:
    - each injection text
    - the first assistant text after the model sees the injection
    - the first tool_call in that assistant message, if any
    """
    if not log_path.exists():
        print(f"[Extractor] Log file not found: {log_path}")
        return []

    with open(log_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    injections: Dict[str, str] = data.get("injections", {}) or {}
    messages: List[Dict[str, Any]] = data.get("messages", []) or []

    results: List[Dict[str, Any]] = []

    if not injections or not messages:
        print("[Extractor] No injections or messages in log.")
        return results

    # Iterate over each injection.
    for inj_name, inj_text in injections.items():
        inj_text = inj_text or ""
        if not inj_text:
            continue

        # Pre-normalize the injection once to avoid recomputing for every message.
        inj_norm = _normalize_for_match(inj_text)
        if not inj_norm:
            continue

        trigger_idx: Optional[int] = None

        # 1) Find the first message containing the injection text after normalization.
        for i, msg in enumerate(messages):
            contents = msg.get("content") or []
            for part in contents:
                if part.get("type") != "text":
                    continue
                txt = part.get("content", "")
                txt_norm = _normalize_for_match(txt)

                if inj_norm in txt_norm:
                    trigger_idx = i
                    break
            if trigger_idx is not None:
                break

        if trigger_idx is None:
            print(f"[Extractor] Injection '{inj_name}' text not found in messages.")
            continue

        # 2) Find the first assistant message after trigger_idx.
        assistant_idx: Optional[int] = None
        assistant_msg: Optional[Dict[str, Any]] = None

        for j in range(trigger_idx + 1, len(messages)):
            msg = messages[j]
            if msg.get("role") == "assistant":
                assistant_idx = j
                assistant_msg = msg
                break

        if assistant_msg is None:
            print(f"[Extractor] No assistant reaction found after injection '{inj_name}'.")
            continue

        # 3) Join all text content from that assistant message.
        assistant_contents = assistant_msg.get("content") or []
        assistant_text_parts = [
            part.get("content", "")
            for part in assistant_contents
            if part.get("type") == "text"
        ]
        assistant_text = "\n".join(assistant_text_parts).strip()

        # 4) Take the first tool_call, if any.
        tool_calls = assistant_msg.get("tool_calls") or []
        first_tool_call = tool_calls[0] if tool_calls else None

        results.append(
            {
                "injection_name": inj_name,
                "injection_text": inj_text,
                "trigger_message_index": trigger_idx,
                "assistant_index": assistant_idx,
                "assistant_text": assistant_text,
                "assistant_first_tool_call": first_tool_call,
            }
        )

    return results

def extract_call_chain_after_injection(log_path: Path):
    """
    Extract all tool_calls triggered by the assistant after each injection is seen
    in an AgentDojo log.

    Returns a list where each item has this structure:
    {
        "injection_name": ...,
        "injection_text": ...,
        "trigger_message_index": ...,
        "call_chain": [
            {
                "assistant_index": j,
                "tool_calls": [...]
            },
            ...
        ]
    }
    """
    if not log_path.exists():
        print(f"[Extractor] Log file not found: {log_path}")
        return []

    with open(log_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    injections = data.get("injections") or {}
    messages = data.get("messages") or []

    results = []

    for inj_name, inj_text in injections.items():
        inj_text = inj_text or ""
        if not inj_text:
            continue

        inj_norm = _normalize_for_match(inj_text)
        if not inj_norm:
            continue

        # --- Find the trigger position: the first message containing the injection.
        trigger_idx = None
        for i, msg in enumerate(messages):
            contents = msg.get("content") or []
            for part in contents:
                if part.get("type") != "text":
                    continue
                txt_norm = _normalize_for_match(part.get("content", ""))
                if inj_norm in txt_norm:
                    trigger_idx = i
                    break
            if trigger_idx is not None:
                break

        if trigger_idx is None:
            print(f"[Extractor] Injection '{inj_name}' not found in messages.")
            continue

        # --- Collect assistant tool_calls after the trigger.
        call_chain = []
        for j in range(trigger_idx + 1, len(messages)):
            msg = messages[j]
            role = msg.get("role")

            if role == "user":
                # A user message marks the end of this agent reaction chain.
                break

            if role == "assistant":
                tool_calls = msg.get("tool_calls") or []
                if tool_calls:
                    call_chain.append(tool_calls[0])

        results.append(
            {
                "injection_name": inj_name,
                "injection_text": inj_text,
                "trigger_message_index": trigger_idx,
                "call_chain": call_chain,
            }
        )

    return results

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("log_path", type=Path)
    args = parser.parse_args()
    log_path = args.log_path
    res = extract_reactions_after_injection(log_path)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    res = extract_call_chain_after_injection(log_path)
    print(json.dumps(res, ensure_ascii=False, indent=2))
