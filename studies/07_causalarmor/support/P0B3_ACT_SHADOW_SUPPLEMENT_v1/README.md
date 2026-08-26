# P0b-3-ACT shadow-serialization supplement v1

Purpose: complete the secondary shadow-serialization benign-vs-attack split already specified in canonical dossier v114 §1.6.8. This package makes zero model/network calls.

Important: run `P0B3_ACT_SHADOW_00_freeze.py` first. It validates only input identity/schema/types/denominators and does **not** aggregate benign/attack shadow outcomes. Then run `P0B3_ACT_SHADOW_01_run.py` unchanged.

The shadow endpoint is the already-frozen `shadow_any_flag` corresponding to `COMPLETION_PLUS_TOOL_CALL`; the overall frozen P0b-3 shadow count is already known as 538/624. This supplement only reveals its benign/attack decomposition. It is descriptive secondary sensitivity, not a second intervention arm.
