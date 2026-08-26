#!/usr/bin/env python3
"""Synthetic-only preflight for the frozen AW-N3 AgentWatcher configuration."""
from __future__ import annotations

import argparse
import importlib.util
import json
import time
import urllib.request
from pathlib import Path

from awn3_common import *


def http_json(base, path, payload=None, timeout=300):
    url = base.rstrip("/") + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer x"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def load_get_message2(repo: Path):
    p = repo / "src" / "defenses" / "monitor_llm_module" / "messages.py"
    spec = importlib.util.spec_from_file_location("awn3_aw_messages", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.get_message2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--run-dir", default="AW_N3_AUTHOR_v1")
    ap.add_argument("--monitor-base-url", default="http://localhost:8120/v1")
    args = ap.parse_args()

    paths = project_paths(Path(args.project_root), Path(args.run_dir))
    root, out, repo = paths["root"], paths["run"], paths["aw_repo"]
    validate_parent_sources(root)
    freeze_path = out / "AWN3_FREEZE.json"
    require_file(freeze_path)
    freeze = read_json(freeze_path)

    if (out / "AWN3_SCIENCE_UNIQUE_OUTPUTS.jsonl").exists():
        raise SystemExit("FATAL: scientific outputs already exist; preflight is no longer pre-outcome")

    ids = [x.get("id") for x in http_json(args.monitor_base_url, "/models").get("data", [])]
    if AW_MONITOR_ADAPTER not in ids:
        raise SystemExit(
            "FATAL: monitor endpoint does not expose exact frozen adapter\n"
            f"expected={AW_MONITOR_ADAPTER}\nserved={ids}"
        )

    get_message2 = load_get_message2(repo)
    msgs = get_message2(
        "Summarize the supplied weather report.",
        "The report says it will be sunny tomorrow.",
        'summarize_report({"day":"tomorrow"})',
    )
    r = http_json(
        args.monitor_base_url,
        "/chat/completions",
        {
            "model": AW_MONITOR_ADAPTER,
            "messages": msgs,
            "temperature": MONITOR_TEMPERATURE,
            "max_tokens": 512,
        },
    )
    raw = (r["choices"][0]["message"]["content"] or "").strip()
    if not raw:
        raise SystemExit("FATAL: frozen monitor returned empty synthetic output")
    parsed = parse_monitor_output(raw)
    if not parsed["parse_ok"]:
        raise SystemExit(f"FATAL: synthetic monitor output does not satisfy frozen parser: {raw!r}")
    print("[AWN3-02] monitor synthetic self-test PASS")

    # Exact frozen attribution source + revision on synthetic text only.
    aw = load_official_agentwatcher_module(repo)
    attr_path = frozen_hf_snapshot(AW_ATTRIBUTION_MODEL, AW_ATTRIBUTION_REVISION)
    t0 = time.time()
    windows, _, intervals, _ = aw.attribute(
        "You are a helpful assistant.",
        "Summarize the supplied weather report.",
        "The report says it will be sunny tomorrow.",
        'summarize_report({"day":"tomorrow"})',
        w_s=AW_W_S,
        w_l=AW_W_L,
        w_r=AW_W_R,
        K=AW_K,
        attribution_model=attr_path,
    )
    if not windows or not intervals:
        raise SystemExit("FATAL: official AgentWatcher attribution synthetic test returned no window")
    print(f"[AWN3-02] attribution synthetic self-test PASS ({time.time()-t0:.2f}s)")

    pf = {
        "schema": "AWN3_PREFLIGHT_V1_2026-08-19",
        "freeze_sha256": freeze["freeze_sha256"],
        "monitor_base_url": args.monitor_base_url,
        "monitor_model": AW_MONITOR_ADAPTER,
        "served_model_ids": ids,
        "monitor_synthetic_output_sha256": sha256_bytes(raw.encode("utf-8")),
        "monitor_parser_ok": True,
        "attribution_model": AW_ATTRIBUTION_MODEL,
        "attribution_revision": AW_ATTRIBUTION_REVISION,
        "attribution_snapshot_path": str(attr_path),
        "completed_at_utc": now_utc(),
        "no_scientific_inputs_used": True,
        "no_scientific_outcomes_generated": True,
    }
    write_json(out / "AWN3_PREFLIGHT.json", pf)
    print("[AWN3-02] PREFLIGHT PASS; NO scientific N3 inputs used")
    print(f"[AWN3-02] preflight_sha256={sha256_file(out / 'AWN3_PREFLIGHT.json')}")


if __name__ == "__main__":
    main()
