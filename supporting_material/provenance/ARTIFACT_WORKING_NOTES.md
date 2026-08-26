# USENIX Security '27 Working Artifact Base

This directory is a **working reviewer-artifact derivative** of the private research workspace. It is intentionally conservative: paper-bearing producers, frozen inputs, saved raw/results data, deterministic analyzers, supporting provenance, and source-locked external dependencies were copied while the private historical cleanup archive and cleanup machinery were excluded.

## Source snapshot

- Source archive: `phase0_pilot_for_chatgpt.tar(20260814-173429).gz`
- Source SHA-256: `51f65b74a1841a349b48460504a799e48086a5a81509098cf57dd8de92959193`
- Source files: 5,404
- Copied source files: 4,085
- Excluded source files: 1,319
  - private `archive/`: 1,292
  - old cleanup machinery: 16
  - obsolete P7 local-preflight material: 11

Exact source inclusion and exclusion decisions are recorded in:

- `ARTIFACT_SOURCE_INCLUDE_MANIFEST_v1.tsv`
- `ARTIFACT_SOURCE_EXCLUDE_MANIFEST_v1.tsv`

## Six compressed containers intentionally retained

These are not redundant clutter in the current producer tree; retained code still reads or hash-checks them:

- `A13_C0_HISTORICAL_A13_COMPLETE_v1.zip`
- `A13_C0_INPUT_BUNDLE_v1.zip`
- `N3_COMPLETE_AUTHOR_v1_2.tar.gz`
- `P0B3_CAUSALARMOR_CALIBRATION_FREEZE_COMPLETE_v1.zip`
- `P0B3_CAUSALARMOR_LIVE_v1.zip`
- `external/attriguard_zenodo_v1/usenix-artifacts.zip`

## Important: this is NOT the final anonymous artifact yet

Work only inside this derivative for reviewer-facing cleanup. Do not mutate private/frozen originals solely for presentation.

Known finishing work includes:

1. Replace the current root `README.md` (it is an old AttriGuard freeze-only README) with a paper-level reviewer README.
2. Remove/sanitize author paths and identity-bearing metadata in the reviewer derivative. At build time, 103 copied files contained `/home/anon_`.
3. Replace or remove private Git metadata only after retained AgentWatcher reproduction no longer depends on an actual Git checkout.
4. Add final paper figures/tables and a claim-to-artifact map.
5. Add one clean reviewer reproduction entrypoint and fresh-directory verification.
6. Perform the final P7/current-literature/manuscript claim audit on the finished derivative.

The directory structure has otherwise been preserved deliberately so producer-to-data lineage remains easy to trace during this finishing phase.
