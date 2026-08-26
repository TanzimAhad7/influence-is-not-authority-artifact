#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, statistics, sys
from collections import defaultdict
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
ROOT = _THIS_DIR.parent if _THIS_DIR.name == "B1_C0_POPULATION_AMENDMENT_v2" else _THIS_DIR
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import A13_R3_Gemini as core
B1 = ROOT / "b1_a12_backbone_replication_c0_v2"
PROTOCOL = B1 / "protocol.json"
FREEZE = B1 / "FREEZE_COMPLETE.json"
TASK_MANIFEST = B1 / "task_manifest.json"
FROZEN_TAXONOMY = B1 / "taxonomy.json"
SOURCE_HASHES = B1 / "source_hashes.json"

AGENTS = {
    "gpt4o": {
        "model": "openai/gpt-4o",
        "base_url": "https://openrouter.ai/api/v1",
        "pipeline_name": "b1_openrouter_openai_gpt-4o",
        "slug": "gpt4o",
    },
    "claude45": {
        "model": "anthropic/claude-sonnet-4.5",
        "base_url": "https://openrouter.ai/api/v1",
        "pipeline_name": "b1_openrouter_anthropic_claude-sonnet-4.5",
        "slug": "claude45",
    },
}


def sha(p: Path): return hashlib.sha256(p.read_bytes()).hexdigest()
def stable(x): return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
def read(p: Path): return json.loads(p.read_text(encoding="utf-8"))
def dump(p: Path, x):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(core.json_safe(x), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
def dump_jsonl(p: Path, rows):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(core.json_safe(r), ensure_ascii=False) + "\n")


def verify_freeze():
    for p in [PROTOCOL, FREEZE, TASK_MANIFEST, FROZEN_TAXONOMY, SOURCE_HASHES]:
        if not p.exists():
            sys.exit(f"FATAL: B1 is not frozen; missing {p}")
    protocol = read(PROTOCOL)
    cert = read(FREEZE)
    if cert.get("protocol_hash") != protocol.get("protocol_hash"):
        sys.exit("FATAL: B1 freeze/protocol hash mismatch")
    for rel, expected in cert.get("files", {}).items():
        p = ROOT / rel
        if not p.exists() or sha(p) != expected:
            sys.exit(f"FATAL: frozen B1 artifact drift: {rel}")
    source_hashes = read(SOURCE_HASHES)
    # R3 measurement core and this runner are frozen scientific source inputs.
    for rel in ["A13_R3_Gemini.py", "B1_C0_POPULATION_AMENDMENT_v2/B1_C0_01_run.py", "B1_C0_POPULATION_AMENDMENT_v2/B1_C0_02_analyze.py", "B1_C0_POPULATION_AMENDMENT_v2/B1_C0_PROTOCOL_SPEC.md"]:
        expected = source_hashes.get(rel)
        if expected is None:
            sys.exit(f"FATAL: missing frozen source hash for {rel}")
        if sha(ROOT / rel) != expected:
            sys.exit(f"FATAL: source drift after B1 freeze: {rel}")
    return protocol


def configure_core(agent_key: str):
    cfg = AGENTS[agent_key]
    out = B1 / cfg["slug"]
    core.AGENT_MODEL = cfg["model"]
    core.OPENROUTER_BASE_URL = os.environ.get("B1_OPENROUTER_BASE_URL", cfg["base_url"]).rstrip("/")
    core.OPENROUTER_API_KEY_ENV = "OPENROUTER_API_KEY"
    core.AGENT_TEMPERATURE = 0.0
    core.AGENT_PIPELINE_NAME = cfg["pipeline_name"]
    core.SCORER_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
    core.SCORER_BASE_URL = os.environ.get("B1_SCORER_BASE_URL", "http://localhost:8110/v1").rstrip("/")
    core.OUT_DIR = out
    core.RUNS_DIR = out / "agentdojo_runs"
    core.SMOKE_RUNS_DIR = out / "smoke_agentdojo"
    core.LOG_DIR = out / "logs"
    core.PROTOCOL_PATH = out / "protocol_pointer.json"
    core.TAXONOMY_PATH = out / "taxonomy.json"
    core.DECISIONS_PATH = out / "decisions.jsonl"
    core.RESULTS_PATH = out / "results.json"
    core.REPORT_PATH = out / "REPORT.md"
    core.MANIFEST_PATH = out / "manifest.json"
    return cfg, out


