# Plan: Device Time Tracking via NFC Login/Logout

Track how long a user uses a device by scanning an NFC tag to "log in" and scanning again to "log out." The resulting time difference is used to calculate a time-based price that lands on the member's Laufzettel.

---

## Goals

- Member/guest taps NFC card on a device to start a timed session
- Taps again to end the session; duration is calculated and billed
- Price is derived from a linked catalog item (`MaterialVariante` with `per_minute` or `per_hour` pricing)
- Auto-logout at 21:00 daily; members can also self-logout from their dashboard
- Device page shows active sessions, history, and pricing configuration
- Guest support included; guest NFC tag is released on logout

---

## Confirmed Decisions

| # | Decision |
|---|----------|
| 1 | Pricing dropdown filters to `MaterialVariante` with `pricing_model` in `per_minute` / `per_hour` |
| 2 | Price display: "€X.XX/min" or "€X.XX/h" based on variante's `pricing_model` |
| 3 | No concurrent session limit (member can use multiple devices at once) |
| 4 | Keep `DeviceSession` history forever (add index on `created_at`) |
| 5 | Clear `guest_nfc_uid` on guest logout so the physical tag can be reused |
| 6 | `requires_permission` is per-device (on `DevicePricing`), not global |
| 7 | Guests can use time-billed devices |
| 8 | Auto-logout runs at 21:00 local time (Europe/Berlin) via APScheduler |

---

## Database Models (laufzettel.db)

### `DevicePricing` — links a device to a catalog item for time billing

```python
class DevicePricing(Base):
    __tablename__ = "device_pricing"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, unique=True, index=True)
    variante_id = Column(Integer, index=True, nullable=False)   # ref catalog.MaterialVariante
    requires_permission = Column(Integer, default=0)            # 1 = require DevicePermission, 0 = open
    is_active = Column(Integer, default=1)                      # enable/disable time billing
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
```

### `DeviceSession` — active or historical device usage session

```python
class DeviceSession(Base):
    __tablename__ = "device_sessions"

    id = Column(Integer, primary_key=True, index=True)
    laufzettel_id = Column(Integer, index=True, nullable=False)  # link to Laufzettel
    device_id = Column(String, index=True, nullable=False)
    uid = Column(String, index=True, nullable=False)
    mitglied_id = Column(Integer, index=True, nullable=True)     # member (if identified)
    guest_id = Column(String, index=True, nullable=True)         # guest (if not member)
    variante_id = Column(Integer, nullable=False)                # pricing snapshot
    start_time = Column(DateTime(timezone=True), default=_utcnow)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)            # calculated on end
    calculated_price = Column(Float, nullable=True)              # duration * unit price
    tax_rate = Column(Float, nullable=True)                      # snapshot from variante
    is_active = Column(Integer, default=1)                       # 1 = active, 0 = ended
    ended_by = Column(String, nullable=True)                     # "scan" | "member" | "admin" | "auto_2100"
    created_at = Column(DateTime(timezone=True), default=_utcnow)
```

---

## MQTT Handler Update (`backend/core/mqtt.py`)

In `handle_device_message()` when `subtopic in ("scan", "tag")`:

1. Validate member/guest (existing logic)
2. Look up `DevicePricing` for this `device_id` in `laufzettel.db`
   - If none or `is_active=0` → skip time tracking, fall through to existing behavior
3. If `requires_permission=1` → verify `DevicePermission` (existing logic)
4. Query `DeviceSession` for active session (`is_active=1`) for this `(device_id, uid)`

**If active session exists → LOGOUT:**
- Set `end_time = now`, compute `duration_seconds`
- Compute `calculated_price` based on `variante.pricing_model` (`per_minute` → duration/60, `per_hour` → duration/3600)
- Create/update `LaufzettelMaterial`:
  - `name = f"{variante.name} (Zeit)"`
  - `menge` = duration in minutes or hours (matching pricing model)
  - `unit` = "min" or "h"
  - `calculated_price`, `tax_rate`, `variante_id`
- Set `DeviceSession.is_active = 0`, `ended_by = "scan"`
- If guest: call `_release_guest_nfc_tag()` equivalent to clear `guest_nfc_uid`

**If no active session → LOGIN:**
- Get/create `Laufzettel` for member/guest (existing logic)
- Create `DeviceSession` with `start_time = now`, snapshot `variante_id` + `tax_rate`
- Add `device_id` to `Laufzettel.nodes` JSON

---

## Auto-Logout at 21:00 (`backend/laufzettel/utils.py` + `backend/main.py`)

APScheduler job (already started in `main.py`):

```python
scheduler.add_job(
    auto_end_sessions_at_2100,
    'cron',
    hour=21,
    minute=0,
    id='auto_end_sessions',
    timezone='Europe/Berlin'
)
```

