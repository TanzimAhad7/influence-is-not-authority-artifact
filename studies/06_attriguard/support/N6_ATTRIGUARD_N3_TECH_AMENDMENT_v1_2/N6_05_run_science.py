#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, hashlib, json, os, sys, time
from pathlib import Path
import openai

from n6_tech_common import *
from N6_03_paired_adapter import *

AMENDMENT_FILE = "N6_TECHNICAL_AMENDMENT_v1_2.json"

def content_to_jsonable(x):
    try:
        return json.loads(json.dumps(x, default=str))
    except Exception:
        return str(x)

def serialize_call(c):
    return {"function": c.function, "arguments": dict(c.args), "id": c.id}

def serialize_last_message(messages):
    if not messages:
        return None
    m = messages[-1]
    return {
        "role": m.get("role"),
        "content": content_to_jsonable(m.get("content")),
        "tool_calls": [serialize_call(c) for c in (m.get("tool_calls") or [])],
    }

class RecordingCompletions:
    def __init__(self, inner, sink):
        self.inner = inner; self.sink = sink
    def create(self, **kwargs):
        t0=time.time()
        response=self.inner.create(**kwargs)
        elapsed=time.time()-t0
        usage=getattr(response,"usage",None)
        if hasattr(usage,"model_dump"): usage=usage.model_dump()
        rec={
            "requested_model":kwargs.get("model"),
            "temperature":None if str(kwargs.get("temperature"))=="NOT_GIVEN" else kwargs.get("temperature"),
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
    def __init__(self,label,inner,provider_sink):
        self.label=label; self.inner=inner; self.provider_sink=provider_sink; self.records=[]
    def query(self,query,runtime,env,messages,extra_args):
        before=len(self.provider_sink)
        result=self.inner.query(query,runtime,env,messages,extra_args)
        out=result[3]
        self.records.append({
            "label":self.label,
            "input_message_count":len(messages),
            "output_last_message":serialize_last_message(out),
            "provider_calls":content_to_jsonable(self.provider_sink[before:]),
        })
        return result

def get_first_shadow_calls(main_records):
    # With max_iters=1, the first main-record is the shadow replay; the second,
    # when present, is the post-tools continuation.
    if not main_records:
        return []
    last=main_records[0].get("output_last_message") or {}
    return last.get("tool_calls") or []

def json_call_signature(c):
    return (c["function"], json.dumps(c["arguments"],sort_keys=True,separators=(",",":"),ensure_ascii=False))

def structural_route_from_json(candidate, shadow):
    sig=(candidate.function,json.dumps(dict(candidate.args),sort_keys=True,separators=(",",":"),ensure_ascii=False))
    ss={json_call_signature(x) for x in shadow}
    if sig in ss: return "EXACT_SHADOW_SURVIVAL"
    if any(x["function"]==candidate.function for x in shadow): return "FUZZY_JUDGE_PATH"
    return "NO_SAME_FUNCTION_HARD_FAIL"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",default=".")
    args=ap.parse_args()
    project=Path(args.project_root).resolve()
    package=Path(__file__).resolve().parent

    design, parent, audit = verify_parent(project)
    n3, official_root, paths = locate_sources(project)
    amendment_p=project/"N6_ATTRIGUARD_N3_PREFREEZE_v1_out"/AMENDMENT_FILE
    if not amendment_p.is_file():
        raise SystemExit("FATAL: N6 v1.1 technical amendment missing; run N6_04 first")
    amendment=json.loads(amendment_p.read_text())
    ah=amendment.pop("amendment_hash")
    if stable_hash(amendment)!=ah:
        raise SystemExit("FATAL: technical amendment internal hash mismatch")
    amendment["amendment_hash"]=ah
    if amendment.get("status")!="FROZEN_TECHNICAL_AMENDMENT_ZERO_MODEL_CALLS":
        raise SystemExit("FATAL: technical amendment not frozen")
    for fn,h in amendment["frozen_package_hashes"].items():
        p=package/fn
        if not p.is_file() or sha256_file(p)!=h:
            raise SystemExit(f"FATAL: frozen package source drift: {fn}")

    contexts, projection, prior_audit, n3_protocol, member_shas=load_n3(n3)
    if member_shas != parent["n3_member_sha256"]:
        raise SystemExit("FATAL: N3 member drift")
    units={u["unit_id"]:u for u in design["units"]}

    key=os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise SystemExit("FATAL: OPENROUTER_API_KEY is not set")
    raw_client=openai.OpenAI(api_key=key,base_url=parent["official_configuration"]["base_url"])

    pipe_dir=official_root/"main/pipeline"
    sys.path.insert(0,str(pipe_dir))
    sys.path.insert(0,str(package))
    import pydantic_fix  # noqa
    import AttriGuard as AG
    from openai_llm_compat import OpenAILLM
    from agentdojo.functions_runtime import EmptyEnv

    patch_external_resolvers(AG)
    if sha256_file(pipe_dir/"AttriGuard.py") != EXPECTED["attriguard_py_sha256"]:
        raise SystemExit("FATAL: official core changed after runtime alias patch")

    outdir=project/"n6_attriguard_n3_v1/scientific_v1"
    outdir.mkdir(parents=True,exist_ok=True)
    results_p=outdir/"N6_RESULTS.jsonl"
    attempts_p=outdir/"N6_ATTEMPTS.jsonl"
    provider_p=outdir/"N6_PROVIDER_CALLS.jsonl"

    successful={}
    if results_p.exists():
        for r in load_jsonl(results_p):
            if r.get("status")=="SUCCESS":
                k=(r["unit_id"],int(r["repeat"]))
                if k in successful:
                    raise SystemExit(f"FATAL: duplicate successful key {k}")
                successful[k]=r

    for item in parent["schedule"]:
        k=(item["unit_id"],int(item["repeat"]))
        if k in successful:
            print(f"[N6-05] SKIP completed {item['schedule_index']:03d}/240 {k}")
            continue
        unit=units[item["unit_id"]]
        base=projection["bases"][unit["base_id"]]

        terminal=False
        for attempt in (1,2):
            provider_sink=[]
            client=RecordingClient(raw_client,provider_sink)
            cfg=parent["official_configuration"]
            main_llm=RecordingLLM("main",OpenAILLM(
                client,cfg["requested_model"],temperature=cfg["main_shadow_temperature"]
            ),provider_sink)
            attenuation=RecordingLLM("attenuation",OpenAILLM(
                client,cfg["requested_model"],temperature=cfg["attenuation_temperature"],
                top_p=cfg["attenuation_top_p"]
            ),provider_sink)
            judge=RecordingLLM("judge",OpenAILLM(
                client,cfg["requested_model"],temperature=cfg["judge_temperature"],
                top_p=cfg["judge_top_p"]
            ),provider_sink)

            loop=AG.AttriGuardExecutionLoop(
                main_llm,
                judge_llm=judge,
                attenuation_llm=attenuation,
                attenuation_level=cfg["attenuation_level"],
                survival_mode=cfg["survival_mode"],
                max_iters=1,
                skip_empty_tool_results_audit=cfg["skip_empty_tool_results_audit"],
                debug=False,
            )
            runtime,_,_=build_runtime(unit,base)
            built=build_messages(unit,base,item["candidate_order"])

            t0=time.time()
            err=None
            out_messages=[]
            try:
                q,rt2,env2,out_messages,extra=loop.query(
                    built["query"],runtime,EmptyEnv(),copy.deepcopy(built["messages"]),{}
                )
            except Exception as e:
                err=f"{type(e).__name__}: {e}"
            elapsed=time.time()-t0

            attempt_rec={
                **item,
                "base_id":unit["base_id"],
                "family":unit["family"],
                "descendant":unit["descendant"],
                "context_id":unit["context_id"],
                "condition_attempt":attempt,
                "status":"ERROR" if err else "CALL_COMPLETED",
                "error":err,
                "elapsed_seconds":elapsed,
                "provider_calls":content_to_jsonable(provider_sink),
                "main_records":content_to_jsonable(main_llm.records),
                "attenuation_records":content_to_jsonable(attenuation.records),
                "judge_records":content_to_jsonable(judge.records),
            }
            append_jsonl(attempts_p,attempt_rec)
            for j,pc in enumerate(provider_sink,1):
                append_jsonl(provider_p,{
                    **item,"base_id":unit["base_id"],"family":unit["family"],
                    "descendant":unit["descendant"],"condition_attempt":attempt,
                    "call_index_within_attempt":j,**pc
                })

            if err is not None:
                if attempt==1:
                    print(f"[N6-05] exception; wait 30s then one frozen retry: {k} {err}")
                    time.sleep(30)
                    continue
                print(f"[N6-05] TERMINAL ERROR {k}: {err}")
                terminal=True
                break

            ar=extract_tool_result(out_messages,built["AUTH_call"].id)
            xr=extract_tool_result(out_messages,built["ALT_call"].id)
            # Missing defense states are invalid output, not an exception: frozen policy says NO retry.
            if ar is None or xr is None or not isinstance(ar.get("defense_state"),dict) or not isinstance(xr.get("defense_state"),dict):
                invalid={
                    **item,"base_id":unit["base_id"],"family":unit["family"],
                    "descendant":unit["descendant"],"context_id":unit["context_id"],
                    "status":"INVALID_OUTPUT_NO_RETRY",
                    "condition_attempt":attempt,
                    "error":"missing AUTH/ALT tool result or defense_state",
                    "provider_call_count":len(provider_sink),
                }
                append_jsonl(results_p,invalid)
                print(f"[N6-05] INVALID OUTPUT / NO RETRY {k}")
                terminal=True
                break

            shadow=get_first_shadow_calls(main_llm.records)
            auth_route=structural_route_from_json(built["AUTH_call"],shadow)
            alt_route=structural_route_from_json(built["ALT_call"],shadow)
            auth_block=bool(ar["defense_state"].get("flag"))
            alt_block=bool(xr["defense_state"].get("flag"))

            result={
                **item,
                "base_id":unit["base_id"],
                "family":unit["family"],
                "descendant":unit["descendant"],
                "context_id":unit["context_id"],
                "prompt_sha256":unit["prompt_sha256"],
                "status":"SUCCESS",
                "condition_attempt":attempt,
                "AUTH_sha256":unit["AUTH_sha256"],
                "ALT_sha256":unit["ALT_sha256"],
                "execution_arg":unit["execution_arg"],
                "AUTH_blocked":auth_block,
                "ALT_blocked":alt_block,
                "Z":int(alt_block)-int(auth_block),
                "AUTH_route":auth_route,
                "ALT_route":alt_route,
                # Official judge reason is retained raw. It is only semantically
                # interpretable for FUZZY_JUDGE_PATH because the official source
                # keeps _last_judge_reason as mutable state across candidates.
                "AUTH_judge_reason_raw":ar["defense_state"].get("judge_reason"),
                "ALT_judge_reason_raw":xr["defense_state"].get("judge_reason"),
                "attenuated_external":ar["defense_state"].get("attenuated_external"),
                "defense_input":ar.get("defense_input"),
                "shadow_calls":shadow,
                "provider_call_count":len(provider_sink),
                "provider_response_models":sorted({str(x.get("response_model")) for x in provider_sink}),
                "elapsed_seconds":elapsed,
            }
            append_jsonl(results_p,result)
            successful[k]=result
            print(f"[N6-05] SUCCESS {item['schedule_index']:03d}/240 {k} AUTH_block={auth_block} ALT_block={alt_block} Z={result['Z']}")
            terminal=True
            break

        if not terminal:
            raise SystemExit(f"FATAL: internal runner state for {k}")

    completed=sum(1 for r in load_jsonl(results_p) if r.get("status")=="SUCCESS")
    print(f"[N6-05] successful paired runs={completed}/240")
    if completed != 240:
        print("[N6-05] INCOMPLETE: do not run confirmatory analysis until 240/240 SUCCESS")
    else:
        print("[N6-05] COMPLETE: run N6_06_analyze.py")

if __name__=="__main__":
    main()
