#!/usr/bin/env python3
"""Pre-R2 server smoke test.

Checks:
1) expected Llama model is served;
2) OpenAI-style automatic tool calling works;
3) boundary-safe explicit-token /completions scoring still works.

This does NOT run AgentDojo or produce scientific outcomes.
"""

import hashlib
import json
import sys
import urllib.request

from transformers import AutoTokenizer

BASE = "http://localhost:8110/v1"
MODEL = "meta-llama/Llama-3.3-70B-Instruct"
KEY = "x"
TIMEOUT = 180


def call(path, payload=None):
    req = urllib.request.Request(
        BASE + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def ids_hash(ids):
    return hashlib.sha256(
        json.dumps(list(map(int, ids)), separators=(",", ":")).encode()
    ).hexdigest()


print("A13-R2 LLAMA SERVER PREFLIGHT")

models = call("/models")
ids = [x.get("id") for x in models.get("data", [])]
if MODEL not in ids:
    sys.exit(f"FAIL: expected {MODEL}, got {ids}")
print("[1/3] model endpoint PASS")

tool_payload = {
    "model": MODEL,
    "messages": [
        {
            "role": "user",
            "content": "Use the multiply tool to calculate 7 times 6. Do not calculate it yourself."
        }
    ],
    "tools": [
        {
            "type": "function",
            "function": {
                "name": "multiply",
                "description": "Multiply two integers.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer"},
                        "b": {"type": "integer"}
                    },
                    "required": ["a", "b"],
                    "additionalProperties": False
                }
            }
        }
    ],
    "tool_choice": "auto",
    "temperature": 0,
    "max_tokens": 128,
}
d = call("/chat/completions", tool_payload)
msg = d["choices"][0]["message"]
calls = msg.get("tool_calls") or []
if not calls:
    sys.exit("FAIL: chat/completions returned no parsed tool_calls")
fn = calls[0].get("function") or {}
if fn.get("name") != "multiply":
    sys.exit(f"FAIL: parsed unexpected tool: {fn}")
args = fn.get("arguments")
if isinstance(args, str):
    args = json.loads(args)
try:
    normalized_args = {
        "a": int(args["a"]),
        "b": int(args["b"]),
    }
except Exception:
    sys.exit(f"FAIL: unexpected multiply arguments: {args!r}")

if normalized_args != {"a": 7, "b": 6}:
    sys.exit(f"FAIL: unexpected multiply arguments: {args!r}")

print(f"[2/3] parsed automatic tool calling PASS (raw args={args!r})")

tok = AutoTokenizer.from_pretrained(MODEL, local_files_only=True, use_fast=True)
completion = 'multiply({"a":7,"b":6})'
completion_ids = tok.encode(completion, add_special_tokens=False)
if not completion_ids:
    sys.exit("FAIL: completion tokenization empty")

hashes = []
scores = []
for prompt in [
    "user: calculate the product\nassistant: ",
    "user: please use the available information to calculate the product\nassistant: ",
]:
    prompt_ids = tok.encode(prompt, add_special_tokens=True)
    all_ids = prompt_ids + completion_ids
    res = call("/completions", {
        "model": MODEL,
        "prompt": all_ids,
        "add_special_tokens": False,
        "max_tokens": 0,
        "echo": True,
        "logprobs": 1,
        "temperature": 0,
        "return_tokens_as_token_ids": True,
    })
    vals = res["choices"][0]["logprobs"]["token_logprobs"]
    if len(vals) != len(all_ids):
        sys.exit(
            f"FAIL: echoed token-logprob count {len(vals)} != input count {len(all_ids)}"
        )
    selected = vals[len(prompt_ids):]
    if len(selected) != len(completion_ids) or any(v is None for v in selected):
        sys.exit("FAIL: exact completion suffix was not scoreable")
    hashes.append(ids_hash(completion_ids))
    scores.append(sum(float(v) for v in selected))

if len(set(hashes)) != 1:
    sys.exit("FAIL: completion token IDs changed across prompts")
print(
    f"[3/3] boundary-safe scorer PASS "
    f"({len(completion_ids)} fixed tokens; sha256={hashes[0][:16]}...)"
)

print("\nR2 SERVER PREFLIGHT PASS")
print("Do not run the benchmark until the frozen A13_R2_Llama.py protocol also validates.")
