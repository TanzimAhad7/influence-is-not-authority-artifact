# v1.3 → P2b-XM-CI v1.1 adjudication lineage

This file records why the corrected package exists. It is **not** a source of corrected-run thresholds.

## Preserved v1.3 disposition

- Prospective operational gate status: **FAIL — preserved**.
- Intended cross-model replay-stability inference: **VOID / NON-INTERPRETABLE**.
- H-SLOT: **VOID / UNRESOLVED**.
- No v1.3 intervention was authorized.

The strict output contract was prospectively declared. The later audit does not convert the original gate arithmetic into a retroactive PASS.

## Instrument findings that justify a new experiment

The complete 390-row audit localized a behavioral-interface validity failure:

- the parser returned no call **and no parser error** for any nonempty completion not beginning with `{` or `[`, making ordinary text/no-action observationally indistinguishable from rejected call-shaped output;
- total no-call/no-parser-error rows were 295/390;
- 286/390 were the conservative recoverable-call subset of those rows;
- historical assistant actions were demonstrated with a `HISTORICAL_TOOL_CALLS` marker while the candidate contract demanded bare JSON;
- tool schema descriptions and candidate calls used different wrapper names (`parameters` versus `arguments`);
- historical tool results were transported as ordinary user text;
- output surface varied strongly by model family;
- downstream frozen-continuation utility can be restored by later ORIGINAL continuation calls, so it is not a pure action-local replay measure.

These facts motivate **instrument correction**. They do not license confirmatory rescoring of v1.3.

## Llama provenance correction

The claim that the executed Llama arm was an off-spec post-outcome switch is rejected.

All three scientific freezes record executed registry SHA-256:

`ede7a8e2e4496bd08894967f50d5e88166e0a02e50f09aaf397f92d0944ce5c2`

and the Llama freeze/live command/revision identify:

`meta-llama/Llama-3.3-70B-Instruct`

The Llama-3.3 amendment therefore belongs to the prospectively frozen executed state. The originally distributed v1.3 source ZIP predates that local amendment and is historical packaging, not the authoritative executed model identity.

## Uploaded artifact hashes used for this design review

- complete v1.3 results ZIP: `3002bde540c4e3bb21df09e3c0c022a8ed0b3d6d0b77f196ebdb3e0c1872d01a`
- uploaded v1.3 source package ZIP: `477ba7865f2f02a36eb8cc6e9d264f9401e9d600fa3fa66d42d85527be82b34d`
- 390-row line-by-line audit CSV: `1ce21c17a114309a0732f01b0a20818e883d7fdde5a905b0efec3403d856c287`
- 26-decision forensic matrix CSV: `c648d9ff5cfc349b27a042f694de6e4b622d41700305f1802213c61608c7c297`
- post-hoc slot diagnostics CSV: `42af69dfd65c69ac7e8401716195e6e752c2abd058e4d76d25059ea2fa3032f8`

## What was deliberately *not* carried into the corrected gate

No corrected validity threshold uses post-hoc observations such as expected parse counts, expected no-action counts, expected exact replay ranges, or recovered H-SLOT magnitudes.
