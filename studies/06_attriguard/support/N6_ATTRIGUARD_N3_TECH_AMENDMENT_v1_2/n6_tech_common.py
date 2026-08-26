from __future__ import annotations
import hashlib, json, tarfile
from pathlib import Path
from typing import Any

PARENT_PROTOCOL_HASH = "fec6c25db0fe0143119b93e1c5178db3c5a14c7cd24514af5eb4329f2ef7fd5e"
PARENT_DESIGN_HASH = "bf0d2d48dfc9707124b6c115c7ea065dcde6d610098fd76aade3e75138bb50f2"
PARENT_SCOPE_SHA256 = "ab676a7505a5c11b15e3950f7395c25f16dbd870b5e5c5639f33e30fcb6a4820"

EXPECTED = {
    "n3_archive_sha256": "d678a768ec8d7cd2c9ce90a938dbfeb24ddea7e6e0e4bfcf18b33c51439f7de7",
    "attriguard_zip_sha256": "81c6d58fdd09c8af217e59dc752dc032dab32c29e204dd7f9d936592174bbf1a",
    "attriguard_py_sha256": "6d28e2208efbd521bf3f2e90c553e57b11c786e65564eababacb8cdf4f8050d8",
    "attriguard_pipeline_sha256": "1976917813ea957529fcb5f8672ef1b2ac199b82b9fb5164c402d1998ae2f96d",
    "openai_compat_sha256": "706bfb0b26bf4cc5f317892798b509d82966bb0d92305f65be45cbcb4bd7764a",
    "prior_a14_adapter_sha256": "fb613a6e427fa28bdc0ddf3774fbdd0abbbcc593733f41eca1d19449b758467a",
}

N3_MEMBERS = {
    "contexts": "N3_PREFREEZE_AUTHOR_v1_1/N3_POSITIVE_CONTEXTS.jsonl",
    "projection": "N3_PREFREEZE_AUTHOR_v1_1/N3_BASE_PROJECTION.json",
    "audit": "N3_PREFREEZE_AUTHOR_v1_1/N3_HUMAN_AUDIT.jsonl",
    "protocol": "N3_PREFREEZE_AUTHOR_v1_1/N3_PROTOCOL_DRAFT.json",
}

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def stable_json(x: Any) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def stable_hash(x: Any) -> str:
    return hashlib.sha256(stable_json(x).encode()).hexdigest()

def load_jsonl(p: Path):
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

def append_jsonl(p: Path, obj: dict):
    import os
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())

def verify_parent(project: Path):
    out = project / "N6_ATTRIGUARD_N3_PREFREEZE_v1_out"
    design_p = out / "N6_DESIGN_DRAFT.json"
    freeze_p = out / "N6_SCIENTIFIC_PREFREEZE.json"
    audit_p = out / "N6_ATTRIGUARD_SCOPE_AUDIT.jsonl"
    for p in (design_p, freeze_p, audit_p):
        if not p.is_file():
            raise SystemExit(f"FATAL: missing parent prefreeze artifact {p}")
    design = json.loads(design_p.read_text())
    dh = design.pop("design_hash")
    if dh != PARENT_DESIGN_HASH or stable_hash(design) != dh:
        raise SystemExit("FATAL: parent N6 design hash mismatch")
    design["design_hash"] = dh

    freeze = json.loads(freeze_p.read_text())
    ph = freeze.pop("protocol_hash")
    if ph != PARENT_PROTOCOL_HASH or stable_hash(freeze) != ph:
        raise SystemExit("FATAL: parent N6 protocol hash mismatch")
    freeze["protocol_hash"] = ph
    if freeze.get("status") != "FROZEN_PRE_OUTCOME_ZERO_MODEL_CALLS":
        raise SystemExit("FATAL: parent N6 protocol not pre-outcome frozen")
    if sha256_file(audit_p) != PARENT_SCOPE_SHA256:
        raise SystemExit("FATAL: parent N6 scope audit hash mismatch")
    rows = load_jsonl(audit_p)
    if len(rows) != 24 or any(r.get("attriguard_scope_decision") != "PASS" for r in rows):
        raise SystemExit("FATAL: parent N6 author scope audit is not 24/24 PASS")
    return design, freeze, rows

def locate_sources(project: Path):
    n3 = project / "N3_COMPLETE_AUTHOR_v1_2.tar.gz"
    official_zip = project / "external/attriguard_zenodo_v1/usenix-artifacts.zip"
    official_root = project / "external/attriguard_zenodo_v1/usenix-artifacts"
    core = official_root / "main/pipeline/AttriGuard.py"
    pipe = official_root / "main/pipeline/my_agent_pipeline.py"
    compat = official_root / "main/pipeline/openai_llm_compat.py"
    prior = project / "ATTRIGUARD_A14_V2_01_adapter.py"
    paths = {
        "n3_archive_sha256": n3,
        "attriguard_zip_sha256": official_zip,
        "attriguard_py_sha256": core,
        "attriguard_pipeline_sha256": pipe,
        "openai_compat_sha256": compat,
        "prior_a14_adapter_sha256": prior,
    }
    for k,p in paths.items():
        if not p.is_file():
            raise SystemExit(f"FATAL: missing source input {p}")
        got = sha256_file(p)
        if got != EXPECTED[k]:
            raise SystemExit(f"FATAL: {k} drift {got} != {EXPECTED[k]}")
    return n3, official_root, paths

def load_n3(n3: Path):
    with tarfile.open(n3, "r:gz") as tf:
        blobs = {}
        shas = {}
        for k,m in N3_MEMBERS.items():
            f = tf.extractfile(m)
            if f is None:
                raise SystemExit(f"FATAL: missing N3 member {m}")
            b = f.read()
            blobs[k] = b
            shas[k] = sha256_bytes(b)
    contexts = [json.loads(x) for x in blobs["contexts"].decode().splitlines() if x.strip()]
    projection = json.loads(blobs["projection"])
    audit = [json.loads(x) for x in blobs["audit"].decode().splitlines() if x.strip()]
    protocol = json.loads(blobs["protocol"])
    return contexts, projection, audit, protocol, shas
