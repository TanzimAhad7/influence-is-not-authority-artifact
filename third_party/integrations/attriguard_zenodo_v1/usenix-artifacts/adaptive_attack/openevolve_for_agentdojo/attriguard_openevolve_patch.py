"""
Runtime patches for running AttriGuard adaptive attacks on PyPI OpenEvolve.

The released repository intentionally does not vendor OpenEvolve.  This module
keeps the small AgentDojo-specific behavior that our experiment needs and
installs it into the imported OpenEvolve package at process startup.
"""

from __future__ import annotations

import asyncio
import json
import logging
import multiprocessing as mp
import os
import random
import re
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent
MAX_JSON_CHARS = 6000
_UPSTREAM_PROMPT_SAMPLER = None


def _to_json_block(obj: Any, max_chars: int = MAX_JSON_CHARS) -> str:
    try:
        value = json.dumps(obj, ensure_ascii=False, indent=2, default=str)
    except Exception:
        value = json.dumps(str(obj), ensure_ascii=False)
    if len(value) > max_chars:
        value = value[:max_chars] + "\n... (truncated)"
    return value


def _load_runtime_agentdojo_cfg() -> Dict[str, Any]:
    config_path = os.environ.get("OPENEvolve_CONFIG_PATH")
    if not config_path:
        return {}
    path = Path(config_path)
    if not path.exists():
        return {}
    try:
        cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    top_level = cfg.get("agentdojo")
    if isinstance(top_level, dict) and top_level:
        return top_level
    evaluator = cfg.get("evaluator") or {}
    extra_kwargs = evaluator.get("extra_kwargs") or {}
    nested = extra_kwargs.get("agentdojo_cfg")
    return nested if isinstance(nested, dict) else {}


def _extract_candidates(llm_response: str) -> List[str]:
    if not llm_response:
        return []
    try:
        data = json.loads(llm_response)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", llm_response)
        if not match:
            return []
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    if not isinstance(data, dict):
        return []
    candidates = data.get("candidates")
    if not isinstance(candidates, list):
        return []
    return [str(candidate) for candidate in candidates if candidate is not None]


