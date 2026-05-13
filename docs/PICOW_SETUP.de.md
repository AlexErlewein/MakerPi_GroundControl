# Pico W Setup

Anleitung zur Einrichtung von Raspberry Pi Pico W Geräten als NFC-Scanner und Sensoren.

## Hardware

### Benötigt

- Raspberry Pi Pico W
- NFC-Reader RC522
- Jumper-Kabel
- USB-Kabel

### Anschluss (RC522 → Pico W)

| RC522 | Pico W |
|-------|--------|
| VCC | 3V3 (OUT) |
| GND | GND |
| MOSI | GP19 (SPI0 MOSI) |
| MISO | GP16 (SPI0 MISO) |
| SCK | GP18 (SPI0 SCK) |
| SDA | GP17 (SPI0 CS) |
| RST | GP20 |

## Software

### Firmware installieren

1. **MicroPython herunterladen**
   - https://micropython.org/download/rp2-pico-w/
   - `rp2-pico-w-<version>.uf2`

2. **Aufspielen**
   - BOOTSEL-Taste am Pico W gedrückt halten
   - USB-Kabel anschließen
   - RPi-RP2-Laufwerk erscheint
   - `.uf2` Datei kopieren
   - Pico W startet neu

### Code installieren

**Datei: `main.py` auf dem Pico W**

```python
import network
import machine
import time
from umqtt.simple import MQTTClient

# Konfiguration
WIFI_SSID = "dein-wlan"
WIFI_PASS = "wlan-passwort"
MQTT_BROKER = "192.168.1.100"  # IP des Pi mit GroundControl
DEVICE_ID = "pico_w_001"

# WLAN verbinden
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASS)

while not wlan.isconnected():
    time.sleep(1)

print("WLAN verbunden:", wlan.ifconfig()[0])

# MQTT Client
client = MQTTClient(DEVICE_ID, MQTT_BROKER)
client.connect()
print("MQTT verbunden")

# NFC-Reader (vereinfacht - ohne MFRC522-Lib für Lesbarkeit)
# In Produktion: MFRC522 Library verwenden
def read_nfc():
    # Hier NFC-Leselogik
    # Rückgabe: uid (string) oder None
    return None  # Platzhalter

# Main Loop
last_status = time.time()

while True:
    # NFC prüfen
    uid = read_nfc()
    if uid:
        topic = f"makerpi/devices/{DEVICE_ID}/event"
        msg = f'{{"uid":"{uid}","action":"scan"}}'
        client.publish(topic, msg)
        print("NFC gescannt:", uid)
        time.sleep(3)  # Debounce
    
    # Status-Heartbeat alle 30s
    if time.time() - last_status > 30:
        topic = f"makerpi/devices/{DEVICE_ID}/status"
        msg = f'{{"state":"online","timestamp":{time.time()}}}'
        client.publish(topic, msg)
        last_status = time.time()
    
    time.sleep(0.1)
```

### Libraries

Für vollständige NFC-Funktionalität:

```bash
# MFRC522 Library
# Download: https://github.com/danjperron/MFRC522-python
# Dateien auf Pico W kopieren:
# - mfrc522.py
```

## Konfiguration in GroundControl

Geräte werden automatisch erkannt – keine manuelle Registrierung nötig.

Erste Nachricht erscheint im Dashboard unter "Geräte".

## Troubleshooting

### WLAN verbindet nicht

```python
# Debug-Output
print(wlan.status())  # 3 = connected
print(wlan.ifconfig())  # IP-Adresse prüfen
```

### MQTT verbindet nicht

- Broker-IP prüfen
- Mosquitto läuft? `sudo systemctl status mosquitto`
- Firewall: Port 1883 offen?

### NFC wird nicht gelesen

- Verkabelung prüfen
- SPI-Pins korrekt?
- RC522-LED leuchtet?

## Mehrere Picos

Jeder Pico braucht eindeutige `DEVICE_ID`:

```python
# Pico 1
DEVICE_ID = "pico_w_001"

# Pico 2  
DEVICE_ID = "pico_w_002"
```

## Batteriebetrieb

Für mobilen Einsatz:

- LiPo-Akku mit JST-PH-Anschluss
- oder USB-Powerbank
- Laufzeit: ~8-12 Stunden mit 2000mAh

## Erweiterte Features

### Temperatur-Sensor

```python
import dht

sensor = dht.DHT22(machine.Pin(22))

def read_sensors():
    sensor.measure()
    temp = sensor.temperature()
    humidity = sensor.humidity()
    return {"temp": temp, "humidity": humidity}
```

