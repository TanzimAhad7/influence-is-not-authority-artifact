#!/usr/bin/env python3
import argparse, csv, importlib.metadata, json, copy, inspect
from pathlib import Path
from collections import Counter, defaultdict
from p0bv_common import *

def verify_freeze(path):
    fr=json.load(open(path));bad=[]
    for group in ['input_files','optional_input_files','code_files']:
        for k,d in fr.get(group,{}).items():
            p=Path(d['path'])
            if not p.exists():bad.append(f'{group}:{k}: missing {p}')
            elif sha256_file(p)!=d['sha256']:bad.append(f'{group}:{k}: hash changed')
    import agentdojo
    current_tree,_=tree_sha256(Path(agentdojo.__file__).resolve().parent,('.py',))
    if current_tree!=fr['runtime']['agentdojo_python_tree_sha256']:bad.append('agentdojo Python source tree changed after freeze')
    if bad:raise RuntimeError('Freeze verification failed:\n'+'\n'.join(bad))
    return fr

def method_source_hash(bound):
    try:return source_hash(bound.__func__)
    except Exception:return source_hash(bound)

def run_task_signature(suite,task,FunctionsRuntime):
    base=suite.load_and_inject_default_environment({})
    init_error=None;gt_error=None;exec_error=None
    try:
        env=task.init_environment(copy.deepcopy(base))
    except Exception as e:
        env=copy.deepcopy(base);init_error=f'{type(e).__name__}: {e}'
    init_dump=dump_model(env)
    try:gt=task.ground_truth(copy.deepcopy(env));gt_dump=function_calls_dump(gt)
    except Exception as e:gt=[];gt_dump=[];gt_error=f'{type(e).__name__}: {e}'
    post=copy.deepcopy(env)
    if gt:
        rt=FunctionsRuntime(suite.tools)
        try:
            for c in gt:rt.run_function(post,c.function,c.args,raise_on_error=True)
        except Exception as e:exec_error=f'{type(e).__name__}: {e}'
    return {
      'id':task.ID,'class':class_name(task),'class_source_sha256':source_hash(type(task)),
      'prompt':getattr(task,'PROMPT',None),'ground_truth_output':getattr(task,'GROUND_TRUTH_OUTPUT',None),
      'difficulty':str(getattr(task,'DIFFICULTY',None)),
      'ground_truth_method_sha256':method_source_hash(task.ground_truth),
      'utility_method_sha256':method_source_hash(task.utility),
      'utility_from_traces_method_sha256':method_source_hash(task.utility_from_traces),
      'init_environment_method_sha256':method_source_hash(task.init_environment),
      'initial_environment_sha256':obj_hash(init_dump),'ground_truth_calls':gt_dump,'ground_truth_calls_sha256':obj_hash(gt_dump),
      'post_ground_truth_environment_sha256':obj_hash(dump_model(post)),
      'init_error':init_error,'ground_truth_error':gt_error,'ground_truth_execution_error':exec_error
    }

def run_injection_signature(suite,task,FunctionsRuntime):
    base=suite.load_and_inject_default_environment({});gt_error=None;exec_error=None
    try:gt=task.ground_truth(copy.deepcopy(base));gt_dump=function_calls_dump(gt)
    except Exception as e:gt=[];gt_dump=[];gt_error=f'{type(e).__name__}: {e}'
    post=copy.deepcopy(base)
    if gt:
        rt=FunctionsRuntime(suite.tools)
        try:
            for c in gt:rt.run_function(post,c.function,c.args,raise_on_error=True)
        except Exception as e:exec_error=f'{type(e).__name__}: {e}'
    return {
      'id':task.ID,'class':class_name(task),'class_source_sha256':source_hash(type(task)),
      'goal':getattr(task,'GOAL',None),'ground_truth_output':getattr(task,'GROUND_TRUTH_OUTPUT',None),
      'difficulty':str(getattr(task,'DIFFICULTY',None)),
      'ground_truth_method_sha256':method_source_hash(task.ground_truth),
      'security_method_sha256':method_source_hash(task.security),
      'security_from_traces_method_sha256':method_source_hash(task.security_from_traces),
      'ground_truth_calls':gt_dump,'ground_truth_calls_sha256':obj_hash(gt_dump),
      'post_ground_truth_environment_sha256':obj_hash(dump_model(post)),
      'ground_truth_error':gt_error,'ground_truth_execution_error':exec_error
    }

