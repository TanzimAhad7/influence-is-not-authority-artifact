#!/usr/bin/env python3
from __future__ import annotations
import copy, datetime as dt, hashlib, json, sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent if Path(__file__).resolve().parent.name == 'B1_C0_POPULATION_AMENDMENT_v2' else Path(__file__).resolve().parent
PKG = ROOT / 'B1_C0_POPULATION_AMENDMENT_v2'
OLD = ROOT / 'b1_a12_backbone_replication'
OUT = ROOT / 'b1_a12_backbone_replication_c0_v2'
HIST_TAX = ROOT / 'a13/taxonomy.json'
C0_PREFREEZE = ROOT / 'A13_C0_EXTENSION_PREFREEZE_v1/A13_C0_EXTENSION_FREEZE_v1.json'
C0_RUNNER_FREEZE = ROOT / 'A13_C0_EXTENSION_RUNNER_FREEZE_v1/A13_C0_EXTENSION_RUNNER_FREEZE_v1.json'
C0_COMBINED = ROOT / 'A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl'

EXPECTED = {
    'b1_a12_backbone_replication/protocol.json': 'e7c74b3499446d053155e5a3140367fa2013c16ef18b08bfd952986b7e785434',
    'b1_a12_backbone_replication/task_manifest.json': 'f5305527f168ca227432f515395a7cea545aadffa7606f87f86caef99d5ad667',
    'b1_a12_backbone_replication/taxonomy.json': '02894700c2ff370b28b858a6f533805c37fd11d86bb1c70af3b71ac21cdc674b',
    'b1_a12_backbone_replication/FREEZE_COMPLETE.json': '7d4b86223c9b4ec2da73865136590468d91ce3f60bbca1f718cf4b74b5c25b53',
    'a13/taxonomy.json': '02894700c2ff370b28b858a6f533805c37fd11d86bb1c70af3b71ac21cdc674b',
    'A13_C0_EXTENSION_PREFREEZE_v1/A13_C0_EXTENSION_FREEZE_v1.json': '41ce8878845184e4306a7817c490f1d679999475b3cae2f5512d7ec66595624c',
    'A13_C0_EXTENSION_RUNNER_FREEZE_v1/A13_C0_EXTENSION_RUNNER_FREEZE_v1.json': '6e700c303c648b36ad99fcb07f1fe1339668ecb75f535f05081760a45fd21bb3',
    'A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl': 'f24b89d53ad504cf16dce3820e9b028f1d752bcc829ecf43ed3e0997feb764f5',
    'A13_R3_Gemini.py': '1fdc1bc127cb5415b4dd1133abbd9ffdce97b0cf490edfb78399cecd9a78c719',
    'start_A13_R1_Llama_vLLM.sh': 'aeddbb05d32fa9fc690d4556e521fd3dae7ad3b4568e01e7244ee7732a8b02b4',
}
OLD_PROTOCOL_HASH = '61f47a7507f03b01931e6c5b3452dfe43ac9a9b67b52b3079b85214880c7827f'
EXPECTED_EXT_IDS = {
    'workspace/user_task_13/c0ext_gt2/append_to_file',
    'workspace/user_task_29/c0ext_gt1/append_to_file',
    'workspace/user_task_34/c0ext_gt2/append_to_file',
    'workspace/user_task_7/c0ext_gt1/reschedule_calendar_event',
}
ADDED_FUNCTIONS = {'append_to_file', 'reschedule_calendar_event'}
ALLOWED = {'SPECIFIED', 'DELEGATED', 'PARTIAL'}
EXPECTED_LABELS = {'SPECIFIED': 22, 'DELEGATED': 24, 'PARTIAL': 27}
EXPECTED_SUITE_TASKS = {'workspace': 19, 'slack': 18, 'travel': 6, 'banking': 12}