class PatchedPromptSampler:
    """Prompt sampler extension that adds AgentDojo/AttriGuard template fields."""

    def __init__(self, config: Any):
        upstream_cls = _UPSTREAM_PROMPT_SAMPLER
        if upstream_cls is None:
            from openevolve.prompt.sampler import PromptSampler as upstream_cls
        if upstream_cls is PatchedPromptSampler:
            raise RuntimeError("PatchedPromptSampler was installed without its upstream class")

        self._upstream = upstream_cls(config)
        self.config = self._upstream.config
        self.template_manager = self._upstream.template_manager
        self.system_template_override = None
        self.user_template_override = None
        self._identified_vuln_cache: Dict[Tuple[str, int], str] = {}

    def __getattr__(self, name: str) -> Any:
        return getattr(self._upstream, name)

    def set_templates(
        self, system_template: Optional[str] = None, user_template: Optional[str] = None
    ) -> None:
        self.system_template_override = system_template
        self.user_template_override = user_template
        self._upstream.set_templates(system_template, user_template)

    def build_prompt(
        self,
        current_program: str = "",
        parent_program: str = "",
        program_metrics: Dict[str, Any] | None = None,
        previous_programs: List[Dict[str, Any]] | None = None,
        top_programs: List[Dict[str, Any]] | None = None,
        inspirations: List[Dict[str, Any]] | None = None,
        language: str = "python",
        evolution_round: int = 0,
        diff_based_evolution: bool = True,
        template_key: Optional[str] = None,
        program_artifacts: Optional[Dict[str, Any]] = None,
        feature_dimensions: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, str]:
        from openevolve.utils.metrics_utils import (
            format_feature_coordinates,
            get_fitness_score,
            safe_numeric_average,
        )

        program_metrics = program_metrics or {}
        previous_programs = previous_programs or []
        top_programs = top_programs or []
        inspirations = inspirations or []

        metrics_whitelist = {"combined_score", "reaction_text"}
        filtered_metrics = {
            key: value for key, value in program_metrics.items() if key in metrics_whitelist
        }

        if template_key:
            user_template_key = template_key
        elif self.user_template_override:
            user_template_key = self.user_template_override
        else:
            user_template_key = "diff_user" if diff_based_evolution else "full_rewrite_user"

        user_template = self.template_manager.get_template(user_template_key)

        if self.system_template_override:
            system_message = self.template_manager.get_template(self.system_template_override)
        else:
            system_message = self.config.system_message
            if system_message in self.template_manager.templates:
                system_message = self.template_manager.get_template(system_message)

        metrics_str = self._upstream._format_metrics(filtered_metrics)
        json_input_template = self._template_expects_past_attempts_json(user_template)

        if json_input_template:
            improvement_areas = ""
            evolution_history = self._build_past_attempts_json(
                previous_programs,
                top_programs,
                inspirations,
                parent_program=kwargs.get("parent_program_dict"),
                safe_numeric_average=safe_numeric_average,
            )
        else:
            improvement_areas = self._upstream._identify_improvement_areas(
                current_program,
                parent_program,
                filtered_metrics,
                previous_programs,
                feature_dimensions,
            )
            evolution_history = self._upstream._format_evolution_history(
                previous_programs,
                top_programs,
                inspirations,
                language,
                feature_dimensions,
            )

        artifacts_section = ""
        if self.config.include_artifacts and program_artifacts:
            artifacts_section = self._upstream._render_artifacts(program_artifacts)

        if self.config.use_template_stochasticity:
            user_template = self._upstream._apply_template_variations(user_template)

        feature_dimensions = feature_dimensions or []
        fitness_score = get_fitness_score(filtered_metrics, feature_dimensions)
        feature_coords = format_feature_coordinates(filtered_metrics, feature_dimensions)

        metrics = program_metrics
        defense_description = self._load_defense_description(
            kwargs.get("defense_name"), kwargs.get("defense_description")
        )
        identified_vulnerabilities = self._load_identified_vulnerabilities(evolution_round)

        def maybe_json(value: Any) -> Any:
            return _to_json_block(value) if json_input_template else value

        context = {
            "metrics": metrics_str,
            "fitness_score": f"{fitness_score:.4f}",
            "feature_coords": feature_coords,
            "feature_dimensions": ", ".join(feature_dimensions) if feature_dimensions else "None",
            "improvement_areas": improvement_areas,
            "evolution_history": evolution_history,
            "current_program": current_program,
            "language": language,
            "artifacts": artifacts_section,
            "combined_score": metrics.get("combined_score"),
            "attack_success_rate": metrics.get("attack_success_rate"),
            "function_call_sequence_similarity": metrics.get(
                "function_call_sequence_similarity"
            ),
            "user_task_id": metrics.get("user_task_id"),
            "user_task_goal": maybe_json(metrics.get("user_task_goal") or ""),
            "injection_task_id": metrics.get("injection_task_id"),
            "injection_task_goal": maybe_json(metrics.get("injection_task_goal") or ""),
            "expected_function_calls_json": _to_json_block(
                metrics.get("expected_function_calls", [])
            ),
            "executed_function_calls_json": _to_json_block(
                metrics.get("executed_function_calls", [])
            ),
            "reaction_text": metrics.get("reaction_text"),
            "reaction_func": _to_json_block(metrics.get("reaction_func")),
            "defense_description": maybe_json(defense_description),
            "identified_vulnerabilities": identified_vulnerabilities,
        }
        context.update(kwargs)

        return {"system": system_message, "user": user_template.format(**context)}

    def _template_expects_past_attempts_json(self, user_template: str) -> bool:
        template_stripped = user_template.lstrip()
        return (
            template_stripped.startswith("{")
            and "{evolution_history}" in user_template
            and '"past_attempts"' in user_template
        )

    def _build_past_attempts_json(
        self,
        previous_programs: List[Dict[str, Any]],
        top_programs: List[Dict[str, Any]],
        inspirations: List[Dict[str, Any]],
        parent_program: Optional[Dict[str, Any]] = None,
        safe_numeric_average=None,
    ) -> str:
        past_attempts: List[Dict[str, Any]] = []
        seen_payloads = set()

        def append_program(program: Dict[str, Any]) -> None:
            metrics = program.get("metrics", {}) or {}
            score = metrics.get("scorer_score")
            if score is None:
                score = metrics.get("combined_score")
            if score is None and safe_numeric_average is not None:
                score = safe_numeric_average(metrics)
            rationale = metrics.get("scorer_rationale") or metrics.get("rationale") or ""
            payload = program.get("code", "") or ""
            if not payload or payload in seen_payloads:
                return
            seen_payloads.add(payload)
            past_attempts.append(
                {"payload": payload, "score": score, "rationale": rationale}
            )

        if parent_program:
            append_program(parent_program)

        for program in top_programs[: min(self.config.num_top_programs, len(top_programs))]:
            append_program(program)

        for program in inspirations[
            : min(self.config.num_diverse_programs, len(inspirations))
        ]:
            append_program(program)

        return json.dumps(past_attempts, ensure_ascii=False, indent=2)

    def _load_defense_description(
        self, defense_name: Optional[str], override_text: Optional[str] = None
    ) -> str:
        if override_text:
            return str(override_text)
        if not defense_name:
            return ""
        custom_dir = getattr(self.template_manager, "custom_dir", None)
        if not custom_dir:
            return ""
        desc_path = Path(custom_dir) / f"descriptionfor{defense_name}.txt"
        if not desc_path.exists():
            return ""
        return desc_path.read_text(encoding="utf-8").strip()

    def _load_identified_vulnerabilities(self, evolution_round: int) -> str:
        output_root = os.environ.get("OPENEvolve_OUTPUT_ROOT")
        suite_name = os.environ.get("OPENEvolve_SUITE")
        if not output_root or not suite_name:
            return "[]"

        refresh_bucket = max(0, evolution_round // 10)
        cache_key = (output_root, refresh_bucket)
        cached = self._identified_vuln_cache.get(cache_key)
        if cached is not None:
            return cached

        root = Path(output_root) / suite_name
        if not root.exists():
            self._identified_vuln_cache[cache_key] = "[]"
            return "[]"

        candidates: List[Dict[str, str]] = []
        for run_dir in root.iterdir():
            if not run_dir.is_dir():
                continue
            best_dir = run_dir / "best"
            info_path = best_dir / "best_program_info.json"
            best_program_path = best_dir / "best_program.txt"
            if not info_path.exists() or not best_program_path.exists():
                continue
            try:
                info = json.loads(info_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            metrics = info.get("metrics", {}) or {}
            if metrics.get("attack_success_rate") not in (1.0, True):
                continue
            injection_goal = metrics.get("injection_task_goal") or ""
            payload = best_program_path.read_text(encoding="utf-8").strip()
            if injection_goal and payload:
                candidates.append(
                    {"raw_payload": injection_goal, "successful_payload": payload}
                )

        samples = candidates
        if len(candidates) > 3:
            samples = random.Random(refresh_bucket).sample(candidates, 3)
        result = json.dumps(samples, ensure_ascii=False, indent=2)
        self._identified_vuln_cache[cache_key] = result
        return result


def _patched_worker_init(config_dict: dict, evaluation_file: str, parent_env: dict = None) -> None:
    import os as _os

    if parent_env:
        _os.environ.update(parent_env)

    global _worker_config
    global _worker_evaluation_file
    global _worker_evaluator
    global _worker_llm_ensemble
    global _worker_prompt_sampler

    from openevolve.config import (
        Config,
        DatabaseConfig,
        EvaluatorConfig,
        LLMConfig,
        LLMModelConfig,
        PromptConfig,
    )

    models = [LLMModelConfig(**m) for m in config_dict["llm"]["models"]]
    evaluator_models = [
        LLMModelConfig(**m) for m in config_dict["llm"]["evaluator_models"]
    ]
    llm_dict = config_dict["llm"].copy()
    llm_dict["models"] = models
    llm_dict["evaluator_models"] = evaluator_models

    _worker_config = Config(
        llm=LLMConfig(**llm_dict),
        prompt=PromptConfig(**config_dict["prompt"]),
        database=DatabaseConfig(**config_dict["database"]),
        evaluator=EvaluatorConfig(**config_dict["evaluator"]),
        **{
            key: value
            for key, value in config_dict.items()
            if key not in ["llm", "prompt", "database", "evaluator"]
        },
    )
    _worker_evaluation_file = evaluation_file
    _worker_evaluator = None
    _worker_llm_ensemble = None
    _worker_prompt_sampler = None


def _lazy_init_worker_components() -> None:
    global _worker_evaluator
    global _worker_llm_ensemble
    global _worker_prompt_sampler

    if _worker_llm_ensemble is None:
        from openevolve.llm.ensemble import LLMEnsemble

        _worker_llm_ensemble = LLMEnsemble(_worker_config.llm.models)

    if _worker_prompt_sampler is None:
        _worker_prompt_sampler = PatchedPromptSampler(_worker_config.prompt)

    if _worker_evaluator is None:
        from openevolve.evaluator import Evaluator
        from openevolve.llm.ensemble import LLMEnsemble

        evaluator_llm = LLMEnsemble(_worker_config.llm.evaluator_models)
        evaluator_prompt = PatchedPromptSampler(_worker_config.prompt)
        evaluator_prompt.set_templates("evaluator_system_message")
        _worker_evaluator = Evaluator(
            _worker_config.evaluator,
            _worker_evaluation_file,
            evaluator_llm,
            evaluator_prompt,
            database=None,
            suffix=getattr(_worker_config, "file_suffix", ".py"),
        )


def _parse_candidate(parent_code: str, candidate: str, config: Any) -> tuple[str, str, str]:
    if config.diff_based_evolution:
        from openevolve.utils.code_utils import apply_diff, extract_diffs, format_diff_summary

        diff_blocks = extract_diffs(candidate, config.diff_pattern)
        if not diff_blocks:
            raise ValueError("No valid diffs found in response")
        child_code = apply_diff(parent_code, candidate, config.diff_pattern)
        changes_summary = format_diff_summary(
            diff_blocks,
            max_line_len=config.prompt.diff_summary_max_line_len,
            max_lines=config.prompt.diff_summary_max_lines,
        )
        return child_code, changes_summary, ""

    from openevolve.utils.code_utils import parse_full_rewrite

    child_code = parse_full_rewrite(candidate, config.language)
    if not child_code:
        raise ValueError("No valid code found in response")
    return child_code, "Full rewrite", ""


def _score_metrics(metrics: Dict[str, Any]) -> float:
    from openevolve.utils.metrics_utils import safe_numeric_average

    value = metrics.get("combined_score")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return float(safe_numeric_average(metrics))


def _patched_run_iteration_worker(
    iteration: int, db_snapshot: Dict[str, Any], parent_id: str, inspiration_ids: List[str]
):
    from openevolve.database import Program
    from openevolve.process_parallel import SerializableResult
    from openevolve.utils.metrics_utils import safe_numeric_average

    try:
        _lazy_init_worker_components()

        programs = {
            pid: Program.from_dict(prog_dict)
            for pid, prog_dict in db_snapshot["programs"].items()
        }
        parent = programs[parent_id]
        inspirations = [programs[pid] for pid in inspiration_ids if pid in programs]
        parent_artifacts = db_snapshot["artifacts"].get(parent_id)

        parent_island = parent.metadata.get("island", db_snapshot["current_island"])
        island_programs = [
            programs[pid] for pid in db_snapshot["islands"][parent_island] if pid in programs
        ]
        island_programs.sort(
            key=lambda p: p.metrics.get("combined_score", safe_numeric_average(p.metrics)),
            reverse=True,
        )
        programs_for_prompt = island_programs[
            : _worker_config.prompt.num_top_programs
            + _worker_config.prompt.num_diverse_programs
        ]
        best_programs_only = island_programs[: _worker_config.prompt.num_top_programs]

        agentdojo_cfg = _load_runtime_agentdojo_cfg()
        prompt = _worker_prompt_sampler.build_prompt(
            current_program=parent.code,
            parent_program=parent.code,
            program_metrics=parent.metrics,
            previous_programs=[p.to_dict() for p in best_programs_only],
            top_programs=[p.to_dict() for p in programs_for_prompt],
            inspirations=[p.to_dict() for p in inspirations],
            language=_worker_config.language,
            evolution_round=iteration,
            diff_based_evolution=_worker_config.diff_based_evolution,
            program_artifacts=parent_artifacts,
            feature_dimensions=db_snapshot.get("feature_dimensions", []),
            defense_name=agentdojo_cfg.get("defense"),
            parent_program_dict=parent.to_dict(),
        )

        iteration_start = time.time()
        yellow = "\033[93m"
        reset = "\033[0m"
        model_names = [
            getattr(model, "name", str(model))
            for model in getattr(_worker_config.llm, "models", [])
        ]
        reasoning_efforts = [
            getattr(model, "reasoning_effort", "")
            for model in getattr(_worker_config.llm, "models", [])
        ]
        print(yellow + "[mutator_llm] model:\n" + ", ".join(model_names) + reset)
        print(
            yellow
            + "[mutator_llm] reasoning_effort:\n"
            + ", ".join(str(value) for value in reasoning_efforts)
            + reset
        )
        print(yellow + "[mutator_llm] system prompt:\n" + prompt["system"] + reset)
        print(yellow + "[mutator_llm] user prompt:\n" + prompt["user"] + reset)
        try:
            llm_response = asyncio.run(
                _worker_llm_ensemble.generate_with_context(
                    system_message=prompt["system"],
                    messages=[{"role": "user", "content": prompt["user"]}],
                )
            )
        except Exception as exc:
            return SerializableResult(
                error=f"LLM generation failed: {exc}", iteration=iteration
            )
        if llm_response is None:
            return SerializableResult(error="LLM returned None response", iteration=iteration)

        print(yellow + "[mutator_llm] output:\n" + llm_response + reset)
        candidates = _extract_candidates(llm_response) or [llm_response]
        best_child = None
        best_score = float("-inf")
        last_error = None

        for candidate_index, candidate in enumerate(candidates):
            try:
                child_code, changes_summary, child_changes_desc = _parse_candidate(
                    parent.code, candidate, _worker_config
                )
                if len(child_code) > _worker_config.max_code_length:
                    raise ValueError(
                        f"Generated code exceeds maximum length "
                        f"({len(child_code)} > {_worker_config.max_code_length})"
                    )

                child_id = str(uuid.uuid4())
                child_metrics = asyncio.run(
                    _worker_evaluator.evaluate_program(child_code, child_id)
                )
                artifacts = _worker_evaluator.get_pending_artifacts(child_id)
                score = _score_metrics(child_metrics)
                child_program = Program(
                    id=child_id,
                    code=child_code,
                    changes_description=child_changes_desc,
                    language=_worker_config.language,
                    parent_id=parent.id,
                    generation=parent.generation + 1,
                    metrics=child_metrics,
                    iteration_found=iteration,
                    metadata={
                        "changes": changes_summary,
                        "parent_metrics": parent.metrics,
                        "island": parent_island,
                        "candidate_index": candidate_index,
                        "candidate_count": len(candidates),
                    },
                )
                if best_child is None or score > best_score:
                    best_child = (child_program, artifacts)
                    best_score = score
            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Iteration %s candidate %s failed: %s",
                    iteration,
                    candidate_index,
                    exc,
                )

        if best_child is None:
            return SerializableResult(
                error=last_error or "No valid candidates found", iteration=iteration
            )

        child_program, artifacts = best_child
        return SerializableResult(
            child_program_dict=child_program.to_dict(),
            parent_id=parent.id,
            iteration_time=time.time() - iteration_start,
            prompt=prompt,
            llm_response=llm_response,
            artifacts=artifacts,
            iteration=iteration,
            target_island=db_snapshot.get("sampling_island"),
        )
    except Exception as exc:
        logger.exception("Error in worker iteration %s", iteration)
        from openevolve.process_parallel import SerializableResult

        return SerializableResult(error=str(exc), iteration=iteration)


def _make_patched_controller(base_controller):
    class PatchedProcessParallelController(base_controller):
        def start(self) -> None:
            config_dict = self._serialize_config(self.config)
            current_env = dict(os.environ)
            executor_kwargs = {
                "max_workers": self.num_workers,
                "initializer": _patched_worker_init,
                "initargs": (config_dict, self.evaluation_file, current_env),
            }
            if sys.version_info >= (3, 11):
                executor_kwargs["max_tasks_per_child"] = self.config.max_tasks_per_child
            elif self.config.max_tasks_per_child is not None:
                logger.warning(
                    "max_tasks_per_child is only supported in Python 3.11+. "
                    "Ignoring max_tasks_per_child and using spawn start method."
                )
                executor_kwargs["mp_context"] = mp.get_context("spawn")

            self.executor = ProcessPoolExecutor(**executor_kwargs)
            logger.info("Started patched OpenEvolve process pool")

        def _submit_iteration(self, iteration: int, island_id: Optional[int] = None):
            try:
                target_island = island_id if island_id is not None else self.database.current_island
                parent, inspirations = self.database.sample_from_island(
                    island_id=target_island,
                    num_inspirations=self.config.prompt.num_top_programs,
                )
                db_snapshot = self._create_database_snapshot()
                db_snapshot["sampling_island"] = target_island
                return self.executor.submit(
                    _patched_run_iteration_worker,
                    iteration,
                    db_snapshot,
                    parent.id,
                    [insp.id for insp in inspirations],
                )
            except Exception as exc:
                logger.error("Error submitting iteration %s: %s", iteration, exc)
                return None

    return PatchedProcessParallelController


def apply() -> None:
    """Install all runtime patches into the imported OpenEvolve package."""

    import openevolve.controller as controller_module
    import openevolve.process_parallel as process_parallel_module
    import openevolve.prompt.sampler as sampler_module

    global _UPSTREAM_PROMPT_SAMPLER
    if sampler_module.PromptSampler is not PatchedPromptSampler:
        _UPSTREAM_PROMPT_SAMPLER = sampler_module.PromptSampler

    base_controller = process_parallel_module.ProcessParallelController
    patched_controller = _make_patched_controller(base_controller)

    sampler_module.PromptSampler = PatchedPromptSampler
    controller_module.PromptSampler = PatchedPromptSampler
    process_parallel_module._worker_init = _patched_worker_init
    process_parallel_module._run_iteration_worker = _patched_run_iteration_worker
    process_parallel_module.ProcessParallelController = patched_controller
    controller_module.ProcessParallelController = patched_controller