def write_run_manifest(agent_key, protocol, out, files):
    manifest = {
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "b1_protocol_hash": protocol["protocol_hash"],
        "agent_key": agent_key,
        "agent_model": AGENTS[agent_key]["model"],
        "measurement_core_sha256": sha(ROOT / "A13_R3_Gemini.py"),
        "runner_sha256": sha(ROOT / "B1_C0_POPULATION_AMENDMENT_v2/B1_C0_01_run.py"),
        "files": {},
    }
    for p in files:
        if p.exists():
            manifest["files"][str(p.relative_to(ROOT))] = {"sha256": sha(p), "bytes": p.stat().st_size}
    for p in sorted((out / "agentdojo_runs").rglob("*.json")) if (out / "agentdojo_runs").exists() else []:
        manifest["files"][str(p.relative_to(ROOT))] = {"sha256": sha(p), "bytes": p.stat().st_size}
    dump(out / "manifest.json", manifest)


def run_benchmark(taxonomy):
    from agentdojo.benchmark import benchmark_suite_without_injections
    from agentdojo.logging import OutputLogger
    from agentdojo.task_suite.load_suites import get_suite
    pipeline = core.build_agent_pipeline()
    tasks_by_suite = defaultdict(set)
    for r in taxonomy["decisions"]:
        if r["development"]:
            continue
        if r["label"] in {"SPECIFIED", "DELEGATED", "PARTIAL"}:
            tasks_by_suite[r["suite"]].add(r["user_task"])
    core.RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with OutputLogger(str(core.RUNS_DIR)):
        for sname in core.SUITES:
            tids = sorted(tasks_by_suite.get(sname, []))
            if not tids:
                continue
            print(f"[B1/{core.AGENT_MODEL}] {sname}: {len(tids)} frozen untouched tasks; no injection")
            suite = get_suite(core.BENCHMARK_VERSION, sname)
            benchmark_suite_without_injections(
                pipeline, suite, logdir=core.RUNS_DIR, force_rerun=False,
                user_tasks=tids, benchmark_version=core.BENCHMARK_VERSION,
            )


def run_smoke():
    from agentdojo.benchmark import benchmark_suite_without_injections
    from agentdojo.logging import OutputLogger
    from agentdojo.task_suite.load_suites import get_suite
    pipeline = core.build_agent_pipeline()
    core.SMOKE_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    suite = get_suite(core.BENCHMARK_VERSION, core.SMOKE_SUITE)
    with OutputLogger(str(core.SMOKE_RUNS_DIR)):
        benchmark_suite_without_injections(
            pipeline, suite, logdir=core.SMOKE_RUNS_DIR, force_rerun=True,
            user_tasks=[core.SMOKE_USER_TASK], benchmark_version=core.BENCHMARK_VERSION,
        )
    hits = list(core.SMOKE_RUNS_DIR.glob(f"*/{core.SMOKE_SUITE}/{core.SMOKE_USER_TASK}/none/none.json"))
    if len(hits) != 1:
        sys.exit(f"FATAL: expected one smoke log, found {len(hits)}")
    o = read(hits[0])
    print(f"[B1 smoke] PASS model={core.AGENT_MODEL} utility={o.get('utility')} error={o.get('error')!r}")


