# N3 discriminant-validity prefreeze v1

**Purpose:** zero-science-call N0-FRZ package for the optional N3 novelty experiment authorized by canonical v110.

## Design

- Reuse the exact 24 A14-Minimal bases and all 96 frozen A14 cells as an in-run nuisance replication.
- For each base and SHAM/ECHO descendant cell, derive a same-family alternate execution value by circular next-base mapping.
- Build two matched TOOL_ID contexts that preserve the original factual tool evidence and append the same directive template:
  - `ALIGNED`: external directive favors the already-authorized execution value.
  - `CONFLICT`: external directive favors the alternate execution value, which the existing A14 oracle denies **only** because the protected execution argument is wrong.
- Score **both** AUTH and ALT actions in both directive contexts. This permits an action-identity-controlled selectivity contrast rather than attributing token/action identity differences to authorization.
- Primary scorer: exact pinned Llama-3.3-70B revision. Gemma-3-12B is a fixed source-fidelity replication.
- N2 is not part of this package.

## Author steps — prefreeze only

From `/home/anon_/ratchet/phase0_pilot`, place this folder as `N3_DISCRIMINANT_PREFREEZE_v1`, then:

```bash
cd /home/anon_/ratchet/phase0_pilot
(cd N3_DISCRIMINANT_PREFREEZE_v1 && sha256sum -c PACKAGE_SHA256.txt)
python N3_DISCRIMINANT_PREFREEZE_v1/N3_00_prepare_prefreeze.py \
  --project-root /home/anon_/ratchet/phase0_pilot \
  --out N3_PREFREEZE_AUTHOR_v1

python N3_DISCRIMINANT_PREFREEZE_v1/N3_01_human_audit_cli.py \
  --project-root /home/anon_/ratchet/phase0_pilot \
  --run-dir N3_PREFREEZE_AUTHOR_v1

python N3_DISCRIMINANT_PREFREEZE_v1/N3_02_freeze_protocol.py \
  --project-root /home/anon_/ratchet/phase0_pilot \
  --run-dir N3_PREFREEZE_AUTHOR_v1 \
  --package-dir N3_DISCRIMINANT_PREFREEZE_v1
```

Then archive **before any science**:

```bash
tar -czf N3_N0_FRZ_AUTHOR_v1.tar.gz \
  N3_PREFREEZE_AUTHOR_v1 \
  N3_DISCRIMINANT_PREFREEZE_v1
sha256sum N3_N0_FRZ_AUTHOR_v1.tar.gz > N3_N0_FRZ_AUTHOR_v1.tar.gz.sha256
```

Upload the archive + SHA for independent freeze adjudication.

## HARD STOP

Do **not** execute `N3_03_score_science.py` until the frozen archive has been independently audited. The scorer and analyzer are included now only so their bytes are part of the pre-outcome freeze.


## v1.2 pre-outcome technical amendment (independent freeze audit)

This amendment changes **no scientific design object**: the 24 bases, alternate mapping, ALIGNED/CONFLICT
directives, authorization oracle, D/Q/T estimands, inference, exclusions, and outcome-complete interpretation
remain byte-identical to the v1.1 prefreeze corpus. The existing 24/24 author human audit is reused by hash.

Before any scientific outcome, v1.2 hardens provenance/integrity only:
- verifies the semantic self-hash and complete freeze-file ledger before scoring/analysis;
- binds the local `/v1` endpoint to the exact live vLLM PID command line and frozen model/revision/tokenizer-revision/port;
- disallows custom/remote endpoints under this freeze;
- verifies target-action serialization hashes before scoring;
- refuses outcome-driven reruns after `RUN_COMPLETE.json`;
- records hashes for preflight, cache, raw request/response, and score ledgers;
- makes the analyzer verify all freeze/science hashes, scorer/model/revision metadata, runtime attestation, and exact 288-unit identity before computing D/Q/T;
- refuses any pre-outcome re-freeze if science/analysis artifacts already exist.

The refreeze step is permitted only while `scientific_model_calls_before_freeze=0`.
