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

PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = PROJECT_ROOT / "a15b0_architecture_boundary"

# Completed-parent identities: these bind A15b-0 to the audited project state.
EXPECTED_B1_PROTOCOL_HASH = "61f47a7507f03b01931e6c5b3452dfe43ac9a9b67b52b3079b85214880c7827f"

EXPECTED_A13_PROTOCOL_HASH = "b4a140c7d8ef49149ac72e35e9e52405f614fa5361558c7b2ac0c56fe0063b80"
EXPECTED_A13_PROTOCOL_FILE_SHA256 = "8c0caa2e509f94d0e2eea37cfaf53840319d407167c15e2a052633c53854de43"
EXPECTED_A13_DECISIONS_SHA256 = "af6a62c5689e7d26180f0091a121839b645e1dcb54e5aaf87427f6e75c19dca9"
EXPECTED_A13_MANIFEST_SHA256 = "971eb1ea932a2bc9687c288532b3b9e1b8ae608a492b068d1edf8eae33b0cf0b"
EXPECTED_A13_RESULTS_SHA256 = "6ced3fc14a60574f95881344ac3d6bb5b8cf7d88d59ac3c844cae35d4121646b"

EXPECTED_A15A_INVENTORY_SHA256 = "180a3767588932c160ca4de6fb18c6cd1e0331568814525d31663d416e3d5883"

EXPECTED_A14_PROTOCOL_HASH = "94bb3c7e0ca174aa8be69b8c0949e7d93a567d960a9ba06016ba4d08f8503ee1"
EXPECTED_A14_PROTOCOL_FILE_SHA256 = "5f500ae7891700b5dec48ef09b46c649cf827e8801bc0c8d4375ac5b5dcd5473"
EXPECTED_A14_STRUCTURED_CONTEXTS_SHA256 = "a8ededeeb2343792385eca69eb33fe7bfd379cc3176e9226f6bbe5be3a140d21"
EXPECTED_A14_BASE_INSTANCES_SHA256 = "32d8d56e9ba07c6cbc0d58a640466078c531b658b2173292721829e176f21af7"
EXPECTED_A14_LLAMA_SCORES_SHA256 = "1c2ee74880a4a74d2bbfad06a6fad4e0f8c09a0fd474d8a0a9a7e43f5fb91111"
EXPECTED_A14_GEMMA_SCORES_SHA256 = "edbf606d112410e50ff260e63d7008470c5299ddabfd43188ed7d942c42ec0fa"

AW_REPO_URL = "https://github.com/Wang-Yanting/AgentWatcher.git"
AW_ATTRIBUTION_MODEL = "meta-llama/Llama-3.1-8B-Instruct"
AW_MONITOR_ADAPTER = "SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507"
AW_MONITOR_EXPECTED_BASE = "Qwen/Qwen3-4B-Instruct-2507"
AW_W_S = 10
AW_W_L = 150
AW_W_R = 50
AW_K = 3

CONTROLLED_BOOTSTRAP_B = 20000
CONTROLLED_BOOTSTRAP_SEED = 15015001
NATURAL_BOOTSTRAP_B = 20000
NATURAL_BOOTSTRAP_SEED = 15015002

def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def sha256_bytes(b: bytes):
    return hashlib.sha256(b).hexdigest()

def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def stable_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def stable_hash(obj):
    return sha256_bytes(stable_json(obj).encode("utf-8"))

def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except Exception as e:
                raise RuntimeError(f"invalid JSONL {path}:{i}: {e}")
    return rows

def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)

def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)

def require_file(path: Path, sha=None):
    if not path.is_file():
        raise RuntimeError(f"required file missing: {path}")
    got = sha256_file(path)
    if sha is not None and got != sha:
        raise RuntimeError(f"hash drift: {path}\n  got={got}\n  expected={sha}")
    return got

def text_content(msg):
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

