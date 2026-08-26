# N6 AttriGuard × N3 technical amendment v1.2

This supersedes the failed zero-model-call v1.1 preflight. No N6 scientific
outcome was produced by that failure.

Run from `/home/anon_/ratchet/phase0_pilot`:

```bash
python3 -u \
  N6_ATTRIGUARD_N3_TECH_AMENDMENT_v1_2/N6_04_no_model_preflight_and_amend.py \
  2>&1 | tee N6_04_technical_preflight_v1_2.log
```

Expected ending:

```text
[N6-04] v1.2 TECHNICAL PREFLIGHT PASS / ZERO NETWORK-MODEL CALLS
[N6-04] resolver entity cross-check 240/240 PASS
[N6-04] 240/240 frozen schedule adaptations provider-serialize
[N6-04] dynamic official-core dual-candidate stub tests=8/8 PASS
[N6-04] amendment_hash=...
[N6-04] STOP. Upload v1.2 amendment artifacts. Do NOT run N6_05 yet.
```

Then archive:

```bash
tar -czf N6_ATTRIGUARD_N3_TECH_PREFLIGHT_AUTHOR_v1_2.tar.gz \
  N6_ATTRIGUARD_N3_TECH_AMENDMENT_v1_2 \
  N6_ATTRIGUARD_N3_PREFREEZE_v1_out/N6_TECHNICAL_AMENDMENT_v1_2.json \
  N6_04_technical_preflight_v1_2.log

sha256sum N6_ATTRIGUARD_N3_TECH_PREFLIGHT_AUTHOR_v1_2.tar.gz \
  | tee N6_ATTRIGUARD_N3_TECH_PREFLIGHT_AUTHOR_v1_2.tar.gz.sha256
```

Upload those two files.

Do not run `N6_05_run_science.py` until the v1.2 preflight is independently audited.
