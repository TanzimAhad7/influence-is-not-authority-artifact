import warnings
warnings.filterwarnings(
    "ignore",
    message=r"You are using a Python version.*google\.api_core.*",
    category=FutureWarning,
)

import importlib
import os
import logging
from itertools import repeat
from multiprocessing import Pool
from pathlib import Path
from typing import Literal

import click
import yaml
from dotenv import load_dotenv
from rich import print
from rich.live import Live
from rich.logging import RichHandler

from my_agent_pipeline import DEFENSES, AgentPipeline, PipelineConfig
from agentdojo.attacks.attack_registry import ATTACKS, load_attack
from agentdojo.benchmark import SuiteResults, benchmark_suite_with_injections, benchmark_suite_without_injections
from agentdojo.logging import OutputLogger
from agentdojo.models import ModelsEnum
from agentdojo.task_suite.load_suites import get_suite, get_suites
from agentdojo.task_suite.task_suite import TaskSuite

import pydantic_fix
from runtime_patches import apply_runtime_workarounds
import combine_attack

def load_agentdojo_cfg(config_path: str | Path = "config.yaml") -> dict:
    """
    Read evaluator.extra_kwargs.agentdojo_cfg from OpenEvolve's config.yaml.
    Return {} if the file does not exist or the field is missing.
    """
    if isinstance(config_path, str):
        config_path = Path(config_path)

    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    evaluator_cfg = cfg.get("evaluator", {}) or {}
    extra_kwargs = evaluator_cfg.get("extra_kwargs", {}) or {}
    agentdojo_cfg = extra_kwargs.get("agentdojo_cfg", {}) or {}

    return agentdojo_cfg

def _parse_task_pairs(task_pairs_cfg: list) -> list[tuple[str, str, str]]:
    """Parse task_pairs from config into (suite, user_task, injection_task) tuples.

    Supported formats in config:
      - "suite:user_task&injection_task"
      - {"suite": "...", "task_pair": "user_task&injection_task"}
      - {"suite": "...", "user_task": "...", "injection_task": "..."}
    """
    parsed: list[tuple[str, str, str]] = []
    for item in task_pairs_cfg:
        if isinstance(item, str):
            if ":" not in item or "&" not in item:
                raise ValueError(f"Invalid task_pairs entry '{item}'. Expected 'suite:user_task&injection_task'.")
            suite_name, pair = item.split(":", 1)
            user_task, injection_task = pair.split("&", 1)
            parsed.append((suite_name, user_task, injection_task))
            continue
        if isinstance(item, dict):
            suite_name = item.get("suite")
            if suite_name is None:
                raise ValueError(f"Invalid task_pairs entry {item}. Missing 'suite'.")
            if "task_pair" in item:
                pair = item["task_pair"]
                if "&" not in pair:
                    raise ValueError(f"Invalid task_pair '{pair}'. Expected 'user_task&injection_task'.")
                user_task, injection_task = pair.split("&", 1)
                parsed.append((suite_name, user_task, injection_task))
                continue
            user_task = item.get("user_task")
            injection_task = item.get("injection_task")
            if user_task is None or injection_task is None:
                raise ValueError(f"Invalid task_pairs entry {item}. Missing 'user_task' or 'injection_task'.")
            parsed.append((suite_name, user_task, injection_task))
            continue
        raise ValueError(f"Invalid task_pairs entry type: {type(item)}")
    return parsed

def benchmark_suite(
    suite: TaskSuite,
    model: ModelsEnum,
    logdir: Path,
    force_rerun: bool,
    benchmark_version: str,
    user_tasks: tuple[str, ...] = (),
    injection_tasks: tuple[str, ...] = (),
    model_id: str | None = None,
    attack: str | None = None,
    defense: str | None = None,
    tool_delimiter: str = "tool",
    system_message_name: str | None = None,
    system_message: str | None = None,
    live: Live | None = None,
    tool_output_format: Literal["yaml", "json"] | None = None,
) -> SuiteResults:
    if not load_dotenv(".env"):
        warnings.warn("No .env file found")

    print(f"Running benchmark for suite: '{suite.name}'")
    print(f"Using model: '{model}'")
    if attack is not None:
        print(f"Using attack: '{attack}'")
    if defense is not None:
        print(f"Using defense: '{defense}'")
    if len(user_tasks) > 0:
        print(f"Using user tasks: {', '.join(user_tasks)}")

    pipeline = AgentPipeline.from_config(
        PipelineConfig(
            llm=model,
            model_id=model_id,
            defense=defense,
            tool_delimiter=tool_delimiter,
            system_message_name=system_message_name,
            system_message=system_message,
            tool_output_format=tool_output_format,
            attack=attack,
            suite_name=suite.name,
        )
    )
    with OutputLogger(str(logdir), live=live):
        if attack is None:
            results = benchmark_suite_without_injections(
                pipeline,
                suite,
                user_tasks=user_tasks if len(user_tasks) != 0 else None,
                logdir=logdir,
                force_rerun=force_rerun,
                benchmark_version=benchmark_version,
            )
        else:
            attacker_ = load_attack(attack, suite, pipeline)
            results = benchmark_suite_with_injections(
                pipeline,
                suite,
                attacker_,
                user_tasks=user_tasks if len(user_tasks) != 0 else None,
                injection_tasks=injection_tasks if len(injection_tasks) != 0 else None,
                logdir=logdir,
                force_rerun=force_rerun,
                benchmark_version=benchmark_version,
            )
    print(f"Finished benchmark for suite: '{suite.name}'")

    return results


