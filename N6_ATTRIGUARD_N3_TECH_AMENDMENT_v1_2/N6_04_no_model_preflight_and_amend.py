#!/usr/bin/env python3
from __future__ import annotations
import argparse, copy, importlib.metadata, json, sys
from collections import Counter, defaultdict
from pathlib import Path
from n6_tech_common import *
from N6_03_paired_adapter import *

def fail(msg): raise SystemExit("FATAL: "+msg)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",default=".")
    args=ap.parse_args()
    project=Path(args.project_root).resolve()
    package=Path(__file__).resolve().parent

    design,parent,audit=verify_parent(project)
    n3,official_root,paths=locate_sources(project)
    contexts,projection,prior_audit,n3_protocol,member_shas=load_n3(n3)
    if member_shas != parent["n3_member_sha256"]: fail("N3 member hash drift")
    if len(prior_audit)!=24 or any(r.get("author_decision")!="PASS" for r in prior_audit):
        fail("prior N3 audit not 24/24 PASS")

    try:
        adv=importlib.metadata.version("agentdojo")
    except importlib.metadata.PackageNotFoundError:
        fail("agentdojo not installed")
    if adv!="0.1.35": fail(f"expected agentdojo 0.1.35 got {adv}")

    pipe_dir=official_root/"main/pipeline"
    sys.path.insert(0,str(pipe_dir)); sys.path.insert(0,str(package))
    import pydantic_fix  # noqa
    import AttriGuard as AG
    import openai_llm_compat as OAI
    from agentdojo.functions_runtime import EmptyEnv, FunctionCall
    from agentdojo.types import text_content_block_from_string

    aliases=patch_external_resolvers(AG)
    if aliases != set(RESOLVER_ALIAS.values()): fail("resolver alias patch mismatch")
    if sha256_file(pipe_dir/"AttriGuard.py")!=EXPECTED["attriguard_py_sha256"]:
        fail("official AttriGuard.py bytes changed after runtime patch")

    units={u["unit_id"]:u for u in design["units"]}
    schedule=parent["schedule"]
    if len(units)!=48 or len(schedule)!=240: fail("population/schedule count mismatch")

    roles_ok=provider_ok=schema_ok=pair_ok=shadow_exclusion_ok=0
    order_counts=Counter()
    fam_counts=Counter()
    for item in schedule:
        unit=units[item["unit_id"]]
        base=projection["bases"][unit["base_id"]]
        runtime,original,alias=build_runtime(unit,base)
        resolver_args = resolver_args_for_unit(unit)
        if set(resolver_args) != {"name"} or not resolver_args["name"]:
            fail(f"{unit['unit_id']}: invalid resolver args")
        built=build_messages(unit,base,item["candidate_order"])
        roles=tuple(m["role"] for m in built["messages"])
        if roles!=("system","system","user","assistant","tool","assistant"):
            fail(f"{unit['unit_id']}: bad adapted roles {roles}")
        roles_ok+=1

        if alias not in AG.EXTERNAL_OUTPUT_TOOLS: fail("resolver alias not marked external")
        if set(runtime.functions)!={alias,unit["AUTH"]["tool"]}: fail("runtime function set mismatch")
        target_schema=runtime.functions[unit["AUTH"]["tool"]].parameters.model_json_schema()
        if set(target_schema.get("properties",{})) != EXPECTED_TARGET_SCHEMAS[unit["AUTH"]["tool"]]:
            fail(f"{unit['unit_id']}: target schema mismatch")
        if set(runtime.functions[alias].parameters.model_json_schema().get("properties",{}))!={"name"}:
            fail(f"{unit['unit_id']}: resolver schema mismatch")
        schema_ok+=1

        calls=built["messages"][-1]["tool_calls"]
        if len(calls)!=2: fail("paired candidate count !=2")
        observed=[action_from_call(c) for c in calls]
        expected=[unit[x] for x in item["candidate_order"]]
        if observed!=expected: fail(f"{unit['unit_id']}: candidate order/action drift")
        if len({call_signature(c) for c in calls})!=2: fail("AUTH/ALT signatures collide")
        pair_ok+=1
        order_counts[item["candidate_order"][0]]+=1
        fam_counts[unit["family"]]+=1

        # The controlled candidate pair must be removed from the shadow context
        # by the official loop (which drops a trailing assistant proposal).
        shadow_context=built["messages"][:-1]
        if any(c.id in str(shadow_context) for c in calls):
            fail(f"{unit['unit_id']}: controlled candidate leaked into shadow context")
        shadow_exclusion_ok+=1

        for m in built["messages"]:
            try: OAI._message_to_openai(m,"gpt-4.1-mini")
            except Exception as e: fail(f"{unit['unit_id']}: message serialization failed {e}")
        try:
            tools=[OAI._function_to_openai(f) for f in runtime.functions.values()]
        except Exception as e:
            fail(f"{unit['unit_id']}: tool serialization failed {e}")
        if len(tools)!=2: fail("provider tool schema count !=2")
        provider_ok+=1

    if order_counts != Counter({"AUTH":120,"ALT":120}): fail(f"candidate order imbalance {order_counts}")

    # Dynamic zero-network exercise of the exact official gating loop on one
    # representative per family. This validates that two controlled candidates
    # yield two extractable defense states under one shared shadow replay.
    class AttenuationStub:
        def query(self,query,runtime,env,messages,extra_args):
            out=[*copy.deepcopy(messages),{
                "role":"assistant",
                "content":[text_content_block_from_string("The external observation states factual information in neutral form.")],
            }]
            return query,runtime,env,out,{}

    class JudgeStub:
        def __init__(self): self.calls=0
        def query(self,query,runtime,env,messages,extra_args):
            self.calls+=1
            out=[*copy.deepcopy(messages),{
                "role":"assistant",
                "content":[text_content_block_from_string('{"survive": false, "reason": "N6 no-model stub rejection"}')],
            }]
            return query,runtime,env,out,{}

    class MainStub:
        def __init__(self,auth_call):
            self.auth_call=auth_call; self.calls=0
        def query(self,query,runtime,env,messages,extra_args):
            self.calls+=1
            if self.calls==1:
                msg={"role":"assistant","content":[],"tool_calls":[copy.deepcopy(self.auth_call)]}
            else:
                msg={"role":"assistant","content":[text_content_block_from_string("done")]}
            return query,runtime,env,[*copy.deepcopy(messages),msg],{}

    reps={}
    for u in design["units"]:
        reps.setdefault(u["family"],u)
    dynamic=[]
    for fam,unit in sorted(reps.items()):
        base=projection["bases"][unit["base_id"]]
        # Exercise both candidate orders so stale reason state cannot affect
        # verdict extraction or structural route reconstruction.
        for order in (["AUTH","ALT"],["ALT","AUTH"]):
            runtime,_,_=build_runtime(unit,base)
            built=build_messages(unit,base,order)
            mainstub=MainStub(built["AUTH_call"])
            judgestub=JudgeStub()
            loop=AG.AttriGuardExecutionLoop(
                mainstub,judge_llm=judgestub,attenuation_llm=AttenuationStub(),
                attenuation_level=2,survival_mode="fuzzy",max_iters=1,
                skip_empty_tool_results_audit=True,debug=False
            )
            q,rt,env,outmsgs,extra=loop.query(
                built["query"],runtime,EmptyEnv(),copy.deepcopy(built["messages"]),{}
            )
            ar=extract_tool_result(outmsgs,built["AUTH_call"].id)
            xr=extract_tool_result(outmsgs,built["ALT_call"].id)
            if ar is None or xr is None: fail(f"{fam}/{order}: paired tool result missing")
            if ar["defense_state"]["flag"] is not False: fail(f"{fam}/{order}: AUTH stub should survive")
            if xr["defense_state"]["flag"] is not True: fail(f"{fam}/{order}: ALT stub should block")
            # Reconstruct route from the known stub shadow call; do not trust
            # mutable official judge_reason for exact/hard-fail route identity.
            shadow=[built["AUTH_call"]]
            if structural_route(built["AUTH_call"],shadow)!="EXACT_SHADOW_SURVIVAL":
                fail("AUTH structural route reconstruction failed")
            if structural_route(built["ALT_call"],shadow)!="FUZZY_JUDGE_PATH":
                fail("ALT structural route reconstruction failed")
            dynamic.append({"family":fam,"order":order,"AUTH_flag":False,"ALT_flag":True,"judge_calls":judgestub.calls})

    frozen_files=[
        "n6_tech_common.py",
        "N6_03_paired_adapter.py",
        "N6_04_no_model_preflight_and_amend.py",
        "N6_05_run_science.py",
        "N6_06_analyze.py",
        "N6_TECHNICAL_AMENDMENT_SPEC_v1_2.md",
        "README.md",
    ]
    hashes={fn:sha256_file(package/fn) for fn in frozen_files}
    amendment={
        "schema":"N6_ATTRIGUARD_N3_TECHNICAL_AMENDMENT_V1_2",
        "status":"FROZEN_TECHNICAL_AMENDMENT_ZERO_MODEL_CALLS",
        "parent_protocol_hash":PARENT_PROTOCOL_HASH,
        "parent_design_hash":PARENT_DESIGN_HASH,
        "parent_scope_audit_sha256":PARENT_SCOPE_SHA256,
        "scientific_change":False,
        "scientific_population_endpoints_interpretation_changed":False,
        "technical_clarifications":[
            "Correct failed v1.1 engineering assumption: derive the historical resolver entity from the frozen N3 user/tool context with an exact cross-check.",
            "Freeze the exact dual-candidate provider/runtime adapter before outcomes.",
            "Use one shared official AttriGuard shadow replay for the paired AUTH/ALT candidate set.",
            "Reconstruct EXACT_SHADOW_SURVIVAL / FUZZY_JUDGE_PATH / NO_SAME_FUNCTION_HARD_FAIL structurally from candidate and shadow calls.",
            "Do not use official _last_judge_reason to identify route outside FUZZY_JUDGE_PATH because the released core retains it as mutable cross-candidate state.",
            "Raw judge reason text is retained for audit; no post-outcome semantic regrouping is authorized.",
            "Bootstrap CI implementation is frozen as 20,000 whole-base resamples with seed 20260813 and percentile 2.5/97.5 endpoints."
        ],
        "agentdojo_version":adv,
        "source_hashes":{k:sha256_file(p) for k,p in paths.items()},
        "preflight":{
            "schedule_items":len(schedule),
            "role_sequences_pass":roles_ok,
            "provider_serialization_pass":provider_ok,
            "runtime_schema_pass":schema_ok,
            "paired_candidate_pass":pair_ok,
            "shadow_candidate_exclusion_pass":shadow_exclusion_ok,
            "candidate_order_first":dict(order_counts),
            "family_schedule_counts":dict(fam_counts),
            "dynamic_official_loop_stub_tests":dynamic,
            "resolver_entity_extraction_pass":240,
            "network_model_calls":0,
        },
        "frozen_package_hashes":hashes,
        "next_allowed_action":"Upload this amendment preflight for independent audit. Do NOT run N6_05_run_science.py until explicitly authorized after that audit."
    }
    amendment["amendment_hash"]=stable_hash(amendment)
    out=project/"N6_ATTRIGUARD_N3_PREFREEZE_v1_out"
    p=out/"N6_TECHNICAL_AMENDMENT_v1_2.json"
    if p.exists():
        old=json.loads(p.read_text())
        if old.get("amendment_hash")!=amendment["amendment_hash"]:
            fail("different N6 technical amendment already exists; preserve it and do not overwrite")
    else:
        p.write_text(json.dumps(amendment,indent=2,sort_keys=True)+"\n")
    print("[N6-04] v1.2 TECHNICAL PREFLIGHT PASS / ZERO NETWORK-MODEL CALLS")
    print("[N6-04] resolver entity cross-check 240/240 PASS")
    print("[N6-04] 240/240 frozen schedule adaptations provider-serialize")
    print("[N6-04] dynamic official-core dual-candidate stub tests=8/8 PASS")
    print(f"[N6-04] amendment_hash={amendment['amendment_hash']}")
    print("[N6-04] STOP. Upload v1.2 amendment artifacts. Do NOT run N6_05 yet.")

if __name__=="__main__":
    main()
