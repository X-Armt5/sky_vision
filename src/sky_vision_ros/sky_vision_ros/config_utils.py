# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/config_utils.py
"""
config_utils.py
YAML loading, selector resolution, and mission/orchard/row/task lookups.
Used by: offboard_control_node, database_logger_node, picking_manager_node.
"""
import yaml
import os
from sky_vision_ros.geometry_utils import gazebo_to_px4_ned


def load_yaml(yaml_path: str) -> dict:
    """Loads a YAML file and returns the ros__parameters dict."""
    path = os.path.expanduser(yaml_path)
    with open(path, 'r') as f:
        raw = yaml.safe_load(f)
    return raw.get('/**', {}).get('ros__parameters', {})


def get_mission(config: dict, mission_id: str) -> dict:
    """Returns mission config dict for the given mission_id."""
    return config.get('missions', {}).get(mission_id, {})


def get_orchard(config: dict, orchard_id: str) -> dict:
    """Returns orchard config dict for the given orchard_id."""
    return config.get('orchards', {}).get(orchard_id, {})


def get_row(config: dict, orchard_id: str, row_id: str) -> dict:
    """Returns row config dict for the given orchard and row."""
    orchard = get_orchard(config, orchard_id)
    return orchard.get('rows', {}).get(row_id, {})


def get_scan_profile(config: dict, profile_id: str) -> dict:
    """Returns a scan profile dict by its ID."""
    return config.get('scan_profiles', {}).get(profile_id, {})


def get_task_default(config: dict, task_type: str) -> dict:
    """Returns task default config for the given task type."""
    return config.get('task_defaults', {}).get(task_type, {})


def get_action_pose_default(config: dict, pose_key: str) -> dict:
    """Returns action pose defaults for a given key."""
    return config.get('object_action_defaults', {}).get(pose_key, {})




def get_takeoff_height(config: dict) -> float:
    """
    Single source of truth for mission takeoff height.
    Always read from flight_defaults in system_config.yaml.
    """
    return float(config.get('flight_defaults', {})
                          .get('mission_takeoff_height_m', -5.2))

def resolve_mission_waypoints(config: dict, mission_id: str) -> list:
    """
    Resolves a flat list of PX4 NED waypoints from a mission definition.
    Takeoff height is always read from config — never hardcoded or passed in.
    Applies Gazebo→PX4 NED frame conversion on every plant position.
    """
    takeoff_height_m = get_takeoff_height(config)   # <-- single source

    mission  = get_mission(config, mission_id)
    orchard  = get_orchard(config, mission.get('orchard_id', ''))
    defaults = orchard.get('defaults', {})
    rows_cfg = orchard.get('rows', {})
    z_offset = float(defaults.get('plant_center_z_m', 0.0))

    waypoints = []
    for row_id in mission.get('row_ids', []):
        row   = rows_cfg.get(row_id, {})
        gaz_x = float(row.get('x_m', 0.0))
        for gaz_y in row.get('plant_y_values_m', []):
            wp = gazebo_to_px4_ned(gaz_x, float(gaz_y),
                                   takeoff_height_m, z_offset)
            waypoints.append(wp)
    return waypoints

def is_picking_enabled(config: dict) -> bool:
    """Returns True if the manipulator is enabled in config."""
    return config.get('manipulator', {}).get('enabled', False)


def get_terminal_statuses(config: dict) -> list:
    """Returns the list of terminal lifecycle statuses."""
    return config.get('object_status', {}).get('terminal_statuses', [])
