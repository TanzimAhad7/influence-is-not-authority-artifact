# A13-C0 anonymization-only archive rewrite

Two author-run archives required by the original A13-C0 extension runner contained local author paths in logs/audit metadata. The distributed copies replace only known identity/environment strings and tar owner metadata. Science-bearing frozen members used by the extension runner remain byte-identical. The rerun wrapper patches only the two whole-archive SHA constants to the anonymized archive hashes before generating a fresh runner freeze.

## `A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz`

- original research archive SHA-256: `bacedba13f854aebd3168ad020b5123ec889a870d5c03cd1c7f519f0daccd495`
- distributed anonymous archive SHA-256: `a36088527544d5955d3fa26c3e4f59638d7c9514d0fc6323148fad545e216c62`
- members with identity-only text replacement: `3`
  - `A13_C0_V2_1_DEEP_ZERO_CALL_AUDIT.py`
  - `A13_C0_V2_1_AUTHOR_RUN.log`
  - `A13_C0_V2_1_AUTHOR_AUDIT/A13_C0_V2_1_DEEP_AUDIT.json`

## `A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz`

- original research archive SHA-256: `035af5fb370cef996739ec6b99db24e9be66a446050779a5c26242fcdda2396d`
- distributed anonymous archive SHA-256: `9b4f5752df0ca741ab6eb4509569ad1d3ac935a08338f5b5699f17dc616df4df`
- members with identity-only text replacement: `1`
  - `A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_RUN.log`

