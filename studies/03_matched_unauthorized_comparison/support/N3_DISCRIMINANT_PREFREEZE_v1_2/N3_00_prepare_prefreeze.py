#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from n3_common import *

def main():
    ap=argparse.ArgumentParser(description="Build N3 zero-call prefreeze draft from exact frozen A14 artifacts")
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--out", default="N3_PREFREEZE_AUTHOR_v1")
    args=ap.parse_args()
    root=Path(args.project_root).resolve(); out=(root/args.out).resolve()
    if out.exists():
        raise SystemExit(f"FATAL: output exists; refuse overwrite: {out}")
    obj=build_prefreeze_objects(root)
    out.mkdir(parents=True)
    dump_json(out/"N3_PROTOCOL_DRAFT.json", obj["protocol_draft"])
    dump_json(out/"N3_BASE_PROJECTION.json", {"schema_version":SCHEMA_VERSION,"bases":obj["alt_map"]})
    dump_jsonl(out/"N3_BASELINE_A14_UNITS.jsonl", obj["baseline_units"])
    dump_jsonl(out/"N3_POSITIVE_CONTEXTS.jsonl", obj["positive_contexts"])
    dump_jsonl(out/"N3_POSITIVE_SCORING_UNITS.jsonl", obj["positive_units"])
    dump_jsonl(out/"N3_HUMAN_AUDIT_TEMPLATE.jsonl", obj["audit_template"])
    dump_json(out/"N3_MECHANICAL_CHECKS.json", obj["mechanical_checks"])
    hashes={p.name:sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()}
    dump_json(out/"N3_PREFREEZE_DRAFT_MANIFEST.json", {"schema_version":SCHEMA_VERSION,"status":"DRAFT_READY_HUMAN_AUDIT_REQUIRED","scientific_model_calls":0,"files":hashes})
    print("N3 PREFREEZE PREPARATION PASS")
    print(f"out={out}")
    print("bases=24 baseline_units=96 positive_contexts=96 positive_scoring_units=192")
    print("scientific_model_calls=0")
    print("NEXT: run N3_01_human_audit_cli.py; DO NOT RUN SCIENCE")
if __name__=='__main__': main()
