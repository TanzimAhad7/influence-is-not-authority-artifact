# E2E-ATTR-AUTH — Integrated final pre-science build

This package replaces the earlier separate A4→A5→… audit cadence. It performs the remaining pre-science engineering as one integrated branch.

## What the first command does

Zero scientific calls. It builds and tests:

- deterministic PAEF specs for all 14 frozen tasks;
- 140 oracle mutation tests;
- CLEAN/ALIGNED/CONFLICT matched renderer;
- deterministic AgentDojo-v1 injection carrier selection;
- official AttriGuard source/version/config locks;
- 420-row randomized schedule (14×3×2×5);
- frozen analysis producer + synthetic self-test;
- scientific runner code and retry/integrity policy.

## What the second command does

A tiny **non-scientific** live technical preflight on permanently excluded `workspace/user_task_0`, once OFF and once AttriGuard ON. It checks that the actual provider/pipeline works and that ON tool results contain AttriGuard defense annotations. It then seals the prefreeze if PASS.

It does **not** use any of the 14 scientific tasks.

## Do not run the science launcher until the consolidated output has been audited once.
