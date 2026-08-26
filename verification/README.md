# Verification

The supported deterministic verification entry point is at the repository root:

```bash
bash VERIFY.sh
```

It re-derives and cross-checks the manuscript-bearing quantities from the frozen evidence and then checks package integrity and source-tree coverage.

Expected scientific summary:

```text
SUMMARY: 56 PASS / 0 FAIL / 56 total
RESULTS_ONLY_VERIFY=PASS
```

The machine-readable output produced by a run is written to `artifact_outputs/verification/` and is intentionally not part of the frozen package.

An older 45-claim packaging-time suite is preserved only for provenance under `supporting_material/legacy_verification/`; it is not the supported verification interface for this release.
