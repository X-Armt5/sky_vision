#!/bin/bash
# ~/sky_vision/scripts/run_system_nodes.sh
# chmod +x ~/sky_vision/scripts/run_system_nodes.sh

CONFIG=$HOME/sky_vision/config/system_config.yaml

echo "Cleaning up previous nodes..."
pkill -f "sky_vision_ros" || true
sleep 2

echo "Launching Sky Vision system nodes..."

# 1. Database Logger
gnome-terminal --title="Database Logger" -- bash -c "
source $HOME/sky_vision/scripts/env.sh
ros2 run sky_vision_ros database_logger --ros-args --params-file $CONFIG
exec bash" &
sleep 1

# 2. Vision Tracker
gnome-terminal --title="Vision Tracker" -- bash -c "
source $HOME/sky_vision/scripts/env.sh
ros2 run sky_vision_ros vision_tracker --ros-args --params-file $CONFIG
exec bash" &
sleep 1

# 3. QGC Video Streamer
gnome-terminal --title="QGC Streamer" -- bash -c "
source $HOME/sky_vision/scripts/env.sh
ros2 run sky_vision_ros video_streamer_qgc --ros-args --params-file $CONFIG
exec bash" &
sleep 1

# 4. Picking Manager
gnome-terminal --title="Picking Manager" -- bash -c "
source $HOME/sky_vision/scripts/env.sh
ros2 run sky_vision_ros picking_manager --ros-args --params-file $CONFIG
exec bash" &
sleep 1

# 5. Offboard Flight Controller
# Override mission at launch with: -p mission_id:=orchard_a_row_03 -p task_type:=row_scan
gnome-terminal --title="Flight Controller" -- bash -c "
source $HOME/sky_vision/scripts/env.sh
ros2 run sky_vision_ros offboard_control --ros-args --params-file $CONFIG -p mission_id:=orchard_a_row_04
exec bash" &

echo "All nodes launched."
