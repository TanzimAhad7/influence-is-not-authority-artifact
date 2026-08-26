#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, math, random
from collections import Counter, defaultdict
from pathlib import Path

from ci_integrity import load_and_verify_global_freeze
from p2b_common import freeze_hash, read_json, read_jsonl

HERE=Path(__file__).resolve().parent

def stable(v): return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def percentile(xs,q):
    if not xs:return None
    ys=sorted(xs); pos=(len(ys)-1)*q; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:return ys[lo]
    w=pos-lo; return ys[lo]*(1-w)+ys[hi]*w

def bootstrap_mean(vals,n,seed):
    vals=[float(x) for x in vals if x is not None]
    if not vals:return {'n':0,'mean':None,'ci95':[None,None]}
    rng=random.Random(seed); boots=[]
    for _ in range(n):
        samp=[vals[rng.randrange(len(vals))] for _ in range(len(vals))]; boots.append(sum(samp)/len(samp))
    return {'n':len(vals),'mean':sum(vals)/len(vals),'ci95':[percentile(boots,.025),percentile(boots,.975)]}

def unique_target_call(row,target_fn):
    calls=row.get('candidate_calls') or []; matches=[c for c in calls if c.get('function')==target_fn]
    if len(calls)==0:status='NO_TOOL_CALL'
    elif len(matches)==0:status='TARGET_FUNCTION_ABSENT'
    elif len(matches)==1 and len(calls)==1:status='UNIQUE_TARGET_ONLY'
    elif len(matches)==1:status='UNIQUE_TARGET_PLUS_EXTRA_CALLS'
    else:status='MULTIPLE_TARGET_FUNCTION_CALLS'
    return (matches[0] if len(matches)==1 else None),status

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-dir',required=True); ap.add_argument('--global-freeze',default=str(HERE/'P2B_XM_CI_GLOBAL_FREEZE.json')); a=ap.parse_args()
    gf=load_and_verify_global_freeze(Path(a.global_freeze)); run=Path(a.run_dir).resolve(); tax=read_json(HERE/'P2B_ARGUMENT_ROLE_TAXONOMY.json'); inv={r['decision_id']:r for r in read_jsonl(HERE/'inputs/P2B_REPLAY_INVENTORY.jsonl')}; rows=read_jsonl(run/'P2B_CI_BASELINE_RAW.jsonl'); freeze=read_json(run/'P2B_CI_ARM_FREEZE.json'); analysis=read_json(run/'P2B_CI_ARM_ANALYSIS.json')
    if freeze_hash(freeze)!=freeze['freeze_sha256']:raise SystemExit('FATAL arm freeze mismatch')
    if len(rows)!=130:raise SystemExit(f'FATAL incomplete baseline {len(rows)}/130')
    for did,r in inv.items():
        if set(r['target_action']['args'])!=set(tax['per_decision'].get(did,{})):raise SystemExit(f'FATAL taxonomy drift {did}')
    slot_rows=[]; action_rows=[]; by_decision_class=defaultdict(list)
    for row in rows:
        did=row['decision_id']; target=inv[did]['target_action']; target_fn=target['function']; tc,status=unique_target_call(row,target_fn)
        action_rows.append({'model_key':freeze['model_key'],'decision_id':did,'repeat_index':int(row['repeat_index']),'interface_status':row['interface_status'],'action_structure':status,'candidate_n_tool_calls':int(row.get('candidate_n_tool_calls',0)),'action_local_preserved':bool(row['action_local_preserved']),'utility_preserved':bool(row['utility_preserved']),'instrument_invalid_response':row['interface_status'] in {'FORMAT_INSTRUMENT_VIOLATION','ACTION_CONTRACT_VIOLATION'}})
        if tc is None:continue
        cand_args=tc.get('args') or {}; target_args=target.get('args') or {}; extra=sorted(set(cand_args)-set(target_args)); class_exact=defaultdict(list)
        for arg,tval in target_args.items():
            cls=tax['per_decision'][did][arg]; present=arg in cand_args; cval=cand_args.get(arg); exact=present and stable(cval)==stable(tval); class_exact[cls].append(1.0 if exact else 0.0)
            slot_rows.append({'model_key':freeze['model_key'],'decision_id':did,'repeat_index':int(row['repeat_index']),'target_function':target_fn,'action_structure':status,'argument':arg,'argument_class':cls,'candidate_present':present,'exact_json_match':exact,'target_value_json':stable(tval),'candidate_value_json':stable(cval) if present else '', 'extra_candidate_args_json':stable(extra),'action_local_preserved':bool(row['action_local_preserved']),'utility_preserved':bool(row['utility_preserved'])})
        for cls,vals in class_exact.items():by_decision_class[(did,cls)].append(sum(vals)/len(vals))
    decision_scores={}
    for (did,cls),vals in sorted(by_decision_class.items()):decision_scores.setdefault(did,{})[cls]=sum(vals)/len(vals)
    bcfg=tax['bootstrap']; reps=int(bcfg['repetitions']); seed=int(bcfg['seed']); classes=['OPEN_TEXT','STRUCTURED_SCALAR','REFERENCE_IDENTITY','OPAQUE_EXACT']
    class_summary={}
    for j,cls in enumerate(classes):class_summary[cls]=bootstrap_mean([d.get(cls) for d in decision_scores.values() if cls in d],reps,seed+101*j)
    def paired(x,y,off):
        vals=[]; dids=[]
        for did,d in sorted(decision_scores.items()):
            if x in d and y in d:vals.append(d[x]-d[y]);dids.append(did)
        o=bootstrap_mean(vals,reps,seed+off);o['decision_ids']=dids;o['contrast']=f'{x}_minus_{y}';return o
    contrasts={'OPEN_TEXT_minus_REFERENCE_IDENTITY':paired('OPEN_TEXT','REFERENCE_IDENTITY',1001),'STRUCTURED_SCALAR_minus_REFERENCE_IDENTITY':paired('STRUCTURED_SCALAR','REFERENCE_IDENTITY',2001),'OPEN_TEXT_minus_STRUCTURED_SCALAR':paired('OPEN_TEXT','STRUCTURED_SCALAR',3001)}
    instrument_valid=bool(analysis['instrument']['pass'])
    obj={'schema':'P2B_XM_CI_ARGUMENT_VOLATILITY_V1','model_key':freeze['model_key'],'model_id':freeze['runtime']['served_model_id'],'arm_freeze_sha256':freeze['freeze_sha256'],'global_freeze_sha256':gf['freeze_sha256'],'rows':130,'inference_unit':'decision','conditioning':'exactly one candidate call matches target function; unchanged from v1.3 H-SLOT','instrument_valid_for_confirmatory_hslot':instrument_valid,'confirmatory_status':'ELIGIBLE' if instrument_valid else 'VOID_FOR_ARM_INSTRUMENT_FAILURE','class_summary':class_summary,'paired_contrasts':contrasts,'action_structure_counts':dict(sorted(Counter(r['action_structure'] for r in action_rows).items())),'decision_scores':decision_scores}
    (run/'P2B_CI_ARGUMENT_VOLATILITY.json').write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    with (run/'P2B_CI_ARGUMENT_SLOT_ROWS.csv').open('w',newline='') as f:
        if slot_rows:w=csv.DictWriter(f,fieldnames=list(slot_rows[0]));w.writeheader();w.writerows(slot_rows)
    with (run/'P2B_CI_ACTION_STRUCTURE_ROWS.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(action_rows[0]));w.writeheader();w.writerows(action_rows)
    lines=[f"# P2b-XM-CI H-SLOT — {freeze['model_key']}",'',f"Instrument-valid confirmatory status: **{'YES' if instrument_valid else 'NO'}**",'',"The v1.3 directional hypotheses and bootstrap/inference unit are retained unchanged.",'']
    for name,c in contrasts.items():
        if c['mean'] is None: lines.append(f'- `{name}`: not estimable')
        else: lines.append(f"- `{name}`: n={c['n']}, mean={c['mean']:+.3%}, 95% CI=[{c['ci95'][0]:+.3%}, {c['ci95'][1]:+.3%}]")
    lines += ['', 'H-SLOT cannot rescue a failed replay-validity gate and does not by itself authorize intervention.']
    (run/'P2B_CI_ARGUMENT_VOLATILITY.md').write_text('\n'.join(lines)+'\n'); print((run/'P2B_CI_ARGUMENT_VOLATILITY.md').read_text(),flush=True)

if __name__=='__main__':main()
