# Installere QGroundControl via android:
https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html

# Åpne appen, gå til appl innstillinger "application settings", skroll ned til "comms links" og lag ny link:
Inni appen: 
Application Settings >> Comm Links >> Links >> Add New Link > Add 
Navn (AppleFarmDrone)
Type UDP 
Port 14550 
# Den vil finne px4 serveren, men begge må være i samme nettverk (LAN)

# Få både pcen og android enheten til å være på samme nettverk og finn IP-Adresse til androiden

# Sett IP-Adressen i system_config.yaml:
mavlink_target_ip: "192.168.1.13"

# Lukk appen og kjør run_px4_sim.sh på pcen:
cd ~/sky_vision/scripts
./run_px4_sim.sh

# Etter at simulasjonen har kjørt, kan QGC appen åpnes og da vil man kunne styre dronen via appen og se dronen i gz simulatoren

# Vær oppmerksom på at IP-Adressen vil forandre seg