def diff_keys(a,b,keys):return [k for k in keys if a.get(k)!=b.get(k)]

def compare_task(old,new,suite_env_changed,suite_tools_changed):
    if old is None or new is None:return 'TASK_ADDED_REMOVED',['presence']
    keys_prompt=['prompt','ground_truth_output','ground_truth_method_sha256','ground_truth_calls_sha256','post_ground_truth_environment_sha256']
    keys_eval=['utility_method_sha256','utility_from_traces_method_sha256']
    keys_other=['class','class_source_sha256','difficulty','init_environment_method_sha256','initial_environment_sha256','init_error','ground_truth_error','ground_truth_execution_error']
    if suite_env_changed or suite_tools_changed:return 'ENVIRONMENT_OR_TOOL_CHANGE',(['suite_environment'] if suite_env_changed else [])+(['suite_tools'] if suite_tools_changed else [])+diff_keys(old,new,keys_prompt+keys_eval+keys_other)
    p=diff_keys(old,new,keys_prompt);e=diff_keys(old,new,keys_eval);o=diff_keys(old,new,keys_other)
    if p:return 'PROMPT_OR_GROUND_TRUTH_CHANGE',p+e+o
    if e and not o:return 'EVALUATOR_ONLY_CHANGE',e
    if o or e:return 'UNKNOWN_REQUIRES_MANUAL_REVIEW',o+e
    return 'IDENTICAL_FOR_OUR_ESTIMAND',[]

