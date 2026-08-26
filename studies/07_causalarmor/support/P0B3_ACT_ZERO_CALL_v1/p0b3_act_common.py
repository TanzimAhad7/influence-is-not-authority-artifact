#!/usr/bin/env python3
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

SCHEMA = "P0B3_ACT_POSTHOC_V1"
EXPECTED_EVENT_SCHEMA = "P0B3_DEFENSE_EVENT_V1"
EXPECTED_INPUT_REL = Path("P0B3_CAUSALARMOR_LIVE_RUN_v1/P0B3_DEFENSE_EVENTS.jsonl")
EXPECTED_INPUT_SHA256 = "bc8c17c257b00a12295c54384c9ce7bc3490f8d6c1f1d3b89aee36641253746a"
EXPECTED_TOTAL_EVENTS = 624
EXPECTED_OVERALL_PRIMARY_FLAGGED = 516
GROUPS = ("benign", "attack")
SOURCE_FILES = (
    "p0b3_act_common.py",
    "P0B3_ACT_00_freeze.py",
    "P0B3_ACT_01_run.py",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as exc:
                raise RuntimeError(f"invalid JSON at {path}:{lineno}: {exc}") from exc
            if not isinstance(obj, dict):
                raise RuntimeError(f"non-object JSON at {path}:{lineno}")
            rows.append(obj)
    return rows


def group_from_episode_id(episode_id: str) -> str:
    if not isinstance(episode_id, str) or ":" not in episode_id:
        raise RuntimeError(f"invalid episode_id: {episode_id!r}")
    group = episode_id.split(":", 1)[0]
    if group not in GROUPS:
        raise RuntimeError(f"unexpected episode group {group!r} in {episode_id!r}")
    return group


def validate_events(rows: List[Dict[str, Any]], *, aggregate_flags: bool) -> Dict[str, Any]:
    if len(rows) != EXPECTED_TOTAL_EVENTS:
        raise RuntimeError(f"expected {EXPECTED_TOTAL_EVENTS} defense events, found {len(rows)}")

    seen = set()
    denominators = {g: 0 for g in GROUPS}
    flagged = {g: 0 for g in GROUPS}

    for i, row in enumerate(rows, 1):
        if row.get("schema") != EXPECTED_EVENT_SCHEMA:
            raise RuntimeError(f"row {i}: unexpected schema {row.get('schema')!r}")

        episode_id = row.get("episode_id")
        attempt_id = row.get("attempt_id")
        decision_index = row.get("decision_index")
        if not isinstance(attempt_id, str) or not attempt_id:
            raise RuntimeError(f"row {i}: invalid attempt_id")
        if not isinstance(decision_index, int):
            raise RuntimeError(f"row {i}: invalid decision_index")

        key = (episode_id, attempt_id, decision_index)
        if key in seen:
            raise RuntimeError(f"duplicate event identity at row {i}: {key!r}")
        seen.add(key)

        primary = row.get("primary_any_flag")
        intervened = row.get("intervened")
        if not isinstance(primary, bool) or not isinstance(intervened, bool):
            raise RuntimeError(f"row {i}: primary_any_flag/intervened must be booleans")
        if primary != intervened:
            raise RuntimeError(
                f"row {i}: primary_any_flag={primary} disagrees with intervened={intervened}"
            )

        group = group_from_episode_id(episode_id)
        denominators[group] += 1
        if aggregate_flags and primary:
            flagged[group] += 1

    if len(seen) != EXPECTED_TOTAL_EVENTS:
        raise RuntimeError("event identity uniqueness check failed")
    if sum(denominators.values()) != EXPECTED_TOTAL_EVENTS:
        raise RuntimeError("group denominator reconciliation failed")

    out: Dict[str, Any] = {
        "total_events": len(rows),
        "unique_event_identities": len(seen),
        "denominators": denominators,
    }
    if aggregate_flags:
        out["flagged"] = flagged
    return out


def load_freeze(path: Path) -> Dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"cannot load freeze {path}: {exc}") from exc
    if obj.get("schema") != SCHEMA or obj.get("stage") != "FREEZE":
        raise RuntimeError("freeze schema/stage mismatch")
    return obj


def source_hashes(package_dir: Path) -> Dict[str, str]:
    out = {}
    for name in SOURCE_FILES:
        p = package_dir / name
        if not p.is_file():
            raise RuntimeError(f"missing package source file: {p}")
        out[name] = sha256_file(p)
    return out


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
