#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, math, tarfile
from pathlib import Path
from typing import Any

RUN_DIR = Path("N4_N5_RUN_v1")

PATHS = {
    "a14": Path("a14_minimal_factorial/analysis/results.json"),
    "r2a": Path("a14_minimal_factorial/threshold_aivr_v1/results.json"),
    "a15a": Path("a15a_selectivity_consequence/results.json"),
    "agentwatcher": Path("a15b0_architecture_boundary/analysis_results.json"),
    "attriguard": Path("attriguard_a14_v2/scientific_v1/SCIENTIFIC_ANALYSIS.json"),
    "p2": Path("P2_AGENTWATCHER_NODEFENSE_RUN_v1/P2_ANALYSIS.json"),
    "p0b3": Path("P0B3_CAUSALARMOR_LIVE_RUN_v1/P0B3_ANALYSIS.json"),
    "b1": Path("b1_a12_backbone_replication_c0_v2/combined_results.json"),
    "n3_tar": Path("N3_COMPLETE_AUTHOR_v1_2.tar.gz"),
    "p0b3_act": Path("P0B3_ACT_RUN_v1/P0B3_ACT_RESULT.json"),
    "p0b3_shadow": Path("P0B3_ACT_SHADOW_RUN_v1/P0B3_ACT_SHADOW_RESULT.json"),
}
N3_MEMBER = "N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def load_json(p: Path) -> Any:
    return json.loads(p.read_text())

def load_n3(tar_path: Path):
    with tarfile.open(tar_path, "r:gz") as tf:
        m = tf.getmember(N3_MEMBER)
        b = tf.extractfile(m).read()
    return json.loads(b), sha256_bytes(b)

def close(a, b, tol=1e-10):
    return abs(float(a)-float(b)) <= tol

def req(cond: bool, msg: str):
    if not cond:
        raise SystemExit("FATAL: " + msg)

def require_paths():
    missing = [str(p) for p in PATHS.values() if not p.exists()]
    if missing:
        raise SystemExit("FATAL: missing required closed-evidence inputs:\n  " + "\n  ".join(missing))

