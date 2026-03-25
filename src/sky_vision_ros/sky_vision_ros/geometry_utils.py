# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/geometry_utils.py
"""
geometry_utils.py
Shared coordinate transforms, view geometry, distance calculations,
and action-pose offset logic.
Used by: offboard_control_node, vision_tracker_node, picking_manager_node.
"""
import math


# ----------------------------------------------------------
# GPS <-> Local NED Conversions
# ----------------------------------------------------------

def gps_to_ned(target_lat: float, target_lon: float,
               home_lat: float, home_lon: float) -> tuple:
    """Converts GPS to local NED (x_north, y_east) in meters relative to home."""
    R = 6378137.0
    dlat = math.radians(target_lat - home_lat)
    dlon = math.radians(target_lon - home_lon)
    x_north = dlat * R
    y_east  = dlon * R * math.cos(math.radians(home_lat))
    return x_north, y_east


def ned_to_gps(target_x: float, target_y: float,
               home_lat: float, home_lon: float) -> tuple:
    """Converts local NED (x_north, y_east) back to GPS."""
    R = 6378137.0
    lat_rad = math.radians(home_lat) + (target_x / R)
    lon_rad = math.radians(home_lon) + (target_y / (R * math.cos(math.radians(home_lat))))
    return math.degrees(lat_rad), math.degrees(lon_rad)


def haversine_distance(lat1: float, lon1: float,
                       lat2: float, lon2: float) -> float:
    """Calculates distance in meters between two GPS coordinates."""
    R = 6378137.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def euclidean_distance_3d(x1, y1, z1, x2, y2, z2) -> float:
    """Euclidean distance between two 3D points."""
    return math.sqrt((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)



# ----------------------------------------------------------
# Gazebo world coordinates > PX4 NED local frame Conversions
# ----------------------------------------------------------

def gazebo_to_px4_ned(gazebo_x_east: float,
                       gazebo_y_north: float,
                       takeoff_height_m: float,
                       z_offset_m: float = 0.0) -> dict:
    """
    Converts Gazebo world coordinates to PX4 NED local frame.

    Gazebo frame:  x = East,  y = North,  z = Up
    PX4 NED frame: x = North, y = East,   z = Down (negative = up)

    Args:
        gazebo_x_east:    Gazebo x coordinate (East direction) in meters.
        gazebo_y_north:   Gazebo y coordinate (North direction) in meters.
        takeoff_height_m: Mission flight altitude in PX4 z (negative = above ground).
        z_offset_m:       Additional vertical offset from YAML waypoint definition.

    Returns:
        dict with keys x (North), y (East), z (Down/negative).
    """
    return {
        'x': gazebo_y_north,
        'y': gazebo_x_east,
        'z': takeoff_height_m + z_offset_m,
    }


def parse_raw_waypoint(raw_waypoint,
                        takeoff_height_m: float,
                        index: int = 0) -> dict:
    """
    Parses a raw YAML waypoint (string 'x,y,z' or list [x,y,z])
    and converts Gazebo frame to PX4 NED frame.

    Returns dict with keys x, y, z or raises ValueError on bad input.
    """
    if isinstance(raw_waypoint, str):
        parts = [p.strip() for p in raw_waypoint.split(',')]
    elif isinstance(raw_waypoint, (list, tuple)):
        parts = [str(p).strip() for p in raw_waypoint]
    else:
        raise ValueError(
            f"Waypoint {index}: unsupported format '{raw_waypoint}'.")

    if len(parts) != 3:
        raise ValueError(
            f"Waypoint {index}: expected 'x,y,z', got '{raw_waypoint}'.")

    try:
        gazebo_x_east  = float(parts[0])
        gazebo_y_north = float(parts[1])
        z_offset       = float(parts[2])
    except ValueError:
        raise ValueError(
            f"Waypoint {index}: non-numeric values in '{raw_waypoint}'.")

    return gazebo_to_px4_ned(gazebo_x_east, gazebo_y_north,
                              takeoff_height_m, z_offset)


# ----------------------------------------------------------
# Euler / Quaternion
# ----------------------------------------------------------

def get_euler_from_quaternion(q0, q1, q2, q3) -> tuple:
    """Converts quaternion to (yaw, pitch, roll) in radians."""
    yaw   = math.atan2(2.0*(q0*q3 + q1*q2), 1.0 - 2.0*(q2**2 + q3**2))
    sinp  = 2.0*(q0*q2 - q3*q1)
    pitch = math.copysign(math.pi/2, sinp) if abs(sinp) >= 1 else math.asin(sinp)
    roll  = math.atan2(2.0*(q0*q1 + q2*q3), 1.0 - 2.0*(q1**2 + q2**2))
    return yaw, pitch, roll


# ----------------------------------------------------------
# Camera / View Geometry
# ----------------------------------------------------------

def calculate_ground_intersection(altitude: float, total_pitch: float) -> float:
    """
    Horizontal ground distance from camera nadir to target.
    Guards against both zero pitch (tan=0 → division by zero)
    and near-90° pitch (straight down → zero horizontal offset).
    """
    # Clamp near-zero pitch to a minimum safe value (1 degree)
    MIN_PITCH_RAD = math.radians(1.0)

    if math.isclose(total_pitch, math.pi / 2, abs_tol=1e-5):
        return 0.0

    if abs(total_pitch) < MIN_PITCH_RAD:
        total_pitch = math.copysign(MIN_PITCH_RAD, total_pitch) if total_pitch != 0.0 else MIN_PITCH_RAD

    tan_val = math.tan(total_pitch)
    if math.isclose(tan_val, 0.0, abs_tol=1e-9):
        return altitude / 1e-9  # effectively infinite distance, capped below

    result = altitude / tan_val

    # Safety cap: ground distance should not exceed a physically reasonable range
    MAX_GROUND_DIST_M = 500.0
    return max(-MAX_GROUND_DIST_M, min(MAX_GROUND_DIST_M, result))

def calculate_3d_distance(altitude: float, total_pitch: float) -> float:
    """True Euclidean distance from camera lens to target."""
    if total_pitch <= 0.0:
        return float('inf')
    return altitude / math.sin(total_pitch)


def calculate_total_camera_pitch(mount_pitch: float,
                                  drone_pitch: float,
                                  gimbal_pitch: float = 0.0) -> float:
    """Total downward camera pitch angle."""
    return mount_pitch - drone_pitch + gimbal_pitch


# ----------------------------------------------------------
# Action Pose Offsets
# ----------------------------------------------------------

def compute_action_pose(target_x: float, target_y: float, target_z: float,
                        drone_yaw: float,
                        standoff_m: float,
                        vertical_offset_m: float,
                        access_mode: str) -> dict:
    """
    Computes a safe drone pose from which to inspect or pick a target.
    access_mode: 'top' positions drone above target,
                 'side' positions drone horizontally offset.
    Returns dict with keys x, y, z, yaw.
    """
    if access_mode == 'top':
        pose_x = target_x
        pose_y = target_y
        pose_z = target_z - standoff_m - vertical_offset_m
        pose_yaw = drone_yaw
    else:
        pose_x   = target_x - standoff_m * math.cos(drone_yaw)
        pose_y   = target_y - standoff_m * math.sin(drone_yaw)
        pose_z   = target_z + vertical_offset_m
        pose_yaw = math.atan2(target_y - pose_y, target_x - pose_x)

    return {'x': pose_x, 'y': pose_y, 'z': pose_z, 'yaw': pose_yaw}
