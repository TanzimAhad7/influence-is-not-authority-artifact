#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

import requests
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from canonical_json_adapter import canonicalize_history
from p2b_common import read_json, read_jsonl, sha256_file, write_json

def stable_sha(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()

def served_model(base_url: str, api_key: str) -> str:
    r = requests.get(
        base_url.rstrip("/") + "/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=20,
    )
    r.raise_for_status()
    ids = [x["id"] for x in r.json().get("data", [])]
    if len(ids) != 1:
        raise SystemExit(f"FATAL expected exactly one served model, got {ids}")
    return ids[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-key", required=True, choices=["llama","gemma","qwen_canonical"])
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--base-url", default="http://localhost:8100/v1")
    ap.add_argument("--api-key", default=os.getenv("P2B_API_KEY","EMPTY"))
    ap.add_argument("--revision-lock", required=True)
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()

    here = Path(__file__).resolve().parent
    reg = read_json(here / "MODEL_REGISTRY.json")
    cfg = reg["models"][args.model_key]
    lock = read_json(Path(args.revision_lock))
    lock_cfg = lock["models"][args.model_key]

    if cfg["model_id"] != lock_cfg["model_id"]:
        raise SystemExit("FATAL registry/revision-lock model mismatch")

    model = served_model(args.base_url, args.api_key)
    if model != cfg["model_id"]:
        raise SystemExit(f"FATAL served model mismatch expected={cfg['model_id']} got={model}")

    inv = read_jsonl(here / "inputs/P2B_REPLAY_INVENTORY.jsonl")
    if len(inv) != 26:
        raise SystemExit(f"FATAL expected 26 decisions, got {len(inv)}")

    project_root = Path(args.project_root).resolve()
    url = args.base_url.rstrip("/") + "/chat/completions/render"
    headers = {
        "Authorization": f"Bearer {args.api_key}",
        "Content-Type": "application/json",
    }

    results = []
    for row in sorted(inv, key=lambda x: x["decision_id"]):
        raw_path = project_root / row["raw_log_path"]
        if not raw_path.exists():
            raise SystemExit(f"FATAL missing raw log {raw_path}")
        got_raw_sha = sha256_file(raw_path)
        if got_raw_sha != row["raw_log_sha256"]:
            raise SystemExit(
                f"FATAL raw log hash drift {row['decision_id']}: "
                f"expected={row['raw_log_sha256']} got={got_raw_sha}"
            )

        raw = read_json(raw_path)
        prefix = list(raw.get("messages") or [])[: int(row["target_message_index"])]
        runtime = FunctionsRuntime(get_suite("v1", row["suite"]).tools)
        messages = canonicalize_history(prefix, runtime)

        # Local structural invariant before hitting the live tokenizer/chat template.
        conv_roles = [m["role"] for m in messages if m["role"] != "system"]
        if not conv_roles or conv_roles[0] != "user":
            raise SystemExit(f"FATAL local role-shape failure {row['decision_id']}: {conv_roles}")
        if any(a == b for a, b in zip(conv_roles, conv_roles[1:])):
            raise SystemExit(f"FATAL local non-alternation {row['decision_id']}: {conv_roles}")

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 0,
            "max_tokens": 1024,
            "stream": False,
        }
        req_sha = stable_sha(payload)
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        body = resp.content
        item = {
            "decision_id": row["decision_id"],
            "raw_log_path": row["raw_log_path"],
            "raw_log_sha256": got_raw_sha,
            "canonical_request_sha256": req_sha,
            "canonical_roles": [m["role"] for m in messages],
            "http_status": resp.status_code,
            "render_response_sha256": hashlib.sha256(body).hexdigest(),
            "render_response_bytes": len(body),
            "pass": resp.status_code == 200,
        }
        if resp.status_code != 200:
            item["error_body"] = body.decode("utf-8", errors="replace")[:4000]
        results.append(item)
        print(
            f"RENDER {args.model_key} {row['decision_id']} "
            f"status={resp.status_code} pass={item['pass']}",
            flush=True,
        )

    passed = len(results) == 26 and all(x["pass"] for x in results)
    outdir = Path(args.out_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    out = {
        "schema": "P2B_XMODEL_RENDER_PREFLIGHT_V1_3",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "model_key": args.model_key,
        "model_id": model,
        "revision_lock_sha256": lock["lock_sha256"],
        "render_endpoint": url,
        "decisions": 26,
        "passed": sum(x["pass"] for x in results),
        "pass": passed,
        "scientific_model_generations": 0,
        "results": results,
    }
    write_json(outdir / "P2B_RENDER_PREFLIGHT.json", out)
    print(f"RENDER PREFLIGHT {'PASS' if passed else 'FAIL'} {sum(x['pass'] for x in results)}/26", flush=True)
    if not passed:
        raise SystemExit(6)

if __name__ == "__main__":
    main()
