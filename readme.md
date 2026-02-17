![meshfest-lite-v1](https://github.com/user-attachments/assets/47a2aec6-0193-45ea-89e2-839fcbd40c36)

## Index


🇺🇸 [Application Summary](#application-summary) • [Architecture Diagram](#architecture-diagram-hf--mesh-hybrid-model) • [CLI Reference](#meshfest-lite--cli-reference) • [Syntax & Examples](#sintaxis--examples)

🇪🇸 [Resumen de la Aplicación](#resumen-en-castellano) • [Sintaxis y Ejemplos](#sintaxis-version-en-castellano)


---

## **Application Summary**

MesHFest-lite is a lightweight & simple communication bridge designed to interconnect Meshtastic networks with HF digital modes such as VARA HF (and still not JS8Call), enabling seamless message forwarding between radio and mesh infrastructures.

The application acts as an intelligent gateway that can relay, format, acknowledge, and route messages between different technologies, allowing stations operating on HF to communicate with Meshtastic nodes and vice versa.

MesHFest-lite is a simplified version (one file) designed to run as a service or as a simple bridge/chat, making it ideal for unattended stations, portable deployments, or minimal setups where stability and low resource usage are key.

Key features include:
- Bidirectional message bridging (Mesh <-> HF)
- Automatic forwarding and acknowledgment handling
- Callsign-aware routing logic
- Lightweight and service-friendly architecture
- Designed for experimentation, emergency comms, and hybrid RF networks
- Send and receive files from station to station (not to Meshtastic).

MesHFest enables the creation of hybrid communication ecosystems where Meshtastic and HF digital radio coexist and complement each other.

---


# 🧠 Architecture Diagram (HF ↔ Mesh Hybrid Model)


```
           ~~~~~~~~~~~~~ HF RF LINK ~~~~~~~~~~~~~
             (AX.25 + QXT1 ACK Protocol Layer)
               │                          │
         ┌─────▼─────┐              ┌─────▼─────┐
         │  VARA HF  │              │  VARA HF  │
         │  Modem A  │              │  Modem B  │
         └─────┬─────┘              └─────┬─────┘
               │                          │
           KISS TCP                     KISS TCP
               │                          │
  ┌────────────▼─────────┐          ┌─────▼────────────────┐
  │    MeshFest-Lite     │          │    MeshFest-Lite     │
  │  HF ↔ Mesh Router A  │          │  HF ↔ Mesh Router B  │
  └────────────┬─────────┘          └──────────┬───────────┘
               │                               │
           Meshtastic                      Meshtastic
           Interface A                    Interface B
               │                               │
        ┌──────▼──────┐                  ┌──-──▼──────┐
        │ LoRa Mesh A │                  │ LoRa Mesh B│
        │ (Nodes)     │                  │ (Nodes)    │
        └─────────────┘                  └────────────┘
        
```

---

# 🔎 Logical Flow

```
Meshtastic <---> MeshFest-lite <---> VARA HF ((( HF ))) VARA HF <--->  MeshFest-lite <---> Meshtastic
```

---

# 📡 Transport Stack (Top → Bottom)

HF Backbone:
- VARA as modem (transport only)
- KISS TCP 
- AX.25 framing
- QXT1 application ACK (stop-and-wait, retries)

Gateway Layer:
- MeshFest-Lite routing engine
- Policy enforcement
- Relay tagging (`>DEST:`)

Access Layer:
- Meshtastic interface (Serial / TCP)
- Meshtastic Mesh


## Transport Model

MeshFest-Lite uses:

- VARA as **physical/modem layer only**
- KISS TCP for AX.25 framing
- QXT1 application-layer protocol:
  - `T_MSG`
  - Message ID
  - Sequence number
  - Stop-and-wait ACK handling
  - Retries

It does **NOT** rely on VARA's internal ARQ session management, this allow to use transceivers without CAT control, just using VOX.

---

# Sintaxis & Examples

To exit the program, type `exit` or press `Ctrl+C`.

## 1️⃣ Core HF / VARA Configuration

### `--call` (required)
Your station callsign.

Example:
```bash
--call EA1ABC
```

---

### `--host`
KISS TCP host (usually VARA running locally).  
Default: `127.0.0.1`

```bash
--host 127.0.0.1
```

---

### `--port`
KISS TCP port used by VARA.  
Default: `8100`

```bash
--port 8100
```

---

### `--axdst`
AX.25 destination field (cosmetic only).  
Default: `APVARA`

```bash
--axdst APVARA
```

---

## 2️⃣ Meshtastic Interface Configuration

### `--mesh-serial`
Serial device for Meshtastic.

```bash
--mesh-serial /dev/ttyUSB0
```

Windows:
```bash
--mesh-serial COM5
```

---

### `--mesh-host`
Connect to Meshtastic via TCP.  
Default port: `4403`

```bash
--mesh-host 192.168.1.25:4403
```

---

### `--mesh-dest-id`
Send directly to a specific node ID.

```bash
--mesh-dest-id !abcdef01
```

---

### `--mesh-channel-index`
Select channel by index.

```bash
--mesh-channel-index 1
```

---

### `--mesh-channel-name`
Select channel by name.

```bash
--mesh-channel-name "LongFast"
```

---

### `--mesh-want-ack`
Request ACK when sending to a specific node.

```bash
--mesh-want-ack
```

---

## 3️⃣ Security & Policy Controls

### `--mesh-allow-dest-shortname`

Restricts which Meshtastic shortnames can be used as relay destinations (HF → Mesh).

```bash
--mesh-allow-dest-shortname QXT3,QXT6
```

If omitted, any destination is allowed.

---

### `--hf-allow-tx-dest-shortname`

Restricts which `@DEST` commands can be transmitted over HF.

```bash
--hf-allow-tx-dest-shortname QXT4
```

Example:

If running with:

```bash
--hf-allow-tx-dest-shortname QXT4
```

Then:

```
30QXT3: @QXT3 test
```

Will be blocked.

But:

```
30QXT3: @QXT4 test
```

Will be transmitted.

---

## 4️⃣ Bridge Configuration (VARA ↔ Meshtastic)

### `--bridge-mesh`
Enable Meshtastic ↔ VARA bridging.

```bash
--bridge-mesh
```

---

### `--bridge-mesh-to-vara`
VARA destination for traffic coming from Mesh.  
Default: `ALL`

```bash
--bridge-mesh-to-vara EA1ABC
```

---

### `--bridge-varato-mesh-prefix`
Prefix for traffic from VARA to Mesh.

```bash
--bridge-varato-mesh-prefix "[VARA HF] "
```

---

### `--bridge-meshto-vara-prefix`
Prefix for traffic from Mesh to VARA.

```bash
--bridge-meshto-vara-prefix "MESHTASTIC "
```

---

## 5️⃣ Monitoring & Logging

### `--monitor`
Monitor mode (shows readable traffic not addressed to you).

```bash
--monitor
```

---

### `-v / --verbose`

Log level:

- `0` = errors  
- `1` = normal  
- `2` = debug  

```bash
-v 2
```

---

### `--log-mode`

Options:
- `console`
- `file`
- `both`

```bash
--log-mode both
```

---

### `--log-file`

Log file path.  
Default: `meshfest.log`

```bash
--log-file mylog.txt
```

---

## 6️⃣ Language

### `--lang`

Interface language:

- `en`
- `es`

```bash
--lang es
```

---

## 🔧 Full Example

```bash
python meshfest-lite.py \
  --call EA1ABC \
  --host 127.0.0.1 \
  --port 8100 \
  --bridge-mesh \
  --mesh-host 192.168.1.25:4403 \
  --mesh-want-ack \
  --bridge-mesh-to-vara EA9XYZ \
  --hf-allow-tx-dest-shortname MSH4 \
  --verbose 2
```


---

# 🧪 Example Configurations

## Minimal HF Mode

```bash
python meshfest-lite.py \
  --call EA1ABC \
  --host 127.0.0.1 \
  --port 8100
```

---

## Full Bridge with Security Policy

```bash
python meshfest-lite.py \
  --call EA1ABC \
  --bridge-mesh \
  --mesh-host 192.168.1.25:4403 \
  --mesh-want-ack \
  --bridge-mesh-to-vara EA9XYZ \
  --mesh-allow-dest-shortname MSH3,MSH6 \
  --hf-allow-tx-dest-shortname MSH4 \
  --verbose 2
```

---

# 📦 File Transfer Workflow (Custom Reliable Layer)

MeshFest-Lite file transfer uses:

- Fragmentation
- Message IDs
- Sequence numbers
- Custom ACK handling
- Retries

---

# 🧩 Advanced Usage / Network Design Notes

## Custom Reliability Layer

MeshFest-Lite implements its own:

- Stop-and-wait protocol
- Message tracking
- ACK validation
- Retry logic
- Delivery confirmation logs

This allows:

- Deterministic routing
- Policy-based forwarding
- Hybrid network bridging
- Fine-grained control over message flow

---

## Why Not Native VARA ARQ?

Using KISS + custom protocol allows:

- Full control of routing logic
- Embedded metadata
- Relay tagging (`>DEST:` format)
- Multi-hop style relaying
- Hybrid mesh/HF policy enforcement

It turns VARA into a **transparent transport layer**, not a session controller.

---

## 🇪🇸**Resumen de la Aplicación**

MesHFest es un puente de comunicaciones ligero diseñado para interconectar redes Meshtastic con modos digitales en HF como VARA HF (y todavía no JS8Call), permitiendo el reenvío transparente de mensajes entre infraestructuras de radio y redes Meshtastic.

La aplicación actúa como una pasarela inteligente capaz de reenviar, formatear, confirmar y enrutar mensajes entre distintas tecnologías, permitiendo que estaciones en HF puedan comunicarse con nodos Meshtastic y viceversa.

MesHFest Lite es una versión simplificada pensada para ejecutarse como servicio o como un puente/chat sencillo, ideal para estaciones desatendidas, despliegues portátiles o configuraciones mínimas donde la estabilidad y el bajo consumo de recursos son prioritarios.

Características principales:
- Puente bidireccional de mensajes (Mesh ⇄ HF)
- Gestión automática de reenvíos y confirmaciones
- Lógica de enrutado basada en indicativos
- Arquitectura ligera orientada a ejecución como servicio
- Diseñado para experimentación, comunicaciones de emergencia y redes RF híbridas

MesHFest permite crear ecosistemas de comunicación híbridos donde LoRa mesh y radio digital en HF conviven y se complementan.

# MeshFest-Lite – Command Line Options

Interactive chat and file transfer over VARA HF (KISS/TCP) with optional Meshtastic bridge.

---

# Sintaxis y Ejemplos

## 1️⃣ Configuración HF / VARA

### `--call` (obligatorio)
Indicativo de tu estación.

```bash
--call EA1ABC
```

---

### `--host`
IP del servidor KISS (VARA).  
Por defecto: `127.0.0.1`

---

### `--port`
Puerto TCP de VARA.  
Por defecto: `8100`

---

### `--axdst`
Campo destino AX.25 (solo estético).  
Por defecto: `APVARA`

---

## 2️⃣ Configuración Meshtastic

### `--mesh-serial`
Puerto serie USB.

```bash
--mesh-serial /dev/ttyUSB0
```

---

### `--mesh-host`
Conexión por red.

```bash
--mesh-host 192.168.1.25:4403
```

---

### `--mesh-dest-id`
Enviar a un NodeId concreto.

```bash
--mesh-dest-id !abcdef01
```

---

### `--mesh-channel-index`
Seleccionar canal por índice.

---

### `--mesh-channel-name`
Seleccionar canal por nombre.

---

### `--mesh-want-ack`
Solicitar ACK al enviar a un nodo específico.

---

## 3️⃣ Controles de Seguridad

### `--mesh-allow-dest-shortname`

Limita qué nodos Meshtastic pueden recibir tráfico reenviado desde HF.

```bash
--mesh-allow-dest-shortname MSH3,MSH6
```

---

### `--hf-allow-tx-dest-shortname`

Limita qué comandos `@DEST` pueden transmitirse por HF.

```bash
--hf-allow-tx-dest-shortname MSH4
```

Ejemplo:

```
EA1ABC: @MSH3 prueba
```

Será bloqueado.

```
EA1ABC: @MSH4 prueba
```

Será transmitido.

---

## 4️⃣ Configuración del Bridge

### `--bridge-mesh`
Activa el bridge Meshtastic ↔ VARA.

---

### `--bridge-mesh-to-vara`
Destino VARA para tráfico procedente de la malla.

---

### `--bridge-varato-mesh-prefix`
Prefijo VARA → Mesh.

---

### `--bridge-meshto-vara-prefix`
Prefijo Mesh → VARA.

---

## 5️⃣ Monitorización y Logs

### `--monitor`
Modo monitor.

---

### `--verbose`
Nivel de log (0, 1, 2).

---

### `--log-mode`
Destino del log (console, file, both).

---

### `--log-file`
Archivo de log.

---

## 6️⃣ Idioma

### `--lang`
Idioma de la interfaz (`es` o `en`).



