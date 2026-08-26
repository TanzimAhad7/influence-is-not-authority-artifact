# E2E-ATTR-AUTH v1 — Phase A1 Start Here

This is the first executable pre-outcome step under `USENIX27_FINAL_EXPERIMENT_FREEZE_E2E_ATTRIGUARD_v4_FINAL_CODING_FREEZE_RECONCILED.md`.

## Scientific status

- ZERO model/provider calls.
- ZERO outcome inspection.
- This phase does **not** freeze final `B`.
- It reproduces the A13 corrected census, enumerates same-function AgentDojo-v1 ALT candidates, applies the frozen one-decision-per-task rule, and performs the source-only multi-call dependency audit.
- The next hard gate is the blinded authorization/effect + AttriGuard threat-model scope audit.

## Put these files on the author server

Create:

```bash
cd /home/anon_/ratchet/phase0_pilot
mkdir -p E2E_ATTR_AUTH_v1/code
```

Place in `E2E_ATTR_AUTH_v1/code/`:

- `E2E_A1_00_build_census.py`
- `E2E_A1_01_multicall_source_audit.py`
- `run_E2E_A1_phase0_2.sh`

Place the four current authority documents at project root:

- `CANONICAL_USENIX_RESEARCH_DOSSIER_v140_E2E_SYSTEMS_STORY_RECONCILED.md`
- `USENIX27_MANUSCRIPT_BLUEPRINT_RECONCILED_v20_E2E_SYSTEMS_STORY_RECONCILED.md`
- `USENIX27_SUBMISSION_LEVEL_WRITING_DIAGNOSIS_v8_E2E_COHERENCE_RECONCILED.md`
- `USENIX27_FINAL_EXPERIMENT_FREEZE_E2E_ATTRIGUARD_v4_FINAL_CODING_FREEZE_RECONCILED.md`

The existing project root must also contain the frozen A13 files already used by the paper:

- `A13_C0_INPUT_BUNDLE_v1.zip`
- `A13_C0_HISTORICAL_A13_COMPLETE_v1.zip`
- `A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl`

## Run

This phase is zero-call and short, so foreground execution is appropriate:

```bash
cd /home/anon_/ratchet/phase0_pilot
PROJECT_ROOT="$PWD" bash E2E_ATTR_AUTH_v1/code/run_E2E_A1_phase0_2.sh
```

## Expected hard census anchors

The wrapper will fail before producing a scientific cohort if these do not reproduce exactly:

- AgentDojo `0.1.35`
- benchmark `v1`
- corrected combined rows: `73`
- primary-valid decisions: `29`
- distinct primary-valid natural tasks: `25`

## Independent ChatGPT verification result — NOT author evidence

Using the uploaded project snapshot and exact frozen inputs, the code currently reproduces:

- `29` primary-valid decisions / `25` tasks;
- `18` tasks with at least one same-function AgentDojo-v1 ALT candidate after the frozen one-decision-per-task tiebreak;
- `11` strict single-call candidate tasks;
- `7` selected multi-call candidates requiring source audit;
- source audit: `3 PASS`, `4 FAIL`, `0 PENDING`;
- preliminary retained after source audit: `14` tasks;
- the four source-audit exclusions are the Slack `add_user_to_channel` cases whose selected malicious call requires the prior malicious `invite_user_to_slack` call to create Fred.

These are **verification expectations only**. The author-run outputs are the provenance-bearing outputs.

## Do not proceed to model science

After Phase A1 completes, stop. Do not run AttriGuard or the victim model.

Send back the complete directory:

`E2E_ATTR_AUTH_v1/prefreeze/phase0_2_author_run/`

The next step is to build and freeze the blinded rater packet / scope audit from the author-run census.
