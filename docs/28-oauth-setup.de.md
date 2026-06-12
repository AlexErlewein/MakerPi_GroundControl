# OAuth Setup-Anleitung

Diese Anleitung erklärt, wie man Google OAuth 2.0-Authentifizierung für MakerPi GroundControl einrichtet.

## Übersicht

OAuth ermöglicht es Benutzern, sich mit ihrem Google-Konto anzumelden, anstatt Benutzername/Passwort zu verwenden. Dies bietet:
- **Bessere UX:** Ein-Klick-Login
- **Sicherheit:** Kein Passwort-Sharing mit der Anwendung
- **Mobile-freundlich:** Funktioniert nahtlos auf mobilen Geräten

## Voraussetzungen

- HTTPS muss konfiguriert sein (siehe `scripts/setup-https.sh`)
- Google Cloud Console-Konto
- MakerPi GroundControl auf deinem Pi deployt

## Schritt 1: Google Cloud Console Setup

### 1.1 OAuth 2.0 Client ID erstellen

1. Gehe zur [Google Cloud Console](https://console.cloud.google.com/)
2. Erstelle ein neues Projekt oder wähle ein bestehendes
3. Navigiere zu **APIs & Services** → **Credentials**
4. Klicke auf **Create Credentials** → **OAuth 2.0 Client ID**
5. Konfiguriere den Consent-Screen, wenn du dazu aufgefordert wirst:
   - **User Type:** External
   - **App Name:** MakerPi GroundControl
   - **User Support Email:** Deine E-Mail
   - **Developer Contact:** Deine E-Mail
6. Füge autorisierte Redirect-URIs hinzu:
   ```
   https://<deine-pi-ip>:8443/auth/google/callback
   https://<deine-tailscale-domain>/auth/google/callback
   ```
7. Klicke auf **Create**
8. Kopiere die **Client ID** und den **Client Secret**

### 1.2 Google+ API aktivieren (falls nötig)

1. Navigiere zu **APIs & Services** → **Library**
2. Suche nach "Google+ API"
3. Aktiviere sie (erforderlich für den Zugriff auf Benutzerprofile)

## Schritt 2: MakerPi GroundControl konfigurieren

### 2.1 config.json aktualisieren

Bearbeite `config/config.json` auf deinem Pi:

```json
{
    "oauth_enabled": true,
    "oauth_google_client_id": "deine-client-id.apps.googleusercontent.com",
    "oauth_google_client_secret": "dein-client-secret",
    "oauth_google_redirect_uri": "https://192.168.178.47:8443/auth/google/callback"
}
```

**Wichtig:** Ersetze `192.168.178.47` durch die tatsächliche IP-Adresse deines Pi.

### 2.2 Redirect URI in Google Cloud Console aktualisieren

Stelle sicher, dass die Redirect-URI in der Google Cloud Console exakt übereinstimmt:
- `https://<deine-pi-ip>:8443/auth/google/callback`

Für Tailscale-Zugriff füge auch hinzu:
- `https://<deine-tailscale-domain>/auth/google/callback`

## Schritt 3: Deployen und Testen

### 3.1 Abhängigkeiten synchronisieren

```bash
cd /home/alex/MakerPi_GroundControl
uv sync
```

### 3.2 Services neu starten

```bash
sudo systemctl restart groundcontrol
sudo systemctl restart groundcontrol-docs
```

### 3.3 OAuth testen

1. Öffne deinen Browser unter `https://<deine-pi-ip>:8443`
2. Du solltest einen "🔑 Mit Google anmelden"-Button sehen
3. Klicke auf den Button
4. Du wirst zur Google-Anmeldeseite weitergeleitet
5. Melde dich mit deinem Google-Konto an
6. Erteile MakerPi GroundControl die Berechtigung
7. Du solltest zum Mitgliederbereich weitergeleitet werden

## Schritt 4: Benutzererstellung überprüfen

Nach dem ersten OAuth-Login überprüfe, ob der Benutzer in `auth.db` erstellt wurde:

```bash
sqlite_web -H 0.0.0.0 auth.db
```

Navigiere zur Tabelle `users` und überprüfe:
- `username` = Google-E-Mail-Adresse
- `role` = `member` (Standard)
- `hashed_password` = leer (OAuth-Benutzer haben keine Passwörter)

## Schritt 5: Admin-Zugriff konfigurieren (optional)

Wenn du möchtest, dass OAuth-Benutzer Admin-Zugriff haben:

### Option 1: Rolle manuell setzen

```bash
sqlite3 auth.db "UPDATE users SET role='admin' WHERE username='deine-email@gmail.com';"
```

### Option 2: Admin-Benutzer zuerst erstellen

1. Erstelle zuerst einen Admin-Benutzer über das Passwort-Login
2. Melde dich dann mit derselben E-Mail über OAuth an
3. Das System wird die Konten zusammenführen (OAuth + Passwort)

## Fehlerbehebung

### OAuth-Button wird nicht angezeigt

**Problem:** Der "Mit Google anmelden"-Button erscheint nicht auf der Landing-Page.

**Lösung:**
1. Überprüfe, ob `config/config.json` `oauth_enabled: true` hat
2. Überprüfe, ob Client ID und Secret gesetzt sind
3. Überprüfe die Browser-Konsole auf Fehler
4. Verifiziere, dass `/auth/oauth/status` `enabled: true` zurückgibt

### Redirect URI passt nicht

**Problem:** Google gibt einen "redirect_uri_mismatch"-Fehler zurück.

**Lösung:**
1. Überprüfe, ob die Redirect-URI in der Google Cloud Console exakt übereinstimmt
2. Inkludiere die Portnummer (z.B. `:8443`)
3. Verwende HTTPS, nicht HTTP
4. Überprüfe auf nachgestellte Schrägstriche

### OAuth nicht aktiviert Fehler

**Problem:** Browser zeigt "OAuth is not enabled"-Fehler.

**Lösung:**
1. Überprüfe, ob `config/config.json` `oauth_enabled: true` hat
2. Starte den groundcontrol-Service neu
3. Überprüfe die Logs: `sudo journalctl -u groundcontrol -f`

### Benutzer nicht erstellt

**Problem:** OAuth-Login erfolgreich, aber Benutzer wird nicht in der Datenbank erstellt.

**Lösung:**
1. Überprüfe die Datenbankberechtigungen
2. Überprüfe die Logs auf Datenbankfehler
3. Verifiziere, dass `auth.db` beschreibbar ist
4. Überprüfe `backend/auth/oauth.py` auf Fehler

### Session nicht erstellt

**Problem:** OAuth-Login erfolgreich, aber Session wird nicht erstellt.

**Lösung:**
1. Überprüfe, ob `SECRET_KEY` in config gesetzt ist
2. Überprüfe, ob Session-Middleware funktioniert
3. Überprüfe, ob der Browser Cookies akzeptiert
4. Verifiziere, dass HTTPS funktioniert (Sessions erfordern sichere Cookies)

## Sicherheitsüberlegungen

### Client Secret Sicherheit

- Committe `oauth_google_client_secret` niemals zu git
- Speichere in `config/config.json` (gitignored)
- Verwende Umgebungsvariablen für die Produktion
- Rotiere Secrets regelmäßig

### HTTPS-Anforderung

- OAuth 2.0 erfordert HTTPS
- Das System lehnt OAuth über HTTP ab
- Stelle sicher, dass `scripts/setup-https.sh` ausgeführt wurde
- Verifiziere, dass HSTS-Header gesetzt ist

### Scope-Begrenzung

Das System fordert minimale Scopes:
- `openid` - Benutzeridentifikation
- `email` - E-Mail-Adresse
- `profile` - Basisprofilinformationen

Dies sind das Minimum, das für die Authentifizierung erforderlich ist.

### Token-Speicherung

- OAuth-Tokens werden nicht dauerhaft gespeichert
- Nur Session-Daten werden serverseitig gespeichert
- Tokens sind kurzlebig (1 Stunde)
- Session-Timeout gilt (3 Minuten Inaktivität)

## Erweiterte Konfiguration

### Mehrere OAuth-Provider

Um zusätzliche OAuth-Provider hinzuzufügen (z.B. GitHub, Facebook):

1. Füge providerspezifische Config zu `config.py` hinzu
2. Registriere den Provider in `backend/auth/oauth.py`
3. Füge providerspezifische Routes hinzu
4. Aktualisiere die Landing-Page mit zusätzlichen Buttons

### Benutzerdefinierte Redirect URI

Wenn du eine benutzerdefinierte Domain verwendest:

```json
{
    "oauth_google_redirect_uri": "https://custom-domain.com/auth/google/callback"
}
```

Aktualisiere die Redirect-URI in der Google Cloud Console entsprechend.

### Auto-Verify für Admins

Standardmäßig werden OAuth-Benutzer mit `role='admin'` automatisch verifiziert (kein Passwort-Wiedereingabe erforderlich). Um dies zu deaktivieren:

Bearbeite `backend/auth/oauth.py`:

```python
request.session["admin_verified"] = False  # Immer Passwort erforderlich
```

## Migration von reinem Passwort-Login

Wenn du bestehende Passwort-Benutzer hast und OAuth aktivieren möchtest:

1. Aktiviere OAuth in config
2. Deploye das Update
3. Benutzer können entweder Login-Methode wählen
4. Wenn ein Benutzer sich mit derselben E-Mail über OAuth anmeldet wie sein Passwort-Konto, werden die Konten zusammengeführt
5. Passwort-Login bleibt funktional

## Testen

### Lokales Testen

Um OAuth lokal zu testen:

1. Verwende `http://localhost:8000` (nicht HTTPS)
2. Hinweis: OAuth erfordert HTTPS in der Produktion
3. Für lokales Testen benötigst du möglicherweise einen Proxy oder ngrok

### Produktionstest

1. Teste mit einem echten Google-Konto
2. Teste auf mobilen Geräten
3. Teste mit verschiedenen Browsern
4. Teste Fehler-Szenarien (Zugriff verweigert, Netzwerkfehler)

## Überwachung

### OAuth-Status prüfen

```bash
curl https://<deine-pi-ip>:8443/auth/oauth/status
```

Erwartete Antwort:
```json
{
    "enabled": true,
    "google_configured": true,
    "redirect_uri": "https://192.168.178.47:8443/auth/google/callback"
}
```

### OAuth-Logs anzeigen

```bash
sudo journalctl -u groundcontrol -f | grep -i oauth
```

## Zusammenfassung

Das OAuth-Setup umfasst:
1. Erstellen von OAuth 2.0 Client ID in Google Cloud Console
2. Konfigurieren von Redirect-URIs
3. Aktualisieren von `config/config.json`
4. Deployen und Testen
5. Überprüfen der Benutzererstellung

Das System ist so konzipiert, dass es additiv ist - das Passwort-Login bleibt neben OAuth funktional.

## Zusätzliche Ressourcen

- [OAuth 2.0 Dokumentation](/docs/27-oauth-guide.de.md)
- [Authentifizierungssystem-Dokumentation](/docs/26-authentication-system.de.md)
- [Google OAuth 2.0 Dokumentation](https://developers.google.com/identity/protocols/oauth2)
