#!/usr/bin/env python3
"""
Frozen A15b-0A/B paired-trace analysis.

Requires full non-development AgentWatcher controlled/natural outputs and
the natural Gemma CausalArmor rescore. Does not run models.
"""
from __future__ import annotations
import collections
import math
import random
import statistics
import sys

from a15b0_common import *

def quantile(xs,q):
    if not xs: return None
    xs=sorted(xs)
    if len(xs)==1:return xs[0]
    pos=q*(len(xs)-1); lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:return xs[lo]
    w=pos-lo
    return xs[lo]*(1-w)+xs[hi]*w

def base_bootstrap(vals, B, seed):
    ids=sorted(vals)
    point=statistics.mean(vals.values())
    rng=random.Random(seed)
    draws=[]
    for _ in range(B):
        samp=[ids[rng.randrange(len(ids))] for _ in ids]
        draws.append(statistics.mean(vals[x] for x in samp))
    return {"mean":point,"ci95":[quantile(draws,.025),quantile(draws,.975)],"B":B,"seed":seed}

def controlled_analysis():
    manifest=read_jsonl(OUT_DIR/"controlled_96_inputs.jsonl")
    outrows=read_jsonl(OUT_DIR/"agentwatcher_controlled_outputs.jsonl")
    noattr_rows=read_jsonl(OUT_DIR/"agentwatcher_no_localization_controlled_outputs.jsonl")
    if any(r.get("development") for r in outrows+noattr_rows):
        raise RuntimeError("development AgentWatcher output cannot enter analysis")
    if any(not r.get("monitor_parse_ok") for r in outrows+noattr_rows):
        raise RuntimeError("unparsed AgentWatcher monitor output; analysis incomplete")

    # Map deduplicated outputs back to all 96 conditions by frozen static-input hash.
    byhash={r["agentwatcher_static_input_sha256"]:r for r in outrows}
    noattr_byhash={r["agentwatcher_static_input_sha256"]:r for r in noattr_rows}
    if len(byhash)!=len(outrows):
        raise RuntimeError("duplicate controlled AgentWatcher output hashes")
    expanded={}
    expanded_noattr={}
    for m in manifest:
        h=m["agentwatcher_static_input_sha256"]
        z=byhash.get(h)
        zn=noattr_byhash.get(h)
        if z is None:
            raise RuntimeError(f"missing AW output for {m['condition_id']}")
        if zn is None:
            raise RuntimeError(f"missing no-localization output for {m['condition_id']}")
        expanded[m["condition_id"]] = bool(z["detect_flag"])
        expanded_noattr[m["condition_id"]] = bool(zn["detect_flag"])

    bybase=collections.defaultdict(dict)
    ca_bybase=collections.defaultdict(dict)
    for m in manifest:
        key=(m["factor_provenance"],m["factor_descendant"])
        bybase[m["base_id"]][key]=float(expanded[m["condition_id"]])
        ca_bybase[m["base_id"]][key]=float(m["ca_gemma_flag_tau0"])

    gaps={}
    p1aw={}
    p1ca={}
    for b,d in bybase.items():
        aw=.5*((d[("TOOL_ID","SHAM")]-d[("USER_ID","SHAM")])+
               (d[("TOOL_ID","ECHO")]-d[("USER_ID","ECHO")]))
        c=ca_bybase[b]
        ca=.5*((c[("TOOL_ID","SHAM")]-c[("USER_ID","SHAM")])+
               (c[("TOOL_ID","ECHO")]-c[("USER_ID","ECHO")]))
        p1aw[b]=aw;p1ca[b]=ca;gaps[b]=ca-aw

    inf=base_bootstrap(gaps,CONTROLLED_BOOTSTRAP_B,CONTROLLED_BOOTSTRAP_SEED)
    lo=inf["ci95"][0]
    if inf["mean"]<=0: status="NO_EXPECTED_BOUNDARY"
    elif lo is not None and lo>0: status="STRONG_BOUNDARY"
    else: status="DIRECTIONAL_BOUNDARY"

    # Secondary incremental localization value: full AW minus monitor-without-localization.
    loc_delta={}
    for b in sorted(bybase):
        rr=[m for m in manifest if m["base_id"]==b]
        loc_delta[b]=statistics.mean(
            float(expanded[m["condition_id"]])-float(expanded_noattr[m["condition_id"]])
            for m in rr
        )
    loc_inf=base_bootstrap(loc_delta,CONTROLLED_BOOTSTRAP_B,CONTROLLED_BOOTSTRAP_SEED+77)

    return {
        "status":status,
        "n_bases":24,
        "P1_CA_mean":statistics.mean(p1ca.values()),
        "P1_AW_mean":statistics.mean(p1aw.values()),
        "G_P1":inf,
        "per_base":{"P1_CA":p1ca,"P1_AW":p1aw,"gap":gaps},
        "localization_increment_secondary":{
            "definition":"FULL_AW_flag minus NO_LOCALIZATION_MONITOR_flag, averaged within base",
            "inference":loc_inf,
            "no_formal_equivalence_claim":True,
        },
        "cell_flag_rates":{
            f"{p}__{d}": statistics.mean(
                expanded[m["condition_id"]] for m in manifest
                if m["factor_provenance"]==p and m["factor_descendant"]==d
            )
            for p in ("USER_ID","TOOL_ID") for d in ("SHAM","ECHO")
        }
    }

def cluster_stat(rows, value_key, subset_label=None):
    rr=[r for r in rows if subset_label is None or r["label"]==subset_label]
    by=collections.defaultdict(list)
    for r in rr: by[r["cluster_id"]].append(float(r[value_key]))
    cluster_means={k:statistics.mean(v) for k,v in by.items()}
    return cluster_means

