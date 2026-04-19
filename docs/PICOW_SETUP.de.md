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

## Ressourcen

- MicroPython-Docs: https://docs.micropython.org/
- Pico W Datasheet: https://datasheets.raspberrypi.com/picow/pico-w-datasheet.pdf
- MFRC522-Lib: https://github.com/danjperron/MFRC522-python
