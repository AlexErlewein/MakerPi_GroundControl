# 15 - Mitglieder-Bereich

## Übersicht

Das System unterscheidet zwischen zwei Benutzertypen:
- **Admins**: Vollzugriff auf alle Funktionen
- **Mitglieder**: Eingeschränkter Zugriff auf eigene Laufzettel

## Rollen-System

### Admin (`role: "admin"`)
- Zugriff auf Dashboard (`/dashboard`)
- Verwaltung aller Laufzettel
- Mitgliederverwaltung
- Katalog-Verwaltung
- Admin-User-Verwaltung
- Bezahl-Funktionen

### Mitglied (`role: "member"`)
- Zugriff auf Mitglieder-Dashboard (`/member`)
- Nur eigene Laufzettel einsehen
- Materialien zu eigenen Laufzettel hinzufügen
- Kein Bearbeiten/Löschen von Einträgen
- Keine Bezahl-Funktion

## Anmeldung

### Option 1: RFID-Karte (Mitglieder)
1. Mitglied hält Karte an RFID-Reader
2. System erkennt Karte und loggt automatisch ein
3. Weiterleitung zum Mitglieder-Bereich

### Option 2: Benutzername/Passwort
- Mitglieder: Zugriff auf `/member`
- Admins: Zugriff auf `/dashboard`

## Datenbank-Schema

```sql
-- Users Tabelle mit Rollen
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT DEFAULT 'member',  -- 'admin' oder 'member'
    mitglied_id INTEGER,           -- Link zur members Tabelle
    created_at TIMESTAMP
);
```

## API-Endpunkte

### Mitglied-spezifisch
- `GET /member` - Mitglieder-Dashboard
- `GET /member/laufzettel` - Eigene Laufzettel
- `GET /member/laufzettel/{id}` - Laufzettel-Details
- `POST /api/member/laufzettel/{id}/material` - Material hinzufügen
- `POST /api/auth/login-rfid` - RFID-Login

### Admin-spezifisch
- `GET /dashboard` - Admin-Dashboard
- `GET /admin/*` - Alle Admin-Funktionen
- `POST /admin/users/add` - User erstellen

## Konfiguration

### Ersten Admin erstellen
Beim ersten Start wird automatisch ein Admin-User erstellt:
- Username: `admin` (oder `ADMIN_USERNAME` aus config)
- Passwort: `changeme` (oder `ADMIN_PASSWORD` aus config)
- Role: `admin`

### Mitglieder-User erstellen
```bash
curl -X POST http://localhost:8000/admin/users/add \
  -d "username=mitglied1" \
  -d "password=passwort123" \
  -d "role=member"
```

### RFID-Karte zuweisen
1. Mitglied in Datenbank erstellen
2. RFID-Tag mit Mitglied verknüpfen (über Mitglieder-Verwaltung)
3. User hat dann automatisch Zugriff via RFID

## Sicherheit

### Session-Handling
- Session-Cookies mit `SECRET_KEY` signiert
- Session enthält: `user`, `role`, `mitglied_id`
- Bei ungültiger Session: automatische Weiterleitung zur Landing Page

### Zugriffsprüfung
```python
# Beispiel: Mitglied-Endpunkt
def require_member(request: Request):
    user = get_current_user(request)
    if user.role not in ["admin", "member"]:
        raise HTTPException(401, "Access denied")
    return user
```

### Laufzettel-Sicherheit
Mitglieder können nur Laufzettel sehen, die `mitglied_id` entsprechen:
```python
laufzettel = db.query(Laufzettel).filter(
    Laufzettel.mitglied_id == current_user.mitglied_id
).all()
```

## Frontend

### Landing Page (`/`)
- RFID-Scan-Bereich für Mitglieder
- Link zum Admin-Login
- Dokumentation-Link

### Mitglieder-UI
- Vereinfachte Ansicht ohne Admin-Funktionen
- Keine "Bezahlen"-Buttons
- Keine "Löschen"-Buttons
- Nur "Material hinzufügen" bei offenen Laufzetteln

### Admin-UI
- Vollständige Funktionalität
- Alle Laufzettel sichtbar
- Bezahl-Funktionen aktiv

## Troubleshooting

### "User not found" Fehler
- Alte Session-Cookies löschen
- Browser-Cache leeren
- Incognito-Fenster testen

### RFID funktioniert nicht
- MQTT-Broker läuft?
- RFID-Reader korrekt verbunden?
- Tag im System registriert?
- Mitglied mit Tag verknüpft?

### Zugriffsprobleme
- User hat richtige `role`?
- Mitglied hat `mitglied_id` gesetzt?
- Session gültig (nicht abgelaufen)?

## Dateien

- `backend/auth/models.py` - User-Model mit role/mitglied_id
- `backend/member_routes.py` - Mitglied-spezifische Routes
- `backend/auth/routes.py` - Login/Session-Routes
- `templates/landing.html` - Startseite mit RFID
- `templates/member-laufzettel-open.html` - Offenes Mitglieder-Laufzettel
- `templates/member-laufzettel-historie.html` - Mitglieder-Zahlungshistorie
- `templates/member-laufzettel-detail.html` - Mitglied-Detailansicht
- `static/css/member.css` - Styling für den Mitglieder-Bereich
