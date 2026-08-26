# Reproduction Orchestration

This directory contains the stage wrappers used for fresh experiment reruns.

For normal use, start from the repository root:

```bash
bash CHECK_E2E.sh --structural
bash RUN_END_TO_END.sh --list
```

The numbered wrappers are under `stages/`. They follow the paper's evidence chain from natural relevance through figure regeneration.

The original frozen experiment scripts use historical top-level run identifiers. `materialize_legacy_worktree.py`, `resolve_legacy_path.py`, and `LEGACY_PATH_MAP.tsv` provide a compatibility layer inside a disposable rerun worktree. They do not restore the flat historical hierarchy in the distributed repository.

See `../REPRODUCE.md` and `../FULL_RERUN.md` for requirements and commands.