def show_results(suite_name: str, results: SuiteResults, show_security_results: bool):
    utility_results = results["utility_results"].values()
    avg_utility = sum(utility_results) / len(utility_results)

    print(f"Results for suite {suite_name}")
    print(f"Average utility: {avg_utility * 100:.2f}%")

    if show_security_results:
        passed_injection_tasks = sum(results["injection_tasks_utility_results"].values())
        total_injection_tasks = len(results["injection_tasks_utility_results"])
        print(f"\nPassed injection tasks as user tasks: {passed_injection_tasks}/{total_injection_tasks}")

        security_results = results["security_results"].values()
        avg_security = sum(security_results) / len(security_results)
        print(f"Average security: {avg_security * 100:.2f}%")


@click.command()
@click.option(
    "--model",
    default=None,
    type=click.Choice([value for value in ModelsEnum]),
    help="The language model to benchmark. Defaults to `gpt-4o-2024-05-13`.",
)
@click.option(
    "--model-id",
    type=str,
    default=None,
    help="The model id for local models.",
)
@click.option(
    "--benchmark-version",
    default=None,
    type=str,
    help="The version of the benchmark to run. Defaults to `v1.2`.",
)
@click.option(
    "--tool-delimiter",
    type=str,
    default=None,
    help="Which tool delimiter to use. Used for local models only.",
)
@click.option(
    "--logdir",
    default=None,
    type=Path,
    help="The directory to save logs. Defaults to `./runs`.",
)
@click.option(
    "--attack",
    type=str,
    default=None,
    help=f"The attack to use. `None` by default. It should be one of {ATTACKS}, or a custom attack defined and registered in of of the `--module-to-load`. If `None`, no attack is used.",
)
@click.option(
    "--defense",
    type=click.Choice(DEFENSES),
    default=None,
    help="The defense to use. `None` by default.",
)
@click.option(
    "--system-message-name",
    type=str,
    default=None,
    help="The name of the system message to use among the default ones in `data/system_messages.yaml`.",
)
@click.option(
    "--system-message",
    type=str,
    default=None,
    help="The system message to use (as a string). If provided, `--system-message-name` is ignored.",
)
@click.option(
    "--user-task",
    "-ut",
    "user_tasks",
    type=str,
    multiple=True,
    default=tuple(),
    help="The user tasks to benchmark. If not provided, all tasks in the suite are run.",
)
@click.option(
    "--injection-task",
    "-it",
    "injection_tasks",
    type=str,
    multiple=True,
    default=tuple(),
    help="The user tasks to benchmark. If not provided, all tasks in the suite are run.",
)
@click.option(
    "--suite",
    "-s",
    "suites",
    type=str,
    multiple=True,
    default=tuple(),
    help="The user tasks to benchmark. If not provided, all tasks in the suite are run.",
)
@click.option(
    "--max-workers",
    type=int,
    default=1,
    help="How many suites can be benchmarked in parallel through multithreading. Nothing is parallelized by default.",
)
@click.option(
    "--force-rerun",
    "-f",
    is_flag=True,
    help="Whether to re-run tasks that have already been run.",
)
@click.option(
    "--module-to-load",
    "-ml",
    "modules_to_load",
    type=str,
    multiple=True,
    default=tuple(),
    help="The modules to load before running the benchmark. Useful for registering custom attacks, defenses, or suites.",
)
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("config.yaml"),
    show_default=True,
    help="Path to the YAML config file (used to load agentdojo_cfg).",
)
def main(
    suites: tuple[str, ...],
    model: ModelsEnum | None,
    benchmark_version: str | None = None,
    logdir: Path | None = None,
    user_tasks: tuple[str, ...] = (),
    injection_tasks: tuple[str, ...] = (),
    model_id: str | None = None,
    attack: str | None = None,
    defense: str | None = None,
    tool_delimiter: str | None = None,
    system_message_name: str | None = None,
    system_message: str | None = None,
    max_workers: int = 1,
    force_rerun: bool = False,
    modules_to_load: tuple[str, ...] = (),
    config_path: Path = Path("config.yaml"),
):
    apply_runtime_workarounds()

    os.environ["OPENEvolve_CONFIG_PATH"] = str(config_path)
    agentdojo_cfg = load_agentdojo_cfg(config_path)

    if benchmark_version is None:
        benchmark_version = agentdojo_cfg.get("benchmark_version", "v1.2.3")

    if len(suites) == 0:
        suite_name = agentdojo_cfg.get("suite_name")
        if suite_name:
            suites = (suite_name,)

    if model is None:
        model_name = agentdojo_cfg.get("model", "gpt-4o-2024-05-13")
        model = ModelsEnum(model_name)

    if model_id is None:
        model_id = agentdojo_cfg.get("model_id")

    if logdir is None:
        logdir_str = agentdojo_cfg.get("logdir", "./runs")
        logdir = Path(logdir_str)

    if attack is None:
        attack = agentdojo_cfg.get("attack")
    if defense is None:
        defense = agentdojo_cfg.get("defense") or None

    if tool_delimiter is None:
        tool_delimiter = agentdojo_cfg.get("tool_delimiter", "tool")

    if len(user_tasks) == 0:
        user_tasks = tuple(agentdojo_cfg.get("user_tasks") or [])
    if len(injection_tasks) == 0:
        injection_tasks = tuple(agentdojo_cfg.get("injection_tasks") or [])
    task_pairs_cfg = agentdojo_cfg.get("task_pairs") or []
    task_pairs = _parse_task_pairs(task_pairs_cfg) if task_pairs_cfg else []

    for module in modules_to_load:
        importlib.import_module(module)

    if len(suites) == 0:
        suites = tuple(get_suites(benchmark_version).keys())

    if task_pairs and (len(user_tasks) != 0 or len(injection_tasks) != 0):
        raise ValueError("Do not combine task_pairs with user_tasks/injection_tasks in config or CLI.")

    if len(suites) != 1:
        print(f"Benchmarking suites {', '.join(suites)}")

    if len(suites) != 1 and len(user_tasks) != 0:
        raise ValueError("A user task can be specified only when one suite is being executed")

    if max_workers == 1:
        results = {}
        if task_pairs:
            for suite_name, user_task, injection_task in task_pairs:
                suite = get_suite(benchmark_version, suite_name)
                results.setdefault(suite_name, SuiteResults(
                    utility_results={}, security_results={}, injection_tasks_utility_results={}
                ))
                partial = benchmark_suite(
                    suite,
                    model,
                    logdir,
                    benchmark_version=benchmark_version,
                    user_tasks=(user_task,),
                    injection_tasks=(injection_task,),
                    model_id=model_id,
                    attack=attack,
                    defense=defense,
                    tool_delimiter=tool_delimiter,
                    system_message_name=system_message_name,
                    system_message=system_message,
                    force_rerun=force_rerun,
                )
                results[suite_name]["utility_results"].update(partial["utility_results"])
                results[suite_name]["security_results"].update(partial["security_results"])
                results[suite_name]["injection_tasks_utility_results"].update(
                    partial["injection_tasks_utility_results"]
                )
        else:
            for suite_name in suites:
                suite = get_suite(benchmark_version, suite_name)
                results[suite_name] = benchmark_suite(
                    suite,
                    model,
                    logdir,
                    benchmark_version=benchmark_version,
                    user_tasks=user_tasks,
                    injection_tasks=injection_tasks,
                    model_id=model_id,
                    attack=attack,
                    defense=defense,
                    tool_delimiter=tool_delimiter,
                    system_message_name=system_message_name,
                    system_message=system_message,
                    force_rerun=force_rerun,
                )
        combined_results = SuiteResults(utility_results={}, security_results={}, injection_tasks_utility_results={})
        for suite_name, result in results.items():
            show_results(suite_name, result, attack is not None)
            for user_task, injection_task in result["utility_results"]:
                new_user_task = suite_name + "_" + user_task
                combined_results["utility_results"][(new_user_task, injection_task)] = result["utility_results"][
                    (user_task, injection_task)
                ]
            for user_task, injection_task in result["security_results"]:
                new_user_task = suite_name + "_" + user_task
                combined_results["security_results"][(new_user_task, injection_task)] = result["security_results"][
                    (user_task, injection_task)
                ]
            for injection_task in result["injection_tasks_utility_results"]:
                new_injection_task = suite_name + "_" + injection_task
                combined_results["injection_tasks_utility_results"][new_injection_task] = result[
                    "injection_tasks_utility_results"
                ][injection_task]
        show_results("combined", combined_results, attack is not None)
        exit(0)

    with Pool(max_workers) as p:
        arguments = zip(
            suites,
            repeat(model),
            repeat(logdir),
            repeat(user_tasks),
            repeat(injection_tasks),
            repeat(model_id),
            repeat(attack),
            repeat(defense),
            repeat(tool_delimiter),
            repeat(system_message_name),
            repeat(system_message),
            repeat(force_rerun),
        )
        results = p.starmap(benchmark_suite, arguments)

    for suite_name, result in zip(suites, results):
        show_results(suite_name, result, attack is not None)


if __name__ == "__main__":
    format = "%(message)s"
    logging.basicConfig(
        format=format,
        level=logging.INFO,
        datefmt="%H:%M:%S",
        handlers=[RichHandler(show_path=False, markup=True)],
    )
    main()
