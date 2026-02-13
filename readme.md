## PARÁMETRO OBLIGATORIO 

--call
Tu indicativo, por ejemplo: EA1ABC

--- 
## CONFIGURACIÓN VARA HF (KISS/TCP) 

--host
Host KISS TCP (VARA).
Valor por defecto: 127.0.0.1

--port
Puerto KISS TCP (VARA).
Valor por defecto: 8100

--axdst
Campo destino AX.25 (cosmético).
Valor por defecto: APVARA
---
## CONFIGURACIÓN MESHTASTIC 

--mesh-serial
Puerto serie de Meshtastic (COMx o /dev/ttyUSB0)

--mesh-host
IP[:PUERTO] de Meshtastic (puerto por defecto 4403)

--mesh-dest-id
DestinationId (ejemplo: !abcdef01) para enviar a un nodo concreto

--mesh-dest-shortname
ShortName del nodo destino (ejemplo: QXT6)

--mesh-channel-index
Canal de Meshtastic (índice)

--mesh-channel-name
Canal de Meshtastic (nombre)

--mesh-want-ack
Solicitar ACK cuando se envía a un nodo concreto (destinationId)
---
## OPCIONES DE BRIDGE 

--bridge-mesh
Activa el bridge Meshtastic ↔ VARA

--bridge-varato-mesh-prefix
Prefijo para lo que sale de VARA hacia Mesh
Valor por defecto: [VARA]

--bridge-meshto-vara-prefix
Prefijo para lo que sale de Mesh hacia VARA
Valor por defecto: [MESH]

--bridge-mesh-to-vara
Destino en VARA para lo que venga de Mesh (ALL o CALL)
Valor por defecto: ALL
---

## MONITORIZACIÓN Y LOG

--monitor
Modo monitor: muestra mensajes legibles aunque no vayan dirigidos a mí o a ALL (sin ACK)

-v / --verbose
Nivel de log:
0 = solo errores
1 = normal
2 = debug

--log-mode
Destino del log: console, file o both
Valor por defecto: console

--log-file
Ruta del fichero de log (si --log-mode incluye file)
Valor por defecto: meshfest.log

---
## IDIOMA 

--lang
Idioma de los mensajes:
es = castellano
en = inglés
Valor por defecto: en

---

# EJEMPLOS 
- Mensajeria entre Estaciones, sin Bridge:
python meshfest-lite.py --call EA1ABC --host 127.0.0.1 --port 8100

- Modo Monitor:

python meshfest-lite.py --call EA1ABC --host 127.0.0.1 --port 8100 --monitor

- Bridge entre Nodo y Nodo Mesh <-> VARA <-> Mesh con MONITOR:

python meshfest-lite.py --call EA1ABC --bridge-mesh --mesh-host 192.168.1.25:4403 --mesh-dest-shortname QXT6 --mesh-want-ack --bridge-mesh-to-vara 30QXT3 --monitor

- Bridge de Nodo a Canal con un destino Indicativo:

python meshfest-lite.py --call EA1ABC --bridge-mesh --mesh-host 192.168.1.25:4403 --mesh-channel-name Familia --mesh-want-ack --bridge-mesh-to-vara EA9XYZ

Si 30qxt3 envia a 30qxt1 esta lo reenviara al Canal Familia.
--> Probar si puede reenviar 30qxt2
---------------------------------

- Bridge de Nodo a Canal para ALL (todos los indicativos):

python meshfest-lite.py --call EA1ABC --bridge-mesh --mesh-host 192.168.1.25:4403 --mesh-channel-name Familia --mesh-want-ack


- Mensajeria con log en pantalla y archivo verbose y en una ruta especifica:

python meshfest-lite.py --call EA1ABC --host 127.0.0.1 --port 8100 --log-mode both --verbose 2 --log-file C:\temp\meshfest.log
