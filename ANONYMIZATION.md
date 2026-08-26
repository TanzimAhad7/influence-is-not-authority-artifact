# Anonymization and Source-Tree Coverage

This package is an anonymous derivative of the complete `artifacts/` directory in the supplied frozen project snapshot.

## Coverage

The source snapshot contained:

- **5,731 files** under `artifacts/`.
- **5,694 source files retained** in this anonymous derivative.
- **37 source files excluded**, all of them `.git` metadata from a bundled third-party repository/worktree.
- **162 retained source files identity-sanitized** because they contained author-local paths, author identity strings, or institution-host strings.

No scientific input, result row, model output, analysis output, protocol, freeze record, log, or manuscript-bearing producer was removed as a curation choice.

`SOURCE_ARTIFACT_COVERAGE.tsv` is the authoritative one-row-per-source-file map. It contains:

```text
source_path
source_sha256
status
final_path
final_sha256
```

`SOURCE_ARTIFACT_COVERAGE.json` provides the summary counts used by `VERIFY.sh`.

## What was changed

The anonymization pass removes or neutralizes only identity/environment information. Examples include:

- author home-directory prefixes;
- author name/email strings;
- institution-specific host names;
- Git metadata containing commit identity, email, or local paths.

Nested ZIP/TAR.GZ files present in the source `artifacts/` tree were recursively inspected and anonymized where necessary rather than being dropped wholesale. Where an anonymization change altered a nested archive's bytes, directly associated checksum sidecars were updated when they represented that repacked container.

Because anonymization changes bytes, old historical checksum ledgers preserved inside historical bundles may describe the **pre-anonymization research snapshot**. They are retained as provenance. The authoritative integrity record for the distributed anonymous package is the top-level `SHA256SUMS.txt`.

## What was not changed

The anonymization step does not alter the reported scientific estimands, frozen result populations, current claim values, or artifact verification logic. `VERIFY.sh` re-derives the current manuscript-bearing quantities after anonymization and must finish with 56 PASS / 0 FAIL.

## Automated checks

Run:

```bash
bash CHECK_ANONYMITY.sh
```

The checker scans artifact paths/content and nested archives for the known author/institution identifiers, Git metadata, symlinks, and high-confidence credential patterns. Known synthetic benchmark fixtures are not treated as author credentials.

The same check is included automatically in:

```bash
bash VERIFY.sh
```

## Added rerun dependencies outside the original artifact derivative

Two A13-C0 author-run archives were required by the original extension runner but lived outside the codebase `artifacts/` derivative. They are included so the branch can be executed that branch. Their research copies contained author-local paths only in logs/audit metadata, so the distributed archives replace those identity strings and tar owner names. `reproduction/A13_C0_ANONYMIZATION_MAP.md` records both original and anonymous archive hashes and the modified members. The science-bearing prefreeze script/JSON members remain byte-identical.

At rerun time, `reproduction/patch_a13c0_runner_for_anonymous_archives.py` makes a temporary copy of the original extension runner and updates only the two whole-archive SHA constants to the anonymized archive hashes. The temporary runner then creates a fresh preflight freeze, and science mode verifies that same temporary runner/freeze. The original research runner remains distributed unchanged.
