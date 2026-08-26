#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def fatal(m): raise SystemExit("FATAL: "+m)
def read_jsonl(p):
    out=[]
    for i,line in enumerate(p.read_text().splitlines(),1):
        if line.strip():
            try: out.append(json.loads(line))
            except Exception as e: fatal(f"{p.name} line {i}: {e}")
    return out
def sha256_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--project-root",required=True)
    a=ap.parse_args(); root=Path(a.project_root).resolve()
    out=root/"P0B3_CAUSALARMOR_LIVE_RUN_v1"
    rows=read_jsonl(out/"P0B3_SCIENCE_ROWS.jsonl")
    if len(rows)!=1046: fatal(f"expected 1046 science rows, got {len(rows)}")
    if any(r.get("status")!="OK" for r in rows): fatal("non-OK science row")
    if len({r["episode_id"] for r in rows})!=1046: fatal("duplicate episode IDs")
    if (out/"P0B3_ERRORS.jsonl").exists() and (out/"P0B3_ERRORS.jsonl").read_text().strip():
        fatal("Attempt 1 contains scientific hard-stop errors; do not call this a clean complete rerun")
    analysis=json.loads((out/"P0B3_ANALYSIS.json").read_text())
    if analysis.get("status")!="COMPLETE": fatal("analysis not COMPLETE")
    if analysis.get("population")!={"benign":97,"primary_attack":949,"legacy_nested":629}:
        fatal("analysis population mismatch")
    cap=json.loads((out/"P0B3_CLEAN_RERUN_CAPACITY_FINALIZATION.json").read_text())
    if cap.get("status")!="FROZEN_BEFORE_ATTEMPT1_BENCHMARK_OUTCOMES":
        fatal("capacity finalization record invalid")

    names=[
      "P0B3_LIVE_IMPLEMENTATION_FREEZE.json","P0B3_LIVE_PREFLIGHT.md","P0B3_TECHNICAL_CALLS.jsonl",
      "P0B3_CLEAN_RERUN_CAPACITY_FINALIZATION.json","P0B3_CLEAN_RERUN_CAPACITY_FINALIZATION.md",
      "P0B3_SCIENCE_ROWS.jsonl","P0B3_DEFENSE_EVENTS.jsonl","P0B3_PROVIDER_CALLS.jsonl",
      "P0B3_ANALYSIS.json","P0B3_SUITE_RESULTS.csv","P0B3_REPORT.md","FINAL_ARTIFACT_SHA256.txt"
    ]
    rows_hash=[]
    for n in names:
        p=out/n
        if not p.exists(): fatal(f"missing final artifact: {n}")
        rows_hash.append((sha256_file(p),n))
    (out/"P0B3_CLEAN_RERUN_FINAL_SHA256.txt").write_text("".join(f"{h}  {n}\n" for h,n in rows_hash))

    summary={
      "schema":"P0B3_CLEAN_FULL_RERUN_COMPLETE_V1",
      "status":"COMPLETE_PENDING_INDEPENDENT_ADJUDICATION",
      "attempt":"ATTEMPT1_CLEAN_FULL_RERUN",
      "science_rows":1046,
      "errors":0,
      "population":{"benign":97,"primary_attack":949,"legacy_nested":629},
      "primary_disposition":analysis["primary"]["disposition"],
      "serialization_gate":analysis["serialization_sensitivity"]["frozen_gt10pp_gate"],
      "attempt0_role":"PROVENANCE_ONLY",
      "p6_permission":"BLOCKED_UNTIL_INDEPENDENT_ADJUDICATION"
    }
    (out/"P0B3_CLEAN_FULL_RERUN_COMPLETE.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print("P0b-3 CLEAN FULL RERUN EXECUTION COMPLETE: 1046/1046")
    print("Attempt 1 status: COMPLETE_PENDING_INDEPENDENT_ADJUDICATION")
    print("PRIMARY DISPOSITION:",analysis["primary"]["disposition"])
    print("SERIALIZATION GATE:",analysis["serialization_sensitivity"]["frozen_gt10pp_gate"])
    print("P6: BLOCKED UNTIL INDEPENDENT ADJUDICATION")

if __name__=="__main__":
    main()
