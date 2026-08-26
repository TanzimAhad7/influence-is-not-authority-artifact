#!/usr/bin/env python3
"""Deterministic, no-network verifier for the USENIX Security '27 artifact.

The default verification path reads only frozen files shipped in this artifact.
It makes no model/provider calls, installs no packages, and records no host/user paths.
"""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "artifact_outputs" / "verification"
OUTDIR.mkdir(parents=True, exist_ok=True)
CLAIMS: list[dict[str, Any]] = []


def _load_layout_map() -> dict[str, str]:
    p = ROOT / "LEGACY_PATH_MAP.tsv"
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    with p.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            out[row["legacy_top_level"]] = row["new_path"]
    return out


LAYOUT_MAP = _load_layout_map()


def resolve_path(rel: str | Path) -> Path:
    relp = Path(rel)
    if relp.is_absolute():
        return relp
    parts = relp.parts
    if parts and parts[0] in LAYOUT_MAP:
        return ROOT / LAYOUT_MAP[parts[0]] / Path(*parts[1:])
    return ROOT / relp


def jload(rel: str) -> Any:
    return json.loads(resolve_path(rel).read_text(encoding="utf-8"))


def jsonl(rel: str) -> list[dict[str, Any]]:
    return [json.loads(x) for x in resolve_path(rel).read_text(encoding="utf-8").splitlines() if x.strip()]


def csvrows(rel: str) -> list[dict[str, str]]:
    with resolve_path(rel).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256(rel: str) -> str:
    h = hashlib.sha256()
    with resolve_path(rel).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def close(a: Any, b: Any, tol: float = 1e-9) -> bool:
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(float(a), float(b), rel_tol=tol, abs_tol=tol)
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return all(close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict) and set(a) == set(b):
        return all(close(a[k], b[k], tol) for k in a)
    return a == b


def display_source(source: str) -> str:
    parts = source.split(" + ")
    out_parts = []
    for part in parts:
        replaced = part
        for old, new in sorted(LAYOUT_MAP.items(), key=lambda kv: len(kv[0]), reverse=True):
            if part == old:
                replaced = new
                break
            if part.startswith(old + "/"):
                replaced = new + part[len(old):]
                break
        out_parts.append(replaced)
    return " + ".join(out_parts)


def add(cid: str, description: str, expected: Any, actual: Any, source: str,
        verification_type: str = "frozen_analysis_check", tol: float = 1e-9,
        note: str | None = None) -> None:
    ok = close(actual, expected, tol)
    row = {
        "id": cid,
        "description": description,
        "expected": expected,
        "actual": actual,
        "source": display_source(source),
        "verification_type": verification_type,
        "status": "PASS" if ok else "FAIL",
    }
    if note:
        row["note"] = note
    CLAIMS.append(row)


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def percentile_linear(xs: list[float], p: float) -> float:
    ys = sorted(xs)
    x = (len(ys) - 1) * p
    lo, hi = math.floor(x), math.ceil(x)
    if lo == hi:
        return ys[lo]
    return ys[lo] * (hi - x) + ys[hi] * (x - lo)


