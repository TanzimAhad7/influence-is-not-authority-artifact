#!/usr/bin/env python3
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument('--result-dir',required=True)
ap.add_argument('--out',required=True)
a=ap.parse_args()
root=Path(a.result_dir)
rows=[]
for p in root.rglob('*.json'):
    try:d=json.loads(p.read_text())
    except Exception:continue
    if d.get('attack_type')=='tool_knowledge' and d.get('injection_task_id') is not None:
        rows.append((p,d))
if len(rows)!=200: raise SystemExit(f'expected 200 tool_knowledge attack rows, got {len(rows)}')
keys=[(d['suite_name'],d['user_task_id'],d['injection_task_id']) for _,d in rows]
if len(set(keys))!=200: raise SystemExit('duplicate AgentWatcher ON pair keys')
obj={
 'schema':'REPRO_AGENTWATCHER_ON_200_SUMMARY_V1',
 'n':200,
 'utility_true':sum(bool(d.get('utility')) for _,d in rows),
 'utility_rate':sum(bool(d.get('utility')) for _,d in rows)/200,
 'attack_success_true':sum(bool(d.get('security')) for _,d in rows),
 'attack_success_rate':sum(bool(d.get('security')) for _,d in rows)/200,
 'note':'Uses the same AgentDojo output fields consumed by the frozen P2 comparison: utility and security (attack-success endpoint in this attack population).'
}
Path(a.out).parent.mkdir(parents=True,exist_ok=True)
Path(a.out).write_text(json.dumps(obj,indent=2)+'\n')
print(json.dumps(obj,indent=2))
