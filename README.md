# 🛰️ MakerPi GroundControl

MQTT broker management and monitoring system for Raspberry Pi with web interface.

## Features

- **MQTT Broker**: Mosquitto broker running on Raspberry Pi
- **Web Dashboard**: Real-time monitoring of connected devices and messages
- **Data Storage**: SQLite database for message history
- **Device Tracking**: Automatic device discovery and status tracking
- **REST API**: Full API for integration with other services

## Architecture

```
┌─────────────┐      publish      ┌──────────────┐
│  PicoW      │ ─────────────────►│   Mosquitto  │
│  (client)   │                   │   (broker)   │
└─────────────┘                   └──────────────┘
                                           │
                                           │ subscribe
                                           ▼
                                  ┌──────────────┐
                                  │  FastAPI     │
                                  │  Backend     │
                                  └──────────────┘
                                           │
                                ┌──────────┴──────────┐
                                ▼                     ▼
                         ┌────────────┐      ┌─────────────┐
                         │   SQLite   │      │  Web UI     │
                         │  Database  │      │  (HTML/JS)  │
                         └────────────┘      └─────────────┘
```

## Quick Start

### 1. Clone on Raspberry Pi

```bash
git clone https://github.com/AlexErlewein/MakerPi_GroundControl.git
cd MakerPi_GroundControl
sudo bash scripts/setup.sh
```

### 2. Access the Dashboard

Open your browser: `http://<pi-ip>:8000`

## Project Structure

```
MakerPi_GroundControl/
├── backend/
│   └── main.py          # FastAPI application with MQTT client
├── config/
│   └── mosquitto.conf   # MQTT broker configuration
├── scripts/
│   ├── setup.sh         # Initial setup script for Pi
│   └── deploy.sh        # Deploy updates from dev machine
├── static/
│   ├── css/
│   │   └── style.css    # Dashboard styles
│   └── js/
│       └── app.js       # Dashboard frontend logic
├── templates/
│   └── index.html       # Main dashboard template
├── requirements.txt     # Python dependencies
└── README.md
```

## Development Workflow

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run locally (requires MQTT broker)
uvicorn backend.main:app --reload
```

### Deploying to Pi

```bash
# From your development machine, sync changes to Pi
./scripts/deploy.sh raspberrypi.local
# or use IP
./scripts/deploy.sh 192.168.1.100
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web dashboard |
| `/api/status` | GET | System status (MQTT connection) |
| `/api/devices` | GET | List all registered devices |
| `/api/messages` | GET | Recent messages (query: `?limit=100&topic=xyz`) |
| `/api/topics` | GET | List all active topics |

## MQTT Configuration

- **Host**: `localhost` (on Pi) or Pi's IP address
- **Port**: `1883`
- **Anonymous access**: Enabled (for local network)

### Example MQTT Publish (PicoW)

```python
import network
import umqtt.simple

mqtt = umqtt.simple.MQTTClient("pico-w", "192.168.1.100")
mqtt.connect()
mqtt.publish("pico-w/sensors/temp", "22.5")
mqtt.disconnect()
```

## Service Management

```bash
# View service status
sudo systemctl status groundcontrol

# View logs
sudo journalctl -u groundcontrol -f

# Restart service
sudo systemctl restart groundcontrol

# Restart Mosquitto
sudo systemctl restart mosquitto
```

## Database

SQLite database located at: `/opt/makerpi-groundcontrol/groundcontrol.db`

### Schema

**devices** table:
- `id` - Primary key
- `device_id` - Unique device identifier
- `name` - Device name
- `last_seen` - Last activity timestamp
- `status` - Current status (online/offline/unknown)

**mqtt_messages** table:
- `id` - Primary key
- `topic` - MQTT topic
- `payload` - Message payload
- `qos` - Quality of Service level
- `retained` - Retained flag
- `timestamp` - Message timestamp

## Requirements

- Raspberry Pi (3B+ or newer recommended)
- Raspberry Pi OS
- Python 3.9+
- Mosquitto MQTT Broker

## License

MIT
