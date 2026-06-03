# 19 · Mitglied-Registrierung

## Übersicht

Das Mitglied-Registrierungssystem ermöglicht es neuen Mitgliedern, sich über ein öffentliches Webformular unter `/register` anzumelden. Diese Funktion erstellt einen Mitgliedsantrag in easyVerein (falls konfiguriert), der vom Vorstand bestätigt werden muss, mit einem lokalen Fallback für Offline-Szenarien. Der Beitrag wird stets monatlich per SEPA-Lastschrift eingezogen.

## Funktionen

- **Öffentliches Registrierungsformular**: Zugänglich unter `/register` ohne Authentifizierung
- **easyVerein-Integration**: Erstellt Mitgliedsantrag (`isApplication: true`) in easyVerein — der Vorstand muss den Antrag bestätigen, bevor das Mitglied aktiv wird
- **Lokaler Fallback**: Erstellt lokale Mitglied-Datensätze auch wenn easyVerein nicht verfügbar ist
- **E-Mail-Validierung**: Verhindert doppelte Registrierungen mit derselben E-Mail
- **Datenschutzerklärung**: Erfordert Akzeptanz der Datenschutzrichtlinie vor der Übermittlung
- **Monatlicher Beitrag**: Fester monatlicher Zahlungsintervall (keine Auswahlmöglichkeit)

## Konfiguration

Fügen Sie diese Einstellungen zu `config/config.json` hinzu:

```json
{
  "easyverein_api_key": "YOUR_EASYVEREIN_API_KEY_HERE",
  "easyverein_org_id": "YOUR_ORG_ID_HERE",
  "easyverein_registration_mock": false,
  "easyverein_signup_redirect_url": "",
  "membership_groups": [
    {
      "label": "Regulär (30 €/Monat)",
      "ev_url": "",
      "amount": 30
    },
    {
      "label": "Ermäßigt (15 €/Monat)",
      "ev_url": "",
      "amount": 15
    }
  ]
}
```

### Konfigurationsschlüssel

| Schlüssel | Zweck |
|---|---|
| `easyverein_api_key` | API-Schlüssel für easyVerein-Integration (optional) |
| `easyverein_org_id` | Organisations-ID in easyVerein (optional) |
| `easyverein_registration_mock` | Auf `true` setzen, um easyVerein-Aufrufe zum Testen zu simulieren |
| `easyverein_signup_redirect_url` | Externe URL für Signup-Weiterleitung (optional) |
| `membership_groups` | Array von Mitgliedschaftsgruppen-Konfigurationen |

### Konfiguration von Mitgliedschaftsgruppen

Jede Mitgliedschaftsgruppe in `membership_groups` unterstützt:

| Feld | Typ | Beschreibung |
|---|---|---|
| `label` | string | Anzeigelabel für die Mitgliedschaftsoption |
| `ev_url` | string | easyVerein-URL für diesen Mitgliedschaftstyp (optional) |
| `amount` | number | Monatlicher Zahlungsbetrag in EUR |

## Registrierungsablauf

```mermaid
flowchart LR
    A["Benutzer besucht /register"] --> B["Füllt Registrierungsformular aus"]
    B --> C["Akzeptiert Datenschutzrichtlinie"]
    C --> D["Sendet Formular ab"]
    D --> E{"easyVerein konfiguriert?"}
    E -->|Ja| F["Kontakt in easyVerein erstellen"]
    F --> G["Mitglied in easyVerein erstellen"]
    G --> H["Mitgliedsnummer abrufen"]
    H --> I["Lokalen Mitglied-Datensatz erstellen (Status: inactive)"]
    E -->|Nein| J["Lokale Mitglieds-ID generieren"]
    J --> I
    I --> K["Bestätigung anzeigen"]
    K --> L["Warte auf Vorstands-Bestätigung in easyVerein"]
```

## API-Endpunkte

### `GET /register`

Gibt das öffentliche Registrierungsformular zurück.

