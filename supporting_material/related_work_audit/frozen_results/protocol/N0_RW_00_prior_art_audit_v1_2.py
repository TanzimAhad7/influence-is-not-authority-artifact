#!/usr/bin/env python3
"""
N0-RW v1.2: early prior-art collision audit for the authorization-specificity /
property-preserving A14->N3 framing.

ZERO LLM/MODEL CALLS.
Uses only public scholarly metadata APIs (arXiv + OpenAlex).

This script DOES NOT decide novelty. It freezes and executes a reproducible
retrieval/screening protocol, preserves raw API responses, separates the project's
locked novelty-cutoff policy from later concurrent-awareness work, and emits manual
full-text adjudication sheets.

Critical policy encoded here (from the canonical dossier):
  * arXiv/preprint novelty-killing eligibility: first public date <= 2026-07-15
  * peer-reviewed accepted/published novelty-killing eligibility: formal acceptance /
    publication date <= 2026-07-31 (MANUAL verification required)
  * later/current work through 2026-08-12 is still retrieved for disclosure and
    collision awareness, but must not automatically kill novelty under the locked
    internal priority policy.

Recommended author workflow:
  python3 N0_RW_00_prior_art_audit_v1_2.py --freeze \
      --out N0_RW_AUTHOR_RUN_v1_2 --runner RUN_N0_RW_v1_2.sh
  python3 N0_RW_00_prior_art_audit_v1_2.py --run \
      --out N0_RW_AUTHOR_RUN_v1_2 --runner RUN_N0_RW_v1_2.sh

Run only in a NEW output directory. If a retrieval attempt aborts, preserve that
attempt as provenance and start a fresh output directory for the next attempt.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

PROTOCOL = "N0-RW-v1.2"
CURRENT_AWARENESS_CUTOFF_DATE = "2026-08-12"
SEARCH_MIN_DATE = "2022-01-01"
LOCKED_PREPRINT_CUTOFF_DATE = "2026-07-15"
LOCKED_PEER_REVIEW_CUTOFF_DATE = "2026-07-31"
USER_AGENT = "N0-RW-USENIX-prior-art-audit/1.1"

ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

# Exact known neighbors. Include both cutoff-eligible work and known post-cutoff
# concurrent work so the audit cannot silently omit already-known collisions.
SEED_ARXIV_IDS = [
    "2602.07918",  # CausalArmor
    "2603.10749",  # AttriGuard
    "2602.22724",  # AgentSentry
    "2605.11039",  # PACT / Granularity Mismatch
    "2605.26497",  # AuthGraph
    "2606.08275",  # Causal Agent Replay
    "2607.20827",  # Liao: Auditing Provenance Sensitivity... (post preprint cutoff)
    "2603.19469",  # Framework for Formalizing LLM Agent Security
    "2503.15547",  # Prompt Flow Integrity
    "2606.13884",  # Risk-Aware Causal Gating / Capability Minimization
    "2605.03378",  # ARGUS
    "2605.17634",  # AI Agents May Always Fall for Prompt Injections
    "2607.01236",  # provenance-analysis agent security (cutoff-eligible under 2026-07-15 policy)
    "2604.04978",  # permission-gate stress-test adjacent
    "2607.06000",  # CXI (cutoff-eligible under 2026-07-15 policy)
    "2607.10487",  # Commit-Time Authorization (cutoff-eligible under 2026-07-15 policy)
    "2607.27267",  # FAVA (known post-cutoff concurrent)
]

# arXiv has an explicit Boolean query grammar. Keep these as valid structured
# expressions rather than sending natural-language strings after a single all: prefix.
ARXIV_CORE_QUERIES = [
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:authorization OR all:authority OR all:permission) AND (all:provenance OR all:"prompt injection" OR all:guardrail)',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:"source authority" OR all:"source trust" OR all:provenance) AND (all:action OR all:"tool call")',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:"causal attribution" OR all:counterfactual OR all:ablation) AND (all:"prompt injection" OR all:guardrail OR all:security)',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:"task-relevant evidence" OR all:"authorized evidence" OR all:"untrusted evidence" OR all:"external evidence") AND (all:control OR all:authorization OR all:guardrail)',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:"negative control" OR all:"positive control" OR all:invariance OR all:metamorphic OR all:"stress test") AND (all:security OR all:guardrail OR all:authorization)',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:"construct validity" OR all:specificity OR all:"property preserving" OR all:"property-preserving") AND (all:security OR all:guardrail OR all:authorization)',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:"argument role" OR all:"argument-level" OR all:"parameter source") AND (all:provenance OR all:authority OR all:authorization)',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:"least privilege" OR all:capability OR all:permission) AND (all:causal OR all:provenance OR all:"prompt injection")',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND all:"indirect prompt injection" AND (all:authorization OR all:authority OR all:provenance)',
    '(all:"LLM agent" OR all:"LLM agents" OR all:"large language model agent" OR all:"large language model agents") AND (all:audit OR all:evaluation OR all:"stress test") AND (all:guardrail OR all:defense) AND (all:authorization OR all:authority OR all:provenance)',
]

# OpenAlex search supports natural/Boolean text search. Words without Boolean operators
# are ANDed; explicit alternatives are used where recall benefits.
OPENALEX_CORE_QUERIES = [
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND (authorization OR authority) AND (provenance OR "prompt injection" OR guardrail)',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND ("source authority" OR "source trust" OR provenance) AND (action OR "tool call")',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND ("causal attribution" OR counterfactual OR ablation) AND ("prompt injection" OR guardrail)',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND ("authorized evidence" OR "task relevant evidence" OR "untrusted evidence") AND (control OR authorization)',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND ("negative control" OR "positive control" OR invariance OR metamorphic OR "stress test") AND security',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND ("construct validity" OR specificity OR "property preserving") AND (security OR guardrail)',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND ("argument level" OR "parameter source" OR "argument role") AND (provenance OR authorization)',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND ("least privilege" OR capability OR permission) AND (causal OR provenance OR "prompt injection")',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND "indirect prompt injection" AND (authorization OR authority OR provenance)',
    '("LLM agent" OR "LLM agents" OR "large language model agent" OR "large language model agents") AND (audit OR evaluation OR "stress test") AND guardrail AND (authorization OR authority OR provenance)',
]

KEYWORD_GROUPS = {
    "authorization": ["authoriz", "authority", "permission", "privilege", "capability"],
    "provenance": ["provenance", "source authority", "source trust", "origin", "data flow"],
    "agent_security": ["agent", "tool call", "tool invocation", "prompt injection", "guardrail", "defense"],
    "causal": ["causal", "counterfactual", "ablation", "attribution", "re-execution", "replay"],
    "testing": ["stress test", "audit", "negative control", "positive control", "metamorphic", "invariance", "construct validity", "specificity"],
    "evidence_control": ["evidence", "control", "task-relevant", "trusted", "untrusted", "relevance"],
}

SCREENING_MANUAL_COLUMNS = [
    "screen_title_abstract_YN",
    "potentially_relevant_YN",
    "full_text_priority_HIGH_MEDIUM_LOW_NONE",
    "screening_notes",
]

FULLTEXT_MANUAL_COLUMNS = [
    "full_text_read_YN",
    "agent_or_guardrail_scope_YN",
    "distinguishes_authority_from_relevance_or_provenance_YN",
    "property_preserving_negative_control_YN",
    "holds_authorization_fixed_in_negative_control_YN",
    "holds_exact_action_or_security_effect_fixed_YN",
    "audits_guardrail_signal_or_guardrail_verdict_YN",
    "matched_property_changing_positive_control_YN",
    "causal_attribution_proxy_or_guardrail_YN",
    "explicit_construct_validity_or_specificity_interpretation_YN",
    "same_core_combination_as_N3_YN",
    "collision_level_NONE_ADJACENT_PARTIAL_MATERIAL",
    # Cutoff status MUST be manually adjudicated. A post-2026-07-15 preprint may still
    # be eligible if formal peer-reviewed acceptance/publication occurred by 2026-07-31.
    "peer_reviewed_accepted_or_published_YN",
    "formal_acceptance_or_publication_date",
    "locked_cutoff_status_ELIGIBLE_CONCURRENT_UNCLEAR",
    "can_block_N3_under_locked_policy_YN",
    "submission_disclosure_needed_YN",
    "supporting_section_or_figure",
    "adjudication_notes",
]


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def normalize_title(s: str) -> str:
    s = normalize_space(s).lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return normalize_space(s)


def normalize_doi(s: str) -> str:
    s = normalize_space(s).lower()
    s = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", s)
    return s.strip()


def normalize_arxiv_id(s: str) -> str:
    s = normalize_space(s)
    m = re.search(r"(?:arxiv:|/abs/|/pdf/)?(\d{4}\.\d{4,5})(?:v\d+)?", s, flags=re.I)
    return m.group(1) if m else ""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha(obj: object) -> str:
    b = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def parse_iso_date(s: str) -> Optional[str]:
    s = normalize_space(s)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s
    return None


def http_get(
    url: str,
    *,
    timeout: int = 75,
    retries: int = 5,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Tuple[bytes, Dict[str, str]]:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    if extra_headers:
        headers.update(extra_headers)

    last: Optional[BaseException] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                meta = {k: v for k, v in r.headers.items()}
                meta["http_status"] = str(getattr(r, "status", 200))
                return body, meta
        except urllib.error.HTTPError as e:
            last = e
            # Retry only transient failures / rate limiting. Do not waste time retrying
            # deterministic request errors such as 400/401/403/404.
            if e.code == 429 or 500 <= e.code <= 599:
                retry_after = e.headers.get("Retry-After") if e.headers else None
                try:
                    delay = float(retry_after) if retry_after else min(30.0, 2.0 ** attempt)
                except ValueError:
                    delay = min(30.0, 2.0 ** attempt)
                if attempt + 1 < retries:
                    time.sleep(delay)
                    continue
            break
        except Exception as e:  # network/DNS/timeout
            last = e
            if attempt + 1 < retries:
                time.sleep(min(30.0, 2.0 ** attempt))
                continue
            break
    raise RuntimeError(f"GET failed after {retries} attempts: {url}\n{last}")


def parse_arxiv_atom(data: bytes, discovery_tag: str) -> Tuple[List[Dict], Dict[str, int]]:
    root = ET.fromstring(data)
    total_text = root.findtext("opensearch:totalResults", default="0", namespaces=ARXIV_NS)
    items_text = root.findtext("opensearch:itemsPerPage", default="0", namespaces=ARXIV_NS)
    try:
        total_results = int(total_text)
    except ValueError:
        total_results = -1
    try:
        items_per_page = int(items_text)
    except ValueError:
        items_per_page = -1

    out: List[Dict] = []
    for e in root.findall("atom:entry", ARXIV_NS):
        title = normalize_space(e.findtext("atom:title", default="", namespaces=ARXIV_NS))
        entry_id = normalize_space(e.findtext("atom:id", default="", namespaces=ARXIV_NS))
        if title.lower() == "error" or "/api/errors#" in entry_id:
            summary = normalize_space(e.findtext("atom:summary", default="", namespaces=ARXIV_NS))
            raise RuntimeError(f"arXiv API returned an error entry for {discovery_tag}: {summary or entry_id}")

        abstract = normalize_space(e.findtext("atom:summary", default="", namespaces=ARXIV_NS))
        published = normalize_space(e.findtext("atom:published", default="", namespaces=ARXIV_NS))
        updated = normalize_space(e.findtext("atom:updated", default="", namespaces=ARXIV_NS))
        authors = [
            normalize_space(a.findtext("atom:name", default="", namespaces=ARXIV_NS))
            for a in e.findall("atom:author", ARXIV_NS)
        ]
        arxiv_id = normalize_arxiv_id(entry_id)
        if not arxiv_id:
            raise RuntimeError(f"Could not parse arXiv id from entry id: {entry_id}")

        doi = ""
        for child in e:
            if child.tag.endswith("}doi") and child.text:
                doi = normalize_doi(child.text)
                break

        out.append({
            "title": title,
            "normalized_title": normalize_title(title),
            "abstract": abstract,
            "arxiv_first_public_date": published[:10],
            "arxiv_updated_date": updated[:10],
            "openalex_publication_date": "",
            "authors": "; ".join(a for a in authors if a),
            "arxiv_id": arxiv_id,
            "doi": doi,
            "openalex_id": "",
            "landing_url": entry_id,
            "primary_url": entry_id,
            "source": "arxiv",
            "discovered_by": discovery_tag,
            "openalex_relevance_score": "",
        })
    return out, {"total_results": total_results, "items_per_page": items_per_page, "entries_parsed": len(out)}


def openalex_abstract(inv: Optional[Dict]) -> str:
    if not inv:
        return ""
    pairs: List[Tuple[int, str]] = []
    for word, positions in inv.items():
        if not isinstance(positions, list):
            continue
        for p in positions:
            if isinstance(p, int):
                pairs.append((p, word))
    pairs.sort()
    return normalize_space(" ".join(word for _, word in pairs))


def parse_openalex(data: bytes, discovery_tag: str) -> Tuple[List[Dict], Dict[str, object]]:
    obj = json.loads(data.decode("utf-8"))
    if not isinstance(obj, dict) or "results" not in obj:
        raise RuntimeError(f"Unexpected OpenAlex response envelope for {discovery_tag}")

    out: List[Dict] = []
    for w in obj.get("results") or []:
        title = normalize_space(w.get("title") or w.get("display_name") or "")
        if not title:
            continue
        ids = w.get("ids") or {}
        arxiv_id = normalize_arxiv_id(ids.get("arxiv") or "")
        doi = normalize_doi(ids.get("doi") or w.get("doi") or "")
        oa_id = normalize_space(w.get("id") or ids.get("openalex") or "")

        authors: List[str] = []
        for a in w.get("authorships") or []:
            nm = normalize_space(((a.get("author") or {}).get("display_name") or ""))
            if nm:
                authors.append(nm)

        primary_location = w.get("primary_location") or {}
        primary_url = normalize_space(primary_location.get("landing_page_url") or "")
        if not primary_url:
            best_oa = w.get("best_oa_location") or {}
            primary_url = normalize_space(best_oa.get("landing_page_url") or "")
        landing = primary_url or normalize_space(ids.get("doi") or "") or oa_id

        relevance = w.get("relevance_score")
        relevance_s = "" if relevance is None else str(relevance)

        out.append({
            "title": title,
            "normalized_title": normalize_title(title),
            "abstract": openalex_abstract(w.get("abstract_inverted_index")),
            "arxiv_first_public_date": "",
            "arxiv_updated_date": "",
            "openalex_publication_date": normalize_space(w.get("publication_date") or ""),
            "authors": "; ".join(authors),
            "arxiv_id": arxiv_id,
            "doi": doi,
            "openalex_id": oa_id,
            "landing_url": landing,
            "primary_url": primary_url,
            "source": "openalex",
            "discovered_by": discovery_tag,
            "openalex_relevance_score": relevance_s,
        })

    meta = obj.get("meta") or {}
    return out, {
        "count": meta.get("count"),
        "page": meta.get("page"),
        "per_page": meta.get("per_page"),
        "cost_usd": meta.get("cost_usd"),
        "entries_parsed": len(out),
    }


def triage_score(row: Dict) -> Tuple[int, str]:
    text = (row.get("title", "") + " " + row.get("abstract", "")).lower()
    hit_groups: List[str] = []
    for group, terms in KEYWORD_GROUPS.items():
        if any(term in text for term in terms):
            hit_groups.append(group)
    return len(hit_groups), ";".join(hit_groups)


def title_core_hit(row: Dict) -> bool:
    t = row.get("title", "").lower()
    return any(x in t for x in [
        "authorization", "authority", "provenance", "prompt injection", "guardrail",
        "causal attribution", "permission", "privilege", "security", "stress-test", "stress test",
    ])


def provisional_timing_bucket(row: Dict) -> str:
    arxiv_date = parse_iso_date(row.get("arxiv_first_public_date", ""))
    oa_date = parse_iso_date(row.get("openalex_publication_date", ""))
    if arxiv_date:
        if arxiv_date <= LOCKED_PREPRINT_CUTOFF_DATE:
            return "PREPRINT_DATE_ELIGIBLE;PEER_REVIEW_STATUS_STILL_MANUAL"
        return "POST_PREPRINT_CUTOFF_CONCURRENT_UNLESS_PEER_REVIEW_ELIGIBLE"
    if oa_date:
        if oa_date <= LOCKED_PEER_REVIEW_CUTOFF_DATE:
            return "NO_ARXIV_DATE;PEER_REVIEW_ELIGIBILITY_MANUAL"
        return "CURRENT_AWARENESS_ONLY_BY_METADATA_DATE"
    return "DATE_UNCLEAR_MANUAL_REVIEW_REQUIRED"


def config_obj() -> Dict:
    return {
        "protocol": PROTOCOL,
        "purpose": "early collision audit before N3 freeze; not final P7 and not an automatic novelty verdict",
        "current_awareness_cutoff_date": CURRENT_AWARENESS_CUTOFF_DATE,
        "search_min_date": SEARCH_MIN_DATE,
        "locked_cutoff_policy": {
            "preprint_first_public_date_on_or_before": LOCKED_PREPRINT_CUTOFF_DATE,
            "peer_reviewed_formal_acceptance_or_publication_on_or_before": LOCKED_PEER_REVIEW_CUTOFF_DATE,
            "post_preprint_cutoff_work": "concurrent awareness unless manually established peer-reviewed eligibility under locked policy",
            "submission_hygiene": "all known materially overlapping work still requires disclosure/related-work consideration",
        },
        "seed_arxiv_ids": SEED_ARXIV_IDS,
        "arxiv_core_queries": ARXIV_CORE_QUERIES,
        "openalex_core_queries": OPENALEX_CORE_QUERIES,
        "retrieval": {
            "arxiv_seed_batch": 1,
            "arxiv_per_query_relevance": 100,
            "arxiv_per_query_recent": 50,
            "openalex_per_query_relevance": 100,
            "openalex_per_query_recent": 100,
            "arxiv_sort_modes": ["relevance", "submittedDate:descending"],
            "openalex_sort_modes": ["relevance_score:desc", "publication_date:desc,relevance_score:desc"],
            "strict_fetch_completeness": True,
            "strict_seed_recovery": True,
            "scientific_model_calls": 0,
        },
        "manual_collision_rule": {
            "material_collision_requires_full_text_review": True,
            "focus_combination": [
                "LLM/tool-agent security or guardrail setting",
                "authorization distinguished from mere relevance/provenance/trust",
                "property-preserving negative control with authorization held fixed",
                "exact action and/or security-relevant effect held fixed where applicable",
                "guardrail observable or guardrail verdict audited (not only agent action selection)",
                "matched property-changing positive control contrasting authorized evidence dependence with unauthorized control",
                "explicit construct-validity/authorization-specificity interpretation",
            ],
            "automatic_keyword_scores_are_screening_only": True,
            "post_cutoff_concurrent_work_cannot_automatically_block_N3_under_locked_internal_policy": True,
        },
    }


def expected_retrieval_job_count() -> int:
    return 1 + 2 * len(ARXIV_CORE_QUERIES) + 2 * len(OPENALEX_CORE_QUERIES)


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_freeze(outdir: Path, script_path: Path, runner_path: Optional[Path]) -> None:
    if outdir.exists():
        raise SystemExit(f"STOP: output path already exists; use a new clean directory: {outdir}")
    outdir.mkdir(parents=True, exist_ok=False)
    protocol_dir = outdir / "protocol"
    protocol_dir.mkdir()

    cfg = config_obj()
    script_sha = sha256_file(script_path)
    shutil.copy2(script_path, protocol_dir / script_path.name)

    runner_sha = ""
    runner_name = ""
    if runner_path is not None:
        if not runner_path.is_file():
            raise SystemExit(f"STOP: runner not found: {runner_path}")
        runner_sha = sha256_file(runner_path)
        runner_name = runner_path.name
        shutil.copy2(runner_path, protocol_dir / runner_name)

    write_json(outdir / "N0_RW_PLAN_PREVIEW.json", cfg)
    freeze = {
        "created_utc": now_utc(),
        "protocol": PROTOCOL,
        "script_path": script_path.name,
        "script_sha256": script_sha,
        "runner_path": runner_name,
        "runner_sha256": runner_sha,
        "config_sha256": canonical_json_sha(cfg),
        "config": cfg,
        "expected_retrieval_jobs": expected_retrieval_job_count(),
        "scientific_model_calls": 0,
        "note": "Freeze records retrieval/screening protocol only. Novelty/collision status requires manual full-text adjudication and locked-cutoff classification.",
    }
    write_json(outdir / "N0_RW_FREEZE.json", freeze)

    print(f"N0-RW FREEZE PASS: {outdir / 'N0_RW_FREEZE.json'}")
    print(f"protocol={PROTOCOL}")
    print(f"script_sha256={script_sha}")
    if runner_sha:
        print(f"runner_sha256={runner_sha}")
    print(f"config_sha256={freeze['config_sha256']}")
    print(f"expected_retrieval_jobs={freeze['expected_retrieval_jobs']}")


def verify_freeze(outdir: Path, script_path: Path, runner_path: Optional[Path]) -> Dict:
    freeze_path = outdir / "N0_RW_FREEZE.json"
    if not freeze_path.exists():
        raise SystemExit("STOP: no N0_RW_FREEZE.json. Run --freeze first.")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))

    if freeze.get("protocol") != PROTOCOL:
        raise SystemExit(f"STOP: protocol mismatch: freeze={freeze.get('protocol')} current={PROTOCOL}")
    if sha256_file(script_path) != freeze.get("script_sha256"):
        raise SystemExit("STOP: science retrieval script changed after freeze")
    if canonical_json_sha(config_obj()) != freeze.get("config_sha256"):
        raise SystemExit("STOP: frozen config changed after freeze")

    frozen_script_copy = outdir / "protocol" / freeze["script_path"]
    if not frozen_script_copy.exists() or sha256_file(frozen_script_copy) != freeze.get("script_sha256"):
        raise SystemExit("STOP: frozen protocol copy of script is missing or hash-mismatched")

    frozen_runner_sha = freeze.get("runner_sha256") or ""
    if frozen_runner_sha:
        if runner_path is None:
            raise SystemExit("STOP: freeze includes runner hash but --runner was not supplied to --run")
        if sha256_file(runner_path) != frozen_runner_sha:
            raise SystemExit("STOP: runner changed after freeze")
        frozen_runner_copy = outdir / "protocol" / freeze["runner_path"]
        if not frozen_runner_copy.exists() or sha256_file(frozen_runner_copy) != frozen_runner_sha:
            raise SystemExit("STOP: frozen protocol copy of runner is missing or hash-mismatched")

    return freeze


def assert_clean_pre_run(outdir: Path) -> None:
    allowed = {
        "N0_RW_FREEZE.json",
        "N0_RW_PLAN_PREVIEW.json",
        "protocol",
    }
    extras = sorted(p.name for p in outdir.iterdir() if p.name not in allowed)
    if extras:
        raise SystemExit(
            "STOP: output directory contains post-freeze/partial-run material. "
            "Preserve it as provenance and start a NEW output directory. Extra entries: "
            + ", ".join(extras)
        )


def date_in_awareness_window(row: Dict) -> bool:
    candidates = [
        parse_iso_date(row.get("arxiv_first_public_date", "")),
        parse_iso_date(row.get("openalex_publication_date", "")),
    ]
    known = [d for d in candidates if d]
    if not known:
        return True  # retain uncertain dates for manual review
    earliest = min(known)
    return SEARCH_MIN_DATE <= earliest <= CURRENT_AWARENESS_CUTOFF_DATE


def better_value(current: str, incoming: str, *, prefer_longer: bool = False) -> str:
    current = current or ""
    incoming = incoming or ""
    if not current:
        return incoming
    if not incoming:
        return current
    if prefer_longer and len(incoming) > len(current):
        return incoming
    return current


def _author_tokens(s: str) -> Set[str]:
    # Conservative title-dedup aid. We only need enough normalization to avoid
    # collapsing two genuinely different works with an identical title.
    toks: Set[str] = set()
    for name in (s or "").split(";"):
        parts = re.findall(r"[a-z0-9]+", name.lower())
        if parts:
            toks.add(parts[-1])
    return toks


def _title_merge_compatible(group: Dict, row: Dict) -> bool:
    # Explicit conflicting stable identifiers mean "do not title-merge".
    ga, ra = group.get("arxiv_id", ""), row.get("arxiv_id", "")
    gd, rd = normalize_doi(group.get("doi", "")), normalize_doi(row.get("doi", ""))
    if ga and ra and ga != ra:
        return False
    if gd and rd and gd != rd:
        return False

    # If both sides have author metadata, require at least one surname token in
    # common before using title as a bridge. Missing author metadata is allowed
    # because arXiv/OpenAlex occasionally omit it in one source.
    g_auth = _author_tokens(group.get("authors", ""))
    r_auth = _author_tokens(row.get("authors", ""))
    if g_auth and r_auth and not (g_auth & r_auth):
        return False
    return True


def merge_rows(rows: Sequence[Dict], seed_ids: Set[str]) -> List[Dict]:
    # Deduplicate by stable identifiers first. Exact normalized title is only a
    # conservative fallback bridge and is never allowed to override conflicting
    # arXiv IDs / DOIs. False duplicate retention is preferable to false merging.
    groups: List[Dict] = []
    stable_to_idx: Dict[Tuple[str, str], int] = {}
    title_to_idxs: Dict[str, List[int]] = {}

    def stable_keys(r: Dict) -> List[Tuple[str, str]]:
        keys: List[Tuple[str, str]] = []
        if r.get("arxiv_id"):
            keys.append(("arxiv", r["arxiv_id"]))
        if r.get("doi"):
            keys.append(("doi", normalize_doi(r["doi"])))
        if r.get("openalex_id"):
            keys.append(("openalex", r["openalex_id"]))
        return keys

    for raw in rows:
        if not raw.get("normalized_title") or not date_in_awareness_window(raw):
            continue

        skeys = stable_keys(raw)
        stable_matches = {stable_to_idx[k] for k in skeys if k in stable_to_idx}
        if len(stable_matches) > 1:
            # A single incoming record linking two previously separate stable-ID
            # groups is unusual. Keeping it separate is safer than silently
            # collapsing potentially distinct works.
            chosen: Optional[int] = None
        elif len(stable_matches) == 1:
            chosen = next(iter(stable_matches))
        else:
            compatible = [
                idx for idx in title_to_idxs.get(raw["normalized_title"], [])
                if _title_merge_compatible(groups[idx], raw)
            ]
            chosen = compatible[0] if len(compatible) == 1 else None

        if chosen is None:
            chosen = len(groups)
            g = dict(raw)
            g["sources_set"] = set()
            g["discovered_by_set"] = set()
            groups.append(g)
            title_to_idxs.setdefault(raw["normalized_title"], []).append(chosen)
        else:
            g = groups[chosen]

        g["sources_set"].add(raw.get("source", ""))
        g["discovered_by_set"].add(raw.get("discovered_by", ""))

        for fld in ["abstract", "authors"]:
            g[fld] = better_value(g.get(fld, ""), raw.get(fld, ""), prefer_longer=True)
        for fld in ["arxiv_id", "doi", "openalex_id", "landing_url", "primary_url", "arxiv_updated_date", "openalex_relevance_score"]:
            g[fld] = better_value(g.get(fld, ""), raw.get(fld, ""))

        g["arxiv_first_public_date"] = better_value(
            g.get("arxiv_first_public_date", ""), raw.get("arxiv_first_public_date", "")
        )
        dates = [
            d for d in [
                parse_iso_date(g.get("openalex_publication_date", "")),
                parse_iso_date(raw.get("openalex_publication_date", "")),
            ] if d
        ]
        if dates:
            g["openalex_publication_date"] = min(dates)

        # Register all stable IDs now present on the merged group. Do not overwrite
        # an existing mapping to another group; that preserves ambiguity instead of
        # silently joining records.
        for k in stable_keys(g):
            stable_to_idx.setdefault(k, chosen)

    out: List[Dict] = []
    for g in groups:
        g["sources"] = ";".join(sorted(s for s in g.pop("sources_set") if s))
        g["discovered_by"] = ";".join(sorted(s for s in g.pop("discovered_by_set") if s))
        g["seed_neighbor"] = "YES" if g.get("arxiv_id") in seed_ids else "NO"
        score, groups_hit = triage_score(g)
        g["triage_group_count"] = score
        g["triage_groups"] = groups_hit
        g["title_core_hit"] = "YES" if title_core_hit(g) else "NO"
        g["provisional_timing_bucket"] = provisional_timing_bucket(g)
        out.append(g)

    out.sort(key=lambda x: (
        0 if x.get("seed_neighbor") == "YES" else 1,
        -int(x.get("triage_group_count", 0)),
        0 if x.get("title_core_hit") == "YES" else 1,
        x.get("arxiv_first_public_date") or x.get("openalex_publication_date") or "9999-99-99",
        x.get("title", "").lower(),
    ))
    return out


def arxiv_date_clause() -> str:
    lo = SEARCH_MIN_DATE.replace("-", "") + "0000"
    hi = CURRENT_AWARENESS_CUTOFF_DATE.replace("-", "") + "2359"
    return f"submittedDate:[{lo} TO {hi}]"


def write_csv(path: Path, rows: Iterable[Dict], fields: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(fields), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})


def run_audit(outdir: Path, script_path: Path, runner_path: Optional[Path]) -> None:
    freeze = verify_freeze(outdir, script_path, runner_path)
    assert_clean_pre_run(outdir)

    raw_dir = outdir / "raw"
    raw_dir.mkdir()
    rows: List[Dict] = []
    errors: List[Dict] = []
    job_records: List[Dict] = []
    run_started = now_utc()

    openalex_key = os.environ.get("OPENALEX_API_KEY", "").strip()
    oa_headers = {"Authorization": f"Bearer {openalex_key}"} if openalex_key else {}

    def record_success(job_id: str, source: str, url_without_secret: str, raw_path: Path, meta: Dict[str, object], headers: Dict[str, str]) -> None:
        job_records.append({
            "job_id": job_id,
            "source": source,
            "status": "SUCCESS",
            "url": url_without_secret,
            "raw_file": str(raw_path.relative_to(outdir)),
            "raw_sha256": sha256_file(raw_path),
            "response_meta": meta,
            "http_status": headers.get("http_status", ""),
            "rate_limit_remaining": headers.get("X-RateLimit-Remaining", ""),
            "rate_limit_credits_used": headers.get("X-RateLimit-Credits-Used", ""),
        })

    def record_error(job_id: str, source: str, query: str, exc: BaseException) -> None:
        errors.append({"job_id": job_id, "source": source, "query": query, "error": repr(exc)})

    # 1) Exact seed batch.
    seed_q = ",".join(SEED_ARXIV_IDS)
    seed_params = {"id_list": seed_q, "max_results": len(SEED_ARXIV_IDS)}
    seed_url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(seed_params)
    seed_job = "ARXIV_SEEDS"
    try:
        body, headers = http_get(seed_url)
        raw_path = raw_dir / "arxiv_seed_neighbors.xml"
        raw_path.write_bytes(body)
        parsed, meta = parse_arxiv_atom(body, seed_job)
        rows.extend(parsed)
        record_success(seed_job, "arxiv", seed_url, raw_path, meta, headers)
        recovered = {r.get("arxiv_id") for r in parsed}
        missing = sorted(set(SEED_ARXIV_IDS) - recovered)
        unexpected = sorted(recovered - set(SEED_ARXIV_IDS))
        if missing or unexpected:
            raise RuntimeError(f"seed recovery mismatch missing={missing} unexpected={unexpected}")
    except Exception as e:
        record_error(seed_job, "arxiv", seed_q, e)
    time.sleep(3.0)

    # 2) arXiv structured query retrieval in BOTH relevance and recent modes.
    date_clause = arxiv_date_clause()
    for i, core_q in enumerate(ARXIV_CORE_QUERIES, 1):
        full_q = f"({core_q}) AND {date_clause}"
        for mode, sort_by, sort_order, max_results in [
            ("relevance", "relevance", "descending", 100),
            ("recent", "submittedDate", "descending", 50),
        ]:
            job_id = f"ARXIV_Q{i:02d}_{mode.upper()}"
            print(f"[{job_id}] {core_q}", flush=True)
            params = {
                "search_query": full_q,
                "start": 0,
                "max_results": max_results,
                "sortBy": sort_by,
                "sortOrder": sort_order,
            }
            url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
            try:
                body, headers = http_get(url)
                raw_path = raw_dir / f"arxiv_q{i:02d}_{mode}.xml"
                raw_path.write_bytes(body)
                parsed, meta = parse_arxiv_atom(body, job_id)
                rows.extend(parsed)
                record_success(job_id, "arxiv", url, raw_path, meta, headers)
            except Exception as e:
                record_error(job_id, "arxiv", full_q, e)
            time.sleep(3.0)

    # 3) OpenAlex retrieval in relevance and recent modes.
    oa_filter = f"from_publication_date:{SEARCH_MIN_DATE},to_publication_date:{CURRENT_AWARENESS_CUTOFF_DATE}"
    for i, q in enumerate(OPENALEX_CORE_QUERIES, 1):
        for mode, sort_value in [
            ("relevance", "relevance_score:desc"),
            ("recent", "publication_date:desc,relevance_score:desc"),
        ]:
            job_id = f"OPENALEX_Q{i:02d}_{mode.upper()}"
            print(f"[{job_id}] {q}", flush=True)
            params = {
                "search": q,
                "per_page": 100,
                "filter": oa_filter,
                "sort": sort_value,
            }
            url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
            try:
                body, headers = http_get(url, extra_headers=oa_headers)
                raw_path = raw_dir / f"openalex_q{i:02d}_{mode}.json"
                raw_path.write_bytes(body)
                parsed, meta = parse_openalex(body, job_id)
                rows.extend(parsed)
                record_success(job_id, "openalex", url, raw_path, meta, headers)
            except Exception as e:
                record_error(job_id, "openalex", q, e)
            time.sleep(0.20)

    write_json(outdir / "N0_RW_RETRIEVAL_JOBS.json", job_records)
    write_json(outdir / "N0_RW_FETCH_ERRORS.json", errors)

    expected_jobs = int(freeze["expected_retrieval_jobs"])
    success_jobs = sum(1 for j in job_records if j.get("status") == "SUCCESS")
    if errors or success_jobs != expected_jobs:
        aborted = {
            "aborted_utc": now_utc(),
            "run_started_utc": run_started,
            "reason": "STRICT_FETCH_COMPLETENESS_FAILURE",
            "expected_retrieval_jobs": expected_jobs,
            "successful_retrieval_jobs": success_jobs,
            "fetch_error_count": len(errors),
            "scientific_model_calls": 0,
            "instruction": "Preserve this directory as failed provenance. Do not reuse it. Start a fresh output directory for a new frozen attempt.",
        }
        write_json(outdir / "N0_RW_ABORTED.json", aborted)
        raise SystemExit(
            f"STOP: retrieval incomplete: {success_jobs}/{expected_jobs} successful jobs; errors={len(errors)}. "
            f"Preserve {outdir} and rerun using a NEW output directory."
        )

    merged = merge_rows(rows, set(SEED_ARXIV_IDS))
    recovered_seed_ids = sorted({r.get("arxiv_id") for r in merged if r.get("arxiv_id") in set(SEED_ARXIV_IDS)})
    if recovered_seed_ids != sorted(SEED_ARXIV_IDS):
        raise SystemExit(
            "STOP: strict seed recovery failed after merge. "
            f"expected={sorted(SEED_ARXIV_IDS)} recovered={recovered_seed_ids}"
        )

    master_fields = [
        "title", "arxiv_first_public_date", "openalex_publication_date", "arxiv_updated_date",
        "authors", "arxiv_id", "doi", "openalex_id", "primary_url", "landing_url",
        "seed_neighbor", "triage_group_count", "triage_groups", "title_core_hit",
        "provisional_timing_bucket", "sources", "discovered_by", "openalex_relevance_score", "abstract",
    ]
    write_csv(outdir / "N0_RW_CANDIDATE_MASTER.csv", merged, master_fields)

    # Every candidate gets a human title/abstract screening row. This prevents the >=3
    # keyword heuristic from silently excluding a lexical-near miss.
    screening_fields = master_fields + SCREENING_MANUAL_COLUMNS
    screening_rows: List[Dict] = []
    for r in merged:
        x = dict(r)
        for c in SCREENING_MANUAL_COLUMNS:
            x[c] = ""
        screening_rows.append(x)
    write_csv(outdir / "N0_RW_SCREENING_ALL.csv", screening_rows, screening_fields)

    # Full-text priority is a workload aid only. Seeds are always included. Non-seeds
    # enter if they hit >=3 semantic keyword groups OR a core term appears in title and
    # they hit >=2 groups. The ALL-screening sheet remains authoritative for recall.
    priority = [
        r for r in merged
        if r.get("seed_neighbor") == "YES"
        or int(r.get("triage_group_count", 0)) >= 3
        or (r.get("title_core_hit") == "YES" and int(r.get("triage_group_count", 0)) >= 2)
    ]
    manual_fields = master_fields + FULLTEXT_MANUAL_COLUMNS
    manual_rows: List[Dict] = []
    for r in priority:
        x = dict(r)
        for c in FULLTEXT_MANUAL_COLUMNS:
            x[c] = ""
        manual_rows.append(x)
    write_csv(outdir / "N0_RW_MANUAL_ADJUDICATION.csv", manual_rows, manual_fields)

    summary = {
        "completed_utc": now_utc(),
        "run_started_utc": run_started,
        "protocol": PROTOCOL,
        "freeze_sha256": sha256_file(outdir / "N0_RW_FREEZE.json"),
        "script_sha256": sha256_file(script_path),
        "runner_sha256": sha256_file(runner_path) if runner_path else "",
        "config_sha256": freeze["config_sha256"],
        "expected_retrieval_jobs": expected_jobs,
        "successful_retrieval_jobs": success_jobs,
        "raw_records_before_dedupe": len(rows),
        "unique_candidates": len(merged),
        "all_screening_rows": len(screening_rows),
        "fulltext_priority_rows": len(priority),
        "seed_ids_requested": len(SEED_ARXIV_IDS),
        "seed_ids_recovered": recovered_seed_ids,
        "fetch_error_count": 0,
        "openalex_api_key_present": bool(openalex_key),
        "scientific_model_calls": 0,
        "automatic_novelty_verdict": None,
        "automatic_collision_verdict": None,
        "locked_policy_warning": "Do not let post-2026-07-15 arXiv-only concurrent work automatically block N3. Manual peer-review status and locked-cutoff adjudication are required.",
        "next_step": "Screen every N0_RW_SCREENING_ALL.csv row; full-read/adjudicate plausible collisions in N0_RW_MANUAL_ADJUDICATION.csv; only then issue N0-RW disposition / N0-FRZ decision.",
    }
    write_json(outdir / "N0_RW_RUN_COMPLETE.json", summary)

    # Final ledger includes every file except the ledger itself.
    ledger = outdir / "N0_RW_SHA256.txt"
    files = sorted(p for p in outdir.rglob("*") if p.is_file() and p != ledger)
    with ledger.open("w", encoding="utf-8") as f:
        for p in files:
            f.write(f"{sha256_file(p)}  {p.relative_to(outdir)}\n")

    print("\nN0-RW DISCOVERY RUN COMPLETE")
    print(f"protocol={PROTOCOL}")
    print(f"retrieval_jobs={success_jobs}/{expected_jobs}")
    print(f"unique_candidates={len(merged)}")
    print(f"all_screening_rows={len(screening_rows)}")
    print(f"fulltext_priority_rows={len(priority)}")
    print(f"seed_recovery={len(recovered_seed_ids)}/{len(SEED_ARXIV_IDS)}")
    print("fetch_error_count=0")
    print("scientific_model_calls=0")
    print("NO NOVELTY OR COLLISION VERDICT HAS BEEN AUTOMATICALLY ISSUED")
    print("POST-CUTOFF CONCURRENT WORK IS SEPARATED FROM LOCKED NOVELTY-KILLING ELIGIBILITY")


def print_plan() -> None:
    print(json.dumps(config_obj(), indent=2, ensure_ascii=False))


def main() -> None:
    ap = argparse.ArgumentParser()
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--print-plan", action="store_true")
    ap.add_argument("--out", default="N0_RW_AUTHOR_RUN_v1_2")
    ap.add_argument("--runner", default="", help="Path to the shell runner; hashed/copied at freeze and verified at run.")
    args = ap.parse_args()

    script_path = Path(__file__).resolve()
    runner_path = Path(args.runner).resolve() if args.runner else None
    outdir = Path(args.out).resolve()

    if args.print_plan:
        print_plan()
    elif args.freeze:
        write_freeze(outdir, script_path, runner_path)
    elif args.run:
        run_audit(outdir, script_path, runner_path)


if __name__ == "__main__":
    main()