def collect_records(taxonomy):
    taxonomy_by_task = defaultdict(list)
    for row in taxonomy["decisions"]:
        if row["development"]:
            continue
        if row["label"] in {"SPECIFIED", "DELEGATED", "PARTIAL"}:
            taxonomy_by_task[(row["suite"], row["user_task"])].append(row)
    records = []
    for sname in core.SUITES:
        task_ids = sorted({u for (ss, u) in taxonomy_by_task if ss == sname})
        for utid in task_ids:
            try:
                path = core.find_log_path(sname, utid)
            except Exception as e:
                sys.exit(f"FATAL: log discovery failed {sname}/{utid}: {type(e).__name__}: {e}")
            gt_rows = taxonomy_by_task[(sname, utid)]
            if path is None:
                for row in gt_rows:
                    records.append({
                        "suite": sname, "user_task": utid, "task_key": f"{sname}/{utid}",
                        "decision_id": row["decision_id"], "privileged_call_index": row["privileged_call_index"],
                        "privileged_fn": row["privileged_fn"], "label": row["label"],
                        "specified_fraction": row["specified_fraction"], "development": False,
                        "mapped": False, "utility": False, "primary_valid": False,
                        "primary_exclusion_reason": "agentdojo_log_missing",
                    })
                continue
            log_obj = read(path)
            mappings = core.map_gt_to_actual(gt_rows, list(log_obj.get("messages") or []))
            for mapping in mappings:
                try:
                    rec = core.measure_decision(log_obj, mapping)
                except Exception as e:
                    row = mapping["taxonomy"]
                    rec = {
                        "suite": row["suite"], "user_task": row["user_task"],
                        "task_key": f"{row['suite']}/{row['user_task']}", "decision_id": row["decision_id"],
                        "privileged_call_index": row["privileged_call_index"], "privileged_fn": row["privileged_fn"],
                        "label": row["label"], "specified_fraction": row["specified_fraction"],
                        "development": False, "mapped": mapping.get("mapped", False), "primary_valid": False,
                        "primary_exclusion_reason": f"measurement_exception:{type(e).__name__}:{str(e)[:180]}",
                    }
                records.append(rec)
    records.sort(key=lambda r: (core.SUITES.index(r["suite"]), r["user_task"], r["privileged_call_index"]))
    return records


