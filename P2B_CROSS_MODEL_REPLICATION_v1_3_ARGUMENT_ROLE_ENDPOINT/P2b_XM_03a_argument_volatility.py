#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, math, random
from collections import defaultdict
from pathlib import Path

def readj(p): return json.loads(Path(p).read_text())
def readjl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]
def stable(v): return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def percentile(xs, q):
    if not xs: return None
    ys=sorted(xs)
    pos=(len(ys)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return ys[lo]
    w=pos-lo
    return ys[lo]*(1-w)+ys[hi]*w

def bootstrap_mean(vals, n, seed):
    vals=[float(x) for x in vals if x is not None]
    if not vals:
        return {"n":0,"mean":None,"ci95":[None,None]}
    rng=random.Random(seed)
    boots=[]
    for _ in range(n):
        samp=[vals[rng.randrange(len(vals))] for _ in range(len(vals))]
        boots.append(sum(samp)/len(samp))
    return {
        "n":len(vals),
        "mean":sum(vals)/len(vals),
        "ci95":[percentile(boots,0.025),percentile(boots,0.975)],
    }

def unique_target_call(row, target_fn):
    calls=row.get("candidate_calls") or []
    matches=[c for c in calls if c.get("function")==target_fn]
    if len(calls)==0:
        status="NO_TOOL_CALL"
    elif len(matches)==0:
        status="TARGET_FUNCTION_ABSENT"
    elif len(matches)==1 and len(calls)==1:
        status="UNIQUE_TARGET_ONLY"
    elif len(matches)==1:
        status="UNIQUE_TARGET_PLUS_EXTRA_CALLS"
    else:
        status="MULTIPLE_TARGET_FUNCTION_CALLS"
    return (matches[0] if len(matches)==1 else None), status

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--run-dir",required=True)
    ap.add_argument("--package-root",default=str(Path(__file__).resolve().parent))
    args=ap.parse_args()

    pkg=Path(args.package_root).resolve()
    run=Path(args.run_dir).resolve()
    tax=readj(pkg/"P2B_ARGUMENT_ROLE_TAXONOMY.json")
    inv={r["decision_id"]:r for r in readjl(pkg/"inputs/P2B_REPLAY_INVENTORY.jsonl")}
    rows=readjl(run/"P2B_XMODEL_BASELINE_RAW.jsonl")
    freeze=readj(run/"P2B_XMODEL_FREEZE.json")

    if len(rows)!=130:
        raise SystemExit(f"FATAL incomplete baseline {len(rows)}/130")
    if set(r["decision_id"] for r in rows)!=set(inv):
        raise SystemExit("FATAL decision population mismatch")

    # Verify taxonomy coverage against the frozen inventory.
    for did,r in inv.items():
        frozen_args=set(r["target_action"]["args"])
        mapped=set(tax["per_decision"].get(did,{}))
        if frozen_args!=mapped:
            raise SystemExit(f"FATAL taxonomy coverage mismatch {did}: target={frozen_args} mapped={mapped}")

    slot_rows=[]
    action_rows=[]
    by_decision_class=defaultdict(list)

    for row in rows:
        did=row["decision_id"]
        target=inv[did]["target_action"]
        target_fn=target["function"]
        tc,status=unique_target_call(row,target_fn)
        action_rows.append({
            "model_key": freeze["model_key"],
            "decision_id":did,
            "repeat_index":int(row["repeat_index"]),
            "action_structure":status,
            "candidate_n_tool_calls":int(row.get("candidate_n_tool_calls",0)),
            "utility_preserved":bool(row["utility_preserved"]),
            "parser_failure":bool(row.get("adapter_parse_error")),
        })

        if tc is None:
            continue

        cand_args=tc.get("args") or {}
        target_args=target.get("args") or {}
        extra_args=sorted(set(cand_args)-set(target_args))

        # Per-class, per-repeat exactness is slot-normalized within the frozen target call.
        class_exact=defaultdict(list)
        for arg,tval in target_args.items():
            cls=tax["per_decision"][did][arg]
            present=arg in cand_args
            cval=cand_args.get(arg)
            exact=present and stable(cval)==stable(tval)
            class_exact[cls].append(1.0 if exact else 0.0)
            slot_rows.append({
                "model_key":freeze["model_key"],
                "decision_id":did,
                "repeat_index":int(row["repeat_index"]),
                "target_function":target_fn,
                "action_structure":status,
                "argument":arg,
                "argument_class":cls,
                "candidate_present":present,
                "exact_json_match":exact,
                "target_value_json":stable(tval),
                "candidate_value_json":stable(cval) if present else "",
                "extra_candidate_args_json":stable(extra_args),
                "utility_preserved":bool(row["utility_preserved"]),
            })
        for cls,vals in class_exact.items():
            by_decision_class[(did,cls)].append(sum(vals)/len(vals))

    # Decision is the inference unit.
    decision_scores={}
    for (did,cls),vals in sorted(by_decision_class.items()):
        decision_scores.setdefault(did,{})[cls]=sum(vals)/len(vals)

    bcfg=tax["bootstrap"]
    reps=int(bcfg["repetitions"]); seed=int(bcfg["seed"])

    class_names=["OPEN_TEXT","STRUCTURED_SCALAR","REFERENCE_IDENTITY","OPAQUE_EXACT"]
    class_summary={}
    for j,cls in enumerate(class_names):
        vals=[d.get(cls) for d in decision_scores.values() if cls in d]
        class_summary[cls]=bootstrap_mean(vals,reps,seed+101*j)

    def paired(a,b,seed_offset):
        vals=[]
        dids=[]
        for did,d in sorted(decision_scores.items()):
            if a in d and b in d:
                vals.append(d[a]-d[b]); dids.append(did)
        out=bootstrap_mean(vals,reps,seed+seed_offset)
        out["decision_ids"]=dids
        out["contrast"]=f"{a}_minus_{b}"
        return out

    contrasts={
        "OPEN_TEXT_minus_REFERENCE_IDENTITY":paired("OPEN_TEXT","REFERENCE_IDENTITY",1001),
        "STRUCTURED_SCALAR_minus_REFERENCE_IDENTITY":paired("STRUCTURED_SCALAR","REFERENCE_IDENTITY",2001),
        "OPEN_TEXT_minus_STRUCTURED_SCALAR":paired("OPEN_TEXT","STRUCTURED_SCALAR",3001),
    }

    action_counts=defaultdict(int)
    for r in action_rows: action_counts[r["action_structure"]]+=1

    obj={
        "schema":"P2B_XMODEL_ARGUMENT_VOLATILITY_V1",
        "model_key":freeze["model_key"],
        "model_id":freeze["runtime"]["served_model_id"],
        "freeze_sha256":freeze["freeze_sha256"],
        "rows":len(rows),
        "inference_unit":"decision",
        "conditioning":"exactly one candidate call matches target function",
        "class_summary":class_summary,
        "paired_contrasts":contrasts,
        "action_structure_counts":dict(sorted(action_counts.items())),
        "decision_scores":decision_scores,
    }
    (run/"P2B_ARGUMENT_VOLATILITY.json").write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")

    with (run/"P2B_ARGUMENT_SLOT_ROWS.csv").open("w",newline="") as f:
        if slot_rows:
            w=csv.DictWriter(f,fieldnames=list(slot_rows[0]))
            w.writeheader(); w.writerows(slot_rows)

    with (run/"P2B_ACTION_STRUCTURE_ROWS.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(action_rows[0]))
        w.writeheader(); w.writerows(action_rows)

    lines=[
        f"# P2b Argument-Role Replay Volatility — {freeze['model_key']}",
        "",
        "Secondary endpoint; primary P2b baseline gate is unchanged.",
        "",
        "| Class | Decisions with estimable score | Mean exact preservation | 95% decision-bootstrap CI |",
        "|---|---:|---:|---:|",
    ]
    for cls in class_names:
        s=class_summary[cls]
        mean="NA" if s["mean"] is None else f"{s['mean']:.3%}"
        ci="NA" if s["ci95"][0] is None else f"[{s['ci95'][0]:.3%}, {s['ci95'][1]:.3%}]"
        lines.append(f"| {cls} | {s['n']} | {mean} | {ci} |")
    lines += ["","## Within-decision paired contrasts",""]
    for name,c in contrasts.items():
        m="NA" if c["mean"] is None else f"{c['mean']:+.3%}"
        ci="NA" if c["ci95"][0] is None else f"[{c['ci95'][0]:+.3%}, {c['ci95'][1]:+.3%}]"
        lines.append(f"- `{name}`: n={c['n']}, mean={m}, 95% CI={ci}")
    lines += ["","## Action-structure counts",""]
    for k,v in sorted(action_counts.items()):
        lines.append(f"- `{k}`: {v}")
    lines += ["",
        "Interpretation boundary: exact argument preservation is a replay-volatility measure, "
        "not semantic-equivalence or downstream-utility by itself."
    ]
    (run/"P2B_ARGUMENT_VOLATILITY.md").write_text("\n".join(lines)+"\n")
    print((run/"P2B_ARGUMENT_VOLATILITY.md").read_text(),flush=True)

if __name__=="__main__":
    main()
