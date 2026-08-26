# P0b-V — AgentDojo v1 ↔ v1.2.2 compatibility audit

**Gate status:** `HEADLINE_TASK_DIFFERENCE_BUT_EXISTING_DELETION_SENSITIVITY_PRESERVES_BROAD_DIRECTIONS`

- Scientific model calls: **0**
- Installed package: **agentdojo==0.1.35**
- Benchmark suites compared: **v1 vs v1.2.2**
- AgentWatcher 200-pair attack anchor was already frozen on **v1.2.2**.

## Suite-level compatibility

- banking: environment_changed=False, tools_changed=False, changed user tasks=2, changed injection tasks=8.
- slack: environment_changed=False, tools_changed=False, changed user tasks=8, changed injection tasks=0.
- travel: environment_changed=False, tools_changed=False, changed user tasks=20, changed injection tasks=4.
- workspace: environment_changed=False, tools_changed=False, changed user tasks=23, changed injection tasks=13.

## Changed user tasks

- `banking/user_task_15` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|ground_truth_method_sha256|ground_truth_calls_sha256|post_ground_truth_environment_sha256|utility_method_sha256|class|class_source_sha256`
- `banking/user_task_6` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `slack/user_task_11` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|class|class_source_sha256`
- `slack/user_task_12` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `slack/user_task_13` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `slack/user_task_14` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `slack/user_task_2` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `slack/user_task_4` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `slack/user_task_5` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `slack/user_task_8` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `travel/user_task_0` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|ground_truth_output|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_1` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|ground_truth_output|post_ground_truth_environment_sha256|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_10` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_11` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_12` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|ground_truth_method_sha256|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_13` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_14` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_15` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_16` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|class|class_source_sha256`
- `travel/user_task_17` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `travel/user_task_18` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_19` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_2` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_3` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|post_ground_truth_environment_sha256|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_4` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|ground_truth_output|post_ground_truth_environment_sha256|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_5` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_6` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|ground_truth_output|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_7` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|post_ground_truth_environment_sha256|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_8` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|post_ground_truth_environment_sha256|utility_method_sha256|class|class_source_sha256`
- `travel/user_task_9` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|utility_method_sha256|class|class_source_sha256`
- `workspace/user_task_0` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `prompt|ground_truth_output|utility_method_sha256|class|class_source_sha256`
- `workspace/user_task_12` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_13` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_15` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_16` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `workspace/user_task_17` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `workspace/user_task_18` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `ground_truth_calls_sha256|post_ground_truth_environment_sha256|utility_method_sha256|class|class_source_sha256`
- `workspace/user_task_19` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_20` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `ground_truth_calls_sha256|post_ground_truth_environment_sha256|class|class_source_sha256`
- `workspace/user_task_21` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_22` → **UNKNOWN_REQUIRES_MANUAL_REVIEW**; fields: `class|class_source_sha256|utility_method_sha256`
- `workspace/user_task_25` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_29` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_31` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_32` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_33` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_34` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_36` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_37` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_4` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_6` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`
- `workspace/user_task_7` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `ground_truth_method_sha256|ground_truth_calls_sha256|post_ground_truth_environment_sha256|utility_method_sha256|class|class_source_sha256`
- `workspace/user_task_9` → **PROMPT_OR_GROUND_TRUTH_CHANGE**; fields: `post_ground_truth_environment_sha256`

## Historical paper-bearing overlap

- Unique changed task keys touching A13/A15a/P2b/AgentWatcher-natural: **11**: `slack/user_task_13`, `slack/user_task_2`, `slack/user_task_4`, `travel/user_task_3`, `workspace/user_task_12`, `workspace/user_task_13`, `workspace/user_task_15`, `workspace/user_task_21`, `workspace/user_task_4`, `workspace/user_task_6`, `workspace/user_task_9`.
- A13 task-weighted H: original difference **+0.6349**, excluding all changed historical task keys **+0.6000** with 95% task-bootstrap CI **[-0.0952, +1.0000]**.

## Corrected-P2b all-changed-task deletion diagnostic

- gemma: n=15; action-local **40.0%** (6 majority cells); downstream **73.3%** (11 majority cells).
- llama: n=15; action-local **53.3%** (8 majority cells); downstream **80.0%** (12 majority cells).
- qwen: n=15; action-local **53.3%** (8 majority cells); downstream **80.0%** (12 majority cells).

## Interpretation lock

- Historical A13/A15a/P2b/AgentWatcher-natural results remain frozen and must be called AgentDojo-v1 evidence.
- A14-Minimal is not affected by this task-suite mismatch.
- The AgentWatcher attack anchor is not a historical-v1 mismatch because its own freeze is v1.2.2.
- Do not authorize a broad rerun automatically. A targeted revalidation branch, if any, is decided only after manual review of the changed-task rows and source signatures.
- P0b-3 calibration must use v1.2.2.
