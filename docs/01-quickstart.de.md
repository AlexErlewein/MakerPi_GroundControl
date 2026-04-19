# Schnellstart

## Lokale Entwicklung

### Voraussetzungen

- Python 3.12 oder höher
- uv (Python-Paketmanager) – `pip install uv`

### Schritte

```bash
# Repository klonen
git clone <repository-url>
cd MakerPi_GroundControl

# Abhängigkeiten installieren
uv sync

# Anwendung starten
uv run uvicorn backend.main:app --reload --port 8000
```

Die App ist dann unter `http://localhost:8000` erreichbar.

Standard-Login:
- **Benutzername:** `admin`
- **Passwort:** in `config/config.json` konfiguriert (Standard: `changeme`)

## Raspberry Pi Deployment

### Option A: Schnelles Test-Skript

```bash
curl -fsSL https://raw.githubusercontent.com/alexander-manin/MakerPi_GroundControl/main/scripts/setup.sh | bash
```

Dies installiert:
- System-Abhängigkeiten
- Diese Anwendung als systemd-Service
- Mosquitto MQTT Broker (optional)

### Option B: Manuelle Installation

1. **System-Abhängigkeiten**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv git
   ```

2. **Projekt einrichten**
   ```bash
   git clone <repository-url>
   cd MakerPi_GroundControl
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Konfiguration**
   ```bash
   cp config/config.example.json config/config.json
   # config.json nach Bedarf bearbeiten
   ```

4. **Als Service ausführen**
   ```bash
   sudo cp systemd/makerpi-groundcontrol.service /etc/systemd/system/
   sudo systemctl enable makerpi-groundcontrol
   sudo systemctl start makerpi-groundcontrol
   ```

## Zugriff auf die Anwendung

Nach dem Start ist die Anwendung unter `http://<pi-ip>:8000` erreichbar.

## Nächste Schritte

- Konfiguriere [Tags und Laufzettel](./03-tags-and-laufzettel) für das NFC-System
- Richte den [Material-Katalog](./04-material-katalog) ein
- Verbinde [MQTT-Sensoren](./06-mqtt-data-flow) für Geräte-Monitoring
