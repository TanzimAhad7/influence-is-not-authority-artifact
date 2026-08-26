# A13-R1B — Boundary-Safe Technical Validation Report

- Status: **STRONG_REPLICATION**
- Frozen R1B protocol: `3f8591539a8036ce2dbcdd2781cfb3d3eb460533bf45255e44543b9e429322a1`
- Parent A13 protocol: `b4a140c7d8ef49149ac72e35e9e52405f614fa5361558c7b2ac0c56fe0063b80`
- Scorer: `meta-llama/Llama-3.3-70B-Instruct`
- Agent trajectories/actions: exact frozen A13-Qwen traces/actions
- Fixed valid decisions boundary-safe rescored: 26 / 26

## Primary H_mean result

SPECIFIED=0.857, DELEGATED=0.167, DIFF=0.690, 95% task-bootstrap CI=[0.225, 1.000]

## Continuous M

SPECIFIED=0.745, DELEGATED=-0.050, DIFF=0.795, 95% task-bootstrap CI=[-0.197, 2.018]

## Cross-scorer agreement

- Primary H_mean agreement: 0.938 (16 decisions)
- Primary M Pearson: 0.992
- Primary M Spearman: 0.888

## Interpretation guardrail

R1B is a post-outcome technical validation of the completed R1 scoring boundary. It does not test whether Llama as an AgentDojo agent produces the same task population; that is A13-R2. It also does not establish causality; A14 remains required.
