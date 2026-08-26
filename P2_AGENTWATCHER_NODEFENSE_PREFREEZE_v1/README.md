# P2 AgentWatcher same-200 defense-disabled baseline — clean pre-outcome package

This package was constructed from the user's current project snapshot and the authoritative v104 P2 requirement.

It runs **one scientific arm only**: the exact frozen `tool_knowledge` 200-pair population with `defense=none`.

Historical frozen AgentWatcher reference:
- utility: `56/200 = 28%`;
- ASR: `0/200`;
- selected pair SHA: `b7c7846baeb5481ef93023d64d0b0ca110dc12f0563d52bb728e7f4ee958b26a`.

The science script does not invoke AgentWatcher's monitor or attribution model. It uses the same historical AgentDojo runtime and requested `gpt-4o-mini` OpenRouter route, but omits `--defense piarena`, which is the existing runtime's native no-defense path.

## Required environment

- existing `/home/anon_/ratchet/phase0_pilot/.venv`;
- existing current project tree matching the frozen manifests;
- either `OPENROUTER_API_KEY` or `OPENAI_API_KEY` containing the OpenRouter credential.

The child science process explicitly sets `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and removes inherited `PIARENA_*` defense variables. No API secret is written to artifacts.

## Run

Use the background command supplied by ChatGPT. `RUN_P2.sh` freezes all inputs before the first scientific API call, runs the 200-pair no-defense arm, validates exact pair-set equality, computes the pre-frozen analysis, verifies hashes, and creates the complete archive.
