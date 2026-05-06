# PicoW MQTT Connection Guide

Quick reference for connecting your Raspberry Pi Pico W to the GroundControl MQTT broker.

## MicroPython Example

```python
import network
import umqtt.simple
import machine
import time
import json
from machine import Pin

# Configuration - update these values for your setup
CONFIG = {
    "wifi_ssid": "YourWiFiName",
    "wifi_password": "YourWiFiPassword",
    "mqtt_broker": "192.168.178.47",  # Change to your Pi's IP
    "mqtt_port": 1883
}

WIFI_SSID = CONFIG["wifi_ssid"]
WIFI_PASSWORD = CONFIG["wifi_password"]
MQTT_BROKER = CONFIG["mqtt_broker"]
MQTT_PORT = CONFIG["mqtt_port"]

# Unique client ID (use last 4 chars of MAC)
CLIENT_ID = f"pico-{machine.unique_id():x}"[-8:]

def connect_wifi():
    """Connect to WiFi"""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print(f"Connecting to {WIFI_SSID}...")
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.5)
            print(".", end="")
    print("\nWiFi connected!")
    print(f"IP: {wlan.ifconfig()[0]}")
    return wlan

def connect_mqtt():
    """Connect to MQTT broker"""
    print(f"Connecting to MQTT broker {MQTT_BROKER}...")
    client = umqtt.simple.MQTTClient(
        client_id=CLIENT_ID,
        server=MQTT_BROKER,
        port=MQTT_PORT,
        keepalive=60
    )
    client.connect()
    print(f"Connected as {CLIENT_ID}")
    return client

# Main
try:
    wlan = connect_wifi()
    client = connect_mqtt()

    # Publish a test message
    client.publish(f"{CLIENT_ID}/status", "online")
    print("Sent status: online")

    # Send sensor data example
    counter = 0
    while True:
        counter += 1
        payload = f"{{\"count\": {counter}, \"temp\": 20 + (counter % 10)}}}"
        client.publish(f"{CLIENT_ID}/data", payload)
        print(f"Sent: {payload}")

        time.sleep(5)

finally:
    client.disconnect()
    print("Disconnected")
```

## C/C++ Example (pico-sdk)

```c
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "mqtt_client.h"

#define WIFI_SSID "YourWiFiName"
#define WIFI_PASSWORD "YourWiFiPassword"
#define MQTT_BROKER "192.168.1.100"
#define MQTT_PORT 1883

int main() {
    stdio_init_all();

    // Initialize WiFi
    if (cyw43_arch_init_with_country(CYW43_COUNTRY_UK)) {
        printf("WiFi init failed\n");
        return 1;
    }

    cyw43_arch_enable_sta_mode();

    // Connect to WiFi
    printf("Connecting to WiFi...\n");
    if (cyw43_arch_wifi_connect_timeout_ms(WIFI_SSID, WIFI_PASSWORD,
                                           CYW43_AUTH_WPA2_AES_PSK, 30000)) {
        printf("WiFi connection failed\n");
        return 1;
    }
    printf("WiFi connected!\n");

    // TODO: Initialize MQTT client and publish
    // Use mqtt_client.h from pico-examples

    while (true) {
        sleep_ms(1000);
    }

    cyw43_arch_deinit();
    return 0;
}
```

## Publishing Topics

The GroundControl dashboard will automatically detect new devices. Use these topic patterns:

```
<device-id>/status      - Device status (online/offline)
<device-id>/data        - Sensor data (JSON recommended)
<device-id>/temp        - Temperature reading
<device-id>/humidity    - Humidity reading
<device-id>/alert       - Alerts/notifications
```

## JSON Data Format

```json
{
    "temperature": 22.5,
    "humidity": 65,
    "timestamp": 1710745200,
    "battery": 85
}
```

## Testing Your Connection

1. Flash the code to your Pico W
2. Check GroundControl dashboard at `http://<pi-ip>:8000`
3. Your device should appear in the "Devices" table
4. Messages will appear in "Recent Messages"

## NFC Card Security (Required Firmware Update)

Since the introduction of the 3VL security model, the firmware must:

