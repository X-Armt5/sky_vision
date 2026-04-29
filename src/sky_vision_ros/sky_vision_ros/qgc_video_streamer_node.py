#!/usr/bin/env python3
# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/qgc_video_streamer_node.py
"""
qgc_video_streamer_node.py
Responsibility: QGroundControl-targeted video streaming.
Thin wrapper over video_stream_utils with QGC defaults (port 5600, H.264 UDP).
"""
import rclpy
from rclpy.node      import Node
from sensor_msgs.msg import Image
from cv_bridge       import CvBridge

from sky_vision_ros.ros_utils          import discover_px4_topics
from sky_vision_ros.video_stream_utils import build_gstreamer_pipeline, open_video_writer


class QGCVideoStreamerNode(Node):

    def __init__(self):
        super().__init__('qgc_video_streamer_node')

        # QGC defaults: port 5600, same IP key as system_config.yaml
        self.declare_parameter('stream_target_ip',   '192.168.11.32')
        self.declare_parameter('stream_target_port', 5600)
        self.declare_parameter('target_fps',         30.0)

        self.target_ip   = str(self.get_parameter('stream_target_ip').value).strip()
        self.target_port = int(self.get_parameter('stream_target_port').value)
        self.target_fps  = float(self.get_parameter('target_fps').value)

        self.bridge       = CvBridge()
        self.video_writer = None

        self.get_logger().info(
            f"QGC Video Streamer ready → {self.target_ip}:{self.target_port}")
        self._discovery_timer = self.create_timer(1.0, self._find_camera)

    def _find_camera(self):
        topics = discover_px4_topics(self)
        if 'camera' not in topics:
            return
        self._discovery_timer.cancel()
        self.create_subscription(Image, topics['camera'], self._image_cb, 10)
        self.get_logger().info(f"QGC Streamer bound to: {topics['camera']}")

    def _image_cb(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w, _ = frame.shape
        if self.video_writer is None:
            pipeline = build_gstreamer_pipeline(self.target_ip, self.target_port)
            self.video_writer = open_video_writer(pipeline, self.target_fps, w, h)
            if self.video_writer:
                self.get_logger().info("QGC GStreamer pipeline opened.")
            else:
                self.get_logger().error("QGC pipeline failed to open.")
        if self.video_writer:
            self.video_writer.write(frame)


def main(args=None):
    rclpy.init(args=args)
    node = QGCVideoStreamerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node.video_writer:
            node.video_writer.release()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
