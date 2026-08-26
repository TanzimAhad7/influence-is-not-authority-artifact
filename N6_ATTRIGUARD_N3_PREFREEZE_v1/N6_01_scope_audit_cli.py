#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, datetime
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument("--project-root",default=".")
args=ap.parse_args()
root=Path(args.project_root).resolve()/"N6_ATTRIGUARD_N3_PREFREEZE_v1_out"
p=root/"N6_ATTRIGUARD_SCOPE_AUDIT.jsonl"
if not p.is_file(): raise SystemExit("FATAL: run N6_00_build_design.py first")
rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
for i,r in enumerate(rows):
    if r.get("attriguard_scope_decision") in {"PASS","FAIL"}: continue
    print("\n"+"="*90)
    print(f"N6 AttriGuard threat-model scope audit {i+1}/24: {r['base_id']} [{r['family']}]")
    print("USER TASK:\n",r["user_task"])
    print("\nFROZEN CONFLICT EXTERNAL OBSERVATION:\n",r["conflict_external_observation"])
    print("\nAUTH:\n",json.dumps(r["AUTH"],indent=2))
    print("\nALT:\n",json.dumps(r["ALT"],indent=2))
    print("\nCHECKLIST:")
    for j,c in enumerate(r["checklist"],1): print(f" {j}. {c}")
    ans=input("\nAuthor decision [PASS/FAIL/QUIT]: ").strip().upper()
    if ans=="QUIT": break
    if ans not in {"PASS","FAIL"}:
        print("Invalid; try again."); continue
    notes=input("Author notes (optional): ").strip()
    r["attriguard_scope_decision"]=ans
    r["author_notes"]=notes
    r["audited_at_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    r["auditor_role"]="author"
    with p.open("w") as f:
        for x in rows: f.write(json.dumps(x,sort_keys=True)+"\n")

passed=sum(r.get("attriguard_scope_decision")=="PASS" for r in rows)
failed=sum(r.get("attriguard_scope_decision")=="FAIL" for r in rows)
pending=24-passed-failed
print(f"\n[N6-01] PASS={passed} FAIL={failed} PENDING={pending}")
if failed:
    print("[N6-01] HARD STOP: at least one base is out-of-scope; do not freeze or run science.")
elif pending==0:
    print("[N6-01] HUMAN SCOPE AUDIT COMPLETE: 24/24 PASS")
else:
    print("[N6-01] Resume this same command to continue.")
