#### First script

pkill -f MicroXRCEAgent || true
# Kills processes matching pattern "MicroXRCEAgent"
pkill -f gz || true
# Kills all gazebo harmonic processes
pkill -f px4 || true
# Kills all px4 processes
sleep 2
# Pauses 2s for graceful termination
cd ~/PX4-Autopilot || exit 1
# Changes to PX4 repo, exits on failure

#### Second script

gnome-terminal -- bash -c "
# Opens new terminal, runs commands in background
source ~/sky_vision/scripts/env.sh;
# Loads projects environment setup script
echo 'Starting MicroXRCEAgent...';
# Prints status message that shows the agent startup has begun
MicroXRCEAgent udp4 -p 8888;
# starts DDS agent on UDP port 8888 for uORB-to-DDS bridging (PX4 to ROS2)
exec bash
# Replaces shell with interactive Bash on finish (keeps terminal open)
" &
sleep 3
# Pauses 3s for graceful termination

#### Third script

gnome-terminal -- bash -c "
# Opens new terminal, runs commands in background
source ~/sky_vision/scripts/env.sh;
# Sources env
echo 'Waiting for Gazebo to publish camera topics...';
# Prints status waits for Gazebo topics

while true; do
# Infinite loop until topic found
    CAMERA_TOPIC=\$(gz topic -l | grep -E '/sensor/.*image' | head -n 1)
# Lists all Gazebo topics (gz topic -l), greps for ones matching /sensor/...image (e.g., /world/apple_orchard/model/x500_gimbal/link/camera/image), and takes the first match (head -n 1). Stores it in CAMERA_TOPIC. The $(...) captures the output
    if [ -n \"\$CAMERA_TOPIC\" ]; then
# Checks if CAMERA_TOPIC is non-empty 
        echo \"✅ Found Camera: \$CAMERA_TOPIC\"
# Prints out the found topic name
        break
# Exits the loop once a topic is found
    fi
    sleep 1
# Pauses for 1s before running the loop again if no topic was found
done
echo 'Starting Image Bridge...'
# Prints status message for the bridge statup
ros2 run ros_gz_image image_bridge \$CAMERA_TOPIC
# Runs the ros_gz_image bridge node, passing the detected topic (e.g., /world/.../image).
exec bash
# Replaces the current shell with a new fresh one
" &
sleep 2
# Pauses 2s for graceful termination

#### Fourth script

gnome-terminal -- bash -c "
# Open a new terminal, runs commands in background
cd ~/PX4-Autopilot;
# change directory to PX4-Autopilot
echo 'Starting PX4 SITL & Gazebo Harmonic...';
# Prints a status message in the terminal so you know the statup has begun
CONFIG_FILE=~/sky_vision/config/system_config.yaml
# Stores the path to your configuration file in a shell so it can be reused in later commands
TARGET_SYS=\$(grep 'px4_target_system:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')
# Reads the px4_target_system value from the YAML file, it finds matching line, removes anything after a # comment, extracts the value after the colon, and spaces, quotes and double quotes
MAVLINK_IP=\$(grep 'mavlink_target_ip:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')
# Does the same parsing for the MAVLink target IP address. That IP is later passed to mavlink start -t , -t means partner IP
# export PX4_HOME_LAT=\$(grep 'px4_home_lat:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')
# export PX4_HOME_LON=\$(grep 'px4_home_lon:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')
# export PX4_HOME_ALT=\$(grep 'px4_home_alt:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')
# These lines are disabled because they start with #. If enabled, they would set the home latitude, longitude, and altitude for SITL. Right now, they do nothing
# CHANGED MODEL TO GIMBAL
PX4_SYS_AUTOSTART=4019 \\
# Set the PX4 airframe autostart ID to 4019, which corresponds to the gazebo gz_x500_gimbal vechile
PX4_GZ_MODEL_POSE=\"0,0\" \\
# Sets the såawn pose of the gazebo model
PX4_GZ_MODEL=x500_gimbal \\
# Selects the gazebo model name to use
PX4_GZ_WORLD=apple_orchard \\
# Chooses the Gazebo world to load
./build/px4_sitl_default/bin/px4 -i \$TARGET_SYS << EOF
# Runs the PX4 SITL binadry and assigns the system instance ID with -i. The << EOF make the lines until the next EOF be fed as commands into PX4 shell
mavlink stop-all
# Stops all currently running MAVLink instances
mavlink start -u 14550 -t \$MAVLINK_IP -r 4000
# Starts a new MAVLink instance on UDP port 14550, targets the IP stored in MAVLink_IP and limits transmission rate to 4000 B/s. -u selects the local UDP port, -t set the partner IP, -r sets the maximum sending rate
param set COM_ARM_WO_GPS 1
# Allows arming without GPS
param set MNT_MODE_IN 4
# Sets the mount/gimbal input mode to 4, which is used to configure how the gimbal recieves control inputs
EOF
# PX4 stops reading the embedded command block
exec bash
# Replaces the current PX4 shell with a new fresh one
" &
sleep 8
# Pauses 8s for graceful termination

#### Fifth script

gnome-terminal -- bash -c "
# Open a new terminal, runs commands in background
source ~/sky_vision/scripts/env.sh
# Sources the env in the new terminal
echo 'Starting PX4 sensor listeners...';
# Print status message to show that the PX4 sensor listener is starting
ros2 run px4_ros_com sensor_combined_listener;
# Runs the sensor_combined_listener exutable from px4_ros_com ROS2 package 
exec bash
# Replaces the cureent shell with new one
" &

