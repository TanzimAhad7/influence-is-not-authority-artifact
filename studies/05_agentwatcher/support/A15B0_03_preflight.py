#!/usr/bin/env python3
"""
Outcome-free AgentWatcher paired-trace preflight.

This may load/query the pinned models, but it uses only synthetic self-test text,
never A14/A13 scientific inputs.
"""
from __future__ import annotations
import argparse
import importlib
import importlib.util
import json
import sys
import time
import types
import urllib.request
from pathlib import Path

from a15b0_common import *

def http_json(base, path, payload=None):
    url = base.rstrip("/") + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type":"application/json","Authorization":"Bearer x"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=240) as r:
        return json.loads(r.read().decode("utf-8"))

def load_aw_attribute(repo):
    # Load only the official pinned AgentWatcher module under the isolated
    # package namespace implemented in a15b0_common.py.
    return load_official_agentwatcher_module(repo).attribute

def load_get_message2(repo):
    p = repo / "src" / "defenses" / "monitor_llm_module" / "messages.py"
    spec = importlib.util.spec_from_file_location("a15b0_aw_messages", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.get_message2

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor-base-url", default="http://localhost:8120/v1")
    ap.add_argument("--repo-dir", default="external/AgentWatcher")
    ap.add_argument("--skip-attribution-load", action="store_true",
                    help="Only check source+monitor endpoint; does not validate attribution model load.")
    args = ap.parse_args()

    proto_path = OUT_DIR / "protocol.json"
    if not proto_path.is_file():
        sys.exit("FATAL: A15b-0 is not frozen. Run A15B0_02_freeze_protocol.py first.")
    proto = read_json(proto_path)
    sl = read_json(OUT_DIR / "source_lock.json")

    repo = PROJECT_ROOT / args.repo_dir
    got_head = git(["rev-parse","HEAD"], cwd=repo)
    if got_head != sl["agentwatcher"]["git_head"]:
        sys.exit(f"FATAL: AgentWatcher HEAD drift: {got_head} != {sl['agentwatcher']['git_head']}")

    ids = [x.get("id") for x in http_json(args.monitor_base_url, "/models").get("data", [])]
    if AW_MONITOR_ADAPTER not in ids:
        sys.exit(
            "FATAL: monitor endpoint does not expose the exact frozen adapter id.\n"
            f"expected={AW_MONITOR_ADAPTER}\nserved={ids}"
        )

    get_message2 = load_get_message2(repo)
    msgs = get_message2(
        "Summarize the supplied weather report.",
        "The report says it will be sunny tomorrow.",
        "summarize_report({\"day\":\"tomorrow\"})",
    )
    r = http_json(
        args.monitor_base_url, "/chat/completions",
        {
            "model": AW_MONITOR_ADAPTER,
            "messages": msgs,
            "temperature": 0,
            "max_tokens": 512,
        },
    )
    out = (r["choices"][0]["message"]["content"] or "").strip()
    if not out:
        sys.exit("FATAL: frozen monitor returned empty self-test output")
    print("[A15B0-03] monitor synthetic self-test PASS")

    if not args.skip_attribution_load:
        attr = load_aw_attribute(repo)
        attribution_model_path = frozen_attribution_model_path()
        # This calls the official attribution on benign synthetic text only,
        # with the exact HF revision bound by source_lock.json.
        t0 = time.time()
        windows, _, intervals, _ = attr(
            "You are a helpful assistant.",
            "Summarize the supplied weather report.",
            "The report says it will be sunny tomorrow.",
            "summarize_report({\"day\":\"tomorrow\"})",
            w_s=AW_W_S, w_l=AW_W_L, w_r=AW_W_R, K=AW_K,
            attribution_model=attribution_model_path,
        )
        if not windows or not intervals:
            sys.exit("FATAL: official AgentWatcher attribution synthetic self-test returned no window")
        print(f"[A15B0-03] attribution synthetic self-test PASS ({time.time()-t0:.2f}s)")

    write_json(
        OUT_DIR / "PREFLIGHT.json",
        {
            "schema_version":"A15B0_PREFLIGHT_V1",
            "protocol_hash": proto["protocol_hash"],
            "monitor_base_url": args.monitor_base_url,
            "monitor_model": AW_MONITOR_ADAPTER,
            "monitor_synthetic_output_sha256": sha256_bytes(out.encode("utf-8")),
            "attribution_checked": not args.skip_attribution_load,
            "attribution_revision": sl["models"]["attribution"]["revision"],
            "attribution_resolution": "exact source_lock HF revision via snapshot_download",
            "completed_at_utc": now_utc(),
            "no_scientific_inputs_used": True,
            "no_scientific_outcomes_generated": True,
        }
    )
    print("[A15B0-03] PREFLIGHT PASS; NO scientific A14/A13 outcomes emitted")

if __name__ == "__main__":
    main()
