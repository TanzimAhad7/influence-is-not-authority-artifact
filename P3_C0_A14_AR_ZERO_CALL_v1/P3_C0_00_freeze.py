#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def stable(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--project-root', required=True)
    ap.add_argument('--package-dir', default=str(Path(__file__).resolve().parent))
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    pkg = Path(args.package_dir).resolve()
    out = Path(args.out_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    cfg_path = pkg / 'P3_C0_CONFIG.json'
    cfg = json.loads(cfg_path.read_text())
    inputs = {}
    for name, spec in cfg['expected_inputs'].items():
        p = root / spec['relative_path']
        if not p.exists():
            raise SystemExit(f'FATAL missing input {name}: {p}')
        got = sha256(p)
        if got != spec['sha256']:
            raise SystemExit(f'FATAL hash mismatch {name}: expected {spec["sha256"]}, got {got}')
        inputs[name] = {'path': str(p), 'sha256': got, 'bytes': p.stat().st_size}

    code_names = ['P3_C0_CONFIG.json', 'P3_C0_00_freeze.py', 'P3_C0_01_refresh.py', 'P3_C0_02_hash_outputs.py']
    code = {}
    for name in code_names:
        p = pkg / name
        if not p.exists():
            raise SystemExit(f'FATAL package file missing: {p}')
        code[name] = {'sha256': sha256(p), 'bytes': p.stat().st_size}

    fr = {
        'schema': 'P3_C0_CORRECTED29_REFRESH_FREEZE_V1',
        'created_at_utc': datetime.now(timezone.utc).isoformat(),
        'scientific_model_calls': 0,
        'status': cfg['status'],
        'config': cfg,
        'input_files': inputs,
        'package_files': code,
        'note': 'Post-hoc zero-call presentation/influence freeze. It does not alter the frozen A13-C0 primary estimand or result.'
    }
    fr['freeze_payload_sha256'] = hashlib.sha256(stable(fr).encode()).hexdigest()
    p = out / 'P3_C0_ANALYSIS_FREEZE.json'
    p.write_text(json.dumps(fr, indent=2, sort_keys=True) + '\n')
    print(f'P3-C0 FREEZE PASS: {p}')
    print(f'freeze_payload_sha256={fr["freeze_payload_sha256"]}')


if __name__ == '__main__':
    main()
