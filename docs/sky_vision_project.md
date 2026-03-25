#### Bruker uv for å lage sky_vision workspace:

cd ~
uv init sky_vision
cd sky_vision

uv venv --system-site-packages .venv

#### Lage source(src) directory i sky_vision og gå inn i den for klone px4 msgs og px4 com fra github:

mkdir -p ~/sky_vision/src
cd ~/sky_vision/src

git clone https://github.com/PX4/px4_msgs.git
git clone https://github.com/PX4/px4_ros_com.git

# gå tilbake til workspace og source env også colcon build hele workspace:
cd ~/sky_vision
source /opt/ros/jazzy/setup.bash
colcon build

#### For å gjør det enkelere å source ROS dependcies, så kan en shell script lages (env.sh), da kommer alt til å source med en kommando i workspace:

cd ~/sky_vision
nano env.sh

sette alle source som trengs:

#!/bin/bash

# disse er allerde sourcet i filen .bashrc:

source /opt/ros/jazzy/setup.bash # Initialize the core ROS 2 Jazzy distribution
source ~/px4_ros_uxrce_dds_ws/src/install/setup.bash # Load micro-XRCE-DDS bridge setup
source ~/sky_vision/install/local_setup.bash # PX4 message and sky_vision project environment

# Gjør env.sh kjørbar, legg den inn i .bashrc og source den:

chmod +x env.sh
echo "source ~/sky_vision/env.sh" >> ~/.bashrc
source ~/.bashrc

#### Test

# Termianl 1:
cd /PX4-Autopilot
# kjør:
PX4_SYS_AUTOSTART=4002 \\
PX4_GZ_MODEL_POSE="0,0" \\
PX4_GZ_MODEL=x500_depth \\
./build/px4_sitl_default/bin/px4 -i 0

# Terminal 2:

MicroXRCEAgent udp4 -p 8888

# Terminal 3:
ros2 launch px4_ros_com sensor_combined_listener.launch.py

# Hvis dette funker vil du kunne se dataene blir printet i terminal hvor du kjørte ros listener:
RECEIVED SENSOR COMBINED DATA
================================
ts: 870938190
gyro_rad[0]: 0.00341645
gyro_rad[1]: 0.00626475
gyro_rad[2]: -0.000515705
gyro_integral_dt: 4739
accelerometer_timestamp_relative: 0
accelerometer_m_s2[0]: -0.273381
accelerometer_m_s2[1]: 0.0949186
accelerometer_m_s2[2]: -9.76044
accelerometer_integral_dt: 4739

#### Nå må ros-jazzy-ros-gz-image package istalleres for å kunne kjøre imagebridge etterpå:
sudo apt update &&
sudo apt install ros-jazzy-ros-gz-image

#### Nå skal en ny package lages i sky_vision/src, med en launch og init.py filer:
cd ~/sky_vision/src
ros2 pkg create --build-type ament_python sky_vision_ros
cd sky_vision_ros
mkdir -p sky_vision_ros launch
touch sky_vision_ros/**init**.py

# Inni sky_vision_ros skal det lages både nodene og nyttige verktøy(utilities), utilities skal kunne importeres inni nodene hvis behov til bruk:
config_utils.py
database_logger_node.py
db_utils.py
detection_utils.py
entity_utils.py
geometry_utils.py
offboard_control_node.py
pick_utils.py
picking_manager_node.py
qgc_video_streamer_node.py
ros_utils.py
size_estimation_utils.py
tast_utils.py
video_stream_utils.py
video_streamer_node.py
vision_tracker_node.py

# Alle scriptene skal være kjørbare:
chmod +x ~/sky_vision/src/sky_vision_ros/sky_vision_ros/database_logger_node.py
chmod +x ~/sky_vision/src/sky_vision_ros/sky_vision_ros/offboard_control_node.py
chmod +x ~/sky_vision/src/sky_vision_ros/sky_vision_ros/picking_manager_node.py
chmod +x ~/sky_vision/src/sky_vision_ros/sky_vision_ros/qgc_video_streamer_node.py
chmod +x ~/sky_vision/src/sky_vision_ros/sky_vision_ros/video_streamer_node.py
chmod +x ~/sky_vision/src/sky_vision_ros/sky_vision_ros/vision_tracker_node.py

# Alle scriptene må også legges inni setup.py i entry_points og gjør setup.py kjørbar:

entry_points={
        'console_scripts': [
            # Flight Control
            'offboard_control = sky_vision_ros.offboard_control_node:main',
            # Vision
            'vision_tracker    = sky_vision_ros.vision_tracker_node:main',
            # Video Streaming
            'video_streamer     = sky_vision_ros.video_streamer_node:main',
            'video_streamer_qgc = sky_vision_ros.qgc_video_streamer_node:main',
            # Database
            'database_logger   = sky_vision_ros.database_logger_node:main',
            # Picking
            'picking_manager   = sky_vision_ros.picking_manager_node:main',
        ],
    },

chmod +x ~/sky_vision/src/sky_vision_ros/setup.py

# Nå må alt dette buildes med colcon:
cd ~/sky_vision
colcon build --packages-select sky_vision_ros

# Lage directory (scripts) for å sette alle shell scriptene:
cd ~/sky_vision
mkdir -p ~/sky_vision/scripts
# Sett env.sh inni directory:
mv ~/sky_vision/env.sh ~/sky_vision/scripts/
# Etter å ha laget en annen shell script for drone simulatoren(sånn at du ikke trenger å skrive alle komandoene hver gang), gjør scripten kjørbar:
cd ~/sky_vision/scripts
chmod +x run_px4_sim.sh

# Test