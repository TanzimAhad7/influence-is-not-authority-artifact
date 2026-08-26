"""
A15b-0C AgentWatcher-only runtime registry.

The public registry eagerly imports unrelated defenses. This runtime worktree
exposes only the frozen AgentWatcher arm. AgentWatcher's algorithmic
implementation is imported unchanged.
"""

from .agentwatcher import agentwatcher, agentwatcher_batch

DEFENSES = {"agentwatcher": agentwatcher}
DEFENSES_BATCH = {"agentwatcher": agentwatcher_batch}


class DefenseWrapper:
    def __init__(self, defense_func):
        self.defense_func = defense_func

    def execute(self, target_inst, context, **kwargs):
        return self.defense_func(
            target_inst=target_inst,
            context=context,
            **kwargs,
        )


def get_defense(defense_name: str):
    name = defense_name.lower()
    if name not in DEFENSES:
        raise ValueError(
            "A15b reconstruction runtime exposes only AgentWatcher; "
            f"requested={defense_name!r}"
        )
    return DefenseWrapper(DEFENSES[name])
