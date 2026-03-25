# ~/sky_vision/src/sky_vision_ros/sky_vision_ros/video_stream_utils.py
"""
video_stream_utils.py
Shared GStreamer H.264 UDP pipeline builder for video streaming nodes.
Used by: video_streamer_node, qgc_video_streamer_node.
"""
import cv2


def build_gstreamer_pipeline(target_ip: str, target_port: int) -> str:
    """
    Returns a GStreamer pipeline string for H.264 UDP streaming.
    Locks input caps to BGR to prevent OpenCV negotiation failure.
    """
    return (
        f"appsrc ! video/x-raw,format=BGR ! "
        "videoconvert ! video/x-raw,format=I420 ! "
        "x264enc tune=zerolatency bitrate=1000 speed-preset=superfast ! "
        "h264parse ! "
        f"rtph264pay config-interval=1 pt=96 ! "
        f"udpsink host={target_ip} port={target_port} sync=false"
    )


def open_video_writer(pipeline: str, fps: float,
                      width: int, height: int):
    """
    Creates and returns a cv2.VideoWriter using the given GStreamer pipeline.
    Returns None if the writer fails to open.
    """
    writer = cv2.VideoWriter(
        pipeline,
        cv2.CAP_GSTREAMER,
        0,
        float(fps),
        (int(width), int(height)),
        True
    )
    if not writer.isOpened():
        return None
    return writer
