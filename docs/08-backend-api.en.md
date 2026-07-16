# Backend API Reference

API endpoints are split across module route files (`backend/laufzettel/routes.py`, `backend/catalog/routes.py`, etc.) and registered in `backend/main.py`. They follow a consistent pattern: open a DB session, do work, return a dict or raise `HTTPException`.

## Endpoint overview

### System & inspection

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/status` | Device counts, message counts (24h + total) |
| `GET` | `/api/topics` | All seen MQTT topics |
| `GET` | `/api/messages` | Recent MQTT messages (`?limit=N&topic=...`) |
| `GET` | `/api/database/stats` | core DB file info, device + message stats |

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

### NFC scans

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/scans` | Recent scan log with `card_verified` status |
| `GET` | `/api/scans/stream` | SSE stream of live scan events |

### Members (Mitglieder)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/mitglieder` | List all members |
| `POST` | `/api/mitglieder` | Create a member manually |
| `GET` | `/api/mitglieder/{id}` | Get one member |
| `PUT` | `/api/mitglieder/{id}` | Update member fields |
| `DELETE` | `/api/mitglieder/{id}` | Delete a member |
| `POST` | `/api/mitglieder/{id}/enroll-card` | Send card write command to enrollment PicoW |
| `GET` | `/api/mitglieder/sync-status` | easyVerein sync status |
| `POST` | `/api/mitglieder/sync` | Trigger manual easyVerein sync |

### Guest Laufzettel

| Method | Path | Description |
|---|---|---|
| `GET` | `/guest/laufzettel` | Guest form page (QR code landing) |
| `POST` | `/api/guest/laufzettel` | Create a guest Laufzettel |
| `GET` | `/api/guest/session-check` | Check if guest has an active session |
| `GET` | `/api/guest/laufzettel/{id}` | Guest Laufzettel detail |
| `POST` | `/api/guest/laufzettel/{id}/material` | Add material to guest Laufzettel |

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

### Payment

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/payment/config` | Config flags: `sumup_configured`, `sumup_mock`, `payment_mode` |
| `POST` | `/api/laufzettel/{id}/pay/bar` | Record cash payment — locks Laufzettel |
| `POST` | `/api/laufzettel/{id}/pay/karte` | Initiate card payment (Solo Cloud API or Payment Switch) |
| `GET` | `/api/laufzettel/{id}/pay/karte/status` | Poll transaction status (Solo mode only) |
| `POST` | `/api/laufzettel/{id}/pay/karte/confirm-mock` | Manually confirm payment (mock / Payment Switch) |
| `DELETE` | `/api/laufzettel/{id}/pay/karte` | Cancel a pending card payment |
| `DELETE` | `/api/laufzettel/{id}/pay` | Reset payment status (admin correction) |

`payment_mode` values: `"solo"` (Cloud API to paired Solo reader), `"payment_switch"` (URL scheme → SumUp app on phone), `"mock"`, or `null` (unconfigured).

> All `POST /pay/...` endpoints return `409` if the Laufzettel is already paid.

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
| `POST` | `/api/katalog/bulk-import` | Bulk-create location + categories + variants atomically |

### HTML page routes

| Method | Path | Template |
|---|---|---|
| `GET` | `/` | `landing.html` (public) |
| `GET` | `/dashboard` | `index.html` (admin) |
| `GET` | `/database` | `database.html` |
| `GET` | `/tags` | `tags.html` |
| `GET` | `/devices/{device_id}` | `device-detail.html` |
| `GET` | `/laufzettel` | `laufzettel.html` |
| `GET` | `/laufzettel/{id}` | `laufzettel-detail.html` |
| `GET` | `/katalog` | `katalog.html` |
| `GET` | `/mitglieder` | `mitglieder.html` |
| `GET` | `/kasse` | `kasse.html` |
| `GET` | `/member` | `member-laufzettel-open.html` |
| `GET` | `/member/laufzettel` | `member-laufzettel-open.html` |
| `GET` | `/member/laufzettel/{id}` | `member-laufzettel-detail.html` |
| `GET` | `/bug-report` | `bug-report.html` |
| `GET` | `/shopify` | `shopify.html` |
| `GET` | `/guest/laufzettel` | `guest-laufzettel-form.html` |
| `GET` | `/admin/users` | `admin-users.html` |

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
| `409` | Conflict (e.g. duplicate uid, or Laufzettel already paid and locked) |
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
