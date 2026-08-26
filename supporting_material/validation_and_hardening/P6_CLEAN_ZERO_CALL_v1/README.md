# P6 CLEAN ZERO-CALL v1

Fresh P6 implementation built from the current v103 research state and current project artifact schemas. It does **not** reuse the prior P6 implementation.

P6 is deterministic synthesis only. It performs **0 model/API/GPU calls** and does not create a new estimand. It packages the existing evidence into:

`authorization consistency × benign operating point × malicious discrimination × replay/equivalence validity × selected-population behavior`.

## Upstream prerequisite

The current project snapshot contains the complete AttriGuard 480/480 raw run but may lack its native deterministic analysis output. Before P6, run the existing upstream analyzer:

```bash
python -u ATTRIGUARD_A14_V2_06_analyze_science.py --project-root /home/anon_/ratchet/phase0_pilot
sha256sum attriguard_a14_v2/scientific_v1/SCIENTIFIC_ANALYSIS.json
```

Required SHA-256:

`3b74caf3ff5960fc3ee8a3222975a3d715dd46d9d58b28a06a88c434abeadb65`

P6 consumes the analyzer's **native** `SCIENTIFIC_ANALYSIS.json`; no renamed compatibility copy is used.