def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def sha(p: Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def stable(x): return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
def dump(p: Path, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(x, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
def read(p: Path): return json.loads(p.read_text(encoding='utf-8'))

def require(cond, msg):
    if not cond: sys.exit('FATAL: ' + msg)

def verify_inputs():
    for rel, exp in EXPECTED.items():
        p = ROOT / rel
        require(p.exists(), f'missing required input {rel}')
        got = sha(p)
        require(got == exp, f'hash mismatch {rel}: expected {exp}, got {got}')
    oldp = read(OLD/'protocol.json')
    oldc = read(OLD/'FREEZE_COMPLETE.json')
    require(oldp.get('protocol_hash') == OLD_PROTOCOL_HASH, 'historical B1 protocol hash drift')
    require(oldc.get('protocol_hash') == OLD_PROTOCOL_HASH, 'historical B1 certificate hash drift')
    require(oldp['task_population']['n_tasks'] == 52, 'historical B1 must remain 52 tasks')
    # No historical B1 scientific outcomes may exist before this population-only amendment.
    for key in ['gpt4o','claude45']:
        d = OLD/key
        if d.exists():
            bad = [d/n for n in ['decisions.jsonl','results.json','REPORT.md'] if (d/n).exists()]
            require(not bad, f'historical B1 outcome exists before amendment: {bad}')
    # Likewise refuse to overwrite a partial/scientific v2 run.
    for key in ['gpt4o','claude45']:
        d = OUT/key
        if d.exists():
            bad = [d/n for n in ['decisions.jsonl','results.json','REPORT.md'] if (d/n).exists()]
            require(not bad, f'v2 scientific outcome already exists: {bad}')

def load_jsonl(p):
    return [json.loads(x) for x in p.read_text(encoding='utf-8').splitlines() if x.strip()]

def gt_index_map(hist):
    inv = {(x['suite'],x['user_task']): x for x in hist['task_inventory']}
    by_task = defaultdict(list)
    for r in hist['decisions']:
        by_task[(r['suite'],r['user_task'])].append(r)
    out = {}
    for tk, rows in by_task.items():
        gt = inv[tk].get('ground_truth_all') or []
        cursor = -1
        for r in sorted(rows, key=lambda z: z['privileged_call_index']):
            hits=[]
            for i,c in enumerate(gt):
                if i <= cursor: continue
                if c.get('function') == r['privileged_fn'] and (c.get('args') or {}) == (r.get('gt_args') or {}):
                    hits.append(i)
            require(hits, f'cannot locate historical GT row in full GT order: {r["decision_id"]}')
            i=hits[0]; out[r['decision_id']]=i; cursor=i
    require(len(out)==len(hist['decisions']), 'not all historical decisions received a GT-order index')
    return out

def build_amended_taxonomy():
    hist = read(HIST_TAX)
    rfreeze = read(C0_RUNNER_FREEZE)
    ext = rfreeze.get('extension_decisions') or []
    require({x['extension_decision_id'] for x in ext} == EXPECTED_EXT_IDS, 'C0 extension decision set mismatch')
    require({x['function'] for x in ext} == ADDED_FUNCTIONS, 'C0 added-function set mismatch')
    # Cross-check final corrected structural ledger without consuming its outcome fields.
    combined = load_jsonl(C0_COMBINED)
    require(len(combined)==73, f'corrected combined ledger must contain 73 rows, got {len(combined)}')
    require(len({(r['suite'],r['user_task']) for r in combined})==55, 'corrected combined ledger must contain 55 tasks')
    require(Counter(r['label'] for r in combined)==Counter(EXPECTED_LABELS), 'corrected combined label counts mismatch')
    require(EXPECTED_EXT_IDS <= {r['decision_id'] for r in combined}, 'corrected combined ledger missing extension IDs')

    fullidx = gt_index_map(hist)
    rows = copy.deepcopy(hist['decisions'])
    for r in rows:
        r['historical_privileged_call_index'] = r['privileged_call_index']
        r['ground_truth_call_index'] = fullidx[r['decision_id']]
        r['c0_extension'] = False

    for x in ext:
        rows.append({
            'suite': x['suite'],
            'user_task': x['user_task'],
            'privileged_call_index': None,  # assigned below from corrected full-GT order
            'historical_privileged_call_index': None,
            'ground_truth_call_index': x['ground_truth_call_index'],
            'privileged_fn': x['function'],
            'gt_args': copy.deepcopy(x['gt_args']),
            'decision_id': x['extension_decision_id'],
            'prompt': x['prompt'],
            'prompt_sha256': x['prompt_sha256'],
            'n_priv_calls_in_gt': None,
            'args_matched': x['args_matched'],
            'args_matchable': x['args_matchable'],
            'chars_matched': x['chars_matched'],
            'chars_total': x['chars_total'],
            'specified_fraction': x['specified_fraction'],
            'per_arg': copy.deepcopy(x['per_arg']),
            'label': x['label'],
            'development': False,
            'primary_eligible_label': x['label'] in {'SPECIFIED','DELEGATED'},
            'operationalization': 'mechanical prompt-coverage label; C0 population overlay; not semantic ground truth',
            'c0_extension': True,
            'c0_execution_mode': x['execution_mode'],
        })

    # Assign a corrected privileged-order index per task solely for the fresh B1 mapping order.
    by_task=defaultdict(list)
    for r in rows: by_task[(r['suite'],r['user_task'])].append(r)
    for tk, rr in by_task.items():
        ordered=sorted(rr, key=lambda z:(z['ground_truth_call_index'], z['decision_id']))
        for i,r in enumerate(ordered): r['privileged_call_index']=i
        for r in rr: r['n_priv_calls_in_gt']=len(ordered)

    # Keep a deterministic order.
    suite_order={s:i for i,s in enumerate(['workspace','slack','travel','banking'])}
    rows.sort(key=lambda r:(suite_order[r['suite']],r['user_task'],r['ground_truth_call_index'],r['decision_id']))
    amended=copy.deepcopy(hist)
    amended['decisions']=rows
    amended['b1_c0_population_amendment']={
        'type':'PRE_OUTCOME_POPULATION_ONLY',
        'historical_b1_protocol_hash':OLD_PROTOCOL_HASH,
        'historical_taxonomy_sha256':sha(HIST_TAX),
        'c0_prefreeze_sha256':sha(C0_PREFREEZE),
        'c0_runner_freeze_sha256':sha(C0_RUNNER_FREEZE),
        'corrected_73_ledger_sha256':sha(C0_COMBINED),
        'added_functions':sorted(ADDED_FUNCTIONS),
        'extension_decision_ids':sorted(EXPECTED_EXT_IDS),
        'historical_decision_ids_renumbered':False,
        'note':'privileged_call_index in this derived B1 taxonomy is corrected full privileged-action order; historical index retained separately.',
    }
    amended['taxonomy_hash']=hashlib.sha256(stable({k:v for k,v in amended.items() if k!='taxonomy_hash'}).encode()).hexdigest()
    return amended

def build_manifest(tax):
    by=defaultdict(list)
    for r in tax['decisions']:
        if r['development'] or r['label'] not in ALLOWED: continue
        by[(r['suite'],r['user_task'])].append(r)
    tasks=[]
    for (s,t),rr in sorted(by.items()):
        tasks.append({'suite':s,'user_task':t,'task_key':f'{s}/{t}',
                      'labels_present':sorted({r['label'] for r in rr}),
                      'decision_ids':[r['decision_id'] for r in sorted(rr,key=lambda z:z['privileged_call_index'])]})
    counts=Counter(t['suite'] for t in tasks)
    require(len(tasks)==55, f'amended B1 task count must be 55, got {len(tasks)}')
    require(dict(counts)==EXPECTED_SUITE_TASKS, f'amended suite task counts mismatch: {dict(counts)}')
    rows=[r for r in tax['decisions'] if not r['development'] and r['label'] in ALLOWED]
    require(len(rows)==73, f'amended classifiable decision count must be 73, got {len(rows)}')
    require(Counter(r['label'] for r in rows)==Counter(EXPECTED_LABELS), 'amended taxonomy label counts mismatch')
    require(len({r['decision_id'] for r in rows})==73, 'duplicate amended decision IDs')
    return {'source':'C0-corrected A13 finite census, pre-outcome B1 population amendment',
            'n_tasks':55,'n_decisions':73,'suite_counts':EXPECTED_SUITE_TASKS,'label_counts':EXPECTED_LABELS,'tasks':tasks}

def main():
    verify_inputs()
    needed=[PKG/'B1_C0_00_amend_freeze.py',PKG/'B1_C0_01_run.py',PKG/'B1_C0_02_analyze.py',PKG/'B1_C0_PROTOCOL_SPEC.md']
    for p in needed: require(p.exists(), f'missing amendment package source {p.name}')
    tax=build_amended_taxonomy(); manifest=build_manifest(tax)
    oldp=read(OLD/'protocol.json')
    protocol=copy.deepcopy(oldp)
    protocol['schema']='B1_A12_BACKBONE_PROSPECTIVE_REPLICATION_C0_AMENDED_V2'
    protocol['scientific_status']='pre-outcome population-only amendment after A13-C0 closure; no B1 benchmark outcome observed'
    protocol['task_population']={
        'source':'C0-corrected A13 finite census; historical B1 52-task freeze retained as immutable provenance',
        'historical_b1_protocol_hash':OLD_PROTOCOL_HASH,
        'historical_n_tasks':52,
        'n_tasks':55,
        'n_decisions':73,
        'suite_counts':EXPECTED_SUITE_TASKS,
        'run_partial_tasks':True,
        'development_tasks':oldp['task_population']['development_tasks'],
        'no_model_specific_task_selection':True,
    }
    protocol['population_amendment']={
        'scope':'POPULATION_ONLY',
        'models_changed':False,'agent_temperature_changed':False,'scorer_changed':False,
        'mapping_semantics_changed':False,'span_eligibility_changed':False,'ablation_changed':False,
        'primary_endpoint_changed':False,'secondary_endpoint_changed':False,'inference_changed':False,
        'joint_interpretation_changed':False,
        'historical_protocol_hash':OLD_PROTOCOL_HASH,
        'historical_taxonomy_sha256':sha(HIST_TAX),
        'c0_prefreeze_sha256':sha(C0_PREFREEZE),
        'c0_runner_freeze_sha256':sha(C0_RUNNER_FREEZE),
        'corrected_73_ledger_sha256':sha(C0_COMBINED),
        'extension_decision_ids':sorted(EXPECTED_EXT_IDS),
        'added_privileged_functions':sorted(ADDED_FUNCTIONS),
        'amended_taxonomy_sha256':None,
        'reason':'C0 found a pre-outcome taxonomy coverage defect; B1 had no outcomes, so corrected 55-task/73-decision population supersedes only B1 population.',
    }
    # Write taxonomy first so its file hash can be bound into the protocol.
    OUT.mkdir(parents=True,exist_ok=True)
    tmp_tax=OUT/'taxonomy.json'; dump(tmp_tax,tax)
    protocol['population_amendment']['amended_taxonomy_sha256']=sha(tmp_tax)
    source_hashes={str(p.relative_to(ROOT)):sha(p) for p in needed + [ROOT/'A13_R3_Gemini.py',ROOT/'start_A13_R1_Llama_vLLM.sh']}
    protocol['source_hashes']=source_hashes
    core={k:v for k,v in protocol.items() if k!='protocol_hash'}
    protocol['protocol_hash']=hashlib.sha256(stable(core).encode()).hexdigest()

    # Immutable verification on rerun.
    if (OUT/'FREEZE_COMPLETE.json').exists() and (OUT/'protocol.json').exists():
        old=read(OUT/'protocol.json'); cert=read(OUT/'FREEZE_COMPLETE.json')
        require(old.get('protocol_hash')==protocol['protocol_hash']==cert.get('protocol_hash'), 'amended B1 freeze drift; preserve existing v2 directory')
        for rel,h in cert.get('files',{}).items(): require(sha(ROOT/rel)==h, f'amended frozen artifact drift: {rel}')
        print('[B1-C0-00] existing immutable amendment freeze verified')
        print('[B1-C0-00] protocol_hash='+protocol['protocol_hash'])
        return

    dump(OUT/'protocol.json',protocol)
    dump(OUT/'task_manifest.json',manifest)
    # taxonomy already written
    # Preserve model lineage as exact copy of historical B1 lineage.
    dump(OUT/'model_lineage.json',read(OLD/'model_lineage.json'))
    dump(OUT/'source_hashes.json',source_hashes)
    files=[OUT/'protocol.json',OUT/'task_manifest.json',OUT/'taxonomy.json',OUT/'model_lineage.json',OUT/'source_hashes.json']
    cert={'status':'B1_C0_AMENDED_FROZEN_NO_BENCHMARK_OUTCOMES','frozen_at_utc':now(),
          'protocol_hash':protocol['protocol_hash'],'historical_b1_protocol_hash':OLD_PROTOCOL_HASH,
          'n_tasks':55,'n_decisions':73,'files':{str(p.relative_to(ROOT)):sha(p) for p in files}}
    dump(OUT/'FREEZE_COMPLETE.json',cert)
    print('[B1-C0-00] FREEZE PASS')
    print('[B1-C0-00] protocol_hash='+protocol['protocol_hash'])
    print(f"[B1-C0-00] population=55 tasks / 73 decisions suites={EXPECTED_SUITE_TASKS} labels={EXPECTED_LABELS}")
    print('[B1-C0-00] models/endpoints/H/M/bootstrap unchanged; NO GPT-4o / Claude benchmark outcomes generated')

if __name__=='__main__': main()
