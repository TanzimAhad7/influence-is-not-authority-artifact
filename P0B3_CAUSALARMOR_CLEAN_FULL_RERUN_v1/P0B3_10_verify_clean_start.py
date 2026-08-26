#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, urllib.request
from pathlib import Path

LIVE_ZIP_SHA="136a78c700b0a21ffb2aa9355addae33dc056bd7750b7c8f2fd68d6fe6763a91"
FREEZE_SHA="0ad06fefbbc09d79eadf1e0186570d6181b4b5b22812889cbfed5476ecb0f82c"
PROXY_REPO="google/gemma-3-12b-it"
PROXY_REV="96b6f1eccf38110c56df3a15bffe176da04bfd80"
PORT="8100"

def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def fatal(msg):
    raise SystemExit("FATAL: "+msg)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",required=True)
    a=ap.parse_args()
    root=Path(a.project_root).resolve()
    live_zip=root/"P0B3_CAUSALARMOR_LIVE_v1.zip"
    live_dir=root/"P0B3_CAUSALARMOR_LIVE_v1"
    freeze=root/"P0B3_CAUSALARMOR_CALIBRATION_FREEZE_COMPLETE_v1.zip"
    out=root/"P0B3_CAUSALARMOR_LIVE_RUN_v1"
    hist=root/"P0B3_AUTHOR_RUN_HISTORY"/"P0B3_ATTEMPT0_16K_TECHNICAL_ABORT_992_OF_1046"

    if not live_zip.exists() or sha256_file(live_zip)!=LIVE_ZIP_SHA:
        fatal("original frozen live ZIP missing or SHA mismatch")
    if not freeze.exists() or sha256_file(freeze)!=FREEZE_SHA:
        fatal("completed freeze ZIP missing or SHA mismatch")
    if not live_dir.exists():
        fatal("original frozen live directory missing")
    if not hist.exists():
        fatal("Attempt 0 has not been archived; run P0B3_00_ARCHIVE_ATTEMPT0.sh first")
    if out.exists() and any(out.iterdir()):
        fatal("clean output path is not empty; refusing to mix Attempt 1 with prior files")

    # Verify the live package's internal manifest before any benchmark outcome.
    mf=live_dir/"PACKAGE_SHA256.txt"
    if not mf.exists():
        fatal("live package PACKAGE_SHA256.txt missing")
    for line in mf.read_text().splitlines():
        if not line.strip(): continue
        want,rel=line.split(None,1)
        p=live_dir/rel.strip()
        if not p.exists() or sha256_file(p)!=want:
            fatal(f"live-package hash mismatch: {rel.strip()}")

    # Verify exact 32K server process. This is local technical validation only.
    try:
        ps=subprocess.check_output(["ps","-eo","pid,args"],text=True,errors="replace")
    except Exception as e:
        fatal(f"cannot inspect vLLM process: {e}")
    candidates=[x.strip() for x in ps.splitlines() if PROXY_REPO in x and "vllm" in x.lower() and "--port 8100" in x]
    required=[
        PROXY_REPO,
        PROXY_REV,
        "--tokenizer-revision "+PROXY_REV,
        "--served-model-name google/gemma-3-12b-it",
        "--dtype bfloat16",
        "--tensor-parallel-size 2",
        "--max-model-len 32768",
        "--port 8100",
    ]
    strict=[x for x in candidates if all(s in x for s in required)]
    if not strict:
        fatal("exact finalized 32K Gemma vLLM process not found")

    req=urllib.request.Request("http://127.0.0.1:8100/v1/models",headers={"Authorization":"Bearer EMPTY"})
    try:
        with urllib.request.urlopen(req,timeout=30) as r:
            models=json.loads(r.read().decode())
    except Exception as e:
        fatal(f"vLLM /v1/models unavailable: {e}")
    ids=[x.get("id") for x in models.get("data",[]) if isinstance(x,dict)]
    if PROXY_REPO not in ids:
        fatal(f"served model mismatch: {ids}")

    print("P0b-3 CLEAN FULL RERUN LOCAL VERIFY PASS")
    print("Attempt 0 archived: yes")
    print("Attempt 1 output path clean: yes")
    print("frozen live ZIP SHA: "+LIVE_ZIP_SHA)
    print("completed freeze SHA: "+FREEZE_SHA)
    print("Gemma serving ceiling: 32768")
    print("AgentDojo benchmark episodes executed by this verifier: 0")

if __name__=="__main__":
    main()
