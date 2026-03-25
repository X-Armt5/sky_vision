# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/detection_utils.py
"""
detection_utils.py
Bounding box parsing, center extraction, health label mapping,
detection payload building, and duplicate candidate preparation.
Used by: vision_tracker_node, database_logger_node.
"""
import math


def extract_bbox(box) -> dict:
    """Extracts bbox pixel coords and center from a YOLO box object."""
    x1, y1, x2, y2 = map(int, box.xyxy[0])
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    return {'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'cx': cx, 'cy': cy,
            'width_px': x2 - x1, 'height_px': y2 - y1}


def map_health_label(class_name: str,
                     healthy_labels: list,
                     unhealthy_labels: list,
                     default: str = 'unknown') -> str:
    """Maps a raw class name string to a canonical health status."""
    name = class_name.lower()
    if any(label in name for label in healthy_labels):
        return 'healthy'
    if any(label in name for label in unhealthy_labels):
        return 'unhealthy'
    return default


def build_detection_payload(class_id: int,
                             class_name: str,
                             health_status: str,
                             confidence: float,
                             bbox: dict,
                             image_w: int,
                             image_h: int,
                             latitude: float,
                             longitude: float,
                             altitude_m: float,
                             orchard_lps: dict,
                             plant_relative: dict,
                             distance_from_lens_m: float,
                             estimated_size_mm: float,
                             orchard_id: str = '',
                             row_id: str = '',
                             plant_id: str = '',
                             object_id: str = '',
                             view_mode: str = 'unknown',
                             task_type: str = '') -> dict:
    """Builds a complete generic detection payload dict for publishing."""
    return {
        'class_id':              class_id,
        'class_name':            class_name,
        'health_status':         health_status,
        'confidence':            round(float(confidence), 4),
        'bbox_x1_px':            bbox['x1'],
        'bbox_y1_px':            bbox['y1'],
        'bbox_x2_px':            bbox['x2'],
        'bbox_y2_px':            bbox['y2'],
        'image_width_px':        image_w,
        'image_height_px':       image_h,
        'latitude':              latitude,
        'longitude':             longitude,
        'altitude_m':            altitude_m,
        'orchard_lps_x_m':       orchard_lps.get('x', 0.0),
        'orchard_lps_y_m':       orchard_lps.get('y', 0.0),
        'orchard_lps_z_m':       orchard_lps.get('z', 0.0),
        'plant_relative_x_m':    plant_relative.get('x', 0.0),
        'plant_relative_y_m':    plant_relative.get('y', 0.0),
        'plant_relative_z_m':    plant_relative.get('z', 0.0),
        'distance_from_lens_m':  distance_from_lens_m,
        'estimated_size_mm':     estimated_size_mm,
        'orchard_id':            orchard_id,
        'row_id':                row_id,
        'plant_id':              plant_id,
        'object_id':             object_id,
        'view_mode':             view_mode,
        'task_type':             task_type,
    }
