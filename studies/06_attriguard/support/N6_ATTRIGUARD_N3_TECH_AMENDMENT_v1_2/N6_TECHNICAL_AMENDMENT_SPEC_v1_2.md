# N6 technical amendment v1.2 — corrected pre-outcome runtime fidelity hardening

This supersedes the failed zero-call v1.1 engineering preflight package
(SHA-256 `57fd1d5b887422de91161ebcc50401620254123fd5a6021f494d59c29686a830`).

The v1.1 preflight failed before any network/model call because its adapter
incorrectly assumed `N3_BASE_PROJECTION.json` contained a `semantic` block.
The frozen N3 projection intentionally contains action/oracle projection fields only.

v1.2 changes **no scientific population, endpoint, interpretation law, model
route, lambda, survival mode, repeat count, candidate mapping, or frozen N3 context**.

The provider-valid historical resolver `name` is reconstructed only from the
already-frozen N3 context. The trusted USER task and frozen factual resolver
observation are parsed independently and must agree exactly. Any mismatch is a
hard stop.

The exact dual-candidate runtime/provider preflight, structural route
reconstruction, no-network official-core stub tests, and frozen science
runner/analyzer remain as in v1.1.

The released AttriGuard `_last_judge_reason` caveat remains: final
`defense_state.flag` is authoritative; raw reason text is interpreted only on an
actual `FUZZY_JUDGE_PATH`.

This is a pre-outcome technical correction, not a scientific redesign.
