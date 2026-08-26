# P2b-XM-CI v1.2 — pre-outcome verification report

## Disposition

This package supersedes the first pre-outcome v1.0 package **before any corrected scientific generation**. v1.3 remains immutable historical provenance.

## Reproduced v1.3 failure mechanism

Using the exact saved v1.3 raw generations and the original `canonical_json_adapter.parse_candidate_text`, the silent no-call/no-parser-error counts reproduce as:

- Llama: 75/130
- Gemma: 130/130
- Qwen: 90/130
- Total: 295/390

The original adapter returned `([], None)` for nonempty completions not starting with `{` or `[`, so call-shaped narrated/fenced/historical-marker outputs could be observationally merged with genuine no-action.

## Corrected-interface checks

- Candidate output uses one common JSON-schema-constrained action envelope for all three families.
- Historical assistant actions use the same action-envelope grammar as candidate output.
- Historical assistant natural-language content is preserved inside `content` even when the turn also contains tool calls.
- Genuine no-action requires an explicit parsed `action_type=text` envelope with zero calls.
- Empty/non-JSON/schema-invalid output is `FORMAT_INSTRUMENT_VIOLATION`; branch-inconsistent output is `ACTION_CONTRACT_VIOLATION`. Neither is relabeled as genuine no-action.
- Historical tool results remain explicitly labeled `event_type=tool_result` and the system prompt states that they are observations, not user instructions.
- Action-local validity and downstream frozen-continuation utility are measured separately.
- H-SLOT uses the unchanged v1.3 taxonomy and pre-specified directions.
- Scientific population files and taxonomy are byte-identical to v1.3.
- Excluded synthetic stress cases cover long histories, multiple prior actions, open text, date/time, reference identity, branch progression, role adjacency, genuine no-action, tool-result/user adjacency, historical assistant prose+tool calls, and adjacent assistant tool envelopes.

## Important pre-run correction discovered during verification

The first v1.0 candidate adapter dropped historical assistant prose whenever the same assistant turn contained tool calls. That would have changed the replay prefix. v1.1 fixes this generically by retaining that prose in the common envelope and adds excluded synthetic tests for the invariant. Do not use the superseded v1.0 package.

## What remains to be verified live

Offline review cannot establish model-family behavior under constrained decoding. Before the global scientific freeze, the excluded technical stress preflight must pass on the exact pinned Llama, Gemma, and Qwen servers. Only after all three pass may `P2b_CI_02_freeze_global.py` create the scientific freeze.


## Client-stack freeze

The excluded technical preflight records the exact Python, OpenAI client, `jsonschema`, and `requests` versions. The global freeze requires the same stack across all three technical preflights, and the arm freeze/baseline abort on client-stack drift. This prevents request-serialization changes from silently changing the scientific instrument.


## Live excluded-preflight amendment: v1.1 → v1.2

Before any global freeze or corrected scientific generation, the first live v1.1 Llama technical suite returned 9/10. The sole failure was not an interface failure: `stress_long_history_open_text` returned `PARSED_TOOL`, `interface_error=None`, the correct `write_synthetic_note` tool, `priority=7`, `reference_id=SYN-LONG-FINAL`, and schema-valid text. The only exact-value difference was expected Unicode `✓` versus generated `✅`.

This falsified the v1.1 **technical gate definition**, not the common constrained interface. v1.1 required exact synthetic envelope equality and therefore conflated instrument validity with semantic replay accuracy. v1.2 changes only the excluded technical pass predicate: branch/tool-path/schema validity gates the instrument; exact synthetic values remain diagnostic. The same general rule applies to every excluded case and every model. The candidate interface, scientific inputs, model revisions, H-SLOT, action-local endpoint/gate, downstream endpoint/gate, and all 26 scientific contexts remain unchanged.

The v1.1 9/10 artifact must be retained as technical provenance. It cannot be reused as a v1.2 preflight because `P2b_CI_02_freeze_global.py` binds each preflight to the exact current interface/preflight source hashes. All three model preflights must be rerun on v1.2.