Topic: `makerpi/devices/{DEVICE_ID}/sensors`

### Taster für manuelle Aktionen

```python
button = machine.Pin(21, machine.Pin.IN, machine.Pin.PULL_UP)

if not button.value():  # Gedrückt
    client.publish(f"makerpi/devices/{DEVICE_ID}/event", 
                   '{"action":"button_pressed"}')
```

## Firmware-Updates

### Over-the-Air (OTA)

```python
# OTA-Support hinzufügen
# Siehe: https://github.com/rdehuyar/micropython-ota

import ota

def check_update():
    ota.check_for_update(MQTT_BROKER, "firmware/latest.uf2")
```

## NFC-Kartensicherheit (Pflichtupdate)

Seit der Einführung des 3VL-Sicherheitsmodells muss die Firmware folgende Aufgaben übernehmen:

1. Den **Sektorschlüssel** vom Backend via MQTT empfangen und im RAM halten
2. Sich bei **Sektor 1** mit diesem Schlüssel authentifizieren, bevor Kartendaten gelesen werden
3. Die **Signatur** (member_id + HMAC) aus Sektor 1 auslesen und im Scan-Payload mitsenden
4. Beim **Einschreiben** die Daten in Sektor 1 schreiben und den Sektor-Trailer mit dem neuen Schlüssel aktualisieren

### Datenlayout auf der Karte (Sektor 1)

| Block | Inhalt |
|---|---|
| 4 | `member_id` als ASCII, auf 16 Bytes mit `\0` aufgefüllt |
| 5 | HMAC-SHA256-Digest Bytes 0–15 (Rohbytes) |
| 6 | HMAC-SHA256-Digest Bytes 16–31 (Rohbytes) |
| 7 | Sektor-Trailer: neuer KeyA \| `FF 07 80 69` \| KeyB (ungenutzt) |

### MQTT-Themen für die Sicherheitsfunktionen

| Thema | Richtung | Beschreibung |
|---|---|---|
| `groundcontrol/nfc/config` | Server → PicoW | Retained: Sektorschlüssel als JSON `{"sector_key": "a1b2c3d4e5f6", "sector": 1}` |
| `{device_id}/command` | Server → PicoW | Einschreibungsbefehl `{"action": "write_card", "member_id": ..., "signature": ..., "sector_key": ...}` |
| `{device_id}/scan` | PicoW → Server | Scan-Ereignis — jetzt mit `member_id` und `signature` wenn Sektor 1 lesbar |
| `{device_id}/write_result` | PicoW → Server | Ergebnis nach Einschreibung `{"uid": ..., "member_id": ..., "status": "ok"}` |

### Vollständiges Firmware-Beispiel (`main.py`)

