# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/entity_utils.py
"""
entity_utils.py
Generic ID and name builders for orchards, rows, plants, objects, tasks, and poses.
Used by: vision_tracker_node, database_logger_node, picking_manager_node.
"""


def build_plant_id(orchard_id: str, row_id: str, plant_index: int) -> str:
    return f"{orchard_id}_{row_id}_plant_{plant_index:02d}"


def build_plant_name(crop_type: str, row_id: str, plant_index: int) -> str:
    return f"{crop_type}_{row_id}_plant_{plant_index:02d}"


def build_object_id(plant_id: str, object_index: int) -> str:
    return f"{plant_id}_object_{object_index:03d}"


def build_object_name(object_label: str, row_id: str,
                      plant_index: int, object_index: int) -> str:
    return f"{object_label}_{row_id}_plant_{plant_index:02d}_object_{object_index:03d}"


def build_task_id(object_id: str, task_type: str, timestamp_s: float) -> str:
    ts = str(int(timestamp_s))
    return f"task_{object_id}_{task_type}_{ts}"
