#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import queue
import socket
import struct
import threading
import time
import zlib
import re
import hashlib
from datetime import datetime
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, Any, List

# ---------------- KISS constants ----------------
FEND  = 0xC0
FESC  = 0xDB
TFEND = 0xDC
TFESC = 0xDD

# ---------------- AX.25 UI constants ----------------
AX25_UI  = 0x03
AX25_PID = 0xF0

# ---------------- App protocol ----------------
MAGIC = b"QXT1"  # 4 bytes
T_MSG  = 1
T_ACK  = 2
T_FILE = 3
T_FEND = 4  # file end

# MAGIC(4) | TYPE(1) | FLAGS(1) | SRC(10) | DST(10) | MSGID(4) | SEQ(2) | TOT(2) | PAYLEN(2) | CRC32(4)
HDR_FMT = "!4sBB10s10sIHHHI"
HDR_LEN = struct.calcsize(HDR_FMT)

FLAG_BROADCAST = 0x01

# ---------------- Colores en Texto App para no utilizar dependencias

ANSI_RED = "\x1b[31m"
ANSI_GREEN = "\x1b[32m"
ANSI_YELLOW = "\x1b[33m"
ANSI_CYAN = "\x1b[36m"
ANSI_MAGENTA = "\x1b[35m"
ANSI_RESET = "\x1b[0m"

def c_tx(s: str) -> str: return f"{ANSI_RED}{s}{ANSI_RESET}"
def c_rx(s: str) -> str: return f"{ANSI_GREEN}{s}{ANSI_RESET}"
def c_info(s: str) -> str: return f"{ANSI_CYAN}{s}{ANSI_RESET}"
def c_warn(s: str) -> str: return f"{ANSI_YELLOW}{s}{ANSI_RESET}"
def c_err(s: str) -> str: return f"{ANSI_MAGENTA}{s}{ANSI_RESET}"

# ---------------- Tunables
MAX_PAYLOAD = 180        # bytes per file chunk
#ACK_TIMEOUT = 30.0        # seconds
MAX_RETRIES = 3

# --- Adaptive ACK timeout tuning ---
MIN_ACK_TIMEOUT = 25.0       # mínimo, aunque el mensaje sea pequeño
MAX_ACK_TIMEOUT = 90.0      # máximo, para que no se eternice
BASE_ACK_TIMEOUT = 6.0      # margen base (turnaround/cola/ARQ)
ACK_MARGIN = 6.0            # margen extra fijo
#EST_BYTES_PER_SEC = 61.0    # estimación conservadora VARA HF (ajustable)
RTT_MULT = 2.0              # multiplica el RTT estimado para timeout
EWMA_ALPHA = 0.25           # suavizado (0.1-0.3 suele ir bien)
DEFAULT_RTT = 35.0
EFFICIENCY = 0.5            # eficiencia útil HF
EST_BITS_PER_SEC = 61.0     # lo que has medido/configurado


# ------------ LANG TEXTS -------------
TEXTS = {
    "es": {
        "connected_vara": "[INFO] ✅ Conectado a VARA HF {host}:{port}",
        "retry_no_ack": "[RETRY] ⚠️ Sin ACK de {dst} tras {timeout:.0f}s "
                        "(msgid={msgid} seq={seq} len={payload_len}) "
                        "intento {attempt}/{max_retries}",
        "fail_no_ack": "[FAIL] ❌ Sin ACK tras {max_retries} reintentos: {dst} msgid={msgid} seq={seq}",
        "err_invalid_format": "[ERR] ❌ Formato inválido. Usa 'ALL: mensaje' o 'CALL: mensaje'",
        "ack_dm": "[ACK DM] ✅ Mensaje confirmado por {dst}",
        "fail_not_delivered": "[FAIL] ❌ No entregado a {dst}: {msg}",
        "err_send_file_all": "[ERR] ❌ Para enviar fichero debes usar un destinatario concreto (no ALL).",
        "err_file_not_found": "[ERR] ❌ No existe fichero: {path}",
        "warn_rx_file_stale": "[WARN] ⚠️ RX FILE stale: descartando {filename} msgid={msgid} (sin actividad)",
        "rx_file_start": "[RX FILE] Iniciando {filename} ({filesize} bytes) desde {src} msgid={msgid}",
        "warn_rx_file_end_unknown": "[WARN] ⚠️ RX FILE fin recibido pero total desconocido: {filename} msgid={msgid}. No guardo.",
        "warn_rx_file_incomplete": "[WARN] ⚠️ RX FILE incompleto: {filename} desde {src} msgid={msgid} recibido={received}/{expected_total} bytes={recv_bytes}/{filesize} faltan={preview}{more}. No guardo.",
        "help_body": """
    Comandos:
      ALL: <mensaje>                 Enviar broadcast (sin ACK)
      CALLSIGN: <mensaje>            Enviar directo (con ACK)
      SEND <CALLSIGN> <ruta>         Enviar fichero
      WHOAMI                         Muestra tu callsign
      HELP                           Esta ayuda
      EXIT                           Salir

    Ejemplos:
      ALL: hola a todos
      EA4XYZ: mensaje de prueba
      SEND EA4XYZ C:\\temp\\foto.jpg

-------------------------------------------------------------------------------------""",
        "info_mesh_dest_confirmed": "[INFO] ✅ Destino Meshtastic confirmado: {dest_input} ({dest_id})",
        "err_mesh_dest_id_invalid": "[ERR] ❌ No se pudo usar destinationId '{dest_id}'. Aborto.",
        "err_mesh_shortname_not_found": "[ERR] ❌ No se encontró el nodo '{shortname}' en iface.nodes del nodo bridge. Aborto.",
        "warn_mesh_not_ready": "[WARN] ⚠️ Meshtastic no confirmó readiness, continúo igualmente...",
        "warn_mesh_not_ready_retry": "[WARN] ⚠️ Meshtastic aún no listo ({error}) intento {attempt}/3",
        "err_bridge_mesh_missing_iface": "[ERR] ❌ Para --bridge-mesh debes indicar --mesh-serial o --mesh-host",
        "info_monitor_on": "[INFO] ✅ Monitor ON: mostraré textos aunque no vayan a mí/ALL (sin ACK)",
        "err_no_kiss_connection": "[ERR] ❌ No hay conexión KISS. Saliendo.",
        "warn_nodeid_not_found": "[ERR] ❌ NodeId para '{dest}' no encontrado en DB (iface.nodes). DM no enviado.",
        "warn_forward_incomplete": "[WARN] ⚠️ Forward incompleto desde {src}: {text}",
        "warn_forward_malformed": "Forward malformado desde {src}: {text}",



    },
    "en": {
        "connected_vara": "[INFO] ✅ Connected to VARA HF {host}:{port}",
        "retry_no_ack": "[RETRY] ⚠️ No ACK from {dst} after {timeout:.0f}s "
                        "(msgid={msgid} seq={seq} len={payload_len}) "
                        "attempt {attempt}/{max_retries}",
        "fail_no_ack": "[FAIL] ❌ No ACK after {max_retries} retries: {dst} msgid={msgid} seq={seq}",
        "err_invalid_format": "[ERR] ❌ Invalid format. Use 'ALL: message' or 'CALL: message'",
        "ack_dm": "[ACK DM] ✅ Message acknowledged by {dst}",
        "fail_not_delivered": "[FAIL] ❌ Not delivered to {dst}: {msg}",
        "err_send_file_all": "[ERR] ❌ To send a file you must use a specific recipient (not ALL).",
        "err_file_not_found": "[ERR] ❌ File not found: {path}",
        "warn_rx_file_stale": "[WARN] ⚠️RX FILE stale: discarding {filename} msgid={msgid} (no activity)",
        "rx_file_start": "[RX FILE] Starting {filename} ({filesize} bytes) from {src} msgid={msgid}",
        "warn_rx_file_end_unknown": "[WARN] ⚠️ RX FILE end received but total unknown: {filename} msgid={msgid}. Not saving.",
        "warn_rx_file_incomplete": "[WARN] ⚠️ RX FILE incomplete: {filename} from {src} msgid={msgid} received={received}/{expected_total} bytes={recv_bytes}/{filesize} missing={preview}{more}. Not saving.",
        "help_body": """
    Commands:
      ALL: <message>                 Send broadcast (no ACK)
      CALLSIGN: <message>            Send direct message (with ACK)
      SEND <CALLSIGN> <path>         Send file
      WHOAMI                         Show your callsign
      HELP                           Show this help
      EXIT                           Exit

    Examples:
      ALL: hello everyone
      EA4XYZ: test message
      SEND EA4XYZ C:\\temp\\photo.jpg

-------------------------------------------------------------------------------------""",
        "info_mesh_dest_confirmed": "[INFO] ✅ Meshtastic destination confirmed: {dest_input} ({dest_id})",
        "err_mesh_dest_id_invalid": "[ERR] ❌ Could not use destinationId '{dest_id}'. Aborting.",
        "err_mesh_shortname_not_found": "[ERR] ❌ Node '{shortname}' not found in iface.nodes of the bridge node. Aborting.",
        "warn_mesh_not_ready": "[WARN] ⚠️ Meshtastic did not confirm readiness, continuing anyway...",
        "warn_mesh_not_ready_retry": "[WARN] ⚠️ Meshtastic not ready yet ({error}) attempt {attempt}/3",
        "err_bridge_mesh_missing_iface": "[ERR] ❌ For --bridge-mesh you must specify --mesh-serial or --mesh-host",
        "info_monitor_on": "[INFO] ✅ Monitor ON: I will display messages even if not addressed to me/ALL (no ACK)",
        "err_no_kiss_connection": "[ERR] ❌ No KISS connection available. Exiting.",
        "warn_nodeid_not_found": "[ERR] ❌ NodeId for '{dest}' not found in DB (iface.nodes). DM not sent.",
        "warn_forward_incomplete": "[WARN] ⚠ Incomplete forward from {src}: {text}",
        "warn_forward_malformed": "Malformed forward from {src}: {text}",



    },
}


# ---------------- utils ----------------
def norm_call(s: str) -> str:
    s = s.strip().upper()
    return (s if s else "NOCALL")[:10]

def pad10(s: str) -> bytes:
    return norm_call(s).encode("ascii", errors="ignore").ljust(10, b" ")

def unpad10(b: bytes) -> str:
    return b.decode("ascii", errors="ignore").strip()

def now() -> float:
    return time.time()
    
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

def strip_ansi(t: str) -> str:
    return ANSI_RE.sub("", t)

# ---------------- KISS framing ----------------
def kiss_escape(data: bytes) -> bytes:
    out = bytearray()
    for b in data:
        if b == FEND:
            out.extend([FESC, TFEND])
        elif b == FESC:
            out.extend([FESC, TFESC])
        else:
            out.append(b)
    return bytes(out)

