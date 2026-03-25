# ~/sky_vision/scripts/run_px4_sim.sh

# you need to make the script executable by running
# chmod +x ~/sky_vision/scripts/run_px4_sim.sh
# ~/sky_vision/scripts/run_px4_sim.sh
#!/bin/bash

# ==========================================
# 1. Cleanup Previous Instances
# ==========================================
pkill -f MicroXRCEAgent || true
pkill -f gz || true
pkill -f px4 || true
sleep 2

cd ~/PX4-Autopilot || exit 1

# ==========================================
# 2. Micro XRCE-DDS Agent
# ==========================================
gnome-terminal -- bash -c "
source ~/sky_vision/scripts/env.sh;
echo 'Starting MicroXRCEAgent...';
MicroXRCEAgent udp4 -p 8888;
exec bash
" &

sleep 3

# ==========================================
# 3. Dynamic Camera Bridge
# ==========================================
gnome-terminal -- bash -c "
source ~/sky_vision/scripts/env.sh;
echo 'Waiting for Gazebo to publish camera topics...';

while true; do
    # Dynamically find the image topic 
    CAMERA_TOPIC=\$(gz topic -l | grep -E '/sensor/.*image' | head -n 1)

    if [ -n \"\$CAMERA_TOPIC\" ]; then
        echo \"✅ Found Camera: \$CAMERA_TOPIC\"
        break
    fi
    sleep 1
done

echo 'Starting Image Bridge...'
ros2 run ros_gz_image image_bridge \$CAMERA_TOPIC
exec bash
" &

sleep 2

# ==========================================
# 4. PX4 SITL + Gazebo Harmonic
# ==========================================
gnome-terminal -- bash -c "
cd ~/PX4-Autopilot;
echo 'Starting PX4 SITL & Gazebo Harmonic...';

CONFIG_FILE=~/sky_vision/config/system_config.yaml

TARGET_SYS=\$(grep 'px4_target_system:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')
MAVLINK_IP=\$(grep 'mavlink_target_ip:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')

# export PX4_HOME_LAT=\$(grep 'px4_home_lat:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')
# export PX4_HOME_LON=\$(grep 'px4_home_lon:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')
# export PX4_HOME_ALT=\$(grep 'px4_home_alt:' \$CONFIG_FILE | cut -d '#' -f 1 | awk -F ':' '{print \$2}' | tr -d ' \"')

# CHANGED MODEL TO GIMBAL
PX4_SYS_AUTOSTART=4019 \\
PX4_GZ_MODEL_POSE=\"0,0\" \\
PX4_GZ_MODEL=x500_gimbal \\
PX4_GZ_WORLD=apple_orchard_100x75_grasspatch_no_collision_v3 \\
./build/px4_sitl_default/bin/px4 -i \$TARGET_SYS << EOF

mavlink stop-all
mavlink start -u 14550 -t \$MAVLINK_IP -r 4000
param set COM_ARM_WO_GPS 1
param set MNT_MODE_IN 4
EOF
exec bash
" &

sleep 8 

# ==========================================
# 5. PX4 Sensor Listeners
# ==========================================
gnome-terminal -- bash -c "
source ~/sky_vision/scripts/env.sh
echo 'Starting PX4 sensor listeners...';
ros2 run px4_ros_com sensor_combined_listener;
exec bash
" &