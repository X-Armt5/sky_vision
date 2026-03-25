# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/pick_utils.py
"""
pick_utils.py
Generic manipulator command abstraction, pick state helpers,
and no-tool fallback behavior.
Used by: picking_manager_node.
"""


def is_tool_enabled(config: dict) -> bool:
    """Returns True only if the physical manipulator is enabled in config."""
    return config.get('manipulator', {}).get('enabled', False)


def get_pick_outcome_no_tool(config: dict) -> str:
    """Returns the configured outcome label when no tool is attached."""
    return config.get('pick_execution', {}).get('mark_outcome_without_tool', 'tool_unavailable')


def allow_approach_without_tool(config: dict) -> bool:
    return config.get('pick_execution', {}).get('allow_approach_without_tool', True)


def get_grasp_timeout(config: dict) -> float:
    return float(config.get('manipulator', {}).get('grasp_timeout_s', 5.0))


def get_post_pick_hold(config: dict) -> float:
    return float(config.get('manipulator', {}).get('post_pick_hold_s', 2.0))


def get_retreat_distance(config: dict) -> float:
    return float(config.get('pick_execution', {}).get('retreat_distance_m', 1.0))


def build_pick_state_machine(tool_enabled: bool) -> list:
    """
    Returns the ordered list of pick states based on tool availability.
    States without a tool stop at ALIGNED and skip GRASP and VERIFY.
    """
    if tool_enabled:
        return ['APPROACH', 'ALIGN', 'GRASP', 'VERIFY', 'RETREAT', 'DONE']
    else:
        return ['APPROACH', 'ALIGN', 'NO_TOOL_HOLD', 'RETREAT', 'DONE']


class PickStateMachine:
    """
    Simple linear pick state machine.
    Drives the picking_manager_node through approach, grasp, and retreat.
    When tool is disabled, transitions through a no-tool path and
    records outcome as 'tool_unavailable' instead of 'picked'.
    """

    def __init__(self, config: dict):
        self.config       = config
        self.tool_enabled = is_tool_enabled(config)
        self.states       = build_pick_state_machine(self.tool_enabled)
        self.state_index  = 0
        self.outcome      = 'pending'

    @property
    def current_state(self) -> str:
        if self.state_index < len(self.states):
            return self.states[self.state_index]
        return 'DONE'

    def advance(self) -> str:
        if self.state_index < len(self.states) - 1:
            self.state_index += 1
        return self.current_state

    def mark_success(self):
        self.outcome = 'picked'
        self.state_index = len(self.states) - 1

    def mark_missed(self):
        self.outcome = 'missed'
        self.state_index = len(self.states) - 1

    def mark_aborted(self, reason: str = ''):
        self.outcome = 'aborted'
        self.state_index = len(self.states) - 1

    def mark_no_tool(self):
        self.outcome = get_pick_outcome_no_tool(self.config)
        self.state_index = len(self.states) - 1

    def is_done(self) -> bool:
        return self.current_state == 'DONE'
