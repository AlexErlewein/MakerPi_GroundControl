# Betrieb und Deployment

Diese Seite beschreibt den laufenden Betrieb, Deployment und Wartung des Produktivsystems.

## Systemübersicht

| Dienst | Port | Systemd-Unit | Beschreibung |
|--------|------|--------------|--------------|
| GroundControl App | 8000 | `groundcontrol.service` | Haupt-Webanwendung (FastAPI) |
| Docs | 8001 | `groundcontrol-docs.service` | Dokumentationsseite |
| SQLite Web | extern | `sqlite-web.service` | Datenbank-Browser (wird vom Auto-Deploy mitgestartet; separat zu installieren/konfigurieren) |
| Auto-Deploy Timer | — | `groundcontrol-autodeploy.timer` | Pollt alle 5 min git, deployed automatisch |

**Projektpfad auf dem Pi:** `/home/dev/Code/MakerPi_GroundControl`

---

## Deploy-Workflow

Das Deploy-Script (`scripts/deploy.sh`) ist **git-basiert**: Änderungen werden lokal committed, gepusht, und der Pi führt einen `git reset --hard` auf den Upstream des aktuellen Branchs aus – keine rsync-Konflikte mehr.

```bash
# Normaler Deploy (committed + pushed + Pi aktualisiert + Service neugestartet)
./scripts/deploy.sh

# Mit Dependency-Update (nach pyproject.toml Änderungen)
./scripts/deploy.sh --update-deps
```

> Schema-Migrationen (neue Spalten) laufen automatisch beim Start des Dienstes über die Inline-Migration in jeder `init_db()` — es gibt kein `--migrate`-Flag und kein separates Skript mehr.

### Was das Script tut

1. Prüft auf uncommitted Changes → fragt nach Commit-Message → `git commit` + `git push`
2. Stellt Verbindung her (Tailscale bevorzugt, Fallback auf lokale IP)
3. Auf Pi: `git fetch && git reset --hard origin/<aktueller Branch>`
4. Optional (nur mit `--update-deps`): `uv sync` auf dem Pi
5. WAL-Checkpoint der Datenbanken, dann `sudo systemctl restart groundcontrol groundcontrol-docs`

### Auto-Deploy

Ein systemd-Timer läuft alle **5 Minuten** und führt `scripts/auto-deploy.sh` aus – sobald ein neuer Commit auf `origin/main` erscheint, wird automatisch deployt und der Service neugestartet.

```bash
# Timer-Status prüfen
sudo systemctl status groundcontrol-autodeploy.timer

# Letzten Auto-Deploy Log sehen
sudo journalctl -u groundcontrol-autodeploy -n 30
```

---

## Dienste verwalten

```bash
# Status aller Dienste
sudo systemctl status groundcontrol groundcontrol-docs sqlite-web

# Logs in Echtzeit
sudo journalctl -u groundcontrol -f

# Neustart
sudo systemctl restart groundcontrol

# Docs-Service
sudo systemctl restart groundcontrol-docs
```

### Health-Check

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
```

---

## Konfiguration

Alle Einstellungen in `config/config.json` (gitignored, nur auf dem Pi):

```json
{
  "pi_host": "192.168.3.228",
  "tailscale_ip": "100.78.55.14",
  "pi_user": "dev",
  "project_dir": "/home/dev/Code/MakerPi_GroundControl",
  "sumup_api_key": "sup_sk_...",
  "sumup_affiliate_key": "...",
  "sumup_merchant_code": "...",
  "sumup_reader_id": ""
}
```

---

## Backup

### Wichtige Dateien

```
config/config.json      # Konfiguration (nicht in git!)
laufzettel.db           # Laufzettel + Material
members.db              # Mitglieder + RFID-Tags
catalog.db              # Materialkatalog
auth.db                 # Benutzerkonten
core.db                 # MQTT-Nachrichten, Gerätestatus
```

### Manuelles Backup

```bash
# Auf dem Pi
cd /home/dev/Code/MakerPi_GroundControl
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p ~/backups
cp *.db ~/backups/db_$DATE/
cp config/config.json ~/backups/db_$DATE/
```

---

## Troubleshooting

### Service startet nicht

```bash
sudo journalctl -u groundcontrol -n 50 --no-pager
# Konfiguration validieren
python3 -c "import json; json.load(open('config/config.json'))"
```

### Datenbank-Fehler

```bash
sqlite3 laufzettel.db "PRAGMA integrity_check;"

# Backup einspielen
sudo systemctl stop groundcontrol
cp ~/backups/db_20260101_120000/laufzettel.db .
sudo systemctl start groundcontrol
```

### MQTT-Verbindungsprobleme

```bash
sudo systemctl status mosquitto
mosquitto_sub -t "#" -v   # Topics live überwachen
```

### Auto-Deploy schlägt fehl

```bash
sudo systemctl reset-failed groundcontrol-autodeploy.service
sudo journalctl -u groundcontrol-autodeploy -n 20
```

---

## Sicherheit

1. **Admin-Passwort ändern** nach erster Anmeldung
2. **config/config.json** nie committen (in `.gitignore`)
3. **Firewall:** Ports 8000/8001 nur im lokalen Netz oder via Tailscale

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 1883/tcp  # MQTT, nur intern
sudo ufw enable
```

---

## Wartungs-Checkliste

### Wöchentlich

- [ ] `sudo journalctl -u groundcontrol --since "7 days ago" | grep ERROR`
- [ ] Festplattenspeicher: `df -h`
- [ ] Datenbankgröße: `ls -lh *.db`

### Monatlich

- [ ] System-Updates: `sudo apt update && sudo apt upgrade`
- [ ] Datenbank-Vacuum: `sqlite3 laufzettel.db "VACUUM;"`

### Jährlich

- [ ] Passwörter rotieren
- [ ] SD-Karte ersetzen (Verschleiß)
