# A15a — Selectivity / Sanitizer Consequence

## Why this experiment exists

A13 already measured attribution on successful benign AgentDojo trajectories. A15a does **not**
pretend that those attribution outcomes are newly preregistered. Instead, it freezes the complete
A13 `primary_valid` benign decision corpus and asks the operational question:

> When the paper-faithful tau=0 rule activates on these already-successful benign decisions, how
> often does the expensive sanitizer stage run, how many external generation calls does it create,
> and what sanitizer wall-clock cost is added in this deployment?

The CausalArmor paper states that its efficiency comes from selectively triggering a capable
sanitizer only when necessary. This package uses the paper's Appendix D.1 sanitizer prompt and
Gemini-2.5-Flash model identifier. The access route is OpenRouter, not the paper's Vertex AI, so
absolute wall-clock latency is explicitly deployment-specific.

## Scientific boundaries

- Uses all `A13 decisions.jsonl` rows with `primary_valid=true` and `development=false`.
- Reuses the frozen A13 SPECIFIED/DELEGATED/PARTIAL labels.
- Primary CausalArmor activation rule at tau=0:
  `flag S iff dS_del > dU_del`; activate decision iff any span flags.
- Does not tune tau.
- No non-execution is counted as defense success.
- The preparation step makes no API/model calls.
- Sanitizer time is a **lower bound** on full defense-path overhead because this package does not
  include attribution recomputation, CoT masking, agent regeneration, or environment execution.
- Lexical/numeric preservation diagnostics are not task utility.

## Run order

1. Keep vLLM OFF.
2. Place these files in `~/ratchet/phase0_pilot/`.
3. Run:

```bash
python3 A15a_00_prepare_freeze.py
```

This freezes `a15a_selectivity_consequence/protocol.json` and emits **no API calls**.

4. Inspect/preserve the output. Then set your existing OpenRouter key in the environment:

```bash
export OPENROUTER_API_KEY='...'
```

5. Run:

```bash
python3 A15a_01_sanitize.py
```

It checkpoints after each job and resumes safely.

6. Analyze:

```bash
python3 A15a_02_analyze.py
```

Outputs:
- `a15a_selectivity_consequence/results.json`
- `a15a_selectivity_consequence/REPORT.md`

## Important

Do not edit `decision_inventory.jsonl`, `sanitizer_jobs.jsonl`, or `protocol.json` after A15a-00.
If the parent A13 files change, A15a-01 fails closed.
