#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path
from p6_common import sha256, load_json

def die(msg):
    print('P6 PREFLIGHT FAIL:',msg,file=sys.stderr)
    raise SystemExit(2)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root',required=True)
    ap.add_argument('--package-dir',required=True)
    ap.add_argument('--out-dir',required=True)
    a=ap.parse_args()
    root=Path(a.project_root).resolve()
    pkg=Path(a.package_dir).resolve()
    out=Path(a.out_dir).resolve()
    if out.exists() and any(out.iterdir()):
        die(f'output directory is not empty: {out}')
    out.mkdir(parents=True,exist_ok=True)
    cfg=load_json(pkg/'P6_CONFIG.json')
    manifest=[]

    for key,spec in cfg['inputs'].items():
        p=root/spec['path']
        if not p.is_file():
            die(f'missing required upstream input: {spec["path"]}')
        got=sha256(p)
        if got!=spec['sha256']:
            die(f'hash mismatch for {spec["path"]}: expected {spec["sha256"]}, got {got}')
        manifest.append({'kind':'file','key':key,'path':spec['path'],'sha256':got,'bytes':p.stat().st_size})

    attr=load_json(root/cfg['inputs']['attriguard_analysis']['path'])
    if not attr.get('run_complete') or attr.get('n_condition_repeats')!=480:
        die('AttriGuard analysis is not a complete 480-row scientific analysis')
    if attr.get('majority_AIVR_class',{}).get('violating_bases')!=0:
        die('unexpected AttriGuard AIVR value')

    p0=load_json(root/cfg['inputs']['p0b3_analysis']['path'])
    if p0.get('status')!='COMPLETE' or p0.get('primary',{}).get('disposition')!='SAME_EXTERNAL_REGIME':
        die('P0b-3 authoritative analysis not in expected closed disposition')

    for key in ['p2b_llama','p2b_gemma','p2b_qwen']:
        x=load_json(root/cfg['inputs'][key]['path'])
        if not x.get('instrument',{}).get('pass'):
            die(f'{key} instrument invalid')
        if x.get('scientific_disposition')!='VALID_BASELINE_FAIL':
            die(f'{key} unexpected scientific disposition')
        if x.get('rows')!=130:
            die(f'{key} row count !=130')

    af=load_json(root/cfg['inputs']['agentwatcher_attack_freeze']['path'])
    frozen={(r['suite'],r['user_task_id'],r['injection_task_id']) for r in af['benchmark']['selected_pairs']}
    if len(frozen)!=200:
        die(f'AgentWatcher freeze has {len(frozen)} unique selected pairs, expected 200')

    attack_summary={}
    for key,spec in cfg['attack_runs'].items():
        d=root/spec['path']
        if not d.is_dir():
            die(f'missing attack result directory: {spec["path"]}')
        selected=[]
        for p in sorted(d.rglob('*.json')):
            x=load_json(p)
            if x.get('attack_type')==spec['attack_type']:
                selected.append((p,x))
        if len(selected)!=spec['expected_n']:
            die(f'{key}: found {len(selected)} scientific attack rows, expected {spec["expected_n"]}')
        pairs={(x['suite_name'],x['user_task_id'],x['injection_task_id']) for _,x in selected}
        if pairs!=frozen:
            die(f'{key}: result pair set does not equal frozen 200-pair set')
        errs=sum(x.get('error') is not None for _,x in selected)
        if errs:
            die(f'{key}: {errs} scientific rows contain errors')
        for p,_ in selected:
            manifest.append({'kind':'attack_row','key':key,'path':p.relative_to(root).as_posix(),'sha256':sha256(p),'bytes':p.stat().st_size})
        attack_summary[key]={
            'n':len(selected),
            'utility_true':sum(bool(x.get('utility')) for _,x in selected),
            'security_true':sum(bool(x.get('security')) for _,x in selected),
        }

    package_files=[]
    for p in sorted(pkg.iterdir()):
        if p.is_file() and p.name!='PACKAGE_SHA256.txt':
            package_files.append({'path':p.name,'sha256':sha256(p),'bytes':p.stat().st_size})

    manifest.sort(key=lambda r:(r['kind'],r['key'],r['path']))
    with (out/'P6_INPUT_MANIFEST.tsv').open('w',newline='',encoding='utf-8') as f:
        fields=['kind','key','path','sha256','bytes']
        w=csv.DictWriter(f,fieldnames=fields,delimiter='\t')
        w.writeheader()
        w.writerows(manifest)

    freeze={
        'schema':'P6_CLEAN_INPUT_FREEZE_V1_2026-08-12',
        'status':'PASS',
        'scientific_model_calls':0,
        'project_root':str(root),
        'config_sha256':sha256(pkg/'P6_CONFIG.json'),
        'package_files':package_files,
        'manifest_sha256':sha256(out/'P6_INPUT_MANIFEST.tsv'),
        'manifest_rows':len(manifest),
        'attack_summary_pre_synthesis':attack_summary,
        'population_lineage':cfg['population_lineage'],
        'hard_boundaries':cfg['hard_boundaries'],
    }
    (out/'P6_INPUT_FREEZE.json').write_text(json.dumps(freeze,indent=2,sort_keys=True)+'\n')
    md=(
        '# P6 Clean Input Freeze\n\n'
        '- Status: **PASS**\n'
        '- Scientific model calls: **0**\n'
        f'- Frozen manifest rows: **{len(manifest)}**\n'
        f'- Manifest SHA-256: `{freeze["manifest_sha256"]}`\n'
        '- AttriGuard native analysis: exact authoritative SHA matched.\n'
        '- P0b-3: authoritative `SAME_EXTERNAL_REGIME` analysis matched.\n'
        '- Corrected P2b: all three instruments valid and all three baseline gates fail.\n'
        '- AgentWatcher attack anchors: both runs match the exact frozen 200-pair set.\n\n'
        f'Population lineage: {cfg["population_lineage"]["natural_downstream_scope"]}\n'
    )
    (out/'P6_INPUT_FREEZE.md').write_text(md)
    print('P6 CLEAN PREFLIGHT / INPUT FREEZE PASS')
    print('manifest_rows=',len(manifest))
    print('manifest_sha256=',freeze['manifest_sha256'])
    print('attack_summary=',json.dumps(attack_summary,sort_keys=True))

if __name__=='__main__':
    main()
