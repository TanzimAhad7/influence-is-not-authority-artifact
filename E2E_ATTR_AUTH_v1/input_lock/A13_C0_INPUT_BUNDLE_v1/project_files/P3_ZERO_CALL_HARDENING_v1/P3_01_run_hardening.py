#!/usr/bin/env python3
import argparse, csv, hashlib, json, math, random, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path


def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def load_jsonl(p):
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]

def mean(xs):
    return statistics.mean(xs) if xs else None

def quantile(sorted_vals, q):
    if not sorted_vals: return None
    if len(sorted_vals)==1: return sorted_vals[0]
    pos=q*(len(sorted_vals)-1); lo=math.floor(pos); hi=math.ceil(pos)
    if lo==hi: return sorted_vals[lo]
    w=pos-lo; return sorted_vals[lo]*(1-w)+sorted_vals[hi]*w

def pct(x):
    return 'NA' if x is None else f'{100*x:.1f}%'

def norm_model(k):
    return 'qwen' if k.startswith('qwen') else k

def rankdata(xs):
    order=sorted(range(len(xs)), key=lambda i: xs[i]); ranks=[0.0]*len(xs); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and xs[order[j]]==xs[order[i]]: j+=1
        r=(i+1+j)/2.0
        for k in range(i,j): ranks[order[k]]=r
        i=j
    return ranks

def pearson(xs,ys):
    if len(xs)<2:return None
    mx,my=mean(xs),mean(ys); dx=[x-mx for x in xs]; dy=[y-my for y in ys]
    den=math.sqrt(sum(x*x for x in dx)*sum(y*y for y in dy))
    return None if den==0 else sum(a*b for a,b in zip(dx,dy))/den

def spearman(xs,ys):
    return pearson(rankdata(xs),rankdata(ys)) if len(xs)>=2 else None

def per_task_label_values(records, field):
    buckets=defaultdict(lambda:defaultdict(list))
    for r in records:
        if not r.get('primary_valid') or r.get('development'): continue
        lab=r.get('label')
        if lab not in {'SPECIFIED','DELEGATED'}: continue
        v=r.get(field)
        if isinstance(v,bool): v=float(v)
        if v is None: continue
        try: v=float(v)
        except: continue
        if math.isfinite(v): buckets[r['task_key']][lab].append(v)
    return {tk:{lab:mean(vs) for lab,vs in dd.items()} for tk,dd in buckets.items()}

def clustered_contrast(records, field, B, seed):
    tv=per_task_label_values(records,field); tids=sorted(tv)
    def calc(sample):
        s=[];d=[]
        for tk in sample:
            if 'SPECIFIED' in tv[tk]: s.append(tv[tk]['SPECIFIED'])
            if 'DELEGATED' in tv[tk]: d.append(tv[tk]['DELEGATED'])
        if not s or not d:return None
        return {'specified_mean':mean(s),'delegated_mean':mean(d),'difference':mean(s)-mean(d),'n_specified_tasks':len(s),'n_delegated_tasks':len(d)}
    pt=calc(tids)
    draws=[]; rng=random.Random(seed+sum(map(ord,field)))
    for _ in range(B):
        samp=[tids[rng.randrange(len(tids))] for __ in tids]
        z=calc(samp)
        if z: draws.append(z['difference'])
    draws.sort(); pt['ci95']=[quantile(draws,.025),quantile(draws,.975)]; pt['bootstrap_valid_draws']=len(draws)
    return pt

