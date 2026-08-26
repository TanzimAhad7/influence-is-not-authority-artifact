#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from collections import defaultdict

def readj(p): return json.loads(Path(p).read_text())
def readjl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]

def summarize(run):
    run=Path(run)
    rows=readjl(run/"P2B_XMODEL_BASELINE_RAW.jsonl")
    f=readj(run/"P2B_XMODEL_FREEZE.json")
    av=readj(run/"P2B_ARGUMENT_VOLATILITY.json")
    if av["freeze_sha256"] != f["freeze_sha256"]:
        raise SystemExit(f"FATAL argument-volatility freeze mismatch in {run}")
    by=defaultdict(list)
    for r in rows: by[r["decision_id"]].append(r)
    per={d:sum(bool(x["utility_preserved"]) for x in rs) for d,rs in sorted(by.items())}
    act=[r for r in rows if r["activated_tau0"]]
    ctl=[r for r in rows if not r["activated_tau0"]]
    return {
      "model_key":f["model_key"],"model_id":f["runtime"]["served_model_id"],
      "freeze_sha256":f["freeze_sha256"],"rows":len(rows),
      "overall":sum(bool(r["utility_preserved"]) for r in rows)/len(rows),
      "majority":sum(v>=3 for v in per.values()),"strong":sum(v>=4 for v in per.values()),
      "activated":sum(bool(r["utility_preserved"]) for r in act)/len(act),
      "controls":sum(bool(r["utility_preserved"]) for r in ctl)/len(ctl),
      "parser_failures":sum(bool(r.get("adapter_parse_error")) for r in rows),
      "no_calls":sum(r["candidate_n_tool_calls"]==0 for r in rows),
      "multi_calls":sum(r["candidate_n_tool_calls"]>1 for r in rows),
      "target_function_match":sum(bool(r["target_function_match"]) for r in rows)/len(rows),
      "exact_target":sum(bool(r["exact_target_action_reproduction"]) for r in rows)/len(rows),
      "per_decision":per,"weak":[d for d,v in per.items() if v<3],
      "argument_volatility":av,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--llama-run",required=True)
    ap.add_argument("--gemma-run",required=True)
    ap.add_argument("--qwen-run",required=True)
    ap.add_argument("--out-dir",required=True)
    a=ap.parse_args()
    models=[summarize(a.llama_run),summarize(a.gemma_run),summarize(a.qwen_run)]
    weak_sets=[set(m["weak"]) for m in models]
    all3=sorted(set.intersection(*weak_sets)) if weak_sets else []
    any2=sorted({d for d in set.union(*weak_sets) if sum(d in s for s in weak_sets)>=2})

    contrast_names=[
        "OPEN_TEXT_minus_REFERENCE_IDENTITY",
        "STRUCTURED_SCALAR_minus_REFERENCE_IDENTITY",
        "OPEN_TEXT_minus_STRUCTURED_SCALAR",
    ]
    contrast_joint={}
    for name in contrast_names:
        vals=[]
        for m in models:
            c=m["argument_volatility"]["paired_contrasts"][name]
            vals.append({
                "model_key":m["model_key"],
                "n":c["n"],
                "mean":c["mean"],
                "ci95":c["ci95"],
            })
        directional_expected = name in {
            "OPEN_TEXT_minus_REFERENCE_IDENTITY",
            "STRUCTURED_SCALAR_minus_REFERENCE_IDENTITY",
        }
        directionally_replicated = (
            directional_expected
            and all(x["mean"] is not None and x["mean"] < 0 for x in vals)
        )
        contrast_joint[name]={
            "models":vals,
            "predeclared_negative_direction":directional_expected,
            "three_of_three_negative":directionally_replicated if directional_expected else None,
        }

    obj={
        "schema":"P2B_XMODEL_JOINT_V1_3_ARGUMENT_ROLE_ENDPOINT",
        "models":models,
        "weak_all_three":all3,
        "weak_at_least_two":any2,
        "argument_role_joint":contrast_joint,
    }
    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    (out/"P2B_XMODEL_JOINT.json").write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")

    lines=["# P2b Cross-Model Joint Baseline v1.3","",
           "| Model | Overall | Majority | Activated | Controls | Parser fail | No-call | Multi-call |",
           "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for m in models:
        lines.append(f"| {m['model_key']} | {m['overall']:.3%} | {m['majority']}/26 | "
                     f"{m['activated']:.3%} | {m['controls']:.3%} | {m['parser_failures']} | "
                     f"{m['no_calls']} | {m['multi_calls']} |")
    lines += ["",f"Weak (<3/5) in all three: `{all3}`",f"Weak in at least two: `{any2}`","",
              "## Prospectively frozen argument-role endpoint",""]
    for name in contrast_names:
        j=contrast_joint[name]
        lines.append(f"### {name}")
        for x in j["models"]:
            ci=x["ci95"]
            lines.append(
                f"- {x['model_key']}: n={x['n']}, mean={x['mean']:+.3%}, "
                f"95% CI=[{ci[0]:+.3%}, {ci[1]:+.3%}]"
                if x["mean"] is not None else f"- {x['model_key']}: not estimable"
            )
        if j["predeclared_negative_direction"]:
            lines.append(f"- 3/3 negative directional replication: **{j['three_of_three_negative']}**")
        lines.append("")
    lines += [
        "Interpretation must distinguish argument-role exact replay volatility, action-structure "
        "errors, benchmark utility, and semantic equivalence. Do not generalize to all replay-based "
        "defenses without a separately frozen matched cross-defense study."
    ]
    (out/"P2B_XMODEL_JOINT.md").write_text("\n".join(lines)+"\n")
    print((out/"P2B_XMODEL_JOINT.md").read_text(),flush=True)

if __name__=="__main__":
    main()