def compare_injection(old,new,suite_env_changed,suite_tools_changed):
    if old is None or new is None:return 'TASK_ADDED_REMOVED',['presence']
    keys_gt=['goal','ground_truth_output','ground_truth_method_sha256','ground_truth_calls_sha256','post_ground_truth_environment_sha256']
    keys_eval=['security_method_sha256','security_from_traces_method_sha256']
    keys_other=['class','class_source_sha256','difficulty','ground_truth_error','ground_truth_execution_error']
    if suite_env_changed or suite_tools_changed:return 'ENVIRONMENT_OR_TOOL_CHANGE',(['suite_environment'] if suite_env_changed else [])+(['suite_tools'] if suite_tools_changed else [])+diff_keys(old,new,keys_gt+keys_eval+keys_other)
    p=diff_keys(old,new,keys_gt);e=diff_keys(old,new,keys_eval);o=diff_keys(old,new,keys_other)
    if p:return 'PROMPT_OR_GROUND_TRUTH_CHANGE',p+e+o
    if e and not o:return 'EVALUATOR_ONLY_CHANGE',e
    if o or e:return 'UNKNOWN_REQUIRES_MANUAL_REVIEW',o+e
    return 'IDENTICAL_FOR_OUR_ESTIMAND',[]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--project-root',required=True);ap.add_argument('--package-dir',default=str(Path(__file__).resolve().parent));ap.add_argument('--out-dir',required=True)
    a=ap.parse_args();root=Path(a.project_root).resolve();pkg=Path(a.package_dir).resolve();out=Path(a.out_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    fr=verify_freeze(out/'P0BV_ANALYSIS_FREEZE.json');cfg=fr['config']
    from agentdojo.task_suite.load_suites import get_suite
    from agentdojo.functions_runtime import FunctionsRuntime

    versions=[cfg['old_benchmark_version'],cfg['target_benchmark_version']]
    all_task_sigs=[];all_inj_sigs=[];task_rows=[];inj_rows=[];tool_rows=[];suite_rows=[]
    task_classification={};inj_classification={};suite_flags={}

    for sname in cfg['suites']:
        suites={v:get_suite(v,sname) for v in versions}
        env_sig={};tools_sig={}
        for v,s in suites.items():
            env=s.load_and_inject_default_environment({});env_sig[v]=obj_hash(dump_model(env));tools_sig[v]=[tool_signature(x) for x in s.tools]
        env_changed=env_sig[versions[0]]!=env_sig[versions[1]];tools_changed=obj_hash(tools_sig[versions[0]])!=obj_hash(tools_sig[versions[1]])
        suite_flags[sname]={'environment_changed':env_changed,'tools_changed':tools_changed}
        old_tools={x['name']:x for x in tools_sig[versions[0]]};new_tools={x['name']:x for x in tools_sig[versions[1]]}
        for name in sorted(set(old_tools)|set(new_tools)):
            o=old_tools.get(name);n=new_tools.get(name);tool_rows.append({'suite':sname,'tool':name,'old_present':o is not None,'new_present':n is not None,'changed':o!=n,'old_sha256':None if o is None else obj_hash(o),'new_sha256':None if n is None else obj_hash(n)})
        tids=sorted(set(suites[versions[0]].user_tasks)|set(suites[versions[1]].user_tasks))
        sig_by_v={v:{} for v in versions}
        for v,s in suites.items():
            for tid,t in s.user_tasks.items():
                sig=run_task_signature(s,t,FunctionsRuntime);sig_by_v[v][tid]=sig;all_task_sigs.append({'suite':sname,'benchmark_version':v,**sig})
        for tid in tids:
            o=sig_by_v[versions[0]].get(tid);n=sig_by_v[versions[1]].get(tid);cls,diffs=compare_task(o,n,env_changed,tools_changed)
            key=f'{sname}/{tid}';task_classification[key]=cls
            task_rows.append({'task_key':key,'suite':sname,'user_task':tid,'classification':cls,'difference_fields':'|'.join(diffs),'old_present':o is not None,'new_present':n is not None,'old_class':None if o is None else o['class'],'new_class':None if n is None else n['class'],'prompt_changed':False if o is None or n is None else o['prompt']!=n['prompt'],'ground_truth_calls_changed':False if o is None or n is None else o['ground_truth_calls_sha256']!=n['ground_truth_calls_sha256'],'evaluator_changed':False if o is None or n is None else (o['utility_method_sha256'],o['utility_from_traces_method_sha256'])!=(n['utility_method_sha256'],n['utility_from_traces_method_sha256']),'initial_env_changed':False if o is None or n is None else o['initial_environment_sha256']!=n['initial_environment_sha256'],'post_gt_env_changed':False if o is None or n is None else o['post_ground_truth_environment_sha256']!=n['post_ground_truth_environment_sha256']})
        iids=sorted(set(suites[versions[0]].injection_tasks)|set(suites[versions[1]].injection_tasks))
        isig_by_v={v:{} for v in versions}
        for v,s in suites.items():
            for iid,t in s.injection_tasks.items():
                sig=run_injection_signature(s,t,FunctionsRuntime);isig_by_v[v][iid]=sig;all_inj_sigs.append({'suite':sname,'benchmark_version':v,**sig})
        for iid in iids:
            o=isig_by_v[versions[0]].get(iid);n=isig_by_v[versions[1]].get(iid);cls,diffs=compare_injection(o,n,env_changed,tools_changed)
            key=f'{sname}/{iid}';inj_classification[key]=cls
            inj_rows.append({'injection_key':key,'suite':sname,'injection_task':iid,'classification':cls,'difference_fields':'|'.join(diffs),'old_present':o is not None,'new_present':n is not None,'goal_changed':False if o is None or n is None else o['goal']!=n['goal'],'ground_truth_calls_changed':False if o is None or n is None else o['ground_truth_calls_sha256']!=n['ground_truth_calls_sha256'],'security_evaluator_changed':False if o is None or n is None else (o['security_method_sha256'],o['security_from_traces_method_sha256'])!=(n['security_method_sha256'],n['security_from_traces_method_sha256'])})
        suite_rows.append({'suite':sname,'old_version':versions[0],'new_version':versions[1],'environment_changed':env_changed,'tools_changed':tools_changed,'old_user_tasks':len(suites[versions[0]].user_tasks),'new_user_tasks':len(suites[versions[1]].user_tasks),'changed_user_tasks':sum(r['suite']==sname and r['classification']!='IDENTICAL_FOR_OUR_ESTIMAND' for r in task_rows),'old_injection_tasks':len(suites[versions[0]].injection_tasks),'new_injection_tasks':len(suites[versions[1]].injection_tasks),'changed_injection_tasks':sum(r['suite']==sname and r['classification']!='IDENTICAL_FOR_OUR_ESTIMAND' for r in inj_rows)})

    # Map paper-bearing populations.
    pop=fr['population_freeze'];impact=[]
    for pname,key in [('A13_PRIMARY','a13_primary_decisions'),('A15A','a15a_decisions'),('P2B','p2b_decisions'),('AGENTWATCHER_NATURAL','agentwatcher_natural_decisions')]:
        for did in pop.get(key,[]):
            tk=task_key_from_decision(did);impact.append({'population':pname,'decision_id':did,'task_key':tk,'classification':task_classification.get(tk,'TASK_NOT_FOUND_IN_DIFF'),'historical_benchmark_version':versions[0]})
    # AgentWatcher attack anchor is already v1.2.2; annotate pair-level source-diff sensitivity without calling it a mismatch.
    attack_pair_rows=[]
    for i,pair in enumerate(pop.get('agentwatcher_attack_anchor_pairs',[])):
        uk=f"{pair['suite']}/{pair['user_task_id']}";ik=f"{pair['suite']}/{pair['injection_task_id']}"
        attack_pair_rows.append({'pair_index':i,'suite':pair['suite'],'user_task_id':pair['user_task_id'],'injection_task_id':pair['injection_task_id'],'anchor_benchmark_version':pop.get('agentwatcher_attack_anchor_benchmark_version'),'user_task_v1_to_v122_classification':task_classification.get(uk,'MISSING'),'injection_task_v1_to_v122_classification':inj_classification.get(ik,'MISSING'),'historical_mismatch':False})

    # Changed task keys that touch the historical headline lineage.
    relevant_historical={'A13_PRIMARY','A15A','P2B','AGENTWATCHER_NATURAL'}
    changed_impact=[r for r in impact if r['population'] in relevant_historical and r['classification']!='IDENTICAL_FOR_OUR_ESTIMAND']
    changed_task_keys=sorted({r['task_key'] for r in changed_impact})

    # A13 all-changed-task deletion diagnostic.
    a13=load_jsonl(Path(fr['input_files']['a13_decisions']['path']));a13_primary=[r for r in a13 if r.get('primary_valid') and not r.get('development')]
    a13_original=task_weighted_H(a13_primary,cfg['bootstrap_repetitions'],cfg['bootstrap_seed'])
    a13_filtered=[r for r in a13_primary if r['task_key'] not in set(changed_task_keys)]
    a13_filtered_res=task_weighted_H(a13_filtered,cfg['bootstrap_repetitions'],cfg['bootstrap_seed'])

    # P2b changed-task deletion diagnostic from P3 cells when available.
    p2b_diag=[]
    p3path=fr.get('optional_input_files',{}).get('p3_cells',{}).get('path')
    if p3path:
        cells=list(csv.DictReader(open(p3path)))
        for model in sorted({r['model'] for r in cells}):
            orig=[r for r in cells if r['model']==model];fil=[r for r in orig if task_key_from_decision(r['decision_id']) not in set(changed_task_keys)]
            def summ(rs):
                return {'n_decisions':len(rs),'action_local_rate':mean([float(r['action_local_rate']) for r in rs]),'downstream_rate':mean([float(r['downstream_rate']) for r in rs]),'action_majority_cells':sum(str(r['action_majority']).lower()=='true' for r in rs),'downstream_majority_cells':sum(str(r['downstream_majority']).lower()=='true' for r in rs)}
            p2b_diag.append({'model':model,'original':summ(orig),'excluding_all_version_changed_historical_tasks':summ(fil)})

    # Summary / gate status.
    suite_material=any(r['environment_changed'] or r['tools_changed'] for r in suite_rows)
    classes=Counter(r['classification'] for r in task_rows);relevant_classes=Counter(r['classification'] for r in changed_impact)
    if suite_material:gate='MATERIAL_SUITE_SEMANTICS_CHANGE_REQUIRES_MANUAL_ADJUDICATION'
    elif not changed_task_keys:gate='NO_HEADLINE_BEARING_TASK_DIFFERENCE'
    elif a13_filtered_res and a13_filtered_res['difference']>0 and all((d['excluding_all_version_changed_historical_tasks']['action_local_rate'] or 0)<0.90 and (d['excluding_all_version_changed_historical_tasks']['downstream_rate'] or 0)<0.90 for d in p2b_diag):gate='HEADLINE_TASK_DIFFERENCE_BUT_EXISTING_DELETION_SENSITIVITY_PRESERVES_BROAD_DIRECTIONS'
    else:gate='HEADLINE_TASK_DIFFERENCE_REQUIRES_TARGETED_MANUAL_REVIEW'

    result={'schema':'P0BV_RESULT_V1','scientific_model_calls':0,'old_version':versions[0],'target_version':versions[1],'suite_summary':suite_rows,'task_class_counts':dict(classes),'changed_historical_task_keys':changed_task_keys,'historical_impact_class_counts':dict(relevant_classes),'a13_original':a13_original,'a13_excluding_all_version_changed_historical_tasks':a13_filtered_res,'p2b_excluding_all_version_changed_historical_tasks':p2b_diag,'agentwatcher_attack_anchor_benchmark_version':pop.get('agentwatcher_attack_anchor_benchmark_version'),'agentwatcher_attack_anchor_pair_count':len(attack_pair_rows),'gate_status':gate,'claim_boundary':'This audit does not modify frozen historical results; it only determines version-specific qualification or need for targeted revalidation.'}

    write_json(out/'P0BV_RESULT.json',result);write_csv(out/'P0BV_SUITE_SUMMARY.csv',suite_rows);write_csv(out/'P0BV_USER_TASK_DIFFS.csv',task_rows);write_csv(out/'P0BV_INJECTION_TASK_DIFFS.csv',inj_rows);write_csv(out/'P0BV_TOOL_DIFFS.csv',tool_rows);write_csv(out/'P0BV_PAPER_POPULATION_IMPACT.csv',impact);write_csv(out/'P0BV_AGENTWATCHER_ATTACK_PAIR_VERSION_MAP.csv',attack_pair_rows);write_jsonl(out/'P0BV_USER_TASK_SIGNATURES.jsonl',all_task_sigs);write_jsonl(out/'P0BV_INJECTION_TASK_SIGNATURES.jsonl',all_inj_sigs)

    changed_rows=[r for r in task_rows if r['classification']!='IDENTICAL_FOR_OUR_ESTIMAND']
    md=['# P0b-V — AgentDojo v1 ↔ v1.2.2 compatibility audit','',f'**Gate status:** `{gate}`','',f'- Scientific model calls: **0**',f'- Installed package: **agentdojo=={importlib.metadata.version("agentdojo")}**',f'- Benchmark suites compared: **{versions[0]} vs {versions[1]}**',f'- AgentWatcher 200-pair attack anchor was already frozen on **{pop.get("agentwatcher_attack_anchor_benchmark_version")}**.', '', '## Suite-level compatibility','']
    for r in suite_rows:md.append(f"- {r['suite']}: environment_changed={r['environment_changed']}, tools_changed={r['tools_changed']}, changed user tasks={r['changed_user_tasks']}, changed injection tasks={r['changed_injection_tasks']}.")
    md += ['', '## Changed user tasks', '']
    for r in changed_rows:md.append(f"- `{r['task_key']}` → **{r['classification']}**; fields: `{r['difference_fields']}`")
    md += ['', '## Historical paper-bearing overlap', '', f'- Unique changed task keys touching A13/A15a/P2b/AgentWatcher-natural: **{len(changed_task_keys)}**: '+(', '.join(f'`{x}`' for x in changed_task_keys) if changed_task_keys else 'none')+'.']
    if a13_original and a13_filtered_res:
        md.append(f"- A13 task-weighted H: original difference **{a13_original['difference']:+.4f}**, excluding all changed historical task keys **{a13_filtered_res['difference']:+.4f}** with 95% task-bootstrap CI **[{a13_filtered_res['ci95'][0]:+.4f}, {a13_filtered_res['ci95'][1]:+.4f}]**.")
    if p2b_diag:
        md += ['', '## Corrected-P2b all-changed-task deletion diagnostic', '']
        for d in p2b_diag:
            z=d['excluding_all_version_changed_historical_tasks'];md.append(f"- {d['model']}: n={z['n_decisions']}; action-local **{100*z['action_local_rate']:.1f}%** ({z['action_majority_cells']} majority cells); downstream **{100*z['downstream_rate']:.1f}%** ({z['downstream_majority_cells']} majority cells).")
    md += ['', '## Interpretation lock', '', '- Historical A13/A15a/P2b/AgentWatcher-natural results remain frozen and must be called AgentDojo-v1 evidence.', '- A14-Minimal is not affected by this task-suite mismatch.', '- The AgentWatcher attack anchor is not a historical-v1 mismatch because its own freeze is v1.2.2.', '- Do not authorize a broad rerun automatically. A targeted revalidation branch, if any, is decided only after manual review of the changed-task rows and source signatures.', '- P0b-3 calibration must use v1.2.2.']
    (out/'P0BV_SUMMARY.md').write_text('\n'.join(md)+'\n')
    print('P0b-V COMPATIBILITY AUDIT COMPLETE')
    print('gate_status=',gate)
    print('changed_historical_task_keys=',len(changed_task_keys),','.join(changed_task_keys))
    print('attack_anchor_benchmark_version=',pop.get('agentwatcher_attack_anchor_benchmark_version'))

if __name__=='__main__':main()
