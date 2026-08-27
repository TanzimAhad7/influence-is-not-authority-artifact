# Artifact Structure, Anonymization, and Third-Party Material

This reviewer-facing guide consolidates the former layout, anonymization, third-party, implementation-support, and A13-C0 anonymization-map documents. The material is preserved here in one place; only repository paths were updated to match the reorganized distribution.

## Current top-level layout

The reviewer-facing roots are `studies/`, `figures/`, `scripts/`, `implementation_evidence/`, `third_party/`, and `supporting_material/`. Under `scripts/`, reproduction orchestration and deterministic verification are separated into `scripts/reproduction/` and `scripts/verification/`. Historical experiment IDs remain only where they are needed for provenance or frozen execution compatibility.


<!-- merged from: ARTIFACT_LAYOUT.md -->
## Artifact Layout

The repository is organized by scientific role rather than historical experiment ID.

### Primary structure

- `studies/01_natural_relevance/` — benign ecological relevance and generator breadth
- `studies/02_controlled_source_relocation/` — 24-base USER→TOOL matched intervention
- `studies/03_matched_unauthorized_comparison/` — same-function authorization-changing control
- `studies/04_threshold_frontier/` — complete deterministic scalar sweep
- `studies/05_agentwatcher/` — paired gate study and separate ON/OFF population
- `studies/06_attriguard/` — route exposure, later review, and aggregate block outcome
- `studies/07_causalarmor/` — calibrated reconstruction and benign activation audit
- `studies/08_live_end_to_end/` — 420 live executions, continuation, and later inspection
- `studies/09_evaluation_replay/` — corrected three-model replay
- `figures/` — final figure PDFs and Python producers
- `scripts/verification/` — deterministic verification outputs/tools
- `scripts/reproduction/` — full-rerun orchestration
- `third_party/` — source-bound external implementations
- `supporting_material/` — provenance, hardening, logs, historical support, and source coverage

### Historical identifiers

The original experiment tree used top-level names such as `A14`, `N3`, `R2B`, `N6`, and `P2B`. These identifiers are preserved inside frozen protocols/results for provenance but no longer dominate repository navigation.

`LEGACY_PATH_MAP.tsv` records every relocated top-level path.

During a fresh rerun, `scripts/reproduction/materialize_legacy_worktree.py` reconstructs the historical top-level layout inside the disposable run worktree. This lets the frozen experiment scripts execute without forcing the public repository to retain the historical flat directory layout.

### Provenance

`supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv` accounts for the original codebase artifact files and records their final distributed locations. Identity-bearing Git metadata remains the documented exclusion.

`SHA256SUMS.txt` protects the final distributed package.


<!-- merged from: ANONYMIZATION.md -->
## Anonymization and Source-Tree Coverage

This package is an anonymous derivative of the complete `artifacts/` directory in the supplied frozen project snapshot.

### Coverage

The source snapshot contained:

- **5,731 files** under `artifacts/`.
- **5,694 source files retained** in this anonymous derivative.
- **37 source files excluded**, all of them `.git` metadata from a bundled third-party repository/worktree.
- **162 retained source files identity-sanitized** because they contained author-local paths, author identity strings, or institution-host strings.

No scientific input, result row, model output, analysis output, protocol, freeze record, log, or manuscript-bearing producer was removed as a curation choice.

`supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv` is the authoritative one-row-per-source-file map. It contains:

```text
source_path
source_sha256
status
final_path
final_sha256
```

`supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.json` provides the summary counts used by `VERIFY.sh`.

### What was changed

The anonymization pass removes or neutralizes only identity/environment information. Examples include:

- author home-directory prefixes;
- author name/email strings;
- institution-specific host names;
- Git metadata containing commit identity, email, or local paths.

Nested ZIP/TAR.GZ files present in the source `artifacts/` tree were recursively inspected and anonymized where necessary rather than being dropped wholesale. Where an anonymization change altered a nested archive's bytes, directly associated checksum sidecars were updated when they represented that repacked container.

Because anonymization changes bytes, old historical checksum ledgers preserved inside historical bundles may describe the **pre-anonymization research snapshot**. They are retained as provenance. The authoritative integrity record for the distributed anonymous package is the top-level `SHA256SUMS.txt`.

### What was not changed

The anonymization step does not alter the reported scientific estimands, frozen result populations, current claim values, or artifact verification logic. `VERIFY.sh` re-derives the current manuscript-bearing quantities after anonymization and must finish with 56 PASS / 0 FAIL.

### Automated checks

Run:

```bash
bash CHECK_ANONYMITY.sh
```

The checker scans artifact paths/content and nested archives for the known author/institution identifiers, Git metadata, symlinks, and high-confidence credential patterns. Known synthetic benchmark fixtures are not treated as author credentials.

The same check is included automatically in:

```bash
bash VERIFY.sh
```

### Added rerun dependencies outside the original artifact derivative

Two A13-C0 author-run archives were required by the original extension runner but lived outside the codebase `artifacts/` derivative. They are included so that branch can be rerun. Their research copies contained author-local paths only in logs/audit metadata, so the distributed archives replace those identity strings and tar owner names. `the A13-C0 anonymization section below` records both original and anonymous archive hashes and the modified members. The science-bearing prefreeze script/JSON members remain byte-identical.

At rerun time, `scripts/reproduction/patch_a13c0_runner_for_anonymous_archives.py` makes a temporary copy of the original extension runner and updates only the two whole-archive SHA constants to the anonymized archive hashes. The temporary runner then creates a fresh preflight freeze, and science mode verifies that same temporary runner/freeze. The original research runner remains distributed unchanged.


<!-- merged from: THIRD_PARTY.md -->
## Third-Party Code and Provenance

This artifact preserves third-party material that was present in the source project `artifacts/` tree because some manuscript claims are implementation- or version-bound.

### AgentWatcher / AgentDojo material

The artifact contains the tested AgentWatcher/AgentDojo source/runtime material under `third_party/integrations/`. License files distributed with the bundled third-party subprojects are retained at their original locations, including the AgentDojo/AgentDyn license files.

The current verifier hashes the tested AgentWatcher integration adapter so the implementation-bound claim can be tied to the exact distributed source.

### AttriGuard material

The source project artifact tree contains an AttriGuard USENIX-artifact snapshot under:

```text
third_party/integrations/attriguard_zenodo_v1/
```

The project provenance records bind this material to the archived AttriGuard artifact and exact tested `AttriGuard.py` source hash used by the implementation-bound analysis. The package is preserved because it was present in the supplied artifact tree.

A clear standalone redistribution license was not found in the supplied AttriGuard archive during curation. Therefore this artifact does **not** make an independent claim about AttriGuard redistribution rights. The retained provenance/source hashes allow the tested implementation to be identified. If the final hosting venue or artifact policy requires separate redistribution permission, the AttriGuard source subtree should be handled according to that policy rather than silently relicensed here.

### Credentials

No third-party provider credentials are included. `.env.example` files and benchmark fixtures may be retained because they are code/data examples, but the artifact hygiene checker searches for high-confidence live credential patterns. Provider-dependent reruns require users to supply their own authorized credentials.


<!-- merged from: artifact_support/README.md -->
## Artifact Support Records

Compact frozen support records used by deterministic verification and figure regeneration. In the reorganized package these records live under `implementation_evidence/`.

These files are support inputs, not an additional experiment hierarchy. For paper-facing navigation, use `studies/` and `CLAIM_TO_ARTIFACT.md`.


<!-- merged from: reproduction/A13_C0_ANONYMIZATION_MAP.md -->
## A13-C0 anonymization-only archive rewrite

Two author-run archives required by the original A13-C0 extension runner contained local author paths in logs/audit metadata. The distributed copies replace only known identity/environment strings and tar owner metadata. Science-bearing frozen members used by the extension runner remain byte-identical. The rerun wrapper patches only the two whole-archive SHA constants to the anonymized archive hashes before generating a fresh runner freeze.

### `A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz`

- original research archive SHA-256: `bacedba13f854aebd3168ad020b5123ec889a870d5c03cd1c7f519f0daccd495`
- distributed anonymous archive SHA-256: `a36088527544d5955d3fa26c3e4f59638d7c9514d0fc6323148fad545e216c62`
- members with identity-only text replacement: `3`
  - `A13_C0_V2_1_DEEP_ZERO_CALL_AUDIT.py`
  - `A13_C0_V2_1_AUTHOR_RUN.log`
  - `A13_C0_V2_1_AUTHOR_AUDIT/A13_C0_V2_1_DEEP_AUDIT.json`

### `A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz`

- original research archive SHA-256: `035af5fb370cef996739ec6b99db24e9be66a446050779a5c26242fcdda2396d`
- distributed anonymous archive SHA-256: `9b4f5752df0ca741ab6eb4509569ad1d3ac935a08338f5b5699f17dc616df4df`
- members with identity-only text replacement: `1`
  - `A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_RUN.log`
