# A14-MINIMAL Pre-Freeze Amendment 01 — Exhaustive Base-Quartet Human Audit

**Timing:** before final A14-MINIMAL protocol freeze and before any A14 scorer/model outcome.

## Motivation

The original pre-freeze construct audit contained 16 pairwise judgments: one complete set of four factorial edge types on the `_00` base from each of the four action families. That validates the transformation templates, but it does not manually inspect every instantiated base.

To make the construct-validity argument easier to defend, this amendment adds an **exhaustive 24-base four-cell human audit**. Every base is displayed with all four factorial cells (`USER_ID×SHAM`, `USER_ID×ECHO`, `TOOL_ID×SHAM`, `TOOL_ID×ECHO`) and receives one human judgment covering the full quartet. Thus all **96/96 scientific conditions** are manually reviewed in their within-base factorial context.

## What changes

- Add `A14M_01b_base_quartet_audit_cli.py`.
- Add deterministic `human_base_quartet_audit_TEMPLATE.jsonl` derived from the exact existing 96-condition corpus.
- Add human result file `human_base_quartet_audit.jsonl`.
- Final freeze now requires both:
  - original pairwise audit: 16/16 TRUE;
  - exhaustive base-quartet audit: 24/24 TRUE.

## What does NOT change

No scientific condition, wording in the 96 experimental prompts, target action, factor level, hypothesis, estimand, inference rule, scorer identity, token map, ablation, or scoring-plan row is changed by this amendment.

The new audit is a **construct-validity check**, not a new outcome and not statistical sampling of model behavior.

## Audit provenance

The audit rubric is author-defined with AI-assisted drafting. The displayed items are mechanically instantiated by code from the exact pre-outcome factorial corpus. Final pass/fail judgments are made by the human author. AI assistance, when used during deliberation, is advisory only.
