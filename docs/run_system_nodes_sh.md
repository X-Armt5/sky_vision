CONFIG=$HOME/sky_vision/config/system_config.yaml
# Stores the full path to the system config YAMML in the config variable
echo "Cleaning up previous nodes..."
# Prints status message to show that its cleaning the previous nodes
pkill -f "sky_vision_ros" || true
# Kills all process with sky_vision_ros in their command line
sleep 2
# Pauses for 2 seconds
echo "Launching Sky Vision system nodes..."
# Prints a status message to signal that the sky vision system nodes are starting

#### 1. Database Logger
gnome-terminal --title="Database Logger" -- bash -c "
# Launches bash inside a new terminal with the title "Databse Logger" for easy identification
source $HOME/sky_vision/scripts/env.sh
# Source the env
ros2 run sky_vision_ros database_logger --ros-args --params-file $CONFIG
# Executes the database_logger node from sky_vision_ros (found in setup.py). Passes params from $CONFIG (system_config.yaml) via --ros-args --params-file, overriding defaults (e.g., DB connection strings, log topics like sensor_combined or detections)
exec bash" &
sleep 1

#### 2. Vision Tracker
gnome-terminal --title="Vision Tracker" -- bash -c "
# Launches bash inside a new terminal with the title "Vision Tracker" for easy identification
source $HOME/sky_vision/scripts/env.sh
# Source env
ros2 run sky_vision_ros vision_tracker --ros-args --params-file $CONFIG
# Executes the vision_tracker node from sky_vision_ros (found in setup.py). Loads parameters from $CONFIG (e.g., model paths, thresholds, camera calibration)
exec bash" &
sleep 1

#### 3. QGC Video Streamer
gnome-terminal --title="QGC Streamer" -- bash -c "
# Launches bash inside a new terminal with the title "QGC Streamer" for easy identification
source $HOME/sky_vision/scripts/env.sh
# source env
ros2 run sky_vision_ros video_streamer_qgc --ros-args --params-file $CONFIG
# Executes the video_streamer_qgc node from sky_vision_ros (found in setup.py). Loads config params (e.g., stream ports, resolutions, MAVLink UDP targets for QGC video view)
exec bash" &
sleep 1

#### 4. Picking Manager
gnome-terminal --title="Picking Manager" -- bash -c "
# Launches bash inside a new terminal with the title "Picking Manager" for easy identification
source $HOME/sky_vision/scripts/env.sh
# source env
ros2 run sky_vision_ros picking_manager --ros-args --params-file $CONFIG
# Executes the picking_manager node from sky_vision_ros (found in setup.py). Applies YAML params (e.g., target criteria, priority rules, integration with tracker/database)
exec bash" &
sleep 1

#### 5. Offboard Flight Controller
# Override mission at launch with: -p mission_id:=orchard_a_row_03 -p task_type:=row_scan
gnome-terminal --title="Flight Controller" -- bash -c "
# Launches bash inside a new terminal with the title "Flight Controller" for easy identification
source $HOME/sky_vision/scripts/env.sh
# source env
ros2 run sky_vision_ros offboard_control --ros-args --params-file $CONFIG -p mission_id:=orchard_a_row_04
# Runs the offboard_control node from sky_vision_ros (found in setup.py). Loads base params from $CONFIG, overrides mission_id to orchard_a_row_04 (hardcoded for this row in the sim), and enables offboard mode to PX4 via px4_ros_com (publishing TrajectorySetpoints)
exec bash" &

echo "All nodes launched."
# Prints status message that confirmes that the full stack (nodes) is up