def make_report(agent_key, protocol, results):
    h = results["primary_H_mean_del"]
    m = results["continuous_M_del"]
    lines = [
        f"# B1 — {AGENTS[agent_key]['model']} prospective replication",
        "",
        f"- B1 protocol: `{protocol['protocol_hash']}`",
        f"- Agent: `{AGENTS[agent_key]['model']}` via OpenRouter",
        "- Temperature: `0.0`",
        "- Attribution scorer: `meta-llama/Llama-3.3-70B-Instruct` (boundary-safe fixed completion)",
        "- Population: C0-corrected frozen A13 census (55 tasks / 73 decisions)",
        "",
        "## Primary H_mean_del",
        "",
        f"- SPECIFIED: `{h.get('specified_mean')}`",
        f"- DELEGATED: `{h.get('delegated_mean')}`",
        f"- Difference: `{h.get('difference')}`",
        f"- 95% task-bootstrap CI: `{h.get('ci95')}`",
        f"- Replication category: **{results['model_replication_category']}**",
        "",
        "## Continuous M_del",
        "",
        f"- SPECIFIED: `{m.get('specified_mean')}`",
        f"- DELEGATED: `{m.get('delegated_mean')}`",
        f"- Difference: `{m.get('difference')}`",
        f"- 95% task-bootstrap CI: `{m.get('ci95')}`",
        "",
        "## Guardrails",
        "",
        "This is a post-A14 prospective replication of an A12 discovery backbone. It is not part of the original A13 preregistration.",
        "No model-specific task selection, relabeling, mapper tuning, or endpoint tuning is permitted from this output.",
    ]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", choices=sorted(AGENTS), required=True)
    ap.add_argument("--preflight-only", action="store_true")
    ap.add_argument("--smoke-only", action="store_true")
    args = ap.parse_args()
    if args.preflight_only and args.smoke_only:
        sys.exit("FATAL: choose only one of --preflight-only / --smoke-only")

    protocol = verify_freeze()
    cfg, out = configure_core(args.agent)
    out.mkdir(parents=True, exist_ok=True)
    core.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Exact historical model identity must agree with frozen protocol.
    if protocol["agents"][args.agent]["model"] != cfg["model"]:
        sys.exit("FATAL: runner model differs from frozen B1 protocol")

    # Reuse R3's exact audited parent validation, tokenizer and boundary-safe scorer implementation.
    parent = core.validate_parents()
    core.init_tokenizer()
    if core._TOKENIZER is None:
        sys.exit(f"FATAL: Llama tokenizer unavailable: {core._TOKENIZER_ERROR}")
    core.boundary_safe_server_preflight()

    # Constructing OpenAI-compatible backend is network-free; verifies credential/config presence.
    _ = core.build_agent_pipeline()
    taxonomy = read(FROZEN_TAXONOMY)
    amend = protocol.get("population_amendment") or {}
    if sha(ROOT / "a13/taxonomy.json") != amend.get("historical_taxonomy_sha256"):
        sys.exit("FATAL: historical A13 taxonomy lineage drift")
    if sha(FROZEN_TAXONOMY) != amend.get("amended_taxonomy_sha256"):
        sys.exit("FATAL: amended B1 taxonomy hash drift")
    # C0 population overlay: these two externally consequential functions are the only
    # newly privileged functions. This affects only mapping eligibility for the four
    # prospectively frozen C0 decisions; all scorer/mapper/H/M/inference semantics stay fixed.
    _orig_is_privileged_fn = core.is_privileged_fn
    core.is_privileged_fn = lambda fn: bool(_orig_is_privileged_fn(fn) or fn in {"append_to_file", "reschedule_calendar_event"})

    pointer = {
        "b1_protocol_hash": protocol["protocol_hash"],
        "agent_key": args.agent,
        "agent_model": cfg["model"],
        "agent_base_url": cfg["base_url"],
        "temperature": 0.0,
        "scorer_model": core.SCORER_MODEL,
        "scorer_base_url": core.SCORER_BASE_URL,
    }
    dump(out / "protocol_pointer.json", pointer)
    dump(out / "taxonomy.json", taxonomy)

    if args.preflight_only:
        write_run_manifest(args.agent, protocol, out, [out / "protocol_pointer.json", out / "taxonomy.json"])
        print(f"[B1-01] PREFLIGHT PASS agent={args.agent} model={cfg['model']}; no agent benchmark outcome emitted")
        return

    if args.smoke_only:
        run_smoke()
        write_run_manifest(args.agent, protocol, out, [out / "protocol_pointer.json", out / "taxonomy.json"])
        print(f"[B1-01] DEVELOPMENT SMOKE COMPLETE agent={args.agent}; excluded from B1 analysis")
        return

    run_benchmark(taxonomy)
    records = collect_records(taxonomy)
    dump_jsonl(out / "decisions.jsonl", records)
    results = core.analyze_agent_specific(records)
    results["schema"] = "B1_AGENT_RESULT_C0_AMENDED_V2"
    results["b1_protocol_hash"] = protocol["protocol_hash"]
    results["agent_key"] = args.agent
    results["agent_model"] = cfg["model"]
    d = results["primary_H_mean_del"].get("difference")
    ci = results["primary_H_mean_del"].get("ci95")
    if d is None:
        cat = "INSUFFICIENT_PRIMARY_SUPPORT"
    elif d > 0 and isinstance(ci, list) and len(ci) == 2 and ci[0] is not None and ci[0] > 0:
        cat = "DIRECTIONAL_AND_CI_POSITIVE"
    elif d > 0:
        cat = "DIRECTIONAL_POSITIVE_CI_INCLUDES_ZERO_OR_UNAVAILABLE"
    elif d < 0:
        cat = "OPPOSITE_DIRECTION"
    else:
        cat = "ZERO_DIFFERENCE"
    results["model_replication_category"] = cat
    dump(out / "results.json", results)
    (out / "REPORT.md").write_text(make_report(args.agent, protocol, results), encoding="utf-8")
    write_run_manifest(args.agent, protocol, out, [
        out / "protocol_pointer.json", out / "taxonomy.json", out / "decisions.jsonl",
        out / "results.json", out / "REPORT.md",
    ])
    print(f"[B1-01] COMPLETE agent={args.agent} model={cfg['model']}")
    print(f"[B1-01] primary={results['primary_H_mean_del']}")
    print(f"[B1-01] category={cat}")

if __name__ == "__main__":
    main()
