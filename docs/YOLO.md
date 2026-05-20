To install YOLOv8 (ultralytics) and its dependencies using uv within our ROS 2 environment, we need to be slightly careful with the numpy version. 

ROS 2's cv_bridge (which we use to convert ROS image topics to OpenCV images) requires numpy < 2.0, but newer versions of ultralytics often try to pull in numpy 2.x, which will break our ROS 2 node.
​

Since we have already created and activated our uv virtual environment with --system-site-packages (which correctly exposes our system's ROS 2 Jazzy python libraries to the venv), we can safely install YOLOv8:

Installation Steps
Make sure our environment is activated:

cd ~/sky_vision
source .venv/bin/activate

Use uv add to install ultralytics while forcing the numpy version to stay below 2.0, and install opencv-python-headless (which is safer for ROS 2 background nodes):

cd sky_vision

source .venv/bin/activate

uv add ultralytics opencv-python "numpy<2" pillow setuptools==79.0.1 # Image extras

uv sync
uv run python -c 'import rclpy, px4_msgs.msg; print("ROS ready!")'

Because we used uv init and created a project, we can use uv add ultralytics "numpy<2" opencv-python-headless to permanently add them to our pyproject.toml file

Verifying the Installation
To verify that YOLOv8 installed correctly and doesn't conflict with ROS 2's cv_bridge, run a quick python test in our terminal:

uv run python -c 'import rclpy; from cv_bridge import CvBridge; from ultralytics import YOLO; print("ROS 2 and YOLO are playing nicely together")'


If that prints the success message without throwing a numpy-related error, we are completely ready to write our YOLO Apple Detection node!

# To run vision_tracker_node.py, needs to be inside the virtual environment
source ~/sky_vision/.venv/bin/activate

## NOT IMPORTANT
# source /home/ubuntu/ardupilot_drone/src/ardupilot/Tools/completion/completion.bash

cd ~/sky_vision

source .venv/bin/activate
# eller
source ~/sky_vision/.venv/bin/activate

uv run python build/sky_vision_ros/sky_vision_ros/vision_tracker_node.py