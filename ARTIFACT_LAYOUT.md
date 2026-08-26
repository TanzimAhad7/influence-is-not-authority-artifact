# Artifact Layout

This package deliberately keeps the full artifact research artifact rather than only a small claim subset.

- top-level experiment/code/result directories: preserved artifact science and provenance
- `figures/`: final submission figures; only Python producers and PDFs
- `source_artifact_figure_history/`: the older figure directory from the original codebase artifact, retained so source coverage remains complete
- `E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1/`: exact final live-E2E runner package required for literal rerun
- `reproduction/`: non-destructive master-runner helpers and stage wrappers
- `artifact_tools/`: frozen-result, source-coverage, anonymity, integrity, and Figure-6 helpers
- `SOURCE_ARTIFACT_COVERAGE.tsv`: original codebase `artifacts/` file → distributed file accounting
- `source_artifact_metadata/SHA256SUMS.txt`: the original codebase artifact's SHA manifest, preserved separately because top-level `SHA256SUMS.txt` now protects this final artifact package
- `SHA256SUMS.txt`: final package integrity manifest

## Main commands

```bash
bash SETUP_E2E.sh --install-vllm
bash CHECK_E2E.sh
bash RUN_END_TO_END.sh --all
bash VERIFY.sh
bash RUN_FIGURES.sh
bash CHECK_ANONYMITY.sh
bash VERIFY_HASHES.sh
```

The live rerun works in a fresh sibling worktree. Frozen distributed results remain unchanged.
