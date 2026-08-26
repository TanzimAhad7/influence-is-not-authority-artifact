#!/usr/bin/env python3
"""
Run the already-frozen AttriGuard × A14 scientific protocol.

DO NOT run until the freeze artifact has been independently audited/authorized.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import openai

FROZEN_ADAPTER_SHA="fb613a6e427fa28bdc0ddf3774fbdd0abbbcc593733f41eca1d19449b758467a"

def digest(p: Path) -> str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def stable_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def load_jsonl(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

def append_jsonl(p: Path, obj: dict):
    with p.open("a",encoding="utf-8") as f:
        f.write(json.dumps(obj,sort_keys=True,ensure_ascii=False)+"\n")
        f.flush()
        os.fsync(f.fileno())

def content_to_jsonable(x):
    try:
        return json.loads(json.dumps(x,default=str))
    except Exception:
        return str(x)

class RecordingCompletions:
    def __init__(self, inner, sink):
        self.inner=inner
        self.sink=sink
    def create(self, **kwargs):
        t0=time.time()
        response=self.inner.create(**kwargs)
        elapsed=time.time()-t0
        usage=getattr(response,"usage",None)
        if hasattr(usage,"model_dump"):
            usage=usage.model_dump()
        rec={
            "requested_model":kwargs.get("model"),
            "temperature":kwargs.get("temperature"),
            "top_p":None if str(kwargs.get("top_p"))=="NOT_GIVEN" else kwargs.get("top_p"),
            "seed":None if str(kwargs.get("seed"))=="NOT_GIVEN" else kwargs.get("seed"),
            "logprobs":None if str(kwargs.get("logprobs"))=="NOT_GIVEN" else kwargs.get("logprobs"),
            "top_logprobs":None if str(kwargs.get("top_logprobs"))=="NOT_GIVEN" else kwargs.get("top_logprobs"),
            "tool_choice":str(kwargs.get("tool_choice")),
            "elapsed_seconds":elapsed,
            "response_id":getattr(response,"id",None),
            "response_model":getattr(response,"model",None),
            "system_fingerprint":getattr(response,"system_fingerprint",None),
            "usage":content_to_jsonable(usage),
        }
        self.sink.append(rec)
        return response

class RecordingChat:
    def __init__(self, inner, sink):
        self.completions=RecordingCompletions(inner.completions,sink)

class RecordingClient:
    def __init__(self, inner, sink):
        self.chat=RecordingChat(inner.chat,sink)

class RecordingLLM:
    def __init__(self, label, inner, provider_sink):
        self.label=label
        self.inner=inner
        self.provider_sink=provider_sink
        self.records=[]
    def query(self, query, runtime, env, messages, extra_args):
        before=len(self.provider_sink)
        t0=time.time()
        result=self.inner.query(query,runtime,env,messages,extra_args)
        elapsed=time.time()-t0
        out_messages=result[3]
        self.records.append({
            "label":self.label,
            "elapsed_seconds":elapsed,
            "input_messages":content_to_jsonable(messages),
            "output_last_message":content_to_jsonable(out_messages[-1] if out_messages else None),
            "provider_calls":content_to_jsonable(self.provider_sink[before:]),
        })
        return result

def find_target_result(messages, target_id):
    for m in messages:
        if m.get("role")=="tool" and m.get("tool_call_id")==target_id:
            return m
    return None

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",default=".")
    args=ap.parse_args()
    project=Path(args.project_root).resolve()
    package=Path(__file__).resolve().parent
    outdir=project/"attriguard_a14_v2/scientific_v1"
    freeze_p=outdir/"ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE.json"
    if not freeze_p.is_file():
        raise SystemExit("FATAL: scientific freeze missing")
    freeze=json.loads(freeze_p.read_text())
    ph=freeze.pop("protocol_hash")
    if stable_hash(freeze)!=ph:
        raise SystemExit("FATAL: scientific freeze internal hash mismatch")
    freeze["protocol_hash"]=ph
    if freeze.get("status")!="FROZEN_PRE_OUTCOME":
        raise SystemExit("FATAL: protocol is not frozen")
    if digest(package/"ATTRIGUARD_A14_V2_01_adapter.py")!=FROZEN_ADAPTER_SHA:
        raise SystemExit("FATAL: adapter source drift")

    key=os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("FATAL: OPENROUTER_API_KEY is not set")
    raw_client=openai.OpenAI(api_key=key,base_url=freeze["execution"]["base_url"])

    official=project/"external/attriguard_zenodo_v1/usenix-artifacts"
    sys.path.insert(0,str(official/"main/pipeline"))
    sys.path.insert(0,str(package))
    import pydantic_fix  # noqa
    import AttriGuard as AG
    from openai_llm_compat import OpenAILLM
    from agentdojo.functions_runtime import EmptyEnv
    from ATTRIGUARD_A14_V2_01_adapter import (
        build_messages,build_runtime,load_frozen_a14,patch_external_resolvers
    )

    patch_external_resolvers(AG)
    rows,bases=load_frozen_a14(project)
    row_by={r["condition_id"]:r for r in rows}

    results_p=outdir/"SCIENTIFIC_RESULTS.jsonl"
    attempts_p=outdir/"SCIENTIFIC_ATTEMPTS.jsonl"
    provider_p=outdir/"PROVIDER_CALLS.jsonl"

    successful={}
    if results_p.exists():
        for r in load_jsonl(results_p):
            key2=(r["condition_id"],int(r["repeat"]))
            if r.get("status")=="SUCCESS":
                if key2 in successful:
                    raise SystemExit(f"FATAL: duplicate successful key in existing results: {key2}")
                successful[key2]=r

    schedule=freeze["execution"]["schedule"]
    for item in schedule:
        key2=(item["condition_id"],int(item["repeat"]))
        if key2 in successful:
            print(f"[AAG-V2-05] SKIP completed {item['schedule_index']:03d}/480 {key2}")
            continue
        row=row_by[item["condition_id"]]
        base=bases[row["base_id"]]

        success=False
        for condition_attempt in (1,2):
            provider_sink=[]
            client=RecordingClient(raw_client,provider_sink)
            main=RecordingLLM("main",OpenAILLM(
                client,freeze["execution"]["requested_model"],
                temperature=freeze["execution"]["main_temperature"]
            ),provider_sink)
            attenuation=RecordingLLM("attenuation",OpenAILLM(
                client,freeze["execution"]["requested_model"],
                temperature=freeze["execution"]["attenuation_temperature"],
                top_p=freeze["execution"]["attenuation_top_p"],
            ),provider_sink)
            judge=RecordingLLM("judge",OpenAILLM(
                client,freeze["execution"]["requested_model"],
                temperature=freeze["execution"]["judge_temperature"],
                top_p=freeze["execution"]["judge_top_p"],
            ),provider_sink)
            loop=AG.AttriGuardExecutionLoop(
                main,
                judge_llm=judge,
                attenuation_llm=attenuation,
                attenuation_level=freeze["execution"]["attenuation_level"],
                survival_mode=freeze["execution"]["survival_mode"],
                max_iters=freeze["execution"]["max_iters"],
                skip_empty_tool_results_audit=True,
                debug=False,
            )
            runtime,orig,alias=build_runtime(row,base)
            built=build_messages(row,base)
            t0=time.time()
            err=None
            try:
                q,rt2,env2,out_messages,extra=loop.query(
                    built["query"],runtime,EmptyEnv(),copy.deepcopy(built["messages"]),{}
                )
            except Exception as e:
                out_messages=[]
                err=f"{type(e).__name__}: {e}"
            elapsed=time.time()-t0

            attempt_record={
                **item,
                "condition_attempt":condition_attempt,
                "status":"SUCCESS" if err is None else "ERROR",
                "error":err,
                "elapsed_seconds":elapsed,
                "provider_calls":provider_sink,
                "main_records":main.records,
                "attenuation_records":attenuation.records,
                "judge_records":judge.records,
            }
            append_jsonl(attempts_p,attempt_record)
            for j,pc in enumerate(provider_sink,1):
                append_jsonl(provider_p,{
                    **item,
                    "condition_attempt":condition_attempt,
                    "call_index_within_attempt":j,
                    **pc,
                })

            if err is None:
                target=built["target_call"]
                tr=find_target_result(out_messages,target.id)
                if tr is None or not isinstance(tr.get("defense_state"),dict):
                    err="MissingTargetDefenseState"
                else:
                    ds=tr["defense_state"]
                    result={
                        **item,
                        "status":"SUCCESS",
                        "condition_attempt":condition_attempt,
                        "target_action_hash":row["target_action_hash"],
                        "target_function":target.function,
                        "blocked":bool(ds.get("flag")),
                        "judge_reason":ds.get("judge_reason"),
                        "attenuated_external":ds.get("attenuated_external"),
                        "defense_input":tr.get("defense_input"),
                        "elapsed_seconds":elapsed,
                        "provider_call_count":len(provider_sink),
                        "provider_response_models":sorted({x.get("response_model") for x in provider_sink if x.get("response_model")}),
                        "provider_system_fingerprints":sorted({x.get("system_fingerprint") for x in provider_sink if x.get("system_fingerprint")}),
                    }
                    append_jsonl(results_p,result)
                    successful[key2]=result
                    success=True
                    print(
                        f"[AAG-V2-05] {item['schedule_index']:03d}/480 "
                        f"{item['condition_id']} rep={item['repeat']} "
                        f"blocked={result['blocked']} calls={len(provider_sink)} "
                        f"elapsed={elapsed:.1f}s"
                    )
                    break
            if err is not None:
                print(
                    f"[AAG-V2-05] ERROR {item['schedule_index']:03d}/480 "
                    f"{item['condition_id']} rep={item['repeat']} "
                    f"attempt={condition_attempt}/2 error={err}"
                )
                if condition_attempt==1:
                    time.sleep(freeze["failure_policy"]["condition_retry_delay_seconds"])

        if not success:
            print(f"[AAG-V2-05] TERMINAL ERROR key={key2}; run will be incomplete")

    success_rows=list(successful.values())
    complete=len(success_rows)==480
    run_summary={
        "schema":"ATTRIGUARD_A14_V2_SCIENTIFIC_RUN_SUMMARY_V1_2026-08-10",
        "protocol_hash":ph,
        "successful_condition_repeats":len(success_rows),
        "expected_condition_repeats":480,
        "complete":complete,
        "results_sha256":digest(results_p) if results_p.exists() else None,
        "attempts_sha256":digest(attempts_p) if attempts_p.exists() else None,
        "provider_calls_sha256":digest(provider_p) if provider_p.exists() else None,
        "provider_response_models":sorted({
            m for r in success_rows for m in r.get("provider_response_models",[])
        }),
        "provider_system_fingerprints":sorted({
            f for r in success_rows for f in r.get("provider_system_fingerprints",[])
        }),
    }
    summary_p=outdir/"RUN_SUMMARY.json"
    summary_p.write_text(json.dumps(run_summary,indent=2,sort_keys=True)+"\n")
    print(f"[AAG-V2-05] successful={len(success_rows)}/480 complete={complete}")
    print(f"[AAG-V2-05] results_sha256={run_summary['results_sha256']}")
    print(f"[AAG-V2-05] provider_models={run_summary['provider_response_models']}")
    print(f"[AAG-V2-05] provider_fingerprints={run_summary['provider_system_fingerprints']}")
    print(f"[AAG-V2-05] summary={summary_p}")
    if not complete:
        raise SystemExit(2)

if __name__=="__main__":
    main()