1. **Receive the sector key** from the backend via MQTT and keep it in RAM
2. **Authenticate to sector 1** with this key before reading card data
3. **Send the signature** (member_id + HMAC) from sector 1 in the scan payload
4. **Write enrollment data** into sector 1 and update the sector trailer with the new key

### Card data layout (Sector 1)

| Block | Content |
|---|---|
| 4 | `member_id` as ASCII, null-padded to 16 bytes |
| 5 | HMAC-SHA256 digest bytes 0–15 (raw bytes) |
| 6 | HMAC-SHA256 digest bytes 16–31 (raw bytes) |
| 7 | Sector trailer: new KeyA \| `FF 07 80 69` \| KeyB (unused) |

### MQTT topics for security features

| Topic | Direction | Description |
|---|---|---|
| `groundcontrol/nfc/config` | Server → PicoW | Retained: sector key as JSON `{"sector_key": "a1b2c3d4e5f6", "sector": 1}` |
| `{device_id}/command` | Server → PicoW | Enrollment command `{"action": "write_card", "member_id": ..., "signature": ..., "sector_key": ...}` |
| `{device_id}/scan` | PicoW → Server | Scan event — now includes `member_id` and `signature` when sector 1 is readable |
| `{device_id}/write_result` | PicoW → Server | Result after enrollment `{"uid": ..., "member_id": ..., "status": "ok"}` |

### Complete firmware example (`main.py`)

```python
import network
import machine
import time
import json
import ubinascii
from umqtt.simple import MQTTClient
from mfrc522 import MFRC522

# ─── Configuration ────────────────────────────────────────────────────────────
WIFI_SSID   = "your-wifi"
WIFI_PASS   = "your-password"
MQTT_BROKER = "192.168.1.100"  # IP of the Pi running GroundControl
DEVICE_ID   = "pico_nfc_01"   # Unique device ID

# ─── State ────────────────────────────────────────────────────────────────────
_sector_key  = bytearray([0xFF]*6)  # Factory default until config arrives
_default_key = bytearray([0xFF]*6)

# ─── NFC reader (RC522 on SPI0) ───────────────────────────────────────────────
rdr = MFRC522(spi_id=0, sck=18, mosi=19, miso=16, cs=17, rst=20)

# Sector 1 block numbers
BLOCK_MEMBER_ID = 4    # member_id (16 bytes, null-padded)
BLOCK_SIG_HI    = 5    # HMAC bytes 0–15
BLOCK_SIG_LO    = 6    # HMAC bytes 16–31
BLOCK_TRAILER   = 7    # Keys + access bits
ACCESS_BITS = bytearray([0xFF, 0x07, 0x80, 0x69])

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _pad(data, length=16):
    return bytearray(data[:length].ljust(length, b'\x00'))

def _strip(data):
    return bytes(data).rstrip(b'\x00').decode('utf-8', errors='ignore').strip()

def read_secure_sector(uid):
    """Authenticate to sector 1 and read member_id + signature.
    Tries custom key first, falls back to factory default.
    Returns dict {member_id, signature} or None on failure."""
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
                print("Read error:", e)
                rdr.stop_crypto1()
                return None
    rdr.stop_crypto1()
    return None

def write_secure_sector(uid, member_id, signature, write_key):
    """Write enrollment data to sector 1 and update the sector trailer.
    First enrollment: authenticates with factory default key, writes data, updates trailer.
    Re-enrollment: authenticates with current key, overwrites data blocks."""
    block4  = _pad(member_id.encode()[:15])
    sig_raw = bytearray.fromhex(signature)
    block5  = bytearray(sig_raw[:16])
    block6  = bytearray(sig_raw[16:32])
    trailer = bytearray(write_key[:6]) + ACCESS_BITS + bytearray([0xFF]*6)

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
                print("Write error:", e)
                rdr.stop_crypto1()
                return False
    rdr.stop_crypto1()
    print("Enrollment failed: authentication denied")
    return False

# ─── MQTT callbacks ───────────────────────────────────────────────────────────

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
                print("Sector key updated")
        except Exception as e:
            print("Config error:", e)

    elif topic_str == f"{DEVICE_ID}/command":
        try:
            cmd = json.loads(msg)
            if cmd.get("action") == "write_card":
                _handle_enrollment(cmd)
        except Exception as e:
            print("Command error:", e)

def _handle_enrollment(cmd):
    """Wait up to 30 s for a card tap, then write enrollment data."""
    member_id  = cmd.get("member_id", "")
    signature  = cmd.get("signature", "")
    key_hex    = cmd.get("sector_key", "")
    request_id = cmd.get("request_id", "")

    if not member_id or len(signature) != 64:
        print("Invalid enrollment command")
        return

    write_key = bytearray.fromhex(key_hex) if len(key_hex) == 12 else _sector_key
    print(f"Waiting for card for {member_id} ...")
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
        print(f"Card detected: {uid_str}")

        status = "ok" if write_secure_sector(uid, member_id, signature, write_key) else "error"
        result = {"uid": uid_str, "member_id": member_id,
                  "request_id": request_id, "status": status}
        mqtt_client.publish(f"{DEVICE_ID}/write_result", json.dumps(result))
        return

    print("Timeout: no card presented")

# ─── Connection setup ─────────────────────────────────────────────────────────

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    while not wlan.isconnected():
        time.sleep(0.5)
    print("WiFi connected:", wlan.ifconfig()[0])

def connect_mqtt():
    global mqtt_client
    client = MQTTClient(DEVICE_ID, MQTT_BROKER, keepalive=60)
    client.set_callback(on_message)
    client.connect()
    # Subscribe to retained config first — sector key arrives immediately
    client.subscribe("groundcontrol/nfc/config")
    client.subscribe(f"{DEVICE_ID}/command")
    client.publish(f"{DEVICE_ID}/status", json.dumps({"status": "online", "nfc_ok": True}))
    mqtt_client = client
    print("MQTT connected as", DEVICE_ID)
    return client

# ─── Main scan loop ───────────────────────────────────────────────────────────

def scan_loop(client):
    last_uid, last_scan_time, last_heartbeat = None, 0, time.time()

    while True:
        client.check_msg()  # Process MQTT messages (non-blocking)

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

        # Debounce: ignore same card within 3 seconds
        if uid_str == last_uid and (now - last_scan_time) < 3:
            rdr.stop_crypto1()
            time.sleep(0.1)
            continue

        last_uid, last_scan_time = uid_str, now
        payload = {"uid": uid_str, "tag_type": hex(tag_type)}

        # Read secure sector 1 with custom key
        secure = read_secure_sector(uid_bytes)
        if secure:
            payload["member_id"] = secure["member_id"]
            payload["signature"]  = secure["signature"]

        client.publish(f"{DEVICE_ID}/scan", json.dumps(payload))
        print("Scan:", uid_str, "→", payload.get("member_id", "(legacy)"))
        time.sleep(0.1)

# ─── Entry point ──────────────────────────────────────────────────────────────

connect_wifi()
client = connect_mqtt()
time.sleep(0.5)    # Allow retained config message to arrive
client.check_msg() # Process sector key immediately
scan_loop(client)
```

