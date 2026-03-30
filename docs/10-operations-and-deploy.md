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
