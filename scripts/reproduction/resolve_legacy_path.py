#!/usr/bin/env python3
from __future__ import annotations
import csv, sys
from pathlib import Path


def load_map(root: Path) -> dict[str, str]:
    p = root / 'LEGACY_PATH_MAP.tsv'
    out: dict[str, str] = {}
    if not p.is_file():
        return out
    with p.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            out[row['legacy_top_level']] = row['new_path']
    return out


def resolve(root: Path, rel: str) -> Path:
    relp = Path(rel)
    if relp.is_absolute():
        return relp
    parts = relp.parts
    if not parts:
        return root
    m = load_map(root)
    first = parts[0]
    if first in m:
        return root / m[first] / Path(*parts[1:])
    return root / relp


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: resolve_legacy_path.py ARTIFACT_ROOT LEGACY_REL', file=sys.stderr)
        return 2
    print(resolve(Path(sys.argv[1]).resolve(), sys.argv[2]))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