**Antwort**: HTML-Seite mit Registrierungsformular

### `POST /api/register`

Verarbeitet eine neue Mitglied-Registrierungsanmeldung.

**Anfragekörper**:
```json
{
  "first_name": "Max",
  "family_name": "Mustermann",
  "email": "max@example.com",
  "date_of_birth": "1990-01-01",
  "mobile_phone": "+491234567890",
  "private_phone": "+491234567891",
  "street": "Musterstraße 1",
  "zip_code": "12345",
  "city": "Musterstadt",
  "country": "Germany",
  "iban": "DE89370400440532013000",
  "bic": "COBADEFFXXX",
  "bank_account_owner": "Max Mustermann",
  "method_of_payment": 1,
  "membership_group_url": "",
  "payment_amount": 30.0,
  "payment_interval_months": 1,
  "salutation": "Herr",
  "privacy_accepted": true
}
```

**Antwort** (Erfolg):
```json
{
  "success": true,
  "message": "Antrag erfolgreich eingereicht"
}
```

**Antwort** (mit easyVerein-Warnung):
```json
{
  "success": true,
  "message": "Antrag erfolgreich eingereicht",
  "warning": "Antrag lokal gespeichert; easyVerein-Übertragung fehlgeschlagen"
}
```

**Fehlerantworten**:
- `400` - Datenschutzrichtlinie nicht akzeptiert
- `422` - Fehlende Pflichtfelder (Name, E-Mail)
- `409` - E-Mail bereits registriert

## easyVerein-Integration

Wenn `easyverein_api_key` konfiguriert ist, führt das Registrierungssystem folgende Schritte aus:

1. Erstellt einen Kontakt-Datensatz in easyVerein mit persönlichen Details
2. Erstellt einen **Mitgliedsantrag** (`isApplication: true`) in easyVerein — der Antrag erscheint in easyVerein unter "offene Mitgliedschaftsanträge" und muss vom Vorstand bestätigt werden
3. Ruft die Mitgliedsnummer von easyVerein ab
4. Verwendet die Mitgliedsnummer als lokale `member_id`
5. Setzt den lokalen Status auf "inactive" — wird bei der nächsten Synchronisation auf "active" aktualisiert, sobald der Antrag in easyVerein bestätigt wurde

### Rate Limiting

Die easyVerein-Integration verwendet konservatives Rate Limiting, um API-Fehler zu vermeiden:
- Seitengröße: 10 Datensätze pro Anfrage
- Anfrageverzögerung: 5 Sekunden zwischen Anfragen
- Max. Wiederholungen: 3 mit exponentiellem Backoff (15s, 30s, 45s)

## Lokaler Fallback

Wenn easyVerein nicht konfiguriert ist oder der API-Aufruf fehlschlägt, führt das System folgende Schritte aus:

1. Generiert eine lokale Mitglieds-ID mit Zeitstempel: `REG-{timestamp}`
2. Erstellt einen lokalen `Mitglied`-Datensatz mit Status "inactive"
3. Speichert Zahlungsdetails im Notizen-Feld
4. Gibt eine Erfolgsantwort zurück (mit Warnung, wenn easyVerein fehlschlug)

## Struktur des Mitglied-Datensatzes

Erstellte Mitglied-Datensätze enthalten:

| Feld | Quelle |
|---|---|
| `member_id` | easyVerein-Mitgliedsnummer oder generierte lokale ID |
| `name` | Kombination aus first_name + family_name |
| `email` | Aus Registrierungsformular (kleingeschrieben) |
| `phone` | mobile_phone oder private_phone |
| `status` | Auf "inactive" gesetzt (erfordert Admin-Aktivierung) |
| `joined_date` | null (wird bei Aktivierung gesetzt) |
| `notes` | Registrierungsmethode und Zahlungsdetails |

## Datenschutz und Sicherheit