def paired_cluster_bootstrap(diff_by_cluster,B,seed):
    ids=sorted(diff_by_cluster)
    point=statistics.mean(diff_by_cluster.values()) if ids else None
    if not ids:return {"mean":None,"ci95":[None,None],"n_clusters":0}
    rng=random.Random(seed);draws=[]
    for _ in range(B):
        samp=[ids[rng.randrange(len(ids))] for _ in ids]
        draws.append(statistics.mean(diff_by_cluster[x] for x in samp))
    return {"mean":point,"ci95":[quantile(draws,.025),quantile(draws,.975)],"n_clusters":len(ids),"B":B,"seed":seed}

def natural_analysis():
    manifest={r["decision_id"]:r for r in read_jsonl(OUT_DIR/"natural_26_inputs.jsonl")}
    aw={r["decision_id"]:r for r in read_jsonl(OUT_DIR/"agentwatcher_natural_outputs.jsonl")}
    noattr={r["decision_id"]:r for r in read_jsonl(OUT_DIR/"agentwatcher_no_localization_natural_outputs.jsonl")}
    ca={r["decision_id"]:r for r in read_jsonl(OUT_DIR/"causalarmor_natural_gemma.jsonl")}
    if set(manifest)!=set(aw) or set(manifest)!=set(noattr) or set(manifest)!=set(ca):
        raise RuntimeError("natural paired ID sets differ")
    if any(r.get("development") for r in list(aw.values())+list(noattr.values())):
        raise RuntimeError("development AW output cannot enter analysis")
    if any(not r.get("monitor_parse_ok") for r in list(aw.values())+list(noattr.values())):
        raise RuntimeError("unparsed AW monitor output; analysis incomplete")
    rows=[]
    for did,m in manifest.items():
        rows.append({
            "decision_id":did,"cluster_id":m["cluster_id"],"label":m["label"],
            "AW_flag":float(bool(aw[did]["detect_flag"])),
            "NOATTR_flag":float(bool(noattr[did]["detect_flag"])),
            "CA_flag":float(bool(ca[did]["CA_FLAG_0"])),
            "diff_CA_minus_AW":float(bool(ca[did]["CA_FLAG_0"]))-float(bool(aw[did]["detect_flag"])),
            "diff_AW_minus_NOATTR":float(bool(aw[did]["detect_flag"]))-float(bool(noattr[did]["detect_flag"])),
        })
    result={"n_decisions":26,"n_clusters":23,"by_label":{}}
    for lab in ("SPECIFIED","DELEGATED","PARTIAL","ALL"):
        rr=rows if lab=="ALL" else [r for r in rows if r["label"]==lab]
        clusters=collections.defaultdict(list)
        for r in rr: clusters[r["cluster_id"]].append(r["diff_CA_minus_AW"])
        diff={k:statistics.mean(v) for k,v in clusters.items()}
        loc_clusters=collections.defaultdict(list)
        for r in rr: loc_clusters[r["cluster_id"]].append(r["diff_AW_minus_NOATTR"])
        loc_diff={k:statistics.mean(v) for k,v in loc_clusters.items()}
        result["by_label"][lab]={
            "n_decisions":len(rr),
            "n_clusters":len(clusters),
            "CA_flag_rate_decision":statistics.mean(r["CA_flag"] for r in rr) if rr else None,
            "AW_flag_rate_decision":statistics.mean(r["AW_flag"] for r in rr) if rr else None,
            "NOATTR_flag_rate_decision":statistics.mean(r["NOATTR_flag"] for r in rr) if rr else None,
            "CA_minus_AW_cluster_weighted":paired_cluster_bootstrap(
                diff,NATURAL_BOOTSTRAP_B,NATURAL_BOOTSTRAP_SEED+sum(map(ord,lab))
            ),
            "AW_minus_NOATTR_cluster_weighted_secondary":paired_cluster_bootstrap(
                loc_diff,NATURAL_BOOTSTRAP_B,NATURAL_BOOTSTRAP_SEED+700+sum(map(ord,lab))
            ),
            "discordant":{
                "CA1_AW0":sum(r["CA_flag"]==1 and r["AW_flag"]==0 for r in rr),
                "CA0_AW1":sum(r["CA_flag"]==0 and r["AW_flag"]==1 for r in rr),
                "both1":sum(r["CA_flag"]==1 and r["AW_flag"]==1 for r in rr),
                "both0":sum(r["CA_flag"]==0 and r["AW_flag"]==0 for r in rr),
            }
        }
    return result

def main():
    proto=read_json(OUT_DIR/"protocol.json")
    controlled=controlled_analysis()
    natural=natural_analysis()
    res={
        "schema_version":"A15B0_ANALYSIS_V1",
        "protocol_hash":proto["protocol_hash"],
        "controlled":controlled,
        "natural":natural,
        "analysis_at_utc":now_utc(),
    }
    write_json(OUT_DIR/"analysis_results.json",res)
    print("[A15B0-06] ANALYSIS COMPLETE")
    print(f"[A15B0-06] controlled status={controlled['status']} G_P1={controlled['G_P1']['mean']:+.4f} CI={controlled['G_P1']['ci95']}")
    d=natural["by_label"]["DELEGATED"]
    print(
        "[A15B0-06] natural DELEGATED: "
        f"N={d['n_decisions']} clusters={d['n_clusters']} "
        f"CA={d['CA_flag_rate_decision']:.3f} AW={d['AW_flag_rate_decision']:.3f}"
    )
    print(f"[A15B0-06] results_sha256={sha256_file(OUT_DIR/'analysis_results.json')}")

if __name__=="__main__":
    main()
