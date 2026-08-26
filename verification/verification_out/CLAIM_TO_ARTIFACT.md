# Claim → Artifact

Every number the manuscript claims, the file it is derived from, and its verification status.
Regenerate with `verify_all_claims.py`.

| id | claim | value | source | status |
|---|---|---|---|---|
| `A14.P1.llama.mean` | A14 P1 mean (llama) | `-1.1797316186554594` | `results.json` | PASS |
| `A14.P1.llama.neg` | A14 P1 negative-sign count (llama) | `24` | `results.json` | PASS |
| `A14.P1.gemma.mean` | A14 P1 mean (gemma) | `-1.0111624004850248` | `results.json` | PASS |
| `A14.P1.gemma.neg` | A14 P1 negative-sign count (gemma) | `24` | `results.json` | PASS |
| `A14.flips.reverse_zero` | A14 tau=0 reverse flips (flag->allow) are zero | `0` | `results.json` | PASS |
| `N3.D_discriminant_gap.llama.mean` | N3 D_discriminant_gap mean (llama) | `0.6545401550713091` | `N3_ANALYSIS.json` | PASS |
| `N3.D_discriminant_gap.llama.pos` | N3 D_discriminant_gap positive count (llama) | `23` | `N3_ANALYSIS.json` | PASS |
| `N3.P_supported_property_shift.llama.mean` | N3 P_supported_property_shift mean (llama) | `-0.5247327485826405` | `N3_ANALYSIS.json` | PASS |
| `N3.P_supported_property_shift.llama.pos` | N3 P_supported_property_shift positive count (llama) | `7` | `N3_ANALYSIS.json` | PASS |
| `N3.Q_action_controlled_selectivity.llama.mean` | N3 Q_action_controlled_selectivity mean (llama) | `-0.3709166390461613` | `N3_ANALYSIS.json` | PASS |
| `N3.Q_action_controlled_selectivity.llama.pos` | N3 Q_action_controlled_selectivity positive count (llama) | `0` | `N3_ANALYSIS.json` | PASS |
| `N3.T_manipulation.llama.mean` | N3 T_manipulation mean (llama) | `0.5077978034986576` | `N3_ANALYSIS.json` | PASS |
| `N3.T_manipulation.llama.pos` | N3 T_manipulation positive count (llama) | `24` | `N3_ANALYSIS.json` | PASS |
| `N3.D_discriminant_gap.gemma.mean` | N3 D_discriminant_gap mean (gemma) | `0.5039115492763485` | `N3_ANALYSIS.json` | PASS |
| `N3.D_discriminant_gap.gemma.pos` | N3 D_discriminant_gap positive count (gemma) | `14` | `N3_ANALYSIS.json` | PASS |
| `N3.P_supported_property_shift.gemma.mean` | N3 P_supported_property_shift mean (gemma) | `-0.5072508512086761` | `N3_ANALYSIS.json` | PASS |
| `N3.P_supported_property_shift.gemma.pos` | N3 P_supported_property_shift positive count (gemma) | `1` | `N3_ANALYSIS.json` | PASS |
| `N3.Q_action_controlled_selectivity.gemma.mean` | N3 Q_action_controlled_selectivity mean (gemma) | `-0.4746909060911159` | `N3_ANALYSIS.json` | PASS |
| `N3.Q_action_controlled_selectivity.gemma.pos` | N3 Q_action_controlled_selectivity positive count (gemma) | `0` | `N3_ANALYSIS.json` | PASS |
| `N3.T_manipulation.gemma.mean` | N3 T_manipulation mean (gemma) | `0.5371537229857792` | `N3_ANALYSIS.json` | PASS |
| `N3.T_manipulation.gemma.pos` | N3 T_manipulation positive count (gemma) | `24` | `N3_ANALYSIS.json` | PASS |
| `N6.route.AUTH.exact_rate` | N6 exact-shadow survival rate (AUTH) | `0.2917` | `N6_ANALYSIS.json` | PASS |
| `N6.route.ALT.exact_rate` | N6 exact-shadow survival rate (ALT) | `0.575` | `N6_ANALYSIS.json` | PASS |
| `N6.route.asymmetry` | ALT reaches exact-shadow survival N times as often as AUTH | `1.97` | `N6_ANALYSIS.json` | PASS |
| `N6.block.AUTH` | N6 AUTH block rate | `0.4708333333333333` | `N6_ANALYSIS.json` | PASS |
| `N6.block.ALT` | N6 ALT block rate | `0.3625` | `N6_ANALYSIS.json` | PASS |
| `E2E.n_rows` | E2E total scientific runs | `420` | `RUN_ROWS.jsonl` | PASS |
| `E2E.all_success` | E2E runs with status SUCCESS | `420` | `RUN_ROWS.jsonl` | PASS |
| `E2E.n_cases` | E2E inferential units (natural tasks) | `14` | `RUN_ROWS.jsonl` | PASS |
| `E2E.delta_dir.point` | Delta_dir point estimate | `-0.2429` | `RUN_ROWS.jsonl` | PASS |
| `E2E.delta_dir.ci_lo` | Delta_dir bootstrap CI lower | `-0.4714` | `RUN_ROWS.jsonl` | PASS |
| `E2E.delta_dir.ci_hi` | Delta_dir bootstrap CI upper | `-0.0429` | `RUN_ROWS.jsonl` | PASS |
| `E2E.delta_dir.signs` | Delta_dir sign counts (pos,tie,neg) | `(1, 8, 5)` | `RUN_ROWS.jsonl` | PASS |
| `E2E.Z.conflict_off` | selected-ALT rate, CONFLICT/OFF | `0.2429` | `RUN_ROWS.jsonl` | PASS |
| `E2E.Z.conflict_on` | selected-ALT rate, CONFLICT/ON | `0.0286` | `RUN_ROWS.jsonl` | PASS |
| `E2E.discord.total` | LIVE-EVAL-DISCORD total discordance | `18` | `RUN_ROWS.jsonl` | PASS |
| `E2E.benign.CLEAN` | CLEAN ON-OFF PAEF contrast | `-0.0857` | `RUN_ROWS.jsonl` | PASS |
| `E2E.benign.ALIGNED` | ALIGNED ON-OFF PAEF contrast | `-0.1143` | `RUN_ROWS.jsonl` | PASS |
| `MECH.privileged_total` | privileged calls in defended arm | `168` | `RUN_ROWS.jsonl` | PASS |
| `MECH.unaudited` | privileged calls executed without audit | `18` | `RUN_ROWS.jsonl` | PASS |
| `MECH.qualifying_ctx` | unaudited calls with prior qualifying external context | `18` | `RUN_ROWS.jsonl` | PASS |
| `MECH.dualuse.paef1` | unaudited executions completing the authorized effect | `15` | `RUN_ROWS.jsonl` | PASS |
| `MECH.dualuse.z1` | unaudited executions realizing the unauthorized effect | `2` | `RUN_ROWS.jsonl` | PASS |
| `MECH.function_mix` | unaudited privileged functions | `{'send_money': 5, 'send_direct_message': 2, 'invite_user_to_slack': 10, 'post_webpage': 1}` | `RUN_ROWS.jsonl` | PASS |
| `SRC.AttriGuard.py` | source hash: AttriGuard.py | `6d28e2208efbd521bf3f2e90c553e57b11c786e65564eababacb8cdf4f8050d8` | `AttriGuard.py` | PASS |

## Six-cell tables (mandatory reporting)


**PAEF**

| cell | value |
|---|---|
| ALIGNED/OFF | 60/70 |
| ALIGNED/ON | 52/70 |
| CLEAN/OFF | 41/70 |
| CLEAN/ON | 35/70 |
| CONFLICT/OFF | 38/70 |
| CONFLICT/ON | 47/70 |

**Z**

| cell | value |
|---|---|
| ALIGNED/OFF | 0/70 |
| ALIGNED/ON | 0/70 |
| CLEAN/OFF | 0/70 |
| CLEAN/ON | 0/70 |
| CONFLICT/OFF | 17/70 |
| CONFLICT/ON | 2/70 |

**utility**

| cell | value |
|---|---|
| ALIGNED/OFF | 60/70 |
| ALIGNED/ON | 50/70 |
| CLEAN/OFF | 46/70 |
| CLEAN/ON | 39/70 |
| CONFLICT/OFF | 40/70 |
| CONFLICT/ON | 46/70 |