def cluster_boot_diff(cells, metric, group_key, g1, g0, B, seed):
    bydec=defaultdict(list)
    for c in cells: bydec[c['decision_id']].append(c)
    d1=[d for d,cs in bydec.items() if cs[0][group_key]==g1]
    d0=[d for d,cs in bydec.items() if cs[0][group_key]==g0]
    def dmean(ds):
        vals=[c[metric] for d in ds for c in bydec[d]]
        return mean(vals)
    p1,p0=dmean(d1),dmean(d0); point=p1-p0
    rng=random.Random(seed+sum(map(ord,metric+str(group_key)+str(g1)+str(g0)))); draws=[]
    for _ in range(B):
        s1=[d1[rng.randrange(len(d1))] for __ in d1]; s0=[d0[rng.randrange(len(d0))] for __ in d0]
        draws.append(dmean(s1)-dmean(s0))
    draws.sort()
    return {'group1':g1,'group0':g0,'n_decisions_group1':len(d1),'n_decisions_group0':len(d0),'mean_group1':p1,'mean_group0':p0,'difference':point,'ci95':[quantile(draws,.025),quantile(draws,.975)]}

def fleiss_kappa(binary_by_dec):
    # 3 raters/models, 2 classes. binary_by_dec: dict decision -> list 0/1
    n=len(binary_by_dec)
    if not n:return None
    N=3
    P=[]; total1=0
    for vals in binary_by_dec.values():
        n1=sum(vals); n0=N-n1; total1+=n1
        P.append((n0*(n0-1)+n1*(n1-1))/(N*(N-1)))
    Pbar=mean(P); p1=total1/(n*N); p0=1-p1; Pe=p0*p0+p1*p1
    return None if Pe==1 else (Pbar-Pe)/(1-Pe)