def kiss_unescape(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        b = data[i]
        if b == FESC and i + 1 < len(data):
            nxt = data[i + 1]
            if nxt == TFEND:
                out.append(FEND)
            elif nxt == TFESC:
                out.append(FESC)
            else:
                out.append(nxt)
            i += 2
        else:
            out.append(b)
            i += 1
    return bytes(out)

def kiss_wrap(ax25_frame: bytes, port: int = 0) -> bytes:
    cmd = ((port & 0x0F) << 4) | 0x00  # data frame
    payload = bytes([cmd]) + ax25_frame
    return bytes([FEND]) + kiss_escape(payload) + bytes([FEND])

def try_extract_kiss(buf: bytearray) -> Optional[bytes]:
    try:
        start = buf.index(FEND)
    except ValueError:
        buf.clear()
        return None
    if start > 0:
        del buf[:start]
    try:
        end = buf.index(FEND, 1)
    except ValueError:
        return None
    raw = bytes(buf[1:end])
    del buf[:end + 1]
    return raw

def kiss_parse(raw_between_fends: bytes) -> Tuple[int, int, bytes]:
    u = kiss_unescape(raw_between_fends)
    if not u:
        raise ValueError("Empty KISS frame")
    cmd = u[0]
    port = (cmd >> 4) & 0x0F
    command = cmd & 0x0F
    data = u[1:]
    return port, command, data

# ---------------- AX.25 build/parse ----------------
def ax25_encode_addr(call: str, last: bool) -> bytes:
    call = call.strip().upper()
    ssid = 0
    if "-" in call:
        base, ss = call.split("-", 1)
        call = base
        try:
            ssid = int(ss)
        except ValueError:
            ssid = 0
    call = call.ljust(6)
    addr = bytes([(ord(c) << 1) & 0xFE for c in call[:6]])
    ssid_byte = 0x60 | ((ssid & 0x0F) << 1)
    if last:
        ssid_byte |= 0x01
    return addr + bytes([ssid_byte])

def ax25_build_ui(dst: str, src: str, info: bytes, digis: Optional[list] = None) -> bytes:
    digis = digis or []
    addr_fields = []
    addr_fields.append(ax25_encode_addr(dst, last=False))
    addr_fields.append(ax25_encode_addr(src, last=(len(digis) == 0)))
    for i, d in enumerate(digis):
        addr_fields.append(ax25_encode_addr(d, last=(i == len(digis) - 1)))
    return b"".join(addr_fields) + bytes([AX25_UI, AX25_PID]) + info

def ax25_parse_ui(frame: bytes) -> Optional[Tuple[str, str, bytes]]:
    if len(frame) < 16:
        return None
    i = 0
    addrs = []
    while True:
        if i + 7 > len(frame):
            return None
        af = frame[i:i+7]
        i += 7
        addrs.append(af)
        if af[6] & 0x01:
            break
        if len(addrs) > 10:
            return None
    if i + 2 > len(frame):
        return None
    control = frame[i]
    pid = frame[i+1]
    i += 2
    if control != AX25_UI or pid != AX25_PID:
        return None

    def decode_addr(af: bytes) -> str:
        call = "".join(chr((b >> 1) & 0x7F) for b in af[:6]).strip()
        ssid = (af[6] >> 1) & 0x0F
        return f"{call}-{ssid}" if ssid else call

    dst = decode_addr(addrs[0])
    src = decode_addr(addrs[1]) if len(addrs) >= 2 else "NOCALL"
    info = frame[i:]
    return dst, src, info

# ---------------- App pack/unpack ----------------
def app_pack(mtype: int, flags: int, src: str, dst: str, msgid: int, seq: int, tot: int, payload: bytes) -> bytes:
    crc = zlib.crc32(payload) & 0xFFFFFFFF
    header = struct.pack(
        HDR_FMT, MAGIC, mtype, flags,
        pad10(src), pad10(dst),
        msgid, seq & 0xFFFF, tot & 0xFFFF,
        len(payload) & 0xFFFF,
        crc
    )
    return header + payload

def app_unpack(data: bytes) -> Optional[Tuple[int, int, str, str, int, int, int, bytes]]:
    if len(data) < HDR_LEN:
        return None
    magic, mtype, flags, src10, dst10, msgid, seq, tot, paylen, crc = struct.unpack(HDR_FMT, data[:HDR_LEN])
    if magic != MAGIC:
        return None
    if len(data) < HDR_LEN + paylen:
        return None
    payload = data[HDR_LEN:HDR_LEN+paylen]
    if (zlib.crc32(payload) & 0xFFFFFFFF) != crc:
        return None
    return mtype, flags, unpad10(src10), unpad10(dst10), msgid, seq, tot, payload

# ---------------- Transport: KISS over TCP ----------------
class KissTCP:
    def __init__(self, host: str, port: int, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: Optional[socket.socket] = None
        self.buf = bytearray()
        self.lock = threading.Lock()  # protect sendall

    def connect(self, app) -> bool:
        if self.sock:
            return True
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(self.timeout)
            s.connect((self.host, self.port))
            s.settimeout(0.2)
            self.sock = s
            #app.log(f"[INFO] ✅ Connected to VARA HF {self.host}:{self.port}", level=1)
            app.log(app.var_text("connected_vara", host=self.host, port=self.port), level=1)

            
            return True
        except Exception as e:
            app.log(f"[ERR] ❌ Could not connect to VARA HF via KISS at {self.host}:{self.port}: {e}",level=0)
            self.sock = None
            return False

        
    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None

    def send_ax25(self, ax25_frame: bytes):
        if not self.sock:
            raise RuntimeError("KISS not connected")
        data = kiss_wrap(ax25_frame)
        with self.lock:
            self.sock.sendall(data)

    def recv_ax25(self) -> Optional[bytes]:
        if not self.sock:
            raise RuntimeError("KISS not connected")
        try:
            chunk = self.sock.recv(4096)
        except socket.timeout:
            chunk = b""
        except OSError:
            self.close()
            return None
        if chunk:
            self.buf.extend(chunk)
        raw = try_extract_kiss(self.buf)
        if raw is None:
            return None
        _, cmd, data = kiss_parse(raw)
        if cmd != 0x00:
            return None
        return data

# ---------------- Application ----------------
@dataclass
class IncomingFile:
    src: str
    filename: str
    total: int
    received: Dict[int, bytes]
    filesize: int
    last_update: float

class VaraApp:
    def __init__(self, mycall: str, kiss_host: str, kiss_port: int, ax25_dst: str = "APVARA", verbose = 1, log_mode="console", log_file="meshfest.log", lang="en"):
        self.mycall = norm_call(mycall)
        self.kiss = KissTCP(kiss_host, kiss_port)
        self.ax25_dst = ax25_dst
        self._msgid = int(time.time()) & 0x7FFFFFFF
        
        self.rtt_ewma: Dict[str, float] = {}             # dst -> rtt medio
        self.send_times: Dict[Tuple[int, int], float] = {}  # (msgid,seq) -> t_send

        self.ack_events: Dict[Tuple[int, int], threading.Event] = {}
        self.ack_lock = threading.Lock()

        self.in_files: Dict[int, IncomingFile] = {}

        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)

        # RX worker uses this to print without interleaving too badly
        self.print_lock = threading.Lock()
        
        #Meshtastic Bridge
        self.bridge = None  # MeshBridge opcional
        
        # Monitorr /sniffer
        self.monitor = False
        
        # Logs
        self.verbose = verbose
        self.log_mode = log_mode
        self.log_file = log_file
        self._log_fh = None
        
        # Creamos  / leemos el fichero de log
        if self.log_mode in ("file", "both"):
            log_path = os.path.abspath(self.log_file)
            log_dir = os.path.dirname(log_path)
            if log_dir and not os.path.isdir(log_dir):
                os.makedirs(log_dir, exist_ok=True)

            self._log_fh = open(log_path, "a", encoding="utf-8", buffering=1)
            self.log(f"[DEBUG] LOG OPEN OK: {os.path.abspath(self.log_file)}", level=2)

        self.lang = lang
        vara_name = "VARA"
        mesh_name = "MESH"


    def send_dm_ack(self, to_call: str, msg: str, *, retries: int = 0, timeout: float = 12.0) -> bool:
        to_call = (to_call or "").strip().upper()
        if not to_call or not msg:
            return False

        msgid = self.next_msgid()
        payload = msg.encode("utf-8", errors="replace")
        pkt = app_pack(T_MSG, 0, self.mycall, to_call, msgid, 0, 0, payload)

        return self._send_with_ack(
            pkt, to_call, msgid, 0,
            retries=retries, timeout=timeout,
            payload_len=len(payload),
            dst_ax25=to_call
        )



    def tag_replace(self, s: str) -> str:
        """
        Sustituye tokens 'VARA' y 'MESH' por los tags literales configurados.
        NO toca corchetes ni símbolos: inserta tal cual.
        """
        if not isinstance(s, str):
            return s
        return s.replace("VARA", self.vara_name).replace("MESH", self.mesh_tag)
        
        
    def close(self):
        if self._log_fh:
            try:
                self._log_fh.close()
            finally:
                self._log_fh = None


    def var_text(self, key: str, **kwargs) -> str:
        # fallback: si falta clave en idioma elegido, intenta EN, si no, devuelve la key
        tmpl = TEXTS.get(self.lang, {}).get(key) or TEXTS["en"].get(key) or key
        try:
            return tmpl.format(**kwargs)
        except Exception:
            # si alguien olvida un placeholder, que no reviente el programa
            return tmpl


    def handle_mesh_forward(self, src_call: str, text: str) -> bool:
        if not text or not text.startswith(">"):
            return False
        if not getattr(self, "mesh", None):
            return False
        body = text[1:].strip()
        if ":" not in body:
            self.log(f"[WARN] Forward malformado desde {src_call}: {text}", level=1)
            return False
        mesh_dest, mesh_msg = body.split(":", 1)
        mesh_dest = mesh_dest.strip()
        mesh_msg = mesh_msg.strip()
        if not mesh_dest or not mesh_msg:
            self.log(f"[WARN] Forward incompleto desde {src_call}: {text}", level=1)
            return False
        # ---------------------------------------------------------
        # PASO 2: extraer cabecera de ruta si viene como:
        #   >DEST: [QXT6>30QXT1] mensaje
        # ---------------------------------------------------------
        route = None
        m_route = re.match(r"^\[([^\]]{2,120})\]\s*(.*)$", mesh_msg)
        if m_route:
            route = (m_route.group(1) or "").strip()
            mesh_msg = (m_route.group(2) or "").strip()

            # Opcional: añade el hop local (esta estación) a la ruta
            if route:
                route = f"{route}>{self.app.mycall}"

        try:
            # Ajusta esta llamada a TU forma real de enviar a mesh
            self.mesh.send_text(mesh_msg, destinationId=mesh_dest)
            self.log(f"[{self.app.vara_name} -> {self.app.mesh_name}] {src_call} -> {mesh_dest}: {mesh_msg}", level=1)
            return True
        except Exception as e:
            self.log(f"[FAIL] ❌ Error reenviando a {self.app.mesh_name}{mesh_dest}: {e}", level=0)
            return False


    
    def estimate_ack_timeout(self, dst: str, payload_len: int) -> float:
        # 1) velocidad efectiva en bytes/s
        bytes_per_sec = max(1.0, (EST_BITS_PER_SEC / 8.0) * EFFICIENCY)

        # 2) tiempo estimado por tamaño
        size_based = BASE_ACK_TIMEOUT + (payload_len / bytes_per_sec) + ACK_MARGIN

        # 3) RTT histórico o por defecto
        rtt = self.rtt_ewma.get(dst.upper(), DEFAULT_RTT)
        hist_based = rtt * RTT_MULT

        # 4) elegir el mayor (seguridad HF)
        t = max(size_based, hist_based)

        # 5) limitar
        if t < MIN_ACK_TIMEOUT:
            t = MIN_ACK_TIMEOUT
        elif t > MAX_ACK_TIMEOUT:
            t = MAX_ACK_TIMEOUT
        return t

    
    ''' texto sin colores
    def log(self, s: str):
        with self.print_lock:
            print(s, flush=True)
    '''
    def log(self, s: str, level: int = 1):
        """
        level:
          0 = errores críticos
          1 = normal (default)
          2 = verbose / debug
        """

        if self.verbose < level:
            return

        # Timestamp (año 2 cifras)
        now = datetime.now().strftime("[%d/%m/%y-%H:%M:%S]")

        # Sanitiza para que no te machaque el timestamp
        s = str(s).replace("\r", "").rstrip("\n")

        with self.print_lock:
            if s.startswith("[RX"):
                color = ANSI_GREEN
            elif s.startswith("[TX") or s.startswith("[ACK"):
                color = ANSI_YELLOW
            elif s.startswith("[RETRY") or s.startswith("[FAIL")  or s.startswith("[DENY") or s.startswith("[FWD FAIL"):
                color = ANSI_RED
            elif s.startswith("[ERR"):
                color = ANSI_MAGENTA #purple color
            elif s.startswith("[DEBUG"):
                color = ANSI_CYAN
            else:
                color = ANSI_CYAN

            #print(f"{ANSI_RESET}{now} {color}{s}{ANSI_RESET}", flush=True)
            line_plain = f"{now} {s}"
            line_console = f"{ANSI_RESET}{now} {color}{s}{ANSI_RESET}"

            # consola
            if self.log_mode in ("console", "both"):
                print(line_console, flush=True)

            # archivo (sin ANSI, siempre limpio)
            if self.log_mode in ("file", "both") and self._log_fh:
                self._log_fh.write(strip_ansi(line_plain) + "\n")


    def send_dm_no_wait(self, to_call: str, msg: str) -> None:
        """
        Envía un DM (T_MSG flags=0) pero NO espera ACK.
        Útil para mensajes de control (DENY/INFO) para no bloquear con timeouts largos.
        """
        to_call = (to_call or "").strip().upper()
        if not to_call or not msg:
            return

        msgid = self.next_msgid()
        payload = msg.encode("utf-8", errors="replace")
        pkt = app_pack(T_MSG, 0, self.mycall, to_call, msgid, 0, 0, payload)

        # Enviar directo por KISS (sin _send_with_ack)
        self.send_ui(pkt, dst_ax25=to_call)

        # Log opcional (deja level=2 si no quieres ruido)
        self.log(f"[TX NOACK] {self.mycall} -> {to_call}: {msg}", level=2)

    
    
    def next_msgid(self) -> int:
        self._msgid = (self._msgid + 1) & 0x7FFFFFFF
        return self._msgid

    def send_ui(self, info: bytes, dst_ax25: Optional[str] = None):
        """
        Envía un frame AX.25 UI por KISS.
        dst_ax25 controla el DEST que verá VARA: SRC -> DEST
        """
        axdst = dst_ax25 or self.ax25_dst
        frame = ax25_build_ui(axdst, self.mycall, info)
        self.kiss.send_ax25(frame)

    def send_ack(self, to_call: str, msgid: int, seq: int):
        pkt = app_pack(T_ACK, 0, self.mycall, to_call, msgid, seq, 0, b"")
        self.send_ui(pkt, dst_ax25=to_call)


    def _send_with_ack(self, pkt: bytes, dst: str, msgid: int, seq: int, payload_len: int, dst_ax25: Optional[str] = None) -> bool:
        """
        Stop-and-wait fiable usando Event + timeout adaptativo por tamaño e histórico.
        """
        key = (msgid, seq)
        dst_u = dst.upper()

        ev = threading.Event()
        with self.ack_lock:
            self.ack_events[key] = ev
            
        try:
            for attempt in range(1, MAX_RETRIES + 1):
                # marca cuándo enviamos este intento (para RTT)
                t_send = now()
                self.send_times[key] = t_send

                self.send_ui(pkt, dst_ax25=dst_ax25)

                # timeout dinámico
                timeout = self.estimate_ack_timeout(dst_u, payload_len)

                if ev.wait(timeout=timeout):
                    # RTT observado
                    rtt = now() - self.send_times.get(key, t_send)

                    # actualizar EWMA por destino
                    prev = self.rtt_ewma.get(dst_u)
                    if prev is None:
                        self.rtt_ewma[dst_u] = rtt
                    else:
                        self.rtt_ewma[dst_u] = (1.0 - EWMA_ALPHA) * prev + EWMA_ALPHA * rtt

                    return True

                #self.log(f"[RETRY] ⚠️ Sin ACK de {dst_u} tras {timeout:.0f}s "
                #    f"(msgid={msgid} seq={seq} len={payload_len}) intento {attempt}/{MAX_RETRIES}")
                self.log( self.var_text("retry_no_ack", dst=dst_u, timeout=timeout, msgid=msgid, seq=seq, payload_len=payload_len, attempt=attempt, max_retries=MAX_RETRIES),level=1)

            #self.log(f"[FAIL] ❌ Sin ACK tras {MAX_RETRIES} reintentos: {dst_u} msgid={msgid} seq={seq}")
            self.log(self.var_text("fail_no_ack", max_retries=MAX_RETRIES, dst=dst_u, msgid=msgid, seq=seq), level=0)

            return False

        finally:
            self.send_times.pop(key, None)
            with self.ack_lock:
                self.ack_events.pop(key, None)

    def send_text(self, text: str, destination_id: Optional[str] = None, channel_index: Optional[int] = None,
              want_ack: bool = False,
              retries: int = 1):

        if not text:
            return None

        # canal por defecto (si no se especifica)
        if channel_index is None:
            channel_index = 0

        kwargs: Dict[str, Any] = {}
        if destination_id:
            kwargs["destinationId"] = destination_id
        if channel_index is not None:
            kwargs["channelIndex"] = channel_index
        if want_ack and destination_id:
            kwargs["wantAck"] = True

        print(f"[{self.app.mesh_name} TX] text={text!r} dest={destination_id} ch={channel_index} ack={want_ack} retries={retries}")

        last_err = None
        for attempt in range(retries + 1):
            try:
                try:
                    r = self.iface.sendText(text, **kwargs)
                except TypeError:
                    kwargs.pop("wantAck", None)
                    r = self.iface.sendText(text, **kwargs)

                if want_ack and destination_id and hasattr(self.iface, "waitForAckNak"):
                    self.iface.waitForAckNak()
                return r

            except Exception as e:
                last_err = e
                time.sleep(0.5 * (attempt + 1))
                try:
                    self._recreate_iface()
                except Exception:
                    pass

        raise last_err if last_err else RuntimeError("[ERR] ❌ Unknown error when sending to Meshtastic")


    def send_text_line(self, line: str):
        """
        Envía una línea de chat en formato:
          - "ALL: mensaje"                      (broadcast sin ACK)
          - "CALL: mensaje"                     (directo con ACK)
          - "RELAY > MESHDEST: mensaje"         (envía por VARA a RELAY para que reenvíe a MESHDEST)

        NUEVO (genérico):
          - "@DEST mensaje"                     (auto convierte a RELAY > DEST usando self.ax25_dst como relay)
            DEST puede ser shortname (QXT3) o NodeId (!abcdef01)
            Permite "@DEST: msg" / "@DEST, msg"
        """

        line = (line or "").strip()
        if not line:
            return

        # --------------------------------------------------
        # NUEVO: modo rápido @DEST mensaje  (genérico)
        # --------------------------------------------------
        t0 = line.lstrip()
        m_at = re.match(r"^@([A-Za-z0-9_!.-]{2,16})\s*[:,]?\s*(.+)\s*$", t0)
        if m_at:
            mesh_dest = (m_at.group(1) or "").strip()
            rest = (m_at.group(2) or "").strip()
            if not mesh_dest or not rest:
                return

            relay_call = self.ax25_dst.strip().upper()
            if not relay_call:
                self.log(self.var_text("err_invalid_format"), level=0)
                return

            # Log bonito: SRC > RELAY > DEST: msg
            # En este modo rápido el SRC es esta estación (self.mycall)
            self.log(f"[TX] {self.mycall} > {relay_call} > {mesh_dest}: {rest}", level=1)

            msgid = self.next_msgid()
            fwd_text = f">{mesh_dest}: {rest}"
            payload = fwd_text.encode("utf-8", errors="replace")
            pkt = app_pack(T_MSG, 0, self.mycall, relay_call, msgid, 0, 0, payload)

            ok = self._send_with_ack(
                pkt,
                relay_call,
                msgid,
                0,
                payload_len=len(payload),
                dst_ax25=relay_call
            )

            if ok:
                self.log(f"[ACK FWD] ✅ Relay {relay_call} received request for {self.mesh_name} {mesh_dest}", level=1)
            else:
                self.log(f"[FAIL] ❌ No delivery to the Relay {relay_call} (para {self.mesh_name} {mesh_dest})", level=0)
            return

        # --------------------------------------------------
        # FORMATO CLÁSICO
        # --------------------------------------------------
        if ":" not in line:
            self.log(self.var_text("err_invalid_format"), level=0)
            return

        left, msg = line.split(":", 1)
        left = left.strip()
        msg = msg.strip()
        if not msg:
            return

        # --------------------------------------------------
        # MODO RELAY EXPLÍCITO: "RELAY > MESHDEST: mensaje"
        # --------------------------------------------------
        if ">" in left:
            relay_part, mesh_part = left.split(">", 1)
            relay_call = relay_part.strip().upper()
            mesh_dest = mesh_part.strip()

            if not relay_call or not mesh_dest:
                self.log(self.var_text("err_invalid_format"), level=0)
                return

            # ---------------------------
            # LOG BONITO PARA RELAY
            # Queremos:
            #   [TX] <ULTIMO_HOP> > <RELAY> > <DEST>: <MSG>
            # Si msg viene con tag:
            #   "[QXT6>30QXT1] mensaje"
            # usamos el ÚLTIMO hop del tag => 30QXT1
            # ---------------------------
            pretty_src = self.mycall
            pretty_msg = msg

            m_route = re.match(r"^\[([^\]]{2,120})\]\s*(.*)$", msg)
            if m_route:
                route = (m_route.group(1) or "").strip()
                pretty_msg = (m_route.group(2) or "").strip()

                hops = [h.strip().upper() for h in route.split(">") if h.strip()]
                if hops:
                    candidate = hops[-1]

                    # Si el tag termina en el relay_call (destino), NO lo uses como origen TX.
                    # En ese caso el origen TX real es esta estación (self.mycall).
                    if candidate == relay_call:
                        pretty_src = self.mycall
                    else:
                        pretty_src = candidate


            self.log(f"[TX DM] {pretty_src} > {relay_call} > {mesh_dest}: {pretty_msg}", level=1)

            # Payload real: mantenemos msg TAL CUAL (incluye tag si venía)
            fwd_text = f">{mesh_dest}: {msg}"

            msgid = self.next_msgid()
            payload = fwd_text.encode("utf-8", errors="replace")
            pkt = app_pack(T_MSG, 0, self.mycall, relay_call, msgid, 0, 0, payload)

            ok = self._send_with_ack(
                pkt,
                relay_call,
                msgid,
                0,
                payload_len=len(payload),
                dst_ax25=relay_call
            )

            if ok:
                self.log(f"[ACK FWD] ✅ Relay {relay_call} received request for {self.mesh_name} {mesh_dest}", level=1)
            else:
                self.log(f"[FAIL] ❌ No Delivery to the relay {relay_call} (para {self.mesh_name} {mesh_dest})", level=0)
            return

        # --------------------------------------------------
        # MODO NORMAL
        # --------------------------------------------------
        to_call = left.upper()

        if to_call == "ALL":
            msgid = self.next_msgid()
            pkt = app_pack(
                T_MSG,
                FLAG_BROADCAST,
                self.mycall,
                "ALL",
                msgid,
                0,
                0,
                msg.encode("utf-8", errors="replace")
            )
            self.send_ui(pkt, dst_ax25="ALL")
            self.log(f"[TX ALL] {self.mycall} -> ALL: {msg}", level=1)
            return

        # DM VARA normal
        self.log(f"[TX] {self.mycall} -> {to_call}: {msg}", level=1)

        msgid = self.next_msgid()
        payload = msg.encode("utf-8", errors="replace")
        pkt = app_pack(T_MSG, 0, self.mycall, to_call, msgid, 0, 0, payload)

        ok = self._send_with_ack(
            pkt,
            to_call,
            msgid,
            0,
            payload_len=len(payload),
            dst_ax25=to_call
        )

        if ok:
            self.log(self.var_text("ack_dm", dst=to_call), level=1)
        else:
            self.log(self.var_text("fail_not_delivered", dst=to_call, msg=msg), level=0)


    def send_file(self, to_call: str, path: str):
        to_call = to_call.strip().upper()
        
        # DEBUG: ver exactamente qué llega
        self.log(f"[DEBUG] SEND to={to_call} path={path}", level=2)
        
        if to_call == "ALL":
            #self.log(f"[ERR] Para enviar fichero debes usar un destinatario concreto (no ALL).", level=0)
            self.log(self.var_text("err_send_file_all"), level=0)
            return
            
        if not os.path.isfile(path):
            #self.log(f"[ERR] No existe fichero: {path}", level=0)
            self.log(self.var_text("err_file_not_found", path=path), level=0)
            return

        filename = os.path.basename(path)
        data = open(path, "rb").read()
        filesize = len(data)
        
        t0 = time.time()
        msgid = self.next_msgid()

        # header: filename\0 + filesize(4)
        header_payload = filename.encode("utf-8", errors="replace") + b"\0" + struct.pack("!I", filesize)
        header_pkt = app_pack(T_FILE, 0, self.mycall, to_call, msgid, 0, 0, header_payload)
        if not self._send_with_ack(header_pkt, to_call, msgid, 0, payload_len=len(header_payload), dst_ax25=to_call):
            return

        self.log(f"[TX FILE] Header {filename} ({filesize} bytes) -> {to_call}", level=1)

        chunks = [data[i:i+MAX_PAYLOAD] for i in range(0, len(data), MAX_PAYLOAD)]
        total = len(chunks)

        for idx, chunk in enumerate(chunks, start=1):
            pkt = app_pack(T_FILE, 0, self.mycall, to_call, msgid, idx, total, chunk)
            if not self._send_with_ack(pkt, to_call, msgid, idx, payload_len=len(chunk), dst_ax25=to_call):
                return
            # Muestra el progreso del envio    
            pct = (idx / total) * 100.0
            sent_bytes = min(idx * MAX_PAYLOAD, filesize)
            self.log(f"[TX FILE] {filename} {sent_bytes}/{filesize} bytes ({pct:.1f}%)", level=1)

        end_pkt = app_pack(T_FEND, 0, self.mycall, to_call, msgid, total + 1, total, b"")
        
        if self._send_with_ack(end_pkt, to_call, msgid, total + 1, payload_len=0, dst_ax25=to_call):
            elapsed = time.time() - t0
            # evitar división por cero
            bps = (filesize / elapsed) if elapsed > 0 else 0.0
            mins = int(elapsed // 60)
            secs = elapsed - mins*60
            bits_per_sec = (filesize * 8.0) / elapsed if elapsed > 0 else 0.0
            self.log(f"[TX FILE] Completed: {filename} in {mins}m {secs:.1f}s ({bits_per_sec:.1f} bps)", level=1)

    
    def poll_once(self):
        FILE_RX_STALE_SECS = 10 * 60  # 10 min sin actividad => descartar recepción a medias (ajusta)

        # --- limpieza de recepciones antiguas (evita acumular incompletos) ---
        try:
            stale = []
            tnow = now()
            for mid, inc in list(self.in_files.items()):
                if (tnow - inc.last_update) > FILE_RX_STALE_SECS:
                    stale.append((mid, inc))
            for mid, inc in stale:
                #self.log(f"[WARN] RX FILE stale: descartando {inc.filename} msgid={mid} (sin actividad)", level=1)
                self.log(self.var_text("warn_rx_file_stale", filename=inc.filename, msgid=mid), level=1)
                self.in_files.pop(mid, None)
        except Exception:
            pass

        frame = self.kiss.recv_ax25()
        if not frame:
            return

        parsed = ax25_parse_ui(frame)
        if not parsed:
            return

        _, _, info = parsed

        app = app_unpack(info)
        if not app:
            return

        mtype, flags, src, dst, msgid, seq, tot, payload = app

        # Normalización para evitar mismatches por case/espacios
        src = (src or "").strip().upper()
        dst = (dst or "").strip().upper()
        my  = (self.mycall or "").strip().upper()

        # ACK recibido (despierta al emisor)
        if mtype == T_ACK:
            self.log(f"[RX ACK] from {src} (ack msgid={msgid} seq={seq})", level=2)
            # Solo nos interesa si va dirigido a mí (defensa extra)
            if dst == my:
                key = (msgid, seq)
                with self.ack_lock:
                    ev = self.ack_events.get(key)
                if ev:
                    ev.set()
            return

        # --- MONITOR ON: si no va a mi/ALL, aun así mostrar T_MSG legibles (sin ACK) ---
        # (usar 'my' normalizado, no self.mycall)
        if dst not in (my, "ALL"):
            if getattr(self, "monitor", False) and mtype == T_MSG:
                text = payload.decode("utf-8", errors="replace")
                # etiqueta monitor con destino real
                self.log(f"[RX MON] {src} -> {dst}: {text}")
            return

        is_bcast = bool(flags & FLAG_BROADCAST) or (dst == "ALL")

        # Para directos, responde ACK (para broadcast no)
        if not is_bcast:
            self.log(f"[TX ACK] -> {src} (rx msgid={msgid} seq={seq})", level=2)
            self.send_ack(src, msgid, seq)

        # ---------------- Text Message ----------------
        if mtype == T_MSG:
            text = payload.decode("utf-8", errors="replace")
            tag = "ALL" if is_bcast else "DM"

            pretty_src = src
            pretty_msg = text

            if text.startswith("!FWD_DENY"):
                self.log(f"[FWD FAIL] {src}: {text}", level=0)
                return

            # ---------------------------------------------------------
            # Si es forwarding tipo >DEST: [ROUTE] mensaje
            # ---------------------------------------------------------
            if text.startswith(">") and ":" in text:
                body = text[1:]
                dest_part, msg_part = body.split(":", 1)
                msg_part = msg_part.strip()

                import re
                m_route = re.match(r"^\[([^\]]{2,120})\]\s*(.*)$", msg_part)
                if m_route:
                    route = m_route.group(1).strip()
                    real_msg = m_route.group(2).strip()

                    # route ejemplo esperado: "QXT6>30QXT1"
                    # pero a veces te llega "QXT6>30QXT3" (mal) y hay que corregirlo

                    hops = [h.strip().upper() for h in route.split(">") if h.strip()]
                    ax_src = (src or "").strip().upper()      # quien lo entregó por VARA (ej: 30QXT1)
                    me = (self.mycall or "").strip().upper()  # esta estación (ej: 30QXT3)

                    origin = hops[0] if hops else ax_src

                    # Segundo hop: idealmente el último del tag (relay emisor),
                    # pero si coincide con "me" o con el destino, usamos ax_src (quien lo entregó)
                    relay_prev = None
                    if len(hops) >= 2:
                        candidate = hops[-1]
                        if candidate != me:
                            relay_prev = candidate

                    if not relay_prev:
                        relay_prev = ax_src or "?"

                    # Ruta final: ORIG > RELAY_PREV > ME
                    full_route = f"{origin} > {relay_prev} > {me}".strip()
                    pretty_src = full_route
                    pretty_msg = real_msg

            self.log(f"[RX {tag}] {pretty_src}: {pretty_msg}")

            # logica actual
            self.handle_mesh_forward(src, text)

            if self.bridge:
                try:
                    self.bridge.on_vara_text(src=src, dst=dst, text=text, is_bcast=is_bcast, msgid=msgid)
                except Exception as e:
                    self.log(f"[ERR] Bridge on_vara_text: {e}", level=0)
            return

        # ---------------- Tramas de fichero ----------------
        if mtype == T_FILE:
            # seq=0: cabecera del fichero: filename\0 + filesize(4)
            if seq == 0:
                if b"\0" not in payload or len(payload) < 6:
                    self.log(f"[RX FILE] header corrupted {src}")
                    return

                fname, rest = payload.split(b"\0", 1)
                filename = fname.decode("utf-8", errors="replace") or "file.bin"

                if len(rest) < 4:
                    self.log(f"[RX FILE] header with no size de {src}")
                    return

                filesize = struct.unpack("!I", rest[:4])[0]
                self.in_files[msgid] = IncomingFile(
                    src=src,
                    filename=filename,
                    total=0,
                    received={},
                    filesize=filesize,
                    last_update=now()
                )
                #self.log(f"[RX FILE] Iniciando {filename} ({filesize} bytes) desde {src} msgid={msgid}")
                self.log(self.var_text("rx_file_start", filename=filename, filesize=filesize, src=src, msgid=msgid), level=1)
                return

            # seq>=1: fragmentos de datos
            inc = self.in_files.get(msgid)
            if not inc:
                # si se perdio la cabecera, ignoramos
                return

            inc.total = tot
            inc.received[seq] = payload
            inc.last_update = now()

            if inc.total > 0:
                got = len(inc.received)
                pct = (got / inc.total) * 100.0
                recv_bytes = sum(len(b) for b in inc.received.values())

                self.log(f"[RX FILE] {inc.filename} {got}/{inc.total} ({pct:.1f}%)", level=1)
                self.log(f"[RX FILE] {inc.filename} {recv_bytes}/{inc.filesize} bytes ({pct:.1f}%)", level=1)

            return

        # ---------------- End Of File ----------------
        if mtype == T_FEND:
            inc = self.in_files.get(msgid)
            if not inc:
                return

            # Si no sabemos total aun (no llego ningún chunk con tot válido), usa el tot del FEND
            if inc.total == 0 and tot > 0:
                inc.total = tot

            expected_total = inc.total

            # Determinar qué partes faltan (1..total)
            missing = []
            if expected_total > 0:
                for i in range(1, expected_total + 1):
                    if i not in inc.received:
                        missing.append(i)

            recv_bytes = sum(len(b) for b in inc.received.values())

            # Si faltan chunks, NO guardar (evita archivos corruptos silenciosos)
            if expected_total == 0:
                #self.log(f"[WARN] RX FILE fin recibido pero total desconocido: {inc.filename} msgid={msgid}. No guardo.", level=1)
                self.log(self.var_text("warn_rx_file_end_unknown", filename=inc.filename, msgid=msgid), level=1)
                self.in_files.pop(msgid, None)
                return

            if missing:
                # muestra solo los primeros para no inundar
                preview = missing[:12]
                more = "" if len(missing) <= 12 else f" (+{len(missing)-12} más)"
                self.log(self.var_text(
                    "warn_rx_file_incomplete",
                    filename=inc.filename,
                    src=inc.src,
                    msgid=msgid,
                    received=len(inc.received),
                    expected_total=expected_total,
                    recv_bytes=recv_bytes,
                    filesize=inc.filesize,
                    preview=preview,
                    more=more
                ), level=1)

                # Limpieza para no dejar basura en memoria
                self.in_files.pop(msgid, None)
                return

            # Completo: ensamblar y guardar
            assembled = b"".join(inc.received.get(i, b"") for i in range(1, expected_total + 1))

            out_path = os.path.join(self.download_dir, inc.filename)
            with open(out_path, "wb") as f:
                f.write(assembled)

            self.log(
                f"[RX FILE] Saved: {out_path} "
                f"({len(assembled)}/{inc.filesize} bytes) from {inc.src}",
                level=1
            )

            # Limpieza
            self.in_files.pop(msgid, None)
            return

        return


# ------------------ Interactive UI ----------------
HELP_HEADER = """

.....................................................................................
: '##::::'##:'########::'######::'##::::'##:'########:'########::'######::'########::
:: ###::'###: ##.....::'##... ##: ##:::: ##: ##.....:: ##.....::'##... ##:... ##..:::
:: ####'####: ##::::::: ##:::..:: ##:::: ##: ##::::::: ##::::::: ##:::..::::: ##:::::
:: ## ### ##: ######:::. ######:: #########: ######::: ######:::. ######::::: ##:::::
:: ##. #: ##: ##...:::::..... ##: ##.... ##: ##...:::: ##...:::::..... ##:::: ##:::::
:: ##:.:: ##: ##:::::::'##::: ##: ##:::: ##: ##::::::: ##:::::::'##::: ##:::: ##:::::
:: ##:::: ##: ########:. ######:: ##:::: ##: ##::::::: ########:. ######::::: ##:::::
::..:::::..::........:::......:::..:::::..::..::::::::........:::......::::::..::::::
-------------------------------------- LITE v 1.0 -----------------------------------

                                    by Quixote Network
                                           

""".strip()

def input_thread(app: VaraApp, stop_evt: threading.Event):

    while not stop_evt.is_set():
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            stop_evt.set()
            break

        if not line:
            continue
        u = line.upper()

        if u in ("QUIT", "EXIT"):
            stop_evt.set()
            break
        if u == "HELP":
            self.log(HELP_HEADER + self.var_text("help_body"), level=1)
            continue
        if u == "WHOAMI":
            app.log(f"MYCALL={app.mycall}")
            continue
        if u.startswith("SEND "):
            rest = line[5:].strip()  # todo lo que viene después de "SEND "
            # separar DEST del resto (solo 1 split)
            parts = rest.split(" ", 1)
            if len(parts) < 2:
                app.log('Use: SEND <CALLSIGN> "path"', level=0)
                continue

            to_call = parts[0].strip()
            path = parts[1].strip().strip('"')

            app.send_file(to_call, path)
            continue

        # Default: treat as chat line "ALL:" or "CALL:"
        app.send_text_line(line)

def rx_thread(app: VaraApp, stop_evt: threading.Event):
    while not stop_evt.is_set():
        try:
            app.poll_once()
            time.sleep(0.01)

        except RuntimeError as e:
            # Si VARA/KISS no está conectado, salir del programa (sin bucle)
            msg = str(e)
            app.log(f"[ERR RX] {msg}", level=0)

            if "KISS not connected" in msg:
                stop_evt.set()
                break

            time.sleep(0.2)

        except Exception as e:
            app.log(f"[ERR RX] {e}", level=0)
            time.sleep(0.2)


# ---------------- Meshtastic optional ----------------
try:
    from pubsub import pub
except Exception:
    pub = None

try:
    from meshtastic.serial_interface import SerialInterface as MSerial
except Exception:
    MSerial = None

try:
    from meshtastic.tcp_interface import TCPInterface as MTCP
except Exception:
    MTCP = None


def create_tcp_interface(host: str, port: int):
    if MTCP is None:
        raise RuntimeError("TCPInterface missing. Install/update with: pip install -U meshtastic protobuf pubsub")
    last_err = None
    for kwargs in (
        {"hostname": host, "portNumber": port},
        {"hostname": host, "portNum": port},
        {"hostname": host},
        {},
    ):
        try:
            return MTCP(**kwargs)
        except TypeError as e:
            last_err = e
        except Exception as e:
            last_err = e
    raise last_err

class Mesh:
    def __init__(self, serial_path: Optional[str], hostport: Optional[str]):
        if pub is None:
            raise RuntimeError("Missing 'pubsub'. Install: pip install -U pubsub")
        if not serial_path and not hostport:
            raise RuntimeError("You need to put --mesh-serial or --mesh-host")

        self._serial_path = serial_path
        self._hostport = hostport
        self.iface = None

        if serial_path:
            if MSerial is None:
                raise RuntimeError("No SerialInterface. Install/Update: pip install -U meshtastic")
            self.iface = MSerial(serial_path)
        else:
            host, port = hostport.split(":") if ":" in hostport else (hostport, "4403")
            self.iface = create_tcp_interface(host, int(port))

    
    def my_node_num(self) -> Optional[int]:
        try:
            ln = getattr(self.iface, "localNode", None)
            if not ln and hasattr(self.iface, "getNode"):
                ln = self.iface.getNode("^local")
            if not ln:
                return None
            # nodeNum suele estar en ln.nodeNum
            return int(getattr(ln, "nodeNum"))
        except Exception:
            return None

    def is_broadcast_to(self, packet: dict) -> bool:
        """
        True si el paquete es broadcast o no viene con 'to' claro.
        """
        try:
            to_val = packet.get("to")
            if to_val is None:
                return True
            # broadcast suele ser 0xffffffff (4294967295)
            if int(to_val) == 0xFFFFFFFF:
                return True
            return False
        except Exception:
            return True

    
    def shortname_from_id(self, node_id: str) -> Optional[str]:
        try:
            n = (self.iface.nodes or {}).get(str(node_id))
            if not n:
                return None
            u = (n.get("user") or {})
            sn = (u.get("shortName") or "").strip()
            return sn or None
        except Exception:
            return None


    def close(self):
        try:
            if hasattr(self.iface, "close"):
                self.iface.close()
        except Exception:
            pass


    def resolve_dest_id(self, dest_id: Optional[str], shortname: Optional[str]) -> Optional[str]:
        if dest_id:
            return dest_id
        if not shortname:
            return None
        sn = shortname.lower()
        try:
            for node_id, n in (self.iface.nodes or {}).items():
                info = (n.get("user") or {})
                if str(info.get("shortName", "")).lower() == sn:
                    return node_id
        except Exception:
            pass
        return None


    def resolve_channel_index(self, idx: Optional[int], name: Optional[str]) -> Optional[int]:
        if idx is not None:
            return idx
        if not name:
            return None

        wanted = name.strip().lower()

        try:
            # Forma moderna
            chs = getattr(self.iface.localNode, "channels", None)
            if not chs:
                return None

            for i, ch in enumerate(chs):
                try:
                    nm = (ch.settings.name or "").strip().lower()
                except Exception:
                    nm = ""

                if nm == wanted:
                    return i

        except Exception:
            pass

        return None


    
    def forward_if_at(self,text: str, channel_index: Optional[int] = None, channel_name: Optional[str] = None, want_ack: bool = False, retries: int = 1) -> bool:
        """
        Si 'text' empieza por @QXT3 (o @ALGO), reenvía el resto por Meshtastic a ese shortName.
        Acepta: @QXT3 hola | @QXT3: hola | @QXT3, hola
        Devuelve True si ha reenviado; False si no aplica.
        """
        text = (text or "").strip()
        if not text:
            return False

        m = re.match(r"^\s*@([A-Za-z0-9_-]{2,16})\s*[:,]?\s*(.*)\s*$", text)
        if not m:
            return False

        short = (m.group(1) or "").strip()
        payload = (m.group(2) or "").strip()
        if not payload:
            return False

        # Si quieres SOLO QXT3, deja esta condición:
        if short.strip().upper() != "QXT3":
            return False

        dest_id = self.resolve_dest_id(None, short)
        if not dest_id:
            self.log(f"[{self.app.vara_name} -> {self.app.mesh_name}] ❌ No resuelvo destinationId para @{short}", level=0)
            return False

        ch_idx = self.resolve_channel_index(channel_index, channel_name)

        self.send_text(payload,
                       destination_id=dest_id,
                       channel_index=ch_idx,
                       want_ack=want_ack,
                       retries=retries)

        self.log(f"[{self.app.vara_name} -> {self.app.mesh_name}] ✅ @{short} (dest_id={dest_id}) <= {payload}", level=1)
        return True


            
    def get_channels(self):
        """
        Devuelve una lista de dicts con 'name' (compat), o lista vacía si aún no está listo.
        Compatible con SerialInterface y TCPInterface.
        """
        iface = self.iface

        # 1) Si por casualidad existe getChannelList (otras versiones)
        if hasattr(iface, "getChannelList"):
            try:
                return iface.getChannelList() or []
            except Exception:
                pass

        # 2) Camino normal: usar el nodo local
        try:
            ln = getattr(iface, "localNode", None)
            if not ln:
                # algunas builds exponen getNode("^local")
                if hasattr(iface, "getNode"):
                    ln = iface.getNode("^local")
            if not ln:
                return []

            chs = getattr(ln, "channels", None)
            if not chs:
                return []

            # Normaliza a lista de dicts con name
            out = []
            for c in chs:
                if c is None:
                    continue
                # c puede ser dict o un objeto protobuf-like
                if isinstance(c, dict):
                    nm = (c.get("settings", {}).get("name") or c.get("name") or "").strip()
                    out.append({"name": nm, **c})
                else:
                    # intenta atributos comunes
                    nm = ""
                    try:
                        # en muchos casos: c.settings.name
                        nm = (getattr(getattr(c, "settings", None), "name", "") or "").strip()
                    except Exception:
                        nm = ""
                    out.append({"name": nm, "raw": c})
            return out
        except Exception:
            return []


    def _recreate_iface(self):
        try:
            if hasattr(self.iface, "close"):
                self.iface.close()
        except Exception:
            pass

        # recrear según cómo se creó
        if self._serial_path:
            self.iface = MSerial(self._serial_path)
        else:
            host, port = self._hostport.split(":") if ":" in self._hostport else (self._hostport, "4403")
            self.iface = create_tcp_interface(host, int(port))


AT_CALL_RE = re.compile(r"^@([A-Za-z0-9/]+)\s*(.*)$")


class MeshBridge:
    """
    Puente opcional:
      - VARA RX (T_MSG)  -> Meshtastic sendText()
      - Meshtastic RX    -> VARA send (directo si @CALL ..., si no ALL)
    Anti-eco con prefijos:
      - Lo que entra desde Mesh y sale a VARA va prefijado con mesh_to_vara_prefix
      - Lo que entra desde VARA y sale a Mesh va prefijado con vara_to_mesh_prefix
      - Se ignoran mensajes que ya tengan el prefijo contrario para evitar bucles.
    """

    def __init__(
        self,
        app: "VaraApp",
        mesh: Mesh,
        *,
        mesh_dest_id: Optional[str],
        mesh_channel_index: Optional[int],
        mesh_channel_name: Optional[str],
        mesh_want_ack: bool,
        # en VARA, a dónde enviamos lo que venga de Mesh (ALL o CALL)
        vara_out_to: str,
        mesh_to_vara_prefix: str = "[{self.app.mesh_name}] ",
        vara_to_mesh_prefix: str = "[{self.app.vara_name}] ",
        mesh_allow_dest_shortnames = None,
    ):
        self.app = app
        self.mesh = mesh
        self.mesh_dest_id = mesh_dest_id
        self.mesh_channel_index = 0 if mesh_channel_index is None else mesh_channel_index
        self.mesh_channel_name = (mesh_channel_name or "").strip() or None
        self.mesh_want_ack = mesh_want_ack

        self.vara_out_to = (vara_out_to or "ALL").strip().upper()
        self.mesh_to_vara_prefix = mesh_to_vara_prefix or ""
        self.vara_to_mesh_prefix = vara_to_mesh_prefix or ""
        
        self.echo_ttl = 180  # segundos
        self._seen = {}      # hash -> timestamp
        
        # Destinations Allowed
        self.mesh_allow_dest_shortnames = mesh_allow_dest_shortnames  # set[str] o None

        # Meshtastic suscription
        pub.subscribe(self._on_mesh_packet, "meshtastic.receive")

        self.app.log(f"[INFO] ✅ MeshBridge active: {self.app.mesh_name} -> {self.app.vara_name} to={self.vara_out_to} " , level=1) 
        self.app.log(f"[INFO] ✅ MeshBridge active: {self.app.vara_name} -> {self.app.mesh_name} to ch={self.mesh_channel_index}", level=1)   
        print(f"{ANSI_CYAN}-------------------------------------------------------------------------------------{ANSI_RESET}")

    TAG_RE = re.compile(r"\[(?:mesh|vara)@[^]]+\]\s*", re.IGNORECASE)
    
    
    def _send_fwd_deny(self, src_call: str, msgid: int, dest: str, allowed_set):
        """
        Envía un DM por VARA al emisor indicando que el forward fue denegado.
        Solo se llama si --mesh-want-ack está activo.
        """
        try:
            src_call = (src_call or "").strip().upper()
            if not src_call or src_call in ("ALL", "CQ"):
                return

            allowed_txt = ",".join(sorted(allowed_set)) if allowed_set else "-"
            mid = msgid if msgid is not None else -1

            # Formato fácil de parsear por el receptor:
            # !FWD_DENY <msgid> <dest> NOT_ALLOWED allowed=<csv>
            deny_text = f"!FWD_DENY {mid} {dest} NOT_ALLOWED"

            # Esto es DM con ACK (porque es "CALL: mensaje")
            self.app.send_dm_ack(src_call, deny_text, retries=0, timeout=12.0)

        except Exception as e:
            self.app.log(f"[WARN] deny DM failed: {e}", level=1)


    def _clean_text(self, s: str) -> str:
        # elimina tags técnicos repetidos en cualquier parte
        s = self.TAG_RE.sub("", s or "")
        # compacta espacios
        return " ".join(s.split()).strip()

    def _gc_seen(self):
        t = time.time()
        dead = [k for k, ts in self._seen.items() if (t - ts) > self.echo_ttl]
        for k in dead:
            self._seen.pop(k, None)

    def _key(self, direction: str, src: str, dst: str, text: str) -> str:
        h = hashlib.sha1(f"{direction}|{src}|{dst}|{text}".encode("utf-8", "ignore")).hexdigest()
        return h

    def _mark(self, k: str):
        self._gc_seen()
        self._seen[k] = time.time()

    def _seen_before(self, k: str) -> bool:
        self._gc_seen()
        return k in self._seen
    
    def _mesh_send(self, text: str, *, destination_id=None, channel_index=None, want_ack=False):
        kwargs = {}
        if destination_id:
            kwargs["destinationId"] = destination_id
        if channel_index is not None:
            kwargs["channelIndex"] = channel_index
        if want_ack and destination_id:
            kwargs["wantAck"] = True

        try:
            return self.mesh.iface.sendText(text, **kwargs)
        except TypeError:
            # por si tu versión no soporta wantAck
            kwargs.pop("wantAck", None)
            return self.mesh.iface.sendText(text, **kwargs)


    # ---------- Mesh -> VARA ----------

    def _on_mesh_packet(self, packet=None, interface=None, topic=None, **kwargs):
        """
        Mesh -> VARA

        SOLO reenvía:
          - Mensajes directos (DM)
          - Dirigidos específicamente a este nodo bridge (este cliente TCP)
        """
        if not packet:
            return

        try:
            # -------- Identidad del bridge (nodeNum y nodeId) --------
            mynum = None
            myid = None
            try:
                ln = getattr(self.mesh.iface, "localNode", None)
                if not ln and hasattr(self.mesh.iface, "getNode"):
                    ln = self.mesh.iface.getNode("^local")
                if ln:
                    # nodeNum: int
                    try:
                        mynum = int(getattr(ln, "nodeNum"))
                    except Exception:
                        mynum = None
                    # nodeId: suele ser string tipo "!e2e5a934"
                    try:
                        myid = str(getattr(ln, "nodeId", "") or "").strip()
                    except Exception:
                        myid = None
                    
            except Exception:
                pass

            from_id = packet.get("fromId")

            if myid and from_id and str(from_id).strip() == myid:
                # Es un mensaje generado por este mismo bridge → no reenviar
                return
            # Si no sé quién soy, no hago nada
            if mynum is None and not myid:
                return

            # -------- Datos de destino del paquete --------
            to_val = packet.get("to")     # suele ser nodeNum (int)
            to_id  = packet.get("toId")   # a veces viene como "!xxxx"

            # -------- Descarta broadcasts / canal --------
            # broadcast típico: to = 0xFFFFFFFF
            try:
                if to_val is not None and int(to_val) == 0xFFFFFFFF:
                    return
            except Exception:
                pass

            # algunas variantes usan toId="^all"/"all"
            if isinstance(to_id, str) and to_id.strip().lower() in ("^all", "all"):
                return

            # -------- Acepta SOLO si es DM dirigido a mí --------
            dm_to_me = False

            # Caso 1: comparo por nodeNum
            try:
                if to_val is not None and mynum is not None and int(to_val) == int(mynum):
                    dm_to_me = True
            except Exception:
                pass

            # Caso 2: comparo por nodeId
            if (not dm_to_me) and to_id and myid:
                try:
                    if str(to_id).strip() == myid:
                        dm_to_me = True
                except Exception:
                    pass

            if not dm_to_me:
                # Debug opcional (descomenta si quieres ver por qué no pasa el filtro)
                # self.app.log(f"[DBG MESH RX] descartado: to={to_val} toId={to_id} mynum={mynum} myid={myid}", level=2)
                return

            # Log para mostrar
            #self.app.log(
            #    f"[MESH->VARA DM] from={packet.get('fromId') or packet.get('from')} "
            #    f"to={to_id or to_val}",level=1)

            # -------- Extraer texto --------
            decoded = packet.get("decoded") or {}
            txt = decoded.get("text")
            if not txt:
                return

            if not isinstance(txt, str):
                try:
                    txt = txt.decode("utf-8", errors="ignore")
                except Exception:
                    return

            txt = txt.strip()
            if not txt:
                return
            
            # Obtener origen en formato humano (shortName si existe)
            from_id = packet.get("fromId") or ""
            src_label = self.mesh.shortname_from_id(from_id) or str(from_id)

            # Texto limpio (sin tags técnicos si usas _clean_text)
            clean_txt = self._clean_text(txt) if hasattr(self, "_clean_text") else txt

            # "RX local": esta estación es quien recibe desde Mesh
            rx_local = (self.app.mycall or "?").strip().upper()

            # "TX next hop": a dónde lo vamos a sacar por VARA
            tx_next = (self.vara_out_to or "ALL").strip().upper()

            self.app.log(f"[{self.app.mesh_name} -> {self.app.vara_name}] {src_label} -> {rx_local} : {clean_txt}", level=1)
            # (opcional, si quieres también ver el siguiente salto)
            # self.app.log(f"[{self.app.mesh_name}->{self.app.vara_name}] {src_label} -> {rx_local} (to {tx_next}) : {clean_txt}", level=1)


            # -------- Anti-eco --------
            if self.vara_to_mesh_prefix and txt.startswith(self.vara_to_mesh_prefix):
                return
            
            # ---------------------------------------------------------
            # PRIORIDAD: @DEST ...  => crear RELAY "RELAY > DEST: ..."
            #  - DEST es shortname (o NodeId si empieza por "!")
            #  - va ANTES de AT_CALL_RE o se lo traga como @CALL normal
            # ---------------------------------------------------------
            t = clean_txt.lstrip()

            # Regex: @DEST [:,] mensaje
            m_at = re.match(r"^@([A-Za-z0-9_!.-]{2,16})\s*[:,]?\s*(.+)\s*$", t)
            if m_at:
                dest = (m_at.group(1) or "").strip()
                body = (m_at.group(2) or "").strip()
                if not dest or not body:
                    return

                relay_call = (self.vara_out_to or "ALL").strip().upper()
                if relay_call == "ALL":
                    self.app.log(f"[WARN] @{dest} recibido pero vara_out_to=ALL; no puedo hacer relay", level=1)
                    return

                # Opción: normaliza DEST a mayúsculas si es shortname
                # Si es NodeId tipo "!abcd1234" lo dejamos tal cual
                dest_norm = dest if dest.startswith("!") else dest.upper()

                # Esto activa el modo RELAY en VaraApp.send_text_line()
                #self.app.send_text_line(f"{relay_call} > {dest_norm}: {body}")
                origin = src_label.strip().upper()          # QXT6
                relay  = relay_call.strip().upper()         # 30QXT1
                self.app.send_text_line(f"{relay_call} > {dest_norm}: [{origin}>{relay}] {body}")

                self.app.log(f"[{self.app.mesh_name} -> {self.app.vara_name} RELAY] {src_label} -> {relay_call} > {dest_norm}: {body}", level=1)
                return

            
            # -------- Reenvio a VARA --------
            m = AT_CALL_RE.match(txt)
            if m:
                to_call = (m.group(1) or "").strip().upper()
                body = (m.group(2) or "").strip()
                if not body:
                    return

                # Relay configurado (si existe)
                relay_call = (
                    (getattr(self, "bridge_mesh_to_vara", None) or getattr(self.app, "bridge_mesh_to_vara", None))
                    or getattr(self, "vara_out_to", None)
                )
                relay_call = (str(relay_call).strip().upper() if relay_call else "")

                # Origen real en formato humano (ya lo calculas antes como src_label)
                origin = src_label.strip().upper()

                if relay_call and relay_call != "ALL":
                    # Formato final: QXT3>30QXT3: mensaje
                    payload = f"{origin}>{relay_call}: {body}"
                    out_line = f"{relay_call}: {payload}"
                else:
                    # Sin relay → envío directo
                    payload = f"{origin}: {body}"
                    out_line = f"{to_call}: {payload}"

                self.app.send_text_line(out_line)
                return



            if self.vara_out_to == "ALL":
                out_line = f"ALL: {txt}".strip()
            else:
                out_line = f"{self.vara_out_to}: {txt}".strip()

            self.app.send_text_line(out_line)

        except Exception as e:
            self.app.log(f"[ERR] ❌ MeshBridge RX {self.app.mesh_name}  error: {e}", level=0)


    def _resolve_mesh_destination_id(self, dest: str):
        d = (dest or "").strip()
        if not d:
            return None
        if d.startswith("!"):  # ya es NodeId
            return d

        # Buscar por shortName en la "DB" de nodos conocida por la interfaz
        try:
            nodes = getattr(self.mesh.iface, "nodes", {}) or {}
            for node_id, node in nodes.items():
                u = (node or {}).get("user", {}) or {}
                sn = (u.get("shortName") or "").strip().upper()
                if sn and sn == d.upper():
                    # node_id suele ser algo como "!abcdef01"
                    return node_id
        except Exception:
            pass

        return None


    def _deny_reply_vara(self, src_call: str, msgid: int, dest: str, allow_set):
        try:
            if not getattr(self, "mesh_want_ack", False):
                return

            src_call = (src_call or "").strip().upper()
            if not src_call or src_call in ("ALL", "CQ"):
                return

            mid = msgid if msgid is not None else -1
            allowed_txt = ",".join(sorted(allow_set)) if allow_set else "-"

            deny_text = f"!FWD_DENY {mid} {dest} NOT_ALLOWED"

            # ✅ Enviar sin esperar ACK para evitar bloqueos/retries largos
            self.app.send_dm_no_wait(src_call, deny_text)

        except Exception as e:
            self.app.log(f"[WARN] deny-reply failed: {e}", level=1)




    # ---------- VARA -> Mesh ----------
    def on_vara_text(self, src: str, dst: str, text: str, is_bcast: bool, msgid: int = None):
        """
        Recibe texto desde VARA y lo reenvía a Meshtastic SOLO si viene en formato forwarding:
            >DEST: mensaje
        donde DEST puede ser ShortName (QXT3) o NodeId (!abcdef01).

        Objetivo:
          - Que en Mesh se vea: "30QXT3: mensaje" (limpio)
          - Sin prefijos técnicos acumulados
          - Anti-eco robusto (TTL cache)
        """
        try:
            # 1) Limpia tags técnicos que puedan venir pegados de otros bridges
            clean = self._clean_text(text)

            # Forwarding explícito soportado:
            #   >DEST: mensaje   (relay clásico)
            #   @DEST mensaje    (tu atajo)
            #   @DEST: mensaje
            #   @DEST, mensaje
            if clean.startswith(">"):
                fwd = clean
            elif clean.lstrip().startswith("@"):
                t = clean.lstrip()
                # Parse @DEST ...

                m = re.match(r"^@([A-Za-z0-9_-]{2,16})\s*[:,]?\s*(.*)\s*$", t)
                if not m:
                    return
                dest = (m.group(1) or "").strip()
                msg  = (m.group(2) or "").strip()
                if not dest or not msg:
                    return
                # Convertimos a tu formato interno: >DEST: mensaje
                fwd = f">{dest}: {msg}"
            else:
                # ---------------------------------------------
                # NUEVO: canal por defecto (--mesh-channel-name)
                # ---------------------------------------------
                try:
                    ch_idx = None

                    # Resolver canal por nombre si existe
                    if getattr(self, "mesh_channel_name", None) and hasattr(self.mesh, "resolve_channel_index"):
                        ch_idx = self.mesh.resolve_channel_index(None, self.mesh_channel_name)

                    if ch_idx is None:
                        return  # No hay canal por defecto configurado

                    rendered = f"{src}: {clean}".strip()

                    # Anti-eco cache
                    k_fwd = self._key("vara2mesh", src=src, dst=f"chan#{ch_idx}", text=rendered)
                    self._mark(k_fwd)

                    self.app.log(f"[{self.app.vara_name} -> {self.app.mesh_name} CH] {src} -> {self.mesh_channel_name}: {clean}", level=1)

                    self._mesh_send(rendered, destination_id=None, channel_index=ch_idx, want_ack=False)

                    return

                except Exception as e:
                    self.app.log(f"[ERR] {self.app.vara_name} -> {self.app.mesh_name} default channel: {e}", level=0)
                    return


            # 2) Anti-eco "compat" (por si aún entra texto marcado como Mesh->VARA de ESTE bridge)
            local_mesh_prefix = f"[mesh@{self.app.mycall}] "
            if clean.startswith(local_mesh_prefix):
                return

            # 3) Anti-eco robusto por caché (evita rebotes incluso sin tags)
            k_back = self._key("mesh2vara", src=src, dst=dst, text=clean)
            if self._seen_before(k_back):
                return

            # 4) Parse: >DEST: mensaje
            body = fwd[1:].strip()
            if ":" not in body:
                self.app.log(self.app.var_text("warn_forward_malformed", src=src, text=clean), level=1)
                return

            mesh_dest, mesh_msg = body.split(":", 1)
            mesh_dest = mesh_dest.strip()
            mesh_msg = mesh_msg.strip()
            
            # ---------------------------------------------------------
            # LIMITADOR (WHITELIST) de destinos Meshtastic
            #   - Si self.mesh_allow_dest_shortnames es None => permitir cualquier destino
            #   - Si no => solo permitir esos shortnames
            # ---------------------------------------------------------
            if getattr(self, "mesh_allow_dest_shortnames", None):
                allow = self.mesh_allow_dest_shortnames

                dest_in = (mesh_dest or "").strip()

                if dest_in.startswith("!"):
                    # El mensaje pide nodeId directo. Intentamos mapearlo a shortName para decidir.
                    dest_sn = None
                    try:
                        nodes = getattr(self.mesh.iface, "nodes", {}) or {}
                        node = nodes.get(dest_in)
                        u = (node or {}).get("user", {}) or {}
                        dest_sn = (u.get("shortName") or "").strip().upper() or None
                    except Exception:
                        dest_sn = None

                    if not dest_sn:
                        self.app.log(
                            f"[DENY] {self.app.vara_name} -> {self.app.mesh_name} destino '{dest_in}' no permitido "
                            f"(no se pudo resolver shortName; permitidos: {','.join(sorted(allow))})",
                            level=1
                        )
                        self._deny_reply_vara(src_call=src, msgid=msgid, dest=dest_in, allow_set=allow)  # <-- AÑADIR
                        return


                    if dest_sn not in allow:
                        self.app.log(
                            f"[DENY] {self.app.vara_name} -> {self.app.mesh_name} destino '{dest_sn}' ({dest_in}) no permitido "
                            f"(permitidos: {','.join(sorted(allow))})",
                            level=1
                        )
                        self._deny_reply_vara(src_call=src, msgid=msgid, dest=dest_sn, allow_set=allow)  # <-- AÑADIR
                        return


                else:
                    # DEST es shortname
                    dest_sn = dest_in.upper()
                    if dest_sn not in allow:
                        self.app.log(
                            f"[DENY] {self.app.vara_name} -> {self.app.mesh_name} destino '{dest_sn}' no permitido "
                            f"(permitidos: {','.join(sorted(allow))})",
                            level=1
                        )
                        self._deny_reply_vara(src_call=src, msgid=msgid, dest=dest_sn, allow_set=allow)
                        return


            if not mesh_dest or not mesh_msg:
                self.app.log(self.app.var_text("warn_forward_incomplete", src=src, text=clean), level=1)
                return

           # ---------------------------------------------------------
            # PASO 2: extraer cabecera de ruta si viene como:
            #   >DEST: [QXT6>30QXT1] mensaje
            # ---------------------------------------------------------
            route = None  # <-- MUY IMPORTANTE

            m_route = re.match(r"^\[([^\]]{2,120})\]\s*(.*)$", mesh_msg)
            if m_route:
                route = (m_route.group(1) or "").strip()
                mesh_msg = (m_route.group(2) or "").strip()

                # Añadir hop local (esta estación) a la ruta
                if route and not route.endswith(self.app.mycall):
                    route = f"{route}>{self.app.mycall}"

            # ---------------------------------------------------------
            # Construcción del texto final para Meshtastic
            # ---------------------------------------------------------
            if route:
                origin = route.split(">", 1)[0].strip()   # primer nodo = emisor real
                rendered = f"[{origin}] {mesh_msg}".strip()
            else:
                rendered = f"[{src}] {mesh_msg}".strip()


            # 5) Render final (lo que verá Meshtastic)
            if route:
                origin = route.split(">", 1)[0].strip()  # primer salto => QXT6
                rendered = f"[{origin}] {mesh_msg}".strip()
            else:
                rendered = f"[{src}] {mesh_msg}".strip()



            # 6) Resolver destino: ShortName -> NodeId, o usar NodeId si ya viene con "!"
            dest_id = None
            dest_in = mesh_dest

            if dest_in.startswith("!"):
                dest_id = dest_in
            else:
                try:
                    nodes = getattr(self.mesh.iface, "nodes", {}) or {}
                    for node_id, node in nodes.items():
                        u = (node or {}).get("user", {}) or {}
                        sn = (u.get("shortName") or "").strip().upper()
                        if sn and sn == dest_in.upper():
                            dest_id = node_id  # normalmente "!abcdef01"
                            break
                except Exception:
                    dest_id = None

            if not dest_id:
                self.app.log(self.app.var_text("warn_nodeid_not_found", dest=mesh_dest),level=1)
                return

            # 7) Marca en caché lo que estamos a punto de meter en Mesh (para no rebotarlo luego)
            k_fwd = self._key("vara2mesh", src=src, dst=dest_id, text=rendered)
            self._mark(k_fwd)

            # 8) Log claro
            # Este log debe reflejar solo el salto actual (esta estación -> destino mesh)
            self.app.log(f"[{self.app.vara_name} -> {self.app.mesh_name}] {self.app.mycall} > {mesh_dest} ({dest_id}): {mesh_msg}", level=1)


            # 9) Envío DM a Mesh (destino resuelto)
            self._mesh_send(rendered, destination_id=dest_id, channel_index=None, want_ack=self.mesh_want_ack)


        except Exception as e:
            self.app.log(f"[ERR] ❌ MeshBridge TX {self.app.mesh_name}  error: {e}", level=0)



def main():
    ap = argparse.ArgumentParser(description="Interactive chat + file transfer over VARA HF (KISS/TCP) & Meshtastic Bridge.")
    ap.add_argument("--call", required=True, help="Your callsign, e.g. EA1ABC")
    ap.add_argument("--host", default="127.0.0.1", help="KISS TCP host (VARA), default 127.0.0.1")
    ap.add_argument("--port", type=int, default=8100, help="KISS TCP port (VARA), default 8100")
    ap.add_argument("--axdst", default="APVARA", help="AX.25 destination field (cosmetic), default APVARA")

    ap.add_argument("--mesh-serial", default=None, help="Meshtastic serial device (COMx or /dev/ttyUSB0)")
    ap.add_argument("--mesh-host", default=None, help="Meshtastic IP[:PORT] (default 4403)")
    ap.add_argument("--mesh-dest-id", default=None, help="DestinationId (e.g. !abcdef01) to send to a specific node")
    ap.add_argument("--mesh-allow-dest-shortname", default=None, help="Comma-separated Meshtastic destination ShortNames allowed for relay (e.g. QXT3,QXT6). If omitted, any destination is allowed.")

    ap.add_argument("--mesh-channel-index", type=int, default=None, help="Meshtastic channel (index)")
    ap.add_argument("--mesh-channel-name", default=None, help="Meshtastic channel (name)")
    ap.add_argument("--mesh-want-ack", action="store_true", help="Request ACK when sending to a specific node (destinationId)")

    ap.add_argument("--bridge-mesh", action="store_true", help="Enable Meshtastic <-> VARA bridge")
    ap.add_argument("--bridge-varato-mesh-prefix", default="[VARA] ", help="Prefix for traffic from VARA to Mesh")
    ap.add_argument("--bridge-meshto-vara-prefix", default="[MESH] ", help="Prefix for traffic from Mesh to VARA")
    ap.add_argument("--bridge-mesh-to-vara", default="ALL", help="VARA destination for traffic coming from Mesh (ALL or CALL)")

    ap.add_argument("--monitor", action="store_true", help="Monitor mode: show readable messages even if not addressed to me/ALL (no ACK)")
    ap.add_argument("-v", "--verbose", type=int, choices=[0, 1, 2], default=1, help="Log level: 0=errors, 1=normal, 2=debug")
    ap.add_argument("--log-mode", choices=["console", "file", "both"], default="console", help="Log destination: console, file, or both")
    ap.add_argument("--log-file", default="meshfest.log", help="Log file path (if --log-mode includes file)")

    ap.add_argument("--lang", choices=["es", "en"], default="en", help="Language of messages: es (Spanish) | en (English)")


    args = ap.parse_args()

    app = VaraApp(args.call, args.host, args.port, ax25_dst=args.axdst, verbose=args.verbose, log_mode=args.log_mode, log_file=args.log_file, lang=args.lang)
    app.verbose = args.verbose
    # Guardar etiqueta literal para sustituir "VARA" en logs/tags
    app.vara_name = (args.bridge_varato_mesh_prefix or "VARA").replace("{call}", app.mycall)
    # Guardar etiqueta literal para sustituir "MESH" en logs/tags
    app.mesh_name = (args.bridge_meshto_vara_prefix or "MESH").replace("{call}", app.mycall)

    print(" ")
    print(f"{ANSI_CYAN}{HELP_HEADER}{app.var_text('help_body')}{ANSI_RESET}")

    app.kiss.connect(app)
    
    if not app.kiss.connect(app):
        #app.log("[ERR] ❌ No hay conexión KISS. Saliendo.", level=0)
        app.log(app.var_text("err_no_kiss_connection"), level=0)

        return
    app.monitor = bool(args.monitor)
    if app.monitor:
        app.log(app.var_text("info_monitor_on"), level=1)
    
    # --mesh-allow-dest-shortname
    # Permitir solo reenviar a determinados nodos, sino todos los nodos destino son permitodos
    allowed_shortnames = None
    if args.mesh_allow_dest_shortname:
        allowed_shortnames = {
            s.strip().upper()
            for s in args.mesh_allow_dest_shortname.split(",")
            if s.strip()}

    
    mesh = None
    if args.bridge_mesh:
        if not args.mesh_serial and not args.mesh_host:
            #app.log("[ERR] Para --bridge-mesh debes indicar --mesh-serial o --mesh-host", level=0)
            app.log(app.var_text("err_bridge_mesh_missing_iface"), level=0)
            return

        mesh = Mesh(serial_path=args.mesh_serial, hostport=args.mesh_host)
        
        # Espera inicial para que Meshtastic complete handshake TCP
        app.log("[INFO] ✅ Connecting to Meshtastic...", level=1)
        time.sleep(5.0)

        # Warm-up real forzando lectura de canales
        app.log("[INFO] ✅ Warm-up Meshtastic (Channels)...", level=1)

        for i in range(3):
            try:
                #ch = mesh.iface.getChannelList()
                ch = mesh.get_channels()
                if ch:
                    app.log("[INFO] ✅ Meshtastic Ready", level=1)
                    break
            except Exception as e:
                #app.log(f"[WARN] Meshtastic aún no listo ({e}) intento {i+1}/3", level=1)
                app.log(app.var_text("warn_mesh_not_ready_retry", error=e, attempt=i+1), level=1)
                time.sleep(2.0)
                
        else:
            #app.log("[WARN] ⚠️ Meshtastic no confirmó readiness, continúo igualmente...", level=1)
            app.log(app.var_text("warn_mesh_not_ready"), level=1)


        mesh_dest_id = mesh.resolve_dest_id(args.mesh_dest_id, args.mesh_allow_dest_shortname)
      
        #Comprobamos si el nodo destino ha sido escuchado por el nodo que hara el reenvio:
        if args.mesh_allow_dest_shortname and not mesh_dest_id:
            #app.log(f"[ERR] ❌ No se encontró el nodo '{args.mesh_dest_shortname}' "f"en iface.nodes del nodo bridge. Aborto.",level=0)
            app.log(app.var_text("err_mesh_shortname_not_found", shortname=args.mesh_allow_dest_shortname), level=0)
            return

        if args.mesh_dest_id and not mesh_dest_id:
            #app.log(f"[ERR] ❌ No se pudo usar destinationId '{args.mesh_dest_id}'. Aborto.",level=0)
            app.log(app.var_text("err_mesh_dest_id_invalid", dest_id=args.mesh_dest_id), level=0)
            return

        mesh_chan_idx = mesh.resolve_channel_index(args.mesh_channel_index, args.mesh_channel_name)
        
        if args.mesh_allow_dest_shortname or args.mesh_dest_id != None:
            app.log(app.var_text("info_mesh_dest_confirmed", dest_input=args.mesh_allow_dest_shortname or args.mesh_dest_id, dest_id=mesh_dest_id), level=1)

        if allowed_shortnames:
            app.log(f"[INFO] ✅ Relay restricted to Meshtastic destinations: {', '.join(sorted(allowed_shortnames))}", level=1)

        # Construcción dinámica de prefijos
        vara_to_mesh_prefix = args.bridge_varato_mesh_prefix.replace("{call}", app.mycall)
        mesh_to_vara_prefix = args.bridge_meshto_vara_prefix.replace("{call}", app.mycall)

        app.bridge = MeshBridge(
            app=app,
            mesh=mesh,
            mesh_dest_id=mesh_dest_id,
            mesh_channel_index=mesh_chan_idx,
            mesh_channel_name=args.mesh_channel_name,
            mesh_want_ack=bool(args.mesh_want_ack),
            mesh_allow_dest_shortnames=allowed_shortnames,
            vara_out_to=args.bridge_mesh_to_vara,
            mesh_to_vara_prefix=mesh_to_vara_prefix,
            vara_to_mesh_prefix=vara_to_mesh_prefix,
        )


    stop_evt = threading.Event()

    # Crear hilos SIEMPRE (no dentro de un if que pueda no ejecutarse)
    t_rx = threading.Thread(target=rx_thread, args=(app, stop_evt), daemon=True)
    t_in = threading.Thread(target=input_thread, args=(app, stop_evt), daemon=True)

    t_rx.start()
    t_in.start()

    # Mantener vivo el main
    try:
        while not stop_evt.is_set():
            time.sleep(0.2)
    except KeyboardInterrupt:
        stop_evt.set()


    # Cerrar mesh al FINAL (no antes)
    if mesh:
        try:
            mesh.close()
        except Exception:
            pass

           
    # keep main alive
    while not stop_evt.is_set():
        time.sleep(0.2)
    
    app.log("Leaving MesHFest...")
    app.kiss.close()
    app.close()
    

if __name__ == "__main__":
    main()
