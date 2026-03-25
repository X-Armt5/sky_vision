# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/size_estimation_utils.py
"""
size_estimation_utils.py
Fruit / object size estimation from bounding box pixels and camera geometry.
Method: pinhole camera model.

  estimated_diameter_mm = (bbox_dimension_px * distance_mm) / focal_length_px

Used by: vision_tracker_node.
Tools required: calibrated focal_length_px from camera intrinsics.
"""


def estimate_size_mm(bbox_width_px: float,
                     bbox_height_px: float,
                     distance_from_lens_m: float,
                     focal_length_px: float,
                     preferred_axis: str = 'min') -> tuple:
    """
    Estimates the physical size of a detected object using the pinhole model.

    Args:
        bbox_width_px:       Bounding box width in pixels.
        bbox_height_px:      Bounding box height in pixels.
        distance_from_lens_m: Distance from camera lens to object in meters.
        focal_length_px:     Camera focal length in pixels (from intrinsics).
        preferred_axis:      'min', 'max', or 'avg' dimension used for diameter.

    Returns:
        (estimated_size_mm, size_confidence, size_method)
    """
    if focal_length_px <= 0 or distance_from_lens_m <= 0:
        return 0.0, 0.0, 'invalid_inputs'

    distance_mm = distance_from_lens_m * 1000.0

    width_mm  = (bbox_width_px  * distance_mm) / focal_length_px
    height_mm = (bbox_height_px * distance_mm) / focal_length_px

    if preferred_axis == 'min':
        estimated = min(width_mm, height_mm)
    elif preferred_axis == 'max':
        estimated = max(width_mm, height_mm)
    else:
        estimated = (width_mm + height_mm) / 2.0

    # Confidence decreases with distance (basic heuristic)
    if distance_from_lens_m < 1.5:
        confidence = 0.9
    elif distance_from_lens_m < 3.0:
        confidence = 0.7
    elif distance_from_lens_m < 6.0:
        confidence = 0.5
    else:
        confidence = 0.3

    return round(estimated, 2), confidence, 'pinhole_bbox'


def size_is_reliable(confidence: float, min_confidence: float = 0.5) -> bool:
    """Returns True if size estimate meets minimum confidence threshold."""
    return confidence >= min_confidence