```python
import network
import machine
import time
import json
import ubinascii
from umqtt.simple import MQTTClient
from mfrc522 import MFRC522

# ─── Konfiguration ────────────────────────────────────────────────────────────
WIFI_SSID   = "dein-wlan"
WIFI_PASS   = "wlan-passwort"
MQTT_BROKER = "192.168.1.100"   # IP des Pi mit GroundControl
DEVICE_ID   = "pico_nfc_01"     # Eindeutige Geräte-ID

# ─── Zustand ──────────────────────────────────────────────────────────────────
_sector_key  = bytearray([0xFF]*6)   # Werksstandard bis Konfiguration empfangen
_default_key = bytearray([0xFF]*6)

# ─── NFC-Reader (RC522 an SPI0) ───────────────────────────────────────────────
rdr = MFRC522(spi_id=0, sck=18, mosi=19, miso=16, cs=17, rst=20)

# Sektor-1-Blöcke
BLOCK_MEMBER_ID = 4    # member_id (16 Bytes, null-aufgefüllt)
BLOCK_SIG_HI    = 5    # HMAC Bytes 0–15
BLOCK_SIG_LO    = 6    # HMAC Bytes 16–31
BLOCK_TRAILER   = 7    # Schlüssel + Zugangsbits
ACCESS_BITS = bytearray([0xFF, 0x07, 0x80, 0x69])

# ─── Hilfsfunktionen ──────────────────────────────────────────────────────────

def _pad(data, length=16):
    return bytearray(data[:length].ljust(length, b'\x00'))

def _strip(data):
    return bytes(data).rstrip(b'\x00').decode('utf-8', errors='ignore').strip()

def read_secure_sector(uid):
    """Authentifiziert Sektor 1 und liest member_id + Signatur.
    Versucht erst den benutzerdefinierten Schlüssel, dann den Werksstandard.
    Gibt dict {member_id, signature} zurück oder None bei Fehler."""
    for key in [_sector_key, _default_key]:
        if rdr.auth(rdr.AUTHENT1A, BLOCK_MEMBER_ID, key, uid) == rdr.OK:
            try:
                d4 = rdr.read(BLOCK_MEMBER_ID)
                d5 = rdr.read(BLOCK_SIG_HI)
                d6 = rdr.read(BLOCK_SIG_LO)
                rdr.stop_crypto1()
                if not (d4 and d5 and d6):
                    return None
                member_id = _strip(d4[:16])
                sig_hex   = ubinascii.hexlify(bytes(d5[:16]) + bytes(d6[:16])).decode()
                return {"member_id": member_id, "signature": sig_hex} if member_id else None
            except Exception as e:
                print("Lesefehler:", e)
                rdr.stop_crypto1()
                return None
    rdr.stop_crypto1()
    return None

def write_secure_sector(uid, member_id, signature, write_key):
    """Schreibt Einschreibungsdaten in Sektor 1 und aktualisiert den Trailer.
    Erster Durchlauf: Werksstandard-Schlüssel → Daten schreiben → Trailer aktualisieren.
    Erneute Einschreibung: benutzerdefinierter Schlüssel → Daten überschreiben."""
    block4   = _pad(member_id.encode()[:15])
    sig_raw  = bytearray.fromhex(signature)
    block5   = bytearray(sig_raw[:16])
    block6   = bytearray(sig_raw[16:32])
    trailer  = bytearray(write_key[:6]) + ACCESS_BITS + bytearray([0xFF]*6)

    for key in [write_key, _default_key]:
        if rdr.auth(rdr.AUTHENT1A, BLOCK_MEMBER_ID, key, uid) == rdr.OK:
            try:
                ok  = rdr.write(BLOCK_MEMBER_ID, list(block4)) == rdr.OK
                ok &= rdr.write(BLOCK_SIG_HI,    list(block5)) == rdr.OK
                ok &= rdr.write(BLOCK_SIG_LO,    list(block6)) == rdr.OK
                ok &= rdr.write(BLOCK_TRAILER,   list(trailer)) == rdr.OK
                rdr.stop_crypto1()
                return ok
            except Exception as e:
                print("Schreibfehler:", e)
                rdr.stop_crypto1()
                return False
    rdr.stop_crypto1()
    print("Einschreibung fehlgeschlagen: Authentifizierung verweigert")
    return False

# ─── MQTT-Callbacks ───────────────────────────────────────────────────────────

mqtt_client = None

def on_message(topic, msg):
    global _sector_key
    topic_str = topic.decode()

    if topic_str == "groundcontrol/nfc/config":
        try:
            cfg     = json.loads(msg)
            key_hex = cfg.get("sector_key", "")
            if key_hex and len(key_hex) == 12:
                _sector_key = bytearray.fromhex(key_hex)
                print("Sektorschlüssel aktualisiert")
        except Exception as e:
            print("Konfigurationsfehler:", e)

    elif topic_str == f"{DEVICE_ID}/command":
        try:
            cmd = json.loads(msg)
            if cmd.get("action") == "write_card":
                _handle_enrollment(cmd)
        except Exception as e:
            print("Befehlsfehler:", e)

def _handle_enrollment(cmd):
    """Wartet bis zu 30 Sekunden auf eine Karte und schreibt Einschreibungsdaten."""
    member_id  = cmd.get("member_id", "")
    signature  = cmd.get("signature", "")
    key_hex    = cmd.get("sector_key", "")
    request_id = cmd.get("request_id", "")

    if not member_id or len(signature) != 64:
        print("Ungültiger Einschreibungsbefehl")
        return

    write_key = bytearray.fromhex(key_hex) if len(key_hex) == 12 else _sector_key
    print(f"Warte auf Karte für {member_id} ...")
    deadline = time.time() + 30

    while time.time() < deadline:
        stat, tag_type = rdr.request(rdr.REQIDL)
        if stat != rdr.OK:
            time.sleep(0.1)
            continue
        stat, uid = rdr.anticoll()
        if stat != rdr.OK or not rdr.select_tag(uid):
            time.sleep(0.1)
            continue

        uid_str = ubinascii.hexlify(bytearray(uid)).decode().upper()
        print(f"Karte erkannt: {uid_str}")

        status = "ok" if write_secure_sector(uid, member_id, signature, write_key) else "error"
        result = {"uid": uid_str, "member_id": member_id,
                  "request_id": request_id, "status": status}
        mqtt_client.publish(f"{DEVICE_ID}/write_result", json.dumps(result))
        return

    print("Timeout: keine Karte aufgelegt")

# ─── Verbindungsaufbau ────────────────────────────────────────────────────────

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    while not wlan.isconnected():
        time.sleep(0.5)
    print("WLAN verbunden:", wlan.ifconfig()[0])

def connect_mqtt():
    global mqtt_client
    client = MQTTClient(DEVICE_ID, MQTT_BROKER, keepalive=60)
    client.set_callback(on_message)
    client.connect()
    # Retained Konfigurationsnachricht sofort empfangen
    client.subscribe("groundcontrol/nfc/config")
    client.subscribe(f"{DEVICE_ID}/command")
    client.publish(f"{DEVICE_ID}/status", json.dumps({"status": "online", "nfc_ok": True}))
    mqtt_client = client
    print("MQTT verbunden als", DEVICE_ID)
    return client

# ─── Haupt-Scan-Schleife ──────────────────────────────────────────────────────

def scan_loop(client):
    last_uid, last_scan_time, last_heartbeat = None, 0, time.time()

    while True:
        client.check_msg()   # MQTT-Nachrichten verarbeiten (nicht-blockierend)

        now = time.time()
        if now - last_heartbeat > 30:
            client.publish(f"{DEVICE_ID}/heartbeat",
                           json.dumps({"status": "online"}))
            last_heartbeat = now

        stat, tag_type = rdr.request(rdr.REQIDL)
        if stat != rdr.OK:
            time.sleep(0.05)
            continue

        stat, uid_bytes = rdr.anticoll()
        if stat != rdr.OK or not rdr.select_tag(uid_bytes):
            time.sleep(0.05)
            continue

        uid_str = ubinascii.hexlify(bytearray(uid_bytes)).decode().upper()

        # Entprellung: gleiche Karte innerhalb von 3 Sekunden ignorieren
        if uid_str == last_uid and (now - last_scan_time) < 3:
            rdr.stop_crypto1()
            time.sleep(0.1)
            continue

        last_uid, last_scan_time = uid_str, now
        payload = {"uid": uid_str, "tag_type": hex(tag_type)}

        # Sektor 1 mit Sicherheitsschlüssel lesen
        secure = read_secure_sector(uid_bytes)
        if secure:
            payload["member_id"] = secure["member_id"]
            payload["signature"]  = secure["signature"]

        client.publish(f"{DEVICE_ID}/scan", json.dumps(payload))
        print("Scan:", uid_str, "→", payload.get("member_id", "(legacy)"))
        time.sleep(0.1)

# ─── Start ────────────────────────────────────────────────────────────────────

connect_wifi()
client = connect_mqtt()
time.sleep(0.5)    # Kurz warten, damit retained Config ankommt
client.check_msg() # Sektorschlüssel sofort verarbeiten
scan_loop(client)
```

