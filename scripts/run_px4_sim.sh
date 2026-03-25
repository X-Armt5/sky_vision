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

