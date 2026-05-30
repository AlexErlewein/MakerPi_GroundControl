# 16 · Backups & Data Safety

## Why backups?

The Raspberry Pi runs 24/7 in the workshop and stores all member data, Laufzettel entries, and payment records in local SQLite databases. A hardware failure (SD cards die, power surges happen) can destroy everything. A solid backup strategy makes the system recoverable within minutes.

---

## Primary solution: Litestream + Backblaze B2 (recommended)

[Litestream](https://litestream.io) is a lightweight tool that **continuously** streams SQLite Write-Ahead Log (WAL) changes to an S3-compatible object store — no cron job, no downtime, no database lock.

[Backblaze B2](https://www.backblaze.com/b2/) offers **10 GB free** object storage. The five small SQLite databases in this system fit comfortably within that limit.

### Setup

#### 1. Create a Backblaze account and bucket

1. Sign up at [backblaze.com](https://www.backblaze.com/)
2. Go to "Buckets" → "Create a Bucket" → name it e.g. `makerpi-backups`, set to **Private**
3. Go to "App Keys" → "Add a New Application Key"
   - Name: `litestream`
   - Bucket: `makerpi-backups`
   - Permissions: `Read and Write`
   - Note down the Key ID and Application Key

Find the S3 endpoint under "Buckets" → select your bucket → "Endpoint":  
Format: `s3.us-west-004.backblazeb2.com` (region varies)

#### 2. Fill in the config

Add to `config/config.json`:

```json
"litestream_enabled": true,
"backblaze_endpoint": "s3.us-west-004.backblazeb2.com",
"backblaze_bucket": "makerpi-backups",
"backblaze_key_id": "YOUR_KEY_ID",
"backblaze_application_key": "YOUR_APPLICATION_KEY"
```

#### 3. Create the Litestream config file

```bash
cp config/litestream.yml.example config/litestream.yml
```

Open the file and fill in all fields:
- `path` → absolute path to each `.db` file on the Pi (e.g. `/home/alex/MakerPi_GroundControl/auth.db`)
- `endpoint`, `bucket`, `access-key-id`, `secret-access-key` → values from step 1

#### 4. Install Litestream (on the Pi as root)

```bash
sudo bash scripts/setup-litestream.sh
```

The script:
- Downloads the correct Litestream binary for the Pi architecture (ARM64/ARMv7/AMD64)
- Copies `config/litestream.yml` to `/etc/litestream.yml`
- Creates and starts a `litestream.service` systemd unit

#### 5. Verify

```bash
sudo systemctl status litestream
sudo journalctl -u litestream -f

# Show snapshots (tells you when replication last ran)
litestream snapshots -config /etc/litestream.yml
```

### Restoring from backup

To restore a database from B2:

```bash
# Stop services
sudo systemctl stop groundcontrol litestream

# Restore database from the latest snapshot
litestream restore -config /etc/litestream.yml /home/alex/MakerPi_GroundControl/laufzettel.db

# Restart services
sudo systemctl start groundcontrol litestream
```

---

## Alternative: rclone (flexible backend support)

[rclone](https://rclone.org) supports 70+ cloud backends: Google Drive, Dropbox, OneDrive, SFTP, S3, and more. Unlike Litestream it takes **daily snapshots** rather than continuous replication — easier to set up but with a potential data loss window of up to 24 hours.

### Setup

#### 1. Install rclone

```bash
sudo apt install rclone
# or for a newer release:
curl https://rclone.org/install.sh | sudo bash
```

#### 2. Configure a remote

```bash
rclone config
```

Example for Google Drive: `n` → name `gdrive` → provider `drive` → complete the OAuth flow in the browser.  
Example for Dropbox: `n` → name `dropbox` → provider `dropbox` → complete the OAuth flow.

#### 3. Create the backup script

```bash
cat > /usr/local/bin/groundcontrol-backup.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="/home/alex/MakerPi_GroundControl"
BACKUP_DIR="/tmp/gc_backup_$(date +%Y%m%d_%H%M%S)"
REMOTE="gdrive:MakerPi_Backups/$(date +%Y/%B)"

mkdir -p "$BACKUP_DIR"

# Back up each database using SQLite's online backup mechanism
for DB in auth members laufzettel catalog core; do
    sqlite3 "$PROJECT_DIR/$DB.db" ".backup $BACKUP_DIR/$DB.db"
done

# Upload and clean up local copy
rclone copy "$BACKUP_DIR" "$REMOTE" --s3-no-check-bucket
rm -rf "$BACKUP_DIR"
echo "Backup complete: $REMOTE"
EOF
chmod +x /usr/local/bin/groundcontrol-backup.sh
```

#### 4. Schedule a daily cron job

```bash
# As root (or with sudo crontab -e):
echo "0 2 * * * /usr/local/bin/groundcontrol-backup.sh >> /var/log/gc-backup.log 2>&1" | sudo tee -a /etc/cron.d/groundcontrol-backup
```

This creates a daily snapshot at 02:00 under `MakerPi_Backups/2026/May/` on Google Drive.

### Restoring with rclone

```bash
# List available backups
rclone ls gdrive:MakerPi_Backups/

# Download a specific backup
rclone copy gdrive:MakerPi_Backups/2026/May/ /tmp/restore/

# Stop service and replace file
sudo systemctl stop groundcontrol
cp /tmp/restore/laufzettel.db /home/alex/MakerPi_GroundControl/laufzettel.db
sudo systemctl start groundcontrol
```

---

## Comparison

| Criterion | Litestream + B2 | rclone + Cloud |
|---|---|---|
| Max data loss | Seconds | 24 hours |
| Setup effort | Medium | Low |
| Cost | B2 free up to 10 GB | Usually free |
| Backend choice | S3-compatible | 70+ backends |
| Recommendation | **Yes** (primary) | As a supplement |
