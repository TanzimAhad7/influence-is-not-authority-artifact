# R2B-JTF-v1 — Joint Threshold Consistency × Matched-Discrimination Frontier

**Evidence class:** post-hoc deterministic analysis over frozen A14 + N3 scores; zero new model/provider calls.

**Interpretation rule:** the complete frontier is the result. Do not cherry-pick a threshold.

## LLAMA
- threshold rows: 386
- tau=0: A14 benign flag rate=0.4271; AIVR=0.8333; N3 AUTH flag rate=0.6250; ALT flag rate=0.7500; paired ALT-AUTH=+0.1250 [+0.0417,+0.2083]
- central A14 benign 20%-80% band: 209 threshold rows
- central-band minimum AIVR: 0.5833333333333334

## GEMMA
- threshold rows: 386
- tau=0: A14 benign flag rate=0.5521; AIVR=0.7500; N3 AUTH flag rate=0.7292; ALT flag rate=0.9167; paired ALT-AUTH=+0.1875 [+0.1042,+0.2917]
- central A14 benign 20%-80% band: 237 threshold rows
- central-band minimum AIVR: 0.625

## Reporting boundary
This sweep jointly exposes benign consistency and matched discrimination at every threshold induced by the frozen score support.
Row-wise bootstrap intervals are descriptive uncertainty along a post-hoc full sweep; they are not a license to select one favorable tau and present it as a prospectively tested operating point.
The analysis does not measure end-to-end ASR, utility, sanitizer/regeneration behavior, or generic CausalArmor performance.
