#!/usr/bin/env python3
"""
A15a-02 — analyze frozen A15a sanitizer consequence.
No model/API calls.
"""
from __future__ import annotations
import json, math, re, statistics, sys
from collections import Counter, defaultdict
from pathlib import Path
from a15a_common import *

PROTOCOL_PATH = OUT_DIR / "protocol.json"
INVENTORY_PATH = OUT_DIR / "decision_inventory.jsonl"
JOBS_PATH = OUT_DIR / "sanitizer_jobs.jsonl"
RESULTS_PATH = OUT_DIR / "sanitizer_results.jsonl"
SUMMARY_PATH = OUT_DIR / "results.json"
REPORT_PATH = OUT_DIR / "REPORT.md"

NUM_RE = re.compile(r"\b(?:\d[\d,.:/-]*\d|\d)\b")
WORD_RE = re.compile(r"[A-Za-z0-9_@.+-]{3,}")

def pct(a,b):
    return a/b if b else None

def quantile(xs, q):
    if not xs: return None
    ys=sorted(xs)
    if len(ys)==1: return ys[0]
    pos=(len(ys)-1)*q
    lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return ys[lo]
    return ys[lo]+(ys[hi]-ys[lo])*(pos-lo)

def preservation(original, sanitized):
    nums = set(NUM_RE.findall(original))
    nums2 = set(NUM_RE.findall(sanitized))
    words = {x.lower() for x in WORD_RE.findall(original)}
    words2 = {x.lower() for x in WORD_RE.findall(sanitized)}
    return {
        "numeric_token_recall": len(nums & nums2)/len(nums) if nums else None,
        "lexical_token_recall": len(words & words2)/len(words) if words else None,
        "original_chars": len(original),
        "sanitized_chars": len(sanitized),
        "char_ratio": len(sanitized)/len(original) if original else None,
    }