- **E-Mail-Validierung**: E-Mail-Adressen werden normalisiert (kleingeschrieben, getrimmt) vor der Speicherung
- **Duplikat-Verhinderung**: Das System überprüft auf vorhandene E-Mail-Adressen vor der Registrierung
- **Datenschutzrichtlinie**: Registrierung erfordert explizite Akzeptanz der Datenschutzrichtlinie
- **Datenspeicherung**: Alle Registrierungsdaten werden lokal in `members.db` gespeichert
- **API-Sicherheit**: Der easyVerein-API-Schlüssel wird in der Konfiguration gespeichert (nicht im Code)

## Admin-Workflow

Nach der Registrierung:

1. **easyVerein**: Den Mitgliedsantrag in easyVerein überprüfen und bestätigen (unter "offene Mitgliedschaftsanträge")
2. Bei der nächsten Synchronisation wird der lokale Status automatisch auf "active" gesetzt
3. RFID-Tag zuweisen, falls erforderlich
4. joined_date wird bei der Bestätigung automatisch gesetzt

---

## easyVerein-Sync-Verwaltung

### Übersicht

Die tägliche Synchronisation läuft automatisch um **03:00 Uhr UTC** via APScheduler. Admins können den Sync jederzeit manuell auslösen und den aktuellen Status über die folgenden Endpunkte überwachen.

### Sync-Endpunkte

#### `GET /api/mitglieder/sync-status`

Gibt den Status des letzten Sync-Laufs zurück. Erfordert eingeloggte Sitzung (kein Admin erforderlich).

**Beispielantwort** (nach erfolgreichem Sync):
```json
{
  "last_sync": "2026-06-03T03:00:42.123456+00:00",
  "success": true,
  "message": "Synced 2 new, 14 updated, 1 skipped, 0 errors",
  "created": 2,
  "updated": 14,
  "skipped": 1,
  "errors": 0
}
```

**Beispielantwort** (noch kein Sync gelaufen — nach Neustart):
```json
{
  "last_sync": null,
  "success": null,
  "message": "No sync performed yet",
  "created": 0,
  "updated": 0,
  "errors": 0
}
```

**Hinweis**: Der Sync-Status wird im Arbeitsspeicher gehalten und nach einem Neustart des Servers zurückgesetzt.

#### `POST /api/mitglieder/sync`

Löst sofort einen manuellen Sync aus. Erfordert **Admin-Verifizierung** (`session["admin_verified"]` aktiv).

**Antwort**: Identisches Format wie `sync-status` — liefert das Ergebnis des soeben abgeschlossenen Syncs.

**Fehlerantworten**:
- `403` - Admin-Verifizierung erforderlich

#### `GET /api/mitglieder/key-status`

Gibt den Ablaufstatus des aktuell konfigurierten easyVerein-API-Schlüssels zurück. Erfordert eingeloggte Sitzung.

**Beispielantwort**:
```json
{
  "expires_at": "2026-12-31",
  "days_left": 211,
  "renew_url": "https://easyverein.com/app/IHRE_ORG_ID/setting/api-key"
}
```

- `expires_at`: ISO-Datum (YYYY-MM-DD) aus `config.json`, oder `null` wenn nicht gesetzt
- `days_left`: Verbleibende Tage bis zum Ablauf; `null` wenn `expires_at` nicht gesetzt oder ungültig
- `renew_url`: Direktlink zur API-Schlüssel-Seite in easyVerein (erfordert `easyverein_org_id` in der Konfiguration)

#### `POST /api/mitglieder/update-api-key`

Aktualisiert den easyVerein-API-Schlüssel und das Ablaufdatum — sowohl in `config/config.json` als auch im laufenden Prozess. Erfordert **Admin-Verifizierung**.

**Anfragekörper**:
```json
{
  "api_key": "NEUER_API_SCHLUESSEL",
  "expires_at": "2027-06-30"
}
```

**Antwort**:
```json
{
  "ok": true,
  "expires_at": "2027-06-30"
}
```