### Wichtige Hinweise zur Implementierung

**Erster Scan nach Einschreibung:** Wurde eine Karte noch nie eingeschrieben, schlägt
`read_secure_sector()` mit dem benutzerdefinierten Schlüssel fehl und fällt auf den
Werksstandard zurück. Die Signatur bleibt in diesem Fall leer — der Server behandelt
den Scan als LEGACY.

**Sektor-Trailer-Schreiben:** `write_secure_sector()` schreibt immer auch den Trailer
(Block 7). Das ist notwendig, damit nachfolgende Scans den neuen Schlüssel verwenden.
Nach dem ersten erfolgreichen Schreibvorgang ist der Werksstandard-Schlüssel für diese
Karte dauerhaft ungültig.

**MFRC522-Bibliothek:** Die verwendete Bibliothek muss `auth()`, `read()`, `write()`,
`stop_crypto1()` unterstützen. Empfehlung: [danjperron/MFRC522-python](https://github.com/danjperron/MFRC522-python)
für MicroPython.

**Reconnect:** Bei MQTT-Verbindungsunterbrechung `connect_mqtt()` erneut aufrufen.
Nach dem Wiederverbinden sendet der Broker die retained `groundcontrol/nfc/config`
automatisch — der Sektorschlüssel wird also ohne weiteres Zutun wiederhergestellt.

## Ressourcen

- MicroPython-Docs: https://docs.micropython.org/
- Pico W Datasheet: https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf
- MFRC522-Lib: https://github.com/danjperron/MFRC522-python
