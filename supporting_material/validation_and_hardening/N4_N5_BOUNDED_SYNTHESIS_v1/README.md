# N4/N5 Bounded Synthesis v1

Zero-model-call synthesis of already-closed evidence.

Run from `/home/anon_/ratchet/phase0_pilot`.

Required existing inputs:
- `a14_minimal_factorial/analysis/results.json`
- `a14_minimal_factorial/threshold_aivr_v1/results.json`
- `a15a_selectivity_consequence/results.json`
- `a15b0_architecture_boundary/analysis_results.json`
- `attriguard_a14_v2/scientific_v1/SCIENTIFIC_ANALYSIS.json`
- `P2_AGENTWATCHER_NODEFENSE_RUN_v1/P2_ANALYSIS.json`
- `P0B3_CAUSALARMOR_LIVE_RUN_v1/P0B3_ANALYSIS.json`
- `N3_COMPLETE_AUTHOR_v1_2.tar.gz`
- `b1_a12_backbone_replication_c0_v2/combined_results.json`
- `P0B3_ACT_RUN_v1/P0B3_ACT_RESULT.json`
- `P0B3_ACT_SHADOW_RUN_v1/P0B3_ACT_SHADOW_RESULT.json`

Commands:

```bash
python3 -u N4_N5_BOUNDED_SYNTHESIS_v1/N4_N5_00_collect_validate.py   2>&1 | tee N4_N5_collect.log

python3 -u N4_N5_BOUNDED_SYNTHESIS_v1/N4_N5_01_synthesize.py   2>&1 | tee N4_N5_synthesis.log
```

Expected final line:
`[N4/N5-01] next=N2-NEC adjudication`

No model or network calls are made. This package does not authorize N2.
