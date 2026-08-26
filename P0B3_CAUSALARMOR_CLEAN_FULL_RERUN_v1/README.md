# P0b-3 CausalArmor Clean Full Rerun v1

## Purpose

Run a **fresh 0/1046 P0b-3 execution** after the author-run Attempt 0 hit a local
vLLM serving-capacity hard stop at 992/1046.

Attempt 0 is provenance only. It is not deleted, repaired in place, or used to choose
between scientific outcomes.

The clean rerun uses the original frozen P0b-3 scientific package and populations.
The only runtime finalization is:

`vLLM max_model_len: 16384 -> 32768`

The following remain unchanged:

- Gemma repo: `google/gemma-3-12b-it`
- Gemma revision/tokenizer revision: `96b6f1eccf38110c56df3a15bffe176da04bfd80`
- dtype: bfloat16
- tensor parallelism: 2
- proxy endpoint/model identity
- ACTION_ONLY primary serialization
- COMPLETION_PLUS_TOOL_CALL shadow serialization
- tau = 0
- 97 benign / 949 primary attack / 629 nested sensitivity populations
- Gemini agent/sanitizer model IDs and OpenRouter route
- frozen calibration gates
- original live science/analyzer code

## Research-integrity status

Attempt 0 is classified as:

**TECHNICAL_ABORT_PRE_DISPOSITION / 992_OF_1046 / PROVENANCE_ONLY**

The decision to run Attempt 1 from scratch was made before any Attempt-0 aggregate
ASR/BU/UA/calibration disposition was computed or used for decision-making.

Attempt 1 is designated:

**CLEAN_FULL_RERUN / SOLE_PRIMARY_P0B3_EXECUTION_IF_COMPLETE_AND_INTEGRITY_PASS**

Do not compare Attempt 0 and Attempt 1 and select the more favorable outcome.
Do not rerun Attempt 1 again merely because its result is unfavorable.

## Expected project layout

Place this package beside:

- `P0B3_CAUSALARMOR_LIVE_v1/`
- `P0B3_CAUSALARMOR_LIVE_v1.zip`
- `P0B3_CAUSALARMOR_CALIBRATION_FREEZE_COMPLETE_v1.zip`

under the project root.

The clean run output remains:

`P0B3_CAUSALARMOR_LIVE_RUN_v1/`

because the original frozen scripts expect that canonical path. The archive script first
moves Attempt 0 out of that path into `P0B3_AUTHOR_RUN_HISTORY/`.

## Reviewer artifact rule

The final reviewer artifact will expose only the clean finalized 32K path. Attempt 0 and
the capacity incident remain under read-only provenance/history.
