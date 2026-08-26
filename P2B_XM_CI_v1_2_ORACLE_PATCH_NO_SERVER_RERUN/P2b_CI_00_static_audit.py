#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path

from common_action_interface import ACTION_VALIDATOR, assistant_action_envelope, blocks_to_text, canonicalize_history, stable_json
from stress_runtime import SyntheticRuntime
from action_local import _normalize_known_nondeterminism

HERE=Path(__file__).resolve().parent
EXPECTED={
 'inputs/P2B_REPLAY_INVENTORY.jsonl':'9fc33a564480335aac2a91a87794a7aea737315ebd3d1c2b9facd07cd7afdded',
 'inputs/P2B_REPLAY_CONTEXTS.jsonl':'1bbf011ec0affe6a5d332c61b6dda6d2820c549fe7cbc83439af38bf83b297ec',
 'inputs/P2B_PREFLIGHT_SUMMARY.json':'fdac39d70a952eb28a424bc0538938b549f442225d7b61b90f6d3728c2d2f053',
 'P2B_ARGUMENT_ROLE_TAXONOMY.json':'66a1705d422a0a8e0b7630f099c806df646f9354f996648d659dbb4a2f519b90',
}

def sha(p):
 h=hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()

def readjl(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x.strip()]

def main():
 checks=[]
 for rel,exp in EXPECTED.items():
  got=sha(HERE/rel); checks.append({'check':f'hash:{rel}','pass':got==exp,'expected':exp,'got':got})
 inv=readjl(HERE/'inputs/P2B_REPLAY_INVENTORY.jsonl')
 checks.append({'check':'population_26','pass':len(inv)==26,'got':len(inv)})
 checks.append({'check':'activated_18','pass':sum(bool(x['activated_tau0']) for x in inv)==18,'got':sum(bool(x['activated_tau0']) for x in inv)})
 tax=json.loads((HERE/'P2B_ARGUMENT_ROLE_TAXONOMY.json').read_text())
 for r in inv:
  did=r['decision_id']; target=set((r['target_action'].get('args') or {}).keys()); mapped=set((tax.get('per_decision',{}).get(did) or {}).keys())
  checks.append({'check':f'taxonomy:{did}','pass':target==mapped,'target':sorted(target),'mapped':sorted(mapped)})
 reg=json.loads((HERE/'MODEL_REGISTRY_CI.json').read_text())
 lock=json.loads((HERE/'P2B_XM_CI_REVISION_LOCK.json').read_text())
 for k,cfg in reg['models'].items():
  lc=lock['models'][k]
  checks.append({'check':f'revision_lock:{k}','pass':all(cfg[x]==lc[x] for x in ('model_id','revision','tokenizer_revision'))})
 stress=json.loads((HERE/'inputs/EXCLUDED_STRESS_CONTEXTS.json').read_text())
 science_ids={x['decision_id'] for x in inv}
 stress_blob=(HERE/'inputs/EXCLUDED_STRESS_CONTEXTS.json').read_text()
 overlap=[did for did in science_ids if did in stress_blob]
 checks.append({'check':'stress_has_no_scientific_decision_ids','pass':not overlap,'overlap':overlap})
 # Regression-test the action-local effect canonicalizer without touching scientific cases.
 email_a={'sender':'a@example.com','recipients':['b@example.com'],'subject':'s','body':'b','status':'sent','timestamp':'2026-01-01T00:00:00','id_':'1'}
 email_b=dict(email_a); email_b['timestamp']='2026-01-01T00:00:01'
 email_c=dict(email_a); email_c['body']='DIFFERENT'
 norm_a=_normalize_known_nondeterminism(email_a)
 norm_b=_normalize_known_nondeterminism(email_b)
 norm_c=_normalize_known_nondeterminism(email_c)
 checks.append({'check':'effect_oracle_ignores_only_email_timestamp_value','pass':norm_a==norm_b})
 checks.append({'check':'effect_oracle_retains_email_semantic_fields','pass':norm_a!=norm_c})
 # Validate every expected envelope and every historical assistant serialization through the exact adapter.
 for case in stress['cases']:
  errs=[e.message for e in ACTION_VALIDATOR.iter_errors(case['expected'])]
  checks.append({'check':f'stress_expected_schema:{case["case_id"]}','pass':not errs,'errors':errs})
  runtime=SyntheticRuntime(case['tools'])
  rendered=canonicalize_history(case['history'],runtime)
  # Every historical assistant action in the semantic history must become a valid action envelope string.
  assistant_msgs=[m for m in rendered if m['role']=='assistant']
  valid=True; aerrs=[]
  for m in assistant_msgs:
   try: obj=json.loads(m['content'])
   except Exception as e: valid=False; aerrs.append(f'json:{e}'); continue
   es=[e.message for e in ACTION_VALIDATOR.iter_errors(obj)]
   if es: valid=False; aerrs.extend(es)
  checks.append({'check':f'historical_candidate_grammar_identity:{case["case_id"]}','pass':valid,'errors':aerrs,'assistant_actions':len(assistant_msgs)})
  # Lossless-content invariant: if a historical assistant turn has both prose and tool calls,
  # the prose must remain inside the common envelope. This is tested only on excluded synthetic cases.
  preserved=True; perr=[]; tested=0
  for src in case['history']:
   if src.get('role')!='assistant' or not (src.get('tool_calls') or []): continue
   txt=blocks_to_text(src.get('content'))
   if not txt: continue
   tested+=1
   env=assistant_action_envelope(src)
   if env.get('content')!=txt:
    preserved=False; perr.append({'expected':txt,'got':env.get('content')})
  checks.append({'check':f'historical_assistant_text_preserved:{case["case_id"]}','pass':preserved,'tested_turns':tested,'errors':perr})
 passed=all(x['pass'] for x in checks)
 out={'schema':'P2B_XM_CI_STATIC_AUDIT_V1','scientific':False,'pass':passed,'checks':checks}
 (HERE/'P2B_CI_STATIC_AUDIT.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
 print(f'STATIC AUDIT {"PASS" if passed else "FAIL"}: {sum(x["pass"] for x in checks)}/{len(checks)}')
 if not passed:
  for x in checks:
   if not x['pass']: print('FAIL',x)
  raise SystemExit(2)

if __name__=='__main__': main()
