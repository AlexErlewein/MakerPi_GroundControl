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

## Troubleshooting

- **Not appearing in dashboard?** Check MQTT broker IP is correct
- **WiFi not connecting?** Verify SSID and password
- **Messages not received?** Ensure Mosquitto service is running: `sudo systemctl status mosquitto`

To monitor all MQTT messages in real-time:
```bash
mosquitto_sub -h localhost -t "#" -v
```
