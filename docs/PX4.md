PX4-Autopilot implementering 

PX4 Autopilot og ROS2-integrasjon  

For å integrere PX4 Autopilot med ROS2 Jazzy ble et utviklingsmiljø etablert på Ubuntu 22.04, med fokus på Software-In-The-Loop (SITL) simulering i Gazebo. Denne oppsettet muliggjør sanntidskommunikasjon mellom PX4 og ROS2-noder via Micro XRCE-DDS, essensielt for dronebaserte inspeksjonsoppgaver i eplehagen. 

PX4-oppsett  

PX4-Autopilot ble klonet med submodules for å sikre alle avhengigheter: 

    cd ~ 

    git clone https://github.com/PX4/PX4-Autopilot.git --recursive 

    bash ./PX4-Autopilot/Tools/setup/ubuntu.sh 

    cd PX4-Autopilot/ 

    make px4_sitl  

Dette installerer simulatoren og verifiserer kompatibilitet med Ubuntu-versjonen. Uten --recursive ville submodules som Gazebo mangles, noe som fører til build-feil. 

Micro XRCE-DDS Agent  

Agenten (v2.4.3, kompatibel med Jazzy) ble bygget i en ROS2-workspace for å utnytte eksisterende avhengigheter som FastCDR og FastDDS: 

    mkdir -p ~/px4_ros_uxrce_dds_ws/src 

    cd ~/px4_ros_uxrce_dds_ws/src 

    git clone -b v2.4.3 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git 

    source /opt/ros/jazzy/setup.bash 

    colcon build 

Output viste normal submodule-kloning (stderr-advarsel er ufarlig). Miljøet sourcet permanent: 

    echo "source ~/px4_ros_uxrce_dds_ws/install/setup.bash" >> ~/.bashrc 

    source ~/.bashrc  

Agent startes med: MicroXRCEAgent udp4 -p 8888. 

Integrert testing 

PX4 kjøres med ROS2-bro: ROS_DOMAIN_ID=3 PX4_UXRCE_DDS_PORT=9999 PX4_UXRCE_DDS_NS=drone make px4_sitl gz_x500 eller make px4_sitl gz_x500 . Topics listes med ros2 topic list, bekreftende broen mellom PX4 og YOLO/Gazebo-noder. 

Denne implementeringen støtter modulær dronekontroll i inspeksjonssystemet, med lav latens DDS-kommunikasjon. 