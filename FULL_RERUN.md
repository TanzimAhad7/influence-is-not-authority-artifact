# Full Rerun Stage Map

The full rerun follows the paper's evidence chain. Run:

```bash
bash RUN_END_TO_END.sh --list
```

Stages:

```text
01_a13_natural                  original benign natural cohort
02_a13_c0_extension             corrected natural-cohort extension/census
03_b1_generator_breadth         GPT-4o / Claude trajectory breadth under fixed Llama scoring
04_a14_controlled_source        controlled USER→TOOL source relocation, Llama + Gemma
05_n3_unauthorized_control      matched same-function unauthorized comparison
06_r2b_threshold_frontier       deterministic complete scalar threshold sweep
07_agentwatcher                 paired AgentWatcher gate study + separate ON/OFF population
08_n6_attriguard_architecture   AttriGuard route/block study
09_causalarmor_calibration      CausalArmor-style reconstruction/calibration
10_live_e2e_attriguard          420 live executions over 14 natural tasks
11_replay                       corrected Llama/Gemma/Qwen evaluation replay
12_figures                      regenerate Figures 1--6
```

Stages 06 and 12 are deterministic and require no provider/model calls. All other stages require the dependencies documented in `REPRODUCE.md`.

The stage wrappers preserve the original scientific entry points. Because the repository is now organized into descriptive study folders, the master runner reconstructs the historical path layout only inside the disposable execution worktree.
