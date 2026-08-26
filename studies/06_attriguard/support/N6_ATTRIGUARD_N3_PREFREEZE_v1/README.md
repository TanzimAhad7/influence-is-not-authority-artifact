# N6 AttriGuard × N3 prefreeze package

**This package makes zero model/API calls.** It builds and freezes the highest-value one-experiment novelty extension without revealing any AttriGuard×N3 verdict.

Run from the project root containing `N3_COMPLETE_AUTHOR_v1_2.tar.gz`, `external/attriguard_zenodo_v1/usenix-artifacts.zip`, the extracted official source, and `ATTRIGUARD_A14_V2_01_adapter.py`.

```bash
python3 -u N6_ATTRIGUARD_N3_PREFREEZE_v1/N6_00_build_design.py 2>&1 | tee N6_00_build.log
python3 -u N6_ATTRIGUARD_N3_PREFREEZE_v1/N6_01_scope_audit_cli.py 2>&1 | tee N6_01_scope_audit.log
python3 -u N6_ATTRIGUARD_N3_PREFREEZE_v1/N6_02_freeze_protocol.py 2>&1 | tee N6_02_freeze.log
```

After `N6_02` says `PREFREEZE PASS`, **STOP**. Do not make scientific calls. Archive and upload:

```bash
tar -czf N6_ATTRIGUARD_N3_PREFREEZE_AUTHOR_v1.tar.gz \
  N6_ATTRIGUARD_N3_PREFREEZE_v1 \
  N6_ATTRIGUARD_N3_PREFREEZE_v1_out \
  N6_00_build.log N6_01_scope_audit.log N6_02_freeze.log
sha256sum N6_ATTRIGUARD_N3_PREFREEZE_AUTHOR_v1.tar.gz \
  | tee N6_ATTRIGUARD_N3_PREFREEZE_AUTHOR_v1.tar.gz.sha256
```

The science runner is intentionally not included until the author prefreeze is independently audited.
