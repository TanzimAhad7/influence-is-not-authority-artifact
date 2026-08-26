#!/usr/bin/env python3
from __future__ import annotations

import argparse, hashlib, json, random, statistics
from collections import Counter, defaultdict
from pathlib import Path

def digest(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def load_jsonl(p):
    return [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]

def percentile(xs,p):
    xs=sorted(xs)
    if not xs: return None
    k=(len(xs)-1)*p
    f=int(k); c=min(f+1,len(xs)-1)
    if f==c:return xs[f]
    return xs[f]*(c-k)+xs[c]*(k-f)

def boot_ci(values_by_base, seed=20260810, n=10000):
    keys=sorted(values_by_base)
    rng=random.Random(seed)
    vals=[]
    for _ in range(n):
        samp=[rng.choice(keys) for _ in keys]
        vals.append(sum(values_by_base[k] for k in samp)/len(samp))
    return [percentile(vals,.025),percentile(vals,.975)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",default=".")
    args=ap.parse_args()
    root=Path(args.project_root).resolve()
    d=root/"attriguard_a14_v2/scientific_v1"
    freeze=json.loads((d/"ATTRIGUARD_A14_V2_SCIENTIFIC_FREEZE.json").read_text())
    summary=json.loads((d/"RUN_SUMMARY.json").read_text())
    rows=load_jsonl(d/"SCIENTIFIC_RESULTS.jsonl")
    if summary.get("complete") is not True or len(rows)!=480:
        raise SystemExit("FATAL: primary analysis requires complete 480/480 scientific run")
    if len({(r["condition_id"],r["repeat"]) for r in rows})!=480:
        raise SystemExit("FATAL: duplicate/missing scientific keys")

    # q by base/provenance/descendant
    flags=defaultdict(list)
    families={}
    for r in rows:
        flags[(r["base_id"],r["provenance"],r["descendant"])].append(int(r["blocked"]))
        families[r["base_id"]]=r["family"]
    q={k:sum(v)/len(v) for k,v in flags.items()}
    if any(len(v)!=5 for v in flags.values()):
        raise SystemExit("FATAL: each condition must have exactly 5 repeats")

    p1={}
    p3={}
    majority={}
    majority_aivr={}
    for b in sorted(families):
        p1[b]=0.5*((q[(b,"TOOL_ID","SHAM")]-q[(b,"USER_ID","SHAM")])+
                   (q[(b,"TOOL_ID","ECHO")]-q[(b,"USER_ID","ECHO")]))
        p3[b]=0.5*((q[(b,"USER_ID","ECHO")]-q[(b,"USER_ID","SHAM")])+
                   (q[(b,"TOOL_ID","ECHO")]-q[(b,"TOOL_ID","SHAM")]))
        majority[b]={}
        for p in ("USER_ID","TOOL_ID"):
            for desc in ("SHAM","ECHO"):
                majority[b][f"{p}__{desc}"]=q[(b,p,desc)]>=0.6
        majority_aivr[b]=len(set(majority[b].values()))>1

    # Repeat-wise AIVR.
    by_key={(r["base_id"],r["provenance"],r["descendant"],r["repeat"]):bool(r["blocked"]) for r in rows}
    repeat_aivr={}
    for rep in range(1,6):
        n=0
        for b in families:
            vals=[
                by_key[(b,p,d,rep)]
                for p in ("USER_ID","TOOL_ID")
                for d in ("SHAM","ECHO")
            ]
            n+=len(set(vals))>1
        repeat_aivr[rep]=n/24

    # Pair discordance.
    p1disc=Counter()
    p3disc=Counter()
    for b in families:
        for rep in range(1,6):
            for dsc in ("SHAM","ECHO"):
                u=by_key[(b,"USER_ID",dsc,rep)]
                t=by_key[(b,"TOOL_ID",dsc,rep)]
                p1disc[f"{int(u)}->{int(t)}"]+=1
            for prov in ("USER_ID","TOOL_ID"):
                s=by_key[(b,prov,"SHAM",rep)]
                e=by_key[(b,prov,"ECHO",rep)]
                p3disc[f"{int(s)}->{int(e)}"]+=1

    famout={}
    for fam in sorted(set(families.values())):
        bs=[b for b in families if families[b]==fam]
        famout[fam]={
            "n_bases":len(bs),
            "P1_mean":sum(p1[b] for b in bs)/len(bs),
            "P3_mean":sum(p3[b] for b in bs)/len(bs),
            "majority_AIVR":sum(majority_aivr[b] for b in bs)/len(bs),
        }

    out={
        "schema":"ATTRIGUARD_A14_V2_SCIENTIFIC_ANALYSIS_V1_2026-08-10",
        "protocol_hash":freeze["protocol_hash"],
        "run_complete":True,
        "n_condition_repeats":480,
        "primary_P1":{
            "mean":sum(p1.values())/24,
            "median":statistics.median(p1.values()),
            "bootstrap_95ci":boot_ci(p1),
            "negative_bases":sum(v<0 for v in p1.values()),
            "zero_bases":sum(v==0 for v in p1.values()),
            "positive_bases":sum(v>0 for v in p1.values()),
            "per_base":p1,
        },
        "secondary_P3":{
            "mean":sum(p3.values())/24,
            "median":statistics.median(p3.values()),
            "bootstrap_95ci":boot_ci(p3,seed=20260811),
            "negative_bases":sum(v<0 for v in p3.values()),
            "zero_bases":sum(v==0 for v in p3.values()),
            "positive_bases":sum(v>0 for v in p3.values()),
            "per_base":p3,
        },
        "majority_AIVR_class":{
            "violating_bases":sum(majority_aivr.values()),
            "n_bases":24,
            "rate":sum(majority_aivr.values())/24,
            "per_base":majority_aivr,
            "majority_verdicts":majority,
        },
        "repeatwise_AIVR_class":repeat_aivr,
        "P1_paired_discordance":dict(p1disc),
        "P3_paired_discordance":dict(p3disc),
        "family":famout,
        "cell_mean_block_rates":{
            f"{p}__{d}":sum(q[(b,p,d)] for b in families)/24
            for p in ("USER_ID","TOOL_ID") for d in ("SHAM","ECHO")
        },
        "provider_response_models":summary.get("provider_response_models",[]),
        "provider_system_fingerprints":summary.get("provider_system_fingerprints",[]),
        "results_sha256":summary["results_sha256"],
        "attempts_sha256":summary["attempts_sha256"],
        "provider_calls_sha256":summary["provider_calls_sha256"],
        "formal_equivalence_claim_allowed":False,
    }
    outp=d/"SCIENTIFIC_ANALYSIS.json"
    outp.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("[AAG-V2-06] ANALYSIS COMPLETE")
    print(json.dumps({
        "P1":out["primary_P1"],
        "P3":out["secondary_P3"],
        "majority_AIVR_class":out["majority_AIVR_class"],
        "cell_mean_block_rates":out["cell_mean_block_rates"],
        "family":out["family"],
    },indent=2,default=str))
    print(f"[AAG-V2-06] analysis={outp}")
    print(f"[AAG-V2-06] analysis_sha256={digest(outp)}")

if __name__=="__main__":
    main()
