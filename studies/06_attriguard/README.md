# 06 — AttriGuard Route and Block Study

## Question

How do reference routing and later review determine the effective security policy?

## Main evidence

- `route_and_block_study/scientific_v1/N6_ANALYSIS.json`
- `route_and_block_study/scientific_v1/N6_RESULTS.jsonl`
- `support/` — prefreeze packages, source-lock/adapter checks, logs, and technical amendments

## Paper result

Across 240 repeated invocations per action type, 113 authorized actions and 87 matched unauthorized actions are blocked overall; the matched confidence interval spans zero.

Unauthorized actions reach exact-reference automatic survival more often, while authorized actions reach the later fuzzy-review path more often. Conditional on later review, unauthorized actions are blocked more often.

## Boundary

Observed reference identity determines the route. The study does not establish that the conflicting directive caused that reference identity.

The source-level implementation finding is version- and configuration-specific.

## Verify

See `CLAIM_TO_ARTIFACT.md` entries `N6.*` and `SOURCE.ATTRIGUARD_SHA`.
