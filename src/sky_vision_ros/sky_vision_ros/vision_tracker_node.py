#!/usr/bin/env python3
# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/vision_tracker_node.py
"""
vision_tracker_node.py
Responsibility: Vision only.
  - YOLO object detection
  - Bbox extraction
  - World position estimation (GPS + LPS)
  - Health label mapping
  - Size estimation
  - Publish structured detection payloads as JSON on /sky_vision/detected_targets
"""
import rclpy, math, json, threading
from rclpy.node import Node
from rclpy.qos  import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
from px4_msgs.msg import VehicleLocalPosition, VehicleAttitude, VehicleStatus, VehicleCommand
from sensor_msgs.msg import Image
from std_msgs.msg    import String
from cv_bridge       import CvBridge
import cv2
from ultralytics import YOLO

from sky_vision_ros.sky_vision_ros.ros_utils            import discover_px4_topics
from sky_vision_ros.sky_vision_ros.geometry_utils       import (ned_to_gps, get_euler_from_quaternion,
                                                  calculate_ground_intersection)
from sky_vision_ros.sky_vision_ros.config_utils         import load_yaml
from sky_vision_ros.sky_vision_ros.detection_utils      import (extract_bbox, map_health_label,
                                                  build_detection_payload)
from sky_vision_ros.sky_vision_ros.size_estimation_utils import estimate_size_mm


