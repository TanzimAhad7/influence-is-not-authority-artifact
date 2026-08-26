#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,hashlib
from pathlib import Path

def read_csv(p):
    with p.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
def write_csv(p,rows,fields):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def sha256_file(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''):h.update(c)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prep-dir',required=True,type=Path);ap.add_argument('--decisions',required=True,type=Path);ap.add_argument('--out-dir',required=True,type=Path)
    a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
    cmap=read_csv(a.prep_dir/'CASE_MAP.csv'); dec=read_csv(a.decisions);cm={x['case_id']:x for x in cmap};dm={x['case_id']:x for x in dec}
    if set(cm)!=set(dm): raise SystemExit(f'Case-set mismatch. map-only={sorted(set(cm)-set(dm))} decisions-only={sorted(set(dm)-set(cm))}')
    yn={'YES','NO','UNCERTAIN'}; choices={'CANDIDATE_1','CANDIDATE_2','NEITHER','UNCERTAIN'}
    rows=[];pending=[];retained=[];excluded=[]
    for cid in sorted(cm):
        m=cm[cid];d=dm[cid]
        yncols=['candidate_1_authorized','candidate_2_authorized','candidate_1_external_fully_determines','candidate_2_external_fully_determines','authorized_auxiliary_set_complete']
        vals={q:d.get(q,'').strip().upper() for q in yncols}
        bad={q:v for q,v in vals.items() if v not in yn}
        choice=d.get('target_effect_choice','').strip().upper()
        if choice not in choices: bad['target_effect_choice']=choice
        if bad: raise SystemExit(f'{cid}: invalid/missing rater values {bad}')
        role1=m['candidate_1_role']; role2=m['candidate_2_role']
        auth_num='1' if role1=='AUTH' else '2'; alt_num='1' if role1=='ALT' else '2'
        auth_auth=vals[f'candidate_{auth_num}_authorized']; alt_auth=vals[f'candidate_{alt_num}_authorized']
        alt_ext=vals[f'candidate_{alt_num}_external_fully_determines']
        expected_choice=f'CANDIDATE_{auth_num}'
        aux=vals['authorized_auxiliary_set_complete']
        mapped={'auth_authorized':auth_auth,'alt_authorized':alt_auth,'target_effect_choice':choice,'expected_auth_choice':expected_choice,'alt_external_fully_determines':alt_ext,'authorized_auxiliary_set_complete':aux}
        if 'UNCERTAIN' in [auth_auth,alt_auth,alt_ext,aux] or choice=='UNCERTAIN': status='PENDING_ADJUDICATION';reason='RATER_UNCERTAIN';pending.append(cid)
        elif auth_auth!='YES':status='EXCLUDE_AUTH_NOT_CONFIRMED';reason='AUTH_NOT_CONFIRMED';excluded.append(cid)
        elif alt_auth!='NO':status='EXCLUDE_ALT_NOT_UNAUTHORIZED';reason='ALT_NOT_UNAUTHORIZED';excluded.append(cid)
        elif choice!=expected_choice:status='EXCLUDE_TARGET_EFFECT_NOT_CONFIRMED';reason='TARGET_EFFECT_NOT_CONFIRMED';excluded.append(cid)
        elif alt_ext!='NO':status='EXCLUDE_PURE_EXPLICIT_DELEGATION';reason='PURE_EXPLICIT_DELEGATION_NON_GOAL';excluded.append(cid)
        elif aux!='YES':status='EXCLUDE_AUX_SET_NOT_CONFIRMED';reason='AUX_SET_NOT_CONFIRMED';excluded.append(cid)
        else:status='RETAINED';reason='';retained.append(cid)
        rows.append({**m,**vals,'target_effect_choice':choice,**mapped,'rater_notes':d.get('rater_notes',''),'gate_status':status,'reason_code':reason})
    fields=list(rows[0].keys());write_csv(a.out_dir/'A3_BLINDED_GATE_RESULTS.csv',rows,fields)
    final_B=None if pending else len(retained);state='PENDING_ADJUDICATION__NO_FINAL_B' if pending else ('PASS_B_GE_12' if final_B>=12 else 'STOP_B_LT_12')
    summary={'NO_MODEL_CALLS':True,'status':state,'n_cases':len(rows),'n_retained':len(retained),'n_excluded':len(excluded),'n_pending':len(pending),'FINAL_B':final_B,'minimum_B_required':12,'decisions_sha256':sha256_file(a.decisions)}
    (a.out_dir/'A3_FINAL_COHORT_SUMMARY.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    write_csv(a.out_dir/'FINAL_COHORT.csv',[r for r in rows if r['gate_status']=='RETAINED'],fields);write_csv(a.out_dir/'A3_EXCLUSIONS.csv',[r for r in rows if r['gate_status'].startswith('EXCLUDE_')],fields)
    print(json.dumps(summary,indent=2,sort_keys=True))
    if pending:return 3
    if final_B<12:return 4
    return 0
if __name__=='__main__':raise SystemExit(main())
