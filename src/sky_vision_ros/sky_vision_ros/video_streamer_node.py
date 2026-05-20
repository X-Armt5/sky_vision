#!/usr/bin/env python3
# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/video_streamer_node.py
"""
video_streamer_node.py
Responsibility: Generic UDP video streaming.
Streams camera feed via GStreamer H.264 UDP to a configurable IP/port.
Pipeline logic shared via video_stream_utils.py.
"""
import rclpy
from rclpy.node      import Node
from sensor_msgs.msg import Image
from cv_bridge       import CvBridge

from sky_vision_ros.ros_utils          import discover_px4_topics
from sky_vision_ros.video_stream_utils import build_gstreamer_pipeline, open_video_writer


class VideoStreamerNode(Node):

    def __init__(self):
        super().__init__('video_streamer_node')

        self.declare_parameter('stream_target_ip', '127.0.0.1')   #('192.168.11.32')
        self.declare_parameter('stream_target_port', 5600)
        self.declare_parameter('target_fps',         30.0)

        self.target_ip   = str(self.get_parameter('stream_target_ip').value).strip()
        self.target_port = int(self.get_parameter('stream_target_port').value)
        self.target_fps  = float(self.get_parameter('target_fps').value)

        self.bridge       = CvBridge()
        self.video_writer = None

        self.get_logger().info(
            f"Video Streamer ready → {self.target_ip}:{self.target_port} "
            f"@ {self.target_fps} FPS")
        self._discovery_timer = self.create_timer(1.0, self._find_camera)

    def _find_camera(self):
        topics = discover_px4_topics(self)
        if 'camera' not in topics:
            return
        self._discovery_timer.cancel()
        self.create_subscription(Image, topics['camera'], self._image_cb, 10)
        self.get_logger().info(f"Bound to camera topic: {topics['camera']}")

    def _image_cb(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
        h, w, _ = frame.shape
        if self.video_writer is None:
            pipeline = build_gstreamer_pipeline(self.target_ip, self.target_port)
            self.video_writer = open_video_writer(pipeline, self.target_fps, w, h)
            if self.video_writer:
                self.get_logger().info("GStreamer pipeline opened.")
            else:
                self.get_logger().error("Failed to open GStreamer pipeline.")
        if self.video_writer:
            self.video_writer.write(frame)


def main(args=None):
    rclpy.init(args=args)
    node = VideoStreamerNode()
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
