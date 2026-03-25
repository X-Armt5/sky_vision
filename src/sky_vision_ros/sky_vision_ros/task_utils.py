# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/task_utils.py
"""
task_utils.py
Lifecycle routing, terminal-state checking, task creation rules,
and health-based task dispatch logic.
Used by: database_logger_node, picking_manager_node.
"""


def should_skip_object(object_status: str, terminal_statuses: list) -> bool:
    """Returns True if the object is in a terminal lifecycle state."""
    return object_status in terminal_statuses


def resolve_next_task_type(health_status: str,
                            current_object_status: str,
                            rules: dict) -> str:
    """
    Resolves the best next task type based on health and automation rules.
    Returns a task_type string or empty string if no task should be created.
    """
    if current_object_status in rules.get('skip_statuses', []):
        return ''

    if health_status == 'unhealthy':
        if rules.get('create_pick_task_for_unhealthy', False):
            return 'object_pick_approach_side'

    if health_status == 'healthy':
        if rules.get('create_inspect_task_for_healthy', False):
            return 'object_inspect_top'

    return ''


def get_terminal_statuses(config: dict) -> list:
    return config.get('object_status', {}).get('terminal_statuses', [])


def is_terminal(status: str, terminal_statuses: list) -> bool:
    return status in terminal_statuses


def pick_outcome_from_config(config: dict, outcome_key: str) -> str:
    return config.get('pick_outcomes', {}).get(outcome_key, outcome_key)
