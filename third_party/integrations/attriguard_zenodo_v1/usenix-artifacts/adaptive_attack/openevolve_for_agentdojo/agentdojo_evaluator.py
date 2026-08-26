import os
import re
import time
import traceback
from pathlib import Path
from typing import Any, Dict
import importlib
import sys


import logging
import contextlib
import io
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("openevolve").setLevel(logging.INFO)
logging.getLogger("agentdojo").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

import yaml

from agentdojo.task_suite.load_suites import get_suite
from agentdojo.models import ModelsEnum
from agentdojo.benchmark import SuiteResults
PIPELINE_DIR = Path(__file__).resolve().parents[1] / "pipeline"
if str(PIPELINE_DIR) not in sys.path:
    sys.path.append(str(PIPELINE_DIR))

from my_agent_pipeline import DEFENSES, AgentPipeline, PipelineConfig
from agentdojo.attacks.attack_registry import ATTACKS, load_attack
from agentdojo.functions_runtime import FunctionCall
import json
import hashlib


# ANSI color codes.
GREEN = "\033[92m"
YELLOW = "\033[93m"
RESET = "\033[0m"
RED = "\033[91m"
BLUE = "\033[94m"

import importlib
import attack as attack_module
from agentdojo.attacks.attack_registry import ATTACKS
# print("registered attacks:", list(ATTACKS.keys()))

import requests

from scorer_llm import (
    CRITIC_API_URL,
    CRITIC_MODEL_NAME,
    CRITIC_API_KEY,
    REQUEST_TIMEOUT,
    RETRY_TIMES,
    RETRY_DELAY,
    call_scorer,
)

# -----------------------------------------------------------------------------
# 1. Read config.yaml and load AgentDojo/evaluator configuration.
# -----------------------------------------------------------------------------

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("OPENEvolve_CONFIG_PATH") or os.path.join(HERE, "config.yaml")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

def _load_default_agentdojo_cfg(config: Dict[str, Any]) -> Dict[str, Any]:
    top_level = config.get("agentdojo", {}) or {}
    if top_level:
        return top_level
    evaluator = config.get("evaluator", {}) or {}
    extra_kwargs = evaluator.get("extra_kwargs", {}) or {}
    nested = extra_kwargs.get("agentdojo_cfg", {}) or {}
    return nested


# Default AgentDojo configuration read from config.yaml.
DEFAULT_AGENTDOJO_CFG = _load_default_agentdojo_cfg(CONFIG)

# At module scope, use only the default configuration to choose benchmark_module.
BENCHMARK_MODULE_NAME = DEFAULT_AGENTDOJO_CFG.get(
    "benchmark_module",
    "my_benchmark",
)

benchmark_module = importlib.import_module(BENCHMARK_MODULE_NAME)
# Get the benchmark_suite function defined in the selected module.
benchmark_suite = getattr(benchmark_module, "benchmark_suite")

# Evaluator configuration used for combined scoring.
evaluator_cfg = CONFIG.get("evaluator", {})
# Lambda: security weight. Larger values penalize high attack success more.
SECURITY_WEIGHT = evaluator_cfg.get("security_weight", 1.0)

logging.getLogger(__name__).debug(
    "[Evaluator] Using AgentDojo benchmark module: %s", BENCHMARK_MODULE_NAME
)
logging.getLogger(__name__).debug("[Evaluator] SECURITY_WEIGHT = %s", SECURITY_WEIGHT)

def extract_checkpoint_id_from_prompt_path(prompt_path: str) -> str | None:
    """
    Parse the checkpoint id from the prompt_path passed by OpenEvolve.
    For example, a path containing .../checkpoints/checkpoint_6/prompt.txt
    returns "6"; returns None if no checkpoint id is found.
    """
    p = Path(prompt_path)
    for part in p.parts:
        m = re.match(r"checkpoint_(\d+)", part)
        if m:
            return m.group(1)
    return None
    
def _json_bool(value: bool) -> str:
    return "true" if value else "false"

