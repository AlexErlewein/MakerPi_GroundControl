# Backend API Reference

All API endpoints live in `backend/main.py`. They follow a consistent pattern: open a DB session, do work, return a dict or raise `HTTPException`, always close session in `finally`.

## Endpoint overview

### System & inspection

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/status` | MQTT connection status, uptime, counts |
| `GET` | `/api/topics` | All seen MQTT topics |
| `GET` | `/api/messages` | Recent MQTT messages (`?limit=N`) |
| `GET` | `/api/database/stats` | Row counts, DB file size |

### Device management

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/devices` | List all known devices |
| `GET` | `/api/devices/{device_id}` | Single device detail |
| `GET` | `/api/devices/{device_id}/messages` | Messages from one device |
| `POST` | `/api/devices/{device_id}/commands` | Send MQTT command to device |

### Tag management

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/tags` | List all registered tags |
| `POST` | `/api/tags` | Create a new tag |
| `GET` | `/api/tags/{uid}` | Get one tag by UID |
| `PUT` | `/api/tags/{uid}` | Update tag fields |
| `DELETE` | `/api/tags/{uid}` | Delete a tag |
| `GET` | `/api/tags/scans` | Recent scan events |
| `GET` | `/api/tags/{uid}/laufzettel` | All Laufzettel for a UID |

### Laufzettel

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/laufzettel` | List all Laufzettel (filterable) |
| `POST` | `/api/laufzettel` | Create a Laufzettel manually |
| `GET` | `/api/laufzettel/{id}` | Get one Laufzettel with material |
| `PUT` | `/api/laufzettel/{id}` | Update Laufzettel fields |
| `DELETE` | `/api/laufzettel/{id}` | Delete a Laufzettel |
| `GET` | `/api/laufzettel/{id}/material` | List material entries |
| `POST` | `/api/laufzettel/{id}/material` | Add a material entry |
| `PUT` | `/api/laufzettel/{id}/material/{mid}` | Update a material entry |
| `DELETE` | `/api/laufzettel/{id}/material/{mid}` | Delete a material entry |

### Material catalog

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/katalog` | Full tree: locations → kategorien → varianten |
| `GET` | `/api/katalog/locations` | List locations |
| `POST` | `/api/katalog/locations` | Create location |
| `PUT` | `/api/katalog/locations/{id}` | Update location |
| `DELETE` | `/api/katalog/locations/{id}` | Delete location |
| `GET` | `/api/katalog/kategorien` | List kategorien |
| `POST` | `/api/katalog/kategorien` | Create kategorie |
| `PUT` | `/api/katalog/kategorien/{id}` | Update kategorie |
| `DELETE` | `/api/katalog/kategorien/{id}` | Delete kategorie |
| `GET` | `/api/katalog/varianten` | List varianten |
| `POST` | `/api/katalog/varianten` | Create variante |
| `PUT` | `/api/katalog/varianten/{id}` | Update variante |
| `DELETE` | `/api/katalog/varianten/{id}` | Delete variante |

### HTML page routes

| Method | Path | Template |
|---|---|---|
| `GET` | `/` | `index.html` |
| `GET` | `/database` | `database.html` |
| `GET` | `/tags` | `tags.html` |
| `GET` | `/devices/{device_id}` | `device-detail.html` |
| `GET` | `/laufzettel` | `laufzettel.html` |
| `GET` | `/laufzettel/{id}` | `laufzettel-detail.html` |
| `GET` | `/katalog` | `katalog.html` |

## Request / response patterns

### Create (POST)

```python
@app.post("/api/katalog/locations")
def create_location(payload: LocationCreate, db: Session = Depends(get_db)):
    loc = Location(name=payload.name)
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc.to_dict()
```

### Update (PUT)

- Body is a Pydantic model with optional fields
- Returns the updated record as a dict

### Delete (DELETE)

- Returns `{"ok": True}` on success
- Returns `404` if not found

### Error responses

| HTTP Status | When |
|---|---|
| `400` | Bad request (validation failure) |
| `404` | Resource not found |
| `409` | Conflict (e.g. duplicate uid) |
| `500` | Unexpected server error |

## Adding a new endpoint

Pattern to follow:

```python
@app.post("/api/myresource")
def create_myresource(payload: MyResourceCreate):
    db = SessionLocal()
    try:
        obj = MyModel(field=payload.field)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj.to_dict()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
```

## Auto-generated API docs

FastAPI generates interactive API docs automatically:

| URL | Description |
|---|---|
| `http://localhost:8000/docs` | Swagger UI — try requests in browser |
| `http://localhost:8000/redoc` | ReDoc — readable reference |
| `http://localhost:8000/openapi.json` | Raw OpenAPI schema |
