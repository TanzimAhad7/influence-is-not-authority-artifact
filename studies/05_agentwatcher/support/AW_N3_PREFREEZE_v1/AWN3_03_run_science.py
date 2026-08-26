#!/usr/bin/env python3
"""Run the frozen full AgentWatcher AW-N3 science once over the 96 unique static inputs."""
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


def selected_context_metadata(aw_mod, full_context, intervals, tool_segments):
    tok = aw_mod.tokenizer
    char_intervals = []
    try:
        enc = tok(full_context, add_special_tokens=True, return_offsets_mapping=True)
        offs = enc["offset_mapping"][1:]  # official attribute() drops first context token
        for a, b in intervals:
            use = [x for x in offs[a:b] if x and x != (0, 0)]
            if use:
                char_intervals.append((min(x[0] for x in use), max(x[1] for x in use)))
            else:
                char_intervals.append((None, None))
    except Exception:
        char_intervals = [(None, None) for _ in intervals]

    tool_ranges = []
    pos = 0
    for i, s in enumerate(tool_segments):
        if i:
            pos += 2
        start = pos
        pos += len(s["content"])
        tool_ranges.append((start, pos))

    tool_overlap = []
    for tr in tool_ranges:
        hit = any(
            a is not None and max(a, tr[0]) < min(b, tr[1])
            for a, b in char_intervals
        )
        tool_overlap.append(hit)

    return {
        "selected_char_intervals": [list(x) for x in char_intervals],
        "tool_segment_selected_overlap": tool_overlap,
        "any_tool_segment_selected": any(tool_overlap),
    }


