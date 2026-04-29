#!/usr/bin/env python3
# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/database_logger_node.py
"""
database_logger_node.py
Responsibility: Persistence only.
  - Receives detection JSON from /sky_vision/detected_targets
  - Finds or creates tracked_object identity
  - Inserts detection_event every time
  - Inserts size_measurement if reliable
  - Upserts action_poses
  - Routes to task creation via task_utils
  - Skips terminal-status objects
"""
import rclpy, json
from rclpy.node import Node
from std_msgs.msg import String

from sky_vision_ros.config_utils  import load_yaml, get_terminal_statuses
from sky_vision_ros.db_utils      import (init_schema, find_duplicate_object_id,
                                           upsert_tracked_object, insert_detection_event,
                                           insert_size_measurement, insert_task_event,
                                           update_object_status, get_object_status,
                                           upsert_action_poses)
from sky_vision_ros.entity_utils  import build_object_id
from sky_vision_ros.task_utils    import should_skip_object, resolve_next_task_type
from sky_vision_ros.size_estimation_utils import size_is_reliable
from sky_vision_ros.geometry_utils import compute_action_pose


class DatabaseLoggerNode(Node):

    def __init__(self):
        super().__init__('database_logger_node')

        self.declare_parameter('config_path', '~/sky_vision/config/system_config.yaml')
        cfg_path    = self.get_parameter('config_path').value
        self.config = load_yaml(cfg_path)

        db_cfg       = self.config.get('database', {})
        self.db_path = db_cfg.get('db_path', '~/sky_vision/data/mission_data.db')
        dup_policy   = db_cfg.get('unique_entity_policy', {})
        self.dup_radius = float(dup_policy.get('max_orchard_lps_distance_m', 0.20))

        self.terminal_statuses = get_terminal_statuses(self.config)

        rules_cfg = self.config.get('task_dispatch_rules', {})
        self.dispatch_rules = {
            'skip_statuses':                 self.terminal_statuses,
            'create_pick_task_for_unhealthy': rules_cfg.get('create_pick_task_for_unhealthy', True),
            'create_inspect_task_for_healthy': rules_cfg.get('create_inspect_task_for_healthy', True),
        }

        init_schema(self.db_path)
        self.get_logger().info(f"Database Logger ready. DB: {self.db_path}")

        self.create_subscription(
            String, '/sky_vision/detected_targets',
            self._detection_cb, 10)

    def _detection_cb(self, msg):
        try:
            data = json.loads(msg.data)
            self._process(data)
        except Exception as e:
            self.get_logger().error(f"Detection callback error: {e}")

    def _process(self, data: dict):
        class_name  = data.get('class_name', '')
        orchard_id  = data.get('orchard_id', '')
        lps_x = data.get('orchard_lps_x_m', 0.0)
        lps_y = data.get('orchard_lps_y_m', 0.0)
        lps_z = data.get('orchard_lps_z_m', 0.0)

        # Find or assign object identity
        object_id = find_duplicate_object_id(
            self.db_path, class_name, orchard_id,
            lps_x, lps_y, lps_z, self.dup_radius)

        is_new = not object_id
        if is_new:
            import time
            object_id = build_object_id(
                data.get('plant_id', f"{orchard_id}_unknown"),
                int(time.time() * 1000) % 1000)

        # Check terminal status
        if not is_new:
            status = get_object_status(self.db_path, object_id)
            if should_skip_object(status, self.terminal_statuses):
                self.get_logger().info(f"Skipping terminal object [{object_id}]")
                return

        # Upsert tracked object
        obj_record = dict(data)
        obj_record['object_id'] = object_id
        obj_record['object_status'] = 'new' if is_new else get_object_status(
            self.db_path, object_id)
        upsert_tracked_object(self.db_path, obj_record)

        # Insert detection event
        event_data = dict(data)
        event_data['object_id'] = object_id
        event_id = insert_detection_event(self.db_path, event_data)

        # Insert size measurement if reliable
        size_mm   = data.get('estimated_size_mm', 0.0)
        size_conf = 0.7 if size_mm > 0 else 0.0
        if size_is_reliable(size_conf, 0.5):
            insert_size_measurement(
                self.db_path, object_id,
                size_mm, 'pinhole_bbox', size_conf, event_id)

        # Compute and save action poses
        yaw = 0.0
        for access_mode in ['top', 'side']:
            task_key = f'inspect_pose_{access_mode}'
            pose_def = self.config.get('object_action_defaults', {}).get(task_key, {})
            pose = compute_action_pose(
                lps_x, lps_y, lps_z, yaw,
                float(pose_def.get('standoff_distance_m', 1.5)),
                float(pose_def.get('vertical_offset_m', 0.0)),
                access_mode)
            poses_data = {
                f'inspect_{access_mode}_x': pose['x'],
                f'inspect_{access_mode}_y': pose['y'],
                f'inspect_{access_mode}_z': pose['z'],
                f'inspect_{access_mode}_yaw': pose['yaw'],
            }
            upsert_action_poses(self.db_path, object_id, poses_data)

        # Resolve next task
        health = data.get('health_status', 'unknown')
        current_status = obj_record['object_status']
        next_task = resolve_next_task_type(health, current_status, self.dispatch_rules)
        if next_task:
            insert_task_event(self.db_path, object_id, next_task,
                              'scheduled', 'pending')
            update_object_status(self.db_path, object_id,
                                 'scheduled_pick' if 'pick' in next_task
                                 else 'scheduled_inspect')

        label = "NEW" if is_new else "UPDATED"
        self.get_logger().info(
            f"{label} [{class_name}] id={object_id} "
            f"health={health} size={size_mm:.1f}mm task={next_task}")


def main(args=None):
    rclpy.init(args=args)
    node = DatabaseLoggerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