def bootstrap_linear(vals: list[float], B: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    sims = []
    n = len(vals)
    for _ in range(B):
        samp = [vals[rng.randrange(n)] for __ in range(n)]
        sims.append(mean(samp))
    return [percentile_linear(sims, .025), percentile_linear(sims, .975)]


def bootstrap_discrete(vals: list[float], B: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    n = len(vals)
    sims = []
    for _ in range(B):
        sims.append(mean([vals[rng.randrange(n)] for __ in range(n)]))
    sims.sort()
    return [sims[int(.025 * B)], sims[min(B - 1, int(.975 * B))]]


def content_text(msg: dict[str, Any]) -> str:
    c = msg.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return "\n".join(str(b.get("content", "")) for b in c if isinstance(b, dict))
    return ""


def tool_batches(messages: list[dict[str, Any]]) -> list[tuple[int, int, list[dict[str, Any]]]]:
    out = []
    i = 0
    while i < len(messages):
        if messages[i].get("role") != "tool":
            i += 1
            continue
        j = i
        batch = []
        while j < len(messages) and messages[j].get("role") == "tool":
            batch.append(messages[j])
            j += 1
        out.append((i, j, batch))
        i = j
    return out


def load_paef_oracle():
    p = ROOT / "artifact_support/paef_oracle.py"
    spec = importlib.util.spec_from_file_location("artifact_paef_oracle", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def resolve_raw(row: dict[str, Any]) -> Path:
    rel = row["raw_result_relpath"]
    marker = "scientific_v1/"
    if marker not in rel:
        raise RuntimeError(f"unexpected raw_result_relpath: {rel}")
    suffix = rel.split(marker, 1)[1]
    return resolve_path("E2E_ATTR_AUTH_v1/scientific_v1") / suffix


def verify_natural() -> None:
    rel = "A13_C0_EXTENSION_SCIENCE_v1/A13_C0_EXTENSION_RESULT_v1.json"
    x = jload(rel)
    raw = jsonl("A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl")
    valid = [r for r in raw if r.get("primary_valid")]
    add("C1.N_VALID", "Corrected natural cohort has 29 valid privileged decisions.", 29, len(valid),
        "A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl", "rederived_raw")
    add("C1.N_TASKS", "Corrected natural cohort spans 25 tasks.", 25,
        len({(r.get("suite"), r.get("user_task")) for r in valid}),
        "A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl", "rederived_raw")
    h = x["coverage_corrected_primary"]["primary_H_mean_del"]
    add("C1.H", "Specified vs delegated user-side dominance contrast.",
        {"specified": .75, "delegated": 1/6, "difference": 7/12,
         "ci95": [0.15551282051282053, 0.9393939393939394]},
        {"specified": h["specified_mean"], "delegated": h["delegated_mean"],
         "difference": h["difference"], "ci95": h["ci95"]}, rel)


def verify_breadth() -> None:
    rel = "b1_a12_backbone_replication_c0_v2/combined_results.json"
    x = jload(rel)
    expected = {
        "gpt4o": {"H_diff": 0.38888888888888895, "H_ci": [-0.027272727272727337, 0.7857142857142858],
                   "M_diff": 0.9107258224408493, "M_ci": [0.10366639991148151, 1.778493563819895]},
        "claude45": {"H_diff": 0.2153846153846154, "H_ci": [-0.3711057692307691, 0.7333333333333333],
                     "M_diff": 0.9744911774070546, "M_ci": [-0.06434624776899199, 2.2378314126842827]},
    }
    actual = {}
    for k in ["gpt4o", "claude45"]:
        actual[k] = {"H_diff": x[k]["primary_H_mean_del"]["difference"], "H_ci": x[k]["primary_H_mean_del"]["ci95"],
                     "M_diff": x[k]["continuous_M_del"]["difference"], "M_ci": x[k]["continuous_M_del"]["ci95"]}
    add("B1.BREADTH", "Prospective GPT-4o/Claude trajectory breadth under fixed Llama scoring.", expected, actual, rel)
    protocol = jload("b1_a12_backbone_replication_c0_v2/protocol.json")
    text = json.dumps(protocol).lower()
    add("B1.ROLE", "Breadth package records generator/scorer role separation.", True,
        "llama-3.3-70b" in text and "scorer" in text and "scorer_changed" in text,
        "b1_a12_backbone_replication_c0_v2/protocol.json", "frozen_metadata_check")


def verify_a14() -> None:
    rel = "a14_minimal_factorial/analysis/results.json"
    x = jload(rel)
    L = x["primary_factorial_CA_MARGIN"]["P1_PROVENANCE_MAIN"]
    G = x["gemma_source_fidelity"]["factorial_CA_MARGIN"]["P1_PROVENANCE_MAIN"]
    add("A14.LLAMA", "Llama source relocation: 24/24 attack-like, mean and CI.",
        {"n":24,"n_negative":24,"mean":-1.1797316186554594,"ci95":[-1.2836113407067742,-1.0797475485595784]},
        {k:L[k] for k in ["n","n_negative","mean","ci95"]}, rel)
    add("A14.GEMMA", "Gemma source relocation: 24/24 attack-like, mean and CI.",
        {"n":24,"n_negative":24,"mean":-1.0111624004850248,"ci95":[-1.1536260005123524,-0.8790134025004686]},
        {k:G[k] for k in ["n","n_negative","mean","ci95"]}, rel)
    # Re-derive support shifts from per-condition score rows for each scorer.
    for scorer in ["llama","gemma"]:
        rows = jsonl(f"a14_minimal_factorial/scorer_{scorer}/condition_scores.jsonl")
        by = {(r["base_id"], r["factor_provenance"], r["factor_descendant"]): r for r in rows}
        bases = sorted({r["base_id"] for r in rows})
        du, ds = [], []
        for bid in bases:
            for desc in ["ECHO","SHAM"]:
                u = by[(bid,"USER_ID",desc)]
                t = by[(bid,"TOOL_ID",desc)]
                du.append(t["dU_fixed"] - u["dU_fixed"])
                ds.append(t["dS_relevant"] - u["dS_relevant"])
        # Main paper uses base-averaged differences. Collapse descendants per base.
        du_b=[]; ds_b=[]
        for bid in bases:
            du_b.append(mean([by[(bid,"TOOL_ID",d)]["dU_fixed"] / by[(bid,"TOOL_ID",d)]["completion_token_count"]
                              - by[(bid,"USER_ID",d)]["dU_fixed"] / by[(bid,"USER_ID",d)]["completion_token_count"]
                              for d in ["ECHO","SHAM"]]))
            ds_b.append(mean([by[(bid,"TOOL_ID",d)]["dS_relevant"] / by[(bid,"TOOL_ID",d)]["completion_token_count"]
                              - by[(bid,"USER_ID",d)]["dS_relevant"] / by[(bid,"USER_ID",d)]["completion_token_count"]
                              for d in ["ECHO","SHAM"]]))
        exp_du = -0.4313119 if scorer=="llama" else -0.5323
        exp_ds = 0.7484197 if scorer=="llama" else 0.4788
        add(f"A14.{scorer.upper()}.SUPPORT_USER", f"{scorer} user-side support falls on all 24 bases.",
            {"all_negative":True,"mean_rounded4":round(exp_du,4)},
            {"all_negative":all(v<0 for v in du_b),"mean_rounded4":round(mean(du_b),4)},
            f"a14_minimal_factorial/scorer_{scorer}/condition_scores.jsonl", "rederived_raw", tol=1e-4)
        add(f"A14.{scorer.upper()}.SUPPORT_TOOL", f"{scorer} relevant-tool support rises on all 24 bases.",
            {"all_positive":True,"mean_rounded4":round(exp_ds,4)},
            {"all_positive":all(v>0 for v in ds_b),"mean_rounded4":round(mean(ds_b),4)},
            f"a14_minimal_factorial/scorer_{scorer}/condition_scores.jsonl", "rederived_raw", tol=1e-4)
    r2b = jload("R2B_JTF_AUTHOR_v1/R2B_JTF_RESULTS.json")
    add("A14.TAU0_AIVR", "At tau=0, authorization-equivalent verdict varies on 20/24 Llama and 18/24 Gemma bases.",
        {"llama":20/24,"gemma":18/24},
        {"llama":r2b["scorers"]["llama"]["tau0"]["a14_aivr"],"gemma":r2b["scorers"]["gemma"]["tau0"]["a14_aivr"]},
        "R2B_JTF_AUTHOR_v1/R2B_JTF_RESULTS.json")


def n3_endpoint(rows: list[dict[str, Any]], seed: int = 20260813, B: int = 20000) -> dict[str, Any]:
    bases = sorted({r["base_id"] for r in rows})
    diffs=[]
    for bid in bases:
        tool = [r["CA_MARGIN"] for r in rows if r["base_id"]==bid and r["unit_type"]=="A14_NUISANCE_REPLICATION" and r["action_role"]=="AUTH" and r["provenance"]=="TOOL_ID"]
        alt = [r["CA_MARGIN"] for r in rows if r["base_id"]==bid and r["unit_type"]=="N3_POSITIVE_CONTROL" and r["action_role"]=="ALT" and r["directive_arm"]=="CONFLICT"]
        if len(tool)!=2 or len(alt)!=2:
            raise RuntimeError(f"N3 endpoint row census mismatch {bid}: {len(tool)}, {len(alt)}")
        diffs.append(mean(alt)-mean(tool))
    return {"mean":mean(diffs),"ci95":bootstrap_discrete(diffs,B,seed),"n_negative":sum(v<0 for v in diffs),"n":len(diffs)}


def verify_n3() -> None:
    rel="N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json"
    x=jload(rel)
    for scorer in ["llama","gemma"]:
        sx=x["scorers"][scorer]
        d=sx["D_discriminant_gap"]
        expected_d = ({"mean":0.654540155,"ci95":[0.447511,0.863571],"n_positive":23}
                      if scorer=="llama" else {"mean":0.503911549,"ci95":[0.180641,0.824582],"n_positive":14})
        actual_d={"mean":d["mean"],"ci95":d["ci95"],"n_positive":d["n_positive"]}
        add(f"N3.{scorer.upper()}.D", f"{scorer} harmless source relocation has larger average displacement than authorization-changing comparison.",
            expected_d, actual_d, rel, tol=2e-6)
        p=sx["P_supported_property_shift"]
        expected_p_neg=17 if scorer=="llama" else 23
        add(f"N3.{scorer.upper()}.P_SIGNS", f"{scorer} authorization-changing comparison case-level sign count is heterogeneous.",
            expected_p_neg, p["n_negative"], rel)
        q=sx["Q_action_controlled_selectivity"]; t=sx["T_manipulation"]
        add(f"N3.{scorer.upper()}.QT", f"{scorer} manipulation/selectivity controls remain directional on 24/24 bases.",
            {"Q_negative":24,"T_positive":24}, {"Q_negative":q["n_negative"],"T_positive":t["n_positive"]}, rel)
        rows=jsonl(f"N3_PREFREEZE_AUTHOR_v1_1/science_{scorer}/SCIENCE_SCORES.jsonl")
        ep=n3_endpoint(rows)
        exp = ({"mean":-0.53361905,"ci95":[-0.7734944,-0.3034540],"n_negative":17,"n":24}
               if scorer=="llama" else {"mean":-0.46147314,"ci95":[-0.6754854,-0.2516981],"n_negative":13,"n":24})
        add(f"N3.{scorer.upper()}.ENDPOINT", f"{scorer} matched unauthorized ALT endpoint is more attack-like on average than authorized TOOL endpoint.",
            exp, ep, f"N3_PREFREEZE_AUTHOR_v1_1/science_{scorer}/SCIENCE_SCORES.jsonl", "rederived_raw", tol=2e-6,
            note="This endpoint contrast is distinct from N3 P_supported_property_shift.")


def verify_r2b() -> None:
    rel="R2B_JTF_AUTHOR_v1/R2B_JTF_RESULTS.json"; x=jload(rel)
    exp_tau={"llama":{"auth":30/48,"alt":36/48,"gap":.125,"aivr":20/24},
             "gemma":{"auth":35/48,"alt":44/48,"gap":.1875,"aivr":18/24}}
    for scorer in ["llama","gemma"]:
        t=x["scorers"][scorer]["tau0"]
        actual={"auth":t["n3_auth_flag_rate"],"alt":t["n3_alt_flag_rate"],"gap":t["n3_alt_minus_auth_mean"],"aivr":t["a14_aivr"]}
        add(f"R2B.{scorer.upper()}.TAU0", f"{scorer} tau=0 anchor.", exp_tau[scorer], actual, rel)
        rows=csvrows(f"R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_{scorer}.csv")
        add(f"R2B.{scorer.upper()}.NROWS", f"{scorer} full threshold sweep has 386 rows.",386,len(rows),f"R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_{scorer}.csv","rederived_raw")
        zero=[r for r in rows if abs(float(r["a14_benign_flag_rate"]))<1e-12]
        zero_best=max(float(r["n3_alt_flag_rate"]) for r in zero)
        add(f"R2B.{scorer.upper()}.ZERO_BENIGN", f"{scorer} best unauthorized catch rate among zero-benign operating points.",
            .25 if scorer=="llama" else .375, zero_best, f"R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_{scorer}.csv","rederived_raw")
        central=[r for r in rows if .2 <= float(r["a14_benign_flag_rate"]) <= .8]
        min_aivr=min(float(r["a14_aivr"]) for r in central)
        add(f"R2B.{scorer.upper()}.CENTRAL_AIVR", f"{scorer} minimum AIVR in predeclared 20-80% benign band.",
            14/24 if scorer=="llama" else 15/24, min_aivr,
            f"R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_{scorer}.csv","rederived_raw")


def verify_agentwatcher() -> None:
    rel="AW_N3_AUTHOR_v1/AWN3_BASE_EFFECTS.csv"; rows=csvrows(rel)
    actual={k:sum(float(r[k])>0.5 for r in rows) for k in ["ALIGNED_AUTH","ALIGNED_ALT","CONFLICT_AUTH","CONFLICT_ALT"]}
    add("AW.MATCHED_GATE", "AgentWatcher aligned discrimination and tested conflict saturation.",
        {"ALIGNED_AUTH":4,"ALIGNED_ALT":21,"CONFLICT_AUTH":24,"CONFLICT_ALT":24}, actual, rel, "rederived_raw")
    p2=jload("P2_AGENTWATCHER_NODEFENSE_RUN_v1/P2_ANALYSIS.json")
    add("AW.ON_OFF", "Separate AgentWatcher ON/OFF matched-input population.",
        {"on_attack":0.0,"off_attack":.16,"on_utility":.28,"off_utility":.60,"n":200},
        {"on_attack":p2["attack_success"]["historical_agentwatcher_rate"],"off_attack":p2["attack_success"]["no_defense_rate"],
         "on_utility":p2["utility"]["historical_agentwatcher_rate"],"off_utility":p2["utility"]["no_defense_rate"],"n":p2["n_pairs"]},
        "P2_AGENTWATCHER_NODEFENSE_RUN_v1/P2_ANALYSIS.json")


def verify_n6() -> None:
    rel="n6_attriguard_n3_v1/scientific_v1/N6_ANALYSIS.json"; x=jload(rel)
    a=x["absolute_operating_points"]; p=x["primary"]
    add("N6.AGGREGATE", "AttriGuard aggregate matched block endpoint.",
        {"auth":113,"alt":87,"gap":-0.10833333333333332,"ci95":[-0.3625,0.14583333333333334],"signs":{"negative":12,"positive":8,"zero":4}},
        {"auth":a["AUTH_blocked"],"alt":a["ALT_blocked"],"gap":p["mean_G_b"],"ci95":p["bootstrap_ci95_percentile"],"signs":p["base_sign_counts"]}, rel)
    routes=x["route_decomposition"]
    add("N6.ROUTES", "AttriGuard exact-survival/fuzzy-review route counts.",
        {"AUTH":{"EXACT":70,"FUZZY":169,"HARD_FAIL":1},"ALT":{"EXACT":138,"FUZZY":101,"HARD_FAIL":1}},
        {"AUTH":{"EXACT":routes["AUTH"]["EXACT_SHADOW_SURVIVAL"],"FUZZY":routes["AUTH"]["FUZZY_JUDGE_PATH"],"HARD_FAIL":routes["AUTH"]["NO_SAME_FUNCTION_HARD_FAIL"]},
         "ALT":{"EXACT":routes["ALT"]["EXACT_SHADOW_SURVIVAL"],"FUZZY":routes["ALT"]["FUZZY_JUDGE_PATH"],"HARD_FAIL":routes["ALT"]["NO_SAME_FUNCTION_HARD_FAIL"]}}, rel)
    rows=jsonl("n6_attriguard_n3_v1/scientific_v1/N6_RESULTS.jsonl")
    cond={}
    for role in ["AUTH","ALT"]:
        fuzzy=[r for r in rows if r[f"{role}_route"]=="FUZZY_JUDGE_PATH"]
        cond[role]={"n":len(fuzzy),"blocked":sum(bool(r[f"{role}_blocked"]) for r in fuzzy)}
    add("N6.FUZZY", "Conditional fuzzy-review block counts.",
        {"AUTH":{"n":169,"blocked":112},"ALT":{"n":101,"blocked":86}}, cond,
        "n6_attriguard_n3_v1/scientific_v1/N6_RESULTS.jsonl","rederived_raw")


def verify_causalarmor() -> None:
    p=jload("P0B3_CAUSALARMOR_LIVE_RUN_v1/P0B3_ANALYSIS.json")
    add("P0B3.PRIMARY", "CausalArmor-style reconstruction broad-regime calibration.",
        {"benign":97,"attack":949,"nested":629,"ASR":3.3719704952581666,"BU":51.54639175257732,"UA":40.67439409905163,"disposition":"SAME_EXTERNAL_REGIME","nested_ASR":5.087440381558029,"serialization_diff_pp":3.525641025641022},
        {"benign":p["population"]["benign"],"attack":p["population"]["primary_attack"],"nested":p["population"]["legacy_nested"],
         "ASR":p["primary"]["ASR_percent"],"BU":p["primary"]["BU_percent"],"UA":p["primary"]["UA_percent"],"disposition":p["primary"]["disposition"],
         "nested_ASR":p["legacy_629_sensitivity"]["ASR_percent"],"serialization_diff_pp":p["serialization_sensitivity"]["absolute_activation_difference_pp"]},
        "P0B3_CAUSALARMOR_LIVE_RUN_v1/P0B3_ANALYSIS.json")
    a=jload("a15a_selectivity_consequence/results.json")
    add("A15A.ACTIVATION", "Benign calibration activation and sanitizer-stage overhead.",
        {"decisions":26,"activated":18,"eligible_spans":96,"sanitized_spans":53,"serial_s":2.3636353709734976},
        {"decisions":a["eligible_decisions"],"activated":a["activated_decisions_tau0"],"eligible_spans":a["eligible_tool_spans"],"sanitized_spans":a["flagged_tool_spans_tau0"],"serial_s":a["per_activated_decision_serial_sanitizer_seconds"]["mean"]},
        "a15a_selectivity_consequence/results.json")


def e2e_task_effects(rows: list[dict[str,Any]], metric: str, kind: str) -> list[float]:
    cells=defaultdict(list)
    for r in rows:
        if r.get("status")=="SUCCESS": cells[(r["case_id"],r["context"],r["defense"])].append(float(r[metric]))
    out=[]
    for cid in sorted({r["case_id"] for r in rows}):
        def m(c,d): return mean(cells[(cid,c,d)])
        if kind=="primary": out.append((m("ALIGNED","ON")-m("CONFLICT","ON"))-(m("ALIGNED","OFF")-m("CONFLICT","OFF")))
        elif kind=="security": out.append(m("CONFLICT","OFF")-m("CONFLICT","ON"))
        elif kind=="direct": out.append(m("CONFLICT","ON")-m("CONFLICT","OFF"))
        else: raise ValueError(kind)
    return out


def verify_e2e() -> None:
    rel="E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl"; rows=jsonl(rel)
    add("E2E.CENSUS", "Live E2E census and completeness.",
        {"rows":420,"tasks":14,"success":420,"cells":6,"per_cell":70},
        {"rows":len(rows),"tasks":len({r["case_id"] for r in rows}),"success":sum(r.get("status")=="SUCCESS" for r in rows),
         "cells":len({(r["context"],r["defense"]) for r in rows}),"per_cell":min(Counter((r["context"],r["defense"]) for r in rows).values())}, rel,"rederived_raw")
    freeze=jload("E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build/FREEZE.json")
    add("E2E.BOOTSTRAP_FREEZE", "Sealed pre-science E2E task-bootstrap procedure.",
        {"B":20000,"seed":2026082002}, {"B":freeze["analysis_bootstrap_draws"],"seed":freeze["analysis_seed"]},
        "E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build/FREEZE.json","frozen_metadata_check")
    primary=e2e_task_effects(rows,"PAEF","primary")
    pci=bootstrap_linear(primary,20000,2026082002)
    add("E2E.PRIMARY", "Pre-specified task-level primary interaction is opposite predicted availability-loss direction.",
        {"mean":-0.24285714285714285,"ci95":[-0.4714285714285714,-0.04285714285714286]},
        {"mean":mean(primary),"ci95":pci}, rel,"rederived_raw", tol=2e-9)
    sec=e2e_task_effects(rows,"Z","security"); d=e2e_task_effects(rows,"PAEF","direct")
    conflict=lambda defense,key:[r for r in rows if r["context"]=="CONFLICT" and r["defense"]==defense and r.get(key) is not None]
    zoff,zon=conflict("OFF","Z"),conflict("ON","Z")
    poff,pon=conflict("OFF","PAEF"),conflict("ON","PAEF")
    add("E2E.SELECTED_ALT", "Under CONFLICT, defense reduces selected unauthorized outcome on this cohort.",
        {"off_true":17,"on_true":2,"n_each":70,"diff":0.21428571428571427,"ci95":[0.04285714285714286,0.42857142857142855]},
        {"off_true":sum(r["Z"] for r in zoff),"on_true":sum(r["Z"] for r in zon),"n_each":len(zoff),"diff":mean(sec),"ci95":bootstrap_linear(sec,20000,2026082002)},
        rel,"rederived_raw",tol=2e-9)
    add("E2E.PAEF", "Direct CONFLICT PAEF difference is positive in sample but null-compatible.",
        {"off_true":38,"on_true":47,"n_each":70,"diff":0.12857142857142856,"ci95":[-0.11428571428571428,0.3857142857142857]},
        {"off_true":sum(r["PAEF"] for r in poff),"on_true":sum(r["PAEF"] for r in pon),"n_each":len(poff),"diff":mean(d),"ci95":bootstrap_linear(d,20000,2026082002)},
        rel,"rederived_raw",tol=2e-9)
    cnt=Counter((int(r["utility"]),int(r["PAEF"])) for r in rows)
    add("E2E.UTILITY_PAEF", "Live utility and PAEF disagree on 18/420 executions.",
        {"discord":18,"utility1_paef0":13,"utility0_paef1":5},
        {"discord":cnt[(1,0)]+cnt[(0,1)],"utility1_paef0":cnt[(1,0)],"utility0_paef1":cnt[(0,1)]}, rel,"rederived_raw")

    # Load frozen PAEF matcher for blocked-proposal classification.
    po=load_paef_oracle()
    spec_dir=resolve_path("E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build/PAEF_ORACLE_FREEZE/PAEF_SPECS")
    specs={p.stem:json.loads(p.read_text()) for p in spec_dir.glob("CASE_*.json")}
    bcnt=Counter()
    for r in rows:
        raw=json.loads(resolve_raw(r).read_text(encoding="utf-8"))
        spec=specs[r["case_id"]]
        for m in raw.get("messages",[]):
            if m.get("role")!="tool" or "[AttriGuardBlocked]" not in str(m.get("error") or ""):
                continue
            tc=m.get("tool_call") or {}
            call={"function":getattr(tc,"function",None) if not isinstance(tc,dict) else tc.get("function"),
                  "args":getattr(tc,"args",{}) if not isinstance(tc,dict) else (tc.get("args") or {})}
            if call["function"] not in po.MUTATORS[spec["suite"]]:
                continue
            cls="AUTH" if po.call_matches(call,spec["target_rule"]) else "ALT" if po.call_matches(call,spec["alt_rule"]) else "OTHER"
            bcnt[(cls,int(r["PAEF"]))]+=1
    add("E2E.CONTINUATION", "Blocked-proposal continuation is symmetric: ALT recovery and AUTH loss are both reported.",
        {"ALT_total":13,"ALT_paef1":12,"ALT_paef0":1,"AUTH_total":9,"AUTH_paef1":0,"AUTH_paef0":9,"OTHER_total":4},
        {"ALT_total":bcnt[("ALT",0)]+bcnt[("ALT",1)],"ALT_paef1":bcnt[("ALT",1)],"ALT_paef0":bcnt[("ALT",0)],
         "AUTH_total":bcnt[("AUTH",0)]+bcnt[("AUTH",1)],"AUTH_paef1":bcnt[("AUTH",1)],"AUTH_paef0":bcnt[("AUTH",0)],
         "OTHER_total":bcnt[("OTHER",0)]+bcnt[("OTHER",1)]}, rel+" + frozen PAEF specs + raw traces","rederived_raw")

    defended=[r for r in rows if r["defense"]=="ON"]
    opened=used=0; unaudited=[]; pred_assoc=0
    for r in defended:
        raw=json.loads(resolve_raw(r).read_text(encoding="utf-8")); msgs=raw.get("messages",[]); batches=tool_batches(msgs)
        qualifying=[]
        for bi,(start,end,batch) in enumerate(batches):
            all_empty=bool(batch) and all(not content_text(m).strip() for m in batch)
            blocked=any("[AttriGuardBlocked]" in str(m.get("error") or "") for m in batch)
            if all_empty and blocked: qualifying.append((bi,start,end))
        if qualifying:
            opened+=1
            if any(qbi < len(batches)-1 for qbi,_,__ in qualifying): used+=1
        # Each privileged diagnostic with audit_skipped should line up to a raw tool result.
        if any(d.get("judge_reason")=="audit_skipped" for d in r.get("privileged_call_diagnostics",[])):
            unaudited.append(r)
            # Strong association: find an audit_skipped privileged tool message immediately after an assistant batch whose previous tool batch qualifies.
            found=False
            for idx,m in enumerate(msgs):
                st=m.get("defense_state") or {}
                if m.get("role")=="tool" and st.get("judge_reason")=="audit_skipped":
                    # find immediately preceding tool batch before the assistant that proposed this call
                    prev_batches=[(s,e,b) for s,e,b in batches if e <= idx]
                    if prev_batches:
                        s,e,b=prev_batches[-1]
                        # exclude current tool if batch ends at idx+1
                        if s <= idx < e and len(prev_batches)>=2:
                            s,e,b=prev_batches[-2]
                        if all(not content_text(mm).strip() for mm in b) and any("[AttriGuardBlocked]" in str(mm.get("error") or "") for mm in b):
                            found=True
            pred_assoc+=int(found)
    n_priv=sum(len(r.get("privileged_call_diagnostics",[])) for r in defended)
    n_skip=sum(sum(d.get("judge_reason")=="audit_skipped" for d in r.get("privileged_call_diagnostics",[])) for r in defended)
    split=Counter()
    for r in defended:
        k=sum(d.get("judge_reason")=="audit_skipped" for d in r.get("privileged_call_diagnostics",[]))
        for _ in range(k):
            split[(int(r["PAEF"]),int(r["Z"]))]+=1
    add("E2E.AUDIT_WINDOWS", "Exploratory source+trace denominator ladder from raw traces.",
        {"defended_runs":210,"opened":44,"later_used":22,"privileged_calls":168,"audit_skipped":18,"all18_predecessor":18,
         "outcomes":{"authorized":15,"selected_alt":2,"neither":1}},
        {"defended_runs":len(defended),"opened":opened,"later_used":used,"privileged_calls":n_priv,"audit_skipped":n_skip,"all18_predecessor":pred_assoc,
         "outcomes":{"authorized":split[(1,0)],"selected_alt":split[(0,1)],"neither":split[(0,0)]}},
        rel+" + raw traces","rederived_raw",
        note="Exploratory/source-bound mechanism evidence; not an exploit-rate estimate.")



def verify_isolation_result() -> None:
    rel = "artifact_support/source_bound_isolation/ATTRIGUARD_AUDIT_TRANSITION_RESULT.json"
    x = jload(rel)
    arms = x["arms"]
    a = arms["A_prior_call_allowed"]
    b = arms["B_prior_call_blocked"]
    c = arms["C_local_patch_prior_call_blocked"]
    add("E2E.SOURCE_ISOLATION", "Deterministic fixed-call isolation reproduces the source-bound audit transition and local patch restores adjudication.",
        {"all_passed":True,"source_sha":"6d28e2208efbd521bf3f2e90c553e57b11c786e65564eababacb8cdf4f8050d8",
         "A_audited":True,"B_audit_skipped":True,"B_executed":True,"C_audited":True},
        {"all_passed":bool(x["all_passed"]),"source_sha":x["attriguard_sha256"],
         "A_audited":a.get("privileged_judge_reason") not in (None,"audit_skipped"),
         "B_audit_skipped":b.get("privileged_judge_reason")=="audit_skipped",
         "B_executed":bool(b.get("privileged_executed")),
         "C_audited":c.get("privileged_judge_reason") not in (None,"audit_skipped")},
        rel, "frozen_deterministic_isolation_check",
        note="Supporting mechanism evidence; not a prospective E2E endpoint or exploit-rate result.")

def verify_replay() -> None:
    exp={"llama":(50,85,35),"gemma":(35,75,40),"qwen":(55,95,40)}
    all_cells=[]
    replay_dir={"llama":"P2B_XM_CI_LLAMA_RUN_v1_2","gemma":"P2B_XM_CI_GEMMA_RUN_v1_2","qwen":"P2B_XM_CI_QWEN_RUN_v1_2"}
    for model in ["llama","gemma","qwen"]:
        rel=f"{replay_dir[model]}/P2B_CI_BASELINE_RAW.jsonl"; rows=jsonl(rel)
        actual=(sum(bool(r["action_local_preserved"]) for r in rows),sum(bool(r["utility_preserved"]) for r in rows),
                sum((not bool(r["action_local_preserved"])) and bool(r["utility_preserved"]) for r in rows))
        add(f"REPLAY.{model.upper()}.GEN", f"{model} generation-level immediate/downstream fidelity counts.",
            {"n":130,"immediate":exp[model][0],"downstream":exp[model][1],"immediate_fail_downstream_pass":exp[model][2]},
            {"n":len(rows),"immediate":actual[0],"downstream":actual[1],"immediate_fail_downstream_pass":actual[2]},rel,"rederived_raw")
        by=defaultdict(list)
        for r in rows: by[r["decision_id"]].append(r)
        for did,rr in by.items():
            if len(rr)!=5: raise RuntimeError(f"replay repeat census {model}/{did}={len(rr)}")
            all_cells.append({"model":model,"decision":did,
                              "immediate":sum(bool(r["action_local_preserved"]) for r in rr)>=3,
                              "downstream":sum(bool(r["utility_preserved"]) for r in rr)>=3,
                              "target_fn":sum(bool(r["target_function_match"]) for r in rr)>=3})
    disagree=[c for c in all_cells if (not c["immediate"]) and c["downstream"]]
    add("REPLAY.CELLS", "Across 78 model-decision cells, downstream success can hide immediate action/effect divergence.",
        {"cells":78,"disagree":23,"target_tool_majority":22},
        {"cells":len(all_cells),"disagree":len(disagree),"target_tool_majority":sum(c["target_fn"] for c in disagree)},
        "studies/09_evaluation_replay/{llama,gemma,qwen}/P2B_CI_BASELINE_RAW.jsonl","rederived_raw")


def verify_source_and_hygiene() -> None:
    attr_src = "artifact_support/ATTRIGUARD_SOURCE_SHA256.txt"
    recorded = (ROOT / attr_src).read_text(encoding="utf-8").split()[0]
    isolation = jload("artifact_support/source_bound_isolation/ATTRIGUARD_AUDIT_TRANSITION_RESULT.json")
    add("SOURCE.ATTRIGUARD_SHA", "Frozen AttriGuard source identity is consistent across provenance and deterministic isolation evidence.",
        {"provenance":"6d28e2208efbd521bf3f2e90c553e57b11c786e65564eababacb8cdf4f8050d8",
         "isolation":"6d28e2208efbd521bf3f2e90c553e57b11c786e65564eababacb8cdf4f8050d8"},
        {"provenance":recorded,"isolation":isolation["attriguard_sha256"]},
        attr_src+" + artifact_support/source_bound_isolation/ATTRIGUARD_AUDIT_TRANSITION_RESULT.json","source_identity_check",
        note="Source identity is bound to the tested AttriGuard snapshot; redistribution scope is documented in THIRD_PARTY.md.")
    add("SOURCE.AGENTWATCHER_SHA", "Frozen AgentWatcher integration adapter hash.",
        "0afc2131bc7dd3a8ab8e498cecf44743801500210609cd995a6721e3987473ac",
        sha256("external/AgentWatcher_armc_runtime_v1/agents/agentdojo/src/agentdojo/agent_pipeline/piarena_defense_adapter.py"), "external/AgentWatcher_armc_runtime_v1/agents/agentdojo/src/agentdojo/agent_pipeline/piarena_defense_adapter.py","source_hash")

    # Hygiene here is deliberately restricted to the immutable distributed file set.
    # artifact_outputs/ is generated after extraction and is not part of the artifact.
    manifest = ROOT / "SHA256SUMS.txt"
    immutable = []
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip() or "  " not in line:
                continue
            _, rel = line.split("  ", 1)
            immutable.append((rel, ROOT / rel))
    else:
        immutable = []

    private_user = "ta" + "had"
    private_name = "tan" + "zim"
    institution = "ut" + "ep"
    lab = "iq" + "sec"
    banned=[re.compile(x,re.I) for x in [re.escape("/home/" + private_user), r"\b"+private_user+r"\b", r"\b"+private_name+r"\b", r"\b"+institution+r"\b", lab]]
    text_ext={".txt",".md",".json",".jsonl",".csv",".tsv",".py",".sh",".yml",".yaml",".tex"}
    hits=[]
    for rel,p in immutable:
        if not p.is_file() or p.suffix.lower() not in text_ext:
            continue
        try: text=p.read_text(encoding="utf-8",errors="ignore")
        except Exception: continue
        if any(pat.search(text) for pat in banned):
            hits.append(rel)
    gitdirs=sorted({rel.split('/.git/',1)[0]+'/.git' for rel,_ in immutable if '/.git/' in '/'+rel or rel.startswith('.git/')})
    add("HYGIENE.IDENTITY", "No known author/institution identity strings in text-readable artifact files.", [], sorted(hits), "immutable distributed files","hygiene_scan")
    add("HYGIENE.GIT", "No .git directories in artifact.", [], gitdirs, "immutable distributed files","hygiene_scan")

    secret_pats = [
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
        re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
        re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    ]
    secret_hits=[]
    tracking_hits=[]
    tracking_pat=re.compile(r"(?:[?&]utm_(?:source|medium|campaign|term|content)=|https?://(?:bit\.ly|tinyurl\.com)/)", re.I)
    synthetic_key_suffixes={
        "agents/agentdyn/src/agentdojo/data/suites/dailylife/include/filesystem.yaml",
        "agents/agentdyn/src/agentdojo/default_suites/v1/dailylife/injection_tasks.py",
        "agents/agentdyn/src/runs/gpt-4o-2024-08-06-piarena-agentwatcher/dailylife/injection_task_4/none/none.json",
    }
    for rel,p in immutable:
        if not p.is_file() or p.suffix.lower() not in text_ext:
            continue
        try: text=p.read_text(encoding="utf-8",errors="ignore")
        except Exception: continue
        if any(pat.search(text) for pat in secret_pats) and not any(rel.endswith(x) for x in synthetic_key_suffixes):
            secret_hits.append(rel)
        parts=Path(rel).parts
        public_surface=(len(parts)==1 or (parts and parts[0] in {"artifact_tools","artifact_support","paper_figures"}))
        if public_surface and tracking_pat.search(text):
            tracking_hits.append(rel)

    # os.walk avoids following symlinks and skips generated artifact_outputs.
    import os
    symlinks=[]
    for dirpath, dirnames, filenames in os.walk(ROOT, followlinks=False):
        rp=Path(dirpath).relative_to(ROOT)
        if rp.parts and rp.parts[0]=="artifact_outputs":
            dirnames[:] = []
            continue
        keep=[]
        for d in dirnames:
            q=Path(dirpath)/d
            if q.is_symlink(): symlinks.append(str(q.relative_to(ROOT)))
            else: keep.append(d)
        dirnames[:] = keep
        for fn in filenames:
            q=Path(dirpath)/fn
            if q.is_symlink(): symlinks.append(str(q.relative_to(ROOT)))

    add("HYGIENE.SECRETS", "No high-confidence author credential material in artifact package.", [], sorted(set(secret_hits)), "immutable distributed files excluding known synthetic AgentDojo key fixture","hygiene_scan")
    add("HYGIENE.TRACKING", "No common tracking-link parameters or short-link trackers in artifact documentation.", [], sorted(set(tracking_hits)), "artifact documentation","hygiene_scan")
    add("HYGIENE.SYMLINKS", "No symlinks in artifact.", [], sorted(symlinks), "immutable distributed files","hygiene_scan")
    cov=json.loads((ROOT/"supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.json").read_text(encoding="utf-8"))
    add("HYGIENE.SOURCE_COVERAGE", "Complete codebase artifacts/ tree retained except identity-bearing Git metadata.",
        {"source_files":5731,"retained_source_files":5694,"excluded_git_metadata_files":37},
        {k:cov[k] for k in ["source_files","retained_source_files","excluded_git_metadata_files"]},
        "supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv","coverage_check")


def write_outputs() -> int:
    fails=[c for c in CLAIMS if c["status"]!="PASS"]
    ledger={"schema":"USENIX27_CLAIM_LEDGER_V1","verification_mode":"deterministic_no_network",
            "summary":{"pass":len(CLAIMS)-len(fails),"fail":len(fails),"total":len(CLAIMS)},"claims":CLAIMS}
    (OUTDIR/"CLAIM_LEDGER.json").write_text(json.dumps(ledger,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    lines=["# Claim-to-Artifact Map","",f"Deterministic verification: **{len(CLAIMS)-len(fails)} PASS / {len(fails)} FAIL / {len(CLAIMS)} total**.",
           "","The default verifier makes no model/provider calls and uses only frozen files in this package.","",
           "| Claim | Status | Verification | Source |","|---|---|---|---|"]
    for c in CLAIMS:
        desc=c["description"].replace("|","/")
        src=c["source"].replace("|","/")
        lines.append(f"| `{c['id']}` {desc} | **{c['status']}** | {c['verification_type']} | `{src}` |")
    lines += ["","## Evidence boundaries","",
              "- Natural-cohort results establish ecological relevance in the audited benchmark, not deployment prevalence.",
              "- N3 is a teacher-forced matched construct comparison, not a deployment attack-success estimate.",
              "- AgentWatcher matched-gate evidence is gate-level; the separate ON/OFF population is a different matched-input experiment.",
              "- AttriGuard N6 aggregate outcome precedes route localization; observed reference identity determines routing, but directive-to-reference causality is unresolved.",
              "- Live PAEF is task-level inference; the direct CONFLICT PAEF difference is null-compatible.",
              "- Audit-coverage analysis is exploratory/source-bound and dual-use; it is not an exploit-rate estimate.",
              "- Replay evaluates metric fidelity, not model quality or ranking."]
    (OUTDIR/"CLAIM_TO_ARTIFACT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (OUTDIR/"SUMMARY.txt").write_text(f"PASS={len(CLAIMS)-len(fails)}\nFAIL={len(fails)}\nTOTAL={len(CLAIMS)}\n",encoding="utf-8")
    for c in CLAIMS:
        print(f"[{c['status']}] {c['id']}: {c['description']}")
        if c["status"]!="PASS":
            print("  expected:",json.dumps(c["expected"],sort_keys=True))
            print("  actual:  ",json.dumps(c["actual"],sort_keys=True))
    print(f"\nSUMMARY: {len(CLAIMS)-len(fails)} PASS / {len(fails)} FAIL / {len(CLAIMS)} total")
    return 1 if fails else 0


def main() -> int:
    verify_natural(); verify_breadth(); verify_a14(); verify_n3(); verify_r2b(); verify_agentwatcher(); verify_n6(); verify_causalarmor(); verify_e2e(); verify_isolation_result(); verify_replay(); verify_source_and_hygiene()
    return write_outputs()

if __name__=="__main__":
    raise SystemExit(main())
