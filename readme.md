# MesHFest


What is MesHFest?

[English Summary](https://github.com/QuixoteSystems/meshfest-lite?tab=readme-ov-file#-meshfest--application-summary) 

¿Qué es MesHFest?

[Resumen en castellano](https://github.com/QuixoteSystems/meshfest-lite/edit/main/readme.md#-meshfest--resumen-de-la-aplicaci%C3%B3n)

---
## 🇺🇸 **Application Summary**

MesHFest is a lightweight communication bridge designed to interconnect Meshtastic networks with HF digital modes such as VARA HF and JS8Call, enabling seamless message forwarding between radio and mesh infrastructures.

The application acts as an intelligent gateway that can relay, format, acknowledge, and route messages between different technologies, allowing stations operating on HF to communicate with Meshtastic nodes and vice versa.

MesHFest Lite is a simplified version designed to run as a service or as a simple bridge/chat, making it ideal for unattended stations, portable deployments, or minimal setups where stability and low resource usage are key.

Key features include:
- Bidirectional message bridging (Mesh ⇄ HF)
- Automatic forwarding and acknowledgment handling
- Callsign-aware routing logic
- Lightweight and service-friendly architecture
- Designed for experimentation, emergency comms, and hybrid RF networks

MesHFest enables the creation of hybrid communication ecosystems where LoRa mesh and HF digital radio coexist and complement each other.

---

## 🇪🇸 **Resumen de la Aplicación**

MesHFest es un puente de comunicaciones ligero diseñado para interconectar redes Meshtastic con modos digitales en HF como VARA HF y JS8Call, permitiendo el reenvío transparente de mensajes entre infraestructuras de radio y redes mesh.

La aplicación actúa como una pasarela inteligente capaz de reenviar, formatear, confirmar y enrutar mensajes entre distintas tecnologías, permitiendo que estaciones en HF puedan comunicarse con nodos Meshtastic y viceversa.

MesHFest Lite es una versión simplificada pensada para ejecutarse como servicio o como un puente/chat sencillo, ideal para estaciones desatendidas, despliegues portátiles o configuraciones mínimas donde la estabilidad y el bajo consumo de recursos son prioritarios.

Características principales:
- Puente bidireccional de mensajes (Mesh ⇄ HF)
- Gestión automática de reenvíos y confirmaciones
- Lógica de enrutado basada en indicativos
- Arquitectura ligera orientada a ejecución como servicio
- Diseñado para experimentación, comunicaciones de emergencia y redes RF híbridas

MesHFest permite crear ecosistemas de comunicación híbridos donde LoRa mesh y radio digital en HF conviven y se complementan.


# Parameters (Flags)
## PARÁMETRO OBLIGATORIO 

```
--call EA1ABC
```
Tu indicativo, por ejemplo: EA1ABC

--- 
## CONFIGURACIÓN VARA HF (KISS/TCP) 
```
--host 127.0.0.1
```
Host KISS TCP (VARA).
Valor por defecto: 127.0.0.1
```
--port 8100
```
Puerto KISS TCP (VARA).
Valor por defecto: 8100
```
--axdst FEST
```
Campo destino AX.25 (cosmético).
Valor por defecto: APVARA
---
## CONFIGURACIÓN MESHTASTIC 
```
--mesh-serial /dev/ttyUSB0
```
Puerto serie de Meshtastic (COMx o /dev/ttyUSB0)

```
--mesh-host 192.168.1.11:4403
```
IP[:PUERTO] de Meshtastic (puerto por defecto 4403)

```
--mesh-dest-id !abcdef01
```
DestinationId (ejemplo: !abcdef01) para enviar a un nodo concreto

```
--mesh-dest-shortname MSH6
```
ShortName del nodo destino (ejemplo: MSH6)


```
--mesh-channel-index 0
```
Canal de Meshtastic (índice) número entero

```
--mesh-channel-name MediumFast
```
Canal de Meshtastic (nombre)

```
--mesh-want-ack
```
Solicitar ACK cuando se envía a un nodo concreto (destinationId)
---
## OPCIONES DE BRIDGE 

```
--bridge-mesh
```
Activa el bridge Meshtastic ↔ VARA

```
--bridge-varato-mesh-prefix
```
Prefijo para lo que sale de VARA hacia Mesh
Valor por defecto: [VARA]

```
--bridge-meshto-vara-prefix
```
Prefijo para lo que sale de Mesh hacia VARA
Valor por defecto: [MESH]

```
--bridge-mesh-to-vara
```
Destino en VARA para lo que venga de Mesh (ALL o CALL)
Valor por defecto: ALL
---

## MONITORIZACIÓN Y LOG

```
--monitor
```
Modo monitor: muestra mensajes legibles aunque no vayan dirigidos a mí o a ALL (sin ACK)
```
-v / --verbose
```
Nivel de log:
0 = solo errores
1 = normal
2 = debug

```
--log-mode console
```
Destino del log. Opciones: console, file o both
Valor por defecto: console

```
--log-file /home/user/meshfest-lite/
```
Ruta del fichero de log (si --log-mode incluye file)
Valor por defecto: meshfest.log

---
## IDIOMA 

```
--lang
```
Idioma de los mensajes:
es = castellano
en = inglés
Valor por defecto: en

---

## EJEMPLOS 

- Mensajeria entre Estaciones VARA, sin Bridge con Meshtastic:
  
```python meshfest-lite.py --call EA1ABC --host 127.0.0.1 --port 8100```

- Modo Monitor:

```python meshfest-lite.py --call EA1ABC --host 127.0.0.1 --port 8100 --monitor```

- Bridge entre Nodo y Nodo Mesh <-> VARA <-> Mesh con MONITOR:

```python meshfest-lite.py --call EA1ABC --bridge-mesh --mesh-host 192.168.1.25:4403 --mesh-dest-shortname QXT6 --mesh-want-ack --bridge-mesh-to-vara EA9YXZ --monitor```

- Bridge de Nodo a Canal con un destino Indicativo:

```python meshfest-lite.py --call EA1ABC --bridge-mesh --mesh-host 192.168.1.25:4403 --mesh-channel-name MediumFast --mesh-want-ack --bridge-mesh-to-vara EA9XYZ```

Si EA9XYZ envia a EA1ABC esta lo reenviara al Canal MediumFast.


- Bridge de Nodo a Canal para ALL (todos los indicativos):

```python meshfest-lite.py --call EA1ABC --bridge-mesh --mesh-host 192.168.1.11:4403 --mesh-channel-name Familia --mesh-want-ack```


- Mensajeria con log en pantalla y archivo verbose y en una ruta especifica:

```python meshfest-lite.py --call EA1ABC --host 127.0.0.1 --port 8100 --log-mode both --verbose 2 --log-file C:\temp\meshfest.log ```