def main():
    for p in [PROTOCOL_PATH, INVENTORY_PATH, JOBS_PATH, RESULTS_PATH]:
        if not p.exists():
            sys.exit(f"FATAL missing {p}")

    protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
    inv = read_jsonl(INVENTORY_PATH)
    jobs = {r["job_id"]: r for r in read_jsonl(JOBS_PATH)}
    san = read_jsonl(RESULTS_PATH)

    if protocol["sanitizer"]["job_list_sha256"] != sha256_file(JOBS_PATH):
        sys.exit("FATAL frozen job hash mismatch.")
    if len(san) != len(jobs) or any(r.get("error") for r in san):
        sys.exit("FATAL sanitizer results incomplete.")

    eligible_n = len(inv)
    activated = [r for r in inv if r["ca_flag_tau0"]]
    all_span_n = sum(r["n_eligible_tool_spans"] for r in inv)
    flagged_span_n = sum(r["n_flagged_spans_tau0"] for r in inv)

    by_label = {}
    for label in sorted({r["label"] for r in inv}):
        rows=[r for r in inv if r["label"]==label]
        act=[r for r in rows if r["ca_flag_tau0"]]
        by_label[label]={
            "n_decisions": len(rows),
            "n_activated": len(act),
            "activation_rate": pct(len(act), len(rows)),
            "eligible_spans": sum(r["n_eligible_tool_spans"] for r in rows),
            "flagged_spans": sum(r["n_flagged_spans_tau0"] for r in rows),
        }

    lats=[float(r["latency_seconds"]) for r in san]
    by_dec=defaultdict(list)
    pres=[]
    for r in san:
        j=jobs[r["job_id"]]
        by_dec[r["decision_id"]].append(float(r["latency_seconds"]))
        p=preservation(j["untrusted_content"], r["sanitized_text"])
        p.update({"job_id":r["job_id"],"decision_id":r["decision_id"],"label":r["label"]})
        pres.append(p)

    serial_per_activated=[sum(v) for v in by_dec.values()]
    parallel_lb_per_activated=[max(v) for v in by_dec.values()]

    def nonnull(key):
        return [x[key] for x in pres if x[key] is not None]

    summary={
        "protocol_hash":protocol["protocol_hash"],
        "scientific_status":protocol["scientific_status"],
        "eligible_decisions":eligible_n,
        "activated_decisions_tau0":len(activated),
        "decision_activation_rate_tau0":pct(len(activated),eligible_n),
        "eligible_tool_spans":all_span_n,
        "flagged_tool_spans_tau0":flagged_span_n,
        "flagged_span_fraction_tau0":pct(flagged_span_n,all_span_n),
        "sanitizer_calls":len(san),
        "sanitizer_calls_per_eligible_decision":pct(len(san),eligible_n),
        "sanitizer_calls_per_activated_decision":pct(len(san),len(activated)),
        "by_label":by_label,
        "sanitizer_latency_seconds":{
            "mean":statistics.mean(lats) if lats else None,
            "median":statistics.median(lats) if lats else None,
            "p95":quantile(lats,.95),
            "total":sum(lats),
        },
        "per_activated_decision_serial_sanitizer_seconds":{
            "mean":statistics.mean(serial_per_activated) if serial_per_activated else None,
            "median":statistics.median(serial_per_activated) if serial_per_activated else None,
            "p95":quantile(serial_per_activated,.95),
        },
        "per_activated_decision_parallel_lower_bound_seconds":{
            "mean":statistics.mean(parallel_lb_per_activated) if parallel_lb_per_activated else None,
            "median":statistics.median(parallel_lb_per_activated) if parallel_lb_per_activated else None,
            "p95":quantile(parallel_lb_per_activated,.95),
        },
        "preservation_diagnostics":{
            "numeric_token_recall_mean":statistics.mean(nonnull("numeric_token_recall")) if nonnull("numeric_token_recall") else None,
            "lexical_token_recall_mean":statistics.mean(nonnull("lexical_token_recall")) if nonnull("lexical_token_recall") else None,
            "char_ratio_mean":statistics.mean(nonnull("char_ratio")) if nonnull("char_ratio") else None,
        },
        "interpretation": {
            "primary": (
                "Measures how often the expensive sanitizer stage is activated on already-successful benign "
                "A13 privileged decisions and the added sanitizer-call cost in this deployment."
            ),
            "lower_bound_note": (
                "Measured sanitizer time excludes proxy-attribution time, retroactive CoT masking, agent "
                "regeneration, and environment execution; it is therefore a lower bound on full defense-path overhead."
            ),
            "provider_note": (
                "Gemini-2.5-Flash model identifier matches the paper sanitizer, but this run uses OpenRouter "
                "rather than the paper's Vertex AI route; absolute wall-clock latency is deployment-specific."
            ),
        }
    }
    dump_json(SUMMARY_PATH,summary)

    lines=[
        "# A15a — Benign Selectivity / Sanitizer Consequence",
        "",
        f"Protocol: `{protocol['protocol_hash']}`",
        "",
        f"- Eligible successful benign decisions: **{eligible_n}**",
        f"- Activated at tau=0: **{len(activated)}/{eligible_n} = {summary['decision_activation_rate_tau0']:.3f}**",
        f"- Flagged tool spans: **{flagged_span_n}/{all_span_n} = {summary['flagged_span_fraction_tau0']:.3f}**",
        f"- Sanitizer calls: **{len(san)}**",
        f"- Calls per eligible decision: **{summary['sanitizer_calls_per_eligible_decision']:.3f}**",
        f"- Calls per activated decision: **{summary['sanitizer_calls_per_activated_decision']:.3f}**",
        "",
        "## Frozen A13 label breakdown",
        "",
    ]
    for k,v in by_label.items():
        lines.append(f"- {k}: {v['n_activated']}/{v['n_decisions']} activated ({v['activation_rate']:.3f})")
    lines += [
        "",
        "## Sanitizer wall-clock (this deployment)",
        "",
        f"- mean per call: {summary['sanitizer_latency_seconds']['mean']:.3f} s",
        f"- median per call: {summary['sanitizer_latency_seconds']['median']:.3f} s",
        f"- p95 per call: {summary['sanitizer_latency_seconds']['p95']:.3f} s",
        f"- mean serial sanitizer time per activated decision: {summary['per_activated_decision_serial_sanitizer_seconds']['mean']:.3f} s",
        "",
        "This excludes attribution time, CoT masking, agent regeneration, and execution, so it is a lower bound",
        "on the full defense path. Absolute latency is deployment-specific because Gemini-2.5-Flash is accessed",
        "through OpenRouter here rather than the paper's Vertex AI route.",
        "",
        "## Preservation diagnostics (descriptive only)",
        "",
        f"- numeric token recall mean: {summary['preservation_diagnostics']['numeric_token_recall_mean']}",
        f"- lexical token recall mean: {summary['preservation_diagnostics']['lexical_token_recall_mean']}",
        f"- sanitized/original char ratio mean: {summary['preservation_diagnostics']['char_ratio_mean']}",
        "",
        "Do not interpret lexical preservation as task utility. Full end-to-end utility/regeneration belongs in A15b or a dedicated follow-up.",
    ]
    REPORT_PATH.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("[A15a-02] COMPLETE")
    print(f"[A15a-02] Results: {SUMMARY_PATH}")
    print(f"[A15a-02] Report:  {REPORT_PATH}")

if __name__=="__main__":
    main()
