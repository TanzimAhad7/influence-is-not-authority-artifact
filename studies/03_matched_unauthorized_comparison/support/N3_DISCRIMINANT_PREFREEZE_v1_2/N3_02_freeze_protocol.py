#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, tarfile
from datetime import datetime, timezone
from pathlib import Path
from n3_common import *

SOURCE_FILES=["n3_common.py","N3_00_prepare_prefreeze.py","N3_01_human_audit_cli.py","N3_02_freeze_protocol.py","N3_03_score_science.py","N3_04_analyze.py","start_N3_Llama_vLLM.sh","start_N3_Gemma_vLLM.sh","README.md","PACKAGE_SHA256.txt"]

def verify_package(pkg: Path):
    ledger={}
    for line in (pkg/"PACKAGE_SHA256.txt").read_text().splitlines():
        if not line.strip(): continue
        h,name=line.split(None,1); ledger[name.strip()]=h
    for name,h in ledger.items():
        p=pkg/name
        if not p.exists() or sha256_file(p)!=h: raise SystemExit(f"FATAL package drift: {name}")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--project-root",required=True); ap.add_argument("--run-dir",default="N3_PREFREEZE_AUTHOR_v1"); ap.add_argument("--package-dir",default="N3_DISCRIMINANT_PREFREEZE_v1"); args=ap.parse_args()
    root=Path(args.project_root).resolve(); rd=root/args.run_dir; pkg=root/args.package_dir
    # Pre-outcome technical amendment hard stop: never re-freeze after any scientific unit/output exists.
    forbidden = [rd/"N3_ANALYSIS.json"]
    for sdir in rd.glob("science_*"):
        for name in ("SCORE_CACHE.jsonl","RAW_REQUESTS.jsonl","RAW_RESPONSES.jsonl","SCIENCE_SCORES.jsonl","RUN_COMPLETE.json"):
            forbidden.append(sdir/name)
    forbidden = [p for p in forbidden if p.exists()]
    if forbidden:
        raise SystemExit("FATAL: scientific/analysis outputs already exist; pre-outcome re-freeze prohibited: " + ", ".join(str(p) for p in forbidden))
    verify_package(pkg)
    source_ids=verify_a14_inputs(root)
    audit=read_jsonl(rd/"N3_HUMAN_AUDIT.jsonl")
    if len(audit)!=24 or any(r.get("author_decision")!="PASS" for r in audit): raise SystemExit("FATAL: human audit not 24/24 PASS")
    draft=read_json(rd/"N3_PROTOCOL_DRAFT.json")
    if draft.get("status")!="PREFREEZE_DRAFT_NO_SCIENCE" or draft.get("scientific_model_calls")!=0: raise SystemExit("FATAL: bad draft status")
    # Rebuild deterministically and require exact corpus equality to preparation output.
    obj=build_prefreeze_objects(root)
    checks=[
      ("N3_PROTOCOL_DRAFT.json", obj["protocol_draft"], "json"),
      ("N3_BASE_PROJECTION.json", {"schema_version":SCHEMA_VERSION,"bases":obj["alt_map"]}, "json"),
      ("N3_BASELINE_A14_UNITS.jsonl", obj["baseline_units"], "jsonl"),
      ("N3_POSITIVE_CONTEXTS.jsonl", obj["positive_contexts"], "jsonl"),
      ("N3_POSITIVE_SCORING_UNITS.jsonl", obj["positive_units"], "jsonl"),
      ("N3_MECHANICAL_CHECKS.json", obj["mechanical_checks"], "json"),
    ]
    for name,expected,kind in checks:
        p=rd/name
        got=read_json(p) if kind=="json" else read_jsonl(p)
        if stable_json(got)!=stable_json(expected): raise SystemExit(f"FATAL: prefreeze artifact drift {name}")
    corpus_files=[x[0] for x in checks]+["N3_HUMAN_AUDIT.jsonl"]
    corpus_hashes={name:sha256_file(rd/name) for name in corpus_files}
    code_hashes={name:sha256_file(pkg/name) for name in SOURCE_FILES if name!="PACKAGE_SHA256.txt"}
    freeze={
      **draft,
      "status":"FROZEN_PRE_OUTCOME_AUTHOR",
      "frozen_at_utc":datetime.now(timezone.utc).isoformat(),
      "scientific_model_calls_before_freeze":0,
      "pre_outcome_technical_amendment":{
          "revision":"v1.2",
          "reason":"independent pre-science audit found enforcement gaps: served revision was not runtime-attested and analyzer did not fully verify science/freeze linkage",
          "scope":"PROVENANCE_AND_INTEGRITY_ONLY",
          "scientific_design_changed":False,
          "bases_or_directives_changed":False,
          "authorization_oracle_changed":False,
          "estimands_changed":False,
          "inference_or_interpretation_changed":False,
          "human_audit_reused_sha256":sha256_file(rd/"N3_HUMAN_AUDIT.jsonl"),
          "science_observed_before_amendment":False,
      },
      "source_identities":source_ids,
      "human_audit":{"rows":24,"pass":24,"sha256":sha256_file(rd/"N3_HUMAN_AUDIT.jsonl")},
      "corpus_hashes":corpus_hashes,
      "implementation_hashes":code_hashes,
      "package_ledger_sha256":sha256_file(pkg/"PACKAGE_SHA256.txt"),
    }
    freeze_nohash=dict(freeze); freeze_nohash.pop("freeze_sha256",None)
    freeze["freeze_sha256"]=sha256_text(stable_json(freeze_nohash))
    dump_json(rd/"N3_FREEZE.json",freeze)
    final_files=corpus_files+["N3_FREEZE.json"]
    with (rd/"N3_FREEZE_SHA256.txt").open("w") as f:
        for name in sorted(final_files): f.write(f"{sha256_file(rd/name)}  {name}\n")
    print("N3 N0-FRZ FREEZE PASS")
    print(f"freeze_sha256={freeze['freeze_sha256']}")
    print(f"human_audit_sha256={freeze['human_audit']['sha256']}")
    print("scientific_model_calls_before_freeze=0")
    print("HARD STOP: do NOT run N3_03_score_science.py yet. Archive/upload this freeze for independent audit first.")
if __name__=='__main__': main()
