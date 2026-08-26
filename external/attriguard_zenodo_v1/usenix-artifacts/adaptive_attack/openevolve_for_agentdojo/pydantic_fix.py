# pydantic_fix.py
from agentdojo.types import FunctionCall  # noqa: F401 imported only to trigger import side effects
from agentdojo.benchmark import TaskResults

TaskResults.model_rebuild()