def _build_defense_state(
    defense_name: str | None,
    trace_messages: Any,
    trace_data: Dict[str, Any] | None = None,
    expected_function_calls: list[dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    if defense_name == "attriguard":
        def _get_tool_call(message: dict) -> dict | None:
            tool_call = message.get("tool_call")
            if isinstance(tool_call, dict):
                return tool_call
            if hasattr(tool_call, "function") and hasattr(tool_call, "args"):
                return {"function": tool_call.function, "args": tool_call.args}
            return None

        injections = []
        if trace_data:
            injections_map = trace_data.get("injections") or {}
            if isinstance(injections_map, dict):
                injections = [str(v) for v in injections_map.values() if v]
        messages = trace_data.get("messages") if trace_data else trace_messages
        if isinstance(messages, list) and injections:
            matched: list[dict[str, Any]] = []
            started = False
            normalized_injections = ["".join(inj.split()) for inj in injections if isinstance(inj, str)]
            for message in messages:
                if started and message.get("role") != "tool":
                    break
                defense_input = message.get("defense_input")
                state = message.get("defense_state")
                if not isinstance(state, dict):
                    continue
                if not isinstance(defense_input, str):
                    continue
                normalized_input = "".join(defense_input.split())
                if any(inj in normalized_input for inj in normalized_injections):
                    matched.append(message)
                    if not started:
                        started = True
            if matched:
                expected = expected_function_calls[0] if expected_function_calls else None
                if expected:
                    expected_fn = expected.get("function")
                    expected_args = expected.get("args")
                    # Full match: function + args
                    for msg in matched:
                        tool_call = _get_tool_call(msg)
                        if not tool_call:
                            continue
                        if tool_call.get("function") == expected_fn and tool_call.get("args") == expected_args:
                            print("[AttriGuard] defense_state match=func+args")
                            return msg.get("defense_state")
                    # Args-partial match: function matches and any expected arg matches
                    if isinstance(expected_args, dict):
                        for msg in matched:
                            tool_call = _get_tool_call(msg)
                            if not tool_call:
                                continue
                            if tool_call.get("function") != expected_fn:
                                continue
                            tool_args = tool_call.get("args")
                            if not isinstance(tool_args, dict):
                                continue
                            if any(tool_args.get(k) == v for k, v in expected_args.items()):
                                print("[AttriGuard] defense_state match=func+args-partial")
                                return msg.get("defense_state")
                    # Function-only match
                    for msg in matched:
                        tool_call = _get_tool_call(msg)
                        if not tool_call:
                            continue
                        if tool_call.get("function") == expected_fn:
                            print("[AttriGuard] defense_state match=func-only")
                            return msg.get("defense_state")
                # No function match: return flag=None with first matched attenuated_external
                first_state = matched[0].get("defense_state") if isinstance(matched[0], dict) else None
                attenuated_external = ""
                if isinstance(first_state, dict):
                    attenuated_external = first_state.get("attenuated_external") or ""
                print("[AttriGuard] defense_state match=no-func")
                return {
                    "flag": None,
                    "attenuated_external": attenuated_external,
                    "judge_reason": None,
                }
        # No defense_input matched payload
        return {
            "flag": None,
            "attenuated_external": None,
            "judge_reason": None,
        }
    return None

def _load_scorer_prompts(defense_name: str | None) -> tuple[str, str]:
    if not defense_name:
        raise ValueError("defense_name is required for scorer prompt selection")
    prompt_dir = Path(HERE) / "scorer_prompt"
    system_path = prompt_dir / f"{defense_name}.txt"
    user_path = prompt_dir / f"user_{defense_name}.txt"
    if not system_path.exists():
        raise FileNotFoundError(f"Missing scorer system prompt: {system_path}")
    if not user_path.exists():
        raise FileNotFoundError(f"Missing scorer user prompt: {user_path}")
    return system_path.read_text(encoding="utf-8"), user_path.read_text(encoding="utf-8")

def _render_user_prompt(template: str, payload: Dict[str, Any]) -> str:
    template_stripped = template.strip()
    placeholder_map = {
        "injection_task_goal": payload.get("injection_task"),
        "injection_task": payload.get("injection_task"),
        "success": payload.get("attack_success"),
        "attack_success": payload.get("attack_success"),
        "messages": payload.get("messages"),
        "defense_state": payload.get("defense_state"),
        "flag": (payload.get("defense_state") or {}).get("flag"),
    }

    def replace_named_placeholder(match: re.Match[str]) -> str:
        key = match.group(1)
        value = placeholder_map.get(key)
        if isinstance(value, bool):
            return _json_bool(value)
        return json.dumps(value, ensure_ascii=False)

    rendered = re.sub(
        r"\{(injection_task_goal|injection_task|success|attack_success|messages|defense_state|flag)\}",
        replace_named_placeholder,
        template_stripped,
    )

    rendered = re.sub(
        r'"injection_task"\s*:\s*"<string>"',
        f"\"injection_task\": {json.dumps(payload['injection_task'], ensure_ascii=False)}",
        rendered,
    )
    rendered = re.sub(
        r'"attack_success"\s*:\s*<boolean>',
        f"\"attack_success\": {_json_bool(payload['attack_success'])}",
        rendered,
    )
    rendered = re.sub(
        r'"messages"\s*:\s*<json>',
        f"\"messages\": {json.dumps(payload['messages'], ensure_ascii=False)}",
        rendered,
    )
    if "defense_state" in payload:
        defense_state = payload["defense_state"]
        if isinstance(defense_state, dict):
            for key, value in defense_state.items():
                if isinstance(value, bool):
                    rendered = re.sub(
                        rf'"{key}"\s*:\s*<boolean>',
                        f"\"{key}\": {_json_bool(value)}",
                        rendered,
                    )
                elif isinstance(value, (int, float)):
                    rendered = re.sub(
                        rf'"{key}"\s*:\s*<number>',
                        f"\"{key}\": {value}",
                        rendered,
                    )
            rendered = re.sub(
                r'"defense_state"\s*:\s*\{[^}]*\}',
                f"\"defense_state\": {json.dumps(defense_state, ensure_ascii=False)}",
                rendered,
            )

    if re.search(r"<(string|boolean|number|json)>", rendered):
        raise ValueError("Unfilled placeholders found in evaluator user prompt")
    return rendered

def _call_scorer_llm(system_prompt: str, user_prompt: str, temperature: float = 0.0) -> Dict[str, Any]:
    return call_scorer(system_prompt, user_prompt, temperature=temperature)

# -----------------------------------------------------------------------------
# 2. Helper: read the current candidate prompt.
# -----------------------------------------------------------------------------

def load_trigger_text(prompt_path: str) -> str:
    """
    Read text from the prompt file path provided by OpenEvolve.
    """
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read().strip()


# -----------------------------------------------------------------------------
# 4. Helper: call AgentDojo benchmark_suite once for a given prompt.
# -----------------------------------------------------------------------------

def run_agentdojo_with_prompt(
        trigger_text: str,
        stage: str = "stage2",
        agentdojo_cfg: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
    """
    Directly call agentdojo_benchmark.benchmark_suite(...) and pass trigger_text
    to AgentPipeline as the system_message.

    config.yaml needs an agentdojo section, for example:

    agentdojo:
      benchmark_module: "agentdojo_benchmark"
      benchmark_version: "v1.2.1"
      suite_name: "default_suite"
      logdir: "./runs_evolve"
      model: "gpt-4o-2024-05-13"
      model_id: null
      attack: null
      defense: null
      tool_delimiter: "tool"
      user_tasks: []          # Optional subset.
      injection_tasks: []     # Optional subset.

    Returns:
        {
          "task_success_rate": float,
          "attack_success_rate": float,
          "raw_results": SuiteResults
        }
    """

    cfg = agentdojo_cfg or DEFAULT_AGENTDOJO_CFG
    if not cfg:
        raise ValueError(
            "agentdojo_cfg is None and DEFAULT_AGENTDOJO_CFG is empty; "
            "please set evaluator.extra_kwargs.agentdojo_cfg or top-level agentdojo in config.yaml"
        )
    agentdojo_cfg = cfg

    benchmark_version = agentdojo_cfg.get("benchmark_version", "v1.2.1")
    suite_name = agentdojo_cfg.get("suite_name")
    if suite_name is None:
        raise ValueError("agentdojo_cfg['suite_name'] is required")

    logdir = Path(agentdojo_cfg.get("logdir", "./runs"))
    logdir.mkdir(parents=True, exist_ok=True)

    model_name = agentdojo_cfg.get("model", "gpt-4o-2024-05-13")
    model_enum = ModelsEnum(model_name)
    model_id = agentdojo_cfg.get("model_id", None)
    temperature = agentdojo_cfg.get("temperature", None)
    seed = agentdojo_cfg.get("seed", None)
    attack = "evolve"

    raw_defense = cfg.get("defense", None)
    if raw_defense is None:
        defense = None
    elif isinstance(raw_defense, str) and raw_defense.strip().lower() in ("", "none", "null"):
        defense = None
    else:
        # Validate here to make debugging easier.
        if raw_defense not in DEFENSES:
            raise ValueError(
                f"Unknown defense '{raw_defense}', available defenses={DEFENSES}"
            )
        defense = raw_defense
        
    tool_delimiter = agentdojo_cfg.get("tool_delimiter", "tool")

    user_tasks = tuple(agentdojo_cfg.get("user_tasks", []))
    injection_tasks = tuple(agentdojo_cfg.get("injection_tasks", []))

    quiet = bool(agentdojo_cfg.get("quiet", True))
    def _maybe_print(message: str) -> None:
        if not quiet:
            print(message)

    _maybe_print(f"[AgentDojo] stage={stage}, suite='{suite_name}', model='{model_enum}'")
    if attack is not None:
        _maybe_print(f"[AgentDojo] attack='{attack}'")
    if defense is not None:
        _maybe_print(f"[AgentDojo] defense='{defense}'")
    if len(user_tasks) > 0:
        _maybe_print(f"[AgentDojo] user_tasks={user_tasks}")
    if len(injection_tasks) > 0:
        _maybe_print(f"[AgentDojo] injection_tasks={injection_tasks}")
    if temperature is not None:
        _maybe_print(f"[AgentDojo] Using model '{model_name}' with temperature={temperature}")
    if seed is not None:
        _maybe_print(f"[AgentDojo] seed={seed}")
    
    attack_module.CURRENT_INJECTION = trigger_text

    pipeline = AgentPipeline.from_config(
        PipelineConfig(
            llm=model_enum,
            model_id=model_id,
            defense=defense,
            tool_delimiter=tool_delimiter,
            system_message_name=None,
            system_message=None,
            tool_output_format=None,
            temperature=temperature,
            seed=seed
        )
    )
    pipeline_name = pipeline.name or model_name
    suite = get_suite(benchmark_version, suite_name)

    attacker = load_attack(attack, suite, pipeline)
    inj_id = injection_tasks[0]
    inj_task = suite.get_injection_task_by_id(inj_id)
    injection_goal = getattr(inj_task, "GOAL", None) or getattr(inj_task, "PROMPT", None)

    user_tasks_to_run = [suite.get_user_task_by_id(user_task_id) for user_task_id in user_tasks]
    user_task = user_tasks_to_run[0]
    user_task_goal = getattr(user_task, "GOAL", None) or getattr(user_task, "PROMPT", None)

    task_injections = attacker.attack(user_task, inj_task)
    environment = suite.load_and_inject_default_environment(task_injections)
    gt = inj_task.ground_truth(environment)
    def func_call_to_dict(call):
    # If this is pydantic, model_dump()/dict() could be used; otherwise convert manually.
        return {
            "function": call.function,
            "args": getattr(call, "args", None),
            "placeholder_args": getattr(call, "placeholder_args", None),
        }
    expected_calls = [func_call_to_dict(c) for c in gt]
    if quiet:
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        ctx = contextlib.ExitStack()
        ctx.enter_context(contextlib.redirect_stdout(stdout_buf))
        ctx.enter_context(contextlib.redirect_stderr(stderr_buf))
    else:
        ctx = contextlib.nullcontext()

    with ctx:
        results: SuiteResults = benchmark_suite(     
            suite=suite,
            model=model_enum,
            logdir=logdir,
            force_rerun=False,
            benchmark_version=benchmark_version,
            user_tasks=user_tasks,
            injection_tasks=injection_tasks,
            model_id=model_id,
            attack=attack,
            defense=defense,
            tool_delimiter=tool_delimiter,
            system_message_name=None,
            system_message=None,
            live=None,
            tool_output_format=None,
            # temperature=temperature,
            # seed=seed
        )

    _maybe_print("-" * 80)

    # ====== Add a hash suffix to the trace file to prevent overwrites. ======
    hash_str = hashlib.sha1(trigger_text.encode("utf-8")).hexdigest()[:8]
    attack_name = attack or "none"
    orig_trace_path = (logdir / pipeline_name / suite_name / user_tasks[0] / attack_name / f"{inj_id}.json")
    hashed_filename = f"{inj_id}_{hash_str}.json"
    func_trace_path = orig_trace_path.with_name(hashed_filename)
    trace_dir = orig_trace_path.parent
    selected_trace_path = None
    try:
        if orig_trace_path.exists():
            # Rename only if it has not already been renamed to avoid duplicate rename errors.
            if not func_trace_path.exists():
                orig_trace_path.rename(func_trace_path)
                _maybe_print(f"[AgentDojo] Renamed trace file to {func_trace_path.name}")
            selected_trace_path = func_trace_path
        else:
            candidates = sorted(
                trace_dir.glob(f"{inj_id}*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                selected_trace_path = candidates[0]
            else:
                _maybe_print(f"[AgentDojo] Default trace file not found: {orig_trace_path}")
    except Exception as e:
        _maybe_print(f"[AgentDojo] ⚠️ Failed to rename trace file: {orig_trace_path} -> {func_trace_path}, err={e}")
    # ==========================================================

    _maybe_print(f"[AgentDojo] User task {user_tasks[0]} goal/prompt: {GREEN}{user_task_goal}{RESET}")
    _maybe_print(f"[AgentDojo] Injection task {inj_id} goal/prompt: {RED}{injection_goal}{RESET}")

    _maybe_print(f"[AgentDojo] expect {len(expected_calls)} function calls:{RED}")
    for i, call in enumerate(expected_calls, 1):
        fn = call.get("function")
        args = call.get("args")
        _maybe_print(f"  #{i}: {fn}({args})")
    _maybe_print(RESET)

    # Read func_trace from the log.
    trace_messages = None
    trace_data = None
    path_to_read = selected_trace_path or func_trace_path
    if path_to_read.exists():
        try:
            with open(path_to_read, "r", encoding="utf-8") as f:
                trace_data = json.load(f)
            func_trace = (trace_data.get("func_trace") or [])
            trace_messages = trace_data.get("messages")

            _maybe_print(f"[AgentDojo] Loaded {len(func_trace)} function calls from trace file:{YELLOW}")
            for i, call in enumerate(func_trace, 1):
                fn = call.get("function")
                args = call.get("args")
                _maybe_print(f"  #{i}: {fn}({args})")
            _maybe_print(RESET)

        except Exception as e:
            _maybe_print(f"[AgentDojo] ⚠️ Failed to read func_trace from {path_to_read}: {e}")
            func_trace = []
            trace_messages = None
            trace_data = None
    else:
        _maybe_print(f"[AgentDojo] ⚠️ Trace file not found: {path_to_read}")
        func_trace = []
        trace_messages = None
        trace_data = None

    # -----------------------
    # Extract metrics from SuiteResults.
    # -----------------------
    utility_values = list(results["utility_results"].values())
    if len(utility_values) > 0:
        task_success_rate = sum(utility_values) / len(utility_values)
    else:
        task_success_rate = -1

    security_values = list(results["security_results"].values())
    if len(security_values) > 0:
        attack_success_rate = sum(security_values) / len(security_values)
    else:
        attack_success_rate = -1
    
    injection_tasks_utility_values = list(results["injection_tasks_utility_results"].values())
    if len(injection_tasks_utility_values) > 0:
        injection_tasks_success_rate = sum(injection_tasks_utility_values) / len(injection_tasks_utility_values)
    else:
        injection_tasks_success_rate = -1
    
    _maybe_print(f"[AgentDojo] task_success_rate={YELLOW}{task_success_rate:.3f}{RESET}, ")
    _maybe_print(f"[AgentDojo] attack_success_rate={YELLOW}{attack_success_rate:.3f}{RESET}, ")
    _maybe_print(f"[AgentDojo] injection_tasks_success_rate={YELLOW}{injection_tasks_success_rate:.3f}{RESET}, ")

    attack_success = attack_success_rate == 1.0
    defense_state = _build_defense_state(defense, trace_messages, trace_data, expected_calls)
    scorer_input = {
        "injection_task": injection_goal,
        "attack_success": attack_success,
        "defense_state": defense_state,
        "messages": trace_messages,
    }
    system_prompt, user_template = _load_scorer_prompts(defense)
    user_prompt = _render_user_prompt(user_template, scorer_input)
    scorer_result = _call_scorer_llm(system_prompt, user_prompt)
    scorer_score = float(scorer_result.get("score", 0.0))
    scorer_rationale = scorer_result.get("rationale")
    _maybe_print(f"[AgentDojo] LLM scorer score: {YELLOW}{scorer_score:.2f}{RESET}")

    _maybe_print("-" * 80)

    return {
        "user_task_id": user_tasks[0],
        "user_task_goal": user_task_goal,
        "injection_task_id": inj_id,
        "injection_task_goal": injection_goal,
        "expected_function_calls": expected_calls,
        "executed_function_calls": func_trace,
        "trace_messages": trace_messages,
        "task_success_rate": task_success_rate,
        "attack_success_rate": attack_success_rate,
        "attack_task_success_rate": injection_tasks_success_rate,
        "scorer_score": scorer_score,
        "scorer_rationale": scorer_rationale,
        "raw_results": results,
    }

# -----------------------------------------------------------------------------
# 6. Stage 2 evaluation: full evaluation.
# -----------------------------------------------------------------------------
def evaluate_stage2(prompt_path: str, agentdojo_cfg: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Stage 2 evaluation: full evaluation used for the final score.
    """
    quiet = bool((agentdojo_cfg or {}).get("quiet", True))
    def _maybe_print(message: str) -> None:
        if not quiet:
            print(message)

    _maybe_print("-" * 80)
    _maybe_print("[Stage2] Starting AgentDojo evaluation...")
    _maybe_print("-" * 80)

    res: Dict[str, Any] = {}
    try:
        trigger_text = load_trigger_text(prompt_path)
        _maybe_print(f"[Stage2] Loaded prompt from: {prompt_path}")

        t0 = time.time()
        prev_disable = None
        if quiet:
            prev_disable = logging.root.manager.disable
            logging.disable(logging.CRITICAL)
        # Pass in the modified base_cfg here.
        try:
            res = run_agentdojo_with_prompt(
                trigger_text,
                stage="stage2",
                agentdojo_cfg=agentdojo_cfg,
            )
        finally:
            if prev_disable is not None:
                logging.disable(prev_disable)

        elapsed_ms = (time.time() - t0) * 1000.0

        task_success = float(res.get("task_success_rate", 0.0))
        attack_success = float(res.get("attack_success_rate", 0.0))
        attack_task_success_rate = float(res.get("attack_task_success_rate", 0.0))
        scorer_score = float(res.get("scorer_score", 0.0))
        scorer_rationale = res.get("scorer_rationale")
        _maybe_print(
            f"[Stage2] utility={task_success:.3f}, "
            f"attack_success_rate={attack_success:.3f}, "
            f"attack_task_success_rate={attack_task_success_rate:.3f}, "
            f"scorer_score={scorer_score:.2f}, time={elapsed_ms:.1f}ms"
        )

        return {
            "utility": task_success,
            "attack_success_rate": attack_success,
            "attack_task_success_rate": attack_task_success_rate,
            "combined_score": scorer_score,
            "scorer_score": scorer_score,
            "scorer_rationale": scorer_rationale,
            "user_task_id": res.get("user_task_id"),
            "user_task_goal": res.get("user_task_goal"),
            "injection_task_id": res.get("injection_task_id"),
            "injection_task_goal": res.get("injection_task_goal"),
            "expected_function_calls": res.get("expected_function_calls"),
            "executed_function_calls": res.get("trace_messages"),
            "eval_time_ms": elapsed_ms,
            "eval_time_ms": elapsed_ms,
        }

    except Exception as e:
        _maybe_print(f"[Stage2] Evaluation failed: {e}")
        if not quiet:
            traceback.print_exc()
        _maybe_print("-" * 80)

        return {
            "utility": 0.0,
            "attack_success_rate": 0.0,
            "attack_task_success_rate": 0.0,
            "combined_score": 0.0,
            "user_task_id": res.get("user_task_id"),
            "user_task_goal": res.get("user_task_goal"),
            "injection_task_id": res.get("injection_task_id"),
            "injection_task_goal": res.get("injection_task_goal"),
            "expected_function_calls": res.get("expected_function_calls"),
            "executed_function_calls": None,
            "eval_time_ms": 0.0,
            "error": str(e),
        }


# -----------------------------------------------------------------------------
# 7. Main evaluate() entry point for backwards compatibility.
# -----------------------------------------------------------------------------

def evaluate(
    prompt_path: str,
    agentdojo_cfg: Dict[str, Any] | None = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Main evaluation function - for backwards compatibility.
    OpenEvolve calls this by default; this implementation directly uses Stage 2.
    """
    if agentdojo_cfg is None:
        agentdojo_cfg = kwargs.get("agentdojo_cfg")
    return evaluate_stage2(prompt_path, agentdojo_cfg=agentdojo_cfg)
