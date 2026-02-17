<p align="center"><img src="https://github.com/user-attachments/assets/0b4b4762-5eaf-4b14-a8ea-89b3aff7a322" width="450"></p>
<p align="center">
<a href="#application-summary">🇺🇸 Application Summary</a> •
<a href="#sintaxis-english-version">Syntax</a> •
<a href="#meshfest-lite--cli-reference">CLI Reference</a> •
<a href="#architecture-diagram-hf--mesh-hybrid-model">Architecture</a><br>
<p align="center">
<a href="#resumen-en-castellano">🇪🇸 Resumen</a> •
<a href="#sintaxis-version-en-castellano">Sintaxis y Ejemplos</a>
  </p>
</p>



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

# 🇬🇧 Sintaxis & Examples

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
--bridge-mesh-to-vara 30QXT3
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
  --call 30QXT1 \
  --host 127.0.0.1 \
  --port 8100 \
  --bridge-mesh \
  --mesh-host 192.168.1.25:4403 \
  --mesh-want-ack \
  --bridge-mesh-to-vara 30QXT3 \
  --hf-allow-tx-dest-shortname QXT4 \
  --verbose 2
```

---

## 🇪🇸**Resumen de la Aplicación**

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

# MeshFest-Lite – Command Line Options

Interactive chat and file transfer over VARA HF (KISS/TCP) with optional Meshtastic bridge.

---

# 🇪🇸 Sintaxis Versión en Castellano

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
--mesh-allow-dest-shortname QXT3,QXT6
```

---

### `--hf-allow-tx-dest-shortname`

Limita qué comandos `@DEST` pueden transmitirse por HF.

```bash
--hf-allow-tx-dest-shortname QXT4
```

Ejemplo:

```
30QXT3: @QXT3 prueba
```

Será bloqueado.

```
30QXT3: @QXT4 prueba
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

---
# 📖 MeshFest-Lite – CLI Reference

## 🛰 Core HF / VARA Options

| Flag | Type | Default | Description |
|------|------|---------|------------|
| `--call` | string | **required** | Your station callsign (e.g. EA1ABC) |
| `--host` | string | `127.0.0.1` | VARA KISS TCP host |
| `--port` | int | `8100` | VARA KISS TCP port |
| `--axdst` | string | `APVARA` | AX.25 destination field (cosmetic only) |

---

## 📡 Meshtastic Interface

| Flag | Type | Default | Description |
|------|------|---------|------------|
| `--mesh-serial` | string | `None` | Serial device (COMx or /dev/ttyUSB0) |
| `--mesh-host` | string | `None` | Meshtastic IP[:PORT] (default port 4403) |
| `--mesh-dest-id` | string | `None` | Destination NodeId (e.g. !abcdef01) |
| `--mesh-channel-index` | int | `None` | Channel index |
| `--mesh-channel-name` | string | `None` | Channel name |
| `--mesh-want-ack` | flag | `False` | Request ACK when sending to specific node |

---

## 🔒 Security & Policy Controls

| Flag | Type | Default | Description |
|------|------|---------|------------|
| `--mesh-allow-dest-shortname` | string (CSV) | `None` | Allowed Meshtastic shortnames for relay (HF → Mesh). If omitted, any destination is allowed |
| `--hf-allow-tx-dest-shortname` | string (CSV) | `None` | Allowed `@DEST` commands for HF TX. If omitted, any `@DEST` is allowed |

---

## 🔁 Bridge Configuration (VARA ↔ Mesh)

| Flag | Type | Default | Description |
|------|------|---------|------------|
| `--bridge-mesh` | flag | `False` | Enable Meshtastic ↔ VARA bridge |
| `--bridge-mesh-to-vara` | string | `ALL` | VARA destination for traffic coming from Mesh |
| `--bridge-varato-mesh-prefix` | string | `[VARA] ` | Prefix added to VARA → Mesh traffic |
| `--bridge-meshto-vara-prefix` | string | `[MESH] ` | Prefix added to Mesh → VARA traffic |

---

## 📊 Monitoring & Logging

| Flag | Type | Default | Description |
|------|------|---------|------------|
| `--monitor` | flag | `False` | Monitor mode (show readable traffic not addressed to you) |
| `-v`, `--verbose` | int (0/1/2) | `1` | Log level (0=errors, 1=normal, 2=debug) |
| `--log-mode` | enum | `console` | Log destination: `console`, `file`, `both` |
| `--log-file` | string | `meshfest.log` | Log file path (used if log-mode includes file) |

---

## 🌍 Language

| Flag | Type | Default | Description |
|------|------|---------|------------|
| `--lang` | enum (`en`, `es`) | `en` | Interface language |

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
  --call 30QXT1 \
  --bridge-mesh \
  --mesh-host 192.168.1.25:4403 \
  --mesh-want-ack \
  --bridge-mesh-to-vara 30QXT3 \
  --mesh-allow-dest-shortname QXT3,QXT6 \
  --hf-allow-tx-dest-shortname QXT4 \
  --verbose 2
```

