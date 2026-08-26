"""
Runtime-only patches that avoid modifying installed AgentDojo source files.
"""


def apply_runtime_workarounds():
    """
    Apply safe runtime patches.

    - Slack UserTask6.utility: if Bob's inbox is missing, return False instead of raising KeyError.
    """
    try:
        from agentdojo.default_suites.v1.slack import user_tasks as slack_user_tasks
    except Exception:
        return

    original_utility = slack_user_tasks.UserTask6.utility

    def safe_utility(self, model_output, pre_environment, post_environment, strict: bool = True):
        try:
            return original_utility(self, model_output, pre_environment, post_environment, strict=strict)
        except KeyError as err:
            if err.args and err.args[0] == "Bob":
                return False
            raise

    slack_user_tasks.UserTask6.utility = safe_utility
