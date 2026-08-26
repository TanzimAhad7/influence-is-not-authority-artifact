# 09 — Evaluation Replay

## Question

Can ordinary downstream task success hide a change in the immediate privileged action or effect?

## Main evidence

- `llama/`
- `gemma/`
- `qwen/`
- `joint/`
- `support/` — corrected replay protocol, model registry, earlier validation branches, and cross-model support

## Scale

```text
78 model-decision cells
5 generations per cell
390 generations total
```

## Paper result

23/78 cells pass the downstream majority check while failing the immediate action/effect check; 22/23 still use the intended tool.

## Boundary

This is an evaluation-fidelity study, not a model leaderboard.

## Verify

See `CLAIM_TO_ARTIFACT.md` entries `REPLAY.*`.