---

# 🔐 Traffic Control Model (Quick Overview)

| Direction | Controlled By |
|------------|--------------|
| HF → Mesh relay | `--mesh-allow-dest-shortname` |
| Local HF TX using `@DEST` | `--hf-allow-tx-dest-shortname` |
| Mesh → HF forwarding | `--bridge-mesh-to-vara` |

---

MeshFest-Lite combines:

- HF ARQ transport (VARA HF via KISS TCP)
- Meshtastic IP/Serial interface
- Policy-aware message routing
- Optional traffic filtering for secure hybrid deployments



# 🧠 Architecture Diagram (HF ↔ Mesh Hybrid Model)

```
                    ┌────────────────────────────┐
                    │        MeshFest-Lite       │
                    │  Custom HF + Mesh Router   │
                    └─────────────┬──────────────┘
                                  │
                          HF via KISS TCP
                          (VARA as modem)
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                   │
   ┌────▼────┐                                        ┌────▼────┐
   │  VARA   │                                        │  KISS   │
   │  Modem  │                                        │  TCP    │
   └────┬────┘                                        └────┬────┘
        │                                                   │
        │                                                   │
   ┌────▼───────────────────────────────────────────────────▼────┐
   │                         HF Network                           │
   │            AX.25 Frames + Custom ACK Protocol                │
   └───────────────────────────────────────────────────────────────┘

                                  │
                                  │ Meshtastic (Serial / TCP)
                                  │
                           ┌──────▼──────┐
                           │  Meshtastic │
                           │   Interface │
                           └──────┬──────┘
                                  │
                     ┌────────────▼────────────┐
                     │      LoRa Mesh Network   │
                     │  (Nodes, ShortNames)     │
                     └──────────────────────────┘
```

## Transport Model

MeshFest-Lite uses:

- VARA as **physical/modem layer only**
- KISS TCP for AX.25 framing
- Custom application-layer protocol:
  - `T_MSG`
  - Message ID
  - Sequence number
  - Stop-and-wait ACK handling
  - Retries

It does **NOT** rely on VARA's internal ARQ session management.

---

# 🔁 Message Flow Examples

## 1️⃣ Direct HF Message (Custom Reliable Mode)

User input:
```
EA1XYZ: Hello
```

Flow:
```
User
  ↓
MeshFest
  ↓
AX.25 frame (T_MSG)
  ↓
VARA modem (audio transport)
  ↓
Remote station
  ↓
Custom ACK returned
```

Reliability is handled by:

- `_send_with_ack()`
- Custom ACK tracking
- Application-level retransmission

---

## 2️⃣ HF Relay to Mesh (Using @DEST)

User input:
```
30QXT3: @QXT4 test message
```

Flow:
```
Local User
   ↓
MeshFest
   ↓
AX.25 T_MSG frame
   ↓
HF Relay (30QXT3)
   ↓
Relay parses ">QXT4:"
   ↓
Meshtastic node QXT4
```

Security control:

- `--hf-allow-tx-dest-shortname`
- `--mesh-allow-dest-shortname`

---

## 3️⃣ Mesh to HF Forwarding

```
Mesh Node
   ↓
Meshtastic Interface
   ↓
MeshFest Bridge
   ↓
AX.25 frame
   ↓
HF transmission
```

Transport reliability on HF:

- Application-layer ACK
- Configurable retries
- Stop-and-wait logic

---

# 📦 File Transfer Workflow (Custom Reliable Layer)

MeshFest-Lite file transfer uses:

- Fragmentation
- Message IDs
- Sequence numbers
- Custom ACK handling
- Retries

## HF File Transfer Model

```
File
  ↓
Chunked into payload blocks
  ↓
Each block sent as T_MSG
  ↓
ACK received
  ↓
Next block
```

This is **application-controlled reliability**, independent of VARA ARQ.

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

## Deployment Modes

| Mode | Description |
|------|------------|
| Transparent HF Node | AX.25 custom reliable messaging |
| Controlled Relay | Policy-based forwarding |
| Hybrid Gateway | HF ↔ Mesh bridge |
| Secure Bridge | Allowlist filtering enabled |

---

MeshFest-Lite is a:

**Custom reliable messaging engine over HF + LoRa mesh integration layer**

Not just a chat client, and not dependent on VARA’s native ARQ sessions.

