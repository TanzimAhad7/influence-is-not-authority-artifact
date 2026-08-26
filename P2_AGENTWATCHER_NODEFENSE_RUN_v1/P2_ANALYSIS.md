# P2 AgentWatcher Same-200 Defense-Disabled Result

**Primary verdict:** `MATCHED_INPUT_DEFENSE_OVERHEAD_SUPPORTED`

## Utility

- historical AgentWatcher: `56/200 = 28.0%`
- no defense: `120/200 = 60.0%`
- matched-input difference (no-defense − AgentWatcher): `+32.00` percentage points
- cluster-bootstrap 95% CI: `[+21.03, +43.15]` pp
- discordance: AgentWatcher fail → no-defense pass `77`; AgentWatcher pass → no-defense fail `13`

## Attack success

- historical AgentWatcher: `0/200 = 0.0%`
- no defense: `32/200 = 16.0%`
- difference: `+16.00` pp
- cluster-bootstrap 95% CI: `[+10.36, +22.34]` pp

## Scope qualification

Historical defense-on and P2 no-defense are separate API executions. Requested model/route and frozen inputs are matched, but unobserved provider drift cannot be ruled out; phrase as matched-input overhead evidence, not a randomized causal trial.

Do not convert this matched-input comparison into a stronger causal claim than the frozen design supports.
