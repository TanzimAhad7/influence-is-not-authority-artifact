# P2b-XM-CI v1.2.1R Action-Local Oracle Amendment + Technical-Preflight Evidence Reuse

Status: PRE-OUTCOME / ZERO CORRECTED SCIENTIFIC GENERATIONS / SUPERSEDES THE ORIGINAL v1.2 GLOBAL FREEZE.

## Trigger
The v1.2 3-model excluded stress preflights each passed 10/10 and a global freeze was created. Llama post-freeze render then passed 26/26, but arm-freeze action-local self-test halted on 8/26 exact-target replays. All eight had exact target action reproduction and differed only in full-environment equality; they were one send_email and seven create_calendar_event cases.

## Root cause
AgentDojo 0.1.35 generates runtime email timestamps. send_email uses runtime time, and create_calendar_event sends invitation email(s). Exact replay can therefore differ in generated email timestamp values even when requested action semantics and all other effects are identical.

## Correction
The action-local effect comparator canonicalizes only serialized AgentDojo Email timestamp values to a sentinel before full-environment comparison. It retains the timestamp field and remains sensitive to email IDs, recipients, subject/body, status, attachments, calendar state, and every other serialized field. Static regression tests verify timestamp-only differences compare equal and changed email body does not.

## Why the three technical stress suites are not rerun
The Phase-A stress preflight does not import or execute action_local.py. Reuse is permitted only if the exact hashes of all files bound by the stress preflight remain byte-identical: P2b_CI_01_stress_preflight.py, common_action_interface.py, stress_runtime.py, ACTION_ENVELOPE_SCHEMA.json, MODEL_REGISTRY_CI.json, P2B_XM_CI_REVISION_LOCK.json, and inputs/EXCLUDED_STRESS_CONTEXTS.json. The superseding freeze script recomputes these hashes and refuses reuse if any differs.

No scientific generation existed when this amendment was made.