class VisionTrackerNode(Node):

    def __init__(self):
        super().__init__('vision_tracker_node')

        self.declare_parameter('config_path',         '~/sky_vision/config/system_config.yaml')
        self.declare_parameter('yolo_model_path',     'yolov8n.pt')
        self.declare_parameter('target_class_id',     47)
        self.declare_parameter('target_class_name',   'apple')
        self.declare_parameter('detection_confidence', 0.5)
        self.declare_parameter('orchard_id',          'orchard_a')
        self.declare_parameter('row_id',              'row_01')
        self.declare_parameter('task_type',           'row_scan')

        cfg_path = self.get_parameter('config_path').value
        self.config = load_yaml(cfg_path)

        vision_cfg  = self.config.get('vision', {})
        size_cfg    = self.config.get('size_estimation', {})
        health_cfg  = self.config.get('health_assessment', {})

        self.target_id     = self.get_parameter('target_class_id').value
        self.target_name   = self.get_parameter('target_class_name').value
        self.conf_thresh   = self.get_parameter('detection_confidence').value
        self.orchard_id    = self.get_parameter('orchard_id').value
        self.row_id        = self.get_parameter('row_id').value
        self.task_type     = self.get_parameter('task_type').value

        self.focal_length_px      = float(size_cfg.get('focal_length_px', 640.0))
        self.size_preferred_axis  = size_cfg.get('preferred_view_mode', 'min')
        self.min_size_confidence  = float(size_cfg.get('min_confidence_for_size', 0.5))
        self.healthy_labels       = health_cfg.get('healthy_labels',   ['healthy'])
        self.unhealthy_labels     = health_cfg.get('unhealthy_labels',  ['unhealthy'])

        model_path = self.get_parameter('yolo_model_path').value
        self.get_logger().info(f"Loading YOLO model [{model_path}] target=[{self.target_name}]")
        self.yolo_model = YOLO(model_path)

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST, depth=1)
        self._qos = qos

        self.bridge = CvBridge()
        self.frame_lock   = threading.Lock()
        self.latest_frame = None

        self.current_x = self.current_y = self.current_z = 0.0
        self.home_lat = self.home_lon = 0.0
        self.home_set = False
        self.dq = [1.0, 0.0, 0.0, 0.0]
        self.current_gimbal_pitch = 0.0
        self.is_armed     = False
        self.mission_done = False

        self.detection_pub = self.create_publisher(String, '/sky_vision/detected_targets', 10)

        self.get_logger().info("Vision Tracker Node started. Discovering topics...")
        self._discovery_timer = self.create_timer(1.0, self._find_topics)

    def _find_topics(self):
        topics = discover_px4_topics(self)
        required = ['local_pos', 'attitude', 'status', 'camera', 'command']
        if not all(k in topics for k in required):
            return
        self.create_subscription(VehicleLocalPosition, topics['local_pos'], self._local_pos_cb,  self._qos)
        self.create_subscription(VehicleAttitude,      topics['attitude'],  self._attitude_cb,   self._qos)
        self.create_subscription(VehicleStatus,        topics['status'],    self._status_cb,     self._qos)
        self.create_subscription(VehicleCommand,       topics['command'],   self._command_cb,    self._qos)
        self.create_subscription(Image,                topics['camera'],    self._image_cb,      10)
        self._discovery_timer.cancel()
        self.get_logger().info("Vision connected to PX4 and camera.")

    def _local_pos_cb(self, msg):
        self.current_x, self.current_y, self.current_z = msg.x, msg.y, msg.z
        if not self.home_set and msg.xy_global:
            self.home_lat, self.home_lon = msg.ref_lat, msg.ref_lon
            self.home_set = True

    def _attitude_cb(self, msg):
        self.dq = [msg.q[0], msg.q[1], msg.q[2], msg.q[3]]

    def _status_cb(self, msg):
        was_armed   = self.is_armed
        self.is_armed = (msg.arming_state == VehicleStatus.ARMING_STATE_ARMED)
        if was_armed and not self.is_armed:
            self.mission_done = True

    def _command_cb(self, msg):
        if msg.command == 205:
            self.current_gimbal_pitch = math.radians(abs(msg.param1))

    def _image_cb(self, msg):
        if self.mission_done:
            return
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w  = frame.shape[:2]

        if not (self.home_set and self.is_armed):
            status = "WAITING GPS..." if self.is_armed else "WAITING ARM..."
            cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2)
            with self.frame_lock:
                self.latest_frame = frame.copy()
            return

        yaw, _, _ = get_euler_from_quaternion(*self.dq)
        altitude  = abs(self.current_z)
        results   = self.yolo_model.predict(source=frame, verbose=False, conf=self.conf_thresh)
        found     = 0

        nadir_mode = self.current_gimbal_pitch > 1.5
        view_mode  = 'top' if nadir_mode else 'side'

        for result in results:
            for box in result.boxes:
                if int(box.cls[0]) != self.target_id:
                    continue
                found += 1
                bbox = extract_bbox(box)

                # World position
                if nadir_mode:
                    target_lat, target_lon = ned_to_gps(
                        self.current_x, self.current_y,
                        self.home_lat,  self.home_lon)
                    dist_m = altitude
                else:
                    # orbit/side view block
                    vert_offset_pct = (bbox['cy'] - h / 2) / (h / 2)

                    # Clamp to avoid zero pitch — use small non-zero fallback
                    MIN_OFFSET_PCT = 0.01
                    if abs(vert_offset_pct) < MIN_OFFSET_PCT:
                        vert_offset_pct = MIN_OFFSET_PCT

                    virtual_pitch = math.radians(15.0) * vert_offset_pct
                    ground_dist   = calculate_ground_intersection(altitude, virtual_pitch)
                    dist_m        = ground_dist
                    tx = self.current_x + ground_dist * math.cos(yaw)
                    ty = self.current_y + ground_dist * math.sin(yaw)
                    target_lat, target_lon = ned_to_gps(tx, ty, self.home_lat, self.home_lon)

                # Size
                size_mm, size_conf, size_method = estimate_size_mm(
                    bbox['width_px'], bbox['height_px'],
                    dist_m, self.focal_length_px, self.size_preferred_axis)

                # Health
                raw_label = self.target_name
                health = map_health_label(raw_label, self.healthy_labels, self.unhealthy_labels)

                payload = build_detection_payload(
                    class_id=self.target_id,
                    class_name=self.target_name,
                    health_status=health,
                    confidence=float(box.conf[0]),
                    bbox=bbox,
                    image_w=w, image_h=h,
                    latitude=target_lat,
                    longitude=target_lon,
                    altitude_m=altitude,
                    orchard_lps={'x': self.current_x,'y': self.current_y,'z': self.current_z},
                    plant_relative={'x': 0.0,'y': 0.0,'z': 0.0},
                    distance_from_lens_m=dist_m,
                    estimated_size_mm=size_mm,
                    orchard_id=self.orchard_id,
                    row_id=self.row_id,
                    view_mode=view_mode,
                    task_type=self.task_type,
                )

                out = String()
                out.data = json.dumps(payload)
                self.detection_pub.publish(out)

                # UI overlay
                cv2.rectangle(frame, (bbox['x1'], bbox['y1']),
                              (bbox['x2'], bbox['y2']), (0,255,0), 2)
                cv2.putText(frame, f"{self.target_name} {float(box.conf[0]):.2f}",
                            (bbox['x1'], bbox['y1']-30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,255,0), 1)
                cv2.putText(frame, f"Lat:{target_lat:.6f}",
                            (bbox['x1'], bbox['y1']-18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,255), 1)
                cv2.putText(frame, f"Lon:{target_lon:.6f}",
                            (bbox['x1'], bbox['y1']-6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0,255,255), 1)
                cv2.putText(frame, f"Size:{size_mm:.0f}mm ({size_conf:.1f})",
                            (bbox['x1'], bbox['y2']+12),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255,200,0), 1)

        mode_text = f"VIEW:{view_mode.upper()} | FOUND:{found}"
        cv2.putText(frame, mode_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,100,100), 2)

        with self.frame_lock:
            self.latest_frame = frame.copy()


def main(args=None):
    rclpy.init(args=args)
    node = VisionTrackerNode()

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    try:
        while rclpy.ok() and not node.mission_done:
            with node.frame_lock:
                frame = node.latest_frame
            if frame is not None:
                cv2.imshow(f"Vision Tracker: {node.target_name}", frame)
            if cv2.waitKey(30) & 0xFF == ord('q'):
                break
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
