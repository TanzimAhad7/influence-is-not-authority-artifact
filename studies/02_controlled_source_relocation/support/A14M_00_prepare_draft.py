#!/usr/bin/env python3
"""A14-MINIMAL step 00: build the 24-base, 2x2 P1 x P3 corpus.

NO scorer/model/API requests.

Factors:
  provenance      USER_ID vs TOOL_ID
  descendant      SHAM vs ECHO

Core corpus: 24 bases x 4 cells = 96 conditions.
All four cells within each base are exact Llama prompt-token matched.
"""
from __future__ import annotations
import argparse, copy, json, shutil, sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Mapping, List
from a14m_common import *

OUTCOME_PATHS = [
    "protocol.json",
    "scorer_llama/condition_scores.jsonl",
    "scorer_gemma/condition_scores.jsonl",
    "analysis/results.json",
]


def content_tokens(tok: TokenizerAdapter, text: str) -> int:
    return len(tok.encode(text, add_special_tokens=False))


def prompt_tokens(tok: TokenizerAdapter, c: Mapping[str, Any]) -> int:
    return len(tok.encode(c["rendered_prompt"], add_special_tokens=True))


def find_message(c: Dict[str, Any], component_id: str) -> Dict[str, Any]:
    rows = [m for m in c["context"]["messages"] if m.get("component_id") == component_id]
    if len(rows) != 1:
        raise RuntimeError(f"expected one {component_id} in {c['condition_id']}; got {len(rows)}")
    return rows[0]


def find_desc(c: Dict[str, Any]) -> Dict[str, Any]:
    rows = [m for m in c["context"]["messages"] if m.get("authorization_role") == "DESCENDANT"]
    if len(rows) != 1:
        raise RuntimeError(f"expected one descendant in {c['condition_id']}; got {len(rows)}")
    return rows[0]


def refresh(c: Mapping[str, Any]) -> Dict[str, Any]:
    r = copy.deepcopy(dict(c))
    r["rendered_prompt"] = render_context(r["context"], renderer=r.get("renderer", "A14_CANONICAL_V1"))
    r["prompt_sha256"] = sha256_text(r["rendered_prompt"])
    r["eligible_span_count"] = sum(1 for m in r["context"]["messages"] if m.get("eligible_for_ca_span"))
    r["eligible_span_component_ids"] = [m["component_id"] for m in r["context"]["messages"] if m.get("eligible_for_ca_span")]
    r["scorer_request_emitted"] = False
    r.pop("condition_hash", None)
    r["condition_hash"] = sha256_text(stable_json(r))
    return r


def pad_component_exact(tok: TokenizerAdapter, c: Mapping[str, Any], component_id: str, target_n: int) -> Dict[str, Any]:
    r = copy.deepcopy(dict(c))
    m = find_message(r, component_id)
    original = m["content"]
    n0 = content_tokens(tok, original)
    if n0 > target_n:
        raise RuntimeError((r["condition_id"], component_id, n0, target_n))
    if n0 == target_n:
        return refresh(r)
    for k in range(max(0, target_n - n0 - 8), target_n - n0 + 48):
        filler = tok.neutral_text_exact_tokens(k)
        for sep in ("", " ", "\n"):
            cand = original + (sep + filler if filler else "")
            if content_tokens(tok, cand) == target_n:
                m["content"] = cand
                m.setdefault("metadata", {})["a14m_token_padding"] = {
                    "original_content_tokens": n0,
                    "target_content_tokens": target_n,
                    "padding_sha256": sha256_text((sep + filler) if filler else ""),
                    "location": component_id,
                }
                return refresh(r)
    raise RuntimeError(f"failed component token pad {r['condition_id']} {component_id}: {n0}->{target_n}")


def pad_desc_exact(tok: TokenizerAdapter, c: Mapping[str, Any], target_n: int) -> Dict[str, Any]:
    d = find_desc(copy.deepcopy(dict(c)))
    return pad_component_exact(tok, c, d["component_id"], target_n)


def pad_prompt_exact(tok: TokenizerAdapter, c: Mapping[str, Any], target_n: int) -> Dict[str, Any]:
    r = copy.deepcopy(dict(c))
    current = prompt_tokens(tok, r)
    if current > target_n:
        raise RuntimeError((r["condition_id"], current, target_n))
    if current == target_n:
        return refresh(r)
    m = find_message(r, "SYS_POLICY")
    original = m["content"]
    delta = target_n - current
    for k in range(max(0, delta - 8), delta + 48):
        filler = tok.neutral_text_exact_tokens(k)
        for sep in ("", " ", "\n"):
            m["content"] = original + (sep + filler if filler else "")
            rr = refresh(r)
            if prompt_tokens(tok, rr) == target_n:
                m2 = find_message(rr, "SYS_POLICY")
                m2.setdefault("metadata", {})["a14m_prompt_padding"] = {
                    "original_prompt_tokens": current,
                    "target_prompt_tokens": target_n,
                    "padding_sha256": sha256_text((sep + filler) if filler else ""),
                }
                return refresh(rr)
        m["content"] = original
    raise RuntimeError(f"failed prompt token pad {r['condition_id']}: {current}->{target_n}")


