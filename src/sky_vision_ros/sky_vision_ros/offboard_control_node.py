#!/usr/bin/env python3
# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/offboard_control_node.py
"""
offboard_control_node.py
Responsibility: Drone flight control only.
  - Offboard heartbeat
  - Arm / disarm
  - Waypoint progression with pause/hover
  - Approach and retreat poses
  - Gimbal control
  - Return-home and land
Mission content is resolved from YAML via config_utils.
"""
import rclpy, math, time
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from px4_msgs.msg import (OffboardControlMode, TrajectorySetpoint,
                           VehicleCommand, VehicleLocalPosition, VehicleStatus)
from std_msgs.msg import String

from sky_vision_ros.sky_vision_ros.ros_utils     import discover_px4_topics
from sky_vision_ros.sky_vision_ros.config_utils  import load_yaml, resolve_mission_waypoints, get_takeoff_height 
from sky_vision_ros.sky_vision_ros.geometry_utils import euclidean_distance_3d


class OffboardControlNode(Node):

    def __init__(self):
        super().__init__('offboard_control_node')

        self.declare_parameter('config_path', '~/sky_vision/config/system_config.yaml')
        self.declare_parameter('mission_id',  'orchard_a_row_01')
        self.declare_parameter('task_type',   'row_scan')
        self.declare_parameter('target_object_id', '')

        cfg_path   = self.get_parameter('config_path').value
        mission_id = self.get_parameter('mission_id').value
        task_type  = self.get_parameter('task_type').value

        self.config = load_yaml(cfg_path)
        flight      = self.config.get('flight_defaults', {})

        self.takeoff_height = get_takeoff_height(self.config)
        self.arrival_tol      = float(flight.get('arrival_tolerance_m', 1.5))
        self.pause_duration   = float(flight.get('waypoint_pause_duration_s', 15.0))
        self.home_hover_time  = float(flight.get('home_hover_time_s', 5.0))
        self.gimbal_down      = float(flight.get('gimbal_pitch_down_deg', -90.0))
        self.gimbal_forward   = float(flight.get('gimbal_pitch_forward_deg', 0.0))

        drone_cfg      = self.config.get('drone', {})
        self.target_system = int(drone_cfg.get('px4_target_system', 0))
