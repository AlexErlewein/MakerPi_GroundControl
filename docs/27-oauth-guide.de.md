# OAuth (Open Authorization) - Umfassender Leitfaden

Dieses Dokument bietet einen umfassenden Überblick über OAuth 2.0, deckt Konzepte, Flows, Sicherheit und Best Practices für Lernzwecke ab.

---

## Inhaltsverzeichnis

1. [Was ist OAuth?](#was-ist-oauth)
2. [Geschichte und Motivation](#geschichte-und-motivation)
3. [OAuth 2.0 vs OAuth 1.0](#oauth-20-vs-oauth-10)
4. [Kernkonzepte](#kernkonzepte)
5. [OAuth 2.0 Architektur](#oauth-20-architektur)
6. [Grant-Typen](#grant-typen)
7. [Sicherheitsüberlegungen](#sicherheitsüberlegungen)
8. [Best Practices](#best-practices)
9. [Häufige Fehler](#häufige-fehler)
10. [Echtwelt-Beispiele](#echtwelt-beispiele)
11. [OAuth Implementieren](#oauth-implementieren)
12. [OAuth Testen](#oauth-testen)

---

## Was ist OAuth?

**OAuth (Open Authorization)** ist ein offener Standard für Zugriffsberechtigung. Er bietet einen sicheren und standardisierten Weg für Benutzer, Drittanwendungen begrenzten Zugriff auf ihre Ressourcen zu gewähren, ohne ihre Anmeldedaten zu teilen.

### Hauptmerkmale

- **Delegierungsbasiert:** Benutzer autorisieren Anwendungen, in ihrem Namen zu handeln
- **Token-basiert:** Verwendet Access-Tokens statt Anmeldedaten
- **Standardisiert:** RFC 6749 / RFC 6750 (OAuth 2.0)
- **Flexibel:** Unterstützt mehrere Autorisierungs-Flows
- **Sicher:** Mit Sicherheits-Best-Practices entworfen

### Was OAuth löst

**Problem: Passwort-Anti-Pattern**

Vor OAuth verwendeten Anwendungen dieses unsichere Muster:

```
┌─────────────┐
│  Benutzer   │  "Hier ist mein Passwort"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  App        │  Speichert Passwort
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Drittanbieter │  Verwendet Passwort für Ressourcenzugriff
└─────────────┘
```

**Risiken:**
- Passwort an mehreren Orten gespeichert
- Wenn App kompromittiert ist, erhält Angreifer Passwort
- Benutzer muss Passwort überall ändern
- Keine granulare Kontrolle über Berechtigungen
- Keine Möglichkeit, Zugriff zu widerrufen ohne Passwort zu ändern

**OAuth-Lösung:**

```
┌─────────────┐
│  Benutzer   │  "Ich autorisiere diese App für den Zugriff auf meine Daten"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  App        │  Empfängt Autorisierungscode
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  OAuth      │  Tauscht Code gegen Access-Token
│  Server     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  App        │  Verwendet Access-Token für Ressourcenzugriff
└─────────────┘
```

**Vorteile:**
- Benutzer teilt Passwort nie mit App
- Zugriff kann widerrufen werden ohne Passwort zu ändern
- Granulare Berechtigungen (Scopes)
- Zeitlich begrenzter Zugriff
    - Kann jederzeit widerrufen werden

---

## Geschichte und Motivation

### Vor OAuth (2007)

**Das Problem:**
- Jede Anwendung benötigte vollständige Anmeldedaten
- Benutzer mussten Passwörter mit vielen Apps teilen
- Sicherheitsrisiko war proportional zur Anzahl der Apps
- Kein Standardweg für begrenzte Zugriffsberechtigung

**Beispiel-Szenario:**
```
Benutzer möchte nutzen:
- Fotodruck-Service
- Kalender-Integration
    - Social-Media-Sharing

Vor OAuth:
- Muss jedem Service vollständiges E-Mail-Passwort geben
- Wenn ein Service kompromittiert ist, ist E-Mail kompromittiert
- Keine Möglichkeit, Zugriff zu widerrufen ohne Passwort zu ändern
```

### OAuth 1.0 (2007)

**Erster OAuth-Standard**
- Signatur-basierte Sicherheit eingeführt
- Komplexe kryptografische Anforderungen
- Schwierig korrekt zu implementieren
- Sicherheitslücken entdeckt

**Probleme:**
- Erforderte kryptografische Signaturen
- Komplex korrekt zu implementieren
- Session-Fixation-Angriffe
    - Token-Leakage-Schwachstellen

### OAuth 2.0 (2012)

**Vereinfachtes OAuth**
- Signaturen entfernt
- Bearer-Tokens hinzugefügt
- Implementierung vereinfacht
- Neue Grant-Typen hinzugefügt
    - Wurde Industriestandard

**Hauptverbesserungen:**
- Einfacher zu implementieren
- Besseres Sicherheitsprofil
- Flexiblere Grant-Typen
- Mobile-freundlich

---

## OAuth 2.0 vs OAuth 1.0

### Vergleichstabelle

| Feature | OAuth 1.0 | OAuth 2.0 |
|---|---|---|
| Tokens | Request-Tokens + Access-Tokens | Access-Tokens + Refresh-Tokens |
| Sicherheit | Kryptografische Signaturen | TLS (HTTPS) + Bearer-Tokens |
| Komplexität | Hoch (Signaturen, Callbacks) | Niedrig (einfaches HTTP) |
| Mobile-Unterstützung | Schwierig | Native Unterstützung |
| Widerruf | Token-Widerruf-Endpoint | Token-Widerruf-Endpoint |
| Standard | RFC 5849 | RFC 6749 |

### OAuth 1.0 Flow (Vereinfacht)

```
1. Request Token
   ┌─────────┐
   │  App     │ → Consumer Key + Secret
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  OAuth   │ → Request Token (signiert)
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  App     │ → Redirects Benutzer zu OAuth
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  Benutzer │ → Genehmigt Request
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  OAuth   │ → Access Token (signiert)
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  App     │ → Verwendet Access-Token
   └─────────┘
```

### OAuth 2.0 Flow (Vereinfacht)

```
1. Authorization Code
   ┌─────────┐
   │  App     │ → Client ID + Redirect URI
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  OAuth   │ → Redirects Benutzer zum Login
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  Benutzer │ → Genehmigt Request
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  OAuth   │ → Authorization Code
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  App     │ → Tauscht Code gegen Access-Token
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  App     │ → Verwendet Access-Token
   └─────────┘
```

**Hauptunterschied:** OAuth 2.0 entfernte kryptografische Signaturen und verlässt sich auf HTTPS für Sicherheit.

---

## Kernkonzepte

### 1. Rollen

OAuth definiert vier Rollen:

#### Resource Owner
- Die Entität, die die geschützten Ressourcen besitzt
- Typischerweise ein Endbenutzer
- Gewährt Zugriff auf ihre Ressourcen

Beispiel: Ein Benutzer, der seine Google-Kalenderdaten besitzt

#### Client
- Die Anwendung, die Zugriff auf Ressourcen anfordert
- Kann eine Web-App, Mobile-App oder Desktop-App sein
- Muss beim OAuth-Server registriert sein

Beispiel: Eine Kalender-Integrations-App

#### Authorization Server
- Der Server, der Access-Tokens ausstellt
- Validiert Resource Owner Consent
- Verwaltet Client-Registrierungen
- Kann derselbe wie der Resource Server sein

Beispiel: Googles OAuth 2.0 Server

#### Resource Server
- Der Server, der die geschützten Ressourcen hostet
- Validiert Access-Tokens
    - Bedient die angeforderten Ressourcen

Beispiel: Google Calendar API

### 2. Tokens

#### Access Token
- Kurzlebiger Token für Ressourcenzugriff
- Repräsentiert die Autorisierungsberechtigung
    - Wird im HTTP Authorization Header gesendet
- Hat zugehörige Scopes (Berechtigungen)

**Beispiel:**
```
Authorization: Bearer ya29.a0AfH6S2W...
```

#### Refresh Token
- Langlebiger Token für neue Access-Tokens
- Sicher vom Client gespeichert
    - Ermöglicht Zugriff ohne Benutzer-Re-Autorisierung
- Kann widerrufen werden

**Beispiel:**
```json
{
  "access_token": "ya29.a0AfH6S2W...",
  "refresh_token": "1//0fG...",
  "expires_in": 3600
}
```

#### ID Token (OpenID Connect)
- Repräsentiert Benutzeridentität
- Enthält Benutzerinformationen (Name, E-Mail, etc.)
- Vom Authorization Server signiert
    - Wird für Authentifizierung verwendet

**Beispiel:**
```json
{
  "iss": "https://accounts.google.com",
  "sub": "123456789",
  "name": "Max Mustermann",
  "email": "max@example.com"
}
```

### 3. Scopes

Scopes definieren das Zugriffsniveau:

**Beispiel-Scopes:**
```
- read:calendar - Kalenderereignisse lesen
- write:calendar - Kalenderereignisse erstellen/aktualisieren
- profile - Benutzerprofilinformationen zugreifen
- email - Benutzer-E-Mail-Adresse zugreifen
```

**Scope-Format:**
```
scope1 scope2 scope3
```

### 4. Authorization Code

- Temporärer Code, der vom Authorization Server ausgestellt wird
- Wird gegen Access-Token getauscht
    - Einmalig (läuft nach Gebrauch ab)
- Verhindert Token-Interception

**Beispiel:**
```
https://example.com/callback?code=4/A0AfH6S2W...
```

### 5. State Parameter

- Zufälliger String, der vom Client generiert wird
- Wird an Authorization Server gesendet und im Callback zurückgegeben
- Verhindert CSRF-Angriffe
    - Verifiziert, dass Callback legitim ist

**Beispiel:**
```
https://example.com/callback?code=...&state=xyz123
```

---

## OAuth 2.0 Architektur

### Systemarchitektur

```
┌─────────────────────────────────────────────────────────────┐
│                      Resource Owner (Benutzer)                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Browser / Mobile App                              │    │
│  │  - Benutzer sieht Autorisierungsbildschirm          │    │
│  │  - Genehmigt oder lehnt Request ab                   │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Authorization Server (OAuth)                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Client Registrierungs-Datenbank                      │    │
│  │  - Client ID, Client Secret                          │    │
│  │  - Redirect URIs                                      │    │
│  │  - Erlaubte Scopes                                    │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Authorization Endpoint                             │    │
│  │  - /authorize                                       │    │
│  │  - Zeigt Consent-Screen dem Benutzer                  │    │
│  │  - Stellt Authorization Code aus                     │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Token Endpoint                                     │    │
│  │  - /token                                            │    │
│  │  - Tauscht Code gegen Access-Token                  │    │
│  │  - Stellt Refresh-Token aus                          │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                         Client (App)                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Client Credentials                                 │    │
│  │  - Client ID (öffentlich)                             │    │
│  │  - Client Secret (privat)                            │    │
│  │  - Redirect URI                                        │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Token Storage                                        │    │
│  │  - Access-Token (Speicher, Session, Datenbank)       │    │
│  │  - Refresh-Token (sicherer Speicher)                 │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  API Client                                          │    │
│  │  - Macht API-Requests mit Access-Token               │    │
│  │  - Handhabt Token-Refresh                           │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Resource Server (API)                       │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Geschützte Ressourcen                               │    │
│  │  - Benutzerdaten, Kalender, Dateien, etc.            │    │
│  └──────────────────────────────────────────────────────┘    │
│  │  ┌─────────────────────────────────────────────────┐    │
│  │  │ Token Validation Endpoint               │    │
│  │  │ - Validiert Access-Token                │    │
│  │  │ - Prüft Scopes                            │    │
│  │  │ - Gibt Ressource zurück wenn gültig      │    │
│  │  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Kommunikations-Flow

```
┌─────────┐         ┌──────────────┐         ┌──────────────┐
│  Client │         │   OAuth      │         │  Resource     │
└────┬────┘         └──────┬───────┘         └──────┬───────┘
     │                     │                      │
     │ 1. Redirect         │                      │
     ├─────────────────────►                      │
     │                     │                      │
     │                     │ 2. Zeige Consent   │
     │                     ├─────────────────────►
     │                     │                      │
     │                     │ 3. Authorization │
     │                     │      Code          │
     │                     ├─────────────────────►
     │                     │                      │
     │ 4. Authorization     │                      │
     │    Code              │                      │
     │◄────────────────────┤                      │
     │                     │                      │
     │ 5. Exchange Code für   │                      │
     │    Access-Token       │                      │
     ├─────────────────────►                      │
     │                     │                      │
     │ 6. Access-Token       │                      │
     │◄────────────────────┤                      │
     │                     │                      │
     │ 7. Zugriff auf Ressource    │                      │
     │    mit Token        ├─────────────────────►
     │                     │                      │
     │ 8. Ressourcendaten    │                      │
     │◄────────────────────┤                      │
```

---

## Grant-Typen

OAuth 2.0 definiert mehrere Grant-Typen für verschiedene Szenarien:

### 1. Authorization Code Grant

**Anwendungsfall:** Web-Anwendungen mit serverseitigem Backend

**Am besten für:**
- Traditionelle Web-Apps
- Anwendungen, die Client-Secrets sicher speichern können
- Wenn Benutzer während Autorisierung anwesend sind

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. Redirect zu /authorize
     │    params: client_id, redirect_uri, scope, state
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 2. Zeige Consent-Screen
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  Benutzer    │
└──────┬───────┘
     │
     │ 3. Genehmigen
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 4. Authorization Code
     │    redirect_uri?code=...&state=...
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 5. POST /token
     │    params: code, client_id, client_secret, redirect_uri
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 6. Access-Token + Refresh-Token
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 7. Access-Token für Ressourcenzugriff verwenden
     ├──────────────────────────────────────────────►
```

**Code-Beispiel:**
```python
# Schritt 1: Redirect zu Autorisierung
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id="your-client-id",
    client_secret="your-client-secret",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@app.get("/login")
async def login(request: Request):
    return await oauth.google.authorize_redirect(request, "https://example.com/callback")

# Schritt 2: Callback handhaben
@app.get("/callback")
async def callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.parse_id_token(request, token)
    # Access-Token für API-Requests verwenden
```

### 2. Implicit Grant

**Anwendungsfall:** Browser-basierte Apps (SPAs) ohne Backend

**Am besten für:**
- Single-Page-Anwendungen
- JavaScript-Anwendungen
- Wenn Client-Secret nicht sicher gespeichert werden kann

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. Redirect zu /authorize
     │    params: client_id, redirect_uri, scope, response_type=token
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 2. Zeige Consent-Screen
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  Benutzer    │
└──────┬─────┘
     │
     │ 3. Genehmigen
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 4. Access-Token
     │    redirect_uri#access_token=...
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 5. Access-Token aus URL-Fragment extrahieren
     │    Token für Ressourcenzugriff verwenden
```

**Hinweis:** Implicit Grant ist zugunsten von Authorization Code mit PKCE für SPAs deprecated.

### 3. Resource Owner Password Credentials Grant

**Anwendungsfall:** Legacy-Anwendungen, vertrauenswürdige First-Party-Apps

**Am besten für:**
- Legacy-Anwendungen
- Hoch vertrauenswürdige First-Party-Anwendungen
- Wenn Benutzer-Anmeldedaten bereits bekannt sind

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. POST /token
     │    params: grant_type=password, username, password, scope
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 2. Anmeldedaten validieren
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬─────┘
     │
     │ 3. Access-Token
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 4. Access-Token für Ressourcenzugriff verwenden
```

**Sicherheits-Hinweis:** Dieser Grant-Typ sollte nur für hoch vertrauenswürdige Anwendungen verwendet werden. Niemals für Drittanbieter-Apps verwenden.

### 4. Client Credentials Grant

**Anwendungsfall:** Machine-to-Machine-Authentifizierung (keine Benutzerinteraktion)

**Am besten für:**
- Service-Accounts
    - Background-Worker
    - CLI-Tools
    - Daemons

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. POST /token
     │    params: grant_type=client_credentials, client_id, client_secret, scope
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 2. Client-Anmeldedaten validieren
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└────┬─────┘
     │
     │ 3. Access-Token
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 4. Access-Token für Ressourcenzugriff verwenden
```

**Code-Beispiel:**
```python
from requests_oauthlib import OAuth2Session

oauth = OAuth2Session("https://oauth.example.com/token",
                          client_id="client_id",
                          client_secret="client_secret")

token = oauth.fetch_token(token_url="https://api.example.com/oauth/token",
                        scope="read write")

# Token für API-Zugriff verwenden
response = oauth.get("https://api.example.com/resource")
```

### 5. Authorization Code mit PKCE

**Anwendungsfall:** Mobile und native Apps, SPAs

**Am besten für:**
- Mobile-Anwendungen
- Single-Page-Anwendungen
- Apps, die Client-Secrets nicht speichern können
- Apps auf nicht vertrauenswürdigen Geräten

**Zusätzliche Sicherheit:**
- Verwendet Proof Key for Code Exchange (PKCE)
    - Verhindert Authorization-Code-Interception-Angriffe
- Erfordert Code Verifier und Challenge

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. Code Verifier und Challenge generieren
     │    code_verifier = random_string()
     │    code_challenge = random_string()
     │    code_challenge_method = "S256"
     │
     │ 2. Redirect zu /authorize
     │    params: client_id, redirect_uri, scope, state,
     │             code_challenge, code_challenge_method
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬─────┘
     │
     │ 3. Zeige Consent-Screen
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  Benutzer    │
└──────┬─────┘
     │
     │ 4. Genehmigen
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└────┬─────┘
     │
     │ 5. Authorization Code
     │    redirect_uri?code=...&state=...
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 6. POST /token
     │    params: code, code_verifier, client_id, redirect_uri
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└────┬─────┘
     │
     │ 7. Code Verifier validieren
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└────┬─────┘
     │
     │ 8. Access-Token + Refresh-Token
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 9. Access-Token für Ressourcenzugriff verwenden
```

### Grant-Typ-Vergleich

| Grant-Typ | Benutzer-Anwesenheit | Client-Secret | Anwendungsfall | Sicherheit |
|---|---|---|---|---|
| Authorization Code | Ja | Ja | Web-Apps | Hoch |
| Implicit | Ja | Nein | SPAs (deprecated) | Mittel |
| Password | Ja | Ja | Legacy-Apps | Niedrig (Anmeldedaten geteilt) |
| Client Credentials | Nein | Ja | Service-Accounts | Hoch (wenn Secrets geschützt) |
| PKCE | Ja | Nein | Mobile/SPAs | Sehr Hoch |

---

## Sicherheitsüberlegungen

### 1. HTTPS/TLS

**Kritische Anforderung:** OAuth 2.0 erfordert HTTPS für alle Kommunikationen.

**Warum:**
- Verhindert Token-Interception
    - Verhindert Man-in-the-Middle-Angriffe
- Schützt sensible Daten in Transit

**Beispiel:**
```
❌ http://example.com/oauth/authorize
✅ https://example.com/oauth/authorize
```

### 2. State Parameter

**Zweck:** Verhindert CSRF (Cross-Site Request Forgery) Angriffe

**Wie es funktioniert:**
1. Client generiert zufälligen State-String
2. State wird an Authorization Server gesendet
3. Authorization Server gibt State im Callback zurück
4. Client verifiziert, dass State übereinstimmt

**Beispiel:**
```python
import secrets

# State generieren
state = secrets.token_urlsafe(16)

# Redirect mit State
redirect_uri = f"https://oauth.example.com/authorize?state={state}&..."

# State im Callback verifizieren
if request.args.get("state") != state:
    raise HTTPException(status_code=400, detail="Invalid state")
```

### 3. Token-Speicherung

**Access-Token-Speicherung:**
- **Web-Apps:** Serverseitige Session oder Datenbank
- **Mobile-Apps:** Sicherer Speicher (Keychain/Keystore)
- **SPAs:** Speicher (kurzlebig)

**Refresh-Token-Speicherung:**
- **Web-Apps:** Verschlüsselte Datenbank
- **Mobile-Apps:** Sicherer Speicher (Keychain/Keystore)
- **Niemals:** Lokaler Speicher (localStorage, Cookies)

**Beispiel:**
```python
# ✅ Gut: Serverseitige Session
request.session["access_token"] = token

# ❌ Schlecht: Lokaler Speicher (XSS anfällig)
localStorage.setItem("access_token", token)
```

### 4. Token-Ablauf

**Access-Token:** Kurzlebig (typischerweise 1 Stunde)
**Refresh-Token:** Langlebig (Tage bis Monate)

**Warum:**
- Begrenzt Exposition wenn Access-Token kompromittiert ist
    - Erzwingt regelmäßige Re-Autorisierung
    - Ermöglicht Widerruf

**Beispiel:**
```json
{
  "access_token": "ya29.a0AfH6S2W...",
  "expires_in": 3600,
  "refresh_token": "1//0fG...",
  "expires_in": 2592000
}
```

### 5. Scope-Begrenzung

**Prinzip der geringsten Privilegien:** Fordere nur die Scopes an, die du brauchst.

**Beispiel:**
```
❌ Schlecht: scope="read write delete admin"
✅ Gut: scope="read"
```

### 6. PKCE (Proof Key for Code Exchange)

**Zweck:** Verhindert Authorization-Code-Interception-Angriffe

**Wie es funktioniert:**
1. Client generiert Code Verifier
2. Client generiert Code Challenge
3. Authorization Server bindet Code an Challenge
4. Nur Client mit Verifier kann Code gegen Token tauschen

**Erforderlich für:**
- Mobile-Apps
- SPAs
- Native-Apps

---

## Best Practices

### 1. Authorization Code Grant verwenden

**Wann:** Web-Anwendungen mit serverseitigem Backend

**Warum:** Am sichersten, weit unterstützt

**Beispiel:**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```

### 2. PKCE für Mobile/SPAs verwenden

**Wann:** Mobile-Apps, SPAs, native-Apps

**Warum:** Verhindert Code-Interception-Angriffe

**Beispiel:**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# PKCE automatisch für Mobile-Apps aktiviert
```

### 3. State Parameter validieren

**Immer:** State im Callback validieren um CSRF zu verhindern

**Beispiel:**
```python
@app.get("/callback")
async def callback(request: Request):
    # State verifizieren
    state = request.args.get("state")
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state")
    
    # Callback verarbeiten
    token = await oauth.google.authorize_access_token(request)
    ...
```

### 4. Refresh-Tokens sicher speichern

**Web-Apps:** Verschlüsselte Datenbank
**Mobile-Apps:** Keychain/Keystore

**Beispiel:**
```python
# ✅ Gut: Verschlüsselte Datenbank
from cryptography.fernet import Fernet

f = Fernet(ENCRYPTION_KEY)
encrypted_token = f.encrypt(refresh_token)
db.save(encrypted_token)

# ❌ Schlecht: Klartext-Datenbank
db.save(refresh_token)
```

### 5. Token-Refresh implementieren

**Token-Ablauf elegant handhaben:**

```python
def get_access_token():
    if not access_token or access_token_expired():
        refresh_token = get_refresh_token()
        access_token = exchange_refresh_token(refresh_token)
    return access_token
```

### 6. Tokens beim Logout widerrufen

**Tokens löschen wenn Benutzer sich ausloggt:**

```python
@app.post("/logout")
async def logout():
    # Token bei Authorization Server widerrufen
    await oauth.revoke_token(access_token)
    
    # Lokale Tokens löschen
    request.session.clear()
```

### 7. Überall HTTPS verwenden

**Niemals OAuth über HTTP verwenden:**

```python
# ✅ Gut
OAUTH_SERVER = "https://accounts.google.com"

# ❌ Schlecht
OAUTH_SERVER = "http://accounts.google.com"
```

### 8. Tokens validieren

**Tokens vor Gebrauch validieren:**

```python
def validate_token(token):
    # Token bei Authorization Server introspectieren
    response = requests.post(
        "https://oauth.example.com/introspect",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()["active"]
```

### 9. Kurzlebige Access-Tokens verwenden

**Typischer Ablauf:** 1 Stunde oder weniger

**Beispiel:**
```python
# ✅ Gut: 1 Stunde Ablauf
expires_in=3600

# ❌ Schlecht: 30 Tage Ablauf
expires_in=2592000
```

### 10. Minimale Scopes anfordern

**Nur anfordern was du brauchst:**

```python
# ✅ Gut: Minimale Scopes
scope="read calendar"

# ❌ Schlecht: Übermäßig breite Scopes
scope="read write delete admin"
```

---

## Häufige Fehler

### 1. Implicit Grant für SPAs verwenden

**Problem:** Implicit Grant ist deprecated, weniger sicher

**Lösung:** Authorization Code mit PKCE verwenden

**Beispiel:**
```python
# ❌ Deprecated
response_type="token"

# ✅ Modern
response_type="code"
code_challenge=S256
code_verifier=...
```

### 2. Tokens in Local Storage speichern

**Problem:** XSS-Schwachstellen, Token-Diebstahl

**Lösung:** Tokens serverseitig oder in sicherem Speicher speichern

**Beispiel:**
```python
# ❌ Anfällig
localStorage.setItem("access_token", token)

# ✅ Sicher
request.session["access_token"] = token
```

### 3. State Parameter nicht validieren

**Problem:** CSRF-Angriffe

**Lösung:** State immer im Callback validieren

**Beispiel:**
```python
# ❌ Anfällig
@app.get("/callback")
async def callback(request: Request):
    code = request.args.get("code")
    # Callback ohne State-Validierung verarbeiten

# ✅ Sicher
@app.get("/callback")
async def callback(request: Request):
    state = request.args.get("state")
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state")
    code = request.args.get("code")
    # Callback verarbeiten
```

### 4. HTTP statt HTTPS verwenden

**Problem:** Token-Interception, Man-in-the-Middle-Angriffe

**Lösung:** Immer HTTPS verwenden

**Beispiel:**
```python
# ❌ Unsicher
OAUTH_SERVER = "http://accounts.google.com"

# ✅ Sicher
OAUTH_SERVER = "https://accounts.google.com"
```

### 5. Token-Refresh nicht implementieren

**Problem:** Schlechte UX, Benutzer müssen häufig neu autorisieren

**Lösung:** Automatischen Token-Refresh implementieren

**Beispiel:**
```python
def refresh_access_token_if_expired():
    if token_expired():
        new_token = refresh_token_endpoint()
        update_stored_token(new_token)
```

### 6. Client Secrets hardcoden

**Problem:** Secrets im Code exponiert, schwierig zu rotieren

**Lösung:** Umgebungsvariablen verwenden

**Beispiel:**
```python
# ❌ Unsicher
CLIENT_SECRET = "abc123xyz"

# ✅ Sicher
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
```

### 7. Tokens beim Logout nicht widerrufen

**Problem:** Tokens bleiben gültig bis Ablauf

**Lösung:** Tokens bei Authorization Server widerrufen

**Beispiel:**
```python
@app.post("/logout")
async def logout():
    # Bei Authorization Server widerrufen
    await oauth.revoke_token(access_token)
    # Lokale Tokens löschen
    request.session.clear()
```

### 8. Zu viele Scopes anfordern

**Problem:** Überprivilegierte Tokens, Sicherheitsrisiko

**Lösung:** Minimale Scopes anfordern

**Beispiel:**
```python
# ❌ Überprivilegiert
scope="read write delete admin"

# ✅ Minimal
scope="read"
```

### 9. Tokens nicht validieren

**Problem:** Ungültige Tokens können verwendet werden wenn nicht validiert

**Lösung:** Tokens bei Authorization Server validieren

**Beispiel:**
```python
def validate_token(token):
    response = requests.post(
        "https://oauth.example.com/introspect",
        headers={"Authorization": f"Bearer {token}"}
    )
    if not response.json()["active"]:
        raise Exception("Invalid token")
```

### 10. Password Grant für Drittanbieter-Apps verwenden

**Problem:** Anmeldedaten mit Drittanbieter geteilt

**Lösung:** Authorization Code Grant verwenden

**Beispiel:**
```python
# ❌ Unsicher für Drittanbieter
grant_type="password"

# ✅ Sicher für Drittanbieter
grant_type="authorization_code"
```

---

## Echtwelt-Beispiele

### Beispiel 1: Google OAuth 2.0

**Szenario:** Web-App möchte auf Benutzer's Google Kalender zugreifen

**Implementierung:**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id="your-client-id.apps.googleusercontent.com",
    client_secret="your-client-secret",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@app.get("/login/google")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri="https://example.com/auth/callback"
    )

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.parse_id_token(request, token)
    
    # Benutzer in Datenbank erstellen oder aktualisieren
    user = get_or_create_user(user_info)
    
    # Session erstellen
    request.session["user"] = user.email
    request.session["login_method"] = "oauth"
    
    return RedirectResponse("/dashboard")
```

### Beispiel 2: GitHub OAuth 2.0

**Szenario:** App möchte auf Benutzer's GitHub Repositories zugreifen

**Implementierung:**
```python
oauth.register(
    "github",
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    authorize_url="https://github.com/login/oauth/authorize",
    authorize_params={"scope": "user repo"},
    access_token_url="https://github.com/login/oauth/access_token",
)
```

### Beispiel 3: Service Account (Client Credentials)

**Szenario:** Background-Worker muss auf Google Cloud Storage zugreifen

**Implementierung:**
```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    "service-account.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# Credentials für API-Zugriff verwenden
storage_client = storage.Client(credentials=credentials)
```

### Beispiel 4: Mobile-App mit PKCE

**Szenario:** iOS-App muss auf Benutzerdaten zugreifen

**Implementierung:**
```swift
import OAuth2Client
import CryptoSwift

// PKCE Verifier und Challenge generieren
let verifier = Data.randomBytes(32).base64EncodedString()
let challenge = Data.randomBytes(32).base64EncodedString()

// Redirect zu Autorisierung
let authURL = oauth2Client.authorize(
    provider: "google",
    clientID: clientID,
    redirectURI: redirectURI,
    scope: ["openid", "email", "profile"],
    codeChallenge: challenge,
    codeChallengeMethod: "S256",
    codeVerifier: verifier
)
```

---

## OAuth Implementieren

### Schritt 1: Anwendung registrieren

1. Gehe zu OAuth-Provider's Entwickler-Konsole
2. Erstelle neue OAuth 2.0 Anwendung
3. Erhalte Client ID und Client Secret
4. Konfiguriere Redirect URIs
5. Konfiguriere Scopes

### Schritt 2: Grant-Typ wählen

- **Web-App:** Authorization Code
- **Mobile-App:** Authorization Code mit PKCE
- **Service-Account:** Client Credentials
- **Legacy-App:** Password (falls notwendig)

### Schritt 3: OAuth-Flow implementieren

**Für Web-App (Authorization Code):**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "provider",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://provider.example.com/.well-known/openid-configuration",
    client_kwargs={"scope": "scope1 scope2"},
)

@app.get("/login")
async def login(request: Request):
    return await oauth.provider.authorize_redirect(request, REDIRECT_URI)

@app.get("/callback")
async def callback(request: Request):
    token = await oauth.provider.authorize_access_token(request)
    # Session erstellen, zu App redirecten
```

**Für Mobile-App (PKCE):**
```python
# PKCE ist automatisch für Mobile-Apps
oauth.register(
    "provider",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    # PKCE ist automatisch
)
```

### Schritt 4: Token-Refresh handhaben

```python
def refresh_access_token():
    refresh_token = get_stored_refresh_token()
    new_token = oauth.provider.refresh_token(refresh_token)
    update_stored_tokens(new_token)
```

### Schritt 5: Access-Token verwenden

```python
def get_api_data():
    access_token = get_stored_access_token()
    response = requests.get(
        "https://api.example.com/resource",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()
```

---

## OAuth Testen

### Unit Tests

```python
def test_oauth_redirect():
    response = client.get("/login")
    assert response.status_code == 302
    assert "accounts.google.com" in response.headers["location"]

def test_oauth_callback():
    # OAuth Provider mocken
    with patch("authlib.integrations.fastapi_oauthclient") as mock_oauth:
        mock_oauth.google.authorize_access_token.return_value = {
            "access_token": "test_token"
        }
        
        response = client.get("/callback?code=test_code")
        assert response.status_code == 200
```

### Integration Tests

```python
def test_full_oauth_flow():
    # 1. Autorisierung starten
    response = client.get("/login")
    assert response.status_code == 302
    
    # 2. Benutzer-Genehmigung simulieren (in Test-Umgebung)
    # 3. Callback simulieren
    # 4. Verifizieren dass Token gespeichert ist
    # 5. Verifizieren dass API-Zugriff mit Token funktioniert
```

### Security Tests

```python
def test_state_parameter():
    # CSRF-Schutz testen
    response = client.get("/callback?code=test&state=invalid")
    assert response.status_code == 400

def test_https_required():
    # Testen dass HTTP erforderlich ist
    with pytest.raises(Exception):
        oauth.register(
            "provider",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            server_metadata_url="http://provider.example.com"  # HTTP!
        )

def test_token_storage():
    # Testen dass Tokens sicher gespeichert werden
    # Prüfen auf Klartext-Tokens in Datenbank
    # Prüfen auf Tokens in Logs
    # Prüfen auf Tokens in Frontend-Code
```

---

## Zusammenfassung

OAuth 2.0 ist ein mächtiger Standard für sichere Zugriffsberechtigung. Wichtige Erkenntnisse:

### ✅ Vorteile
- **Sicherheit:** Kein Passwort-Sharing, Token-basierter Zugriff
- **Flexibilität:** Mehrere Grant-Typen für verschiedene Szenarien
- **Kontrolle:** Granulare Scopes, widerrufbarer Zugriff
- **Standardisierung:** Branchenweite Unterstützung

### ⚠️ Wichtige Sicherheitsanforderungen
- **HTTPS:** Erforderlich für alle Kommunikationen
- **State Parameter:** Verhindert CSRF-Angriffe
- **PKCE:** Erforderlich für Mobile/SPAs
- **Sichere Speicherung:** Refresh-Tokens schützen
- **Token-Validierung:** Tokens bei Authorization Server validieren

### 🎯 Best Practices
- Authorization Code für Web-Apps verwenden
- PKCE für Mobile/SPAs verwenden
- Client Credentials für Service-Accounts verwenden
- State Parameter immer validieren
- Tokens sicher speichern
- Token-Refresh implementieren
- Minimale Scopes anfordern
- Tokens beim Logout widerrufen

### 🚀 Wann OAuth verwenden
- Drittanbieter-App-Integration
- Mobile-App-Authentifizierung
- Service-Account-Authentifizierung
- API-Zugriffsdelegierung
    - Social Login (Google, Facebook, etc.)

OAuth 2.0 ist der Industriestandard für sichere Autorisierung und sollte verwendet werden, wann immer eine Anwendung auf Benutzerressourcen im Namen des Benutzers zugreifen muss.
