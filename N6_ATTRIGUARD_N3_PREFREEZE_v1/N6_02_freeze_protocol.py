#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, hashlib, datetime
from pathlib import Path
from n6_common import stable_hash, sha256_file, locate_inputs, load_n3

ap=argparse.ArgumentParser()
ap.add_argument("--project-root",default=".")
args=ap.parse_args()
project=Path(args.project_root).resolve()
out=project/"N6_ATTRIGUARD_N3_PREFREEZE_v1_out"
dp=out/"N6_DESIGN_DRAFT.json"; apath=out/"N6_ATTRIGUARD_SCOPE_AUDIT.jsonl"
if not dp.is_file() or not apath.is_file(): raise SystemExit("FATAL: run 00 and 01 first")
design=json.loads(dp.read_text())
# verify the draft itself was not edited after build
h=design.pop("design_hash")
if stable_hash(design)!=h: raise SystemExit("FATAL: design draft changed after build")
design["design_hash"]=h
rows=[json.loads(x) for x in apath.read_text().splitlines() if x.strip()]
if len(rows)!=24: raise SystemExit("FATAL: scope audit row count != 24")
if any(r.get("attriguard_scope_decision")!="PASS" for r in rows):
    raise SystemExit("FATAL: freeze requires 24/24 AttriGuard-scope PASS")
# re-verify immutable scientific inputs now
n3,z,core,pipe,prior,checks=locate_inputs(project)
_,_,prior_audit,_,member_shas=load_n3(n3)
if any(r.get("author_decision")!="PASS" for r in prior_audit): raise SystemExit("FATAL: N3 prior audit changed")
if checks!=design["source_checks"]: raise SystemExit("FATAL: source checks changed since design build")
if member_shas!=design["n3_member_sha256"]: raise SystemExit("FATAL: N3 member hashes changed")

freeze={
    "schema":"N6_ATTRIGUARD_N3_PREFREEZE_V1",
    "status":"FROZEN_PRE_OUTCOME_ZERO_MODEL_CALLS",
    "frozen_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "design_hash":design["design_hash"],
    "scope_audit_sha256":sha256_file(apath),
    "source_checks":checks,
    "n3_member_sha256":member_shas,
    "scientific_question":design["scientific_question"],
    "claim_boundary":design["claim_boundary"],
    "population":design["population"],
    "official_configuration":design["official_configuration"],
    "primary_estimand":design["primary_estimand"],
    "absolute_operating_points":design["absolute_operating_points"],
    "secondary_mechanism":design["secondary_mechanism"],
    "interpretation_law":design["interpretation_law"],
    "hard_stops":design["hard_stops"],
    "schedule":design["schedule"],
    "unit_hashes":{u["unit_id"]:stable_hash(u) for u in design["units"]},
    "inference":{"bootstrap":"paired whole-base nonparametric","B":20000,"seed":20260813,"unit":"base instance","n_bases":24},
    "failure_policy":{"condition_attempts":2,"retry_only_on_exception":True,"retry_delay_seconds":30,"verdict_never_triggers_retry":True,"successful_pair_never_rerun":True,"complete_analysis_requires":"240/240 paired runs"},
    "prohibitions":[
        "No native-proposal/end-to-end AttriGuard claim from this controlled candidate study.",
        "No threshold/lambda tuning after outcomes.",
        "No dropping bases based on verdicts or judge reasons.",
        "No new combined scalar across CausalArmor and AttriGuard.",
        "No claim of generic superiority of AttriGuard or all evidence-preserving causal defenses."
    ]
}
freeze["protocol_hash"]=stable_hash(freeze)
fp=out/"N6_SCIENTIFIC_PREFREEZE.json"
fp.write_text(json.dumps(freeze,indent=2,sort_keys=True)+"\n")
md=f"""# N6 AttriGuard × N3 matched authorization-discrimination prefreeze\n\n**Status:** FROZEN PRE-OUTCOME / ZERO MODEL CALLS  \n**Protocol hash:** `{freeze['protocol_hash']}`\n\nThe primary object is a **source-locked controlled gate-level construct-validity diagnostic**, not a native-proposal or end-to-end defense evaluation. Each frozen N3 CONFLICT context presents the exact same external observation to a paired AUTH/ALT candidate set inside one official AttriGuard invocation. AUTH and ALT use the same function and differ only at the already-audited protected execution argument.\n\nPopulation: 24 bases × 2 descendants × 5 repeats = 240 paired runs = 480 candidate verdicts.\n\nPrimary per-repeat contrast: `block(ALT) - block(AUTH)`. Primary per-base `G_b` averages the ten paired repeats across SHAM/ECHO. Report mean/median/sign counts and paired 20,000-resample whole-base bootstrap CI. Also report absolute AUTH and ALT block rates and route decomposition.\n\n**Do not run scientific calls until this freeze is independently audited.**\n"""
(out/"N6_SCIENTIFIC_PREFREEZE.md").write_text(md)
print("[N6-02] PREFREEZE PASS / ZERO MODEL CALLS")
print("[N6-02] 24/24 AttriGuard-scope author audit PASS")
print(f"[N6-02] protocol_hash={freeze['protocol_hash']}")
print("[N6-02] STOP HERE. Do not run scientific calls. Upload the prefreeze output for audit.")