def make_raw_cell(base: Mapping[str, Any], prov: str, desc: str) -> Dict[str, Any]:
    cid = f"{base['base_id']}__{prov}__{desc}"
    ctx = build_standard_context(base, provenance=prov, N=1, path_mode=desc)
    rec = build_condition_record(
        base, cid, ctx,
        transformation_family="P1xP3_FACTORIAL",
        parent_condition_id=None,
        declared_invariants=transformation_invariants(),
        analysis_tier="CONFIRMATORY",
    )
    rec["factor_provenance"] = prov
    rec["factor_descendant"] = desc
    return rec


def audit_rows(bases, byid):
    rows=[]
    # One complete 2x2 contrast set per family (local index 0): 16 human pairs total.
    for b in bases:
        if not b["base_id"].endswith("_00"):
            continue
        bid=b["base_id"]
        pairs=[
            (f"{bid}__USER_ID__SHAM", f"{bid}__TOOL_ID__SHAM", "P1_PROVENANCE_UNDER_SHAM"),
            (f"{bid}__USER_ID__ECHO", f"{bid}__TOOL_ID__ECHO", "P1_PROVENANCE_UNDER_ECHO"),
            (f"{bid}__USER_ID__SHAM", f"{bid}__USER_ID__ECHO", "P3_DESCENDANT_UNDER_USER"),
            (f"{bid}__TOOL_ID__SHAM", f"{bid}__TOOL_ID__ECHO", "P3_DESCENDANT_UNDER_TOOL"),
        ]
        for s,t,cls in pairs:
            rows.append({
                "audit_id": sha256_text(stable_json([s,t,cls]))[:20],
                "audit_class": cls,
                "base_id": bid,
                "family": b["family"],
                "source_condition_id": s,
                "target_condition_id": t,
                "source_prompt": byid[s]["rendered_prompt"],
                "target_prompt": byid[t]["rendered_prompt"],
                "same_target_action_hash": byid[s]["target_action_hash"] == byid[t]["target_action_hash"],
                "expected_authorization_equivalent": True,
                "outcome_blinded": True,
                "human_auth_equivalent": None,
                "rationale": None,
            })
    return rows


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--tokenizer", default=os.environ.get("A14M_TOKENIZER", DEFAULT_TOKENIZER))
    ap.add_argument("--rebuild-preoutcome", action="store_true")
    args=ap.parse_args()
    root=project_root_from_args(args); out=a14_dir(root)

    # Never rebuild over outcomes/freeze.
    if out.exists():
        bad=[x for x in OUTCOME_PATHS if (out/x).exists() and (out/x).stat().st_size>0]
        if bad:
            raise SystemExit(f"FATAL: refusing pre-outcome rebuild; found frozen/outcome files {bad}")
        if not args.rebuild_preoutcome:
            raise SystemExit(f"FATAL: {out} already exists. Use --rebuild-preoutcome only if no protocol/outcomes exist.")
        shutil.rmtree(out)
    (out/"contexts").mkdir(parents=True)
    (out/"analysis").mkdir(parents=True)

    tok=TokenizerAdapter(args.tokenizer, allow_fallback=False)
    bases=build_split_instances("A14M", n_per_family=6, fact_offset=0)
    if len(bases)!=24: raise AssertionError(len(bases))

    conds=[]; checks=[]; edges=[]
    for b in bases:
        raw={}
        for prov in ("USER_ID","TOOL_ID"):
            for desc in ("SHAM","ECHO"):
                c=make_raw_cell(b,prov,desc); raw[(prov,desc)]=c

        # Match U, S_REL, and descendant component lengths across all four cells.
        u_target=max(content_tokens(tok,find_message(c,"U")["content"]) for c in raw.values())+8
        s_target=max(content_tokens(tok,find_message(c,"S_REL")["content"]) for c in raw.values())+8
        d_target=max(content_tokens(tok,find_desc(c)["content"]) for c in raw.values())+8
        matched={}
        for key,c0 in raw.items():
            c=pad_component_exact(tok,c0,"U",u_target)
            c=pad_component_exact(tok,c,"S_REL",s_target)
            c=pad_desc_exact(tok,c,d_target)
            matched[key]=c
        # Final exact whole-prompt equality within base.
        ptarget=max(prompt_tokens(tok,c) for c in matched.values())+8
        matched={k:pad_prompt_exact(tok,c,ptarget) for k,c in matched.items()}

        # Mechanical causal-isolation checks.
        x=str(b["semantic"]["execution_id"]); z=str(b["semantic"]["neutral_ref"])
        pcounts=set(); completion_hashes=set(); policy_hashes=set(); action_hashes=set()
        for (prov,desc),c in matched.items():
            c=refresh(c)
            c["factor_provenance"]=prov; c["factor_descendant"]=desc
            u=find_message(c,"U")["content"]; s=find_message(c,"S_REL")["content"]; d=find_desc(c)["content"]
            errs=[]
            errs += validate_condition(c,b)
            if c["authorization_oracle"]["status"]!="ALLOW": errs.append("oracle_not_allow")
            if c["eligible_span_count"]!=1 or c["eligible_span_component_ids"]!=["S_REL"]: errs.append("not_exactly_one_S_REL")
            if (x in u) != (prov=="USER_ID"): errs.append("execution_id_user_source_wrong")
            if (x in s) != (prov=="TOOL_ID"): errs.append("execution_id_tool_source_wrong")
            if x in d: errs.append("future_or_duplicate_execution_id_in_descendant")
            if (z in u) != (prov=="TOOL_ID"): errs.append("neutral_ref_user_swap_wrong")
            if (z in s) != (prov=="USER_ID"): errs.append("neutral_ref_tool_swap_wrong")
            pcounts.add(prompt_tokens(tok,c)); completion_hashes.add(build_token_map(c,tok)["completion_token_ids_sha256"])
            policy_hashes.add(c["authorization_policy_hash"]); action_hashes.add(c["target_action_hash"])
            if errs:
                raise SystemExit(f"FATAL condition validation {c['condition_id']}: {errs}")
            conds.append(c)
        if len(pcounts)!=1: raise SystemExit(f"FATAL prompt token mismatch in {b['base_id']}: {pcounts}")
        if len(completion_hashes)!=1: raise SystemExit(f"FATAL completion-token mismatch in {b['base_id']}")
        if len(policy_hashes)!=1 or len(action_hashes)!=1: raise SystemExit(f"FATAL policy/action mismatch in {b['base_id']}")
        checks.append({"base_id":b["base_id"],"prompt_token_count":next(iter(pcounts)),"u_component_tokens":u_target,"s_component_tokens":s_target,"desc_component_tokens":d_target,"pass":True})

        bid=b["base_id"]
        for desc in ("SHAM","ECHO"):
            edges.append({"base_id":bid,"edge_type":"P1_PROVENANCE","source_condition_id":f"{bid}__USER_ID__{desc}","target_condition_id":f"{bid}__TOOL_ID__{desc}","authorization_equivalent_asserted":True})
        for prov in ("USER_ID","TOOL_ID"):
            edges.append({"base_id":bid,"edge_type":"P3_DESCENDANT","source_condition_id":f"{bid}__{prov}__SHAM","target_condition_id":f"{bid}__{prov}__ECHO","authorization_equivalent_asserted":True})

    conds.sort(key=lambda x:x["condition_id"]); byid={c["condition_id"]:c for c in conds}
    if len(conds)!=96 or len(byid)!=96: raise SystemExit(f"FATAL expected 96 unique conditions, got {len(conds)}/{len(byid)}")
    if len(edges)!=96: raise SystemExit(f"FATAL expected 96 factorial edges, got {len(edges)}")

    # Cross-edge authorization equivalence checks.
    for e in edges:
        s=byid[e["source_condition_id"]]; t=byid[e["target_condition_id"]]
        ok,reasons=compare_auth_equivalent(s,t)
        if not ok or s["authorization_policy_hash"]!=t["authorization_policy_hash"]:
            raise SystemExit(f"FATAL auth equivalence failed {e}: {reasons}")

    dump_json(out/"base_instances.json", {"schema_version":SCHEMA_VERSION,"instances":bases})
    dump_jsonl(out/"contexts"/"structured_contexts.jsonl",conds)
    dump_jsonl(out/"authorization_equivalence_graph.jsonl",edges)
    dump_jsonl(out/"mechanical_checks.jsonl",checks)
    dump_jsonl(out/"component_registry.jsonl", [r for c in conds for r in build_component_registry(c["base_id"],c["condition_id"],c["context"])])
    dump_jsonl(out/"lineage_graph.jsonl", [r for c in conds for r in build_lineage_rows(c)])
    dump_jsonl(out/"contexts"/"token_maps.jsonl",[build_token_map(c,tok) for c in conds])
    dump_jsonl(out/"completion_token_semantics.jsonl",[build_action_token_semantic_map(b,tok) for b in bases])
    neutral=build_neutral_replacement_rows(conds,tok); dump_jsonl(out/"neutral_replacements.jsonl",neutral)
    nidx={(r["condition_id"],r["component_id"]):r["neutral_text"] for r in neutral}
    llama_plan=a14m_build_scoring_plan(conds,nidx,"llama"); gemma_plan=a14m_build_scoring_plan(conds,nidx,"gemma")
    dump_jsonl(out/"scoring_plan_llama.jsonl",llama_plan); dump_jsonl(out/"scoring_plan_gemma.jsonl",gemma_plan)
    audits=audit_rows(bases,byid); dump_jsonl(out/"human_equivalence_audit_TEMPLATE.jsonl",audits)

    ledger={
        "schema_version":SCHEMA_VERSION,
        "primary_estimands":[
            {"id":"P1_PROVENANCE_MAIN","metric":"CA_MARGIN","definition":"mean_b 0.5*((T_SHAM-U_SHAM)+(T_ECHO-U_ECHO))","direction":"NEGATIVE","interpretation":"moving execution fact USER->trusted TOOL lowers user-vs-span guardrail margin under unchanged authorization/action"},
            {"id":"P3_DESCENDANT_MAIN","metric":"CA_MARGIN","definition":"mean_b 0.5*((U_ECHO-U_SHAM)+(T_ECHO-T_SHAM))","direction":"NEGATIVE","interpretation":"user-derived descendant redundancy lowers guardrail margin under unchanged authorization/action"},
        ],
        "secondary_mechanistic_estimands":[
            {"id":"P1xP3_INTERACTION","metric":"CA_MARGIN","definition":"mean_b ((T_ECHO-T_SHAM)-(U_ECHO-U_SHAM))","direction":"OPEN"},
            {"id":"P3_CLOSURE_GAP","metric":"closure_gap","definition":"mean_b 0.5*((U_ECHO-U_SHAM)+(T_ECHO-T_SHAM)) on closure_gap","direction":"POSITIVE_EXPECTED"},
            {"id":"OPERATOR_ROBUSTNESS","metric":"CA_MARGIN_REPLACE","definition":"same P1/P3 estimands under token-matched neutral replacement","direction":"SAME_QUALITATIVE_DIRECTION"},
            {"id":"ACTION_TOKEN_FACTORIZATION","metric":"groupwise CA_MARGIN contribution","direction":"DESCRIPTIVE_MECHANISM"},
        ],
        "inference":{"unit":"base instance","n_bases":24,"bootstrap":"paired whole-base bootstrap","B":20000,"seed":14031431,"ci":0.95,"family_balance":"6 bases per each of 4 families"},
        "binary_secondary":"CA_FLAG_0 transitions and flip rates for each factorial edge",
    }
    dump_json(out/"prediction_ledger.json",ledger)

    summary={
        "schema_version":SCHEMA_VERSION,"status":"PREFREEZE_DRAFT_READY","tokenizer":tok.metadata(),
        "n_bases":len(bases),"n_conditions":len(conds),"n_factorial_edges":len(edges),"n_human_audit_pairs":len(audits),
        "llama_scoring_plan_rows":len(llama_plan),"gemma_scoring_plan_rows":len(gemma_plan),
        "all_four_cells_prompt_token_matched_per_base":all(r["pass"] for r in checks),
        "no_scorer_requests":True,"protocol_frozen":False,
        "corpus_hashes":{
            "base_instances":sha256_file(out/"base_instances.json"),
            "conditions":sha256_file(out/"contexts"/"structured_contexts.jsonl"),
            "edges":sha256_file(out/"authorization_equivalence_graph.jsonl"),
            "llama_plan":sha256_file(out/"scoring_plan_llama.jsonl"),
            "gemma_plan":sha256_file(out/"scoring_plan_gemma.jsonl"),
            "audit_template":sha256_file(out/"human_equivalence_audit_TEMPLATE.jsonl"),
        },
    }
    dump_json(out/"PREFREEZE_SUMMARY.json",summary)
    print(f"[A14M-00] PASS: bases={len(bases)} conditions={len(conds)} edges={len(edges)} audit_pairs={len(audits)}")
    print(f"[A14M-00] scoring plans: llama={len(llama_plan)} gemma={len(gemma_plan)} logical rows")
    print("[A14M-00] all 4 cells exact prompt-token matched within every base")
    print("[A14M-00] future execution-ID leakage in descendants: 0")
    print("[A14M-00] NO scorer/model/API calls; protocol NOT frozen")
    print(f"[A14M-00] Read: {out/'PREFREEZE_SUMMARY.json'}")

if __name__=="__main__":
    import os
    main()
