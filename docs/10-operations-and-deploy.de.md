# Betrieb und Deployment

Diese Seite beschreibt den laufenden Betrieb, Deployment-Optionen und Wartung.

## Deployment-Optionen

### 1. Raspberry Pi (Produktion)

**Hardware:**
- Raspberry Pi 4 (4GB+ empfohlen)
- SD-Karte (32GB+ Class 10)
- Ethernet-Verbindung (stabiler als WLAN)

**Setup:**

```bash
# 1. System aktualisieren
sudo apt update && sudo apt upgrade -y

# 2. Setup-Skript ausführen
curl -fsSL https://raw.githubusercontent.com/.../setup.sh | bash

# 3. Konfiguration anpassen
sudo nano /opt/makerpi/config/config.json

# 4. Service neustarten
sudo systemctl restart makerpi-groundcontrol
```

### 2. Docker (fortgeschritten)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t makerpi .
docker run -p 8000:8000 -v $(pwd)/config:/app/config makerpi
```

### 3. Lokale Entwicklung

Siehe [Schnellstart](./01-quickstart).

## Lokale DNS (für Pi)

Eintrag in der lokalen `/etc/hosts` oder Router-DNS:

```
192.168.1.100    makerpi.local
```

Oder Avahi/mDNS verwenden (automatisch auf Raspberry Pi OS):

```bash
# Auf dem Pi
sudo apt install avahi-daemon
# Erreichbar unter: http://makerpi.local
```

## Reverse Proxy (nginx)

Für externen Zugriff mit SSL:

```nginx
server {
    listen 80;
    server_name makerpi.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name makerpi.example.com;

    ssl_certificate /etc/letsencrypt/live/makerpi.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/makerpi.example.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Backup

### Wichtige Dateien

```
config/config.json          # Konfiguration
backend/*.db                # SQLite-Datenbanken
```

### Automatisches Backup

```bash
#!/bin/bash
# /opt/makerpi/scripts/backup.sh

BACKUP_DIR="/backup/makerpi"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Datenbanken sichern
cp /opt/makerpi/backend/*.db $BACKUP_DIR/db_$DATE.sqlite

# Konfiguration sichern
cp /opt/makerpi/config/config.json $BACKUP_DIR/config_$DATE.json

# Alte Backups löschen (älter als 30 Tage)
find $BACKUP_DIR -name "*.sqlite" -mtime +30 -delete
find $BACKUP_DIR -name "*.json" -mtime +30 -delete
```

**Cron-Job:**

```bash
# Täglich um 3 Uhr
0 3 * * * /opt/makerpi/scripts/backup.sh
```

## Monitoring

### Systemd Service Status

```bash
sudo systemctl status makerpi-groundcontrol
sudo journalctl -u makerpi-groundcontrol -f
```

### Health-Check

```bash
curl http://localhost:8000/health
```

### Logs

```bash
# In Echtzeit beobachten
tail -f /var/log/makerpi/app.log

# Letzte 100 Zeilen
tail -n 100 /var/log/makerpi/app.log
```

## Updates

### Manuelles Update

```bash
# 1. Backup erstellen
./scripts/backup.sh

# 2. Code aktualisieren
cd /opt/makerpi
git pull origin main

# 3. Abhängigkeiten aktualisieren
pip install -r requirements.txt

# 4. Datenbank-Migrationen prüfen
# (automatisch bei Start)

# 5. Service neustarten
sudo systemctl restart makerpi-groundcontrol
```

### Automatische Updates (optional)

```bash
# Weekly-Update via Cron
0 4 * * 1 cd /opt/makerpi && git pull && pip install -r requirements.txt && sudo systemctl restart makerpi-groundcontrol
```

## Troubleshooting

### Service startet nicht

```bash
# Logs prüfen
sudo journalctl -u makerpi-groundcontrol -n 50

# Konfiguration validieren
python -c "import json; json.load(open('config/config.json'))"

# Berechtigungen prüfen
ls -la /opt/makerpi/
```

### Datenbank-Fehler

```bash
# SQLite-Integrität prüfen
sqlite3 backend/groundcontrol.db "PRAGMA integrity_check;"

# Bei Problemen: Backup einspielen
systemctl stop makerpi-groundcontrol
cp /backup/makerpi/db_20250101_120000.sqlite backend/groundcontrol.db
systemctl start makerpi-groundcontrol
```

### MQTT-Verbindungsprobleme

```bash
# Mosquitto-Status prüfen
sudo systemctl status mosquitto

# Test-Message senden
mosquitto_pub -t "test/topic" -m "hello"

# Topics überwachen
mosquitto_sub -t "#" -v
```

## Sicherheit

### Standard-Sicherheitsmaßnahmen

1. **Admin-Passwort ändern** nach erster Anmeldung
2. **Firewall:** Nur Port 8000 (oder 443 mit nginx) öffnen
3. **Keine Produktionsdaten** in Git committen
4. **Regelmäßige Backups**

### Netzwerk-Isolierung

```bash
# Firewall-Regeln (ufw)
sudo ufw allow 8000/tcp  # App
sudo ufw allow 1883/tcp  # MQTT (nur wenn extern benötigt)
sudo ufw enable
```

## Leistungsoptimierung

### Raspberry Pi

```bash
# Boot-Performance
sudo raspi-config  # → Performance → GPU-Speicher minimieren

# SD-Karten-IO optimieren
sudo nano /etc/sysctl.conf
# vm.swappiness=10
# vm.vfs_cache_pressure=50
```

### Datenbank

- SQLite ist für < 100k Einträge ausreichend
- Bei größeren Datenmengen: PostgreSQL in Erwägung ziehen
- Regelmäßiges `VACUUM` für Fragmentierung

## Wartungs-Checkliste

### Wöchentlich

- [ ] Logs auf Fehler prüfen
- [ ] Backup-Integrität testen
- [ ] Festplattenspeicher prüfen (`df -h`)

### Monatlich

- [ ] System-Updates einspielen (`sudo apt update`)
- [ ] Datenbank-Dateigröße prüfen
- [ ] Inaktive Tags bereinigen

### Jährlich

- [ ] Passwörter rotieren
- [ ] SD-Karte ersetzen (Verschleiß)
- [ ] Hardware-Reinigung
