QGroundControl installasjon (For kontroll ved android/ios) 

For å installere nyeste versjon av QGroundControl som er stabil og som inkluderer de nye funksjonene: 

wget https://d176tv9ibo4jno.cloudfront.net/builds/master/QGroundControl-x86_64.AppImage 

Dette må gjøres kjørbar ved : chmod +x QGroundControl-x86_64.AppImage 

For å kjøre QGroundControl via terminalen: ./QGroundControl-x86_64.AppImage. Disse systemene må velges, metric system, firmware (PX4 Pro) og vehicle (Multi-Rotor). Programmet må lukkes og åpne på nytt for de nye funksjonene skal utnyttes. 

For android: 

Installere QGroundControl via android: https://docs.qgroundcontrol.com/master/en/qgc-user-guide/getting_started/download_and_install.html 

Etter installasjonen må de samme systemene velges som for pcen. 

For å få konfigurere px4 autopilot til å høre og koble til android Q: 

1. cd ~/PX4-Autopilot/ 

2. make px4_sitl gz_x500 

Inni den samme terminalen: 

pxh>  

mavlink status 

mavlink stop-all && 

mavlink start -u 14550 -t 192.168.11.32 -r 4000 

-u 14550 er local UDP port 

-t 192.168.11.32 din android IP 

-r 4000 er data hastighet 

Inni appen: 

Application Settings >> Comm Links >> Links >> Add New Link > Add 

navn 

Type UDP 

Port 14550 

save 

Den vil finne px4 serveren, men begge må være i samme LAN. 

Lage en fil nano my_px4_start.sh og sett inn: 

PX4_SYS_AUTOSTART=4002 \  

PX4_GZ_MODEL_POSE="0,0" \  

PX4_GZ_MODEL=x500_depth \  

./build/px4_sitl_default/bin/px4 -i 1 << EOF   

mavlink stop-all mavlink start -u 14550 -t 192.168.10.51 -r 4000  

EOF 

Filen skal gjøres kjørbar ved chmod +x my_px4_start.sh, så kan filen kjøres ved ./my_px4_start.sh 

Forklaring av koden: 

PX4_SYS_AUTOSTART=4002: Setter airframe ID for drone modellen, ID er 4002. 

PX4_GZ_MODEL_POSE="0,0": Bestemmer start posisjon (x,y) i gazebo verden(simulatoren). Når disse verdiene er bestemt, vil de andre z, roll, yaw settes som standard altså til 0. 

PX4_GZ_MODEL= x500_depth: Definerer gazebo modellen som skal brukes. Denne modellen er for x500 quadrotor med en depth kamera. 

./build/px4_sitl_default/bin/px4: stien til kompilering av PX4 SITL som er kjørbar. 

-i 1: spesifiserer instans nummer 1, dette er nyttig for fler kjørtøy simulatorer for å sikre unik port tildeling. 

mavlink stop-all: rydder opp/sletter alt standard MAVLink som kan ha konflik med tilpasset konfigurasjon. 

MAVLink start: initialiserer en ny kommunikasjonsinstans. 