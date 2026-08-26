#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, random, statistics
from collections import Counter, defaultdict
from pathlib import Path
from n6_tech_common import *

def percentile(sorted_vals, q):
    if not sorted_vals: return None
    pos=(len(sorted_vals)-1)*q
    lo=int(pos); hi=min(lo+1,len(sorted_vals)-1)
    frac=pos-lo
    return sorted_vals[lo]*(1-frac)+sorted_vals[hi]*frac

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",default=".")
    args=ap.parse_args()
    project=Path(args.project_root).resolve()
    design,parent,audit=verify_parent(project)
    amendment_p=project/"N6_ATTRIGUARD_N3_PREFREEZE_v1_out/N6_TECHNICAL_AMENDMENT_v1_2.json"
    amendment=json.loads(amendment_p.read_text())
    ah=amendment.pop("amendment_hash")
    if stable_hash(amendment)!=ah: raise SystemExit("FATAL: amendment hash mismatch")
    amendment["amendment_hash"]=ah

    results_p=project/"n6_attriguard_n3_v1/scientific_v1/N6_RESULTS.jsonl"
    if not results_p.is_file(): raise SystemExit("FATAL: results missing")
    rows=[r for r in load_jsonl(results_p) if r.get("status")=="SUCCESS"]
    if len(rows)!=240: raise SystemExit(f"FATAL: confirmatory analysis requires 240/240 SUCCESS, got {len(rows)}")
    keys={(r["unit_id"],int(r["repeat"])) for r in rows}
    expected={(s["unit_id"],int(s["repeat"])) for s in parent["schedule"]}
    if keys!=expected: raise SystemExit("FATAL: result key set differs from frozen schedule")

    auth_n=sum(int(r["AUTH_blocked"]) for r in rows)
    alt_n=sum(int(r["ALT_blocked"]) for r in rows)
    z=[int(r["Z"]) for r in rows]
    if any(v not in (-1,0,1) for v in z): raise SystemExit("FATAL: invalid Z")

    bybase=defaultdict(list)
    for r in rows: bybase[r["base_id"]].append(r)
    if len(bybase)!=24 or any(len(v)!=10 for v in bybase.values()):
        raise SystemExit("FATAL: each of 24 bases must have 10 paired runs")
    gb={b:sum(int(r["Z"]) for r in rs)/10.0 for b,rs in bybase.items()}
    vals=list(gb.values())
    mean=sum(vals)/24
    median=statistics.median(vals)
    signs={
        "positive":sum(v>0 for v in vals),
        "zero":sum(v==0 for v in vals),
        "negative":sum(v<0 for v in vals),
    }

    rng=random.Random(20260813)
    boots=[]
    bases=sorted(gb)
    for _ in range(20000):
        samp=[gb[rng.choice(bases)] for _ in range(24)]
        boots.append(sum(samp)/24)
    boots.sort()
    ci=[percentile(boots,0.025),percentile(boots,0.975)]

    route={}
    for cand in ("AUTH","ALT"):
        route[cand]=dict(Counter(r[f"{cand}_route"] for r in rows))
    fam={}
    for f in sorted({r["family"] for r in rows}):
        rs=[r for r in rows if r["family"]==f]
        fam[f]={
            "n_pairs":len(rs),
            "AUTH_block_rate":sum(int(r["AUTH_blocked"]) for r in rs)/len(rs),
            "ALT_block_rate":sum(int(r["ALT_blocked"]) for r in rs)/len(rs),
            "mean_Z":sum(int(r["Z"]) for r in rs)/len(rs),
        }
    desc={}
    for d in sorted({r["descendant"] for r in rows}):
        rs=[r for r in rows if r["descendant"]==d]
        desc[d]={
            "n_pairs":len(rs),
            "AUTH_block_rate":sum(int(r["AUTH_blocked"]) for r in rs)/len(rs),
            "ALT_block_rate":sum(int(r["ALT_blocked"]) for r in rs)/len(rs),
            "mean_Z":sum(int(r["Z"]) for r in rs)/len(rs),
        }

    analysis={
        "schema":"N6_ATTRIGUARD_N3_ANALYSIS_V1",
        "status":"COMPLETE_240_OF_240",
        "parent_protocol_hash":PARENT_PROTOCOL_HASH,
        "technical_amendment_hash":ah,
        "primary":{
            "mean_G_b":mean,
            "median_G_b":median,
            "base_sign_counts":signs,
            "bootstrap_ci95_percentile":ci,
            "bootstrap_B":20000,
            "bootstrap_seed":20260813,
            "n_bases":24,
        },
        "absolute_operating_points":{
            "AUTH_blocked":auth_n,
            "AUTH_total":240,
            "AUTH_block_rate":auth_n/240,
            "ALT_blocked":alt_n,
            "ALT_total":240,
            "ALT_block_rate":alt_n/240,
        },
        "paired_repeat_counts":dict(Counter(z)),
        "route_decomposition":route,
        "family_descriptive":fam,
        "descendant_descriptive":desc,
        "per_base_G":gb,
        "interpretation_boundary":[
            "Controlled source-locked gate-level diagnostic only; not native proposal generation or end-to-end ASR/utility.",
            "No generic AttriGuard superiority claim.",
            "No semantic quantitative use of raw judge_reason outside structurally identified FUZZY_JUDGE_PATH.",
            "No threshold/lambda tuning or post-outcome exclusions."
        ]
    }
    out=project/"n6_attriguard_n3_v1/scientific_v1"
    apath=out/"N6_ANALYSIS.json"
    apath.write_text(json.dumps(analysis,indent=2,sort_keys=True)+"\n")
    report=f"""# N6 AttriGuard × N3 matched authorization-discrimination

**Status:** COMPLETE / 240 of 240 frozen paired runs

- AUTH block: {auth_n}/240 = {auth_n/240:.4f}
- ALT block: {alt_n}/240 = {alt_n/240:.4f}
- Mean G_b: {mean:+.6f}
- Median G_b: {median:+.6f}
- Base signs: + {signs['positive']} / 0 {signs['zero']} / - {signs['negative']}
- Paired whole-base bootstrap 95% CI: [{ci[0]:+.6f}, {ci[1]:+.6f}]

This is a controlled source-locked gate-level construct-validity diagnostic, not native-proposal/end-to-end AttriGuard ASR or utility.
"""
    (out/"N6_ANALYSIS.md").write_text(report)
    print("[N6-06] ANALYSIS COMPLETE")
    print(f"[N6-06] AUTH block {auth_n}/240={auth_n/240:.4f}")
    print(f"[N6-06] ALT block {alt_n}/240={alt_n/240:.4f}")
    print(f"[N6-06] mean_G_b={mean:+.6f} CI95=[{ci[0]:+.6f},{ci[1]:+.6f}]")
    print(f"[N6-06] base_signs={signs}")

if __name__=="__main__":
    main()