**Fehlerantworten**:
- `400` - API-Schlüssel leer oder Datum im falschen Format (erwartet YYYY-MM-DD)
- `403` - Admin-Verifizierung erforderlich

---

## Was der Sync synchronisiert — und was nicht

### Felder, die immer aus easyVerein übernommen werden

Bei jedem Sync-Lauf werden folgende Felder aus easyVerein geschrieben (sofern der Datensatz nicht gesperrt ist):

| Feld | Quelle in easyVerein |
|---|---|
| `name` | `firstName` + `familyName` aus contactDetails |
| `email` | `privateEmail` / `email` aus contactDetails |
| `phone` | `mobilePhone` / `phone` aus contactDetails |
| `status` | Abgeleitet aus `_isApplication`, `resignationDate`, `_isBlocked` |
| `joined_date` | `joinDate` aus easyVerein (nur gesetzt, wenn vorhanden) |

### Felder, die der Sync **niemals** überschreibt

Folgende Felder werden vom Sync grundsätzlich nicht angefasst, auch wenn easyVerein andere Werte liefert:

| Feld | Grund |
|---|---|
| `nfc_uid` | Lokal vergeben; easyVerein kennt keine RFID-UIDs |
| `login_username` | Lokale Anmeldedaten; werden manuell gesetzt |
| `login_password_hash` | Lokale Anmeldedaten; werden manuell gesetzt |
| `notes` | Freies Notizfeld; wird lokal gepflegt |

### Das `sync_locked`-Feld

Sobald ein Admin einen Mitglied-Datensatz über `PUT /api/mitglieder/{id}` bearbeitet, setzt das System automatisch `sync_locked = true`. Datensätze mit `sync_locked = true` werden beim Sync **vollständig übersprungen** — es werden weder Felder aktualisiert noch der Datensatz gelöscht.

Um einen gesperrten Datensatz wieder für den Sync freizugeben, muss `sync_locked` explizit auf `false` gesetzt werden:

```json
PUT /api/mitglieder/{id}
{ "sync_locked": false }
```

Der Sync zählt übersprungene Datensätze im `skipped`-Feld der Sync-Status-Antwort.

---

## Statusübergänge

### inactive → active

Ein Mitglied wechselt von `inactive` auf `active`, wenn easyVerein den Mitgliedsantrag bestätigt. Das erkennt der Sync daran, dass `_isApplication` nicht mehr gesetzt ist und kein `resignationDate` vorliegt. Bei diesem Übergang setzt der Sync auch `joined_date`, sofern easyVerein ein `joinDate` meldet.

**Aus Adminsicht**: Nach dem nächsten Sync (03:00 Uhr oder manuell ausgelöst) erscheint das Mitglied in der Mitgliederliste mit Status "aktiv" und einem gesetzten Beitrittsdatum.

### active → inactive

Ein Mitglied wechselt zurück auf `inactive`, wenn easyVerein eines der folgenden Signale meldet:

| Signal in easyVerein | Bedeutung |
|---|---|
| `resignationDate` gesetzt | Mitglied hat gekündigt |
| `_isBlocked: true` | Mitglied wurde gesperrt |
| `_isApplication: true` | Antrag nicht bestätigt (erneut als Antrag markiert) |

**Aus Adminsicht**: Das Mitglied verschwindet nach dem nächsten Sync aus der aktiven Mitgliederliste. RFID-Tags bleiben erhalten und müssen bei Bedarf manuell deaktiviert werden.

### Statusanzeige im Admin-UI

Die Mitgliederseite (`/mitglieder`) zeigt den aktuellen Sync-Status als Banner oberhalb der Tabelle:
- Letzter Sync-Zeitpunkt und Ergebnis (neue, aktualisierte, übersprungene, fehlerhafte Datensätze)
- Verbleibende Tage bis zum API-Schlüssel-Ablauf mit Direktlink zur Erneuerung in easyVerein
- Schaltfläche "Jetzt synchronisieren" zum manuellen Auslösen (erfordert Admin-Verifizierung)

