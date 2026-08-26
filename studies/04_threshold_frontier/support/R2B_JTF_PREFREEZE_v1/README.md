# R2B_JTF_PREFREEZE_v1

Zero-model-call author-run package for **R2B-JTF-v1**, the joint threshold consistency × matched-discrimination frontier.

## Scientific role
This closes the direct-threshold question left open by the benign-only A14 threshold sweep:

> Can threshold tuning jointly improve authorization-equivalent benign consistency and matched AUTH-vs-ALT discrimination on the same 24-base construct?

The underlying A14/N3 scores already exist. Therefore this is **post-hoc deterministic analysis**, not a new confirmatory model experiment. The two-stage freeze prevents analysis-rule drift before the author-run frontier is generated.

## Frozen inputs expected under `PROJECT_ROOT`

```text
a14_minimal_factorial/scorer_llama/condition_scores.jsonl
a14_minimal_factorial/scorer_gemma/condition_scores.jsonl
N3_PREFREEZE_AUTHOR_v1_1/science_llama/SCIENCE_SCORES.jsonl
N3_PREFREEZE_AUTHOR_v1_1/science_gemma/SCIENCE_SCORES.jsonl
N3_PREFREEZE_AUTHOR_v1_1/N3_FREEZE.json
N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json
```

Their expected hashes are locked in the code. Any drift aborts.

## Stage 1 — freeze only
Copy this entire directory into the current project root as `R2B_JTF_PREFREEZE_v1/`.

Then:

```bash
cd /path/to/current/project
bash R2B_JTF_PREFREEZE_v1/freeze_R2B_JTF_v1.sh "$PWD" R2B_JTF_AUTHOR_v1 \
  | tee R2B_JTF_FREEZE_AUTHOR_v1.log
```

This stage validates the census/lineage, hashes inputs and implementation, writes `R2B_JTF_FREEZE.json`, and **does not calculate any frontier outcome**.

After it passes, preserve the freeze log/hash. Do not edit the package.

## Stage 2 — analyze + verify
The analysis is fast and makes no network/model calls. For the project's background/log discipline:

```bash
nohup bash R2B_JTF_PREFREEZE_v1/analyze_R2B_JTF_v1.sh "$PWD" R2B_JTF_AUTHOR_v1 \
  > R2B_JTF_ANALYZE_AUTHOR_v1.log 2>&1 &
echo $! > R2B_JTF_ANALYZE_AUTHOR_v1.pid
cat R2B_JTF_ANALYZE_AUTHOR_v1.pid
```

Follow with:

```bash
tail -f R2B_JTF_ANALYZE_AUTHOR_v1.log
```

## Expected outputs

```text
R2B_JTF_AUTHOR_v1/
├── R2B_JTF_FREEZE.json
├── R2B_JTF_FRONTIER_llama.csv
├── R2B_JTF_FRONTIER_gemma.csv
├── R2B_JTF_RESULTS.json
├── R2B_JTF_REPORT.md
├── R2B_JTF_MANIFEST.json
├── RUN_COMPLETE.json
└── VERIFY_REPORT.json
```

## Hard stop
After Stage 2, **do not start AW-N3-v1**. Provide:

- the entire `R2B_JTF_AUTHOR_v1/` directory;
- `R2B_JTF_FREEZE_AUTHOR_v1.log`;
- `R2B_JTF_ANALYZE_AUTHOR_v1.log`;
- the package hash file.

The next sequence is raw/code/result audit → canonical update → buried/under-utilized-result audit → blueprint threshold/visual update → only then decide whether AW-N3 proceeds unchanged.
