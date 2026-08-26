# A13-R1 — Llama Scorer-Only Robustness Report

- Status: **STRONG_REPLICATION**
- Frozen R1 protocol: `d6c68d72ab0c665b589da1b5dc2ce217d71955ab874b24496ddaf2aa21982f3b`
- Parent A13 protocol: `b4a140c7d8ef49149ac72e35e9e52405f614fa5361558c7b2ac0c56fe0063b80`
- Scorer: `meta-llama/Llama-3.3-70B-Instruct`
- Agent trajectories/actions: exact frozen A13-Qwen traces/actions
- Fixed valid decisions rescored: 26 / 26

## Primary H_mean result

SPECIFIED=0.857, DELEGATED=0.167, DIFF=0.690, 95% task-bootstrap CI=[0.225, 1.000]

## Continuous M

SPECIFIED=0.536, DELEGATED=-0.069, DIFF=0.606, 95% task-bootstrap CI=[-0.210, 1.479]

## Cross-scorer agreement

- Primary H_mean agreement: 0.938 (16 decisions)
- Primary M Pearson: 0.982
- Primary M Spearman: 0.971

## Interpretation guardrail

R1 is a fixed-trace scorer-family robustness test. It does not test whether Llama as an AgentDojo agent produces the same task population; that is A13-R2. It also does not establish causality; A14 remains required.
