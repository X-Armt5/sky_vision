# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/ros_utils.py
"""
ros_utils.py
Shared ROS 2 topic discovery for PX4 autopilot, camera, and sensor topics.
Used by: offboard_control_node, vision_tracker_node,
         video_streamer_node, qgc_video_streamer_node, target_calculator_node.
"""
import re


def discover_px4_topics(node_obj) -> dict:
    """
    Dynamically scans the ROS 2 environment for PX4, camera, and lidar topics.
    Returns a mapping of abstract labels to actual topic names.
    """
    topic_list = node_obj.get_topic_names_and_types()
    topics = {}

    for topic_name, topic_types in topic_list:
        base_name  = topic_name.split('/')[-1]
        base_clean = re.sub(r'_v\d+$', '', base_name)

        # Inbound (commands to PX4)
        if 'px4_msgs/msg/OffboardControlMode' in topic_types and base_clean == 'offboard_control_mode' and '/in/' in topic_name:
            topics['offboard'] = topic_name
        elif 'px4_msgs/msg/TrajectorySetpoint' in topic_types and base_clean == 'trajectory_setpoint' and '/in/' in topic_name:
            topics['trajectory'] = topic_name
        elif 'px4_msgs/msg/VehicleCommand' in topic_types and base_clean == 'vehicle_command' and '/in/' in topic_name:
            topics['command'] = topic_name

        # Outbound (telemetry from PX4)
        elif 'px4_msgs/msg/VehicleLocalPosition' in topic_types and base_clean == 'vehicle_local_position' and '/out/' in topic_name:
            topics['local_pos'] = topic_name
        elif 'px4_msgs/msg/VehicleGlobalPosition' in topic_types and base_clean == 'vehicle_global_position' and '/out/' in topic_name:
            topics['global_pos'] = topic_name
        elif 'px4_msgs/msg/HomePosition' in topic_types and base_clean == 'home_position' and '/out/' in topic_name:
            topics['home'] = topic_name
        elif 'px4_msgs/msg/VehicleAttitude' in topic_types and base_clean == 'vehicle_attitude' and '/out/' in topic_name:
            topics['attitude'] = topic_name
        elif 'px4_msgs/msg/VehicleStatus' in topic_types and base_clean == 'vehicle_status' and '/out/' in topic_name:
            topics['status'] = topic_name

        # Sensors
        elif 'sensor_msgs/msg/Image' in topic_types and '/sensor/' in topic_name and 'image' in topic_name.lower():
            topics['camera'] = topic_name
        elif 'sensor_msgs/msg/LaserScan' in topic_types and '/sensor/' in topic_name and 'scan' in topic_name.lower():
            topics['lidar'] = topic_name

    if topics:
        node_obj.get_logger().info("--- Discovered Topics ---")
        for key, val in topics.items():
            node_obj.get_logger().info(f"  [{key.upper()}]: {val}")
        node_obj.get_logger().info("-------------------------")

    return topics
