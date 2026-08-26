# P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED

Corrected common-interface replication package for the v73 P2b next step.

## Start here

1. Read `PROTOCOL_P2B_XM_CI_v1_2.md`.
2. Follow `P2b_CI_RUNBOOK.md` exactly.
3. Run `P2b_CI_00_static_audit.py`.
4. Run **excluded synthetic technical stress preflights for all three models**.
5. Only after all three technical preflights pass, create `P2B_XM_CI_GLOBAL_FREEZE.json`.
6. After global freeze, do not edit the package under that freeze.
7. Run Llama, Gemma, and Qwen corrected arms regardless of earlier scientific outcomes.
8. Run the joint analysis.
9. Do **not** run an intervention from this package; none is included.

## Why this is a new package

P2b-XM v1.3 retains its prospective operational FAIL, but its intended replay-stability inference is non-interpretable because action-format/recognition variance dominated the intended construct. This package does not rescore v1.3. It prospectively changes the instrument while preserving the scientific population, repeats, original downstream oracle, and H-SLOT hypothesis.

## Main corrections

- one common JSON-schema-constrained action envelope;
- historical assistant actions and candidate output use the same schema;
- explicit tool-result events rather than ambiguous ordinary text;
- explicit genuine no-action vs format/instrument violation;
- excluded synthetic stress validation before science;
- action-local replay validity separated from legacy downstream frozen-continuation utility;
- deterministic effect-equivalence check against the original target action;
- same 26 decisions × 5 repeats × three frozen model revisions;
- H-SLOT re-tested with the original direction/taxonomy/bootstrap;
- all three corrected arms run regardless of earlier scientific FAIL;
- intervention requires a separate prospective freeze.

## File map

- `ACTION_ENVELOPE_SCHEMA.json` — common candidate/history action schema.
- `MODEL_REGISTRY_CI.json` — model/runtime/gate registry.
- `P2B_XM_CI_REVISION_LOCK.json` — exact model/tokenizer revisions.
- `P2B_ARGUMENT_ROLE_TAXONOMY.json` — unchanged v1.3 H-SLOT taxonomy.
- `inputs/EXCLUDED_STRESS_CONTEXTS.json` — synthetic pre-science technical cases.
- `common_action_interface.py` — common history serializer + constrained-output parser.
- `action_local.py` — schema/execution/effect-equivalence replay oracle.
- `p2b_common.py` — preserved downstream frozen-continuation oracle lineage.
- `P2b_CI_00_static_audit.py` — zero-model-call integrity checks.
- `P2b_CI_01_stress_preflight.py` — excluded technical model preflight.
- `P2b_CI_02_freeze_global.py` — creates global scientific freeze.
- `P2b_CI_03_render_preflight.py` — post-freeze zero-generation 26-prefix render check.
- `P2b_CI_04_freeze_arm.py` — live runtime + oracle + arm freeze.
- `P2b_CI_05_run_baseline.py` — corrected 130-row arm execution, resumable.
- `P2b_CI_06_analyze_arm.py` — separate instrument/action-local/downstream gates.
- `P2b_CI_07_argument_role.py` — H-SLOT analysis.
- `P2b_CI_08_joint_compare.py` — three-arm joint analysis.
- `serve_model.sh`, `stop_server.sh` — exact pinned vLLM server helpers.
- `V13_ADJUDICATION_LINEAGE.md` — provenance-only rationale; not a gate source.

## Build validation

`PREOUTCOME_BUILD_VALIDATION.json` records the offline package checks performed before distribution. It explicitly does **not** substitute for the live excluded technical stress preflight.


**Lossless-history invariant:** historical assistant prose is preserved inside the common action envelope even when the same historical turn contains tool calls; the corrected interface must not delete replay-context content.

- `PREOUTCOME_VERIFICATION_REPORT.md` — independent pre-outcome code/artifact verification and the v1.0→v1.1 fidelity correction.

## v1.2 pre-outcome amendment

v1.1 is superseded before science. Its first live excluded Llama preflight was 9/10 only because the technical gate demanded exact synthetic value replay: the common envelope parsed correctly and the sole mismatch was `✓` versus `✅` in open text. v1.2 separates **technical instrument validity** from **synthetic semantic exactness**. Technical PASS now requires parsed/branch/tool-path/schema validity; exact synthetic values remain diagnostic. Scientific inputs, candidate interface, model revisions, H-SLOT, and scientific action-local/downstream gates are unchanged. Zero corrected scientific generations existed at this amendment.
