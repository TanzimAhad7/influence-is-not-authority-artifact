# Claim-to-Artifact Map

Deterministic verification: **56 PASS / 0 FAIL / 56 total**.

The default verifier makes no model/provider calls and uses only frozen files in this package.

| Claim | Status | Verification | Source |
|---|---|---|---|
| `C1.N_VALID` Corrected natural cohort has 29 valid privileged decisions. | **PASS** | rederived_raw | `A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl` |
| `C1.N_TASKS` Corrected natural cohort spans 25 tasks. | **PASS** | rederived_raw | `A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl` |
| `C1.H` Specified vs delegated user-side dominance contrast. | **PASS** | frozen_analysis_check | `A13_C0_EXTENSION_SCIENCE_v1/A13_C0_EXTENSION_RESULT_v1.json` |
| `B1.BREADTH` Prospective GPT-4o/Claude trajectory breadth under fixed Llama scoring. | **PASS** | frozen_analysis_check | `b1_a12_backbone_replication_c0_v2/combined_results.json` |
| `B1.ROLE` Breadth package records generator/scorer role separation. | **PASS** | frozen_metadata_check | `b1_a12_backbone_replication_c0_v2/protocol.json` |
| `A14.LLAMA` Llama source relocation: 24/24 attack-like, mean and CI. | **PASS** | frozen_analysis_check | `a14_minimal_factorial/analysis/results.json` |
| `A14.GEMMA` Gemma source relocation: 24/24 attack-like, mean and CI. | **PASS** | frozen_analysis_check | `a14_minimal_factorial/analysis/results.json` |
| `A14.LLAMA.SUPPORT_USER` llama user-side support falls on all 24 bases. | **PASS** | rederived_raw | `a14_minimal_factorial/scorer_llama/condition_scores.jsonl` |
| `A14.LLAMA.SUPPORT_TOOL` llama relevant-tool support rises on all 24 bases. | **PASS** | rederived_raw | `a14_minimal_factorial/scorer_llama/condition_scores.jsonl` |
| `A14.GEMMA.SUPPORT_USER` gemma user-side support falls on all 24 bases. | **PASS** | rederived_raw | `a14_minimal_factorial/scorer_gemma/condition_scores.jsonl` |
| `A14.GEMMA.SUPPORT_TOOL` gemma relevant-tool support rises on all 24 bases. | **PASS** | rederived_raw | `a14_minimal_factorial/scorer_gemma/condition_scores.jsonl` |
| `A14.TAU0_AIVR` At tau=0, authorization-equivalent verdict varies on 20/24 Llama and 18/24 Gemma bases. | **PASS** | frozen_analysis_check | `R2B_JTF_AUTHOR_v1/R2B_JTF_RESULTS.json` |
| `N3.LLAMA.D` llama harmless source relocation has larger average displacement than authorization-changing comparison. | **PASS** | frozen_analysis_check | `N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json` |
| `N3.LLAMA.P_SIGNS` llama authorization-changing comparison case-level sign count is heterogeneous. | **PASS** | frozen_analysis_check | `N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json` |
| `N3.LLAMA.QT` llama manipulation/selectivity controls remain directional on 24/24 bases. | **PASS** | frozen_analysis_check | `N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json` |
| `N3.LLAMA.ENDPOINT` llama matched unauthorized ALT endpoint is more attack-like on average than authorized TOOL endpoint. | **PASS** | rederived_raw | `N3_PREFREEZE_AUTHOR_v1_1/science_llama/SCIENCE_SCORES.jsonl` |
| `N3.GEMMA.D` gemma harmless source relocation has larger average displacement than authorization-changing comparison. | **PASS** | frozen_analysis_check | `N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json` |
| `N3.GEMMA.P_SIGNS` gemma authorization-changing comparison case-level sign count is heterogeneous. | **PASS** | frozen_analysis_check | `N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json` |
| `N3.GEMMA.QT` gemma manipulation/selectivity controls remain directional on 24/24 bases. | **PASS** | frozen_analysis_check | `N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json` |
| `N3.GEMMA.ENDPOINT` gemma matched unauthorized ALT endpoint is more attack-like on average than authorized TOOL endpoint. | **PASS** | rederived_raw | `N3_PREFREEZE_AUTHOR_v1_1/science_gemma/SCIENCE_SCORES.jsonl` |
| `R2B.LLAMA.TAU0` llama tau=0 anchor. | **PASS** | frozen_analysis_check | `R2B_JTF_AUTHOR_v1/R2B_JTF_RESULTS.json` |
| `R2B.LLAMA.NROWS` llama full threshold sweep has 386 rows. | **PASS** | rederived_raw | `R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_llama.csv` |
| `R2B.LLAMA.ZERO_BENIGN` llama best unauthorized catch rate among zero-benign operating points. | **PASS** | rederived_raw | `R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_llama.csv` |
| `R2B.LLAMA.CENTRAL_AIVR` llama minimum AIVR in predeclared 20-80% benign band. | **PASS** | rederived_raw | `R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_llama.csv` |
| `R2B.GEMMA.TAU0` gemma tau=0 anchor. | **PASS** | frozen_analysis_check | `R2B_JTF_AUTHOR_v1/R2B_JTF_RESULTS.json` |
| `R2B.GEMMA.NROWS` gemma full threshold sweep has 386 rows. | **PASS** | rederived_raw | `R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_gemma.csv` |
| `R2B.GEMMA.ZERO_BENIGN` gemma best unauthorized catch rate among zero-benign operating points. | **PASS** | rederived_raw | `R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_gemma.csv` |
| `R2B.GEMMA.CENTRAL_AIVR` gemma minimum AIVR in predeclared 20-80% benign band. | **PASS** | rederived_raw | `R2B_JTF_AUTHOR_v1/R2B_JTF_FRONTIER_gemma.csv` |
| `AW.MATCHED_GATE` AgentWatcher aligned discrimination and tested conflict saturation. | **PASS** | rederived_raw | `AW_N3_AUTHOR_v1/AWN3_BASE_EFFECTS.csv` |
| `AW.ON_OFF` Separate AgentWatcher ON/OFF matched-input population. | **PASS** | frozen_analysis_check | `P2_AGENTWATCHER_NODEFENSE_RUN_v1/P2_ANALYSIS.json` |
| `N6.AGGREGATE` AttriGuard aggregate matched block endpoint. | **PASS** | frozen_analysis_check | `n6_attriguard_n3_v1/scientific_v1/N6_ANALYSIS.json` |
| `N6.ROUTES` AttriGuard exact-survival/fuzzy-review route counts. | **PASS** | frozen_analysis_check | `n6_attriguard_n3_v1/scientific_v1/N6_ANALYSIS.json` |
| `N6.FUZZY` Conditional fuzzy-review block counts. | **PASS** | rederived_raw | `n6_attriguard_n3_v1/scientific_v1/N6_RESULTS.jsonl` |
| `P0B3.PRIMARY` CausalArmor-style reconstruction broad-regime calibration. | **PASS** | frozen_analysis_check | `P0B3_CAUSALARMOR_LIVE_RUN_v1/P0B3_ANALYSIS.json` |
| `A15A.ACTIVATION` Benign calibration activation and sanitizer-stage overhead. | **PASS** | frozen_analysis_check | `a15a_selectivity_consequence/results.json` |
| `E2E.CENSUS` Live E2E census and completeness. | **PASS** | rederived_raw | `E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl` |
| `E2E.BOOTSTRAP_FREEZE` Sealed pre-science E2E task-bootstrap procedure. | **PASS** | frozen_metadata_check | `E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build/FREEZE.json` |
| `E2E.PRIMARY` Pre-specified task-level primary interaction is opposite predicted availability-loss direction. | **PASS** | rederived_raw | `E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl` |
| `E2E.SELECTED_ALT` Under CONFLICT, defense reduces selected unauthorized outcome on this cohort. | **PASS** | rederived_raw | `E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl` |
| `E2E.PAEF` Direct CONFLICT PAEF difference is positive in sample but null-compatible. | **PASS** | rederived_raw | `E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl` |
| `E2E.UTILITY_PAEF` Live utility and PAEF disagree on 18/420 executions. | **PASS** | rederived_raw | `E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl` |
| `E2E.CONTINUATION` Blocked-proposal continuation is symmetric: ALT recovery and AUTH loss are both reported. | **PASS** | rederived_raw | `E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl + frozen PAEF specs + raw traces` |
| `E2E.AUDIT_WINDOWS` Exploratory source+trace denominator ladder from raw traces. | **PASS** | rederived_raw | `E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl + raw traces` |
| `E2E.SOURCE_ISOLATION` Deterministic fixed-call isolation reproduces the source-bound audit transition and local patch restores adjudication. | **PASS** | frozen_deterministic_isolation_check | `artifact_support/source_bound_isolation/ATTRIGUARD_AUDIT_TRANSITION_RESULT.json` |
| `REPLAY.LLAMA.GEN` llama generation-level immediate/downstream fidelity counts. | **PASS** | rederived_raw | `P2B_XM_CI_LLAMA_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl` |
| `REPLAY.GEMMA.GEN` gemma generation-level immediate/downstream fidelity counts. | **PASS** | rederived_raw | `P2B_XM_CI_GEMMA_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl` |
| `REPLAY.QWEN.GEN` qwen generation-level immediate/downstream fidelity counts. | **PASS** | rederived_raw | `P2B_XM_CI_QWEN_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl` |
| `REPLAY.CELLS` Across 78 model-decision cells, downstream success can hide immediate action/effect divergence. | **PASS** | rederived_raw | `P2B_XM_CI_*_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl` |
| `SOURCE.ATTRIGUARD_SHA` Frozen AttriGuard source identity is consistent across provenance and deterministic isolation evidence. | **PASS** | source_identity_check | `artifact_support/ATTRIGUARD_SOURCE_SHA256.txt + artifact_support/source_bound_isolation/ATTRIGUARD_AUDIT_TRANSITION_RESULT.json` |
| `SOURCE.AGENTWATCHER_SHA` Frozen AgentWatcher integration adapter hash. | **PASS** | source_hash | `external/AgentWatcher_armc_runtime_v1/agents/agentdojo/src/agentdojo/agent_pipeline/piarena_defense_adapter.py` |
| `HYGIENE.IDENTITY` No known author/institution identity strings in text-readable artifact files. | **PASS** | hygiene_scan | `entire artifact` |
| `HYGIENE.GIT` No .git directories in artifact. | **PASS** | hygiene_scan | `entire artifact` |
| `HYGIENE.SECRETS` No high-confidence author credential material in artifact package. | **PASS** | hygiene_scan | `entire artifact excluding known synthetic AgentDojo key fixture` |
| `HYGIENE.TRACKING` No common tracking-link parameters or short-link trackers in artifact documentation. | **PASS** | hygiene_scan | `artifact documentation` |
| `HYGIENE.SYMLINKS` No symlinks in artifact. | **PASS** | hygiene_scan | `entire artifact` |
| `HYGIENE.SOURCE_COVERAGE` Complete codebase artifacts/ tree retained except identity-bearing Git metadata. | **PASS** | coverage_check | `SOURCE_ARTIFACT_COVERAGE.tsv` |

## Evidence boundaries

- Natural-cohort results establish ecological relevance in the audited benchmark, not deployment prevalence.
- N3 is a teacher-forced matched construct comparison, not a deployment attack-success estimate.
- AgentWatcher matched-gate evidence is gate-level; the separate ON/OFF population is a different matched-input experiment.
- AttriGuard N6 aggregate outcome precedes route localization; observed reference identity determines routing, but directive-to-reference causality is unresolved.
- Live PAEF is task-level inference; the direct CONFLICT PAEF difference is null-compatible.
- Audit-coverage analysis is exploratory/source-bound and dual-use; it is not an exploit-rate estimate.
- Replay evaluates metric fidelity, not model quality or ranking.