### Implementation notes

**First scan before enrollment:** If a card has never been enrolled, `read_secure_sector()`
fails with the custom key and falls back to the factory default. The signature stays
empty — the server treats the scan as LEGACY.

**Sector trailer write:** `write_secure_sector()` always writes block 7 (the trailer).
This is what switches the key on the card. After the first successful write, the factory
default key is permanently invalid for that card.

**MFRC522 library:** The library must support `auth()`, `read()`, `write()`, and
`stop_crypto1()`. Recommended:
[danjperron/MFRC522-python](https://github.com/danjperron/MFRC522-python) for MicroPython.

**Reconnect:** On MQTT disconnect, call `connect_mqtt()` again. The broker re-delivers
the retained `groundcontrol/nfc/config` automatically — the sector key is restored
without any extra logic.

## Troubleshooting

- **Not appearing in dashboard?** Check MQTT broker IP is correct
- **WiFi not connecting?** Verify SSID and password
- **Messages not received?** Ensure Mosquitto service is running: `sudo systemctl status mosquitto`
- **Sector 1 authentication failing?** The sector key on the PicoW may differ from the one used during enrollment. Check that `SECRET_KEY` in `config.json` has not changed since the cards were last enrolled.

To monitor all MQTT messages in real-time:
```bash
mosquitto_sub -h localhost -t "#" -v
```
