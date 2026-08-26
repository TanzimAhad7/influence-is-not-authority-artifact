#!/usr/bin/env python3
"""
A15a-01 — execute the FROZEN sanitizer job list.

Requires:
  export OPENROUTER_API_KEY='...'

This script never changes eligibility, tau, or the job list.
It checkpoints after every completed call and is safe to resume.
"""
from __future__ import annotations
import json, os, sys, time, urllib.request, urllib.error, datetime as dt
from pathlib import Path
from a15a_common import *

PROTOCOL_PATH = OUT_DIR / "protocol.json"
JOBS_PATH = OUT_DIR / "sanitizer_jobs.jsonl"
OUT_PATH = OUT_DIR / "sanitizer_results.jsonl"
CHECKPOINT_PATH = OUT_DIR / "sanitizer_checkpoint.jsonl"

def load_dotenv_key(name: str) -> str | None:
    # Prefer an already-exported environment variable.
    value = os.environ.get(name)
    if value:
        return value

    # Otherwise load from ~/ratchet/phase0_pilot/.env
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return None

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        k, v = line.split("=", 1)
        if k.strip() != name:
            continue

        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]

        return v

    return None


def api_call(system_prompt: str, user_prompt: str):
    key = load_dotenv_key("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError(
            "OPENROUTER_API_KEY was not found in the environment or .env"
        )
    payload = {
        "model": SANITIZER_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        SANITIZER_BASE_URL + "/chat/completions",
        data=data,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read()
            status = getattr(resp, "status", 200)
    except urllib.error.HTTPError as e:
        raw = e.read()
        raise RuntimeError(f"HTTP {e.code}: {raw[:1000]!r}") from e
    latency = time.perf_counter() - t0
    obj = json.loads(raw.decode("utf-8"))
    text = obj["choices"][0]["message"]["content"]
    return text, latency, obj, status

def load_done():
    done = {}
    if CHECKPOINT_PATH.exists():
        for r in read_jsonl(CHECKPOINT_PATH):
            done[r["job_id"]] = r
    return done

def append_jsonl(path: Path, row: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        f.flush()
        os.fsync(f.fileno())

def main():
    if not PROTOCOL_PATH.exists():
        sys.exit("FATAL: run A15a_00_prepare_freeze.py first.")
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    if protocol["sanitizer"]["job_list_sha256"] != sha256_file(JOBS_PATH):
        sys.exit("FATAL: sanitizer job list hash differs from frozen protocol.")

    # Verify parent A13 files have not changed.
    for rel, expected in protocol["parent_a13"]["parent_hashes"].items():
        p = PROJECT_ROOT / rel
        if not p.exists() or sha256_file(p) != expected:
            sys.exit(f"FATAL parent drift: {rel}")

    jobs = read_jsonl(JOBS_PATH)
    done = load_done()
    print(f"[A15a-01] frozen jobs={len(jobs)} already_done={len(done)}")
    print(f"[A15a-01] protocol={protocol['protocol_hash']}")
    print(f"[A15a-01] sanitizer={SANITIZER_MODEL} via {SANITIZER_PROVIDER}")

    for idx, j in enumerate(jobs, 1):
        if j["job_id"] in done:
            continue
        print(f"[{idx:03d}/{len(jobs):03d}] sanitize {j['job_id']}")
        try:
            text, latency, raw_obj, status = api_call(j["system_prompt"], j["user_prompt"])
            usage = raw_obj.get("usage") or {}
            row = {
                "job_id": j["job_id"],
                "decision_id": j["decision_id"],
                "suite": j["suite"],
                "user_task": j["user_task"],
                "task_key": j["task_key"],
                "label": j["label"],
                "span_local_index": j["span_local_index"],
                "span_message_index": j["span_message_index"],
                "tool_name": j["tool_name"],
                "prompt_sha256": j["prompt_sha256"],
                "untrusted_content_sha256": sha256_text(j["untrusted_content"]),
                "sanitized_text": text,
                "sanitized_text_sha256": sha256_text(text),
                "latency_seconds": latency,
                "http_status": status,
                "usage": usage,
                "provider_model_returned": raw_obj.get("model"),
                "request_id": raw_obj.get("id"),
                "completed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "error": None,
            }
        except Exception as e:
            row = {
                "job_id": j["job_id"],
                "decision_id": j["decision_id"],
                "suite": j["suite"],
                "user_task": j["user_task"],
                "task_key": j["task_key"],
                "label": j["label"],
                "span_local_index": j["span_local_index"],
                "span_message_index": j["span_message_index"],
                "tool_name": j["tool_name"],
                "prompt_sha256": j["prompt_sha256"],
                "completed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "error": f"{type(e).__name__}: {e}",
            }
            append_jsonl(CHECKPOINT_PATH, row)
            print(f"  ERROR: {row['error']}")
            sys.exit("Stopped on first sanitizer error; fix provider issue and rerun to resume.")

        append_jsonl(CHECKPOINT_PATH, row)
        done[j["job_id"]] = row
        print(f"  latency={latency:.3f}s chars={len(text)}")

    rows = [done[j["job_id"]] for j in jobs if j["job_id"] in done]
    if len(rows) != len(jobs) or any(r.get("error") for r in rows):
        sys.exit("FATAL: incomplete/error sanitizer rows; final file not written.")
    write_jsonl(OUT_PATH, rows)
    print(f"[A15a-01] COMPLETE: {len(rows)}/{len(jobs)} sanitizer jobs.")
    print(f"[A15a-01] Raw: {OUT_PATH}")

if __name__ == "__main__":
    main()