def action_string(call):
    if "function" in call:
        fn = call.get("function")
    else:
        fn = call.get("tool")
    args = call.get("args") or {}
    return f"{fn}({json.dumps(args, sort_keys=True, ensure_ascii=False)})"

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

def normalize_for_match(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()

def git(args, cwd=None):
    p = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{p.stderr}")
    return p.stdout.strip()

def frozen_hf_snapshot(repo_id: str, revision: str) -> str:
    """Resolve/download an exact HF revision and return its local snapshot path."""
    try:
        from huggingface_hub import snapshot_download
    except Exception as e:
        raise RuntimeError(f"huggingface_hub unavailable while resolving {repo_id}@{revision}: {e}")
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    return snapshot_download(repo_id=repo_id, revision=revision, token=token)

def load_official_agentwatcher_module(repo: Path):
    """
    Load the pinned official AgentWatcher defense module without importing the
    broad defenses/__init__.py aggregator.

    We install an isolated package shell whose __path__ points at the pinned
    checkout. This preserves the official file's relative imports:
      .attention_utils
      ...llm
      ..monitor_llm_module
    while preventing unrelated defense modules from being imported.
    """
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

    root_name = "a15b0_awrelease"

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
                raise RuntimeError(
                    f"unexpected pre-existing package namespace {name}: {got}; expected {path}"
                )
        return m

    ensure_pkg(root_name, src_dir)
    ensure_pkg(f"{root_name}.defenses", defenses_dir)
    ensure_pkg(f"{root_name}.defenses.agentwatcher", aw_dir)

    # The attribution function does not call the monitor module. Provide inert
    # symbols only so the official source can import without pulling the repo's
    # monitor packaging into this in-process attribution path.
    stub_name = f"{root_name}.defenses.monitor_llm_module"
    if stub_name not in sys.modules:
        stub = types.ModuleType(stub_name)
        def _monitor_stub(*args, **kwargs):
            raise RuntimeError("monitor stub must not be called by attribution-only path")
        stub.monitor_llm = _monitor_stub
        stub.monitor_llm_batch = _monitor_stub
        sys.modules[stub_name] = stub

    return importlib.import_module(
        f"{root_name}.defenses.agentwatcher.defense_agentwatcher"
    )

def frozen_attribution_model_path() -> str:
    """Return the exact locally resolved AgentWatcher attribution-model revision frozen in source_lock.json."""
    sl_path = OUT_DIR / "source_lock.json"
    if not sl_path.is_file():
        raise RuntimeError("source_lock.json missing; cannot resolve frozen attribution model")
    sl = read_json(sl_path)
    meta = (sl.get("models") or {}).get("attribution") or {}
    repo_id = meta.get("repo_id")
    revision = meta.get("revision")
    if repo_id != AW_ATTRIBUTION_MODEL or not revision:
        raise RuntimeError(
            f"frozen attribution identity mismatch: repo_id={repo_id!r} revision={revision!r}"
        )
    path = frozen_hf_snapshot(repo_id, revision)
    if not Path(path).exists():
        raise RuntimeError(f"resolved frozen attribution snapshot does not exist: {path}")
    return path

def package_source_hashes():
    names = [
        "a15b0_common.py",
        "A15B0_00_source_lock.py",
        "A15B0_01_prepare_inputs.py",
        "A15B0_02_freeze_protocol.py",
        "A15B0_03_preflight.py",
        "A15B0_04_run_agentwatcher.py",
        "A15B0_04b_run_no_attribution.py",
        "A15B0_05_rescore_natural_gemma.py",
        "A15B0_06_analyze.py",
        "A15B0_PROTOCOL_SPEC.md",
        "A15B0_RUNBOOK.md",
    ]
    out = {}
    for n in names:
        p = PROJECT_ROOT / n
        if not p.is_file():
            raise RuntimeError(f"package source missing: {n}")
        out[n] = sha256_file(p)
    return out
