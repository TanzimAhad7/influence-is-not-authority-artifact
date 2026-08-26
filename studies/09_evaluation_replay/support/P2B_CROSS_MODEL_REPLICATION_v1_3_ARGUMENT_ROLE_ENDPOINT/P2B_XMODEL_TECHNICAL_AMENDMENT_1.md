## Technical Amendment 1 — role-normalization compatibility fix

Trigger: the first Gemma scientific request was rejected by the model chat template with
HTTP 400 before generation:

`Conversation roles must alternate user/assistant/user/assistant/...`

The v1 canonical adapter represented historical tool results as `user` messages. In
histories where a tool result was immediately followed by a user message, this produced
two consecutive `user` roles. Llama accepted that shape; Gemma 3's standard chat template
did not.

This is an infrastructure/chat-template compatibility failure, not a Gemma scientific
outcome.

v1.1 changes only deterministic message serialization:

- all system material is folded into one leading `system` message;
- consecutive same-role historical blocks are concatenated with explicit boundary
  markers;
- no content is dropped, reordered, semantically rewritten, repaired, or selected;
- the resulting conversational turns are locally asserted to alternate
  `user/assistant/user/assistant/...` before the API call.

Unchanged:
- exact 26 decisions;
- 18 activated / 8 controls;
- 5 repeats;
- AgentDojo 0.1.35;
- frozen-continuation evaluator;
- 90% overall gate;
- 23/26 majority gate;
- target-function/exact-action/parser/no-call/multi-call diagnostics;
- Llama/Gemma/Qwen model set.

To preserve the common-adapter comparison, **all three fresh model arms are rerun under
v1.1**. Any v1 Llama arm already observed is retained only as technical/provenance data
and is not pooled into the v1.1 joint estimates.

The strengthened 3-call smoke now exercises the exact historical shape that triggered
the Gemma rejection. It must pass 3/3 before any v1.1 scientific baseline call for each
model.
