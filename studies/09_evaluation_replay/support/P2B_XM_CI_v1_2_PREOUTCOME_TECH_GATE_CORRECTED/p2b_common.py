#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

EXPECTED_AGENTDOJO_VERSION = "0.1.35"
BENCHMARK_VERSION = "v1"


def stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_obj(obj: Any) -> str:
    return sha256_bytes(stable_json(obj).encode("utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(stable_json(obj) + "\n")
        f.flush()
        os.fsync(f.fileno())


def deep_copy_env(env: Any) -> Any:
    if hasattr(env, "model_copy"):
        return env.model_copy(deep=True)
    if hasattr(env, "copy"):
        return env.copy(deep=True)
    return copy.deepcopy(env)


def to_function_call(tc: Any):
    from agentdojo.functions_runtime import FunctionCall
    if isinstance(tc, FunctionCall):
        return tc
    return FunctionCall(
        function=tc["function"],
        args=dict(tc.get("args") or {}),
        id=tc.get("id"),
        placeholder_args=tc.get("placeholder_args"),
    )


def normalize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert JSON-serialized AgentDojo messages back to the structures expected by 0.1.35."""
    out = []
    for m in copy.deepcopy(messages):
        if m.get("role") == "assistant":
            m["tool_calls"] = [to_function_call(x) for x in (m.get("tool_calls") or [])]
        elif m.get("role") == "tool" and m.get("tool_call") is not None:
            m["tool_call"] = to_function_call(m["tool_call"])
        out.append(m)
    return out


def tool_calls_from_assistant_messages(messages: Iterable[dict[str, Any]], start: int = 0, end: int | None = None):
    msgs = list(messages)
    if end is None:
        end = len(msgs)
    calls = []
    for mi in range(start, end):
        m = msgs[mi]
        if m.get("role") != "assistant":
            continue
        for tc in (m.get("tool_calls") or []):
            calls.append((mi, to_function_call(tc)))
    return calls


def get_last_assistant_content(messages: list[dict[str, Any]]):
    for m in reversed(messages):
        if m.get("role") == "assistant":
            return copy.deepcopy(m.get("content") or [])
    return []


def _error_text(err: Any) -> str | None:
    if err is None:
        return None
    s = str(err).strip()
    return s or None


def _error_message_only(err: Any) -> str | None:
    """Normalize historical/runtime errors while tolerating exception-class prefix formatting."""
    s = _error_text(err)
    if s is None:
        return None
    head, sep, tail = s.partition(": ")
    if sep and head.endswith(("Error", "Exception")):
        return tail.strip()
    return s


def historical_tool_errors_by_id(
    messages: list[dict[str, Any]], start: int = 0, end: int | None = None
) -> dict[str, str | None]:
    """Return frozen historical tool-error status keyed by exact tool_call_id."""
    if end is None:
        end = len(messages)
    out: dict[str, str | None] = {}
    for m in messages[start:end]:
        if m.get("role") != "tool":
            continue
        tcid = m.get("tool_call_id")
        if tcid:
            out[str(tcid)] = _error_text(m.get("error"))
    return out


def execute_calls(
    runtime: Any,
    env: Any,
    calls: Iterable[Any],
    *,
    strict: bool = True,
    expected_errors_by_id: dict[str, str | None] | None = None,
):
    """
    Replay tool calls.

    strict=True means unexpected replay errors are fatal.
    When expected_errors_by_id is supplied, a historical error is accepted only if the
    exact frozen tool-call ID recorded an error with the same normalized message.
    """
    trace = []
    results = []
    expected_errors_by_id = expected_errors_by_id or {}

    for tc in calls:
        tc = to_function_call(tc)
        ret, err = runtime.run_function(env, tc.function, tc.args, raise_on_error=False)
        actual_err = _error_text(err)
        expected_present = tc.id is not None and str(tc.id) in expected_errors_by_id
        expected_err = expected_errors_by_id.get(str(tc.id)) if expected_present else None

        trace.append(tc)
        results.append(
            {
                "function": tc.function,
                "args": dict(tc.args),
                "id": tc.id,
                "error": actual_err,
                "historical_expected_error": expected_err if expected_present else None,
            }
        )

        if not strict:
            continue

        if expected_present:
            # Exact historical status is part of the replay contract.
            if (expected_err is None) != (actual_err is None):
                raise RuntimeError(
                    f"Tool replay error-status mismatch for historical call {tc.id}: "
                    f"{tc.function}({dict(tc.args)!r}); expected_error={expected_err!r}, "
                    f"actual_error={actual_err!r}"
                )
            if expected_err is not None:
                if _error_message_only(expected_err) != _error_message_only(actual_err):
                    raise RuntimeError(
                        f"Tool replay historical-error mismatch for call {tc.id}: "
                        f"{tc.function}({dict(tc.args)!r}); expected_error={expected_err!r}, "
                        f"actual_error={actual_err!r}"
                    )
            continue

        if actual_err is not None:
            raise RuntimeError(
                f"Unexpected tool replay failure: {tc.function}({dict(tc.args)!r}): {actual_err}"
            )

    return trace, results


def load_runtime_case(project_root: Path, inventory_row: dict[str, Any]):
    from agentdojo.task_suite.load_suites import get_suite
    from agentdojo.functions_runtime import FunctionsRuntime

    suite_name = inventory_row["suite"]
    user_task_id = inventory_row["user_task"]
    suite = get_suite(BENCHMARK_VERSION, suite_name)
    user_task = suite.user_tasks[user_task_id]

    # Exact AgentDojo 0.1.35 no-injection task initialization used by A13.
    base_env = suite.load_and_inject_default_environment({})
    task_env = user_task.init_environment(base_env)
    initial_pre_env = deep_copy_env(task_env)
    runtime = FunctionsRuntime(suite.tools)

    raw_path = project_root / inventory_row["raw_log_path"]
    if not raw_path.exists():
        raise FileNotFoundError(raw_path)
    if sha256_file(raw_path) != inventory_row["raw_log_sha256"]:
        raise RuntimeError(f"Raw-log hash mismatch: {raw_path}")
    raw = read_json(raw_path)
    messages = normalize_messages(list(raw.get("messages") or []))
    return suite, user_task, runtime, task_env, initial_pre_env, raw, messages


def reconstruct_pre_target(project_root: Path, inventory_row: dict[str, Any]):
    suite, user_task, runtime, task_env, initial_pre_env, raw, messages = load_runtime_case(project_root, inventory_row)
    target_mi = int(inventory_row["target_message_index"])
    prior_pairs = tool_calls_from_assistant_messages(messages, 0, target_mi)
    prior_calls = [tc for _, tc in prior_pairs]

    # Historical tool errors can be legitimate observations used by the agent.
    # Replay accepts them only when the exact frozen tool_call_id recorded the same error.
    prior_expected_errors = historical_tool_errors_by_id(messages, 0, target_mi)
    prior_trace, prior_exec = execute_calls(
        runtime,
        task_env,
        prior_calls,
        strict=True,
        expected_errors_by_id=prior_expected_errors,
    )
    return {
        "suite": suite,
        "user_task": user_task,
        "runtime": runtime,
        "pre_target_env": task_env,
        "initial_pre_env": initial_pre_env,
        "raw": raw,
        "messages": messages,
        "prior_trace": prior_trace,
        "prior_exec": prior_exec,
    }


def evaluate_candidate_frozen_continuation(
    project_root: Path,
    inventory_row: dict[str, Any],
    candidate_assistant_message: dict[str, Any],
) -> dict[str, Any]:
    """
    Primary P2b decision-level oracle.

    1) reconstruct exact AgentDojo task state immediately before the frozen target action;
    2) execute the regenerated assistant message's tool call(s);
    3) replay all subsequent ORIGINAL assistant tool calls after the target turn;
    4) evaluate the resulting task with AgentDojo 0.1.35's own user-task utility helper,
       holding the original final textual answer fixed.

    This is intentionally a decision-point / frozen-continuation oracle, not end-to-end BU.
    """
    state = reconstruct_pre_target(project_root, inventory_row)
    suite = state["suite"]
    user_task = state["user_task"]
    runtime = state["runtime"]
    env = state["pre_target_env"]
    initial_pre_env = state["initial_pre_env"]
    messages = state["messages"]
    target_mi = int(inventory_row["target_message_index"])

    candidate_norm = normalize_messages([candidate_assistant_message])[0]
    candidate_calls = list(candidate_norm.get("tool_calls") or [])

    candidate_trace = []
    candidate_exec = []
    for tc in candidate_calls:
        ret, err = runtime.run_function(env, tc.function, tc.args, raise_on_error=False)
        candidate_trace.append(tc)
        candidate_exec.append({"function": tc.function, "args": dict(tc.args), "error": err})
        # Candidate errors are scientific outcomes, not infrastructure retries.

    continuation_pairs = tool_calls_from_assistant_messages(messages, target_mi + 1, len(messages))
    continuation_calls = [tc for _, tc in continuation_pairs]
    continuation_trace, continuation_exec = execute_calls(runtime, env, continuation_calls, strict=False)

    full_trace = [*state["prior_trace"], *candidate_trace, *continuation_trace]
    original_final_output = get_last_assistant_content(messages)

    try:
        utility = bool(
            suite._check_user_task_utility(
                user_task,
                original_final_output,
                initial_pre_env,
                env,
                full_trace,
            )
        )
        utility_error = None
    except Exception as e:
        utility = False
        utility_error = f"{type(e).__name__}: {e}"

    target = inventory_row["target_action"]
    exact_target = False
    function_match = False
    if len(candidate_calls) == 1:
        c = candidate_calls[0]
        function_match = c.function == target["function"]
        exact_target = function_match and stable_json(dict(c.args)) == stable_json(dict(target.get("args") or {}))

    return {
        "utility_preserved": utility,
        "utility_error": utility_error,
        "candidate_n_tool_calls": len(candidate_calls),
        "candidate_calls": [
            {"function": c.function, "args": dict(c.args), "id": c.id}
            for c in candidate_calls
        ],
        "candidate_execution": candidate_exec,
        "continuation_execution": continuation_exec,
        "target_function_match": function_match,
        "exact_target_action_reproduction": exact_target,
    }


def original_target_message(inventory_row: dict[str, Any]) -> dict[str, Any]:
    target = inventory_row["target_action"]
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [copy.deepcopy(target)],
    }


def verify_original_target_oracle(project_root: Path, inventory_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks = []
    for r in inventory_rows:
        ev = evaluate_candidate_frozen_continuation(project_root, r, original_target_message(r))
        checks.append({
            "decision_id": r["decision_id"],
            "utility_preserved": ev["utility_preserved"],
            "exact_target_action_reproduction": ev["exact_target_action_reproduction"],
            "utility_error": ev["utility_error"],
        })
    return checks


def freeze_hash(freeze: dict[str, Any]) -> str:
    payload = copy.deepcopy(freeze)
    payload.pop("freeze_sha256", None)
    return sha256_obj(payload)
