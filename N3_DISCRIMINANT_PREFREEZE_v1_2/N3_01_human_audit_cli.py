#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from datetime import datetime, timezone
from n3_common import *


def component(ctx, component_id):
    return next((m for m in ctx["messages"] if m.get("component_id") == component_id), None)


def directive_only(content: str) -> str:
    marker = " Action directive:"
    if marker not in content:
        return "<MISSING DIRECTIVE>"
    return "Action directive:" + content.split(marker, 1)[1]


def factual_prefix(content: str) -> str:
    marker = " Action directive:"
    return content.split(marker, 1)[0] if marker in content else content


def main():
    ap = argparse.ArgumentParser(description="Author human construct audit for N3 prefreeze")
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--run-dir", default="N3_PREFREEZE_AUTHOR_v1")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    rd = root / args.run_dir
    templ = rd / "N3_HUMAN_AUDIT_TEMPLATE.jsonl"
    out = rd / "N3_HUMAN_AUDIT.jsonl"
    if out.exists():
        raise SystemExit(f"FATAL: audit output exists; refuse overwrite: {out}")

    rows = read_jsonl(templ)
    pos = read_jsonl(rd / "N3_POSITIVE_CONTEXTS.jsonl")
    pos_by = {(r["base_id"], r["descendant"], r["directive_arm"]): r for r in pos}

    base_obj = read_json(root / A14_BASE_REL)
    bases = {b["base_id"]: b for b in base_obj["instances"]}

    audited = []
    print("N3 HUMAN CONSTRUCT AUDIT — 24 BASES")
    print("Type PASS only after checking every listed item. Type FAIL to stop.")
    print("No scientific outcomes are shown or accessed.\n")

    for i, r in enumerate(rows, 1):
        bid = r["base_id"]
        b = bases[bid]
        print("=" * 100)
        print(f"[{i:02d}/24] {bid}  family={r['family']}")
        print(f"protected argument: {r['execution_arg']}")
        print(f"authorized value : {r['authorized_execution_value']}")
        print(f"alternate value  : {r['alternate_execution_value']}  (donor {r['alternate_value_donor_base']})")
        print("AUTHORIZED ACTION:", stable_json(r["authorized_action"]))
        print("ALTERNATE ACTION :", stable_json(r["alternate_action"]))
        print("Oracle expected  :", stable_json(r["authorization_oracle_expected"]))

        print("\nAUTHORIZATION POLICY (existing frozen A14 policy):")
        print(stable_json(b["authorization_policy"]))
        print(f"authorization_policy_sha256={b['authorization_policy_hash']}")

        # The user/system context should be identical across the matched positive-control arms.
        sample = pos_by[(bid, "SHAM", "ALIGNED")]
        u = component(sample["context"], "U")
        print("\nUSER AUTHORIZATION / REQUEST (unchanged across N3 positive-control arms):")
        print(u.get("content", "<MISSING U>") if u else "<MISSING U>")

        for desc in DESCENDANTS:
            a = pos_by[(bid, desc, "ALIGNED")]
            c = pos_by[(bid, desc, "CONFLICT")]
            sa = component(a["context"], "S_REL")
            sc = component(c["context"], "S_REL")
            if sa is None or sc is None:
                raise SystemExit(f"FATAL: missing S_REL for {bid} {desc}")
            fa = factual_prefix(sa["content"])
            fc = factual_prefix(sc["content"])
            if fa != fc:
                raise SystemExit(f"FATAL: factual S_REL prefix differs across arms for {bid} {desc}")
            print(f"\n{desc} — ORIGINAL FACTUAL TOOL EVIDENCE PREFIX (identical across arms):")
            print(fa)
            print(f"{desc} — ALIGNED DIRECTIVE:")
            print(directive_only(sa["content"]))
            print(f"{desc} — CONFLICT DIRECTIVE:")
            print(directive_only(sc["content"]))
            print(f"{desc} — MATCH CHECKS: same factual prefix=YES; same full S_REL char length={len(sa['content']) == len(sc['content'])}")

        print("\nChecklist:")
        for j, x in enumerate(r["human_checklist"], 1):
            print(f"  {j}. {x}")
        ans = input("Decision [PASS/FAIL]: ").strip().upper()
        if ans not in {"PASS", "FAIL"}:
            raise SystemExit("FATAL: decision must be PASS or FAIL")
        notes = input("Optional notes (Enter for none): ").strip()
        rr = dict(r)
        rr["author_decision"] = ans
        rr["author_notes"] = notes
        rr["audited_at_utc"] = datetime.now(timezone.utc).isoformat()
        rr["auditor_role"] = "author"
        rr["audit_display_revision"] = "PREFREEZE_AMENDMENT_01_SHOW_POLICY_AND_DIRECTIVES"
        audited.append(rr)
        if ans == "FAIL":
            dump_jsonl(out, audited)
            raise SystemExit(f"HARD STOP: author marked {bid} FAIL; N3 freeze forbidden")

    dump_jsonl(out, audited)
    print("\nN3 HUMAN AUDIT COMPLETE: 24/24 PASS")
    print(f"audit_sha256={sha256_file(out)}")
    print("NEXT: run N3_02_freeze_protocol.py; DO NOT RUN SCIENCE")


if __name__ == "__main__":
    main()
