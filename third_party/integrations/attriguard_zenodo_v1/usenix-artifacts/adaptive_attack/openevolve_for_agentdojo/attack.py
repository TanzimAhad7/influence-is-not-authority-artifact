# attack_evolve.py
import json

from agentdojo.attacks import BaseAttack
from agentdojo.attacks.attack_registry import register_attack
from agentdojo.base_tasks import BaseInjectionTask, BaseUserTask

# Store the current trigger in a module-level global.
CURRENT_INJECTION = ""

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

class EvolveAttack(BaseAttack):
    name = "evolve"

    def attack(
        self,
        user_task: BaseUserTask,
        injection_task: BaseInjectionTask,
    ) -> dict[str, str]:
        global CURRENT_INJECTION

        raw_injection = CURRENT_INJECTION or ""
        injection_text = _escape_for_yaml_double_quoted(raw_injection)
        injections: dict[str, str] = {}

        for inj in self.get_injection_candidates(user_task):
            injections[inj] = f"{injection_text}"
            print(f"[EvolveAttack] Injection for {inj}: {injections[inj]}")

        return injections

register_attack(EvolveAttack)
