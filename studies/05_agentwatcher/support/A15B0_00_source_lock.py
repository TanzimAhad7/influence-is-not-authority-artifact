#!/usr/bin/env python3
"""
A15b-0 source lock.

NO benchmark/scientific outcomes are produced.

This pins:
- the exact official AgentWatcher Git checkout,
- exact Hugging Face revisions for the attribution model, monitor adapter, and its base,
- source-file hashes,
- the effective paper-reported AgentWatcher configuration.

Run before A15B0_01_prepare_inputs.py.
"""
from __future__ import annotations
import argparse
import ast
import json
import os
import re
import shutil
import sys
from pathlib import Path

from a15b0_common import *

def find_cli_default_k(main_path: Path):
    text = main_path.read_text(encoding="utf-8", errors="replace")
    # Robust enough for argparse.add_argument("--K", ..., default=<expr>)
    m = re.search(r'add_argument\(\s*["\']--K["\'](?P<body>.*?)\)', text, flags=re.S)
    if not m:
        return {"found": False, "default": None}
    body = m.group("body")
    dm = re.search(r'default\s*=\s*([^,\n]+)', body)
    raw = dm.group(1).strip() if dm else None
    try:
        val = ast.literal_eval(raw) if raw is not None else None
    except Exception:
        val = raw
    return {"found": True, "default": val, "raw": raw}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", action="store_true",
                    help="Clone official AgentWatcher into external/AgentWatcher if absent.")
    ap.add_argument("--repo-dir", default="external/AgentWatcher")
    args = ap.parse_args()

    repo = PROJECT_ROOT / args.repo_dir
    if not repo.exists():
        if not args.clone:
            sys.exit(
                f"FATAL: {repo} does not exist.\n"
                f"Run: python3 A15B0_00_source_lock.py --clone\n"
                "This clones the official repository before any scientific AgentWatcher outcomes."
            )
        repo.parent.mkdir(parents=True, exist_ok=True)
        git(["clone", AW_REPO_URL, str(repo)])

    if not (repo / ".git").exists():
        sys.exit(f"FATAL: {repo} is not a Git checkout. Use a fresh official clone for the source-fidelity lock.")

    remote = git(["config", "--get", "remote.origin.url"], cwd=repo)
    if "Wang-Yanting/AgentWatcher" not in remote:
        sys.exit(f"FATAL: unexpected AgentWatcher remote: {remote}")

    head = git(["rev-parse", "HEAD"], cwd=repo)
    status = git(["status", "--porcelain"], cwd=repo)
    if status.strip():
        sys.exit("FATAL: official AgentWatcher checkout has uncommitted changes. Freeze a clean checkout.")

    required = [
        "src/defenses/agentwatcher/defense_agentwatcher.py",
        "src/defenses/agentwatcher/attention_utils.py",
        "src/defenses/monitor_llm_module/messages.py",
        "src/llm.py",
        "main_agentdojo.py",
    ]
    repo_files = {}
    for rel in required:
        p = repo / rel
        if not p.is_file():
            sys.exit(f"FATAL: official AgentWatcher source missing: {rel}")
        repo_files[rel] = sha256_file(p)

    cli_k = find_cli_default_k(repo / "main_agentdojo.py")

    # Pre-outcome audit for the paper's "No attribution" ablation semantics.
    # We do not assume the exact implementation from the table label alone.
    no_attr_hits = []
    patterns = [
        re.compile(r"no[_ -]?attribution", re.I),
        re.compile(r"attribution[_ -]?method", re.I),
        re.compile(r"without[_ -]?attribution", re.I),
    ]
    for q in sorted(repo.rglob("*")):
        if not q.is_file() or q.suffix.lower() not in {".py", ".md", ".txt", ".sh", ".yaml", ".yml", ".json"}:
            continue
        try:
            lines = q.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for ln, line in enumerate(lines, 1):
            if any(rx.search(line) for rx in patterns):
                no_attr_hits.append({
                    "path": str(q.relative_to(repo)),
                    "line": ln,
                    "text": line.strip()[:500],
                })
                if len(no_attr_hits) >= 100:
                    break
        if len(no_attr_hits) >= 100:
            break

    try:
        from huggingface_hub import HfApi, hf_hub_download
    except Exception as e:
        sys.exit(
            "FATAL: huggingface_hub is required to freeze exact model revisions.\n"
            "Install it in the existing .venv, then rerun. Error: " + repr(e)
        )

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    api = HfApi(token=token)

    def info(repo_id):
        x = api.model_info(repo_id=repo_id)
        if not x.sha:
            raise RuntimeError(f"HF model_info returned no SHA for {repo_id}")
        return {"repo_id": repo_id, "revision": x.sha}

    attribution = info(AW_ATTRIBUTION_MODEL)
    adapter = info(AW_MONITOR_ADAPTER)

    adapter_cfg_path = hf_hub_download(
        repo_id=AW_MONITOR_ADAPTER,
        filename="adapter_config.json",
        revision=adapter["revision"],
        token=token,
    )
    adapter_cfg = json.loads(Path(adapter_cfg_path).read_text(encoding="utf-8"))
    base_id = adapter_cfg.get("base_model_name_or_path")
    if base_id != AW_MONITOR_EXPECTED_BASE:
        sys.exit(
            "FATAL: monitor adapter base-model drift.\n"
            f"  got={base_id!r}\n  expected={AW_MONITOR_EXPECTED_BASE!r}"
        )
    monitor_base = info(base_id)

    license_candidates = [p.name for p in repo.iterdir() if p.is_file() and p.name.lower().startswith(("license", "copying"))]

    lock = {
        "schema_version": "A15B0_SOURCE_LOCK_V1_2026-08-09",
        "created_at_utc": now_utc(),
        "agentwatcher": {
            "official_remote": remote,
            "git_head": head,
            "git_clean": True,
            "source_hashes": repo_files,
            "repo_license_files_visible": sorted(license_candidates),
            "cli_k_default_audit": cli_k,
            "no_attribution_source_audit": {
                "candidate_hits": no_attr_hits,
                "interpretation": (
                    "The paper's Table 4 label alone does not define exact ablation semantics. "
                    "These source hits are recorded pre-outcome so source correspondence can be audited "
                    "without inventing an implementation."
                ),
            },
        },
        "models": {
            "attribution": attribution,
            "monitor_adapter": adapter,
            "monitor_base": monitor_base,
            "monitor_adapter_base_from_config": base_id,
        },
        "primary_configuration": {
            "attribution_model": AW_ATTRIBUTION_MODEL,
            "monitor_adapter": AW_MONITOR_ADAPTER,
            "w_s": AW_W_S,
            "w_l": AW_W_L,
            "w_r": AW_W_R,
            "K": AW_K,
            "monitor_decoding": "greedy / temperature=0 in paired-trace harness",
        },
        "fidelity_note": (
            "Primary paired-trace runs explicitly set paper-reported K=3 and all attribution "
            "hyperparameters; released CLI defaults are never relied upon."
        ),
        "no_scientific_outcomes_generated": True,
    }
    lock["source_lock_hash"] = stable_hash({k: v for k, v in lock.items() if k != "created_at_utc"})

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "source_lock.json"
    if path.exists():
        old = read_json(path)
        if old.get("source_lock_hash") != lock["source_lock_hash"]:
            sys.exit(
                "FATAL: existing source_lock.json differs. Do not overwrite a pre-outcome source lock.\n"
                f"old={old.get('source_lock_hash')}\nnew={lock['source_lock_hash']}"
            )
        print(f"[A15B0-00] existing SOURCE LOCK verified: {lock['source_lock_hash']}")
    else:
        write_json(path, lock)
        print(f"[A15B0-00] SOURCE LOCK PASS: {lock['source_lock_hash']}")

    print(f"[A15B0-00] AgentWatcher HEAD={head}")
    print(f"[A15B0-00] attribution revision={attribution['revision']}")
    print(f"[A15B0-00] monitor adapter revision={adapter['revision']}")
    print(f"[A15B0-00] monitor base revision={monitor_base['revision']}")
    print(f"[A15B0-00] released CLI K default audit={cli_k.get('default')!r}; PRIMARY K is explicitly {AW_K}")
    print(f"[A15B0-00] no-attribution source-audit candidate hits={len(no_attr_hits)}")
    print("[A15B0-00] NO AgentWatcher benchmark/scientific outcomes generated")

if __name__ == "__main__":
    main()
