#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from collections import Counter, defaultdict
from pathlib import Path

from ci_integrity import load_and_verify_global_freeze
from p2b_common import freeze_hash, read_json, read_jsonl, write_json

HERE=Path(__file__).resolve().parent

def rate(rows,key): return sum(bool(r[key]) for r in rows)/len(rows) if rows else None

def gate_for(rows,key,overall_min,majority_min):
    by=defaultdict(list)
    for r in rows: by[r['decision_id']].append(bool(r[key]))
    if len(by)!=26 or any(len(v)!=5 for v in by.values()): raise SystemExit(f'FATAL repeat structure for {key}')
    overall=sum(sum(v) for v in by.values())/130
    maj=sum(sum(v)>=3 for v in by.values()); strong=sum(sum(v)>=4 for v in by.values())
    return {'metric':key,'overall_rate':overall,'decision_majority_success_count':maj,'decision_strong_success_count_ge4of5':strong,'pass':overall>=overall_min and maj>=majority_min,'per_decision_successes':{k:int(sum(v)) for k,v in sorted(by.items())},'weak_decisions':[k for k,v in sorted(by.items()) if sum(v)<3]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--run-dir',required=True); ap.add_argument('--global-freeze',default=str(HERE/'P2B_XM_CI_GLOBAL_FREEZE.json')); a=ap.parse_args()
    gf=load_and_verify_global_freeze(Path(a.global_freeze)); run=Path(a.run_dir).resolve(); f=read_json(run/'P2B_CI_ARM_FREEZE.json')
    if freeze_hash(f)!=f['freeze_sha256']: raise SystemExit('FATAL arm freeze hash mismatch')
    rows=[r for r in read_jsonl(run/'P2B_CI_BASELINE_RAW.jsonl') if r.get('arm_freeze_sha256')==f['freeze_sha256']]
    if len(rows)!=130: raise SystemExit(f'FATAL incomplete baseline {len(rows)}/130')
    keys={(r['decision_id'],int(r['repeat_index'])) for r in rows}
    if len(keys)!=130: raise SystemExit('FATAL duplicate decision/repeat keys')
    statuses=Counter(r['interface_status'] for r in rows)
    invalid_statuses=set(gf['model_registry']['gates']['instrument_validity']['invalid_statuses'])
    instrument_invalid=sum(statuses.get(x,0) for x in invalid_statuses)
    instrument_valid=(instrument_invalid==0)
    gates=gf['model_registry']['gates']
    ag=gates['action_local']; dg=gates['downstream_continuation']
    action_gate=gate_for(rows,'action_local_preserved',float(ag['overall_min']),int(ag['majority_decisions_min']))
    downstream_gate=gate_for(rows,'utility_preserved',float(dg['overall_min']),int(dg['majority_decisions_min']))
    intervention_eligible=instrument_valid and action_gate['pass'] and downstream_gate['pass']
    act=[r for r in rows if r['activated_tau0']]; ctl=[r for r in rows if not r['activated_tau0']]
    obj={
      'schema':'P2B_XM_CI_ARM_ANALYSIS_V1','model_key':f['model_key'],'model_id':f['runtime']['served_model_id'],'global_freeze_sha256':gf['freeze_sha256'],'arm_freeze_sha256':f['freeze_sha256'],'rows':130,
      'instrument':{'interface_status_counts':dict(sorted(statuses.items())),'invalid_statuses':sorted(invalid_statuses),'instrument_invalid_completed_response_count':instrument_invalid,'pass':instrument_valid},
      'action_local_gate':action_gate,'downstream_continuation_gate':downstream_gate,
      'intervention_eligible_under_corrected_baseline':intervention_eligible,
      'intervention_rule':'Eligibility only means a separately named prospective intervention may be designed/frozen for this model. This package does not run intervention.',
      'diagnostics':{
        'exact_target_action_rate':rate(rows,'exact_target_action_reproduction'),'deterministic_effect_equivalence_rate':rate(rows,'deterministic_effect_equivalent'),'tool_schema_valid_rate':rate(rows,'candidate_tool_schema_valid'),'tool_execution_valid_rate':rate(rows,'candidate_tool_execution_valid'),
        'activated_action_local_rate':rate(act,'action_local_preserved'),'controls_action_local_rate':rate(ctl,'action_local_preserved'),'activated_downstream_rate':rate(act,'utility_preserved'),'controls_downstream_rate':rate(ctl,'utility_preserved'),
        'action_structure_counts':dict(sorted(Counter(r['candidate_action_structure'] for r in rows).items()))
      },
      'scientific_disposition':('VALID_BASELINE_PASS' if intervention_eligible else ('INSTRUMENT_VOID' if not instrument_valid else 'VALID_BASELINE_FAIL'))
    }
    write_json(run/'P2B_CI_ARM_ANALYSIS.json',obj)
    lines=[f"# P2b-XM-CI corrected baseline — {f['model_key']}",'',f"**Disposition:** `{obj['scientific_disposition']}`",'',f"- Instrument validity: **{'PASS' if instrument_valid else 'VOID'}** ({instrument_invalid} invalid completed responses across {sorted(invalid_statuses)})",f"- Action-local gate: **{'PASS' if action_gate['pass'] else 'FAIL'}** — {action_gate['overall_rate']:.3%}, majority {action_gate['decision_majority_success_count']}/26",f"- Downstream frozen-continuation gate: **{'PASS' if downstream_gate['pass'] else 'FAIL'}** — {downstream_gate['overall_rate']:.3%}, majority {downstream_gate['decision_majority_success_count']}/26",f"- Exact target-action reproduction: {obj['diagnostics']['exact_target_action_rate']:.3%}",f"- Deterministic effect equivalence: {obj['diagnostics']['deterministic_effect_equivalence_rate']:.3%}",'',f"**Separate intervention freeze eligible for this model:** {'YES' if intervention_eligible else 'NO'}",'',"This analysis does not authorize or execute an intervention. All three corrected arms must be run regardless of this arm's PASS/FAIL."]
    (run/'P2B_CI_ARM_ANALYSIS.md').write_text('\n'.join(lines)+'\n')
    print((run/'P2B_CI_ARM_ANALYSIS.md').read_text(),flush=True)
    # Scientific FAIL is a valid outcome. Exit zero so the runbook cannot accidentally outcome-stop later arms.

if __name__=='__main__': main()