`auto_end_sessions_at_2100()` logic:
- Find all `DeviceSession` where `is_active=1`
- For each: set `end_time` to 21:00 today (or now if already past), compute duration/price
- Create/update `LaufzettelMaterial` entry
- Set `ended_by = "auto_2100"`
- Release guest NFC tags if applicable

---

## API Endpoints

### Device Pricing (`backend/laufzettel/routes.py`)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `GET` | `/api/devices/{device_id}/pricing` | Get device pricing config + eligible catalog varianten | Admin/Member |
| `PUT` | `/api/devices/{device_id}/pricing` | Create/update device pricing (link to variante) | Admin |
| `DELETE` | `/api/devices/{device_id}/pricing` | Remove time billing from device | Admin |

### Device Sessions (`backend/laufzettel/routes.py`)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `GET` | `/api/devices/{device_id}/sessions` | List active + recent sessions for device | Admin/Member |
| `POST` | `/api/devices/{device_id}/sessions/{session_id}/stop` | Manual stop (admin) | Admin |

### Member Self-Service (`backend/member_routes.py`)

| Method | Path | Purpose | Auth |
|--------|------|---------|------|
| `GET` | `/api/member/device-sessions` | List member's active sessions across all devices | Member |
| `POST` | `/api/member/device-sessions/{session_id}/stop` | Member self-logout | Member |

---

## Device Detail Page Enhancements

### Template (`templates/device-detail.html`)

Add three sections:

1. **Pricing Configuration (admin only)**
   - Dropdown of catalog `MaterialVariante` filtered to `pricing_model` in (`per_minute`, `per_hour`)
   - Checkbox: "Requires Permission" (`requires_permission`)
   - Checkbox: "Time billing active" (`is_active`)
   - Save button → `PUT /api/devices/{device_id}/pricing`
   - Shows current price as "€X.XX/min" or "€X.XX/h"

2. **Active Sessions Table**
   - Columns: UID, Member/Guest, Start Time, Duration (live), End Session button
   - Live duration counter updates every second via JS
   - "End Session" → `POST /api/devices/{device_id}/sessions/{id}/stop` (admin only)

3. **Session History Table**
   - Recent ended sessions: UID, Member/Guest, Start, End, Duration, Price, Ended By
   - Sorted by `end_time` desc, limited to ~50 rows

### JavaScript (`static/js/device-detail.js`)

- Poll `/api/devices/{device_id}/sessions` every 10s
- Render active sessions with live `setInterval` duration counter
- Pricing form submit handler
- End session button handlers
- Price display helper ("€X.XX/min" vs "€X.XX/h")

---

## Member Dashboard Integration

### Template (`templates/member-laufzettel-open.html`)

Add **"Aktive Gerätenutzung"** card:
- List member's active `DeviceSession`s across all devices
- Per session: Device name, start time, live duration, estimated cost
- **"Ausloggen"** button per session → `POST /api/member/device-sessions/{id}/stop`

### Guest Support

- `DeviceSession.guest_id` links to `Laufzettel.guest_id`
- Guest login/logout via NFC scan works same as member
- On guest logout: clear `Laufzettel.guest_nfc_uid` so tag can be reused

---

## Files to Modify/Create

| File | Changes |
|------|---------|
| `backend/laufzettel/models.py` | Add `DevicePricing`, `DeviceSession` models |
| `backend/laufzettel/db.py` | Ensure `init_db()` creates new tables |
| `backend/core/mqtt.py` | Update `handle_device_message()` for login/logout logic |
| `backend/laufzettel/utils.py` | Add `auto_end_sessions_at_2100()` + price calc helper |
| `backend/main.py` | Register APScheduler job for 21:00 auto-logout |
| `backend/laufzettel/routes.py` | Add device pricing + session API endpoints |
| `backend/member_routes.py` | Add member self-logout endpoints |
| `templates/device-detail.html` | Add pricing config + session tables sections |
| `static/js/device-detail.js` | Add session polling, pricing form, live timers |
| `static/css/device-detail.css` | Styles for new sections (optional, can reuse existing) |
| `templates/member-laufzettel-open.html` | Add active sessions card with logout buttons |

---

## Implementation Order

1. **Models** — `DevicePricing`, `DeviceSession` in `laufzettel/models.py`
2. **DB init** — ensure tables auto-create on startup
3. **MQTT handler** — login/logout logic in `core/mqtt.py`
4. **Price calculation helper** — in `laufzettel/utils.py`
5. **Auto-logout job** — `auto_end_sessions_at_2100()` + scheduler registration
6. **API endpoints** — device pricing CRUD + session list/stop
7. **Member self-logout** — endpoints in `member_routes.py`
8. **Device detail page** — template + JS for pricing config and sessions
9. **Member dashboard** — active sessions card with self-logout
10. **Test end-to-end** — scan in, scan out, verify price on Laufzettel

---

## Migration Strategy

- New tables only; no changes to existing schema
- Tables auto-created via SQLAlchemy `init_db()` on next startup
- Admin configures pricing per device via device detail page after deploy
- No data backfill needed