---

## Admin-Monitoring

### Prüfen ob ein Sync erfolgreich war

Rufen Sie `GET /api/mitglieder/sync-status` auf oder sehen Sie den Banner auf `/mitglieder`:

- `"success": true` + `"errors": 0` — alles in Ordnung
- `"success": true` + `"errors": N` — Sync lief durch, aber einzelne Datensätze konnten nicht verarbeitet werden (Details in den Server-Logs)
- `"success": false` — Sync ist komplett fehlgeschlagen; `message` enthält den Grund

### Was tun wenn der Sync fehlschlägt

**1. API-Schlüssel abgelaufen**

`GET /api/mitglieder/key-status` prüfen. Wenn `days_left <= 0`:
1. Neuen Schlüssel in easyVerein unter `Einstellungen → API-Schlüssel` generieren
2. `POST /api/mitglieder/update-api-key` mit neuem Schlüssel und Ablaufdatum aufrufen
3. Manuellen Sync via `POST /api/mitglieder/sync` auslösen

Das System sendet ab **7 Tagen vor Ablauf** automatisch eine Warn-E-Mail an die konfigurierte `smtp_from_email`-Adresse.

**2. Netzwerk-/Verbindungsfehler**

Der Sync wiederholt fehlgeschlagene Anfragen bis zu 3 Mal mit exponentiellem Backoff (15 s, 30 s, 45 s). Bleibt der Fehler bestehen:
- Internetkonnektivität des Servers prüfen
- easyVerein-Dienststatus prüfen (https://status.easyverein.com)
- Server-Logs auf genaue Fehlermeldung prüfen: `sudo journalctl -u groundcontrol -f`

**3. HTTP 429 (Rate Limit)**

Der Sync verwendet bereits konservatives Rate Limiting (5 s zwischen Anfragen, Seitengröße 10). Bei anhaltenden 429-Fehlern den nächsten automatischen Sync-Lauf (03:00 Uhr) abwarten oder die Seiten-Größe in `backend/members/easyverein.py` reduzieren.

**4. Einzelne Datensätze mit Fehler**

`"errors": N > 0` bedeutet, dass N Datensätze nicht verarbeitet werden konnten (z. B. fehlende Pflichtfelder in easyVerein). Details stehen in den Server-Logs mit Mitglieds-ID. Diese Mitglieder müssen ggf. manuell angelegt werden.

---

## Testen

Um die Registrierung ohne easyVerein zu testen:

```json
{
  "easyverein_registration_mock": true
}
```

Dies simuliert easyVerein-Aufrufe, ohne tatsächlich die API zu kontaktieren.

## Fehlerbehebung

### easyVerein-Registrierung schlägt fehl

Überprüfen Sie:
- API-Schlüssel ist gültig und nicht abgelaufen
- Organisations-ID ist korrekt
- Internetkonnektivität vom Server
- easyVerein-API-Status

### E-Mail bereits registriert

Das System verhindert doppelte E-Mail-Adressen. Wenn ein Benutzer sich mit einer neuen E-Mail registrieren muss:
1. Sollte der Admin die E-Mail des vorhandenen Datensatzes aktualisieren
2. Oder den doppelten Datensatz löschen, falls er irrtümlich erstellt wurde

### Kollision lokaler Mitglieds-ID

Das System verwendet Zeitstempel, um ID-Kollisionen zu vermeiden. Im unwahrscheinlichen Fall einer Kollision wird die Datenbank-Datensatz-ID angehängt, um Eindeutigkeit zu gewährleisten.

## Verwandte Dokumentation

- [Konfigurationsreferenz](./18-configuration-reference.de.md) - Vollständige Konfigurationsoptionen
- [Authentifizierung](./14-authentication.de.md) - Benutzerauthentifizierung und Zugriffskontrolle
- [Mitgliederbereich](./15-member-area.de.md) - Mitglieder-Self-Service-Funktionen
