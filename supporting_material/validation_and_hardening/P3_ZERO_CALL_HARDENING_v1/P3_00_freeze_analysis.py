#!/usr/bin/env python3
import argparse, hashlib, json, os, sys
from pathlib import Path
from datetime import datetime, timezone


def sha256(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def wc_jsonl(path: Path):
    with path.open('rb') as f:
        return sum(1 for line in f if line.strip())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root', required=True)
    ap.add_argument('--package-dir', default=str(Path(__file__).resolve().parent))
    ap.add_argument('--out-dir', required=True)
    args=ap.parse_args()
    root=Path(args.project_root).resolve(); pkg=Path(args.package_dir).resolve(); out=Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    paths={
      'config': pkg/'P3_CONFIG.json',
      'analysis_script': pkg/'P3_01_run_hardening.py',
      'a13_decisions': root/'a13/decisions.jsonl',
      'a13_results': root/'a13/results.json',
      'a15a_inventory': root/'a15a_selectivity_consequence/decision_inventory.jsonl',
      'a15a_results': root/'a15a_selectivity_consequence/results.json',
      'taxonomy': root/'P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/P2B_ARGUMENT_ROLE_TAXONOMY.json',
      'replay_inventory': root/'P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/inputs/P2B_REPLAY_INVENTORY.jsonl',
      'llama_raw': root/'P2B_XM_CI_LLAMA_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl',
      'gemma_raw': root/'P2B_XM_CI_GEMMA_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl',
      'qwen_raw': root/'P2B_XM_CI_QWEN_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl',
      'llama_slots': root/'P2B_XM_CI_LLAMA_RUN_v1_2/P2B_CI_ARGUMENT_SLOT_ROWS.csv',
      'gemma_slots': root/'P2B_XM_CI_GEMMA_RUN_v1_2/P2B_CI_ARGUMENT_SLOT_ROWS.csv',
      'qwen_slots': root/'P2B_XM_CI_QWEN_RUN_v1_2/P2B_CI_ARGUMENT_SLOT_ROWS.csv'
    }
    missing=[str(p) for p in paths.values() if not p.exists()]
    if missing:
        print('FREEZE FAIL: missing required files:', file=sys.stderr)
        for m in missing: print('  '+m, file=sys.stderr)
        sys.exit(2)

    cfg=json.load(open(paths['config']))
    rows={k:wc_jsonl(p) for k,p in paths.items() if p.suffix=='.jsonl'}
    expected={'llama_raw':130,'gemma_raw':130,'qwen_raw':130,'replay_inventory':26,'a15a_inventory':26}
    problems=[]
    for k,n in expected.items():
        if rows.get(k)!=n: problems.append(f'{k}: expected {n} rows, got {rows.get(k)}')
    if problems:
        print('FREEZE FAIL: row-count mismatch', file=sys.stderr)
        for x in problems: print('  '+x,file=sys.stderr)
        sys.exit(3)

    freeze={
      'schema':'P3_ZERO_CALL_ANALYSIS_FREEZE_V1',
      'created_utc':datetime.now(timezone.utc).isoformat(),
      'status':'POSTHOC_FALSIFICATION_AND_SENSITIVITY_ANALYSIS_FROZEN_FOR_EXECUTION',
      'scientific_model_calls':0,
      'project_root':str(root),
      'package_dir':str(pkg),
      'out_dir':str(out),
      'config':cfg,
      'input_files':{},
      'row_counts':rows
    }
    for k,p in paths.items():
        freeze['input_files'][k]={'path':str(p),'sha256':sha256(p),'bytes':p.stat().st_size}
    fp=out/'P3_ANALYSIS_FREEZE.json'
    fp.write_text(json.dumps(freeze,indent=2,sort_keys=True)+'\n')
    freeze_sha=sha256(fp)
    md=[
      '# P3 zero-call analysis freeze', '',
      '**Status:** PASS', '',
      f'Freeze SHA-256: `{freeze_sha}`', '',
      'This freeze records a **post-hoc falsification/sensitivity analysis** of already-observed data. It is not a prospective confirmatory endpoint.', '',
      '- scientific model calls: **0**',
      f'- A13 decisions rows: **{rows["a13_decisions"]}**',
      f'- A15a inventory rows: **{rows["a15a_inventory"]}**',
      f'- corrected P2b raw rows: **{rows["llama_raw"]+rows["gemma_raw"]+rows["qwen_raw"]}**',
      '- corrected P2b decision inventory: **26**',
      '', '## Claim boundaries'
    ]
    md += [f'- {x}' for x in cfg['claim_boundaries']]
    md += ['', '## Frozen inputs']
    for k,d in freeze['input_files'].items(): md.append(f'- `{k}`: `{d["sha256"]}` — `{d["path"]}`')
    (out/'P3_ANALYSIS_FREEZE.md').write_text('\n'.join(md)+'\n')
    print('P3 ANALYSIS FREEZE PASS')
    print('freeze_file:',fp)
    print('freeze_sha256:',freeze_sha)

if __name__=='__main__': main()
