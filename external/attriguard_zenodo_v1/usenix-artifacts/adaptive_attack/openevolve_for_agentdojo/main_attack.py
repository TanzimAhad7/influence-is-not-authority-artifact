import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
import yaml
from agentdojo.attacks import BaseAttack
from agentdojo.attacks.attack_registry import register_attack
from agentdojo.base_tasks import BaseInjectionTask, BaseUserTask

def _resolve_config_path(config_path: str | Path | None = None) -> Path:
    if config_path is None:
        env_path = os.environ.get("OPENEvolve_CONFIG_PATH")
        if env_path:
            config_path = env_path
            # print(f"load config from OPENEvolve_CONFIG_PATH: {env_path}")
        else:
            config_path = "config.yaml"
    if isinstance(config_path, str):
        config_path = Path(config_path)
    return config_path


def load_agentdojo_cfg(config_path: str | Path | None = None) -> dict:
    """
    Read evaluator.extra_kwargs.agentdojo_cfg from OpenEvolve's config.yaml.
    Return {} if the file does not exist or the field is missing.
    """
    config_path = _resolve_config_path(config_path)

    if not config_path.exists():
        return {}

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    evaluator_cfg = cfg.get("evaluator", {}) or {}
    extra_kwargs = evaluator_cfg.get("extra_kwargs", {}) or {}
    agentdojo_cfg = extra_kwargs.get("agentdojo_cfg", {}) or {}

    return agentdojo_cfg

def _safe_segment(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    safe = value.strip().replace("/", "_").replace("\\", "_")
    return safe or fallback

def _escape_for_yaml_double_quoted(s: str) -> str:
    """
    Convert any string into a safe form for YAML double-quoted values:
    - internal " becomes \"
    - newlines become \n
    - other special characters are escaped in JSON style
    The returned value omits the outer quotes so the YAML template can wrap it.
    """
    if not s:
        return ""
    try:
        dumped = json.dumps(s, ensure_ascii=False)
        # json.dumps returns a value like `"xxx"`; strip the outer quotes.
        return dumped[1:-1]
    except Exception:
        # Fallback: manually apply the minimum required escaping.
        return (
            s.replace("\\", "\\\\")
             .replace('"', '\\"')
             .replace("\n", "\\n")
        )

def normalize_task_id(task_id: str) -> str:
    # Normalize to lowercase.
    tid = task_id.lower()
    # Fix "usertask0" -> "user_task_0".
    tid = tid.replace("usertask", "user_task_")
    # Fix "injectiontask4" -> "injection_task_4".
    tid = tid.replace("injectiontask", "injection_task_")

    return tid

def get_task_id(task) -> str:
    # Wrap access to tolerate field name differences across AgentDojo versions.
    for attr in ("TASK_ID", "task_id", "id", "name"):
        if hasattr(task, attr):
            return str(getattr(task, attr))
    # Fall back if no known task id attribute exists.
    return task.__class__.__name__


def run_openevolve_for_pair(
    user_task: BaseUserTask,
    injection_task: BaseInjectionTask,
    suite_name: str,
) -> str:
    """
    Run the OpenEvolve CLI for one (user_task, injection_task) pair and return
    the final generated payload, such as the text from best_program.
    """

    user_id = get_task_id(user_task)
    inj_id = get_task_id(injection_task)
    user_id = normalize_task_id(user_id)
    inj_id = normalize_task_id(inj_id)

    agentdojo_cfg = load_agentdojo_cfg()
    model = _safe_segment(agentdojo_cfg.get("model"), "model")
    model_id = _safe_segment(agentdojo_cfg.get("model_id"), "model_id")
    defense = _safe_segment(agentdojo_cfg.get("defense"), "defense")

    # Output directory: openevolve_output/{model}__{model_id}__{defense}/{suite_name}/{user}&{inj}
    output_root = Path("openevolve_output") / f"{model}-{model_id}-{defense}"
    output_dir = output_root / suite_name / f"{user_id}&{inj_id}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # These paths follow the current project layout.
    if "initial_trigger" not in agentdojo_cfg:
        raise ValueError("Missing required agentdojo_cfg.initial_trigger in config.yaml")
    initial_trigger = agentdojo_cfg["initial_trigger"]
    evaluator_file = "agentdojo_evaluator.py"
    config_path = str(_resolve_config_path())

    openevolve_cmd = os.environ.get("OPENEvolve_CMD")
    if openevolve_cmd:
        cmd = shlex.split(openevolve_cmd)
    else:
        cmd = [sys.executable, "-m", "openevolve_runner"]
    cmd.extend([
        initial_trigger,
        evaluator_file,
        "--output", str(output_dir),
        "--config", config_path,
        "--agentdojo-suite", suite_name,
        # "--iterations", "50",
        # "--agentdojo-suite", "slack",
        # "--agentdojo-benchmark-version", "v1.2.1",
        # "--agentdojo-logdir", "agentdojo_log",
        # "--agentdojo-attack", "evolve",
        "--agentdojo-user-task", user_id,
        "--agentdojo-injection-task", inj_id,
        # "--agentdojo-tool-delimiter", "tool",
        # "--agentdojo-defense", "none",   # Or omit/pass null depending on CLI parsing.
    ])
    target_score = agentdojo_cfg.get("target_score")
    if target_score is None:
        raise ValueError("Missing required agentdojo_cfg.target_score in config.yaml")
    cmd.extend(["--target-score", str(target_score)])

    # If the CLI uses argparse, make sure defense handles "none"/"null" by default.
    env = os.environ.copy()
    env["OPENEvolve_OUTPUT_ROOT"] = str(output_root.resolve())
    env["OPENEvolve_SUITE"] = suite_name
    subprocess.run(cmd, check=True, env=env)

    # Read back the best trigger/payload.
    # OpenEvolve usually writes {output_dir}/best/best_program.txt or similar.
    best_dir = output_dir / "best"
    # Keep the extension aligned with file_suffix in the controller.
    best_file = best_dir / "best_program.txt"
    if not best_file.exists():
        # This may be .py or .md depending on the actual configuration.
        best_file = best_dir / "best_program.py"

    with open(best_file, "r", encoding="utf-8") as f:
        payload = f.read().strip()
    
    payload = _escape_for_yaml_double_quoted(payload)

    return payload


@register_attack
class OpenEvolveAttack(BaseAttack):
    name = "main_evolve"   # Corresponds to attack: "evolve" in agentdojo_cfg.

    def attack(
        self,
        user_task: BaseUserTask,
        injection_task: BaseInjectionTask,
    ) -> dict[str, str]:
        """
        This is the actual AgentDojo attack interface.

        Approach:
        1. Run OpenEvolve once for the current user_task + injection_task pair.
        2. Get the evolved payload optimized for this task pair.
        3. Insert the payload into all injection candidate positions and return the mapping.
        """
        # Step 1: run OpenEvolve to produce the best payload for this task pair.
        payload = run_openevolve_for_pair(user_task, injection_task, self.task_suite.name)

        # Step 2: generate the injection point -> payload mapping.
        injections: dict[str, str] = {}
        for inj in self.get_injection_candidates(user_task):
            # In the current design, the payload is the complete injection text.
            injections[inj] = payload

        return injections