###        
        self.local_waypoints = resolve_mission_waypoints(self.config, mission_id)

        self.get_logger().info(
            f"Mission [{mission_id}] | Task [{task_type}] | "
            f"Waypoints: {len(self.local_waypoints)}")

        self.current_x = self.current_y = self.current_z = 0.0
        self.home_set     = False
        self.is_armed     = False
        self.landing_triggered = False
        self.returning_home    = False
        self.home_hovering     = False
        self.home_hover_start  = None
        self.current_wp_index  = 0
        self.is_paused         = False
        self.pause_start_time  = None
        self.offboard_counter  = 0
        self.current_gimbal_pitch = 0.0

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST, depth=1)

        self._offboard_pub   = None
        self._trajectory_pub = None
        self._command_pub    = None
        self._qos = qos

        self.get_logger().info("Offboard Control Node started. Discovering topics...")
        self._discovery_timer = self.create_timer(1.0, self._find_topics)

    def _find_topics(self):
        topics = discover_px4_topics(self)
        required = ['offboard', 'trajectory', 'command', 'local_pos', 'status']
        if not all(k in topics for k in required):
            return
        self._offboard_pub   = self.create_publisher(OffboardControlMode, topics['offboard'], self._qos)
        self._trajectory_pub = self.create_publisher(TrajectorySetpoint,  topics['trajectory'], self._qos)
        self._command_pub    = self.create_publisher(VehicleCommand,       topics['command'], self._qos)
        self.create_subscription(VehicleLocalPosition, topics['local_pos'], self._local_pos_cb, self._qos)
        self.create_subscription(VehicleStatus,        topics['status'],    self._status_cb,    self._qos)
        self._discovery_timer.cancel()
        self._control_timer = self.create_timer(0.1, self._control_loop)
        self.get_logger().info("Connected to PX4. Control loop active.")

    def _local_pos_cb(self, msg):
        self.current_x, self.current_y, self.current_z = msg.x, msg.y, msg.z
        if not self.home_set and msg.xy_global:
            self.home_set = True

    def _status_cb(self, msg):
        self.is_armed = (msg.arming_state == VehicleStatus.ARMING_STATE_ARMED)

    def _publish_heartbeat(self):
        msg = OffboardControlMode()
        msg.position  = True
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self._offboard_pub.publish(msg)

    def _publish_setpoint(self, x, y, z, yaw):
        msg = TrajectorySetpoint()
        msg.position  = [float(x), float(y), float(z)]
        msg.yaw       = float(yaw)
        msg.timestamp = int(self.get_clock().now().nanoseconds / 1000)
        self._trajectory_pub.publish(msg)

    def _publish_vehicle_command(self, command, **params):
        msg = VehicleCommand()
        msg.command        = command
        msg.param1         = float(params.get('param1', 0.0))
        msg.param2         = float(params.get('param2', 0.0))
        msg.param3         = float(params.get('param3', 0.0))
        msg.param7         = float(params.get('param7', 0.0))
        msg.target_system  = self.target_system
        msg.target_component = 1
        msg.source_system  = 255
        msg.source_component = 1
        msg.from_external  = True
        msg.timestamp      = int(self.get_clock().now().nanoseconds / 1000)
        self._command_pub.publish(msg)


    def _arm(self) -> None:
        self._publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            param1=1.0,
        )
        self.get_logger().info("Arming drone.")

    def _land(self) -> None:
        self._publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
        self.get_logger().info("Landing sequence initiated.")

    def _engage_offboard(self) -> None:
        self._publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
            param1=1.0,
            param2=6.0,
        )
        self.get_logger().info("Offboard mode engaged.")


    def _point_gimbal(self, pitch_deg: float):
        if math.isclose(pitch_deg, self.current_gimbal_pitch, abs_tol=0.5):
            return
        self._publish_vehicle_command(205, param1=pitch_deg, param7=2.0)
        self.current_gimbal_pitch = pitch_deg

    def _control_loop(self):
        if self.landing_triggered or self._offboard_pub is None:
            return

        self._publish_heartbeat()

        if self.offboard_counter == 10:
            self._engage_offboard()
            self._arm()
            self._point_gimbal(self.gimbal_down)

        if self.offboard_counter < 11:
            self.offboard_counter += 1

        if not self.home_set or not self.local_waypoints:
            return

        if self.returning_home:
            self._handle_return_home()
        elif self.current_wp_index < len(self.local_waypoints):
            self._handle_waypoint()
        else:
            self.returning_home = True

    def _handle_return_home(self):
        self._point_gimbal(self.gimbal_forward)
        self._publish_setpoint(0.0, 0.0, self.takeoff_height,
                                math.atan2(-self.current_y, -self.current_x))
        dist = euclidean_distance_3d(self.current_x, self.current_y, self.current_z,
                                      0.0, 0.0, self.takeoff_height)
        if dist < self.arrival_tol and not self.home_hovering:
            self.home_hovering    = True
            self.home_hover_start = time.time()
        if self.home_hovering and time.time() - self.home_hover_start >= self.home_hover_time:
            self._land()
            self.landing_triggered = True
            raise SystemExit

    def _handle_waypoint(self):
        target = self.local_waypoints[self.current_wp_index]
        dx = target['x'] - self.current_x
        dy = target['y'] - self.current_y
        yaw = math.atan2(dy, dx) if self.current_wp_index > 0 else 0.0
        self._publish_setpoint(target['x'], target['y'], self.takeoff_height, yaw)

        if self.is_paused:
            self._point_gimbal(self.gimbal_down)
            if time.time() - self.pause_start_time >= self.pause_duration:
                self.is_paused = False
                self.current_wp_index += 1
        else:
            self._point_gimbal(self.gimbal_forward)
            dist = euclidean_distance_3d(self.current_x, self.current_y, self.current_z,
                                          target['x'], target['y'], self.takeoff_height)
            if dist < self.arrival_tol:
                if self.current_wp_index == 0:
                    self.current_wp_index += 1
                else:
                    self.is_paused        = True
                    self.pause_start_time = time.time()


def main(args=None):
    rclpy.init(args=args)
    node = OffboardControlNode()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
