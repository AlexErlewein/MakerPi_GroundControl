# 16 · Backups & Datensicherung

## Warum Backups?

Der Raspberry Pi läuft 24/7 in der Werkstatt und speichert alle Mitgliederdaten, Laufzettel und Zahlungsbelege in lokalen SQLite-Datenbanken. Ein Hardwareausfall (SD-Karten sterben, Überspannungen passieren) kann alles vernichten. Mit einem guten Backup-System lässt sich das System innerhalb von Minuten wiederherstellen.

> **Im Repo enthalten:** `scripts/backup_all_dbs.py` sichert alle sechs Datenbanken (`auth`, `core`, `members`, `laufzettel`, `catalog`, `buchhaltung`) auf Google Drive via SQLite-Online-Backup-API und behält jeweils 3 Backups pro Datenbank. Es ist für den Cron-Einsatz gedacht (z.B. `0 23 * * *`). Dies ist der einfachste im Repo enthaltene Backup-Mechanismus. Die folgenden Optionen (Litestream, rclone) sind robustere Alternativen.

---

## Primärlösung: Litestream + Backblaze B2 (empfohlen)

[Litestream](https://litestream.io) ist ein schlankes Tool, das die SQLite Write-Ahead-Log (WAL) Änderungen **kontinuierlich** an einen S3-kompatiblen Objektspeicher streamt – ohne Cron-Job, ohne Ausfallzeiten, ohne Datenbanksperre.

[Backblaze B2](https://www.backblaze.com/b2/) bietet **10 GB kostenlosen** Objektspeicher. Für die kleinen SQLite-Datenbanken dieses Systems (`auth`, `core`, `members`, `laufzettel`, `catalog`, `buchhaltung`) reicht das problemlos.

### Einrichtung

#### 1. Backblaze-Account und Bucket erstellen

1. Unter [backblaze.com](https://www.backblaze.com/) registrieren
2. „Buckets" → „Create a Bucket" → Name z. B. `makerpi-backups`, **Private**
3. „App Keys" → „Add a New Application Key"
   - Name: `litestream`
   - Bucket: `makerpi-backups`
   - Berechtigungen: `Read and Write`
   - Key ID und Application Key notieren

Den S3-Endpoint findest du unter „Buckets" → Bucket auswählen → „Endpoint":  
Format: `s3.us-west-004.backblazeb2.com` (die Region variiert)

#### 2. Config befüllen

`config/config.json` ergänzen:

```json
"litestream_enabled": true,
"backblaze_endpoint": "s3.us-west-004.backblazeb2.com",
"backblaze_bucket": "makerpi-backups",
"backblaze_key_id": "DEINE_KEY_ID",
"backblaze_application_key": "DEIN_APPLICATION_KEY"
```

#### 3. Litestream-Konfigurationsdatei anlegen

```bash
cp config/litestream.yml.example config/litestream.yml
```

Datei öffnen und alle Felder ausfüllen:
- `path` → absoluter Pfad zur jeweiligen `.db`-Datei auf dem Pi (z. B. `/home/alex/MakerPi_GroundControl/auth.db`)
- `endpoint`, `bucket`, `access-key-id`, `secret-access-key` → Werte aus Schritt 1

#### 4. Litestream installieren (auf dem Pi als root)

Es gibt kein Setup-Skript im Repo — Litestream wird manuell installiert:

```bash
# Binary für die Pi-Architektur herunterladen (Beispiel ARM64)
wget https://github.com/benbjohnson/litestream/releases/download/v0.3.13/litestream-v0.3.13-linux-arm64-static.tar.gz
tar -xzf litestream-v0.3.13-linux-arm64-static.tar.gz
sudo install litestream /usr/local/bin/litestream

# Konfiguration und Service installieren
sudo cp config/litestream.yml /etc/litestream.yml
# Eine litestream.service systemd-Unit erstellen, die Folgendes ausführt:
#   /usr/local/bin/litestream replicate -config /etc/litestream.yml
sudo systemctl daemon-reload
sudo systemctl enable --now litestream
```

#### 5. Überprüfen

```bash
sudo systemctl status litestream
sudo journalctl -u litestream -f

# Snapshots anzeigen (zeigt, wann zuletzt repliziert wurde)
litestream snapshots -config /etc/litestream.yml
```

### Wiederherstellung

Um eine Datenbank von B2 wiederherzustellen:

```bash
# Dienst stoppen
sudo systemctl stop groundcontrol litestream

# Datenbank aus dem letzten Snapshot wiederherstellen
litestream restore -config /etc/litestream.yml /home/alex/MakerPi_GroundControl/laufzettel.db

# Dienste wieder starten
sudo systemctl start groundcontrol litestream
```

---

## Alternative: rclone (flexibler Backend-Support)

[rclone](https://rclone.org) unterstützt über 70 Cloud-Backends: Google Drive, Dropbox, OneDrive, SFTP, S3 usw. Im Gegensatz zu Litestream macht es **tägliche Snapshots** statt kontinuierlicher Replikation – einfacher einzurichten, aber mit einem potenziellen Datenverlust von bis zu 24 Stunden.

### Einrichtung

#### 1. rclone installieren

```bash
sudo apt install rclone
# oder aktuellere Version:
curl https://rclone.org/install.sh | sudo bash
```

#### 2. Remote konfigurieren

```bash
rclone config
```

Beispiel für Google Drive: `n` → Name `gdrive` → Provider `drive` → OAuth-Flow im Browser abschließen.  
Beispiel für Dropbox: `n` → Name `dropbox` → Provider `dropbox` → OAuth-Flow.

#### 3. Backup-Skript anlegen

```bash
cat > /usr/local/bin/groundcontrol-backup.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="/home/alex/MakerPi_GroundControl"
BACKUP_DIR="/tmp/gc_backup_$(date +%Y%m%d_%H%M%S)"
REMOTE="gdrive:MakerPi_Backups/$(date +%Y/%B)"

mkdir -p "$BACKUP_DIR"

# Sichere jede Datenbank mit dem SQLite Online-Backup-Mechanismus
for DB in auth members laufzettel catalog core buchhaltung; do
    sqlite3 "$PROJECT_DIR/$DB.db" ".backup $BACKUP_DIR/$DB.db"
done

# Hochladen und lokale Kopie aufräumen
rclone copy "$BACKUP_DIR" "$REMOTE" --s3-no-check-bucket
rm -rf "$BACKUP_DIR"
echo "Backup abgeschlossen: $REMOTE"
EOF
chmod +x /usr/local/bin/groundcontrol-backup.sh
```

#### 4. Täglichen Cron-Job einrichten

```bash
# Als root (oder mit sudo crontab -e):
echo "0 2 * * * /usr/local/bin/groundcontrol-backup.sh >> /var/log/gc-backup.log 2>&1" | sudo tee -a /etc/cron.d/groundcontrol-backup
```

Das erzeugt täglich um 02:00 Uhr einen Snapshot unter `MakerPi_Backups/2026/Mai/` auf Google Drive.

### Wiederherstellung mit rclone

```bash
# Liste der verfügbaren Backups
rclone ls gdrive:MakerPi_Backups/

# Einzelne Datenbank herunterladen
rclone copy gdrive:MakerPi_Backups/2026/Mai/ /tmp/restore/

# Dienst stoppen und Datei ersetzen
sudo systemctl stop groundcontrol
cp /tmp/restore/laufzettel.db /home/alex/MakerPi_GroundControl/laufzettel.db
sudo systemctl start groundcontrol
```

---

## Vergleich

| Kriterium | Litestream + B2 | rclone + Cloud |
|---|---|---|
| Datenverlust max. | Sekunden | 24 Stunden |
| Einrichtungsaufwand | Mittel | Gering |
| Kosten | B2 kostenlos bis 10 GB | Meist kostenlos |
| Backend-Wahl | S3-kompatibel | 70+ Backends |
| Empfehlung | **Ja** (Primärlösung) | Als Ergänzung |
