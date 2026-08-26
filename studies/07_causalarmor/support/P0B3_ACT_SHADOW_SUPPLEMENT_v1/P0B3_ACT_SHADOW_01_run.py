#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json
from datetime import datetime, timezone
from pathlib import Path
from p0b3_act_shadow_common import *

def pct(k,n): return 100.0*k/n

def main():
    ap=argparse.ArgumentParser(description='Run frozen P0b-3-ACT shadow serialization benign/attack split. ZERO MODEL CALLS.')
    ap.add_argument('--project-root',default='.')
    ap.add_argument('--output-dir',default='P0B3_ACT_SHADOW_RUN_v1')
    a=ap.parse_args(); root=Path(a.project_root).resolve(); pkg=Path(__file__).resolve().parent; out=root/a.output_dir
    fp=out/'P0B3_ACT_SHADOW_FREEZE.json'; inp=root/EXPECTED_INPUT_REL
    if not fp.is_file(): raise SystemExit('FATAL: shadow pre-analysis freeze missing')
    freeze=json.loads(fp.read_text())
    if freeze.get('schema')!=SCHEMA or freeze.get('stage')!='FREEZE': raise SystemExit('FATAL: freeze schema/stage mismatch')
    if source_hashes(pkg)!=freeze.get('package_source_sha256'): raise SystemExit('FATAL: package changed after freeze')
    h=sha256_file(inp)
    if h!=EXPECTED_INPUT_SHA256 or h!=freeze['input']['sha256']: raise SystemExit('FATAL: input changed after freeze')
    v=validate(read_jsonl(inp),aggregate_shadow=True)
    if v['denominators']!=freeze['frozen_denominators']: raise SystemExit('FATAL: denominators changed')
    bk=v['flagged']['benign']; ak=v['flagged']['attack']; bn=v['denominators']['benign']; an=v['denominators']['attack']; total=bk+ak
    if total!=EXPECTED_OVERALL_SHADOW_FLAGGED: raise SystemExit(f'FATAL: shadow split does not reconcile: {total}!={EXPECTED_OVERALL_SHADOW_FLAGGED}')
    bp=pct(bk,bn); apct=pct(ak,an); diff=apct-bp
    result={'schema':SCHEMA,'stage':'RESULT','created_utc':datetime.now(timezone.utc).isoformat(),'status':'COMPLETE_ZERO_CALL_PRE_SPECIFIED_SECONDARY_DESCRIPTIVE','scientific_model_calls':0,'input_sha256':h,'freeze_sha256':sha256_file(fp),'endpoint':'SHADOW := shadow_any_flag (COMPLETION_PLUS_TOOL_CALL serialization)','benign':{'flagged_privileged_decisions':bk,'privileged_decisions':bn,'activation_percent':bp},'attack':{'flagged_privileged_decisions':ak,'privileged_decisions':an,'activation_percent':apct},'attack_minus_benign_percentage_points':diff,'overall_reconciliation':{'flagged_privileged_decisions':total,'privileged_decisions':EXPECTED_TOTAL_EVENTS,'expected_frozen_overall_flagged':EXPECTED_OVERALL_SHADOW_FLAGGED,'activation_percent':pct(total,EXPECTED_TOTAL_EVENTS),'pass':total==EXPECTED_OVERALL_SHADOW_FLAGGED},'interpretation_lock':['pre-specified secondary shadow-serialization sensitivity only','post-hoc descriptive triangulation; no causal inference','not a second intervention arm','not ASR or utility','report regardless of shape']}
    rp=out/'P0B3_ACT_SHADOW_RESULT.json'; write_json(rp,result)
    with (out/'P0B3_ACT_SHADOW_SPLIT.csv').open('w',newline='',encoding='utf-8') as f:
      w=csv.writer(f); w.writerow(['population','shadow_flagged_privileged_decisions','privileged_decisions','activation_percent']); w.writerow(['benign',bk,bn,f'{bp:.12f}']); w.writerow(['attack',ak,an,f'{apct:.12f}']); w.writerow(['overall',total,EXPECTED_TOTAL_EVENTS,f'{pct(total,EXPECTED_TOTAL_EVENTS):.12f}'])
    (out/'P0B3_ACT_SHADOW_REPORT.md').write_text(f'# P0b-3-ACT shadow-serialization sensitivity\n\n- benign shadow activation: **{bk}/{bn} = {bp:.2f}%**\n- attack shadow activation: **{ak}/{an} = {apct:.2f}%**\n- descriptive attack − benign difference: **{diff:+.2f} pp**\n- overall reconciliation: **{total}/{EXPECTED_TOTAL_EVENTS} = {pct(total,EXPECTED_TOTAL_EVENTS):.2f}%** (PASS)\n\nInterpretation: pre-specified secondary shadow-serialization sensitivity only; zero calls; no causal inference and no second shadow intervention arm.\n',encoding='utf-8')
    names=['P0B3_ACT_SHADOW_FREEZE.json','P0B3_ACT_SHADOW_FREEZE.md','P0B3_ACT_SHADOW_RESULT.json','P0B3_ACT_SHADOW_SPLIT.csv','P0B3_ACT_SHADOW_REPORT.md']
    with (out/'FINAL_ARTIFACT_SHA256.txt').open('w',encoding='utf-8') as f:
      for n in names: f.write(f'{sha256_file(out/n)}  {n}\n')
    print('[P0B3-ACT-SHADOW-01] COMPLETE / ZERO MODEL CALLS'); print(f'[P0B3-ACT-SHADOW-01] benign={bk}/{bn} ({bp:.2f}%)'); print(f'[P0B3-ACT-SHADOW-01] attack={ak}/{an} ({apct:.2f}%)'); print(f'[P0B3-ACT-SHADOW-01] attack_minus_benign={diff:+.2f} pp'); print(f'[P0B3-ACT-SHADOW-01] overall_reconciliation={total}/{EXPECTED_TOTAL_EVENTS} ({pct(total,EXPECTED_TOTAL_EVENTS):.2f}%) PASS'); print(f'[P0B3-ACT-SHADOW-01] result_sha256={sha256_file(rp)}'); return 0
if __name__=='__main__': raise SystemExit(main())
