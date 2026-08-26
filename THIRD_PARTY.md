# Third-Party Code and Provenance

This artifact preserves third-party material that was present in the source project `artifacts/` tree because some manuscript claims are implementation- or version-bound.

## AgentWatcher / AgentDojo material

The artifact contains the tested AgentWatcher/AgentDojo source/runtime material under `third_party/integrations/`. License files distributed with the bundled third-party subprojects are retained at their original locations, including the AgentDojo/AgentDyn license files.

The current verifier hashes the tested AgentWatcher integration adapter so the implementation-bound claim can be tied to the exact distributed source.

## AttriGuard material

The source project artifact tree contains an AttriGuard USENIX-artifact snapshot under:

```text
third_party/integrations/attriguard_zenodo_v1/
```

The project provenance records bind this material to the archived AttriGuard artifact and exact tested `AttriGuard.py` source hash used by the implementation-bound analysis. The package is preserved because it was present in the supplied artifact tree.

A clear standalone redistribution license was not found in the supplied AttriGuard archive during curation. Therefore this artifact does **not** make an independent claim about AttriGuard redistribution rights. The retained provenance/source hashes allow the tested implementation to be identified. If the final hosting venue or artifact policy requires separate redistribution permission, the AttriGuard source subtree should be handled according to that policy rather than silently relicensed here.

## Credentials

No third-party provider credentials are included. `.env.example` files and benchmark fixtures may be retained because they are code/data examples, but the artifact hygiene checker searches for high-confidence live credential patterns. Provider-dependent reruns require users to supply their own authorized credentials.
