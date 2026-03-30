# Backend API and Structure

This page describes how the backend is organized and where to change things.

## Main backend file

The main application currently lives in:

- `backend/main.py`

It contains:

- SQLAlchemy models
- MQTT handler
- Pydantic request models
- JSON API routes
- HTML routes
- startup/shutdown lifecycle logic

## Main route groups

### Status and inspection

- `/api/status`
- `/api/devices`
- `/api/messages`
- `/api/topics`
- `/api/database/stats`

### Device management

- `/api/devices/{device_id}`
- `/api/devices/{device_id}/messages`
- `/api/devices/{device_id}/commands`

### Tag management

- `/api/tags`
- `/api/tags/scans`
- `/api/tags/{uid}`
- `/api/tags/{uid}/laufzettel`

### Laufzettel

- `/api/laufzettel`
- `/api/laufzettel/{laufzettel_id}`
- `/api/laufzettel/{laufzettel_id}/material`
- `/api/laufzettel/{laufzettel_id}/material/{material_id}`

### Material catalog

- `/api/katalog`
- `/api/katalog/locations`
- `/api/katalog/kategorien`
- `/api/katalog/varianten`

### HTML pages

- `/`
- `/database`
- `/tags`
- `/devices/{device_id}`
- `/laufzettel`
- `/laufzettel/{laufzettel_id}`
- `/katalog`

## Where to change backend behavior

### Add a new DB field

Usually in `backend/main.py`:

1. SQLAlchemy model
2. `to_dict()` method
3. related Pydantic models
4. related API handlers
5. any UI that reads/writes the field

### Add a new API endpoint

Add the route in `backend/main.py`, following the existing pattern:

- open `SessionLocal()`
- query/update models
- return plain dicts or `JSONResponse`
- always close the DB session in `finally`

### Add a new HTML page

1. create a Jinja template in `templates/`
2. create page JS in `static/js/`
3. create page CSS in `static/css/` if needed
4. add a route in `backend/main.py`
5. add a navigation link where appropriate
