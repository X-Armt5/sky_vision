#!/bin/bash
source /opt/ros/jazzy/setup.bash # Initialize the core ROS 2 Jazzy distribution
source ~/px4_ros_uxrce_dds_ws/src/install/setup.bash # Load micro-XRCE-DDS bridge setup
source ~/sky_vision/install/local_setup.bash # PX4 message and sky_vision project environment
export GZ_SIM_RESOURCE_PATH=~/sky_vision/models:$GZ_SIM_RESOURCE_PATH
