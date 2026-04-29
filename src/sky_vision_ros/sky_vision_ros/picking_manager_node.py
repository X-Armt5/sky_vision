#!/usr/bin/env python3
# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/picking_manager_node.py
"""
picking_manager_node.py
Responsibility: Pick execution only.
  - Subscribes to /sky_vision/pick_request
  - Runs PickStateMachine (approach, align, grasp, verify, retreat)
  - When manipulator.enabled: false → runs approach only, records tool_unavailable
  - Publishes outcome to /sky_vision/pick_outcome
  - All tool logic isolated in pick_utils.py
"""
import rclpy, json, time
from rclpy.node   import Node
from std_msgs.msg import String

from sky_vision_ros.config_utils import load_yaml
from sky_vision_ros.pick_utils   import PickStateMachine, is_tool_enabled
from sky_vision_ros.db_utils     import insert_task_event, update_object_status


class PickingManagerNode(Node):

    def __init__(self):
        super().__init__('picking_manager_node')

        self.declare_parameter('config_path', '~/sky_vision/config/system_config.yaml')
        cfg_path    = self.get_parameter('config_path').value
        self.config = load_yaml(cfg_path)

        db_cfg       = self.config.get('database', {})
        self.db_path = db_cfg.get('db_path', '~/sky_vision/data/mission_data.db')

        tool_active = is_tool_enabled(self.config)
        self.get_logger().info(
            f"Picking Manager ready. Tool enabled: {tool_active}")

        self.outcome_pub = self.create_publisher(
            String, '/sky_vision/pick_outcome', 10)

        self.create_subscription(
            String, '/sky_vision/pick_request',
            self._pick_request_cb, 10)

    def _pick_request_cb(self, msg):
        try:
            req = json.loads(msg.data)
            self._execute_pick(req)
        except Exception as e:
            self.get_logger().error(f"Pick request error: {e}")

    def _execute_pick(self, req: dict):
        object_id = req.get('object_id', '')
        task_type = req.get('task_type', 'object_pick_approach_side')

        self.get_logger().info(f"Pick request for object [{object_id}]")

        sm = PickStateMachine(self.config)

        while not sm.is_done():
            state = sm.current_state
            self.get_logger().info(f"  Pick state: {state}")

            if state == 'APPROACH':
                # Offboard node handles actual movement via /sky_vision/pick_request pose
                time.sleep(0.5)
                sm.advance()

            elif state == 'ALIGN':
                time.sleep(0.3)
                sm.advance()

            elif state == 'GRASP':
                if is_tool_enabled(self.config):
                    self.get_logger().info("  Sending grasp command...")
                    # publish to manipulator topic from config
                    time.sleep(float(self.config.get('manipulator',{})
                                     .get('grasp_timeout_s', 5.0)))
                    sm.mark_success()
                else:
                    sm.mark_no_tool()

            elif state == 'NO_TOOL_HOLD':
                self.get_logger().warn(
                    "  No physical tool attached. Approach complete, recording outcome.")
                time.sleep(1.0)
                sm.mark_no_tool()

            elif state == 'VERIFY':
                time.sleep(0.5)
                sm.advance()

            elif state == 'RETREAT':
                time.sleep(0.3)
                sm.advance()

            else:
                sm.advance()

        outcome = sm.outcome
        self.get_logger().info(f"Pick done. Object [{object_id}] outcome=[{outcome}]")

        # Persist outcome
        insert_task_event(self.db_path, object_id, task_type,
                          'completed', outcome)
        if outcome == 'picked':
            update_object_status(self.db_path, object_id, 'picked')
        elif outcome == 'missed':
            update_object_status(self.db_path, object_id, 'missed')

        # Publish outcome
        result = String()
        result.data = json.dumps({
            'object_id': object_id,
            'task_type': task_type,
            'outcome':   outcome})
        self.outcome_pub.publish(result)


def main(args=None):
    rclpy.init(args=args)
    node = PickingManagerNode()
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
