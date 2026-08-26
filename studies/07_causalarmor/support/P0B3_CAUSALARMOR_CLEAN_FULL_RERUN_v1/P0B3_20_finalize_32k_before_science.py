#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

PROXY_REPO="google/gemma-3-12b-it"
PROXY_REV="96b6f1eccf38110c56df3a15bffe176da04bfd80"

def fatal(m): raise SystemExit("FATAL: "+m)
def sha256_file(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def stable(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,default=str)
def objhash(x): return hashlib.sha256(stable(x).encode()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",required=True)
    a=ap.parse_args(); root=Path(a.project_root).resolve()
    out=root/"P0B3_CAUSALARMOR_LIVE_RUN_v1"
    implp=out/"P0B3_LIVE_IMPLEMENTATION_FREEZE.json"
    if not implp.exists(): fatal("original live preflight implementation freeze missing")
    if (out/"P0B3_SCIENCE_ROWS.jsonl").exists(): fatal("science rows exist before capacity finalization")
    impl=json.loads(implp.read_text())
    if impl.get("scientific_agentdojo_episodes_before_this_freeze")!=0:
        fatal("implementation freeze is not pre-outcome")

    # Verify active server is still the finalized 32K process.
    ps=subprocess.check_output(["ps","-eo","pid,args"],text=True,errors="replace")
    candidates=[x.strip() for x in ps.splitlines() if PROXY_REPO in x and "vllm" in x.lower() and "--port 8100" in x]
    required=[
      PROXY_REPO,PROXY_REV,"--tokenizer-revision "+PROXY_REV,
      "--served-model-name google/gemma-3-12b-it","--dtype bfloat16",
      "--tensor-parallel-size 2","--max-model-len 32768","--port 8100"
    ]
    strict=[x for x in candidates if all(s in x for s in required)]
    if not strict: fatal("32K vLLM process drift after live preflight")

    # The original freeze recorded 16K; this companion record prospectively finalizes
    # serving capacity for the clean rerun without changing scientific semantics.
    protocol=json.loads((root/"P0B3_CAUSALARMOR_LIVE_v1"/"FROZEN_INPUTS"/"P0B3_PROTOCOL_FREEZE.json").read_text())
    old=protocol["config"]["models"]["proxy"]["max_model_len"]
    if old!=16384: fatal(f"unexpected original frozen serving ceiling: {old}")

    record={
      "schema":"P0B3_CLEAN_RERUN_SERVING_CAPACITY_FINALIZATION_V1",
      "status":"FROZEN_BEFORE_ATTEMPT1_BENCHMARK_OUTCOMES",
      "attempt":"ATTEMPT1_CLEAN_FULL_RERUN",
      "scientific_agentdojo_episodes_before_finalization":0,
      "historical_attempt0_status":"TECHNICAL_ABORT_PRE_DISPOSITION_992_OF_1046_PROVENANCE_ONLY",
      "reason":"Finalize reviewer-safe serving capacity after Attempt 0 exposed the artificial 16K vLLM ceiling; no Attempt-0 aggregate ASR/BU/UA/disposition was used.",
      "runtime_only_change":{"vllm_max_model_len_old":16384,"vllm_max_model_len_final":32768},
      "unchanged_scientific_semantics":{
        "proxy_repo":PROXY_REPO,
        "proxy_revision":PROXY_REV,
        "tokenizer_revision":PROXY_REV,
        "dtype":"bfloat16",
        "tensor_parallel_size":2,
        "primary_serialization":"ACTION_ONLY",
        "shadow_serialization":"COMPLETION_PLUS_TOOL_CALL",
        "tau":0.0,
        "population":{"benign":97,"primary_attack":949,"legacy_nested":629},
        "agent_model":"google/gemini-2.5-flash",
        "sanitizer_model":"google/gemini-2.5-flash",
        "calibration_gates":"UNCHANGED_FROM_ORIGINAL_FREEZE"
      },
      "implementation_freeze_sha256":impl["implementation_freeze_sha256"],
      "live_preflight_status":impl["status"],
      "vllm_process_evidence":strict[:3],
      "paper_result_rule":"If Attempt 1 completes and passes integrity adjudication, it is the sole primary P0b-3 paper result. Attempt 0 remains provenance only; never select between attempts by outcome."
    }
    record["record_sha256"]=objhash(record)
    p=out/"P0B3_CLEAN_RERUN_CAPACITY_FINALIZATION.json"
    p.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    (out/"P0B3_CLEAN_RERUN_CAPACITY_FINALIZATION.md").write_text(
      "# P0b-3 Clean Rerun Capacity Finalization\n\n"
      "**FROZEN BEFORE ATTEMPT-1 BENCHMARK OUTCOMES.**\n\n"
      "- Attempt 0: archived technical abort at 992/1046; provenance only.\n"
      "- Attempt 1: fresh 0/1046 clean full rerun.\n"
      "- Only runtime finalization: vLLM max_model_len 16384 -> 32768.\n"
      "- Model/revision/tokenizer/scoring/tau/populations/provider models/gates unchanged.\n"
      "- Attempt-0 aggregate outcomes were not used to choose this rerun.\n"
    )
    print("P0b-3 CLEAN RERUN CAPACITY FINALIZATION PASS")
    print("AgentDojo benchmark episodes executed before finalization: 0")
    print("Attempt 1 primary-if-complete rule: FROZEN")
    print("serving ceiling: 32768")
    print("record_sha256:",record["record_sha256"])

if __name__=="__main__":
    main()
