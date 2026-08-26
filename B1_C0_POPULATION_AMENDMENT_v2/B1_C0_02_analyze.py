#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

_THIS_DIR = Path(__file__).resolve().parent
ROOT = _THIS_DIR.parent if _THIS_DIR.name == "B1_C0_POPULATION_AMENDMENT_v2" else _THIS_DIR
B1 = ROOT / "b1_a12_backbone_replication_c0_v2"
PROTOCOL = B1 / "protocol.json"
FREEZE = B1 / "FREEZE_COMPLETE.json"


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding="utf-8"))
def dump(p, x): p.write_text(json.dumps(x, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_agent(key):
    d = B1 / key
    for name in ["protocol_pointer.json", "decisions.jsonl", "results.json", "manifest.json"]:
        if not (d / name).exists():
            sys.exit(f"FATAL: B1 {key} incomplete; missing {name}")
    m = read(d / "manifest.json")
    for rel, rec in m.get("files", {}).items():
        p = ROOT / rel
        if not p.exists() or sha(p) != rec["sha256"]:
            sys.exit(f"FATAL: B1 {key} manifest mismatch: {rel}")
    return read(d / "results.json")


def main():
    if not PROTOCOL.exists() or not FREEZE.exists():
        sys.exit("FATAL: B1 freeze missing")
    protocol = read(PROTOCOL)
    cert = read(FREEZE)
    if cert.get("protocol_hash") != protocol.get("protocol_hash"):
        sys.exit("FATAL: B1 freeze/protocol mismatch")
    g = verify_agent("gpt4o")
    c = verify_agent("claude45")
    for r in [g, c]:
        if r.get("b1_protocol_hash") != protocol["protocol_hash"]:
            sys.exit("FATAL: agent result not tied to frozen B1 protocol")

    dg = g["primary_H_mean_del"].get("difference")
    dc = c["primary_H_mean_del"].get("difference")

    def coverage_estimable(r):
        h = r["primary_H_mean_del"]
        # clustered_group_contrast reports task counts by label in these fields.
        ns = h.get("n_specified_tasks")
        nd = h.get("n_delegated_tasks")
        if ns is None or nd is None:
            # Fall back to a CI being available under the frozen minimum-n rule.
            ci = h.get("ci95")
            return isinstance(ci, list) and len(ci) == 2 and ci[0] is not None and ci[1] is not None
        return ns >= 3 and nd >= 3

    coverage = {"gpt4o": coverage_estimable(g), "claude45": coverage_estimable(c)}
    positives = sum(x is not None and x > 0 for x in [dg, dc])
    if not all(coverage.values()):
        joint = "COVERAGE_LIMITED"
    elif positives == 2:
        joint = "CONVERGENT_DIRECTIONAL_REPLICATION"
    elif positives == 1:
        joint = "MIXED_DIRECTION"
    else:
        joint = "NO_DIRECTIONAL_REPLICATION"

    out = {
        "schema": "B1_COMBINED_RESULT_C0_AMENDED_V2",
        "b1_protocol_hash": protocol["protocol_hash"],
        "joint_category": joint,
        "coverage_estimable": coverage,
        "predeclared_rule": protocol["joint_interpretation"],
        "gpt4o": {
            "agent_model": g["agent_model"],
            "primary_H_mean_del": g["primary_H_mean_del"],
            "continuous_M_del": g["continuous_M_del"],
            "counts": g["counts"],
            "model_replication_category": g["model_replication_category"],
        },
        "claude45": {
            "agent_model": c["agent_model"],
            "primary_H_mean_del": c["primary_H_mean_del"],
            "continuous_M_del": c["continuous_M_del"],
            "counts": c["counts"],
            "model_replication_category": c["model_replication_category"],
        },
        "interpretation_guardrails": [
            "B1 is a post-A14 prospective replication of A12 discovery backbones, not part of the original A13 preregistration.",
            "The joint category is sign-based and was frozen before B1 outcomes; model-specific CIs determine inferential strength.",
            "Do not drop a backbone because of attrition or an inconvenient result; report coverage and exclusions for both.",
            "B1 tests ecological trajectory replication under a fixed Llama attribution scorer; it is not GPT- or Claude-native attribution.",
        ],
    }
    dump(B1 / "combined_results.json", out)
    lines = [
        "# B1 — Discovery-Backbone Prospective Replication — C0-Amended Combined Result",
        "",
        f"**Joint predeclared category: {joint}**",
        "",
        "| Backbone | H SPECIFIED | H DELEGATED | Difference | 95% CI | Model category |",
        "|---|---:|---:|---:|---|---|",
    ]
    for key, r in [("GPT-4o", g), ("Claude Sonnet 4.5", c)]:
        h = r["primary_H_mean_del"]
        lines.append(
            f"| {key} | {h.get('specified_mean')} | {h.get('delegated_mean')} | "
            f"{h.get('difference')} | {h.get('ci95')} | {r.get('model_replication_category')} |"
        )
    lines += [
        "",
        "The two backbones were selected because they were A12 discovery backbones, not as a generic model-breadth sweep.",
        "Model-specific attrition and exclusion counts must accompany this table in the paper/artifact.",
    ]
    (B1 / "COMBINED_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[B1-02] COMPLETE joint_category={joint}")
    print(f"[B1-02] wrote {B1/'combined_results.json'}")
    print(f"[B1-02] wrote {B1/'COMBINED_REPORT.md'}")

if __name__ == "__main__":
    main()