def run_one(aw_mod, get_message2, row, monitor_base_url, attribution_model_path, freeze_hash):
    t0 = time.time()
    windows, _, intervals, _ = aw_mod.attribute(
        "You are a helpful assistant.",
        row["target_task"],
        row["external_context"],
        row["target_action_text"],
        w_s=AW_W_S,
        w_l=AW_W_L,
        w_r=AW_W_R,
        K=AW_K,
        attribution_model=attribution_model_path,
    )
    t1 = time.time()
    selected = "\n\n".join(windows)
    msgs = get_message2(row["target_task"], selected, row["target_action_text"])
    resp = http_json(
        monitor_base_url,
        "/chat/completions",
        {
            "model": AW_MONITOR_ADAPTER,
            "messages": msgs,
            "temperature": MONITOR_TEMPERATURE,
            "max_tokens": MONITOR_MAX_TOKENS,
        },
    )
    t2 = time.time()
    raw = (resp["choices"][0]["message"]["content"] or "").strip()
    parsed = parse_monitor_output(raw)

    selected_norm = normalize_for_match(selected)
    target_value_recall = {
        str(v): normalize_for_match(v) in selected_norm
        for v in sorted(set(scalar_leaves((row.get("target_action") or {}).get("args") or {})))
    }
    meta = selected_context_metadata(
        aw_mod,
        row["external_context"],
        intervals,
        row["tool_segments"],
    )

    return {
        "schema": "AWN3_SCIENCE_OUTPUT_V1_2026-08-19",
        "execution_index": row["execution_index"],
        "base_id": row["base_id"],
        "family": row["family"],
        "directive_arm": row["directive_arm"],
        "action_role": row["action_role"],
        "state": row["state"],
        "oracle_status": row["oracle_status"],
        "agentwatcher_static_input_sha256": row["agentwatcher_static_input_sha256"],
        "mapped_unit_ids": row.get("mapped_unit_ids") or [row["unit_id"]],
        "mapped_descendants": row.get("mapped_descendants") or [row["descendant"]],
        "detect_flag": parsed["detect_flag"],
        "monitor_parse_ok": parsed["parse_ok"],
        "selected_windows_text": list(windows),
        "selected_windows_token_intervals": [list(x) for x in intervals],
        **meta,
        "target_action_value_recall": target_value_recall,
        "all_target_action_values_recalled": all(target_value_recall.values()) if target_value_recall else None,
        "monitor_messages_sha256": stable_hash(msgs),
        "monitor_output": raw,
        "monitor_output_sha256": sha256_bytes(raw.encode("utf-8")),
        "attribution_runtime_s": t1 - t0,
        "monitor_runtime_s": t2 - t1,
        "total_detector_runtime_s": t2 - t0,
        "freeze_sha256": freeze_hash,
    }


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
    preflight_path = out / "AWN3_PREFLIGHT.json"
    exec_path = out / "AWN3_EXECUTION_INPUTS.jsonl"
    require_file(freeze_path)
    require_file(preflight_path)
    require_file(exec_path)
    freeze = read_json(freeze_path)
    pf = read_json(preflight_path)
    if pf.get("freeze_sha256") != freeze.get("freeze_sha256"):
        raise SystemExit("FATAL: preflight/freeze mismatch")

    rows = read_jsonl(exec_path)
    if len(rows) != 96:
        raise SystemExit(f"FATAL: frozen execution denominator drift: {len(rows)} != 96")

    # Exact frozen order is the static-hash order. Add an explicit index without changing content identity.
    hashes = [r["agentwatcher_static_input_sha256"] for r in rows]
    if hashes != sorted(hashes) or len(set(hashes)) != 96:
        raise SystemExit("FATAL: execution input order/uniqueness drift")
    for i, r in enumerate(rows, 1):
        r["execution_index"] = i

    outpath = out / "AWN3_SCIENCE_UNIQUE_OUTPUTS.jsonl"
    if outpath.exists():
        raise SystemExit(f"FATAL: {outpath} already exists. Do not overwrite or rerun scientific outcomes.")

    ids = [x.get("id") for x in http_json(args.monitor_base_url, "/models").get("data", [])]
    if AW_MONITOR_ADAPTER not in ids:
        raise SystemExit(f"FATAL: exact frozen monitor adapter not served: {ids}")

    aw_mod = load_official_agentwatcher_module(repo)
    get_message2 = load_get_message2(repo)
    attr_path = frozen_hf_snapshot(AW_ATTRIBUTION_MODEL, AW_ATTRIBUTION_REVISION)

    outs = []
    run_started = now_utc()
    for i, row in enumerate(rows, 1):
        z = run_one(
            aw_mod,
            get_message2,
            row,
            args.monitor_base_url,
            attr_path,
            freeze["freeze_sha256"],
        )
        outs.append(z)
        print(
            f"[{i:03d}/{len(rows):03d}] {z['base_id']} {z['state']} "
            f"flag={z['detect_flag']} parse={z['monitor_parse_ok']} "
            f"t={z['total_detector_runtime_s']:.2f}s",
            flush=True,
        )

    # Final scientific output is created only after all 96 calls return.
    write_jsonl(outpath, outs)
    run_complete = {
        "schema": "AWN3_SCIENCE_RUN_COMPLETE_V1_2026-08-19",
        "freeze_sha256": freeze["freeze_sha256"],
        "execution_input_sha256": sha256_file(exec_path),
        "science_output_sha256": sha256_file(outpath),
        "n_unique_scientific_calls": len(outs),
        "n_parse_ok": sum(bool(x["monitor_parse_ok"]) for x in outs),
        "n_parse_fail": sum(not bool(x["monitor_parse_ok"]) for x in outs),
        "monitor_model": AW_MONITOR_ADAPTER,
        "attribution_model": AW_ATTRIBUTION_MODEL,
        "attribution_revision": AW_ATTRIBUTION_REVISION,
        "started_at_utc": run_started,
        "completed_at_utc": now_utc(),
        "no_automatic_retries": True,
        "complete": True,
    }
    write_json(out / "AWN3_SCIENCE_RUN_COMPLETE.json", run_complete)

    print("[AWN3-03] SCIENCE RUN COMPLETE")
    print(f"[AWN3-03] unique_calls={len(outs)} parse_ok={run_complete['n_parse_ok']} parse_fail={run_complete['n_parse_fail']}")
    print(f"[AWN3-03] output={outpath}")
    print(f"[AWN3-03] output_sha256={sha256_file(outpath)}")
    print("[AWN3-03] STOP: run analysis/verification; do not start CV2 yet")


if __name__ == "__main__":
    main()
