#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
SOURCE_FILES=[
 'ACTION_ENVELOPE_SCHEMA.json','MODEL_REGISTRY_CI.json','P2B_XM_CI_REVISION_LOCK.json','P2B_ARGUMENT_ROLE_TAXONOMY.json',
 'common_action_interface.py','action_local.py','p2b_common.py','stress_runtime.py','ci_integrity.py',
 'P2b_CI_00_static_audit.py','P2b_CI_01_stress_preflight.py','P2b_CI_02_freeze_global.py','P2b_CI_03_render_preflight.py','P2b_CI_04_freeze_arm.py','P2b_CI_05_run_baseline.py','P2b_CI_06_analyze_arm.py','P2b_CI_07_argument_role.py','P2b_CI_08_joint_compare.py',
 'serve_model.sh','stop_server.sh','PROTOCOL_P2B_XM_CI_v1_2.md','P2b_CI_RUNBOOK.md','README.md','V13_ADJUDICATION_LINEAGE.md','V1_2_TECHNICAL_GATE_AMENDMENT.md','V1_2_1R_ACTION_LOCAL_ORACLE_AMENDMENT.md','PREOUTCOME_VERIFICATION_REPORT.md','requirements_ci.txt','PREOUTCOME_BUILD_VALIDATION.json',
 'inputs/P2B_REPLAY_INVENTORY.jsonl','inputs/P2B_REPLAY_CONTEXTS.jsonl','inputs/P2B_PREFLIGHT_SUMMARY.json','inputs/P2B_PREFLIGHT_REPORT.md','inputs/EXCLUDED_STRESS_CONTEXTS.json'
]
PREFLIGHT_BOUND_FILES=[
 'P2b_CI_01_stress_preflight.py','common_action_interface.py','stress_runtime.py','ACTION_ENVELOPE_SCHEMA.json',
 'MODEL_REGISTRY_CI.json','P2B_XM_CI_REVISION_LOCK.json','inputs/EXCLUDED_STRESS_CONTEXTS.json'
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stable(o): return json.dumps(o,sort_keys=True,separators=(',',':'),ensure_ascii=False)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--preflight-root',default=str(HERE/'technical_preflight')); ap.add_argument('--out',default=str(HERE/'P2B_XM_CI_GLOBAL_FREEZE.json')); a=ap.parse_args()
    subprocess.run([sys.executable,str(HERE/'P2b_CI_00_static_audit.py')],cwd=HERE,check=True)
    static=json.loads((HERE/'P2B_CI_STATIC_AUDIT.json').read_text())
    if not static.get('pass'): raise SystemExit('FATAL static audit missing/fail')
    reg=json.loads((HERE/'MODEL_REGISTRY_CI.json').read_text()); lock=json.loads((HERE/'P2B_XM_CI_REVISION_LOCK.json').read_text())
    expected_bound={x:sha(HERE/x) for x in PREFLIGHT_BOUND_FILES}
    expected_calls=len(json.loads((HERE/'inputs/EXCLUDED_STRESS_CONTEXTS.json').read_text())['cases'])
    pre={}; common_client_stack=None
    for k in reg['run_order']:
        p=Path(a.preflight_root)/k/'P2B_CI_STRESS_PREFLIGHT.json'
        if not p.exists(): raise SystemExit(f'FATAL missing technical preflight {p}')
        d=json.loads(p.read_text()); model=reg['models'][k]; ml=lock['models'][k]
        if not d.get('pass') or d.get('model_key')!=k or d.get('model_id')!=model['model_id']:
            raise SystemExit(f'FATAL bad technical preflight identity/status {k}')
        if d.get('model_revision')!=ml['revision'] or d.get('tokenizer_revision')!=ml['tokenizer_revision']:
            raise SystemExit(f'FATAL technical preflight revision mismatch {k}')
        if d.get('vllm_version')!=reg['common_runtime']['vllm_version']:
            raise SystemExit(f'FATAL technical preflight vLLM mismatch {k}')
        if int(d.get('model_calls',-1))!=expected_calls:
            raise SystemExit(f'FATAL technical preflight call-count mismatch {k}: {d.get("model_calls")} != {expected_calls}')
        if d.get('tested_source_hashes')!=expected_bound:
            raise SystemExit(f'FATAL technical preflight {k} does not bind to the unchanged interface/source bytes; do not reuse it')
        stack=d.get('client_stack')
        if not isinstance(stack,dict) or not all(x in stack for x in ('openai','jsonschema','requests','python')):
            raise SystemExit(f'FATAL missing client stack in technical preflight {k}')
        if common_client_stack is None: common_client_stack=stack
        elif stack!=common_client_stack: raise SystemExit(f'FATAL client-stack drift across technical preflights: {k}')
        pre[k]={'sha256':sha(p),'model_calls':d['model_calls'],'created_utc':d['created_utc'],'live_server_cmdline_sha256':d['live_server_cmdline_sha256'],'tested_source_hashes':d['tested_source_hashes'],'client_stack':stack,'evidence_reuse':'REUSED_FROM_PRE_ORACLE_PATCH_BECAUSE_ALL_PREFLIGHT_BOUND_FILE_HASHES_MATCH_EXACTLY'}
    missing=[x for x in SOURCE_FILES if not (HERE/x).exists()]
    if missing: raise SystemExit(f'FATAL source manifest missing files: {missing}')
    freeze={'schema':'P2B_XM_CI_GLOBAL_FREEZE_V1_2_1R','created_utc':datetime.now(timezone.utc).isoformat(),'status':'SCIENTIFICALLY_FROZEN_AFTER_REVALIDATED_EXCLUDED_TECHNICAL_PREFLIGHT_EVIDENCE_BEFORE_26_DECISION_MODEL_GENERATIONS','model_registry':reg,'revision_lock':lock,'static_audit_sha256':sha(HERE/'P2B_CI_STATIC_AUDIT.json'),'technical_preflights':pre,'client_stack':common_client_stack,'source_hashes':{x:sha(HERE/x) for x in SOURCE_FILES},'preflight_reuse_rule':'Existing 3-model stress evidence is reused only because every file in PREFLIGHT_BOUND_FILES is byte-identical to the bytes originally tested. The changed action-local oracle is not called by Phase-A stress preflight.','science_rule':'No package/source/input/gate/H-SLOT changes after this superseding freeze. A failure of a post-freeze compatibility check requires another named superseding freeze before scientific model generations.','all_three_arms_rule':reg['completion_rule']}
    payload=dict(freeze); freeze['freeze_sha256']=hashlib.sha256(stable(payload).encode()).hexdigest()
    Path(a.out).write_text(json.dumps(freeze,indent=2,sort_keys=True)+'\n')
    print('GLOBAL FREEZE PASS'); print('freeze_sha256='+freeze['freeze_sha256']); print('technical_preflight_evidence=REUSED_AND_HASH_REVALIDATED_NO_MODEL_RERUN')

if __name__=='__main__': main()
