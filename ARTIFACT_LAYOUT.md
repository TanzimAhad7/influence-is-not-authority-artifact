# Artifact Layout

The repository is organized by scientific role rather than historical experiment ID.

## Primary structure

- `studies/01_natural_relevance/` — benign ecological relevance and generator breadth
- `studies/02_controlled_source_relocation/` — 24-base USER→TOOL matched intervention
- `studies/03_matched_unauthorized_comparison/` — same-function authorization-changing control
- `studies/04_threshold_frontier/` — complete deterministic scalar sweep
- `studies/05_agentwatcher/` — paired gate study and separate ON/OFF population
- `studies/06_attriguard/` — route exposure, later review, and aggregate block outcome
- `studies/07_causalarmor/` — calibrated reconstruction and benign activation audit
- `studies/08_live_end_to_end/` — 420 live executions, continuation, and later inspection
- `studies/09_evaluation_replay/` — corrected three-model replay
- `figures/` — final figure PDFs and Python producers
- `verification/` — deterministic verification outputs/tools
- `reproduction/` — full-rerun orchestration
- `third_party/` — source-bound external implementations
- `supporting_material/` — provenance, hardening, logs, historical support, and source coverage

## Historical identifiers

The original experiment tree used top-level names such as `A14`, `N3`, `R2B`, `N6`, and `P2B`. These identifiers are preserved inside frozen protocols/results for provenance but no longer dominate repository navigation.

`LEGACY_PATH_MAP.tsv` records every relocated top-level path.

During a fresh rerun, `reproduction/materialize_legacy_worktree.py` reconstructs the historical top-level layout inside the disposable run worktree. This lets the frozen experiment scripts execute without forcing the public repository to retain the historical flat directory layout.

## Provenance

`supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv` accounts for the original codebase artifact files and records their final distributed locations. Identity-bearing Git metadata remains the documented exclusion.

`SHA256SUMS.txt` protects the final distributed package.
