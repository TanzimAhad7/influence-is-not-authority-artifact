#!/usr/bin/env python3
"""Frozen matched intervention attacks for E2E-ATTR-AUTH.

Important AgentDojo v0.1.35 serialization fact:
TaskSuite.load_and_inject_default_environment() performs Python str.format()
on YAML source *before* yaml.safe_load(). All frozen E2E carriers are embedded
inside YAML double-quoted scalars. Therefore raw quotes/backslashes/newlines in
an injected directive must be YAML-double-quoted escaped at substitution time.

_escape_for_yaml_double_quoted() is transport encoding only. yaml.safe_load()
decodes the inserted text back to the exact frozen raw directive. The pre-science
round-trip audit proves equality for every retained ALIGNED/CONFLICT context.
"""
from __future__ import annotations
import json, os
from pathlib import Path
from agentdojo.attacks.attack_registry import register_attack
from agentdojo.attacks.base_attacks import BaseAttack

_CACHE = None

def _load():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    p = os.environ.get("E2E_CONTEXT_RENDERED")
    if not p:
        raise RuntimeError("E2E_CONTEXT_RENDERED is not set")
    rows = [json.loads(x) for x in Path(p).read_text(encoding="utf-8").splitlines() if x.strip()]
    _CACHE = {(r["suite"], r["user_task"], r["context"]): r for r in rows}
    return _CACHE

def _escape_for_yaml_double_quoted(text: str) -> str:
    """Encode text for insertion inside an existing YAML double-quoted scalar.

    This changes only the pre-parse YAML representation. After yaml.safe_load(),
    the environment value is byte-for-byte the original UTF-8 Python string.
    """
    return (text
            .replace('\\', '\\\\')
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t'))

class _MatchedAttack(BaseAttack):
    context: str
    def attack(self, user_task, injection_task):
        key = (self.task_suite.name, user_task.ID, self.context)
        row = _load().get(key)
        if row is None:
            raise KeyError(f"No frozen context row for {key}")
        candidates = self.get_injection_candidates(user_task)
        if not candidates:
            raise RuntimeError(f"No injection candidate for {key}")
        carrier = candidates[0]
        expected = row["selected_injection_vector"]
        if carrier != expected:
            raise RuntimeError(f"Carrier drift for {key}: runtime={carrier!r} frozen={expected!r}")
        # AgentDojo v0.1.35 formats this value into YAML source. Escape for that
        # transport layer while preserving the exact post-parse directive.
        return {carrier: _escape_for_yaml_double_quoted(row["directive"])}

@register_attack
class E2EAlignedAttack(_MatchedAttack):
    name = "e2e_aligned_v1"
    context = "ALIGNED"

@register_attack
class E2EConflictAttack(_MatchedAttack):
    name = "e2e_conflict_v1"
    context = "CONFLICT"
