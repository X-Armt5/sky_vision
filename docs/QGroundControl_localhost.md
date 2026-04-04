# Endre "mavlink target" til localhost i "system_config.yaml":
mavlink_target_ip: "127.0.0.1"

# Terminal 1: SITL
PX4_GZ_WORLD=apple_orchard make px4_sitl gz_x500_gimbal

# Terminal 2: QGC
./QGroundControl-x86_64.AppImage


#### ELLER set disse comandoene som komentarer i "run_px4_sim.sh":

mavlink stop-all
mavlink start -u 14550 -t \$MAVLINK_IP -r 4000
param set COM_ARM_WO_GPS 1
param set MNT_MODE_IN 4

# Kjør "run_px4_sim.sh":

cd ~/sky_vision/scripts/
./run_px4_sim.sh

# Så må "QGroundControl-x86_64.AppImage" kjøres i en annen terminal:

cd ~

./QGroundControl-x86_64.AppImage

# Nå skal man kunne kontrollere drone via QGC og se dronen bevege seg i gz simulasjonen
