#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

from ci_integrity import load_and_verify_global_freeze
from p2b_common import read_json

HERE=Path(__file__).resolve().parent

def load_arm(path):
    p=Path(path).resolve(); a=read_json(p/'P2B_CI_ARM_ANALYSIS.json'); h=read_json(p/'P2B_CI_ARGUMENT_VOLATILITY.json'); f=read_json(p/'P2B_CI_ARM_FREEZE.json')
    if a['arm_freeze_sha256']!=f['freeze_sha256'] or h['arm_freeze_sha256']!=f['freeze_sha256']:
        raise SystemExit(f'FATAL freeze mismatch in {p}')
    return {'path':str(p),'freeze':f,'analysis':a,'hslot':h}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--llama-run',required=True); ap.add_argument('--gemma-run',required=True); ap.add_argument('--qwen-run',required=True); ap.add_argument('--out-dir',required=True); ap.add_argument('--global-freeze',default=str(HERE/'P2B_XM_CI_GLOBAL_FREEZE.json')); a=ap.parse_args()
    gf=load_and_verify_global_freeze(Path(a.global_freeze)); arms=[load_arm(a.llama_run),load_arm(a.gemma_run),load_arm(a.qwen_run)]
    bykey={x['freeze']['model_key']:x for x in arms}
    if set(bykey)!={'llama','gemma','qwen_canonical'}: raise SystemExit(f'FATAL model set mismatch {set(bykey)}')
    for x in arms:
        if x['freeze']['global_freeze_sha256']!=gf['freeze_sha256']: raise SystemExit('FATAL global-freeze mismatch across arms')
    eligible=[k for k,x in bykey.items() if x['analysis']['intervention_eligible_under_corrected_baseline']]
    instrument_valid_all=all(x['analysis']['instrument']['pass'] for x in arms)
    all_baseline_pass=len(eligible)==3
    names=['OPEN_TEXT_minus_REFERENCE_IDENTITY','STRUCTURED_SCALAR_minus_REFERENCE_IDENTITY','OPEN_TEXT_minus_STRUCTURED_SCALAR']
    hjoint={}
    for name in names:
        vals=[]
        for k in ['llama','gemma','qwen_canonical']:
            c=bykey[k]['hslot']['paired_contrasts'][name]
            vals.append({'model_key':k,'instrument_valid':bykey[k]['hslot']['instrument_valid_for_confirmatory_hslot'],'n':c['n'],'mean':c['mean'],'ci95':c['ci95']})
        directional=name in {'OPEN_TEXT_minus_REFERENCE_IDENTITY','STRUCTURED_SCALAR_minus_REFERENCE_IDENTITY'}
        confirmatory_ready=all(v['instrument_valid'] for v in vals)
        replicated=(confirmatory_ready and directional and all(v['mean'] is not None and v['mean']<0 for v in vals)) if directional else None
        hjoint[name]={'models':vals,'predeclared_negative_direction':directional,'confirmatory_ready':confirmatory_ready,'three_of_three_negative':replicated}
    models=[]
    for k in ['llama','gemma','qwen_canonical']:
        x=bykey[k]; an=x['analysis']
        models.append({'model_key':k,'model_id':an['model_id'],'scientific_disposition':an['scientific_disposition'],'instrument_pass':an['instrument']['pass'],'action_local_gate':an['action_local_gate'],'downstream_continuation_gate':an['downstream_continuation_gate'],'intervention_eligible_under_corrected_baseline':an['intervention_eligible_under_corrected_baseline'],'exact_target_action_rate':an['diagnostics']['exact_target_action_rate'],'deterministic_effect_equivalence_rate':an['diagnostics']['deterministic_effect_equivalence_rate']})
    obj={'schema':'P2B_XM_CI_JOINT_V1','global_freeze_sha256':gf['freeze_sha256'],'models':models,'all_three_instrument_valid':instrument_valid_all,'models_eligible_for_separate_intervention_freeze':eligible,'all_three_corrected_baseline_pass':all_baseline_pass,'h_slot_joint':hjoint,'intervention_policy':'This package never runs intervention. A separate prospective intervention freeze may be created only for model arms whose corrected baseline is eligible. A cross-model consequence claim should not be made unless the separately frozen downstream study supports it on the intended model set.'}
    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True); (out/'P2B_XM_CI_JOINT.json').write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')
    lines=['# P2b-XM-CI corrected common-interface joint analysis','',f"Global freeze: `{gf['freeze_sha256']}`",'', '| Model | Instrument | Action-local gate | Downstream gate | Separate intervention freeze eligible |','|---|---:|---:|---:|---:|']
    for m in models:
        lines.append(f"| {m['model_key']} | {'PASS' if m['instrument_pass'] else 'VOID'} | {'PASS' if m['action_local_gate']['pass'] else 'FAIL'} ({m['action_local_gate']['overall_rate']:.1%}; {m['action_local_gate']['decision_majority_success_count']}/26) | {'PASS' if m['downstream_continuation_gate']['pass'] else 'FAIL'} ({m['downstream_continuation_gate']['overall_rate']:.1%}; {m['downstream_continuation_gate']['decision_majority_success_count']}/26) | {'YES' if m['intervention_eligible_under_corrected_baseline'] else 'NO'} |")
    lines += ['', '## H-SLOT (same pre-specified v1.3 directions; corrected instrument)', '']
    for name in names:
        j=hjoint[name]; lines.append(f'### {name}')
        for v in j['models']:
            if v['mean'] is None: lines.append(f"- {v['model_key']}: not estimable")
            else: lines.append(f"- {v['model_key']}: n={v['n']}, mean={v['mean']:+.3%}, 95% CI=[{v['ci95'][0]:+.3%}, {v['ci95'][1]:+.3%}], instrument_valid={v['instrument_valid']}")
        if j['predeclared_negative_direction']: lines.append(f"- 3/3 negative directional replication (confirmatory only if all instruments valid): **{j['three_of_three_negative']}**")
        lines.append('')
    lines += ['## Intervention boundary','',f"Eligible model arms for a **separately frozen** intervention: `{eligible}`",'', '**No intervention is authorized or executed by this package itself.**', '', 'All three corrected arms are retained regardless of earlier arm outcomes; do not pool these results with Qwen-native v1, canonical-text v1.3, or post-hoc recovered v1.3 estimates as if they shared an instrument.']
    (out/'P2B_XM_CI_JOINT.md').write_text('\n'.join(lines)+'\n'); print((out/'P2B_XM_CI_JOINT.md').read_text(),flush=True)

if __name__=='__main__': main()
