#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,importlib.metadata,inspect,json,os,sys
from pathlib import Path
from p0b3_common import *

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package-dir',default=str(Path(__file__).resolve().parent)); ap.add_argument('--out-dir',required=True)
    a=ap.parse_args(); pkg=Path(a.package_dir).resolve(); out=Path(a.out_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    if any(out.glob('P0B3_SCIENCE*')): raise SystemExit('HARD STOP: science outcome files already present in freeze directory')
    cfg=read_cfg(pkg)
    ver=importlib.metadata.version('agentdojo')
    if ver!=cfg['agentdojo']['package_version']: raise SystemExit(f"HARD STOP: agentdojo package {ver} != {cfg['agentdojo']['package_version']}")
    import agentdojo
    from agentdojo.task_suite.load_suites import get_suite
    from agentdojo.attacks.important_instructions_attacks import ImportantInstructionsAttack
    source_root=Path(agentdojo.__file__).resolve().parent
    tree_hash,tree_rows=tree_sha256(source_root)
    if tree_hash!=cfg['agentdojo']['source_tree_sha256_expected']:
        raise SystemExit(f"HARD STOP: AgentDojo source-tree hash {tree_hash} != expected {cfg['agentdojo']['source_tree_sha256_expected']}")
    suites=cfg['agentdojo']['suites']; vnew=cfg['agentdojo']['benchmark_version']; vold='v1'
    benign=[]; primary=[]; legacy=[]; suite_rows=[]; pop_signature={}
    for sname in suites:
        old=get_suite(vold,sname); new=get_suite(vnew,sname)
        uids=sorted(new.user_tasks); iids=sorted(new.injection_tasks); old_iids=set(old.injection_tasks); common_iids=sorted(set(iids)&old_iids)
        for u in uids:
            task=new.get_user_task_by_id(u)
            benign.append({'suite':sname,'user_task_id':u,'prompt_sha256':hashlib.sha256(str(getattr(task,'PROMPT',None)).encode()).hexdigest(),'class':f'{type(task).__module__}.{type(task).__qualname__}','class_source_sha256':source_hash(type(task))})
            for i in iids: primary.append({'suite':sname,'user_task_id':u,'injection_task_id':i})
            for i in common_iids: legacy.append({'suite':sname,'user_task_id':u,'injection_task_id':i})
        pop_signature[sname]={
          'user_task_ids':uids,'injection_task_ids_v1_2_2':iids,'legacy_intersection_injection_task_ids':common_iids,
          'user_task_count':len(uids),'injection_target_count_v1_2_2':len(iids),'legacy_intersection_target_count':len(common_iids),
          'primary_pair_count':len(uids)*len(iids),'legacy_pair_count':len(uids)*len(common_iids),
        }
        suite_rows.append({'suite':sname,**{k:v for k,v in pop_signature[sname].items() if not isinstance(v,list)}})
    counts={'benign_tasks':len(benign),'v1_2_2_injection_targets':sum(x['injection_target_count_v1_2_2'] for x in pop_signature.values()),'primary_pairs':len(primary),'legacy_pairs':len(legacy)}
    exp=cfg['population']
    expected={'benign_tasks':exp['primary_expected_user_tasks'],'v1_2_2_injection_targets':exp['primary_expected_injection_targets'],'primary_pairs':exp['primary_expected_security_pairs'],'legacy_pairs':exp['secondary_expected_security_pairs']}
    if counts!=expected: raise SystemExit(f'HARD STOP: population counts {counts} != expected {expected}')
    jb=ImportantInstructionsAttack._JB_STRING
    attack={'name':ImportantInstructionsAttack.name,'template':jb,'template_sha256':hashlib.sha256(jb.encode()).hexdigest(),'class_source_sha256':source_hash(ImportantInstructionsAttack)}
    env={'OPENROUTER_API_KEY_present':bool(os.environ.get('OPENROUTER_API_KEY')),'HF_TOKEN_present':bool(os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')),'note':'Presence only; NO network/API/model call was made.'}
    # csvs
    def wcsv(name,rows,fields):
        with (out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    wcsv('P0B3_BENIGN_97_TASKS.csv',benign,['suite','user_task_id','prompt_sha256','class','class_source_sha256'])
    wcsv('P0B3_PRIMARY_949_PAIRS.csv',primary,['suite','user_task_id','injection_task_id'])
    wcsv('P0B3_LEGACY_629_PAIRS.csv',legacy,['suite','user_task_id','injection_task_id'])
    wcsv('P0B3_SUITE_COUNTS.csv',suite_rows,['suite','user_task_count','injection_target_count_v1_2_2','legacy_intersection_target_count','primary_pair_count','legacy_pair_count'])
    result={'schema':'P0B3_ENV_POP_PREFLIGHT_V1','scientific_model_calls':0,'agentdojo_package_version':ver,'agentdojo_source_root':str(source_root),'agentdojo_source_tree_sha256':tree_hash,'counts':counts,'population_signature':pop_signature,'population_hashes':{'benign':obj_hash(benign),'primary949':obj_hash(primary),'legacy629':obj_hash(legacy)},'important_instructions':attack,'credential_presence':env,'package_source_hashes':package_source_hashes(pkg)}
    write_json(out/'P0B3_ENV_POP_PREFLIGHT.json',result)
    md=f'''# P0b-3 environment + population preflight\n\n**PASS / ZERO MODEL CALLS**\n\n- AgentDojo package: `{ver}`\n- source-tree SHA: `{tree_hash}`\n- benchmark: `{vnew}`\n- benign tasks: `{counts['benign_tasks']}`\n- v1.2.2 injection targets: `{counts['v1_2_2_injection_targets']}`\n- primary security pairs: `{counts['primary_pairs']}`\n- legacy-ID subset pairs: `{counts['legacy_pairs']}`\n- ImportantInstructions SHA: `{attack['template_sha256']}`\n- OPENROUTER_API_KEY present: `{env['OPENROUTER_API_KEY_present']}`\n\nNo network, API, GPU, vLLM, or scientific AgentDojo call was made.\n'''
    (out/'P0B3_ENV_POP_PREFLIGHT.md').write_text(md)
    print('P0b-3 ENVIRONMENT/POPULATION PREFLIGHT PASS')
    print(json.dumps(counts,sort_keys=True))
if __name__=='__main__': main()
