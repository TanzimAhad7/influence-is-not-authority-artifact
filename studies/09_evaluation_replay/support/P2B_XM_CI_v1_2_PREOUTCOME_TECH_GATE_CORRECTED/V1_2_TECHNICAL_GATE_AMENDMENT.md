# P2b-XM-CI v1.2 — pre-outcome technical-gate amendment

- v1.1 first live Llama excluded preflight: 9/10.
- Sole failing case: `stress_long_history_open_text`.
- Interface result: `PARSED_TOOL`, no interface error, correct tool/call structure, valid schema.
- Exact semantic difference: expected `✓`, generated `✅` in open text.
- Interpretation: v1.1 technical pass predicate conflated instrument validity with synthetic semantic replay.
- v1.2 technical PASS: parsed/branch/tool-path/schema validity.
- Exact synthetic value equality: diagnostic only.
- Scientific inputs/model revisions/candidate interface/action-local gate/downstream gate/H-SLOT: unchanged.
- Global scientific freeze before amendment: none.
- Corrected scientific generations before amendment: 0.
- Required next step: rerun all three excluded stress suites on exact v1.2 bytes; only 3/3 technical PASS authorizes global freeze.
