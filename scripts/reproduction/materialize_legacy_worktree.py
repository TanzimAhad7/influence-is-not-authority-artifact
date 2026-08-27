#!/usr/bin/env python3
"""Recreate the historical top-level layout inside a disposable rerun worktree.

The distributed artifact uses human-readable study folders. Historical experiment
scripts still refer to their frozen top-level identifiers. This helper copies the
relocated top-level entries back into those historical names only inside the
throw-away worktree used for a fresh rerun. The distributed artifact is untouched.
"""
from __future__ import annotations
import argparse, csv, shutil
from pathlib import Path


def copy_entry(src: Path, dst: Path) -> None:
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, dst, symlinks=True)
    else:
        shutil.copy2(src, dst)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--work-root', required=True)
    args = ap.parse_args()
    work = Path(args.work_root).resolve()
    mp = work / 'LEGACY_PATH_MAP.tsv'
    if not mp.is_file():
        raise SystemExit(f'missing {mp}')
    count = 0
    with mp.open(newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f, delimiter='\t'):
            old = row['legacy_top_level']
            new = row['new_path']
            src = work / new
            dst = work / old
            if not src.exists():
                raise SystemExit(f'mapped source missing: {new}')
            copy_entry(src, dst)
            count += 1
    print(f'LEGACY_WORKTREE_LAYOUT=PASS ({count} top-level paths materialized)')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
