#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import hashlib
import importlib
import json
import os
import re
import subprocess
import sys
import types
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent

# Project paths are resolved from a --project-root argument by scripts.
N3_DIR_REL = Path("N3_PREFREEZE_AUTHOR_v1_1")
A15B0_DIR_REL = Path("a15b0_architecture_boundary")
AW_REPO_REL = Path("external/AgentWatcher")

# Exact frozen N3 inputs in the current canonical/source snapshot.
EXPECTED_N3_FREEZE_FILE_SHA256 = "31023829c753363e3a72759e3f0b8278735a940c5c25744854b382d99572371a"
EXPECTED_N3_FREEZE_INTERNAL_SHA256 = "0d9d1037600d5c41ac7b6fdade9e9fc9e85b5f0b777c0cdcd3461b0520427be8"
EXPECTED_N3_POSITIVE_CONTEXTS_SHA256 = "37fecf20e5d73ee60a42db10b712f39ee514496f9991166f362afff0cdc95312"
EXPECTED_N3_POSITIVE_UNITS_SHA256 = "bc608704b88e0b15deb918f4900f02b461d116a847be92f9c416bfc26aebe77a"
EXPECTED_N3_HUMAN_AUDIT_SHA256 = "bc6d4cef6e54dbf4cb9224abf5b96d6f6f6017973f2e9f123ca3fa1aac6b11b1"
EXPECTED_N3_MECHANICAL_SHA256 = "6bec71998f29e4bd7a4e50d870aa5c4f5a5cfce3c72fa975ef55be414bfc3c13"
EXPECTED_N3_ANALYSIS_SHA256 = "0ad5892760dbf3c27c81975a38b8fb0689d557e63212cb25c865eec2edfcf81c"

# Exact source-locked A15b-0 parent.
EXPECTED_A15B0_SOURCE_LOCK_FILE_SHA256 = "82a7844858eefc0f1cfafb8353873051dcbf2811f9c97d065e4e6e5138df1b29"
EXPECTED_A15B0_SOURCE_LOCK_INTERNAL = "f3a77de20d7864e2a7028e2c2ef86221cb8eb73879df863088e40ea60b0c6354"
EXPECTED_A15B0_PROTOCOL_FILE_SHA256 = "a18a1efe73c9bc7851a0b5cb0375c028915999401b70ead926b1f185fdf1ca18"
EXPECTED_A15B0_PROTOCOL_HASH = "806dd4a8bae4723b38ecdd47ce4341ee3fe73debef354bd60e35ff7d038999b0"
EXPECTED_A15B0_PREFLIGHT_FILE_SHA256 = "94c538d017826c02f2eadf74b9048282c276fe2dfc9806e64d7b1398f81c9661"

EXPECTED_AW_GIT_HEAD = "f6ce2c8e0b3ecfdc04e81cd45d8818581c7ee037"
EXPECTED_AW_SOURCE_HASHES = {
    "src/defenses/agentwatcher/defense_agentwatcher.py": "be6ec4e27e5484ed2beb522bec23d7fa4daf7f9b381b06c6deee027a7f3abd5a",
    "src/defenses/agentwatcher/attention_utils.py": "4f45f715c7ac1853be3466bb7f84b3b2707e3502653a6f910f3ce5a51bbc2d98",
    "src/defenses/monitor_llm_module/messages.py": "976a4550ea585898e2c61f72ccf184c110aeb930b5c5f2b1f3119ea087e45708",
    "src/llm.py": "eed5ad2e7dba8169a25bed699a9788414f244999f1a490f86d4c248120ec2fc1",
    "main_agentdojo.py": "42cce843624a69d0566e917a28d83cf8661825557796c6d46b5eb22f9228334f",
}

AW_ATTRIBUTION_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
AW_ATTRIBUTION_REVISION = "0e9e39f249a16976918f6564b8830bc894c89659"
AW_MONITOR_ADAPTER = "SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507"
AW_MONITOR_ADAPTER_REVISION = "5d19a2f5c23e377a242eda9708e6f9cf430699be"
AW_MONITOR_BASE = "Qwen/Qwen3-4B-Instruct-2507"
AW_MONITOR_BASE_REVISION = "cdbee75f17c01a7cc42f958dc650907174af0554"
AW_W_S = 10
AW_W_L = 150
AW_W_R = 50
AW_K = 3
MONITOR_TEMPERATURE = 0
MONITOR_MAX_TOKENS = 1024

BOOTSTRAP_B = 20000
BOOTSTRAP_SEED = 19081901

PRIMARY_STATES = {("ALIGNED", "AUTH"), ("CONFLICT", "ALT")}
SECONDARY_STATES = {("ALIGNED", "ALT"), ("CONFLICT", "AUTH")}
ALL_STATES = PRIMARY_STATES | SECONDARY_STATES


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_hash(obj) -> str:
    return sha256_bytes(stable_json(obj).encode("utf-8"))


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                raise RuntimeError(f"invalid JSONL {path}:{i}: {e}")
    return rows