def write_csv(path, rows):
    rows=list(rows)
    if not rows:
        path.write_text(''); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def verify_freeze(freeze_path):
    fr=json.load(open(freeze_path))
    bad=[]
    for k,d in fr['input_files'].items():
        p=Path(d['path'])
        if not p.exists(): bad.append(f'{k}: missing {p}')
        elif sha256(p)!=d['sha256']: bad.append(f'{k}: hash changed')
    if bad:
        raise RuntimeError('Freeze verification failed:\n'+'\n'.join(bad))
    return fr

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root',required=True)
    ap.add_argument('--package-dir',default=str(Path(__file__).resolve().parent))
    ap.add_argument('--out-dir',required=True)
    args=ap.parse_args()
    root=Path(args.project_root).resolve(); pkg=Path(args.package_dir).resolve(); out=Path(args.out_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    freeze_path=out/'P3_ANALYSIS_FREEZE.json'
    if not freeze_path.exists(): raise SystemExit('Run P3_00_freeze_analysis.py first.')
    fr=verify_freeze(freeze_path); cfg=fr['config']; B=int(cfg['bootstrap_repetitions']); seed=int(cfg['bootstrap_seed']); thr=float(cfg['cell_majority_threshold'])

    # ---------------- Natural A13/A15a ----------------
    a13=load_jsonl(root/'a13/decisions.jsonl')
    a15=load_jsonl(root/'a15a_selectivity_consequence/decision_inventory.jsonl')
    a13_results=json.load(open(root/'a13/results.json'))
    a15_results=json.load(open(root/'a15a_selectivity_consequence/results.json'))
    a13_primary=[r for r in a13 if r.get('primary_valid') and not r.get('development')]
    a13_h=clustered_contrast(a13_primary,'H_mean_del',B,seed)
    a13_m=clustered_contrast(a13_primary,'M_del',B,seed)

    suites=sorted({r['suite'] for r in a13_primary})
    a13_loso=[]
    for s in suites:
        rr=[r for r in a13_primary if r['suite']!=s]
        h=clustered_contrast(rr,'H_mean_del',B,seed); m=clustered_contrast(rr,'M_del',B,seed)
        a13_loso.append({'excluded_suite':s,'H_difference':h['difference'],'H_ci_low':h['ci95'][0],'H_ci_high':h['ci95'][1],'M_difference':m['difference'],'M_ci_low':m['ci95'][0],'M_ci_high':m['ci95'][1]})

    tasks=sorted({r['task_key'] for r in a13_primary})
    a13_loto=[]
    for tk in tasks:
        rr=[r for r in a13_primary if r['task_key']!=tk]
        h=clustered_contrast(rr,'H_mean_del',max(1000,min(B,5000)),seed)
        a13_loto.append({'excluded_task':tk,'H_difference':h['difference']})

    # task-level span alternative-explanation diagnostics
    taskagg={}
    for tk in sorted({r['task_key'] for r in a13_primary}):
        rs=[r for r in a13_primary if r['task_key']==tk]
        taskagg[tk]={
          'task_key':tk,'suite':rs[0]['suite'],
          'specified_fraction':mean([float(r['specified_fraction']) for r in rs if r.get('specified_fraction') is not None]),
          'n_eligible_tool_spans':mean([float(r.get('n_eligible_tool_spans',0)) for r in rs]),
          'H_mean_del':mean([float(bool(r['H_mean_del'])) for r in rs]),
          'M_del':mean([float(r['M_del']) for r in rs]),
          'labels':','.join(sorted({r['label'] for r in rs}))
        }
    ta=list(taskagg.values()); xs=[r['n_eligible_tool_spans'] for r in ta]
    span_diag={
      'n_tasks':len(ta),
      'spans_vs_H_pearson':pearson(xs,[r['H_mean_del'] for r in ta]),
      'spans_vs_H_spearman':spearman(xs,[r['H_mean_del'] for r in ta]),
      'spans_vs_M_pearson':pearson(xs,[r['M_del'] for r in ta]),
      'spans_vs_M_spearman':spearman(xs,[r['M_del'] for r in ta]),
      'spans_vs_specified_fraction_pearson':pearson(xs,[r['specified_fraction'] for r in ta]),
      'spans_vs_specified_fraction_spearman':spearman(xs,[r['specified_fraction'] for r in ta])
    }

    # A15a selectivity: by suite and label, plus leave-one-suite-out gap between activated and specified baseline
    a15_suite=[]
    for s in sorted({r['suite'] for r in a15}):
        rs=[r for r in a15 if r['suite']==s]
        a15_suite.append({'suite':s,'n_decisions':len(rs),'activation_rate':mean([float(bool(r['ca_flag_tau0'])) for r in rs]),'mean_eligible_spans':mean([r['n_eligible_tool_spans'] for r in rs]),'mean_flagged_spans':mean([r['n_flagged_spans_tau0'] for r in rs])})
    a15_loso=[]
    for s in sorted({r['suite'] for r in a15}):
        rs=[r for r in a15 if r['suite']!=s]
        spec=[float(bool(r['ca_flag_tau0'])) for r in rs if r['label']=='SPECIFIED']
        nonspec=[float(bool(r['ca_flag_tau0'])) for r in rs if r['label'] in {'DELEGATED','PARTIAL'}]
        a15_loso.append({'excluded_suite':s,'overall_activation_rate':mean([float(bool(r['ca_flag_tau0'])) for r in rs]),'specified_activation_rate':mean(spec),'delegated_partial_activation_rate':mean(nonspec),'gap_nonspec_minus_specified':(mean(nonspec)-mean(spec)) if spec and nonspec else None})

    # ---------------- Corrected P2b ----------------
    tax=json.load(open(root/'P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/P2B_ARGUMENT_ROLE_TAXONOMY.json'))
    inv=load_jsonl(root/'P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/inputs/P2B_REPLAY_INVENTORY.jsonl')
    invmap={r['decision_id']:r for r in inv}
    raws=[]
    runmap={'llama':'P2B_XM_CI_LLAMA_RUN_v1_2','gemma':'P2B_XM_CI_GEMMA_RUN_v1_2','qwen':'P2B_XM_CI_QWEN_RUN_v1_2'}
    for model,d in runmap.items():
        rr=load_jsonl(root/d/'P2B_CI_BASELINE_RAW.jsonl')
        for r in rr:
            r=dict(r); r['model']=model; r['masking']=bool(r['utility_preserved'] and not r['action_local_preserved'])
            raws.append(r)
    # integrity
    instrument_bad=[r for r in raws if r.get('interface_status') in {'FORMAT_INSTRUMENT_VIOLATION','ACTION_CONTRACT_VIOLATION'}]
    groups=defaultdict(list)
    for r in raws: groups[(r['model'],r['decision_id'])].append(r)
    if len(raws)!=390 or len(groups)!=78 or instrument_bad:
        raise RuntimeError(f'Corrected P2b integrity failure rows={len(raws)} cells={len(groups)} instrument_bad={len(instrument_bad)}')
    for k,rr in groups.items():
        if len(rr)!=5: raise RuntimeError(f'Cell {k} has {len(rr)} repeats, expected 5')

    cells=[]
    for (model,did),rr in sorted(groups.items()):
        meta=invmap[did]; roles=tax['per_decision'][did]; role_counts=Counter(roles.values())
        action_rate=mean([float(bool(r['action_local_preserved'])) for r in rr]); down_rate=mean([float(bool(r['utility_preserved'])) for r in rr]); mask_rate=mean([float(bool(r['masking'])) for r in rr])
        cells.append({
          'model':model,'decision_id':did,'suite':meta['suite'],'function':meta['target_action']['function'],'label':meta['label'],'activated':bool(meta['activated_tau0']),
          'open_text':role_counts['OPEN_TEXT']>0,'n_open_text':role_counts['OPEN_TEXT'],'n_reference_identity':role_counts['REFERENCE_IDENTITY'],'n_structured_scalar':role_counts['STRUCTURED_SCALAR'],'n_opaque_exact':role_counts['OPAQUE_EXACT'],
          'action_local_rate':action_rate,'downstream_rate':down_rate,'masking_rate':mask_rate,
          'action_majority':action_rate>=thr,'downstream_majority':down_rate>=thr,'masking_majority':mask_rate>=thr,
          'repeat_invariant_action':len({bool(r['action_local_preserved']) for r in rr})==1,
          'repeat_invariant_downstream':len({bool(r['utility_preserved']) for r in rr})==1,
          'repeat_invariant_masking':len({bool(r['masking']) for r in rr})==1
        })

    key_sens={}
    for metric in ['action_local_rate','downstream_rate','masking_rate']:
        key_sens[f'activated_vs_control_{metric}']=cluster_boot_diff(cells,metric,'activated',True,False,B,seed)
        key_sens[f'open_text_vs_no_open_text_{metric}']=cluster_boot_diff(cells,metric,'open_text',True,False,B,seed)

    # subgroup summaries by activation/label/open_text/suite/function/model
    subgroup=[]
    for var in ['activated','label','open_text','suite','function','model']:
        vals=sorted({str(c[var]) for c in cells})
        for sv in vals:
            cs=[c for c in cells if str(c[var])==sv]
            subgroup.append({'variable':var,'value':sv,'n_cells':len(cs),'n_decisions':len({c['decision_id'] for c in cs}),'action_local_rate':mean([c['action_local_rate'] for c in cs]),'downstream_rate':mean([c['downstream_rate'] for c in cs]),'masking_rate':mean([c['masking_rate'] for c in cs])})

    def gap_after_filter(exclude_var, exclude_value):
        cs=[c for c in cells if c[exclude_var]!=exclude_value]
        a=[c for c in cs if c['activated']]; b=[c for c in cs if not c['activated']]
        return {
          'excluded_variable':exclude_var,'excluded_value':exclude_value,
          'n_cells':len(cs),'n_decisions':len({c['decision_id'] for c in cs}),
          'action_gap_activated_minus_control':mean([c['action_local_rate'] for c in a])-mean([c['action_local_rate'] for c in b]),
          'downstream_gap_activated_minus_control':mean([c['downstream_rate'] for c in a])-mean([c['downstream_rate'] for c in b]),
          'masking_gap_activated_minus_control':mean([c['masking_rate'] for c in a])-mean([c['masking_rate'] for c in b])
        }
    los_suite=[gap_after_filter('suite',s) for s in sorted({c['suite'] for c in cells})]
    los_fn=[gap_after_filter('function',f) for f in sorted({c['function'] for c in cells})]
    los_dec=[gap_after_filter('decision_id',d) for d in sorted({c['decision_id'] for c in cells})]

    # within-stratum activated/control descriptives
    within=[]
    for var in ['suite','function','label','open_text']:
        for v in sorted({str(c[var]) for c in cells}):
            cs=[c for c in cells if str(c[var])==v]; a=[c for c in cs if c['activated']]; b=[c for c in cs if not c['activated']]
            if a and b:
                within.append({'stratum_variable':var,'stratum_value':v,'activated_cells':len(a),'control_cells':len(b),'action_gap':mean([c['action_local_rate'] for c in a])-mean([c['action_local_rate'] for c in b]),'downstream_gap':mean([c['downstream_rate'] for c in a])-mean([c['downstream_rate'] for c in b]),'masking_gap':mean([c['masking_rate'] for c in a])-mean([c['masking_rate'] for c in b])})

    # cross-model recurrence
    bydec=defaultdict(list)
    for c in cells: bydec[c['decision_id']].append(c)
    unanimous=[]; bink={}
    for did,cs in sorted(bydec.items()):
        vals=[int(c['action_majority']) for c in sorted(cs,key=lambda z:z['model'])]; bink[did]=vals
        status='ALL_PASS' if sum(vals)==3 else ('ALL_FAIL' if sum(vals)==0 else 'MIXED')
        m=invmap[did]; roles=Counter(tax['per_decision'][did].values())
        unanimous.append({'decision_id':did,'suite':m['suite'],'function':m['target_action']['function'],'label':m['label'],'activated':m['activated_tau0'],'open_text':roles['OPEN_TEXT']>0,'status':status,'n_pass_models':sum(vals),'llama_pass':next(c['action_majority'] for c in cs if c['model']=='llama'),'gemma_pass':next(c['action_majority'] for c in cs if c['model']=='gemma'),'qwen_pass':next(c['action_majority'] for c in cs if c['model']=='qwen')})
    kappa=fleiss_kappa(bink)
    oldweak=set(cfg['original_qwen_majority_weak_decisions'])
    recurrence=[dict(r,original_qwen_weak=(r['decision_id'] in oldweak)) for r in unanimous if r['decision_id'] in oldweak]

    # masking row anatomy + slot mismatches
    slot_index={}
    for model,d in runmap.items():
        p=root/d/'P2B_CI_ARGUMENT_SLOT_ROWS.csv'
        with p.open(newline='') as f:
            for r in csv.DictReader(f):
                key=(model,r['decision_id'],int(r['repeat_index']))
                slot_index.setdefault(key,[]).append(r)
    masked=[]; mismatch_counts=Counter(); masked_structure=Counter(); cond_masked=0
    for r in raws:
        if not r['masking']: continue
        model=r['model']; did=r['decision_id']; rep=int(r['repeat_index']); meta=invmap[did]
        slots=slot_index.get((model,did,rep),[])
        mism=sorted({s['argument_class'] for s in slots if s['exact_json_match'].lower()!='true'})
        if slots: cond_masked+=1
        for cls in mism: mismatch_counts[cls]+=1
        masked_structure[r['candidate_action_structure']]+=1
        masked.append({'model':model,'decision_id':did,'repeat_index':rep,'activated':meta['activated_tau0'],'label':meta['label'],'suite':meta['suite'],'function':meta['target_action']['function'],'candidate_action_structure':r['candidate_action_structure'],'target_function_unique_only':r['target_function_unique_only'],'interface_status':r['interface_status'],'mismatch_classes':';'.join(mism),'has_open_text_mismatch':'OPEN_TEXT' in mism,'has_reference_identity_mismatch':'REFERENCE_IDENTITY' in mism,'has_structured_scalar_mismatch':'STRUCTURED_SCALAR' in mism,'has_opaque_exact_mismatch':'OPAQUE_EXACT' in mism})

    # Conditional actual-tool schema/execution validity
    toolrows=[r for r in raws if r['interface_status']=='PARSED_TOOL']
    cond_tool={}
    for model in ['llama','gemma','qwen']:
        rs=[r for r in toolrows if r['model']==model]
        cond_tool[model]={'n_parsed_tool':len(rs),'schema_valid':sum(bool(r['candidate_tool_schema_valid']) for r in rs),'execution_valid':sum(bool(r['candidate_tool_execution_valid']) for r in rs)}
    cond_tool['joint']={'n_parsed_tool':len(toolrows),'schema_valid':sum(bool(r['candidate_tool_schema_valid']) for r in toolrows),'execution_valid':sum(bool(r['candidate_tool_execution_valid']) for r in toolrows)}

    # summaries
    allpass=sum(r['status']=='ALL_PASS' for r in unanimous); allfail=sum(r['status']=='ALL_FAIL' for r in unanimous)
    result={
      'schema':'P3_ZERO_CALL_HARDENING_RESULT_V1',
      'status':'POSTHOC_FALSIFICATION_AND_SENSITIVITY_ANALYSIS',
      'scientific_model_calls':0,
      'freeze_sha256':sha256(freeze_path),
      'a13':{'recomputed_H':a13_h,'original_H':a13_results['primary_H_mean_del'],'recomputed_M':a13_m,'span_alternative_explanation':span_diag,'leave_one_suite_out':a13_loso,'leave_one_task_out_range':[min(r['H_difference'] for r in a13_loto),max(r['H_difference'] for r in a13_loto)]},
      'a15a':{'original_results':a15_results,'suite_summary':a15_suite,'leave_one_suite_out':a15_loso},
      'p2b':{
        'rows':len(raws),'model_decision_cells':len(cells),'decisions':len(bydec),
        'repeat_invariant_action_cells':sum(c['repeat_invariant_action'] for c in cells),'repeat_invariant_downstream_cells':sum(c['repeat_invariant_downstream'] for c in cells),'repeat_invariant_masking_cells':sum(c['repeat_invariant_masking'] for c in cells),
        'key_sensitivities':key_sens,
        'cross_model_action_unanimity':{'all_pass_decisions':allpass,'all_fail_decisions':allfail,'mixed_decisions':26-allpass-allfail,'unanimous_total':allpass+allfail,'fleiss_kappa':kappa},
        'original_qwen_weak_recurrence':recurrence,
        'masked_generation_count':len(masked),'masked_conditioned_slot_rows_generations':cond_masked,'masked_candidate_structures':dict(masked_structure),'masked_mismatch_class_presence_counts':dict(mismatch_counts),
        'conditional_actual_tool_validity':cond_tool,
        'leave_one_suite_out_masking_gap_range':[min(r['masking_gap_activated_minus_control'] for r in los_suite),max(r['masking_gap_activated_minus_control'] for r in los_suite)],
        'leave_one_function_out_masking_gap_range':[min(r['masking_gap_activated_minus_control'] for r in los_fn),max(r['masking_gap_activated_minus_control'] for r in los_fn)],
        'leave_one_decision_out_masking_gap_range':[min(r['masking_gap_activated_minus_control'] for r in los_dec),max(r['masking_gap_activated_minus_control'] for r in los_dec)]
      },
      'claim_boundaries':cfg['claim_boundaries']
    }

    # write artifacts
    (out/'P3_HARDENING.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    write_csv(out/'P3_A13_LEAVE_ONE_SUITE_OUT.csv',a13_loso)
    write_csv(out/'P3_A13_LEAVE_ONE_TASK_OUT.csv',a13_loto)
    write_csv(out/'P3_A13_TASK_SPAN_DIAGNOSTICS.csv',ta)
    write_csv(out/'P3_A15A_SUITE_SUMMARY.csv',a15_suite)
    write_csv(out/'P3_A15A_LEAVE_ONE_SUITE_OUT.csv',a15_loso)
    write_csv(out/'P3_P2B_MODEL_DECISION_CELLS.csv',cells)
    write_csv(out/'P3_P2B_SUBGROUP_SUMMARY.csv',subgroup)
    write_csv(out/'P3_P2B_WITHIN_STRATUM.csv',within)
    write_csv(out/'P3_P2B_LEAVE_ONE_SUITE_OUT.csv',los_suite)
    write_csv(out/'P3_P2B_LEAVE_ONE_FUNCTION_OUT.csv',los_fn)
    write_csv(out/'P3_P2B_LEAVE_ONE_DECISION_OUT.csv',los_dec)
    write_csv(out/'P3_P2B_CROSS_MODEL_DECISIONS.csv',unanimous)
    write_csv(out/'P3_P2B_ORIGINAL_QWEN_WEAK_RECURRENCE.csv',recurrence)
    write_csv(out/'P3_P2B_MASKED_ROWS.csv',masked)

    # reviewer-facing markdown
    ka=key_sens['activated_vs_control_action_local_rate']; kd=key_sens['activated_vs_control_downstream_rate']; km=key_sens['activated_vs_control_masking_rate']; ko=key_sens['open_text_vs_no_open_text_action_local_rate']
    lines=[
      '# P3 — zero-model-call natural + estimand hardening', '',
      '**Status:** completed post-hoc falsification/sensitivity analysis; not a new prospective endpoint.', '',
      '## 1. A13 natural-result hardening', '',
      f'- Recomputed task-weighted H contrast: SPECIFIED `{a13_h["specified_mean"]:.4f}` vs DELEGATED `{a13_h["delegated_mean"]:.4f}`; difference **{a13_h["difference"]:+.4f}**, 95% task-bootstrap CI **[{a13_h["ci95"][0]:+.4f}, {a13_h["ci95"][1]:+.4f}]**.',
      f'- Original frozen result: difference `{a13_results["primary_H_mean_del"]["difference"]:+.4f}`, CI `{a13_results["primary_H_mean_del"]["ci95"]}`. The recomputation should match modulo deterministic bootstrap implementation details.',
      f'- Leave-one-suite-out H differences span **[{min(r["H_difference"] for r in a13_loso):+.4f}, {max(r["H_difference"] for r in a13_loso):+.4f}]**.',
      f'- Leave-one-task-out H differences span **[{min(r["H_difference"] for r in a13_loto):+.4f}, {max(r["H_difference"] for r in a13_loto):+.4f}]**.',
      f'- Eligible-span count vs task-level H: Pearson `{span_diag["spans_vs_H_pearson"]}`, Spearman `{span_diag["spans_vs_H_spearman"]}`.', '',
      '## 2. A15a selectivity hardening', '',
      f'- Frozen activation: **{a15_results["activated_decisions_tau0"]}/{a15_results["eligible_decisions"]} = {pct(a15_results["decision_activation_rate_tau0"])}**.',
      '- See `P3_A15A_SUITE_SUMMARY.csv` and `P3_A15A_LEAVE_ONE_SUITE_OUT.csv` for suite composition/influence.', '',
      '## 3. Corrected P2b: action-local vs downstream estimand separation', '',
      f'- Analysis unit: **{len(cells)} model×decision cells across {len(bydec)} decisions**; five repeats are stability repetitions, not independent mass-sample units.',
      f'- Action-local: activated **{pct(ka["mean_group1"])}** vs controls **{pct(ka["mean_group0"])}**; difference **{100*ka["difference"]:+.1f} pp**, decision-cluster bootstrap CI **[{100*ka["ci95"][0]:+.1f}, {100*ka["ci95"][1]:+.1f}] pp**.',
      f'- Downstream: activated **{pct(kd["mean_group1"])}** vs controls **{pct(kd["mean_group0"])}**; difference **{100*kd["difference"]:+.1f} pp**, clustered CI **[{100*kd["ci95"][0]:+.1f}, {100*kd["ci95"][1]:+.1f}] pp**.',
      f'- Downstream-PASS/action-local-FAIL masking: activated **{pct(km["mean_group1"])}** vs controls **{pct(km["mean_group0"])}**; difference **{100*km["difference"]:+.1f} pp**, clustered CI **[{100*km["ci95"][0]:+.1f}, {100*km["ci95"][1]:+.1f}] pp**.',
      f'- Masking gap after leaving out one suite spans **[{100*result["p2b"]["leave_one_suite_out_masking_gap_range"][0]:+.1f}, {100*result["p2b"]["leave_one_suite_out_masking_gap_range"][1]:+.1f}] pp**.',
      f'- After leaving out one function spans **[{100*result["p2b"]["leave_one_function_out_masking_gap_range"][0]:+.1f}, {100*result["p2b"]["leave_one_function_out_masking_gap_range"][1]:+.1f}] pp**.',
      f'- After leaving out one decision spans **[{100*result["p2b"]["leave_one_decision_out_masking_gap_range"][0]:+.1f}, {100*result["p2b"]["leave_one_decision_out_masking_gap_range"][1]:+.1f}] pp**.', '',
      '## 4. Argument-role / decision-structure hardening', '',
      f'- OPEN_TEXT-present decisions action-local rate **{pct(ko["mean_group1"])}** vs no-OPEN_TEXT **{pct(ko["mean_group0"])}**; difference **{100*ko["difference"]:+.1f} pp**, decision-cluster CI **[{100*ko["ci95"][0]:+.1f}, {100*ko["ci95"][1]:+.1f}] pp**.',
      f'- Cross-model action-local unanimity: **{allpass} ALL_PASS + {allfail} ALL_FAIL = {allpass+allfail}/26 unanimous**, mixed `{26-allpass-allfail}/26`; exploratory Fleiss κ = **{kappa:.3f}**.',
      '- Original Qwen-native weak-decision recurrence is in `P3_P2B_ORIGINAL_QWEN_WEAK_RECURRENCE.csv`.', '',
      '## 5. Masked-row anatomy', '',
      f'- Total downstream-PASS/action-local-FAIL generations: **{len(masked)}**.',
      f'- Candidate action structures: `{dict(masked_structure)}`.',
      f'- Mismatch-class presence among rows with a uniquely located target call: `{dict(mismatch_counts)}`.', '',
      '## 6. Conditional actual-tool validity', ''
    ]
    for model,d in cond_tool.items():
        lines.append(f'- {model}: parsed-tool `{d["n_parsed_tool"]}`, schema-valid `{d["schema_valid"]}/{d["n_parsed_tool"]}`, execution-valid `{d["execution_valid"]}/{d["n_parsed_tool"]}`.')
    lines += ['', '## 7. Interpretation rules', ''] + [f'- {x}' for x in cfg['claim_boundaries']]
    lines += ['', '### Decision rule for the paper', '',
      '- If A13 direction and the key P2b descriptive patterns remain sign-stable under aggressive suite/function/decision deletion, report them as robust **sensitivity/descriptive** evidence.',
      '- If a pattern flips under one small subgroup, demote it to a limitation and do not build the paper story around it.',
      '- Regardless of outcome, preserve the frozen A13/A15a/P2b primary results unchanged.'
    ]
    (out/'P3_HARDENING_SUMMARY.md').write_text('\n'.join(lines)+'\n')
    print('P3 HARDENING COMPLETE')
    print(out/'P3_HARDENING_SUMMARY.md')

if __name__=='__main__': main()
