# A14M Threshold / Authorization-Invariance Robustness — R2A

**Status:** post-hoc robustness analysis; no new model calls; original A14 confirmatory status unchanged.

## LLAMA
- tau=0 benign flag rate: 41/96 = 0.427
- tau=0 AIVR_class: 20/24 = 0.833
- tau=0 pairwise AIVR: 61/144 = 0.424
- tau=0 P1_SHAM violation: 2/24 = 0.083
- tau=0 P1_ECHO violation: 17/24 = 0.708
- tau=0 P3_USER violation: 3/24 = 0.125
- tau=0 P3_TOOL violation: 18/24 = 0.750
- minimum AIVR_class among nondegenerate threshold rows: 0.041666666666666664
- nondegenerate threshold rows with AIVR_class>0: 191/191

## GEMMA
- tau=0 benign flag rate: 53/96 = 0.552
- tau=0 AIVR_class: 18/24 = 0.750
- tau=0 pairwise AIVR: 65/144 = 0.451
- tau=0 P1_SHAM violation: 6/24 = 0.250
- tau=0 P1_ECHO violation: 13/24 = 0.542
- tau=0 P3_USER violation: 5/24 = 0.208
- tau=0 P3_TOOL violation: 12/24 = 0.500
- minimum AIVR_class among nondegenerate threshold rows: 0.041666666666666664
- nondegenerate threshold rows with AIVR_class>0: 191/191

## Interpretation constraint
This analysis tests whether the controlled benign invariance failure is confined to tau=0.
It does **not** test whether an alternative threshold preserves attack detection. That is R2B.

Do not cherry-pick a threshold. Report the entire sweep and all tied minimum-AIVR nondegenerate regimes.
