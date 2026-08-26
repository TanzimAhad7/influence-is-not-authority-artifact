# B1 C0 v2 Runbook

1. Verify package hashes.
2. Run `B1_C0_00_amend_freeze.py`. This is zero-call and must report 55 tasks / 73 decisions.
3. Start the existing Llama scorer on port 8110.
4. Load `.env` so `OPENROUTER_API_KEY` is present.
5. Run both `--preflight-only` commands.
6. Optionally run the frozen development-only smoke for both backbones.
7. Run GPT-4o once, then Claude Sonnet 4.5 once.
8. Run `B1_C0_02_analyze.py` only after both complete.

Do not modify or delete `b1_a12_backbone_replication/`; it is the immutable historical 52-task freeze.
