# 26 · Authentifizierungssystem

Dieses Dokument bietet einen umfassenden technischen Deep-Dive in das MakerPi GroundControl Authentifizierungssystem, konzipiert zum Lernen und Verständnis der Sicherheitsarchitektur.

---

## Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Architektur](#architektur)
3. [Zweistufiges Authentifizierungsmodell](#zweistufiges-authentifizierungsmodell)
4. [Session-Management](#session-management)
5. [Login-Flows](#login-flows)
6. [Admin-Verifizierung](#admin-verifizierung)
7. [Sicherheitsfunktionen](#sicherheitsfunktionen)
8. [Timeout-Mechanismen](#timeout-mechanismen)
9. [Datenbank-Schema](#datenbank-schema)
10. [Code-Deep-Dive](#code-deep-dive)
11. [Sicherheits-Best-Practices](#sicherheits-best-practices)
12. [Systemerweiterung](#systemerweiterung)
13. [OAuth-Integration](#oauth-integration)

---

## Überblick

Das MakerPi GroundControl Authentifizierungssystem ist ein **session-basiertes, zweistufiges Authentifizierungs-Framework**, das Folgendes bietet:

- **Basis-Authentifizierung** für Mitgliederzugang
- **Admin-Verifizierung** für sensible Operationen
- **RFID-Tag-Unterstützung** für physischen Zugang
- **Automatisches Timeout** für Sicherheit
- **Rollenbasierte Zugriffskontrolle** (RBAC)

### Wichtige Design-Prinzipien

1. **Session-basiert** - Keine API-Tokens, verwendet sichere HTTP-only Cookies
2. **Defense in Depth** - Zweistufige Authentifizierung für sensible Operationen
3. **Activity Tracking** - Zeitstempel-basierte Timeout-Enforcement
4. **Flexible Benutzertypen** - Admin-only, Mitglied-only und Hybrid-Benutzer
5. **Physischer Zugang** - RFID-Tag-Integration für Makerspace-Umgebungen

---

## Architektur

### Systemkomponenten

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Browser)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Login Form   │  │ RFID Scanner  │  │ Admin Panel  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Session Middleware (Starlette)              │  │
│  │  - Cookie-basierte Session-Speicherung                │  │
│  │  - Secret Key Signing                                 │  │
│  │  - Automatische Cookie-Verarbeitung                   │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Auth Router (/auth, /login)              │  │
│  │  - Unified Login Endpoint                            │  │
│  │  - RFID Login Endpoint                               │  │
│  │  - Admin Verifizierung                               │  │
│  │  - Session Management                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Auth Dependencies (auth/dependencies.py)    │  │
│  │  - check_auth()                                       │  │
│  │  - is_admin_verified()                               │  │
│  │  - verify_admin_password()                           │  │
│  │  - is_member_session_valid()                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   Datenbanken (SQLite)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  auth.db     │  │ members.db   │  │  core.db     │    │
│  │  - User      │  │  - Mitglied  │  │  - Device    │    │
│  │  - Password  │  │  - RFIDTag   │  │  - TagScan   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Request-Flow

```
1. User Request
   ↓
2. Session Middleware (prüft Cookie)
   ↓
3. Route Handler (ruft Auth-Dependency auf)
   ↓
4. Auth Dependency (validiert Session)
   ↓
5. Business Logic (wenn Auth erfolgreich)
   ↓
6. Response
```

---

## Zweistufiges Authentifizierungsmodell

### Level 1: Basis-Authentifizierung

**Zweck:** Zugriff auf Mitgliederbereich und grundlegende Operationen gewähren

**Implementierung:** `check_auth(request: Request) -> bool`

**Anforderungen:**
- Gültige Session mit `user`-Key
- Session nicht abgelaufen (3-Minuten-Timeout)

**Gewährt Zugriff auf:**
- Mitgliederbereich (`/member`)
- Mitglied-spezifische Daten
- Basis-API-Endpunkte
- Persönliche Laufzettel

**Code:**
```python
def check_auth(request: Request) -> bool:
    """Prüft, ob Benutzer authentifiziert ist"""
    return request.session.get("user") is not None
```

### Level 2: Admin-Verifizierung

**Zweck:** Zugriff auf sensible administrative Operationen gewähren

**Implementierung:** `is_admin_verified(request: Request) -> bool`

**Anforderungen:**
- Gültige Session mit `user`-Key
- Benutzer ist admin-fähig (`is_admin_capable = True`)
- Admin-Verifizierung aktiv (`admin_verified = True`)
- Verifizierung nicht abgelaufen (10-Minuten-Timeout)

**Gewährt Zugriff auf:**
- Admin-Dashboard (`/dashboard`)
    - Benutzermanagement (`/admin/users`)
    - Geräte-Pairing
    - Systemkonfiguration
    - Finanzdaten-Zugriff
    - Gift-Card-Management

**Code:**
```python
def is_admin_verified(request: Request) -> bool:
    """Prüft, ob Benutzer Admin-Status verifiziert hat (mit 10min Timeout)"""
    session = request.session
    if not session.get("admin_verified"):
        return False

    admin_verified_at = session.get("admin_verified_at")
    last_activity = session.get("last_activity")

    if not admin_verified_at or not last_activity:
        return False

    # ISO-Format-Strings zu datetime parsen
    try:
        last_activity_dt = datetime.fromisoformat(last_activity)
        if last_activity_dt.tzinfo is None:
            last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False

    # 10min Timeout prüfen
    now = datetime.now(timezone.utc)
    if (now - last_activity_dt).total_seconds() > (ADMIN_TIMEOUT_MINUTES * 60):
        # Timeout abgelaufen, Admin-Verifizierung löschen
        session["admin_verified"] = False
        session["admin_verified_at"] = None
        return False

    # Last Activity aktualisieren
    session["last_activity"] = now.isoformat()
    return True
```

### Zugriffskontroll-Matrix

| Operation | Level Erforderlich | Dependency | Timeout |
|---|---|---|---|
| Mitgliederbereich anzeigen | Level 1 | `check_auth` | 3 min |
| Laufzettel erstellen | Level 1 | `check_auth` | 3 min |
| Buchhaltungsdaten anzeigen | Level 1 | `check_auth` | 3 min |
| Admin-Dashboard anzeigen | Level 2 | `is_admin_verified` | 10 min |
| Benutzermanagement | Level 2 | `is_admin_verified` | 10 min |
| Geräte-Pairing | Level 2 | `is_admin_verified` | 10 min |
| Gift-Card-Operationen | Level 1 | `check_auth` | 3 min |

---

## Session-Management

### Session-Struktur

Sessions werden als HTTP-only Cookies gespeichert, die mit einem Secret Key signiert sind. Die Session-Datenstruktur:

```python
{
    # Basis-Authentifizierung
    "user": str,                    # Username (erforderlich für Level 1)
    "mitglied_id": int,             # Mitglieder-Datenbank-ID (optional)
    "login_method": str,            # "password" oder "rfid"
    
    # Admin-Fähigkeiten
    "is_admin_capable": bool,       # Kann Admin werden
    "admin_verified": bool,          # Aktuell im Admin-Modus
    "admin_verified_at": str,        # ISO-Timestamp wann verifiziert
    
    # Activity Tracking
    "last_activity": str,           # ISO-Timestamp der letzten Anfrage
}
```

### Session-Lebenszyklus

```
1. Login → Session Erstellt
   ├─ user: "username"
   ├─ login_method: "password" oder "rfid"
   ├─ is_admin_capable: bestimmt durch Benutzertyp
   ├─ admin_verified: False
   └─ last_activity: aktueller Timestamp

2. Aktivität → Session Aktualisiert
   └─ last_activity: bei jeder Anfrage aktualisiert

3. Admin-Verifizierung → Admin-Modus Aktiviert
   ├─ admin_verified: True
   └─ admin_verified_at: aktueller Timestamp

4. Timeout → Session Gelöscht/Downgraded
   ├─ Level 1 Timeout (3 min): Vollständige Session gelöscht
   └─ Level 2 Timeout (10 min): admin_verified = False

5. Logout → Session Zerstört
   └─ Alle Session-Daten gelöscht
```

### Session-Sicherheitsfunktionen

1. **HTTP-Only Cookies** - Nicht via JavaScript zugänglich
2. **Signed Cookies** - Kryptografisch signiert mit Secret Key
3. **Secure Flag** - Nur über HTTPS übertragen (in Produktion)
4. **SameSite Protection** - CSRF-Schutz
5. **Automatisches Ablaufen** - Serverseitiges Timeout-Enforcement

---

## Login-Flows

### Unified Login Flow

Das System unterstützt mehrere Benutzertypen durch einen einzigen Login-Endpunkt:

```
POST /api/auth/login
{
    "username": "user",
    "password": "pass"
}
```

#### Flowchart

```
┌─────────────────────────────────────────────────────────┐
│                    Login Request                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ Check auth.db User     │
        │ (admin users)          │
        └──────────┬─────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼────┐         ┌─────▼─────┐
   │ Found?  │         │ Not found │
   └────┬────┘         └─────┬─────┘
        │ Yes                  │
        ▼                      │
┌──────────────────┐           │
│ Verify password │           │
└────────┬─────────┘           │
         │                     │
    ┌────┴────┐         ┌─────▼─────┐
    │ Valid?  │         │ Check     │
    └────┬────┘         │ members.db│
         │ No             │ Mitglied  │
         │               └─────┬─────┘
    ┌────▼────┐               │
    │ Return  │         ┌─────▼─────┐
    │ Error   │         │ Found?    │
    └─────────┘         └─────┬─────┘
                        │
                   ┌──────┴──────┐
                   │            │
              ┌────▼────┐  ┌───▼────┐
              │ Yes     │  │ No     │
              └────┬────┘  └───┬────┘
                   │           │
                   ▼           ▼
          ┌──────────────┐  ┌──────────────┐
          │ Verify      │  │ Return error │
          │ member      │  │ Invalid      │
          │ password    │  │ credentials  │
          └──────┬───────┘  └──────────────┘
                 │
           ┌────┴────┐
           │ Valid?  │
           └────┬────┘
                │ Yes
                ▼
     ┌──────────────────────┐
     │ Session erstellen     │
     │ User-Fähigkeiten setz │
     │ Redirect zu Bereich   │
     └──────────────────────┘
```

### Benutzertyp 1: Admin-Only Benutzer

**Quelle:** `auth.db` → `User` Tabelle

**Merkmale:**
- Erstellt via Admin-Panel
- Hat `role = "admin"`
- Kein `mitglied_id` (nicht mit Mitglied verknüpft)
- Passwort in `auth.db` gespeichert

**Login-Prozess:**
```python
# 1. auth.db prüfen
user = get_user(db, username)
if user and verify_password(password, user.hashed_password):
    # 2. Prüfen ob admin-only
    if user.role == "admin" and not user.mitglied_id:
        # 3. Auto-verify (Passwort gerade eingegeben)
        request.session["admin_verified"] = True
        request.session["admin_verified_at"] = now.isoformat()
        # 4. Redirect zu Dashboard
        return RedirectResponse("/dashboard")
```

**Session-Daten:**
```python
{
    "user": "admin",
    "mitglied_id": None,
    "is_admin_capable": True,
    "admin_verified": True,  # Auto-verified
    "login_method": "password"
}
```

### Benutzertyp 2: Mitglieder

**Quelle:** `members.db` → `Mitglied` Tabelle

**Merkmale:**
- Erstellt via Mitglieder-Registrierung oder easyVerein-Sync
- Hat `login_username` und `login_password_hash`
- Kann Admin-RFID-Tag haben
- Passwort in `members.db` gespeichert

**Login-Prozess:**
```python
# 1. members.db prüfen
mitglied = members_db.query(Mitglied).filter(
    Mitglied.login_username == username
).first()

if mitglied and verify_password(password, mitglied.login_password_hash):
    # 2. Admin-RFID-Tag prüfen
    admin_tag = members_db.query(RFIDTag).filter(
        RFIDTag.member_id == mitglied.member_id,
        RFIDTag.is_admin == True,
        RFIDTag.active == 1
    ).first()
    
    # 3. Fähigkeiten setzen
    has_admin = bool(admin_tag)
    request.session["is_admin_capable"] = has_admin
    
    # 4. Redirect zu Mitgliederbereich
    return RedirectResponse("/member")
```

**Session-Daten:**
```python
{
    "user": "member_username",
    "mitglied_id": 123,
    "is_admin_capable": True,  # Wenn Admin-Tag
    "admin_verified": False,  # Erfordert manuelle Verifizierung
    "login_method": "password"
}
```

### Benutzertyp 3: Hybrid-Benutzer (Mitglied + Admin)

**Quelle:** Sowohl `auth.db` als auch `members.db`

**Merkmale:**
- Mitglied mit Admin-RFID-Tag
- Oder Mitglied verknüpft mit Admin-Benutzer in `auth.db`
- Kann Mitgliederbereich zugreifen
- Kann mit Verifizierung Admin werden

**Login-Prozess:**
```python
# 1. auth.db zuerst prüfen (admin users)
user = get_user(db, username)
if user and verify_password(password, user.hashed_password):
    if user.role == "admin" and user.mitglied_id:
        # Hybrid: Admin mit Mitglieder-Link
        request.session["is_admin_capable"] = True
        request.session["admin_verified"] = False  # Manuelle Verifizierung
        return RedirectResponse("/member")

# 2. members.db prüfen (member users)
mitglied = members_db.query(Mitglied).filter(
    Mitglied.login_username == username
).first()
if mitglied and verify_password(password, mitglied.login_password_hash):
    # Admin-Tag prüfen
    admin_tag = members_db.query(RFIDTag).filter(
        RFIDTag.member_id == mitglied.member_id,
        RFIDTag.is_admin == True
    ).first()
    
    has_admin = bool(admin_tag)
    request.session["is_admin_capable"] = has_admin
    return RedirectResponse("/member")
```

### RFID Login Flow

**Endpoint:** `POST /api/auth/login-rfid`

**Zweck:** Physische RFID-Tags können Login auslösen

**Prozess:**
```python
POST /api/auth/login-rfid
{
    "uid": "9CF22507"
}

# 1. UID in members.db nachschlagen
#    a. Mitglied.nfc_uid prüfen (eingetragen via Mitglieder-UI)
#    b. RFIDTag.uid prüfen (legacy Tag-Tabelle)

# 2. Wenn gefunden, Session erstellen
mitglied = members_db.query(Mitglied).filter(
    Mitglied.nfc_uid == uid.upper()
).first()

if mitglied:
    request.session["user"] = mitglied.login_username or str(mitglied.id)
    request.session["mitglied_id"] = mitglied.id
    request.session["login_method"] = "rfid"
    
    # 3. Admin-Tag prüfen
    admin_tag = members_db.query(RFIDTag).filter(
        RFIDTag.member_id == mitglied.member_id,
        RFIDTag.is_admin == True
    ).first()
    
    request.session["is_admin_capable"] = bool(admin_tag)
    request.session["admin_verified"] = False
```

**Wichtig:** RFID-Login **kann** nicht Auto-Verify verwenden. Muss für Admin-Zugriff manuell mit Passwort verifizieren.

### OAuth Login Flow

**Endpoint:** `GET /auth/google` → `GET /auth/google/callback`

**Zweck:** Benutzer können sich mit ihrem Google-Konto anmelden

**Prozess:**
```python
# 1. Redirect zu Google OAuth
GET /auth/google
→ Redirect zu https://accounts.google.com/o/oauth2/v2/auth

# 2. Benutzer genehmigt Zugriff
→ Google redirect zu /auth/google/callback mit Authorization Code

# 3. Code gegen Token tauschen
GET /auth/google/callback?code=...
→ Tauscht Code gegen Access Token
→ Parst ID Token um User Info zu erhalten (email, name)

# 4. User in auth.db abrufen oder erstellen
user = auth_db.query(User).filter(User.username == email).first()

if user:
    # Existierender User - verwende seine Rolle
    is_admin = user.role == "admin"
else:
    # Neuen User erstellen
    user = User(
        username=email,
        hashed_password="",  # Kein Passwort für OAuth-User
        role="member",
        mitglied_id=None,
    )
    auth_db.add(user)
    auth_db.commit()
    is_admin = False

# 5. Session erstellen
request.session["user"] = email
request.session["mitglied_id"] = user.mitglied_id
request.session["is_admin_capable"] = is_admin
request.session["login_method"] = "oauth"
request.session["admin_verified"] = is_admin  # Auto-Verify für OAuth-Admins
request.session["admin_verified_at"] = datetime.now(timezone.utc).isoformat() if is_admin else None
request.session["last_activity"] = datetime.now(timezone.utc).isoformat()
```

**Wichtig:** OAuth-User mit `role='admin'` werden automatisch verifiziert (kein Passwort-Wiedereingabe erforderlich). Dies ist ein Sicherheits-Kompromiss für bessere UX. Um zu deaktivieren, ändere `backend/auth/oauth.py`.

**Konfiguration:**
```json
{
    "oauth_enabled": true,
    "oauth_google_client_id": "deine-client-id.apps.googleusercontent.com",
    "oauth_google_client_secret": "dein-client-secret",
    "oauth_google_redirect_uri": "https://deine-pi-ip:8443/auth/google/callback"
}
```

**Setup:** Siehe [OAuth Setup-Anleitung](/docs/28-oauth-setup.de.md) für detaillierte Anweisungen.

---

## Admin-Verifizierung

### Warum Zweistufige Authentifizierung?

**Problem:** Einstufige Authentifizierung ist unzureichend für sensible Operationen:
- Benutzer könnten Computer unverschlossen lassen
- Session-Hijacking-Risiko
- Versehentliche Admin-Aktionen
- Erfordert explizite Bestätigung für kritische Operationen

**Lösung:** Zweistufige Authentifizierung fügt einen zusätzlichen Verifizierungsschritt für Admin-Operationen hinzu.

### Verifizierungsmethoden

#### Methode 1: Manuelle Passwort-Verifizierung

**Endpoint:** `POST /api/auth/verify-admin`

**Prozess:**
```python
POST /api/auth/verify-admin
{
    "password": "admin_password"
}

# 1. Prüfen ob Benutzer eingeloggt
if not request.session.get("user"):
    return {"success": False, "error": "Not authenticated"}

# 2. Prüfen ob Benutzer admin-fähig
if not request.session.get("is_admin_capable"):
    return {"success": False, "error": "Not admin capable"}

# 3. Passwort verifizieren
username = request.session.get("user")
user = db.query(User).filter(User.username == username).first()

# auth.db Passwort zuerst versuchen
if user.hashed_password and verify_password(password, user.hashed_password):
    pass  # Gültig
else:
    # Mitglieder-Login-Passwort versuchen
    mitglied = members_db.query(Mitglied).filter(
        Mitglied.id == user.mitglied_id
    ).first()
    if not verify_password(password, mitglied.login_password_hash):
        return {"success": False, "error": "Invalid password"}

# 4. Admin verified setzen
request.session["admin_verified"] = True
request.session["admin_verified_at"] = now.isoformat()
return {"success": True}
```

**Anwendungsfälle:**
- Admin-only Benutzer (Auto-Verify nicht benötigt)
- RFID-Login (Passwort nicht während Login eingegeben)
- Sicherheitsbewusste Umgebungen

#### Methode 2: Auto-Verifizierung

**Endpoint:** `POST /api/auth/verify-admin-auto`

**Prozess:**
```python
POST /api/auth/verify-admin-auto

# 1. Prüfen ob Benutzer admin-fähig
if not request.session.get("is_admin_capable"):
    return {"success": False, "error": "Not admin capable"}

# 2. Prüfen ob login_method password war
if request.session.get("login_method") != "password":
    return {"success": False, "error": "requires_password"}

# 3. Auto-verify ohne Passwort
request.session["admin_verified"] = True
request.session["admin_verified_at"] = now.isoformat()
return {"success": True}
```

**Anwendungsfälle:**
- Admin-only Benutzer (Passwort gerade eingegeben)
- Gestraffelter Admin-Workflow
- Reduzierte Reibung für vertrauenswürdige Admins

**Einschränkungen:**
- Funktioniert nur wenn `login_method == "password"`
- Kann nicht mit RFID-Login verwendet werden
- Kann nicht verwendet werden wenn Session-Timeout auftrat

### Verifizierungs-Flowchart

```
┌─────────────────────────────────────────────────────────┐
│              Benutzer fordert Admin-Operation           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ is_admin_verified()?    │
        └──────────┬─────────────┘
                   │
          ┌────────┴────────┐
          │                 │
     ┌────▼────┐      ┌─────▼─────┐
     │  Ja     │      │   Nein     │
     └────┬────┘      └─────┬─────┘
          │                 │
          │                 ▼
          │      ┌──────────────────────┐
          │      │ Passwort-Verifizierung│
          │      │ Prompt anzeigen      │
          │      └──────────┬───────────┘
          │                 │
          │        ┌────────┴────────┐
          │        │                 │
          │   ┌────▼────┐      ┌─────▼─────┐
          │   │ Manuel   │      │ Auto      │
          │   │ verify   │      │ verify    │
          │   └────┬────┘      └─────┬─────┘
          │        │                 │
          │        ▼                 ▼
          │  ┌──────────────┐  ┌──────────────┐
          │  │ Passwort     │  │ login_method │
          │  │ verifizieren  │  │ prüfen      │
          │  └──────┬───────┘  └──────┬───────┘
          │         │                 │
          │    ┌────┴────┐         ┌────┴────┐
          │    │ Gültig?  │         │ Passwort?│
          │    └────┬────┘         └────┬────┘
          │         │ Ja               │ Ja
          │         ▼                   ▼
          │  ┌──────────────────────────────┐
          │  │ admin_verified = True setzen │
          │  │ admin_verified_at = now setzen│
          │  └──────────┬───────────────────┘
          │             │
          └─────────────┴───────────────────
                        │
                        ▼
              ┌──────────────────────┐
              │ Operation ausführen  │
              └──────────────────────┘
```

---

## Sicherheitsfunktionen

### 1. Passwort-Hashing

**Algorithmus:** bcrypt (via passlib)

**Konfiguration:**
```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**Hashing-Prozess:**
```python
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**Eigenschaften:**
- **Langsam aus Design** - Verhindert Brute-Force-Angriffe
- **Automatisch gesalzen** - Verhindert Rainbow-Table-Angriffe
- **Adaptiv** - Rechenaufwand kann über Zeit erhöht werden
- **Industriestandard** - Kampferprobter Algorithmus

### 2. Session-Sicherheit

**Cookie-Eigenschaften:**
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    max_age=None,  # Browser-Session
    httponly=True,  # Nicht via JavaScript zugänglich
    secure=True,   # Nur über HTTPS (Produktion)
    samesite="lax"  # CSRF-Schutz
)
```

**Sicherheitsvorteile:**
- **HTTP-Only:** Verhindert XSS-Cookie-Diebstahl
- **Secure:** Verhindert Man-in-the-Middle-Angriffe
- **SameSite:** Verhindert CSRF-Angriffe
- **Signed:** Verhindert Cookie-Tampering

### 3. Activity Tracking

**Implementierung:**
```python
# Bei jeder authentifizierten Anfrage aktualisiert
session["last_activity"] = datetime.now(timezone.utc).isoformat()

# Bei Auth-Dependency-Aufrufen geprüft
if (now - last_activity_dt).total_seconds() > TIMEOUT_SECONDS:
    session.clear()  # oder admin_verified = False
```

**Vorteile:**
- Automatisches Session-Ablaufen
- Reduziertes Fenster für Session-Hijacking
    - Inaktivitäts-Erkennung
    - Ressourcen-Bereinigung

### 4. Defense in Depth

**Layer 1: Netzwerksicherheit**
- HTTPS-Verschlüsselung (Produktion)
- Secure Cookie Flags
- SameSite Protection

**Layer 2: Authentifizierung**
- Starke Passwort-Hashing
- Session-basierte Auth
- Activity Tracking

**Layer 3: Autorisierung**
- Zweistufige Authentifizierung
- Rollenbasierte Zugriffskontrolle
- Admin-Verifizierung für sensible Ops

**Layer 4: Anwendungssicherheit**
- Input-Validierung
- SQL-Injection-Prävention (ORM)
- XSS-Schutz (Template-Escaping)

### 5. RFID-Sicherheit

**Card-Signature-Verifizierung:**
```python
# 3VL (Three-Level Verification) Signature-System
if card_signature and card_member_id:
    if verify_card_signature(
        verify_member_id, uid, verify_name, card_signature
    ):
        card_verified = 1  # Gültige Signatur
    else:
        card_verified = 0  # Ungültig - möglicher Klon
```

**Sicherheitsfunktionen:**
- HMAC-Signatur-Verifizierung
- Card-seitige Daten-Validierung
- Klon-Erkennung
- Legacy-Card-Support

---

## Timeout-Mechanismen

### Mitglieder-Session Timeout (3 Minuten)

**Zweck:** Mitglieder-Sessions vor Hijacking schützen

**Implementierung:**
```python
MEMBER_TIMEOUT_MINUTES = 3

def is_member_session_valid(request: Request) -> bool:
    session = request.session
    if not session.get("user"):
        return False

    last_activity = session.get("last_activity")
    if not last_activity:
        return False

    # Timestamp parsen
    last_activity_dt = datetime.fromisoformat(last_activity)
    if last_activity_dt.tzinfo is None:
        last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)

    # Timeout prüfen
    now = datetime.now(timezone.utc)
    if (now - last_activity_dt).total_seconds() > (MEMBER_TIMEOUT_MINUTES * 60):
        session.clear()  # Vollständiger Logout
        return False

    # Aktivität aktualisieren
    session["last_activity"] = now.isoformat()
    return True
```

**Verhalten:**
- Nach 3 Minuten Inaktivität → **Vollständiger Logout**
- Benutzer muss neu authentifizieren
- Alle Session-Daten gelöscht

**Begründung:**
- Mitglieder nutzen oft geteilte Computer im Makerspace
- Kurzes Timeout reduziert Risiko von unbefugtem Zugriff
- Schnelles Re-Login ist für Mitglieder-Operationen akzeptabel

### Admin-Verifizierungs Timeout (10 Minuten)

**Zweck:** Admin-Operationen schützen während vernünftigem Workflow

**Implementierung:**
```python
ADMIN_TIMEOUT_MINUTES = 10

def is_admin_verified(request: Request) -> bool:
    session = request.session
    if not session.get("admin_verified"):
        return False

    admin_verified_at = session.get("admin_verified_at")
    last_activity = session.get("last_activity")

    if not admin_verified_at or not last_activity:
        return False

    # Timestamp parsen
    last_activity_dt = datetime.fromisoformat(last_activity)
    if last_activity_dt.tzinfo is None:
        last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)

    # Timeout prüfen
    now = datetime.now(timezone.utc)
    if (now - last_activity_dt).total_seconds() > (ADMIN_TIMEOUT_MINUTES * 60):
        session["admin_verified"] = False
        session["admin_verified_at"] = None
        return False  # Downgrade, kein Logout

    # Aktivität aktualisieren
    session["last_activity"] = now.isoformat()
    return True
```

**Verhalten:**
- Nach 10 Minuten Inaktivität → **Admin-Verifizierung widerrufen**
- Benutzer bleibt eingeloggt (Mitglieder-Zugriff behalten)
- Muss Passwort neu verifizieren für Admin-Operationen

**Begründung:**
- Admin-Operationen sind seltener
- Längeres Timeout erlaubt vernünftigen Workflow
- Downgrade (kein Logout) reduziert Reibung
    - Re-Verifizierung fügt Sicherheit für sensible Ops hinzu

### Timeout-Vergleich

| Timeout | Dauer | Effekt | Anwendungsfall |
|---|---|---|---|
| Mitglieder-Session | 3 min | Vollständiger Logout | Mitgliederbereich, Basis-Operationen |
| Admin-Verifizierung | 10 min | Admin-Downgrade | Admin-Dashboard, sensible Ops |

### Heartbeat-Mechanismus

**Endpoint:** `POST /api/auth/heartbeat`

**Zweck:** Aktivitäts-Timestamp aktualisieren und Session-Gültigkeit prüfen

**Implementierung:**
```python
@router.post("/api/auth/heartbeat")
async def heartbeat(request: Request):
    """Aktivitäts-Timestamp aktualisieren und Session-Gültigkeit prüfen"""
    if not is_member_session_valid(request):
        return JSONResponse({"valid": False}, status_code=401)
    return {"valid": True}
```

**Verwendung:**
- Frontend ruft dies periodisch auf (z.B. alle 30 Sekunden)
- Hält Session während aktiver Nutzung am Leben
    - Bietet frühe Warnung vor Session-Ablauf
    - Ermöglicht eleganten Logout vor Timeout

---

## Datenbank-Schema

### auth.db Schema

#### User Tabelle
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- 'admin' oder 'member'
    mitglied_id INTEGER,     -- Soft Reference zu members.db
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_user_username ON user(username);
CREATE INDEX ix_user_mitglied_id ON user(mitglied_id);
```

**Beziehung zu members.db:**
- `mitglied_id` ist eine Soft Reference (kein Foreign Key Constraint)
- Verknüpft Auth-Benutzer mit Mitglieder-Datensatz
- Ermöglicht Hybrid-Benutzer (Admin + Mitglied)

### members.db Schema

#### Mitglied Tabelle (Relevante Felder)
```sql
CREATE TABLE mitglieder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    email VARCHAR,
    login_username VARCHAR UNIQUE,
    login_password_hash VARCHAR,
    nfc_uid VARCHAR UNIQUE,
    -- ... andere Felder
);

CREATE INDEX ix_mitglieder_login_username ON mitglieder(login_username);
CREATE INDEX ix_mitglieder_nfc_uid ON mitglieder(nfc_uid);
```

#### RFIDTag Tabelle
```sql
CREATE TABLE rfid_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid VARCHAR UNIQUE NOT NULL,
    member_id VARCHAR,
    owner_name VARCHAR NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_rfid_tags_uid ON rfid_tags(uid);
CREATE INDEX ix_rfid_tags_member_id ON rfid_tags(member_id);
```

**Admin-Tag-Erkennung:**
```python
admin_tag = members_db.query(RFIDTag).filter(
    RFIDTag.member_id == mitglied.member_id,
    RFIDTag.is_admin == True,
    RFIDTag.active == 1
).first()
```

---

## Code-Deep-Dive

### Auth-Dependency-Verwendung

#### Basis-Auth in Route Handler
```python
from backend.auth.dependencies import check_auth

@router.get("/api/buchhaltung/summary")
async def get_summary(
    request: Request,
    period: str = Query("month", pattern="^(week|month|year)$"),
    db: Session = Depends(get_db),
):
    # Authentifizierung prüfen
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Business-Logik hier
    ...
```

#### Admin-Verifizierung in Route Handler
```python
from backend.auth.dependencies import is_admin_verified

@router.get("/admin/users")
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    # Admin-Verifizierung prüfen
    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)
    
    # Business-Logik hier
    ...
```

#### Dependency-Injection Pattern
```python
# Für Verwendung mit FastAPI Depends()
def require_auth(request: Request):
    """Dependency: Authentifizierung erforderlich"""
    if not request.session.get("user"):
        raise HTTPException(status_code=401, detail="Not authenticated")

def require_admin(request: Request):
    """Dependency: Admin-Verifizierung erforderlich"""
    if not is_admin_verified(request):
        raise HTTPException(status_code=403, detail="Admin verification required")

# Verwendung in Route
@router.get("/api/sensitive")
async def sensitive_endpoint(
    request: Request = Depends(require_admin)
):
    # Admin-Verifizierung garantiert
    ...
```

### Session-Management Code

#### Login-Session-Erstellung
```python
@router.post("/api/auth/login")
async def unified_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # ... Authentifizierungslogik ...
    
    # Session erstellen
    request.session["user"] = user.username
    request.session["mitglied_id"] = user.mitglied_id
    request.session["is_admin_capable"] = user.role == "admin"
    request.session["login_method"] = "password"
    request.session["admin_verified"] = False
    request.session["admin_verified_at"] = None
    request.session["last_activity"] = datetime.now(timezone.utc).isoformat()
    
    # Redirect basierend auf Benutzertyp
    if user.role == "admin" and not user.mitglied_id:
        return RedirectResponse("/dashboard")
    else:
        return RedirectResponse("/member")
```

#### Logout
```python
@router.get("/logout")
async def logout(request: Request):
    """Session löschen"""
    request.session.clear()
    return RedirectResponse("/", status_code=302)
```

#### Admin-Logout (Downgrade)
```python
@router.post("/api/auth/logout-admin")
async def logout_admin(request: Request):
    """Admin-Verifizierung entfernen, zu Mitgliederbereich zurückkehren"""
    request.session["admin_verified"] = False
    request.session["admin_verified_at"] = None
    return RedirectResponse("/member", status_code=302)
```

### Passwort-Management

#### Passwort-Hashing
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Passwort für Speicherung hashen"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Passwort gegen Hash verifizieren"""
    return pwd_context.verify(plain_password, hashed_password)
```

#### Admin-Benutzer Seeding
```python
def seed_admin_user():
    """Standard-Admin-Benutzer erstellen wenn keine Benutzer existieren"""
    db = SessionLocal()
    try:
        existing = db.query(User).first()
        if existing:
            return  # Bereits geseeded
        
        # Standard-Admin aus Config erstellen
        hashed = get_password_hash(ADMIN_PASSWORD)
        admin = User(
            username=ADMIN_USERNAME,
            hashed_password=hashed,
            role="admin",
            mitglied_id=None,
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()
```

### RFID-Authentifizierung

#### RFID-Login Handler
```python
@router.post("/api/auth/login-rfid")
async def login_rfid(request: Request, uid: str = Form(...)):
    """Login via RFID-Tag-Scan"""
    from backend.members.db import get_db as get_members_db
    from backend.members.models import Mitglied, RFIDTag

    members_db = next(get_members_db())
    try:
        uid_upper = uid.upper()
        
        # Mitglied.nfc_uid prüfen (eingetragen via Mitglieder-UI)
        mitglied = members_db.query(Mitglied).filter(
            Mitglied.nfc_uid == uid_upper
        ).first()
        
        if not mitglied:
            # RFIDTag Tabelle prüfen (legacy)
            tag = members_db.query(RFIDTag).filter(
                RFIDTag.uid == uid_upper,
                RFIDTag.active == 1
            ).first()
            
            if tag:
                # Zu Mitglied über member_id auflösen
                mitglied = members_db.query(Mitglied).filter(
                    Mitglied.member_id == tag.member_id
                ).first()
        
        if mitglied:
            # Session erstellen
            request.session["user"] = mitglied.login_username or str(mitglied.id)
            request.session["mitglied_id"] = mitglied.id
            request.session["login_method"] = "rfid"
            
            # Admin-Tag prüfen
            admin_tag = members_db.query(RFIDTag).filter(
                RFIDTag.member_id == mitglied.member_id,
                RFIDTag.is_admin == True,
                RFIDTag.active == 1
            ).first()
            
            request.session["is_admin_capable"] = bool(admin_tag)
            request.session["admin_verified"] = False
            request.session["last_activity"] = datetime.now(timezone.utc).isoformat()
            
            return {"success": True, "redirect": "/member"}
        
        return {"success": False, "error": "Tag nicht gefunden"}
    finally:
        members_db.close()
```

---

## Sicherheits-Best-Practices

### 1. Passwort-Anforderungen

**Aktuelle Implementierung:**
- Keine expliziten Passwort-Komplexitätsanforderungen
- Verlässt sich auf bcrypts Rechenaufwand für Sicherheit

**Empfehlungen:**
```python
import re

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Prüft ob Passwort Mindestanforderungen erfüllt"""
    if len(password) < 8:
        return False, "Passwort muss mindestens 8 Zeichen haben"
    
    if not re.search(r"[A-Z]", password):
        return False, "Passwort muss Großbuchstaben enthalten"
    
    if not re.search(r"[a-z]", password):
        return False, "Passwort muss Kleinbuchstaben enthalten"
    
    if not re.search(r"\d", password):
        return False, "Passwort muss Ziffer enthalten"
    
    return True, "Gültig"
```

### 2. Session-Konfiguration

**Aktuelle Implementierung:**
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    max_age=None,
    httponly=True,
    secure=True,  # Nur Produktion
    samesite="lax"
)
```

**Empfehlungen:**
- Starkes, zufällig generiertes `SECRET_KEY` verwenden
- `SECRET_KEY` periodisch rotieren (erfordert Session-Invalidierung)
- `max_age` für absolutes Session-Ablaufen in Betracht ziehen
- `samesite="strict"` für höhere Sicherheit (kann einige Integrationen brechen)

### 3. Rate Limiting

**Aktuelle Implementierung:**
- Kein Rate Limiting auf Authentifizierungs-Endpunkten

**Empfehlungen:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@limiter.limit("5/minute")
@router.post("/api/auth/login")
async def unified_login(...):
    # Login-Logik
    ...
```

### 4. Audit-Logging

**Aktuelle Implementierung:**
- Kein Audit-Logging für Authentifizierungs-Ereignisse

**Empfehlungen:**
```python
import logging

auth_logger = logging.getLogger("auth")

@router.post("/api/auth/login")
async def unified_login(...):
    # ... Authentifizierungslogik ...
    
    if success:
        auth_logger.info(
            f"Login-Erfolg: user={username}, method=password, ip={request.client.host}"
        )
    else:
        auth_logger.warning(
            f"Login-Fehlschlag: user={username}, ip={request.client.host}"
        )
```

### 5. Failed-Login Lockout

**Aktuelle Implementierung:**
- Kein Account-Lockout nach fehlgeschlagenen Versuchen

**Empfehlungen:**
```python
from collections import defaultdict
import time

failed_attempts = defaultdict(list)

def check_login_attempts(username: str, ip: str) -> bool:
    """Prüft ob Benutzer/IP gesperrt ist"""
    key = f"{username}:{ip}"
    attempts = failed_attempts[key]
    
    # Versuche älter als 15 Minuten entfernen
    cutoff = time.time() - 900
    attempts = [t for t in attempts if t > cutoff]
    failed_attempts[key] = attempts
    
    # Nach 5 fehlgeschlagenen Versuchen sperren
    if len(attempts) >= 5:
        return False  # Gesperrt
    
    return True  # Erlaubt

def record_failed_attempt(username: str, ip: str):
    """Fehlgeschlagenen Login-Versuch aufzeichnen"""
    key = f"{username}:{ip}"
    failed_attempts[key].append(time.time())
```

---

## OAuth-Integration

### Übersicht

Das System unterstützt Google OAuth 2.0 als Alternative zur passwortbasierten Authentifizierung. OAuth ermöglicht es Benutzern, sich mit ihrem Google-Konto anzumelden, ohne Passwörter mit der Anwendung zu teilen.

### OAuth-Architektur

```
┌─────────────┐
│  Benutzer   │  "Mit Google anmelden"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Web UI     │  Redirect zu /auth/google
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Google     │  Benutzer genehmigt Zugriff
│  OAuth      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Web UI     │  Callback mit Code
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Backend    │  Code gegen Token tauschen
│  OAuth      │  User Info abrufen
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  auth.db    │  User abrufen oder erstellen
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Session    │  Session erstellen
└─────────────┘
```

### OAuth-User-Mapping

OAuth-User werden auf das existierende `auth.db` User-Modell gemappt:

| Feld | OAuth-Wert | Hinweise |
|---|---|---|
| `username` | Google-E-Mail | Wird als eindeutiger Identifikator verwendet |
| `hashed_password` | Leer | OAuth-User haben keine Passwörter |
| `role` | `member` (Standard) | Kann manuell auf `admin` gesetzt werden |
| `mitglied_id` | `None` (Standard) | Kann mit Mitglied-Datensatz verknüpft werden |

### OAuth vs Passwort-Login

| Feature | Passwort-Login | OAuth-Login |
|---|---|---|
| User-Erstellung | Manuell | Automatisch |
| Passwort-Speicherung | Gehasht in DB | Keiner (nur Tokens) |
| Session-Erstellung | Gleich | Gleich |
| Admin-Verifizierung | Passwort erforderlich | Auto-verifiziert (konfigurierbar) |
| Sicherheit | Passwort-basiert | Token-basiert |
| UX | Passworteingabe | Ein-Klick |

### OAuth-Sicherheitsüberlegungen

1. **HTTPS erforderlich:** OAuth 2.0 erfordert HTTPS für alle Kommunikationen
2. **State Parameter:** Validiert OAuth-Callbacks um CSRF-Angriffe zu verhindern
3. **Token-Speicherung:** Tokens werden nicht dauerhaft gespeichert, nur Session-Daten
4. **Scope-Begrenzung:** Fordert nur minimale Scopes (openid, email, profile)
5. **Auto-Verify-Kompromiss:** OAuth-Admins werden für UX auto-verifiziert (kann deaktiviert werden)

### Zusätzliche OAuth-Provider Hinzufügen

Um zusätzliche OAuth-Provider hinzuzufügen (z.B. GitHub, Facebook):

1. Provider-Konfiguration zu `backend/config.py` hinzufügen
2. Provider in `backend/auth/oauth.py` registrieren
3. Providerspezifische Routes hinzufügen
4. Landing-Page mit Provider-Buttons aktualisieren
5. Redirect-URIs in Provider-Developer-Konsole konfigurieren

Beispiel für GitHub:
```python
# backend/config.py
OAUTH_GITHUB_CLIENT_ID: str = _cfg.get("oauth_github_client_id", "")
OAUTH_GITHUB_CLIENT_SECRET: str = _cfg.get("oauth_github_client_secret", "")

# backend/auth/oauth.py
oauth.register(
    "github",
    client_id=OAUTH_GITHUB_CLIENT_ID,
    client_secret=OAUTH_GITHUB_CLIENT_SECRET,
    authorize_url="https://github.com/login/oauth/authorize",
    authorize_params={"scope": "user:email"},
    access_token_url="https://github.com/login/oauth/access_token",
)
```

### OAuth-Konfiguration

OAuth in `config/config.json` aktivieren:
```json
{
    "oauth_enabled": true,
    "oauth_google_client_id": "deine-client-id.apps.googleusercontent.com",
    "oauth_google_client_secret": "dein-client-secret",
    "oauth_google_redirect_uri": "https://deine-pi-ip:8443/auth/google/callback"
}
```

### OAuth-Setup

Siehe [OAuth Setup-Anleitung](/docs/28-oauth-setup.de.md) für detaillierte Setup-Anweisungen inklusive:
- Google Cloud Console Konfiguration
- Redirect URI Setup
- Testen und Fehlerbehebung
- Sicherheits-Best-Practices

---

## Systemerweiterung

### Neue Benutzerrolle Hinzufügen

**Schritt 1: User Modell Aktualisieren**
```python
# backend/auth/models.py
class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # 'admin', 'moderator', 'member'
    mitglied_id = Column(Integer, nullable=True)
```

**Schritt 2: Rollen-Prüfung Hinzufügen**
```python
# backend/auth/dependencies.py
def is_moderator(request: Request) -> bool:
    """Prüft ob Benutzer Moderator-Rolle hat"""
    session = request.session
    if not session.get("user"):
        return False
    
    username = session.get("user")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        return user and user.role == "moderator"
    finally:
        db.close()
```

**Schritt 3: In Routes Verwenden**
```python
@router.get("/api/moderator/endpoint")
async def moderator_endpoint(request: Request):
    if not is_moderator(request):
        raise HTTPException(status_code=403, detail="Moderator-Zugriff erforderlich")
    # Business-Logik
    ...
```

### OAuth-Integration Hinzufügen

**Schritt 1: Abhängigkeiten Installieren**
```bash
uv add authlib python-multipart
```

**Schritt 2: OAuth-Konfiguration Hinzufügen**
```python
# backend/config.py
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")
```

**Schritt 3: OAuth-Routes Hinzufügen**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id=OAUTH_CLIENT_ID,
    client_secret=OAUTH_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/login/google")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, OAUTH_REDIRECT_URI)

@router.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.parse_id_token(request, token)
    
    # Session aus OAuth-Benutzerinfo erstellen
    request.session["user"] = user_info["email"]
    request.session["login_method"] = "oauth"
    # ... Rest der Session-Einrichtung ...
    
    return RedirectResponse("/member")
```

### Two-Factor Authentication (2FA) Hinzufügen

**Schritt 1: Abhängigkeiten Installieren**
```bash
uv add pyotp
```

**Schritt 2: 2FA-Felder zu User Modell Hinzufügen**
```python
# backend/auth/models.py
class User(Base):
    # ... existierende Felder ...
    totp_secret = Column(String, nullable=True)  # TOTP-Secret
    totp_enabled = Column(Boolean, default=False)
```

**Schritt 3: 2FA-Setup Endpoint Hinzufügen**
```python
import pyotp

@router.post("/api/auth/2fa/setup")
async def setup_2fa(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("user")
    user = db.query(User).filter(User.username == username).first()
    
    # Secret generieren
    secret = pyotp.random_base32()
    user.totp_secret = secret
    db.commit()
    
    # QR-Code-URL zurückgeben
    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(
        name=username,
        issuer_name="MakerPi GroundControl"
    )
    
    return {"qr_url": qr_url, "secret": secret}
```

**Schritt 4: 2FA-Verifizierung Hinzufügen**
```python
@router.post("/api/auth/2fa/verify")
async def verify_2fa(request: Request, code: str, db: Session = Depends(get_db)):
    username = request.session.get("user")
    user = db.query(User).filter(User.username == username).first()
    
    if not user.totp_secret:
        return {"success": False, "error": "2FA nicht aktiviert"}
    
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code):
        return {"success": False, "error": "Ungültiger Code"}
    
    # 2FA aktivieren
    user.totp_enabled = True
    db.commit()
    
    return {"success": True}
```

**Schritt 5: In Login-Flow Integrieren**
```python
@router.post("/api/auth/login")
async def unified_login(...):
    # ... existierende Passwort-Verifizierung ...
    
    # Prüfen ob 2FA aktiviert
    if user.totp_enabled:
        # Erfordert 2FA-Code
        return {"require_2fa": True}
    
    # Normaler Login-Flow
    ...
```

### Session-Storage-Backend Hinzufügen

**Aktuell:** In-Memory Session-Speicherung (Standard Starlette)

**Option 1: Redis Session-Speicherung**
```python
from starlette_session.backends.redis import RedisSessionBackend

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    backend=RedisSessionBackend(
        redis_url="redis://localhost:6379",
        prefix="session:"
    )
)
```

**Option 2: Datenbank Session-Speicherung**
```python
from starlette_session.backends.redis import RedisSessionBackend

# Custom Datenbank-Backend
class DatabaseSessionBackend:
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    async def get_session(self, session_id: str):
        # Aus Datenbank abrufen
        ...
    
    async def set_session(self, session_id: str, data: dict):
        # In Datenbank speichern
        ...
    
    async def delete_session(self, session_id: str):
        # Aus Datenbank löschen
        ...
```

---

## Troubleshooting

### Häufige Probleme

#### 1. Session Wird Nicht Persistiert

**Symptome:** Benutzer wird sofort nach Login ausgeloggt

**Ursachen:**
- `SECRET_KEY` ändert sich zwischen Neustarts
- Cookie-Domain/-Path Mismatch
- Browser blockiert Cookies

**Lösungen:**
```python
# Konsistentes SECRET_KEY verwenden
SECRET_KEY = os.getenv("SECRET_KEY") or "development-key-change-in-production"

# Cookie-Konfiguration prüfen
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    domain=None,  # None für aktuelle Domain
    path="/",     # Root-Pfad
)
```

#### 2. Admin-Verifizierung Schlägt Fehl

**Symptome:** Admin-Benutzer können nicht auf Admin-Dashboard zugreifen

**Ursachen:**
- `is_admin_capable` nicht korrekt gesetzt
- Admin-Verifizierungs-Timeout abgelaufen
    - Passwort-Verifizierung schlägt fehl

**Debug:**
```python
# Session-Status prüfen
@router.get("/api/auth/debug-session")
async def debug_session(request: Request):
    return {
        "session": dict(request.session),
        "admin_verified": is_admin_verified(request),
        "admin_capable": request.session.get("is_admin_capable"),
    }
```

#### 3. RFID-Login Funktioniert Nicht

**Symptome:** RFID-Scan loggt Benutzer nicht ein

**Ursachen:**
- UID nicht in Datenbank
- Tag nicht aktiv
    - Mitglied hat kein login_username

**Debug:**
```python
# RFID-Tag-Status prüfen
@router.get("/api/auth/debug-rfid/{uid}")
async def debug_rfid(uid: str):
    from backend.members.db import get_db as get_members_db
    from backend.members.models import Mitglied, RFIDTag
    
    members_db = next(get_members_db())
    try:
        uid_upper = uid.upper()
        
        # Mitglied.nfc_uid prüfen
        mitglied = members_db.query(Mitglied).filter(
            Mitglied.nfc_uid == uid_upper
        ).first()
        
        if mitglied:
            return {
                "source": "Mitglied.nfc_uid",
                "found": True,
                "login_username": mitglied.login_username,
                "has_login": bool(mitglied.login_username)
            }
        
        # RFIDTag prüfen
        tag = members_db.query(RFIDTag).filter(
            RFIDTag.uid == uid_upper
        ).first()
        
        if tag:
            return {
                "source": "RFIDTag",
                "found": True,
                "active": bool(tag.active),
                "is_admin": bool(tag.is_admin)
            }
        
        return {"found": False}
    finally:
        members_db.close()
```

---

## Performance-Überlegungen

### Datenbank-Query-Optimierung

**Aktuell:**
```python
# Separate Datenbank-Queries für Auth und Mitglieder-Daten
user = db.query(User).filter(User.username == username).first()
mitglied = members_db.query(Mitglied).filter(
    Mitglied.login_username == username
).first()
```

**Optimierung:**
```python
# Single Query mit Join (wenn Datenbanken zusammengeführt)
user = db.query(User).join(Mitglied).filter(
    User.username == username
).first()
```

### Session-Speicher-Performance

**Aktuell:** In-Memory-Speicherung (schnell aber nicht skalierbar)

**Überlegungen:**
- Single Server: In-Memory ist in Ordnung
- Multiple Server: Redis oder Datenbank-Backend verwenden
- Session-Größe: Session-Daten minimal halten

### Passwort-Hashing-Performance

**Aktuell:** bcrypt (absichtlich langsam)

**Trade-offs:**
- **Sicherheit:** Langsames Hashing verhindert Brute-Force
- **Performance:** Fügt ~100-200ms pro Login hinzu
- **Akzeptabel:** Login ist seltene Operation

**Optimierung:**
```python
# Argon2id für bessere Security/Performance-Balance verwenden
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)
```

---

## Authentifizierung Testen

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_login_success():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    assert "session" in response.cookies

def test_login_failure():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrong"}
    )
    assert response.status_code == 302  # Redirect mit Fehler

def test_protected_endpoint_without_auth():
    response = client.get("/api/buchhaltung/summary")
    assert response.status_code == 401

def test_protected_endpoint_with_auth():
    # Zuerst einloggen
    client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    # Geschützten Endpoint aufrufen
    response = client.get("/api/buchhaltung/summary")
    assert response.status_code == 200
```

### Integration Tests

```python
def test_admin_verification_flow():
    client = TestClient(app)
    
    # 1. Als Admin einloggen
    client.post("/api/auth/login", data={
        "username": "admin",
        "password": "admin"
    })
    
    # 2. Admin-Endpoint versuchen (sollte ohne Verifizierung fehlschlagen)
    response = client.get("/admin/users")
    assert response.status_code == 302  # Redirect zum Verifizieren
    
    # 3. Admin verifizieren
    response = client.post("/api/auth/verify-admin", data={
        "password": "admin"
    })
    assert response.json()["success"] == True
    
    # 4. Admin-Endpoint aufrufen (sollte erfolgreich sein)
    response = client.get("/admin/users")
    assert response.status_code == 200
```

---

## Zusammenfassung

Das MakerPi GroundControl Authentifizierungssystem bietet:

✅ **Sichere session-basierte Authentifizierung** mit HTTP-only Cookies
✅ **Zweistufige Authentifizierung** für sensible Operationen
✅ **Mehrere Benutzertypen** (admin, mitglied, hybrid)
✅ **RFID-Tag-Unterstützung** für physischen Zugang
✅ **Automatisches Timeout** für Sicherheit
✅ **Activity Tracking** für Session-Management
✅ **Passwort-Hashing** mit bcrypt
✅ **Flexible Architektur** für Erweiterungen

Das System balanciert Sicherheit mit Benutzerfreundlichkeit, indem es angemessenen Schutz für verschiedene Operationsempfindlichkeitsstufen bietet, während gleichzeitig eine reibungslose Benutzererfahrung für legitime Benutzer aufrechterhält.
