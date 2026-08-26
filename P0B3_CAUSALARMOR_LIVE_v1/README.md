# P0B3_CAUSALARMOR_LIVE_v1

Bound to the author-verified zero-call P0b-3 freeze (completed archive SHA-256 `0ad06fefbbc09d79eadf1e0186570d6181b4b5b22812889cbfed5476ecb0f82c`).

Order:
1. Start the exact frozen Gemma-3-12B-IT vLLM proxy.
2. Run `P0B3_10_live_preflight.py`. It uses only synthetic plumbing checks and executes **zero AgentDojo benchmark episodes**.
3. Only after PASS, run `P0B3_RUN_SCIENCE_THEN_ANALYZE.sh`.
4. Archive package + run directory and return them for independent adjudication before P6.

The science runner checkpoints every completed episode. An unresolved runtime/provider/scorer error stops without imputing PASS/FAIL; rerun the identical command to resume. Do not edit the package or implementation freeze after benchmark outcomes exist.

## AgentDojo 0.1.35 ImportantInstructions compatibility

The installed package's `MODEL_NAMES` registry recognizes `gemini-2.5-flash-preview-04-17` but not the later stable identifier `gemini-2.5-flash`. The official attack uses `pipeline.name` only to render a prose model name. The excluded preflight therefore freezes the recognized alias solely for attack templating and verifies that it renders `AI model developed by Google`; actual agent/sanitizer calls remain `google/gemini-2.5-flash` through OpenRouter.
