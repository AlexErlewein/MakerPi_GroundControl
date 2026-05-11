# Planka Kanban Board for MakerPi

A lightweight kanban board for ticket tracking and bug reports, themed to match MakerPi GroundControl.

## Features

- **Kanban-style boards** — drag & drop cards between columns
- **Card details** — descriptions, due dates, labels, checklists, attachments
- **Member assignment** — assign tasks to team members
- **Activity tracking** — see who did what and when
- **Dark theme** — matches GroundControl's color scheme (charcoal + orange accent)
- **Web-based** — accessible from any device on the same network

## Quick Start

### 1. Deploy to Pi

From this directory, run:

```bash
chmod +x deploy.sh
./deploy.sh
```

This will:
- Install Docker on the Pi (if needed)
- Deploy Planka with PostgreSQL
- Apply the GroundControl theme
- Start the service on port `3001`

### 2. Access

Open in any browser:
```
http://192.168.3.228:3001   # Local network
http://100.78.55.14:3001    # Tailscale (anywhere)
```

### 3. First Setup

1. Register your admin account
2. Create a board (e.g., "Bug Reports", "Feature Requests")
3. Add columns (e.g., "To Do", "In Progress", "Done")
4. Start creating cards!

## Management Commands

SSH to the Pi and run:

```bash
cd ~/planka

# View logs
sudo docker compose logs -f

# Stop Planka
sudo docker compose stop

# Start Planka
sudo docker compose start

# Update to latest version
sudo docker compose pull
sudo docker compose up -d

# Backup database
sudo docker exec planka-postgres pg_dump -U planka planka > planka-backup.sql

# Restore database
cat planka-backup.sql | sudo docker exec -i planka-postgres psql -U planka planka

# Remove everything (data will be lost!)
sudo docker compose down -v
```

## Customization

### Changing the Theme

Edit `custom.css` and redeploy:

```bash
scp custom.css dev@192.168.3.228:~/planka/
ssh dev@192.168.3.228 "cd ~/planka && sudo docker compose restart planka"
```

### Changing the Port

Edit `docker-compose.yml` and change the port mapping:

```yaml
ports:
  - "3001:1337"  # Change 3001 to your desired port
```

### Using HTTPS (via GroundControl)

If you want to access Planka through GroundControl's port (e.g., `/kanban`), you can add a reverse proxy route in GroundControl's FastAPI app.

## Architecture

- **Planka container**: The kanban web app (Node.js/React)
- **PostgreSQL container**: Database for cards, boards, users
- **Persistent volumes**: User avatars, attachments, project backgrounds, database
- **Custom CSS**: Mounted at `/app/client/public/custom.css` to override default styles

## Resource Usage

- **Memory**: ~300-400MB total (Planka + PostgreSQL)
- **CPU**: Low idle, moderate during drag-and-drop
- **Disk**: ~500MB for images, grows with attachments

## Troubleshooting

### Services won't start

```bash
ssh dev@192.168.3.228
cd ~/planka
sudo docker compose logs
```

### Database connection errors

Ensure PostgreSQL is healthy:
```bash
sudo docker compose ps
sudo docker compose logs postgres
```

### Custom CSS not applying

Check the CSS file is mounted:
```bash
sudo docker exec planka ls -la /app/client/public/custom.css
```

### Reset everything

```bash
sudo docker compose down -v
sudo docker compose up -d
```

## Links

- [Planka on GitHub](https://github.com/plankanban/planka)
- [Planka Documentation](https://docs.planka.cloud/)

---

**Note**: Planka is separate from GroundControl for isolation. If Planka has issues, it won't affect your main MakerPi system.
