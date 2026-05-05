#!/usr/bin/env python3
"""
Simple MQTT test script
Usage: python scripts/test_mqtt.py <broker-ip>
"""

import sys
import time
import paho.mqtt.client as mqtt

BROKER = sys.argv[1] if len(sys.argv) > 1 else "localhost"
PORT = 1883


def on_connect(client, userdata, flags, reason_code, properties):
    print(f"✅ Connected to {BROKER}:{PORT}")
    client.subscribe("#")


def on_message(client, userdata, msg):
    print(f"📨 {msg.topic}: {msg.payload.decode()}")


def on_disconnect(client, userdata, reason_code, properties):
    print(f"❌ Disconnected: {reason_code}")


print(f"Connecting to MQTT broker at {BROKER}...")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect

try:
    client.connect(BROKER, PORT, 60)
    client.loop_start()

    print("Listening for messages (Ctrl+C to exit)...")
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    print("\nExiting...")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    print(f"Error: {e}")
