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
- `GET /member/laufzettel` - Offener (unbezahlter) Laufzettel
- `GET /member/laufzettel/historie` - Bezahlte Laufzettel (Historie)
- `GET /member/laufzettel/{id}` - Laufzettel-Detailansicht (Lesemodus)
- `GET /member/konto` - Kontoinformationen und Passwortänderung
- `GET /api/member/me` - Eigene Profildaten abrufen (JSON)
- `POST /api/member/laufzettel/{id}/material` - Material hinzufügen
- `GET /api/member/laufzettel/{id}/pdf` - PDF-Download des eigenen Laufzettels
- `POST /api/member/password` - Passwort ändern
- `POST /api/auth/login-rfid` - RFID-Login

### Admin-spezifisch
- `GET /dashboard` - Admin-Dashboard
- `GET /admin/*` - Alle Admin-Funktionen
- `POST /admin/users/add` - User erstellen

## Passwort-Verwaltung

### Passwort ändern: `POST /api/member/password`

Mitglieder können ihr Passwort über das Konto-Formular ändern. Die Route ist unter `/member/konto` erreichbar.

**Request-Body** (Form-encoded):

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `current_password` | string | Nein* | Aktuelles Passwort |
| `new_password` | string | Ja | Neues Passwort (mind. 4 Zeichen) |

*Für neue Mitglieder ohne gesetztes Passwort kann `current_password` weggelassen oder als `H3cke` übermittelt werden.

**Standard-Passwort für neue Mitglieder**

Mitglieder, die über den easyVerein-Sync importiert werden, haben zunächst kein Login-Passwort. Das System behandelt in diesem Fall `H3cke` als implizites Standard-Passwort — es ist nicht in der Datenbank gespeichert, sondern wird bei der Verifizierung dynamisch erzeugt. Beim ersten Passwort-Setzen:

1. `current_password` ist optional oder `"H3cke"`
2. Das neue Passwort muss mindestens 4 Zeichen haben
3. War noch kein `login_username` gesetzt, wird er automatisch aus dem Mitgliedsnamen abgeleitet (Fallback: `member_{id}`)
4. Das neue Passwort-Hash wird sowohl in `members.db` (`login_password_hash`) als auch in `auth.db` (`hashed_password`) gespeichert

**Erfolgreiche Antwort:**

```json
{
  "success": true,
  "has_password": true
}
```

**Fehlerfälle:**

| HTTP-Status | Fehler |
|---|---|
| 400 | Kein Mitgliedsprofil verknüpft |
| 400 | Passwort zu kurz (unter 4 Zeichen) |
| 400 | `current_password` fehlt (wenn bereits ein Passwort gesetzt ist) |
| 403 | Aktuelles Passwort ist falsch |
| 404 | Mitglied nicht gefunden |

**Beispiel-Request:**

```bash
curl -X POST http://localhost:8000/api/member/password \
  -b "session=..." \
  -d "current_password=H3cke" \
  -d "new_password=MeinNeuesPasswort"
```

### Konto-Seite (`GET /member/konto`)

Die Konto-Seite zeigt:
- Benutzername
- Verknüpftes Mitgliedsprofil (Name, E-Mail, Mitgliedsnummer)
- Ob bereits ein Passwort gesetzt wurde (`has_password`)
- Formular zur Passwort-Änderung

## Account-Provisionierung (Admin)

Wenn ein Mitglied erstmalig per Benutzername/Passwort einloggen soll (nicht per RFID), muss ein Login-Account provisioniert werden.

### Automatisch beim RFID-Login

Beim ersten RFID-Scan eines Mitglieds erstellt das System automatisch einen `User`-Eintrag in `auth.db`:

```python
user = User(
    username=mitglied.name,  # Fallback: "member_{id}"
    hashed_password="",      # Leer — nur RFID-Login
    role="admin" if is_admin_card else "member",
    mitglied_id=mitglied.id,
)
```

### Manuell über Admin-UI

Admins können über `POST /admin/users/add` einen User mit Passwort anlegen:

```bash
curl -X POST http://localhost:8000/admin/users/add \
  -d "username=vorname.nachname" \
  -d "password=H3cke" \
  -d "role=member"
```

Nach der Erstellung kann das Mitglied unter `/member/konto` sein Passwort selbst ändern.

### Mitglied mit eigenem Login (`login_username` / `login_password_hash`)

Mitglieder können sich auch direkt über ihre `members.db`-Zugangsdaten einloggen — ohne eigenen `User`-Eintrag in `auth.db`. Der Login-Flow prüft zunächst `auth.db`, dann `members.db`. Die Felder `login_username` und `login_password_hash` in der `Mitglied`-Tabelle werden beim Passwort-Setzen über `POST /api/member/password` befüllt.

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
  -d "password=H3cke" \
  -d "role=member"
```

### RFID-Karte zuweisen
1. Mitglied in Datenbank erstellen
2. RFID-Tag mit Mitglied verknüpfen (über Mitglieder-Verwaltung)
3. User hat dann automatisch Zugriff via RFID

## Sicherheit

### Session-Handling
- Session-Cookies mit `SECRET_KEY` signiert
- Session enthält: `user`, `role`, `mitglied_id`, `last_activity`
- Bei ungültiger Session: automatische Weiterleitung zur Landing Page
- `last_activity` wird bei jedem API-Aufruf aktualisiert (Keep-alive)

### Zugriffsprüfung
```python
# Beispiel: Mitglied-Endpunkt
def require_member(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not authenticated")
    user = db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        raise HTTPException(403, "Access denied")
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

### Passwort vergessen
Admins können das Passwort eines Mitglieds zurücksetzen, indem sie den `User`-Eintrag in `auth.db` löschen und neu anlegen. Alternativ kann `login_password_hash` direkt in `members.db` zurückgesetzt werden — beim nächsten Passwort-Setzen gilt dann wieder `H3cke` als Standard.

## Dateien

- `backend/auth/models.py` - User-Model mit role/mitglied_id
- `backend/member_routes.py` - Mitglied-spezifische Routes inkl. Passwort-Änderung
- `backend/auth/routes.py` - Login/Session-Routes
- `templates/landing.html` - Startseite mit RFID
- `templates/member-laufzettel-open.html` - Offenes Mitglieder-Laufzettel
- `templates/member-laufzettel-historie.html` - Mitglieder-Zahlungshistorie
- `templates/member-laufzettel-detail.html` - Mitglied-Detailansicht
- `templates/member-konto.html` - Konto- und Passwort-Seite
- `static/css/member.css` - Styling für den Mitglieder-Bereich
