# P2b-XM-CI corrected common-interface joint analysis

Global freeze: `d1bb9ec67f10f392e8a85f05955d109747d9bb105da4b0fb3b8da26e50403345`

| Model | Instrument | Action-local gate | Downstream gate | Separate intervention freeze eligible |
|---|---:|---:|---:|---:|
| llama | PASS | FAIL (38.5%; 10/26) | FAIL (65.4%; 17/26) | NO |
| gemma | PASS | FAIL (26.9%; 7/26) | FAIL (57.7%; 15/26) | NO |
| qwen_canonical | PASS | FAIL (42.3%; 11/26) | FAIL (73.1%; 19/26) | NO |

## H-SLOT (same pre-specified v1.3 directions; corrected instrument)

### OPEN_TEXT_minus_REFERENCE_IDENTITY
- llama: n=8, mean=-27.083%, 95% CI=[-62.500%, +10.417%], instrument_valid=True
- gemma: n=10, mean=-36.667%, 95% CI=[-66.667%, -3.333%], instrument_valid=True
- qwen_canonical: n=12, mean=-37.500%, 95% CI=[-61.111%, -16.667%], instrument_valid=True
- 3/3 negative directional replication (confirmatory only if all instruments valid): **True**

### STRUCTURED_SCALAR_minus_REFERENCE_IDENTITY
- llama: n=3, mean=-33.333%, 95% CI=[-100.000%, +100.000%], instrument_valid=True
- gemma: n=6, mean=-58.333%, 95% CI=[-100.000%, +8.333%], instrument_valid=True
- qwen_canonical: n=5, mean=-60.000%, 95% CI=[-100.000%, -20.000%], instrument_valid=True
- 3/3 negative directional replication (confirmatory only if all instruments valid): **True**

### OPEN_TEXT_minus_STRUCTURED_SCALAR
- llama: n=5, mean=+26.667%, 95% CI=[-46.667%, +93.333%], instrument_valid=True
- gemma: n=8, mean=+16.667%, 95% CI=[-31.250%, +62.500%], instrument_valid=True
- qwen_canonical: n=7, mean=+14.286%, 95% CI=[-38.095%, +66.667%], instrument_valid=True

## Intervention boundary

Eligible model arms for a **separately frozen** intervention: `[]`

**No intervention is authorized or executed by this package itself.**

All three corrected arms are retained regardless of earlier arm outcomes; do not pool these results with Qwen-native v1, canonical-text v1.3, or post-hoc recovered v1.3 estimates as if they shared an instrument.
