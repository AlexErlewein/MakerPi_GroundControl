# Operations and Deploy

This page describes how the project is started and deployed.

## Local development

Install dependencies:

```bash
uv sync
```

Run the main app:

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

Run the docs app:

```bash
uv run uvicorn backend.docs_app:app --reload --port 8001
```

## Existing setup script

The repository already includes:

- `scripts/setup.sh`

That script currently installs a systemd service for the main app on port `8000`.

## Recommended docs deployment approach

Add a second service for the docs app, for example:

- `groundcontrol-docs.service`

with an `ExecStart` like:

```bash
uvicorn backend.docs_app:app --host 0.0.0.0 --port 8001
```

## Deploy script

The repository also includes `scripts/deploy.sh`.

Because the docs app lives in the same repo, normal deployment of the codebase should already copy the docs source and docs app code. Only the service/runtime exposure needs to be added.

## Database operations

Useful operations already present in the repo:

- reset database script
- earlier migration helper scripts
- sqlite-web support for browsing data manually

## Production note

If you later put Nginx or another reverse proxy in front of the system, you can expose:

- main app on `/`
- docs app on `/docs` or a subdomain

For now, using a dedicated second port is the simplest approach.

---

## Local DNS: access via `groundcontrol.local`

This setup makes the app reachable at `http://groundcontrol.local` on the local network — no port number needed, no router configuration required.

It works automatically on **macOS, iOS, and iPadOS**. Windows needs Bonjour installed (bundled with iTunes or Apple devices). Android does not support `.local` mDNS — use the Pi's IP address on Android.

### How it works

- **Avahi** (mDNS daemon) advertises the Pi's hostname as `groundcontrol.local` on the local network
- **nginx** listens on port 80 and forwards requests to the FastAPI app on port 8000

### Step 1 — Set the Pi hostname

```bash
sudo hostnamectl set-hostname groundcontrol
```

Then update `/etc/hosts` so the Pi resolves its own name correctly:

```bash
sudo nano /etc/hosts
```

Find the line starting with `127.0.1.1` and change it to:

```
127.0.1.1    groundcontrol
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

### Step 2 — Install and enable Avahi

```bash
sudo apt update
sudo apt install avahi-daemon -y
sudo systemctl enable avahi-daemon
sudo systemctl start avahi-daemon
```

Verify it is running:

```bash
sudo systemctl status avahi-daemon
```

From this point on, other devices on the network can ping `groundcontrol.local`.

### Step 3 — Install nginx

```bash
sudo apt install nginx -y
```

### Step 4 — Create the nginx site config

```bash
sudo nano /etc/nginx/sites-available/groundcontrol
```

Paste the following:

```nginx
server {
    listen 80;
    server_name groundcontrol.local;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
    }
}
```

Save and exit.

### Step 5 — Enable the site

```bash
sudo ln -s /etc/nginx/sites-available/groundcontrol /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
```

Test the config, then restart nginx:

```bash
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
```

### Step 6 — Reboot

```bash
sudo reboot
```

After the reboot, open `http://groundcontrol.local` on any Apple device on the same network.

### Optional: also expose the docs app

Add a second server block to the same config file (or a new file) to expose the docs on port 8001 via a path prefix:

```nginx
server {
    listen 80;
    server_name groundcontrol.local;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /docs/ {
        proxy_pass http://127.0.0.1:8001/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Then `http://groundcontrol.local/docs/` serves the docs app without needing a separate port.

### Troubleshooting

| Problem | Fix |
|---|---|
| `groundcontrol.local` not resolving | Check `sudo systemctl status avahi-daemon` |
| nginx shows default page | Ensure `/etc/nginx/sites-enabled/default` is deleted |
| App not loading through nginx | Check FastAPI is running: `sudo systemctl status groundcontrol` |
| nginx config error | Run `sudo nginx -t` to see the exact error |
