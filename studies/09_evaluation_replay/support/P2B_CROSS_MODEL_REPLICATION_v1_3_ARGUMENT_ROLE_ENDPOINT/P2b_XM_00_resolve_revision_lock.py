#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import HfApi, get_token

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def stable_json(obj) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--hf-token", default=os.getenv("HF_TOKEN"))
    args = ap.parse_args()

    token = args.hf_token or get_token()
    api = HfApi(token=token)

    model_ids = {
        "llama": "meta-llama/Llama-3.3-70B-Instruct",
        "gemma": "google/gemma-3-12b-it",
        "qwen_canonical": "Qwen/Qwen2.5-72B-Instruct",
    }

    models = {}
    for key, model_id in model_ids.items():
        info = api.model_info(model_id, revision="main")
        if not info.sha:
            raise SystemExit(f"FATAL could not resolve immutable revision for {model_id}")
        models[key] = {
            "model_id": model_id,
            "resolved_from": "main",
            "revision": str(info.sha),
            "tokenizer_revision": str(info.sha),
        }
        print(f"REVISION {key} {model_id} {info.sha}", flush=True)

    obj = {
        "schema": "P2B_XMODEL_REVISION_LOCK_V1_3",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "models": models,
        "rule": "Immutable model/tokenizer revisions resolved once before any v1.2 scientific model outcome.",
    }
    obj["lock_sha256"] = sha256_bytes(stable_json(obj))
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(json.dumps(obj, indent=2, sort_keys=True).encode() + b"\n")
    print(f"REVISION LOCK PASS sha256={obj['lock_sha256']}", flush=True)
    print(f"out={out}", flush=True)

if __name__ == "__main__":
    main()
