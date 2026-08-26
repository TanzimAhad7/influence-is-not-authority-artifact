#!/usr/bin/env python3
import argparse, csv, importlib.metadata, json, platform, sys
from pathlib import Path
from p0bv_common import *

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root',required=True)
    ap.add_argument('--package-dir',default=str(Path(__file__).resolve().parent))
    ap.add_argument('--out-dir',required=True)
    a=ap.parse_args(); root=Path(a.project_root).resolve();pkg=Path(a.package_dir).resolve();out=Path(a.out_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    cfg=json.load(open(pkg/'P0BV_CONFIG.json'))

    try: av=importlib.metadata.version('agentdojo')
    except Exception as e: raise SystemExit(f'Cannot resolve installed agentdojo package: {e}')
    if av != cfg['expected_agentdojo_package_version']:
        raise SystemExit(f'Expected agentdojo=={cfg["expected_agentdojo_package_version"]}, found {av}')
    import agentdojo
    from agentdojo.task_suite.load_suites import get_suite
    # Verify both benchmark layers exist in this exact package.
    for v in [cfg['old_benchmark_version'],cfg['target_benchmark_version']]:
        for s in cfg['suites']:
            try:get_suite(v,s)
            except Exception as e:raise SystemExit(f'Cannot load get_suite({v!r},{s!r}): {e}')

    required={}
    for k,rel in cfg['required_inputs'].items():
        p=root/rel
        if not p.exists():raise SystemExit(f'Missing required input {k}: {p}')
        required[k]={'path':str(p),'sha256':sha256_file(p),'bytes':p.stat().st_size}
    optional={}
    for k,rel in cfg['preferred_optional_inputs'].items():
        p=root/rel
        if p.exists():optional[k]={'path':str(p),'sha256':sha256_file(p),'bytes':p.stat().st_size}

    # Source-tree identity: hash exact imported package Python files.
    ad_file=Path(agentdojo.__file__).resolve();ad_root=ad_file.parent
    tree_hash,tree_rows=tree_sha256(ad_root,('.py',))

    a13=load_jsonl(Path(required['a13_decisions']['path']))
    a13_primary=sorted({r['decision_id'] for r in a13 if r.get('primary_valid') and not r.get('development')})
    a15=load_jsonl(Path(required['a15a_inventory']['path']))
    a15_ids=sorted({r['decision_id'] for r in a15})
    aw=load_jsonl(Path(required['agentwatcher_natural']['path']))
    aw_ids=sorted({r['decision_id'] for r in aw if r.get('decision_id')})
    p2b=[]
    if 'p3_cells' in optional:
        with open(optional['p3_cells']['path'],newline='') as f:p2b=sorted({r['decision_id'] for r in csv.DictReader(f)})
    elif 'p2b_inventory' in optional:
        p2b=sorted({r['decision_id'] for r in load_jsonl(Path(optional['p2b_inventory']['path']))})
    attack=json.load(open(required['agentwatcher_attack_freeze']['path']))
    pairs=attack.get('attack_anchor',{}).get('selected_pairs',[]) or recursive_find_pairs(attack)
    attack_version=attack.get('benchmark',{}).get('version')
    populations={
      'a13_primary_decisions':a13_primary,
      'a15a_decisions':a15_ids,
      'p2b_decisions':p2b,
      'agentwatcher_natural_decisions':aw_ids,
      'agentwatcher_attack_anchor_benchmark_version':attack_version,
      'agentwatcher_attack_anchor_pairs':pairs,
    }
    # Internal version assertions from scientific artifacts.
    a13_protocol=json.load(open(required['a13_protocol']['path']))
    assertions={
      'a13_agentdojo_package_version':a13_protocol.get('agentdojo_version'),
      'a13_benchmark_version':a13_protocol.get('benchmark_version'),
      'attack_anchor_benchmark_version':attack_version,
      'p2b_decision_count':len(p2b),
      'a13_primary_decision_count':len(a13_primary)
    }
    if assertions['a13_benchmark_version'] != cfg['old_benchmark_version']:
        raise SystemExit(f'A13 protocol benchmark version unexpected: {assertions["a13_benchmark_version"]}')
    if attack_version != cfg['target_benchmark_version']:
        raise SystemExit(f'AgentWatcher attack freeze benchmark version unexpected: {attack_version}')

    code_files={}
    for p in sorted(pkg.glob('*.py')):
        code_files[p.name]={'path':str(p),'sha256':sha256_file(p),'bytes':p.stat().st_size}
    code_files['P0BV_CONFIG.json']={'path':str(pkg/'P0BV_CONFIG.json'),'sha256':sha256_file(pkg/'P0BV_CONFIG.json'),'bytes':(pkg/'P0BV_CONFIG.json').stat().st_size}

    fr={
      'schema':'P0BV_ANALYSIS_FREEZE_V1','scientific_model_calls':0,'config':cfg,
      'runtime':{'python':sys.version,'platform':platform.platform(),'agentdojo_package_version':av,'agentdojo_import_path':str(ad_file),'agentdojo_python_tree_sha256':tree_hash,'old_benchmark_version':cfg['old_benchmark_version'],'target_benchmark_version':cfg['target_benchmark_version']},
      'input_files':required,'optional_input_files':optional,'code_files':code_files,'population_freeze':populations,'artifact_version_assertions':assertions
    }
    write_json(out/'P0BV_ANALYSIS_FREEZE.json',fr);write_json(out/'P0BV_POPULATION_FREEZE.json',populations)
    with (out/'P0BV_INPUT_MANIFEST.tsv').open('w') as f:
        f.write('kind\tname\tsha256\tbytes\tpath\n')
        for kind,dd in [('required',required),('optional',optional),('code',code_files)]:
            for k,v in dd.items():f.write(f'{kind}\t{k}\t{v["sha256"]}\t{v["bytes"]}\t{v["path"]}\n')
        f.write(f'agentdojo_source\tpython_tree\t{tree_hash}\tNA\t{ad_root}\n')
    md=f"""# P0b-V analysis freeze\n\n- scientific model calls: **0**\n- installed AgentDojo package: **{av}**\n- imported from: `{ad_file}`\n- package source-tree SHA-256: `{tree_hash}`\n- compare benchmark suites: **{cfg['old_benchmark_version']} → {cfg['target_benchmark_version']}**\n- A13 frozen benchmark version: **{assertions['a13_benchmark_version']}**\n- AgentWatcher 200-pair attack-anchor version: **{attack_version}**\n- A13 primary decisions: **{len(a13_primary)}**\n- P2b decisions frozen for mapping: **{len(p2b)}**\n\nThis is a predeclared zero-model-call compatibility audit. No historical result is changed by running it.\n"""
    (out/'P0BV_ANALYSIS_FREEZE.md').write_text(md)
    print('P0b-V ANALYSIS FREEZE PASS')
    print('agentdojo_package=',av)
    print('old_suite=',cfg['old_benchmark_version'],'target_suite=',cfg['target_benchmark_version'])
    print('attack_anchor_suite=',attack_version)

if __name__=='__main__':main()
