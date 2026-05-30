# Konfigurationsreferenz

Alle Laufzeiteinstellungen befinden sich in einer einzigen Datei: `config/config.json`.
Kopiere `config/config.json.example` nach `config/config.json` und trage deine Werte ein.
Die Datei wird einmalig beim Start geladen — nach jeder Änderung muss der Dienst neu gestartet werden.

---

## Kern

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `secret_key` | `"fallback-secret-change-me"` | Zufälliger Geheimschlüssel für Session-Signing, HMAC-Kartensignaturen und abgeleitete Mifare-Schlüssel. **Vor dem ersten Einsatz ändern.** |
| `admin_username` | `"admin"` | Admin-Benutzername |
| `admin_password` | `"changeme"` | Admin-Passwort — sofort ändern |

**Starken `secret_key` generieren:**
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

> ⚠️ Eine Änderung des `secret_key` nach der Kartenenrollierung macht alle bestehenden Kartensignaturen und abgeleiteten Mifare-Sektorschlüssel ungültig. Alle Karten müssen neu eingeschrieben werden.

---

## MQTT

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `mqtt_broker` | `"localhost"` | Hostname oder IP des MQTT-Brokers |
| `mqtt_port` | `1883` | MQTT-Port |

Als Broker wird Mosquitto erwartet. Auf dem Raspberry Pi:
```bash
sudo apt install mosquitto mosquitto-clients -y
sudo systemctl enable mosquitto
```

---

## NFC-Lesegeräte

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `enrollment_reader_id` | `""` | MQTT-Geräte-ID des Lesers für die Kartenenrollierung |
| `payment_reader_id` | `""` | MQTT-Geräte-ID des Lesers an der Zahlungskasse |
| `card_writer_id` | `""` | MQTT-Geräte-ID des PicoW, der Karten physisch beschreibt |

Die Geräte-ID ist das erste Segment eines MQTT-Topics, das der PicoW veröffentlicht. Publiziert der PicoW z. B. auf `Terminal-Reader/scan`, lautet die Geräte-ID `Terminal-Reader`. Sie wird in der Firmware-Konfiguration des PicoW (`config.json` auf dem Gerät) festgelegt.

---

## NFC-Tag-Sicherheit

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `nfc_signature_mode` | `"permissive"` | `"permissive"`: Legacy-Karten ohne Signatur funktionieren weiterhin. `"strict"`: Nur HMAC-verifizierte Karten werden akzeptiert. |
| `mifare_sector_key` | `""` | Optionaler 12-Zeichen-Hex-Override für den Mifare-Classic-Sektorschlüssel. Leer lassen, um automatisch aus dem `secret_key` abzuleiten (empfohlen). |

**Rollout-Reihenfolge:**
1. Mit `"permissive"` deployen — bestehende, nicht eingeschriebene Karten funktionieren weiter
2. Karten über die Mitglieder-Oberfläche neu einschreiben (Karte an den Enrollment-Reader halten)
3. Scan-Protokoll beobachten — eingeschriebene Karten zeigen `card_verified = 1`
4. Sobald alle aktiven Karten eingeschrieben sind, auf `"strict"` wechseln und Dienst neu starten

**DB-Migration** — einmalig auf dem Pi vor dem ersten Deployment mit NFC-Sicherheit ausführen:
```bash
uv run python scripts/migrate_nfc_security.py
```

Siehe [NFC-Tag-Sicherheit](./16-nfc-tag-security.de.md) für das vollständige Bedrohungsmodell und das Kartendaten-Layout.

---

## EasyVerein

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `easyverein_api_key` | `""` | EasyVerein REST-API-Schlüssel |
| `easyverein_org_id` | `""` | Numerische ID deiner Organisation in EasyVerein |
| `easyverein_signup_url` | `""` | Öffentlicher Mitgliedschafts-Anmeldelink — wird per E-Mail an Gäste nach dem Erstellen eines Laufzettels gesendet |