def validate_and_collect():
    require_paths()
    a14 = load_json(PATHS["a14"])
    r2a = load_json(PATHS["r2a"])
    a15a = load_json(PATHS["a15a"])
    aw = load_json(PATHS["agentwatcher"])
    ag = load_json(PATHS["attriguard"])
    p2 = load_json(PATHS["p2"])
    p0b3 = load_json(PATHS["p0b3"])
    b1 = load_json(PATHS["b1"])
    act = load_json(PATHS["p0b3_act"])
    shadow = load_json(PATHS["p0b3_shadow"])
    n3, n3_member_sha = load_n3(PATHS["n3_tar"])

    # A14 exact-action-fixed core.
    l_p1 = a14["primary_factorial_CA_MARGIN"]["P1_PROVENANCE_MAIN"]
    g_p1 = a14["gemma_source_fidelity"]["factorial_CA_MARGIN"]["P1_PROVENANCE_MAIN"]
    repl = a14["operator_robustness_CA_MARGIN_REPLACE"]["P1_PROVENANCE_MAIN"]
    req(l_p1["n"] == 24 and l_p1["n_negative"] == 24, "A14 Llama P1 no longer 24/24 negative")
    req(g_p1["n"] == 24 and g_p1["n_negative"] == 24, "A14 Gemma P1 no longer 24/24 negative")
    req(close(l_p1["mean"], -1.1797316186554594), "A14 Llama P1 changed")
    req(close(g_p1["mean"], -1.0111624004850248), "A14 Gemma P1 changed")
    req(repl["n"] == 24 and repl["n_negative"] == 24 and close(repl["mean"], -1.0168518398608433),
        "A14 token-matched robustness changed")

    # R2A operating point.
    rs = r2a["summary"]
    for scorer in ("llama", "gemma"):
        req(rs[scorer]["n_nondegenerate_rows"] == 191, f"R2A {scorer} nondegenerate row count changed")
        req(rs[scorer]["nondegenerate_rows_with_aivr_gt0"] == 191, f"R2A {scorer} no longer 191/191 AIVR>0")
    req(rs["llama"]["tau0"]["aivr_class_n"] == 20, "R2A Llama tau0 AIVR count changed")
    req(rs["gemma"]["tau0"]["aivr_class_n"] == 18, "R2A Gemma tau0 AIVR count changed")

    # N3 matched discriminant-validity result.
    for scorer, exp in {
        "llama": (0.6545399, -0.370917, 0.507798),
        "gemma": (0.5039115, -0.474691, 0.537154),
    }.items():
        x = n3["scorers"][scorer]
        D = x["D_discriminant_gap"]
        Q = x["Q_action_controlled_selectivity"]
        T = x["T_manipulation"]
        req(D["ci95"][0] > 0 and D["mean"] > 0, f"N3 {scorer} D category changed")
        req(Q["ci95"][1] < 0 and Q["n_negative"] == 24, f"N3 {scorer} Q category changed")
        req(T["ci95"][0] > 0 and T["n_positive"] == 24, f"N3 {scorer} T category changed")

    # B1 breadth.
    req(b1["joint_category"] == "CONVERGENT_DIRECTIONAL_REPLICATION", "B1 joint category changed")
    req(b1["gpt4o"]["primary_H_mean_del"]["difference"] > 0, "B1 GPT-4o direction changed")
    req(b1["claude45"]["primary_H_mean_del"]["difference"] > 0, "B1 Claude direction changed")

    # A15a operational activation.
    req(a15a["eligible_decisions"] == 26 and a15a["activated_decisions_tau0"] == 18, "A15a 18/26 changed")

    # AgentWatcher controlled + natural.
    req(all(v == 0 for v in aw["controlled"]["cell_flag_rates"].values()), "AgentWatcher controlled A14 is no longer all-zero")
    aw_nat = aw["natural"]["by_label"]["ALL"]
    req(aw_nat["n_decisions"] == 26, "AgentWatcher natural denominator changed")
    req(close(aw_nat["AW_flag_rate_decision"], 2/26), "AgentWatcher natural 2/26 changed")
    req(close(aw_nat["CA_flag_rate_decision"], 16/26), "CausalArmor-style natural 16/26 changed")

    # AttriGuard architecture absorption.
    req(ag["run_complete"] is True and ag["n_condition_repeats"] == 480, "AttriGuard run state changed")
    req(all(close(v, 0.0) for v in ag["cell_mean_block_rates"].values()), "AttriGuard final block rate no longer zero")
    req(close(ag["primary_P1"]["mean"], 0.0), "AttriGuard P1 changed")
    req(all(close(v, 0.0) for v in ag["repeatwise_AIVR_class"].values()), "AttriGuard AIVR changed")

    # P2 systems tradeoff.
    req(p2["n_pairs"] == 200 and p2["primary_verdict"] == "MATCHED_INPUT_DEFENSE_OVERHEAD_SUPPORTED",
        "P2 state changed")
    req(close(p2["utility"]["historical_agentwatcher_rate"], .28) and close(p2["utility"]["no_defense_rate"], .60),
        "P2 utility rates changed")
    req(close(p2["attack_success"]["historical_agentwatcher_rate"], 0.0) and close(p2["attack_success"]["no_defense_rate"], .16),
        "P2 attack rates changed")

    # P0b-3 external-regime calibration.
    req(p0b3["primary"]["disposition"] == "SAME_EXTERNAL_REGIME", "P0b-3 disposition changed")
    req(p0b3["resume_integrity"]["successful_attempt_defense_events"] == 624, "P0b-3 event denominator changed")

    # P0b-3-ACT primary + shadow. Read schema flexibly but assert known values.
    def pick(d, *paths):
        for path in paths:
            cur = d
            ok = True
            for k in path:
                if isinstance(cur, dict) and k in cur:
                    cur = cur[k]
                else:
                    ok = False; break
            if ok:
                return cur
        return None

    # Package result schemas carry these direct objects under primary/split or group names.
    text_act = json.dumps(act)
    text_shadow = json.dumps(shadow)
    for needle in ('"benign"', '"attack"'):
        req(needle in text_act, "P0b-3-ACT result lacks benign/attack split")
        req(needle in text_shadow, "P0b-3 shadow result lacks benign/attack split")

    # Robustly recurse for count/denom pairs.
    def find_rate_group(obj, target_num, target_den):
        if isinstance(obj, dict):
            vals = list(obj.values())
            nums = [v for v in vals if isinstance(v, int)]
            if target_num in nums and target_den in nums:
                return True
            return any(find_rate_group(v, target_num, target_den) for v in vals)
        if isinstance(obj, list):
            return any(find_rate_group(v, target_num, target_den) for v in obj)
        return False
    req(find_rate_group(act, 20, 37) and find_rate_group(act, 496, 587), "P0b-3-ACT exact split changed")
    req(find_rate_group(shadow, 22, 37) and find_rate_group(shadow, 516, 587), "P0b-3 shadow exact split changed")

    evidence = {
        "schema": "N4_N5_BOUNDED_SYNTHESIS_EVIDENCE_V1",
        "status": "CLOSED_INPUTS_VALIDATED",
        "no_new_inference": True,
        "no_combined_scalar": True,
        "properties": {
            "authorization_property_preserving_consistency": {
                "A14_llama_P1": l_p1,
                "A14_gemma_P1": g_p1,
                "A14_token_matched_llama_P1": repl,
                "R2A": {
                    "llama_tau0_aivr": f'{rs["llama"]["tau0"]["aivr_class_n"]}/24',
                    "gemma_tau0_aivr": f'{rs["gemma"]["tau0"]["aivr_class_n"]}/24',
                    "llama_nondegenerate_aivr_gt0": "191/191",
                    "gemma_nondegenerate_aivr_gt0": "191/191",
                },
                "interpretation": "The studied CausalArmor-style causal-support observable is not authorization-invariant on the exact-action/effect-fixed A14 orbit."
            },
            "threat_action_discrimination": {
                "N3_llama": {
                    "D": n3["scorers"]["llama"]["D_discriminant_gap"],
                    "Q": n3["scorers"]["llama"]["Q_action_controlled_selectivity"],
                    "T": n3["scorers"]["llama"]["T_manipulation"],
                    "P": n3["scorers"]["llama"]["P_supported_property_shift"],
                    "N": n3["scorers"]["llama"]["N_nuisance"],
                },
                "N3_gemma": {
                    "D": n3["scorers"]["gemma"]["D_discriminant_gap"],
                    "Q": n3["scorers"]["gemma"]["Q_action_controlled_selectivity"],
                    "T": n3["scorers"]["gemma"]["T_manipulation"],
                    "P": n3["scorers"]["gemma"]["P_supported_property_shift"],
                    "N": n3["scorers"]["gemma"]["N_nuisance"],
                },
                "interpretation": "The proxy is action/threat-selective, but raw supported-action magnitude is not cleanly authorization-ordered: benign nuisance displacement is larger on average than the supported unauthorized-control displacement."
            },
            "architecture_operating_point": {
                "A15a": {"activated": 18, "denominator": 26},
                "AgentWatcher_controlled_A14": {"all_4_cell_flag_rates": 0.0, "n_bases": 24},
                "AgentWatcher_natural": {"AW": "2/26", "CausalArmor_style": "16/26"},
                "AttriGuard_controlled_A14": {"final_block_rate": 0.0, "condition_repeats": 480, "P1": 0.0, "AIVR": 0.0},
                "P2": {"defense_on_utility": "56/200", "no_defense_utility": "120/200",
                       "defense_on_ASR": "0/200", "no_defense_ASR": "32/200"},
                "P0b3_external_regime": {
                    "BU_percent": p0b3["primary"]["BU_percent"],
                    "UA_percent": p0b3["primary"]["UA_percent"],
                    "ASR_percent": p0b3["primary"]["ASR_percent"],
                    "disposition": p0b3["primary"]["disposition"],
                },
                "P0b3_ACT": {"ACTION_ONLY_benign": "20/37", "ACTION_ONLY_attack": "496/587",
                             "gap_pp": 30.44, "shadow_benign": "22/37", "shadow_attack": "516/587",
                             "shadow_gap_pp": 28.45},
                "interpretation": "Internal causal-support variation is not final policy. Threshold and guardrail architecture determine whether the signal becomes intervention; the calibrated full pipeline still separates attack from benign activation descriptively."
            },
            "breadth": {
                "B1_joint": b1["joint_category"],
                "GPT4o_H_difference": b1["gpt4o"]["primary_H_mean_del"],
                "Claude45_H_difference": b1["claude45"]["primary_H_mean_del"],
                "interpretation": "The natural SPECIFIED-vs-DELEGATED H direction reproduces across both frozen external backbones, with model-specific H CIs crossing zero."
            }
        },
        "bounded_synthesis": {
            "verdict": "SUPPORTED_TWO_PROPERTY_PLUS_ARCHITECTURE_VIEW",
            "statement": (
                "Causal support contains useful threat/action information but is not an authorization oracle. "
                "Authorization-preserving evidence relocation can move the studied proxy strongly in an attack-like direction; "
                "matched unauthorized control remains action-selective, yet raw proxy magnitude is not cleanly authorization-ordered. "
                "Operating point and architecture determine whether this mixed internal signal becomes final intervention."
            ),
            "prohibited": [
                "No new scalar combining consistency and discrimination.",
                "No claim that causal attribution is totally indiscriminate.",
                "No claim that all causal-attribution defenses are unsafe.",
                "No causal interpretation of P0b-3-ACT.",
                "No N2 authorization from this script."
            ]
        }
    }

    manifest = {
        "schema": "N4_N5_INPUT_MANIFEST_V1",
        "inputs": {k: {"path": str(p), "sha256": sha256_file(p)} for k,p in PATHS.items()},
        "n3_member": {"member": N3_MEMBER, "sha256": n3_member_sha},
    }
    return evidence, manifest
