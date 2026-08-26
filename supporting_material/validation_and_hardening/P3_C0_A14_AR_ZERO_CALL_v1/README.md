# P3-C0 + A14-AR zero-call finishing package v1

This package implements the active v122 finishing step without changing any closed science.

## P3-C0

- Input: frozen A13-C0 combined 73-row ledger + frozen extension-result JSON.
- Verifies exact known SHA-256 values before analysis.
- Preserves the frozen A13-C0 primary headline as authoritative.
- Recomputes corrected-29 leave-one-suite / leave-one-task influence and task-span diagnostics.
- Produces a deterministic SVG forest/influence figure.
- Scientific model calls: **0**.

## A14-AR

- Audits the existing Llama/Gemma A14 raw-response ledgers.
- Never modifies `condition_scores.jsonl` or `RUN_COMPLETE.json`.
- Checks the authoritative 96-row score-ledger hashes.
- Parses every recovered raw row and checks full 96-condition coverage.
- When `raw_requests.jsonl` and `score_cache.jsonl` are present, verifies exact cache-key set equality and raw completion token/logprob agreement with the score cache.
- If complete originals are absent, reports that disclosure/recovery remains required rather than requesting a scientific rerun.
- Scientific model calls: **0**.

## Run

From the project root:

```bash
bash /path/to/P3_C0_A14_AR_ZERO_CALL_v1/run_zero_call_finishing.sh "$PWD" "$PWD/BASE_FINISHING_ZERO_CALL_v1"
```

This should be fast and requires no model server, GPU, OpenRouter key, or Hugging Face token.

## Governance

- Keep historical P3 outputs immutable.
- Do not overwrite frozen A14 score/result ledgers.
- Do not rerun A14 science merely because an archived raw copy was truncated.
- Update the canonical dossier only after the author-run outputs are reviewed and independently reconciled.
