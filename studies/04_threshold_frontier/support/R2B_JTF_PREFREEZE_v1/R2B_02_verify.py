#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

SCHEMA = "R2B_JTF_V1_2026-08-19"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_csv(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--run-dir", default="R2B_JTF_AUTHOR_v1")
    args = ap.parse_args()
    root = Path(args.project_root).resolve()
    rd = root / args.run_dir

    required = [
        rd / "R2B_JTF_FREEZE.json",
        rd / "R2B_JTF_RESULTS.json",
        rd / "R2B_JTF_REPORT.md",
        rd / "R2B_JTF_FRONTIER_llama.csv",
        rd / "R2B_JTF_FRONTIER_gemma.csv",
        rd / "R2B_JTF_MANIFEST.json",
        rd / "RUN_COMPLETE.json",
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise SystemExit("FATAL missing outputs:\n" + "\n".join(missing))

    fr = read_json(rd / "R2B_JTF_FREEZE.json")
    res = read_json(rd / "R2B_JTF_RESULTS.json")
    man = read_json(rd / "R2B_JTF_MANIFEST.json")
    rc = read_json(rd / "RUN_COMPLETE.json")
    for obj, name in [(fr, "freeze"), (res, "results"), (man, "manifest"), (rc, "run_complete")]:
        if obj.get("schema") != SCHEMA:
            raise SystemExit(f"FATAL schema mismatch {name}")
    if res.get("freeze_sha256") != fr.get("freeze_sha256") or rc.get("freeze_sha256") != fr.get("freeze_sha256"):
        raise SystemExit("FATAL freeze lineage mismatch")
    if rc.get("results_sha256") != sha256_file(rd / "R2B_JTF_RESULTS.json"):
        raise SystemExit("FATAL results hash mismatch")
    if rc.get("report_sha256") != sha256_file(rd / "R2B_JTF_REPORT.md"):
        raise SystemExit("FATAL report hash mismatch")
    if rc.get("manifest_sha256") != sha256_file(rd / "R2B_JTF_MANIFEST.json"):
        raise SystemExit("FATAL manifest hash mismatch")
    if not rc.get("no_model_provider_calls"):
        raise SystemExit("FATAL no-model-call attestation missing")

    for name, expected in man.get("files", {}).items():
        p = rd / name
        if not p.exists() or sha256_file(p) != expected:
            raise SystemExit(f"FATAL manifest file mismatch {name}")

    for scorer in ("llama", "gemma"):
        rows = read_csv(rd / f"R2B_JTF_FRONTIER_{scorer}.csv")
        if not rows:
            raise SystemExit(f"FATAL empty frontier {scorer}")
        tau0 = [r for r in rows if r["threshold_label"] == "tau0"]
        if len(tau0) != 1:
            raise SystemExit(f"FATAL tau0 row count {scorer}={len(tau0)}")
        if len(rows) != res["scorers"][scorer]["n_threshold_rows"]:
            raise SystemExit(f"FATAL row-count mismatch {scorer}")
        if sha256_file(rd / f"R2B_JTF_FRONTIER_{scorer}.csv") != res["scorers"][scorer]["frontier_csv_sha256"]:
            raise SystemExit(f"FATAL frontier results hash mismatch {scorer}")

    verification = {
        "schema": SCHEMA,
        "status": "INTEGRITY_PASS",
        "run_dir": str(rd),
        "freeze_sha256": fr["freeze_sha256"],
        "results_sha256": sha256_file(rd / "R2B_JTF_RESULTS.json"),
        "manifest_sha256": sha256_file(rd / "R2B_JTF_MANIFEST.json"),
        "run_complete_sha256": sha256_file(rd / "RUN_COMPLETE.json"),
        "frontier_rows": {
            scorer: len(read_csv(rd / f"R2B_JTF_FRONTIER_{scorer}.csv")) for scorer in ("llama", "gemma")
        },
    }
    vp = rd / "VERIFY_REPORT.json"
    vp.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("[R2B-02] INTEGRITY PASS")
    print(f"[R2B-02] verify_report={vp}")
    print(f"[R2B-02] verify_report_sha256={sha256_file(vp)}")


if __name__ == "__main__":
    main()
