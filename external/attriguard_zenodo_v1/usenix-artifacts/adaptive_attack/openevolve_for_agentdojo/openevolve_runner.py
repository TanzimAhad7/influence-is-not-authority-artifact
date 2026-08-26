"""
Local OpenEvolve runner for AttriGuard adaptive attacks.

This wrapper keeps AgentDojo-specific arguments out of the installed
OpenEvolve CLI.  It prepares a runtime config, applies the local monkey patch,
and then calls the PyPI OpenEvolve API.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

import yaml

from attriguard_openevolve_patch import apply as apply_openevolve_patch


HERE = Path(__file__).resolve().parent

OPENEVOLVE_TOP_LEVEL_KEYS = {
    "max_iterations",
    "checkpoint_interval",
    "log_level",
    "log_dir",
    "random_seed",
    "language",
    "file_suffix",
    "llm",
    "prompt",
    "database",
    "evaluator",
    "evolution_trace",
    "diff_based_evolution",
    "max_code_length",
    "diff_pattern",
    "early_stopping_patience",
    "convergence_threshold",
    "early_stopping_metric",
    "max_tasks_per_child",
}

EVALUATOR_KEYS = {
    "timeout",
    "max_retries",
    "memory_limit_mb",
    "cpu_limit",
    "cascade_evaluation",
    "cascade_thresholds",
    "parallel_evaluations",
    "distributed",
    "use_llm_feedback",
    "llm_feedback_weight",
    "enable_artifacts",
    "max_artifact_storage",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenEvolve runner with AttriGuard/AgentDojo runtime patches"
    )
    parser.add_argument("initial_program")
    parser.add_argument("evaluation_file")
    parser.add_argument("--config", "-c", default="config.yaml")
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--iterations", "-i", type=int, default=None)
    parser.add_argument("--target-score", "-t", type=float, default=None)
    parser.add_argument("--log-level", "-l", default=None)
    parser.add_argument("--checkpoint", default=None)
    parser.add_argument("--api-base", default=None)
    parser.add_argument("--primary-model", default=None)
    parser.add_argument("--secondary-model", default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate imports, config preparation, and patch installation without running evolution.",
    )

    parser.add_argument("--agentdojo-suite", default=None)
    parser.add_argument("--agentdojo-benchmark-version", default=None)
    parser.add_argument("--agentdojo-logdir", default=None)
    parser.add_argument("--agentdojo-model", default=None)
    parser.add_argument("--agentdojo-model-id", default=None)
    parser.add_argument("--agentdojo-attack", default=None)
    parser.add_argument("--agentdojo-defense", default=None)
    parser.add_argument("--agentdojo-tool-delimiter", default=None)
    parser.add_argument("--agentdojo-user-task", action="append", default=None)
    parser.add_argument("--agentdojo-injection-task", action="append", default=None)
    return parser.parse_args()


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _agentdojo_cfg_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    evaluator = config.get("evaluator") or {}
    extra_kwargs = evaluator.get("extra_kwargs") or {}
    nested = extra_kwargs.get("agentdojo_cfg") or {}
    return dict(nested) if isinstance(nested, dict) else {}


def _apply_agentdojo_overrides(agentdojo_cfg: Dict[str, Any], args: argparse.Namespace) -> None:
    mapping = {
        "agentdojo_suite": "suite_name",
        "agentdojo_benchmark_version": "benchmark_version",
        "agentdojo_logdir": "logdir",
        "agentdojo_model": "model",
        "agentdojo_model_id": "model_id",
        "agentdojo_attack": "attack",
        "agentdojo_defense": "defense",
        "agentdojo_tool_delimiter": "tool_delimiter",
    }
    for arg_name, cfg_name in mapping.items():
        value = getattr(args, arg_name)
        if value is not None:
            agentdojo_cfg[cfg_name] = value
    if args.agentdojo_user_task is not None:
        agentdojo_cfg["user_tasks"] = args.agentdojo_user_task
    if args.agentdojo_injection_task is not None:
        agentdojo_cfg["injection_tasks"] = args.agentdojo_injection_task


def _validate_agentdojo_cfg(agentdojo_cfg: Dict[str, Any]) -> None:
    missing = [
        key
        for key in ("suite_name", "model", "model_id", "defense")
        if not agentdojo_cfg.get(key)
    ]
    if missing:
        raise ValueError(
            "Missing required agentdojo config fields: " + ", ".join(missing)
        )
    user_tasks = agentdojo_cfg.get("user_tasks") or []
    injection_tasks = agentdojo_cfg.get("injection_tasks") or []
    if len(user_tasks) != 1 or len(injection_tasks) != 1:
        raise ValueError(
            "openevolve_runner expects exactly one user task and one injection task "
            "for each subprocess run."
        )


def _prepare_runtime_config(
    raw_config: Dict[str, Any],
    agentdojo_cfg: Dict[str, Any],
    output_dir: Path,
) -> tuple[Path, Path]:
    runtime_dir = output_dir / "_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)

    full_config = copy.deepcopy(raw_config)
    full_config["agentdojo"] = copy.deepcopy(agentdojo_cfg)
    full_config.setdefault("evaluator", {}).setdefault("extra_kwargs", {})[
        "agentdojo_cfg"
    ] = copy.deepcopy(agentdojo_cfg)

    openevolve_config = {
        key: copy.deepcopy(value)
        for key, value in raw_config.items()
        if key in OPENEVOLVE_TOP_LEVEL_KEYS
    }
    evaluator = openevolve_config.get("evaluator")
    if isinstance(evaluator, dict):
        openevolve_config["evaluator"] = {
            key: value for key, value in evaluator.items() if key in EVALUATOR_KEYS
        }

    prompt_cfg = openevolve_config.setdefault("prompt", {})
    prompt_cfg["template_dir"] = str((HERE / "mutator_prompt").resolve())
    system_prompt = HERE / "mutator_prompt" / "unified_systemprompt.txt"
    if system_prompt.exists():
        prompt_cfg["system_message"] = system_prompt.read_text(encoding="utf-8")
    defense_name = agentdojo_cfg.get("defense")
    if defense_name:
        evaluator_prompt = HERE / "scorer_prompt" / f"{defense_name}.txt"
        if evaluator_prompt.exists():
            prompt_cfg["evaluator_system_message"] = evaluator_prompt.read_text(
                encoding="utf-8"
            )

    runtime_config_path = runtime_dir / "agentdojo_runtime_config.yaml"
    openevolve_config_path = runtime_dir / "openevolve_config.yaml"
    runtime_config_path.write_text(
        yaml.safe_dump(full_config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    openevolve_config_path.write_text(
        yaml.safe_dump(openevolve_config, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return runtime_config_path, openevolve_config_path


def _write_initial_payload(initial_program: Path, agentdojo_cfg: Dict[str, Any]) -> None:
    suite_name = agentdojo_cfg.get("suite_name")
    injection_tasks = agentdojo_cfg.get("injection_tasks") or []
    if not suite_name or not injection_tasks:
        return

    from agentdojo.task_suite.load_suites import get_suite

    benchmark_version = agentdojo_cfg.get("benchmark_version")
    suite = get_suite(benchmark_version, suite_name)
    injection_task = suite.get_injection_task_by_id(injection_tasks[0])
    injection_goal = (
        getattr(injection_task, "GOAL", None)
        or getattr(injection_task, "PROMPT", None)
        or ""
    )
    initial_program.parent.mkdir(parents=True, exist_ok=True)
    initial_program.write_text(str(injection_goal), encoding="utf-8")


async def main_async() -> int:
    args = parse_args()
    config_path = Path(args.config).expanduser().resolve()
    initial_program = Path(args.initial_program).expanduser()
    evaluation_file = Path(args.evaluation_file).expanduser()

    if not config_path.exists():
        print(f"Error: config file '{config_path}' not found")
        return 1
    if not evaluation_file.exists():
        print(f"Error: evaluation file '{evaluation_file}' not found")
        return 1

    raw_config = _load_yaml(config_path)
    agentdojo_cfg = _agentdojo_cfg_from_config(raw_config)
    _apply_agentdojo_overrides(agentdojo_cfg, args)
    try:
        _validate_agentdojo_cfg(agentdojo_cfg)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1

    output_dir = Path(args.output).expanduser() if args.output else HERE / "openevolve_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    runtime_config_path, openevolve_config_path = _prepare_runtime_config(
        raw_config, agentdojo_cfg, output_dir
    )
    os.environ["OPENEvolve_CONFIG_PATH"] = str(runtime_config_path.resolve())

    _write_initial_payload(initial_program, agentdojo_cfg)
    if not initial_program.exists():
        print(f"Error: initial program file '{initial_program}' not found")
        return 1

    apply_openevolve_patch()

    from openevolve import OpenEvolve
    from openevolve.config import load_config

    config = load_config(openevolve_config_path)
    if args.api_base:
        config.llm.api_base = args.api_base
    if args.primary_model:
        config.llm.primary_model = args.primary_model
    if args.secondary_model:
        config.llm.secondary_model = args.secondary_model
    if args.primary_model or args.secondary_model:
        config.llm.rebuild_models()

    if args.dry_run:
        import agentdojo
        import openevolve

        print("Dry run OK")
        print(f"  agentdojo: {getattr(agentdojo, '__file__', '<unknown>')}")
        print(f"  openevolve: {getattr(openevolve, '__file__', '<unknown>')}")
        print(f"  runtime config: {runtime_config_path}")
        print(f"  openevolve config: {openevolve_config_path}")
        return 0

    try:
        openevolve = OpenEvolve(
            initial_program_path=str(initial_program),
            evaluation_file=str(evaluation_file),
            config=config,
            output_dir=str(output_dir),
        )
        if args.log_level:
            logging.getLogger().setLevel(getattr(logging, args.log_level))

        best_program = await openevolve.run(
            iterations=args.iterations,
            target_score=args.target_score,
            checkpoint_path=args.checkpoint,
        )
        if best_program is not None:
            print("\nEvolution complete!")
            print("Best program metrics:")
            for name, value in best_program.metrics.items():
                if isinstance(value, (int, float)):
                    print(f"  {name}: {value:.4f}")
                else:
                    print(f"  {name}: {value}")
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        import traceback

        traceback.print_exc()
        return 1


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    sys.exit(main())