**API-Schlüssel beschaffen:**
1. Als Admin bei [easyverein.com](https://easyverein.com) einloggen
2. **Einstellungen → API** aufrufen
3. Neuen API-Schlüssel erstellen und kopieren

**Org-ID finden:**
Die Org-ID ist der numerische Teil der EasyVerein-URL, z. B. `https://easyverein.com/organizations/26355/` → Org-ID ist `26355`.

**Anmelde-URL:**
In EasyVerein unter **Mitglieder → Mitglied werden** den öffentlichen Link kopieren. Leer lassen, um die Anmelde-E-Mail zu deaktivieren.

---

## Zahlungen — SumUp

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `sumup_api_key` | `""` | SumUp-API-Schlüssel (`sup_sk_…`) |
| `sumup_merchant_code` | `""` | Dein SumUp-Händlercode (z. B. `M1KJN6HM`) |
| `sumup_reader_id` | `""` | SumUp-Kartenlesegerät-ID (optional — leer lassen, wenn nur QR/Wero verwendet wird) |
| `sumup_affiliate_key` | `""` | SumUp-Affiliate-Schlüssel für Deeplink-QR-Codes (`sup_afk_…`) |
| `sumup_mock` | `true` | Auf `false` setzen im Produktivbetrieb für echte Zahlungsanfragen |

**SumUp-Schlüssel beschaffen:**
1. Bei [me.sumup.com](https://me.sumup.com) einloggen
2. **API-Schlüssel** → neuen Schlüssel mit mindestens `payments`-Scope erstellen
3. Händlercode unter **Konto → Unternehmensprofil**
4. Affiliate-Schlüssel unter **Integrationen → Affiliate**

---

## Zahlungen — Wero

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `wero_enabled` | `false` | Auf `true` setzen, um die Wero-QR-Zahlungsoption anzuzeigen |
| `wero_mock` | `true` | Auf `false` setzen im Produktivbetrieb |
| `wero_merchant_id` | `""` | Wero-Händler-ID |
| `wero_api_key` | `""` | Wero-API-Schlüssel |

Für das Händler-Onboarding und die Zugangsdaten Wero/La Banque Postale kontaktieren.

---

## E-Mail (SMTP)

E-Mail ist vollständig optional. Wenn `smtp_host` leer ist, wird der E-Mail-Versand stillschweigend übersprungen.

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `smtp_host` | `""` | SMTP-Server-Hostname, z. B. `smtp.gmail.com` |
| `smtp_port` | `587` | SMTP-Port — `587` für STARTTLS (die meisten Anbieter), `465` für SSL |
| `smtp_username` | `""` | SMTP-Benutzername (in der Regel die Absender-E-Mail-Adresse) |
| `smtp_password` | `""` | SMTP-Passwort oder App-Passwort |
| `smtp_from_email` | `""` | Die `From:`-Adresse für ausgehende E-Mails |
| `smtp_starttls` | `true` | STARTTLS auf Port 587 verwenden. Auf `false` setzen, wenn `smtp_tls: true` verwendet wird |
| `smtp_tls` | `false` | Direkte TLS-Verbindung auf Port 465. Bei Verwendung `smtp_starttls: false` setzen |

### Gmail OAuth2 (Empfohlen für Gmail)

Für Gmail-Konten wird OAuth2-Authentifizierung gegenüber der herkömmlichen Passwort-Authentifizierung empfohlen.

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `gmail_oauth_enabled` | `false` | OAuth2-Authentifizierung für Gmail aktivieren |
| `gmail_oauth_token_file` | `"config/gmail_oauth_token.json"` | Pfad zur OAuth-Token-Datei |
| `gmail_oauth_username` | `""` | Gmail-Benutzername (für Alias-Unterstützung wie `noreply@domain.com`) |

**Einrichtung:** Siehe [Gmail OAuth2 Setup Guide](./GMAIL_OAUTH_SETUP.md) für detaillierte Anweisungen.

**Welche E-Mails werden gesendet:**
- **Zahlungsquittung** — wird nach Bezahlung eines Laufzettels an die E-Mail-Adresse des Mitglieds/Gastes gesendet
- **EasyVerein-Anmeldeeinladung** — wird an Gäste gesendet, wenn sie das Gast-Laufzettel-Formular absenden (erfordert gesetzten `easyverein_signup_url`)
- **Willkommens-E-Mail** — wird an Gäste gesendet, wenn sie einen Laufzettel erstellen, mit direktem Link zu ihrem Laufzettel

**Gängige Anbietereinstellungen:**

| Anbieter | `smtp_host` | `smtp_port` | `smtp_starttls` | `smtp_tls` |
|---|---|---|---|---|
| Gmail | `smtp.gmail.com` | `587` | `true` | `false` |
| Gmail (SSL) | `smtp.gmail.com` | `465` | `false` | `true` |
| Outlook / Office 365 | `smtp.office365.com` | `587` | `true` | `false` |
| Strato | `smtp.strato.de` | `587` | `true` | `false` |
| IONOS / 1&1 | `smtp.ionos.de` | `587` | `true` | `false` |

**Gmail-Hinweis:** Das normale Google-Passwort kann nicht verwendet werden. Unter **Google-Konto → Sicherheit → Bestätigung in zwei Schritten → App-Passwörter** ein App-Passwort speziell für GroundControl generieren.

---

## Google Drive (PDF-Backup)

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `google_drive_enabled` | `false` | Auf `true` setzen, um generierte Laufzettel-PDFs in Google Drive hochzuladen |
| `google_drive_client_secrets_file` | `"config/gdrive_client_secrets.json"` | Pfad zur OAuth2-Client-Secrets-JSON aus der Google Cloud Console |
| `google_drive_token_file` | `"config/gdrive_token.json"` | Pfad, unter dem das OAuth2-Access-Token nach der ersten Autorisierung gespeichert wird |
| `google_drive_root_folder_id` | `""` | Google-Drive-Ordner-ID, in die PDFs hochgeladen werden |

**Einrichtung:**
1. Auf [console.cloud.google.com](https://console.cloud.google.com) gehen
2. Projekt erstellen → **Google Drive API** aktivieren
3. **APIs & Dienste → Anmeldedaten → Anmeldedaten erstellen → OAuth-Client-ID** (Typ: Desktop-App)
4. JSON herunterladen → als `config/gdrive_client_secrets.json` speichern
5. Einmaligen Autorisierungsflow auf dem Pi ausführen:
   ```bash
   uv run python scripts/gdrive_auth.py
   ```
6. Die Ordner-ID ist das letzte Segment einer Google-Drive-Ordner-URL:
   `https://drive.google.com/drive/folders/1aBcDeFgHiJkLmNoPqRs` → ID ist `1aBcDeFgHiJkLmNoPqRs`

---

## Backups — Litestream / Backblaze B2

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `litestream_enabled` | `false` | Auf `true` setzen, um kontinuierliche SQLite-Backups via Litestream zu aktivieren |
| `backblaze_endpoint` | `""` | Backblaze-B2-S3-kompatibler Endpunkt, z. B. `s3.eu-central-003.backblazeb2.com` |
| `backblaze_bucket` | `""` | Name des B2-Buckets, in den die Datenbanken repliziert werden |
| `backblaze_key_id` | `""` | Backblaze-Application-Key-ID |
| `backblaze_application_key` | `""` | Geheimschlüssel des Backblaze-Application-Keys |

**Backblaze-Zugangsdaten beschaffen:**
1. Bei [backblaze.com](https://www.backblaze.com) einloggen → **B2 Cloud Storage**
2. Bucket erstellen (privat, kein öffentlicher Zugriff)
3. **App Keys → Neuen Application Key hinzufügen**
   - Auf den erstellten Bucket beschränken
   - Berechtigungen: **Lesen und Schreiben**
4. `keyID` und `applicationKey` sofort kopieren — der Geheimschlüssel wird nur einmal angezeigt
5. Der Endpunkt steht in den Bucket-Details unter **Endpunkt**

---

## Plane (Bug-Tracker)

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `plane_url` | `""` | URL deiner Plane-Instanz, z. B. `http://192.168.3.228:3001` |
| `plane_api_token` | `""` | Persönliches Plane-API-Token |
| `plane_workspace_slug` | `""` | Slug des Workspace, in der Plane-URL sichtbar |
| `plane_project_id` | `""` | UUID des Projekts, in dem Bug-Reports erstellt werden |

**Plane-Zugangsdaten beschaffen:**
1. In die Plane-Instanz einloggen
2. **Profil → API-Tokens → Token hinzufügen**
3. Workspace-Slug: in allen Plane-URLs nach der Domain sichtbar, z. B. `https://plane.example.com/h3cke-groundcontrol/` → Slug ist `h3cke-groundcontrol`
4. Projekt-ID: Projekt öffnen → **Einstellungen** — die UUID steht in der Browser-URL

---

## Shopify

| Schlüssel | Standard | Beschreibung |
|---|---|---|
| `shopify_store` | `""` | Deine Shop-Domain, z. B. `your-store.myshopify.com` |
| `shopify_access_token` | `""` | Shopify-Admin-API-Access-Token (`shpat_…`) |

**Shopify-Zugangsdaten beschaffen:**
1. Im Shopify-Admin unter **Apps → Apps entwickeln → App erstellen**
2. Unter **Konfiguration → Admin-API-Zugriffsscopes** benötigte Scopes aktivieren (mindestens `read_products`, `read_inventory`)
3. **API-Zugangsdaten → App installieren** → **Admin-API-Access-Token** kopieren (wird nur einmal angezeigt)

---

## Vollständiges Beispiel

```json
{
    "secret_key": "dein-zufaelliger-64-zeichen-hex-schluessel",
    "admin_username": "admin",
    "admin_password": "DeinStarkesPasswort",

    "mqtt_broker": "localhost",
    "mqtt_port": 1883,

    "enrollment_reader_id": "Terminal-Reader",
    "payment_reader_id": "Terminal-Reader",
    "card_writer_id": "Terminal-Reader",
    "nfc_signature_mode": "permissive",
    "mifare_sector_key": "",

    "easyverein_api_key": "dein-easyverein-api-schluessel",
    "easyverein_org_id": "12345",
    "easyverein_signup_url": "https://easyverein.com/public/...",

    "sumup_api_key": "sup_sk_...",
    "sumup_merchant_code": "XXXXXXXX",
    "sumup_affiliate_key": "sup_afk_...",
    "sumup_mock": false,

    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_username": "du@gmail.com",
    "smtp_password": "dein-app-passwort",
    "smtp_from_email": "noreply@deinedomaene.de",
    "smtp_starttls": true,
    "smtp_tls": false,

    "google_drive_enabled": false,
    "google_drive_client_secrets_file": "config/gdrive_client_secrets.json",
    "google_drive_token_file": "config/gdrive_token.json",
    "google_drive_root_folder_id": "",

    "litestream_enabled": false,
    "backblaze_endpoint": "s3.eu-central-003.backblazeb2.com",
    "backblaze_bucket": "dein-bucket-name",
    "backblaze_key_id": "deine-key-id",
    "backblaze_application_key": "dein-app-key"
}
```