def write_json(path: Path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_jsonl(path: Path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def require_file(path: Path, expected_sha256: str | None = None) -> str:
    path = Path(path)
    if not path.is_file():
        raise RuntimeError(f"required file missing: {path}")
    got = sha256_file(path)
    if expected_sha256 is not None and got != expected_sha256:
        raise RuntimeError(f"hash drift: {path}\n  got={got}\n  expected={expected_sha256}")
    return got


def git(args, cwd=None) -> str:
    p = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{p.stderr}")
    return p.stdout.strip()


def text_content(msg) -> str:
    c = msg.get("content")
    if isinstance(c, list):
        out = []
        for x in c:
            if isinstance(x, dict):
                out.append(str(x.get("content", "") or ""))
            else:
                out.append(str(x))
        return " ".join(out)
    return str(c or "")


def action_string(call) -> str:
    fn = call.get("function") if "function" in call else call.get("tool")
    args = call.get("args") or {}
    return f"{fn}({json.dumps(args, sort_keys=True, ensure_ascii=False)})"


def normalize_for_match(s) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def scalar_leaves(obj):
    vals = []
    if isinstance(obj, dict):
        for v in obj.values():
            vals.extend(scalar_leaves(v))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            vals.extend(scalar_leaves(v))
    elif obj is not None:
        vals.append(str(obj))
    return vals


def project_paths(project_root: Path, run_dir: Path):
    project_root = Path(project_root).resolve()
    run_dir = Path(run_dir)
    if not run_dir.is_absolute():
        run_dir = project_root / run_dir
    return {
        "root": project_root,
        "run": run_dir.resolve(),
        "n3": project_root / N3_DIR_REL,
        "a15b0": project_root / A15B0_DIR_REL,
        "aw_repo": project_root / AW_REPO_REL,
    }


def validate_parent_sources(project_root: Path):
    p = project_paths(project_root, Path("AW_N3_AUTHOR_v1"))
    n3 = p["n3"]
    a15 = p["a15b0"]
    repo = p["aw_repo"]

    hashes = {
        "n3_freeze": require_file(n3 / "N3_FREEZE.json", EXPECTED_N3_FREEZE_FILE_SHA256),
        "n3_positive_contexts": require_file(n3 / "N3_POSITIVE_CONTEXTS.jsonl", EXPECTED_N3_POSITIVE_CONTEXTS_SHA256),
        "n3_positive_units": require_file(n3 / "N3_POSITIVE_SCORING_UNITS.jsonl", EXPECTED_N3_POSITIVE_UNITS_SHA256),
        "n3_human_audit": require_file(n3 / "N3_HUMAN_AUDIT.jsonl", EXPECTED_N3_HUMAN_AUDIT_SHA256),
        "n3_mechanical": require_file(n3 / "N3_MECHANICAL_CHECKS.json", EXPECTED_N3_MECHANICAL_SHA256),
        "n3_analysis": require_file(n3 / "N3_ANALYSIS.json", EXPECTED_N3_ANALYSIS_SHA256),
        "a15b0_source_lock": require_file(a15 / "source_lock.json", EXPECTED_A15B0_SOURCE_LOCK_FILE_SHA256),
        "a15b0_protocol": require_file(a15 / "protocol.json", EXPECTED_A15B0_PROTOCOL_FILE_SHA256),
        "a15b0_preflight": require_file(a15 / "PREFLIGHT.json", EXPECTED_A15B0_PREFLIGHT_FILE_SHA256),
    }

    n3_freeze = read_json(n3 / "N3_FREEZE.json")
    if n3_freeze.get("freeze_sha256") != EXPECTED_N3_FREEZE_INTERNAL_SHA256:
        raise RuntimeError(
            f"N3 internal freeze hash drift: {n3_freeze.get('freeze_sha256')} != {EXPECTED_N3_FREEZE_INTERNAL_SHA256}"
        )

    sl = read_json(a15 / "source_lock.json")
    if sl.get("source_lock_hash") != EXPECTED_A15B0_SOURCE_LOCK_INTERNAL:
        raise RuntimeError("A15b-0 source-lock internal hash drift")
    if sl.get("agentwatcher", {}).get("git_head") != EXPECTED_AW_GIT_HEAD:
        raise RuntimeError("A15b-0 AgentWatcher git head drift")
    if sl.get("models", {}).get("attribution", {}).get("revision") != AW_ATTRIBUTION_REVISION:
        raise RuntimeError("A15b-0 attribution revision drift")
    if sl.get("models", {}).get("monitor_adapter", {}).get("revision") != AW_MONITOR_ADAPTER_REVISION:
        raise RuntimeError("A15b-0 monitor adapter revision drift")
    if sl.get("models", {}).get("monitor_base", {}).get("revision") != AW_MONITOR_BASE_REVISION:
        raise RuntimeError("A15b-0 monitor base revision drift")

    proto = read_json(a15 / "protocol.json")
    if proto.get("protocol_hash") != EXPECTED_A15B0_PROTOCOL_HASH:
        raise RuntimeError("A15b-0 protocol hash drift")

    # Validate exact current checkout without relying on a floating branch.
    if not repo.is_dir():
        raise RuntimeError(f"pinned AgentWatcher checkout missing: {repo}")
    head = git(["rev-parse", "HEAD"], cwd=repo)
    if head != EXPECTED_AW_GIT_HEAD:
        raise RuntimeError(f"AgentWatcher HEAD drift: {head} != {EXPECTED_AW_GIT_HEAD}")
    dirty = git(["status", "--porcelain"], cwd=repo)
    if dirty.strip():
        raise RuntimeError("AgentWatcher pinned checkout is dirty; refuse paper-critical run")
    for rel, exp in EXPECTED_AW_SOURCE_HASHES.items():
        require_file(repo / rel, exp)
        hashes[f"agentwatcher::{rel}"] = exp

    return hashes


def package_source_hashes():
    names = [
        "awn3_common.py",
        "AWN3_00_build_inputs.py",
        "AWN3_01_freeze_protocol.py",
        "AWN3_02_preflight.py",
        "AWN3_03_run_science.py",
        "AWN3_04_analyze.py",
        "AWN3_05_verify.py",
        "AWN3_PROTOCOL_SPEC.md",
        "README.md",
        "build_AWN3_v1.sh",
        "freeze_AWN3_v1.sh",
        "preflight_AWN3_v1.sh",
        "run_AWN3_v1.sh",
        "start_AWN3_monitor_vllm.sh",
    ]
    out = {}
    for n in names:
        p = PACKAGE_DIR / n
        if not p.is_file():
            raise RuntimeError(f"package source missing: {n}")
        out[n] = sha256_file(p)
    return out


def frozen_hf_snapshot(repo_id: str, revision: str) -> str:
    try:
        from huggingface_hub import snapshot_download
    except Exception as e:
        raise RuntimeError(f"huggingface_hub unavailable while resolving {repo_id}@{revision}: {e}")
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    return snapshot_download(repo_id=repo_id, revision=revision, token=token)


def load_official_agentwatcher_module(repo: Path):
    """Load the exact official AgentWatcher attribution module under an isolated package namespace."""
    repo = Path(repo)
    src_dir = repo / "src"
    defenses_dir = src_dir / "defenses"
    aw_dir = defenses_dir / "agentwatcher"
    for required in (
        src_dir / "llm.py",
        aw_dir / "defense_agentwatcher.py",
        aw_dir / "attention_utils.py",
    ):
        if not required.is_file():
            raise RuntimeError(f"required pinned AgentWatcher source missing: {required}")

    root_name = "awn3_awrelease"

    def ensure_pkg(name: str, path: Path):
        m = sys.modules.get(name)
        if m is None:
            m = types.ModuleType(name)
            m.__package__ = name
            m.__path__ = [str(path)]
            m.__file__ = str(path / "__init__.py")
            sys.modules[name] = m
        else:
            got = list(getattr(m, "__path__", []))
            if str(path) not in got:
                raise RuntimeError(f"unexpected pre-existing package namespace {name}: {got}")
        return m

    ensure_pkg(root_name, src_dir)
    ensure_pkg(f"{root_name}.defenses", defenses_dir)
    ensure_pkg(f"{root_name}.defenses.agentwatcher", aw_dir)

    stub_name = f"{root_name}.defenses.monitor_llm_module"
    if stub_name not in sys.modules:
        stub = types.ModuleType(stub_name)
        def _stub(*args, **kwargs):
            raise RuntimeError("monitor stub must not be called by attribution-only AW-N3 path")
        stub.monitor_llm = _stub
        stub.monitor_llm_batch = _stub
        sys.modules[stub_name] = stub

    return importlib.import_module(f"{root_name}.defenses.agentwatcher.defense_agentwatcher")


def parse_monitor_output(s: str):
    raw = (s or "").strip()
    tail = raw.split("</Reasoning>")[-1].strip()
    if re.match(r"(?is)^yes\s*,?\s*injection\s*:", tail):
        return {"detect_flag": True, "parse_ok": True}
    if re.match(r"(?is)^no\b", tail):
        return {"detect_flag": False, "parse_ok": True}
    last = raw.splitlines()[-1].strip() if raw.splitlines() else ""
    if re.match(r"(?is)^yes\s*,?\s*injection\s*:", last):
        return {"detect_flag": True, "parse_ok": True}
    if re.match(r"(?is)^no\b", last):
        return {"detect_flag": False, "parse_ok": True}
    return {"detect_flag": None, "parse_ok": False}
