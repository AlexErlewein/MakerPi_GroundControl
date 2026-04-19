# Wie man Dinge ändert

Diese Seite ist ein Nachschlagewerk für häufige Änderungen und Erweiterungen.

## Inhaltsverzeichnis

1. [Preise ändern](#preise-ändern)
2. [Neues Material hinzufügen](#neues-material-hinzufügen)
3. [Admin-Passwort zurücksetzen](#admin-passwort-zurücksetzen)
4. [Neues UI-Feature hinzufügen](#neues-ui-feature-hinzufügen)
5. [Neuen API-Endpunkt hinzufügen](#neuen-api-endpunkt-hinzufügen)
6. [MQTT-Topic hinzufügen](#mqtt-topic-hinzufügen)

---

## Preise ändern

### Szenario: PLA-Filament wird teurer

1. **Zum Katalog navigieren** → `/katalog`
2. **Standort aufklappen** → z.B. "3D-Druck"
3. **Kategorie finden** → z.B. "PLA"
4. **"Bearbeiten" klicken** neben der Variante
5. **Neuen Preis eingeben**
6. **Speichern**

> ⚠️ **Hinweis:** Bereits berechnete Materialien in Laufzetteln behalten den alten Preis. Nur neue Einträge verwenden den neuen Preis.

---

## Neues Material hinzufügen

### Szenario: Neues Filament-Typ einführen

**Option A: Via Web-UI**

1. `/katalog` öffnen
2. Standort wählen (oder neuen erstellen)
3. "+ Kategorie" klicken
4. Name: "PETG", Preismodell: "pro_gramm"
5. "+ Variante" für jede Farbe/Größe

**Option B: Direkt in Datenbank** (Bulk-Import)

```python
# admin_script.py
from backend.catalog.models import MaterialKategorie, MaterialVariante
from backend.catalog.db import SessionLocal

db = SessionLocal()

# Kategorie erstellen
kat = MaterialKategorie(
    location_id=1,  # 3D-Druck
    name="PETG",
    pricing_model="pro_gramm",
    unit="g"
)
db.add(kat)
db.flush()

# Varianten hinzufügen
for color in ["Weiß", "Schwarz", "Blau"]:
    var = MaterialVariante(
        kategorie_id=kat.id,
        name=f"{color}, 1kg",
        preis_pro_einheit=0.045  # 4.5ct/g
    )
    db.add(var)

db.commit()
```

---

## Admin-Passwort zurücksetzen

### Wenn du das Passwort vergessen hast:

**Option 1: Via Web-UI (als Admin)**
- `/admin/users` → "Passwort ändern"

**Option 2: Datenbank direkt**

```bash
# SQLite-CLI öffnen
sqlite3 backend/auth.db

# Passwort hashen (bcrypt mit passlib)
# Für 'neues_passwort':
UPDATE users SET hashed_password = '$2b$12$...' WHERE username = 'admin';
```

**Option 3: Config zurücksetzen**

```bash
# config.json bearbeiten
{
  "admin_password": "temporär"
}

# Service neustarten
sudo systemctl restart makerpi-groundcontrol
```

---

## Neues UI-Feature hinzufügen

### Szenario: Neues Feld im Laufzettel

**Schritte:**

1. **Template ändern** (`templates/laufzettel-detail.html`)
```html
<div class="form-group">
    <label for="new-field">Neues Feld</label>
    <input type="text" id="new-field">
</div>
```

2. **JS-Logik hinzufügen** (`static/js/laufzettel-detail.js`)
```javascript
document.getElementById('save-btn').addEventListener('click', () => {
    const newField = document.getElementById('new-field').value;
    // API-Aufruf...
});
```

3. **API-Endpunkt erweitern** (siehe nächster Abschnitt)

4. **Datenbank-Schema aktualisieren** (falls nötig)

---

## Neuen API-Endpunkt hinzufügen

### Szenario: Statistik-Endpunkt

**In `backend/core/routes.py`:**

```python
@router.get("/api/stats/daily")
async def get_daily_stats(
    date: str = Query(default=None),
    db: Session = Depends(get_db)
):
    from datetime import date as dt_date
    
    target_date = dt_date.fromisoformat(date) if date else dt_date.today()
    
    # Abfragen
    total = db.query(Laufzettel).filter(Laufzettel.date == target_date).count()
    paid = db.query(Laufzettel).filter(
        Laufzettel.date == target_date,
        Laufzettel.payment_method.isnot(None)
    ).count()
    
    revenue = db.query(func.sum(LaufzettelMaterial.calculated_price)).join(
        Laufzettel
    ).filter(
        Laufzettel.date == target_date,
        Laufzettel.payment_method.isnot(None)
    ).scalar() or 0
    
    return {
        "date": target_date.isoformat(),
        "total_laufzettel": total,
        "paid": paid,
        "pending": total - paid,
        "revenue": round(revenue, 2)
    }
```

---

## MQTT-Topic hinzufügen

### Szenario: Neue Gerätetypen

**Aktuelle Struktur:**
```
makerpi/devices/{device_id}/status
makerpi/devices/{device_id}/event
makerpi/devices/{device_id}/sensors
```

**Neues Topic hinzufügen:**

1. **In `backend/core/mqtt.py`:**

```python
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode()
    
    # Existierende Handler...
    
    # Neuer Handler
    if topic.endswith('/alert'):
        handle_alert(topic, payload)

def handle_alert(topic, payload):
    # Logik hier
    device_id = topic.split('/')[2]
    # Alert verarbeiten, Benachrichtigung senden, etc.
```

2. **Datenbank-Schema erweitern** (falls neue Daten gespeichert werden)

3. **UI aktualisieren** um Alerts anzuzeigen

---

## Häufige Fehler

### "Template not found"

- Template-Datei in `templates/` prüfen
- Namen auf Tippfehler überprüfen
- App neustarten (Caching)

### "404 Not Found" für API

- Route in `main.py` registriert?
- URL-Parameter korrekt?
- HTTP-Methode stimmt?

### Datenbank-Fehler nach Schema-Änderung

```bash
# Migration nötig?
sqlite3 backend/laufzettel.db ".schema laufzettel"

# Manuelle Migration
ALTER TABLE laufzettel ADD COLUMN new_field TEXT;
```

---

## Entwicklungs-Workflow

### Lokale Änderungen testen

```bash
# 1. Code ändern
# 2. Speichern
# 3. Auto-Reload wartet...

# Oder manuell:
uv run uvicorn backend.main:app --reload --port 8000
```

### Debug-Logging

```python
import logging
logger = logging.getLogger(__name__)

# In Route
logger.info(f"Laufzettel {id} geladen")
logger.error(f"Fehler: {e}")
```

---

## Test-Daten generieren

```bash
# Python-Script für Demo-Daten
python scripts/generate_demo_data.py

# Erstellt:
# - 50 Mitglieder
# - 100 Laufzettel
# - 500 Material-Einträge
```

---

## Noch Fragen?

- Technische Details: [System-Architektur](./05-system-architecture)
- API-Referenz: [Backend-API](./08-backend-api)
- Datenstruktur: [Datenbank-Modell](./07-database-model)
