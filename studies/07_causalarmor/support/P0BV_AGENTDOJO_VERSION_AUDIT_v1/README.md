# P0b-V AgentDojo benchmark-version compatibility audit

Purpose: compare the **benchmark suite** used by the historical A13-derived lineage (`v1`) against the
CausalArmor-published suite (`v1.2.2`) under the exact installed **agentdojo==0.1.35** package.

This is a zero-model-call integrity audit. Do not start vLLM or any GPU server.

## What it compares

For banking, Slack, travel, and workspace, the audit compares:

- suite default environment state;
- tool names, descriptions, Pydantic schemas, dependencies, and implementation source;
- every user task: prompt, class/source, initialized state, ground-truth call sequence, post-ground-truth
  environment effect, utility evaluator source;
- every injection task: goal, ground-truth calls/effect, security evaluator source;
- intersections with A13 primary-valid decisions, A15a, corrected P2b, AgentWatcher-natural;
- the frozen AgentWatcher 200-pair attack anchor and its own benchmark-version declaration.

It also recomputes a **diagnostic** A13 task-weighted H contrast after removing every historical
paper-bearing task found to differ across v1/v1.2.2, and a corrected-P2b descriptive summary after
removing those same task keys. These do not replace frozen results.

## Hard rules

- Historical results remain frozen.
- Never call them v1.2.2 if they were run on v1.
- No broad rerun is authorized by this script.
- A14-Minimal is benchmark-suite-independent and outside this gate.
- P0b-3 must use v1.2.2 after this audit is adjudicated.
