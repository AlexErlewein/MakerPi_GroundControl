# 25 · API-Referenz

Dieses Dokument enthält eine detaillierte Dokumentation für alle MakerPi GroundControl API-Endpunkte. Für interaktives Testing siehe die automatisch generierte Swagger UI unter `/docs`.

---

## Authentifizierung

Die meisten API-Endpunkte erfordern eine Authentifizierung per Session-Cookie. Einige Endpunkte sind öffentlich zugänglich für spezifische Anwendungsfälle (z.B. Gastformulare, Spenden-Summen).

### Authentifizierungsmethoden

| Methode | Beschreibung |
|---|---|
| **Session-Cookie** | Standard-Web-Authentifizierung - Login über `/login` oder `/api/auth/login-rfid` |
| **RFID-Scan** | Automatisches Login per NFC-Tag-Scan bei `/api/auth/login-rfid` |
| **Öffentlich** | Einige Endpunkte (unten markiert) erfordern keine Authentifizierung |

### Authentifizierung erforderlich

Die meisten Endpunkte geben `401 Unauthorized` zurück, wenn keine gültige Session vorhanden ist. Überprüfen Sie den Authentifizierungsstatus durch Aufruf von `/api/auth/session` (Admin-/Auth-Session) oder `/api/member/me` (Mitglied-Selbstauskunft).

---

## System-Endpunkte

### `GET /api/status`

**Beschreibung:** Gibt Geräte-Zähler und MQTT-Nachrichten-Zähler (24h und gesamt) zurück.

**Authentifizierung:** Öffentlich

**Antwort:**
```json
{
  "devices_total": 5,
  "devices_online": 3,
  "messages_24h": 1234,
  "messages_total": 5678,
  "status": "ok"
}
```

**Anwendungsfälle:**
- Systemüberwachung
- Dashboard-Status-Indikatoren

---

### `GET /api/database/stats`

**Beschreibung:** Gibt Datei-Info der core-Datenbank sowie aggregierte Geräte- und Nachrichten-Statistiken zurück.

**Authentifizierung:** Öffentlich

**Antwort:**
```json
{
  "database": {
    "file_path": "/pfad/zu/core.db",
    "size_human": "156.0 KB"
  },
  "devices": {
    "total": 5,
    "online": 3,
    "offline": 2,
    "nfc_ok": 4,
    "nfc_error": 1,
    "nfc_unknown": 0
  },
  "messages": {
    "total": 1234,
    "topics": 12,
    "oldest": "2026-01-01T00:00:00",
    "newest": "2026-07-15T12:00:00"
  },
  "devices_oldest_seen": "2026-01-01T00:00:00",
  "devices_newest_seen": "2026-07-15T12:00:00"
}
```

> Per-Datenbank-Health-Status (ok/error pro DB-Datei) wird vom separaten Endpunkt `GET /api/dashboard/db-health` zurückgegeben.

**Anwendungsfälle:**
- Datenbank-Health-Monitoring
- Speicherplatz-Tracking

---

## Geräteverwaltung

### `GET /api/devices`

**Beschreibung:** Listet alle bekannten Geräte aus der MQTT-Erkennung auf.

**Authentifizierung:** Erforderlich

**Antwort:**
```json
[
  {
    "id": 1,
    "device_id": "picow_nfc_01",
    "name": "NFC Reader 1",
    "last_seen": "2024-06-15T10:30:00+00:00",
    "status": "online",
    "nfc_ok": true
  }
]
```

**Anwendungsfälle:**
- Geräteinventar
- Verbindungsüberwachung
- Status-Dashboard

---

### `GET /api/devices/{device_id}`

**Beschreibung:** Gibt detaillierte Informationen über ein spezifisches Gerät zurück einschließlich aktueller Nachrichten und Topic-Statistiken.

**Authentifizierung:** Erforderlich

**Parameter:**
- `device_id` (path): Geräte-Identifikator (z.B. "picow_nfc_01")

**Antwort:**
```json
{
  "device": {
    "id": 1,
    "device_id": "picow_nfc_01",
    "name": "NFC Reader 1",
    "last_seen": "2024-06-15T10:30:00+00:00",
    "status": "online"
  },
  "topic_counts": [
    {"topic": "picow_nfc_01/scan", "count": 123},
    {"topic": "picow_nfc_01/status", "count": 456}
  ],
  "recent_messages": [...]
}
```

**Anwendungsfälle:**
- Geräte-Fehlersuche
- Nachrichtenanalyse
- Aktivitätsüberwachung

---

### `POST /api/devices/{device_id}/activate`

**Beschreibung:** Sendet einen Aktivierungsbefehl an ein Gerät, der angibt, ob ein Mitglied berechtigt ist, es zu verwenden.

**Authentifizierung:** Admin-Verifizierung erforderlich

**Parameter:**
- `device_id` (path): Geräte-Identifikator

**Request Body:**
```json
{
  "member_id": 123,
  "member_name": "Max Mustermann",
  "allowed": true
}
```

**Antwort:**
```json
{
  "success": true
}
```

**Anwendungsfälle:**
- Gerätezugriffskontrolle
- Mitglieder-Berechtigungs-Durchsetzung
- Echtzeit-Zugriffs-Updates

---

## Mitgliederverwaltung

### `GET /api/mitglieder`

**Beschreibung:** Listet alle Mitglieder mit optionaler Filterung auf.

**Authentifizierung:** Erforderlich

**Query-Parameter:**
- `search` (optional): Suche nach Name, Mitglieds-ID oder E-Mail

**Antwort:**
```json
[
  {
    "id": 1,
    "member_id": "12345",
    "name": "Max Mustermann",
    "email": "max@example.com",
    "phone": "+49123456789",
    "status": "active",
    "nfc_uid": "9CF22507",
    "login_username": "maxmustermann",
    "has_login": true,
    "sync_locked": false
  }
]
```

**Anwendungsfälle:**
- Mitgliederverzeichnis
- Suche und Lookup
    - Statusüberwachung

---

### `POST /api/mitglieder`

**Beschreibung:** Erstellt manuell ein neues Mitglied.

**Authentifizierung:** Erforderlich

**Request Body:**
```json
{
  "member_id": "12345",
  "name": "Max Mustermann",
  "email": "max@example.com",
  "phone": "+49123456789",
  "status": "active"
}
```

**Antwort:** Gibt das erstellte Mitglied-Objekt zurück.

**Anwendungsfälle:**
- Manuelle Mitglieder-Registrierung
- Testing und Entwicklung
- Notfall-Mitgliedererstellung

---

### `GET /api/mitglieder/{id}`

**Beschreibung:** Gibt detaillierte Informationen über ein spezifisches Mitglied zurück.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Mitglieder-Datenbank-ID

**Antwort:** Vollständiges Mitglied-Objekt inklusive aller Felder.

**Anwendungsfälle:**
- Mitgliederprofil-Anzeige
- Detaillierte Mitgliederinformationen
    - Berechtigungsprüfung

---

### `PUT /api/mitglieder/{id}`

**Beschreibung:** Aktualisiert Mitgliederinformationen. Alle Felder sind optional.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Mitglieder-Datenbank-ID

**Request Body:**
```json
{
  "name": "Max Mustermann Aktualisiert",
  "email": "max.neu@example.com",
  "phone": "+49123456789",
  "notes": "Aktualisierte Notizen",
  "sync_locked": true
}
```

**Antwort:** Gibt das aktualisierte Mitglied-Objekt zurück.

**Anwendungsfälle:**
- Mitgliederinformations-Updates
    - Statusänderungen
    - Sync-Lock-Management

---

### `DELETE /api/mitglieder/{id}`

**Beschreibung:** Löscht ein Mitglied aus der Datenbank.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Mitglieder-Datenbank-ID

**Antwort:**
```json
{
  "success": true
}
```

**Anwendungsfälle:**
- Mitgliederentfernung
    - Datenbereinigung
    - DSGVO-Konformität

---

## Geräteberechtigungen

### `GET /api/mitglieder/{id}/permissions`

**Beschreibung:** Listet alle Geräteberechtigungen für ein spezifisches Mitglied auf.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Mitglieder-Datenbank-ID

**Antwort:**
```json
[
  {
    "id": 1,
    "device_id": "laser_cutter_01",
    "granted_at": "2024-06-15T10:30:00+00:00"
  },
  {
    "id": 2,
    "device_id": "*",
    "granted_at": "2024-06-15T10:30:00+00:00"
  }
]
```

**Anwendungsfälle:**
- Berechtigungs-Audit
    - Zugriffskontrolle-Verifizierung
    - Mitgliederfähigkeitsprüfung

---

### `POST /api/mitglieder/{id}/permissions`

**Beschreibung:** Gewährt einem Mitglied die Berechtigung, ein spezifisches Gerät zu verwenden.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Mitglieder-Datenbank-ID

**Request Body:**
```json
{
  "device_id": "laser_cutter_01"
}
```

**Spezielle Werte:**
- `"*"` - Gewährt Zugriff auf alle Geräte

**Antwort:** Gibt das erstellte Berechtigungsobjekt zurück.

**Anwendungsfälle:**
- Gerätezugriffsgewährung
    - Schulungsabschluss-Zertifizierung
    - Sicherheitsschulungs-Verifizierung

---

### `DELETE /api/mitglieder/{id}/permissions/{permission_id}`

**Beschreibung:** Entfernt eine Geräteberechtigung von einem Mitglied.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Mitglieder-Datenbank-ID
- `permission_id` (path): Berechtigungs-Datenbank-ID

**Antwort:**
```json
{
  "success": true
}
```

**Anwendungsfälle:**
- Gerätezugriffs-Entzug
    - Sicherheitsschulungs-Ablauf
    - Mitgliedschaftsbeendigung

---

## NFC-Tag-Verwaltung

### `GET /api/tags`

**Beschreibung:** Listet alle registrierten RFID-Tags auf, einschließlich der über Mitgliederprofile eingeschriebenen.

**Authentifizierung:** Erforderlich

**Antwort:**
```json
[
  {
    "id": 1,
    "uid": "9CF22507",
    "owner_name": "Max Mustermann",
    "member_id": "12345",
    "owner_email": "max@example.com",
    "active": true,
    "is_admin": false,
    "created_at": "2024-06-15T10:30:00+00:00",
    "source": "rfid_tag"
  }
]
```

**Anwendungsfälle:**
- Tag-Inventar
    - Besitzer-Lookup
    - Aktive-Tag-Überwachung

---

### `POST /api/tags`

**Beschreibung:** Registriert einen neuen RFID-Tag.

**Authentifizierung:** Erforderlich

**Request Body:**
```json
{
  "uid": "9CF22507",
  "owner_name": "Max Mustermann",
  "member_id": "12345",
  "owner_email": "max@example.com",
  "notes": "Primärer Tag",
  "active": true
}
```

**Antwort:** Gibt das erstellte Tag-Objekt zurück.

**Anwendungsfälle:**
- Neue Tag-Registrierung
    - Gast-Tag-Management
    - Temporäre Tag-Zuweisung

---

### `PUT /api/tags/{uid}`

**Beschreibung:** Aktualisiert einen existierenden RFID-Tag.

**Authentifizierung:** Erforderlich

**Parameter:**
- `uid` (path): Tag-UID (Großbuchstaben)

**Request Body:**
```json
{
  "owner_name": "Max Mustermann Aktualisiert",
  "active": false
}
```

**Antwort:** Gibt das aktualisierte Tag-Objekt zurück.

**Anwendungsfälle:**
- Tag-Besitzer-Änderungen
    - Status-Updates
    - Informationskorrekturen

---

### `DELETE /api/tags/{uid}`

**Beschreibung:** Löscht einen RFID-Tag aus dem System.

**Authentifizierung:** Erforderlich

**Parameter:**
- `uid` (path): Tag-UID (Großbuchstaben)

**Antwort:**
```json
{
  "success": true
}
```

**Anwendungsfälle:**
- Tag-Entfernung
    - Verlorene-Tag-Deaktivierung
    - Systembereinigung

---

## NFC-Scans

### `GET /api/scans`

**Beschreibung:** Gibt aktuelle NFC-Scan-Ereignisse mit Validierungsstatus zurück.

**Authentifizierung:** Erforderlich

**Query-Parameter:**
- `limit` (optional): Maximale Anzahl an Ergebnissen (Standard: 100)

**Antwort:**
```json
[
  {
    "id": 1,
    "uid": "9CF22507",
    "device_id": "picow_nfc_01",
    "validated": true,
    "owner_name": "Max Mustermann",
    "card_verified": 1,
    "atqa": "0400",
    "sak": "08",
    "timestamp": "2024-06-15T10:30:00+00:00"
  }
]
```

**Anwendungsfälle:**
- Zugriffsprotokoll-Überprüfung
    - Sicherheitsüberwachung
    - Nutzungsstatistiken

---

### `GET /api/scans/stream`

**Beschreibung:** Server-Sent Events (SSE) Stream für Live-NFC-Scan-Ereignisse.

**Authentifizierung:** Optional (öffentlich für Geräte-Pairing)

**Query-Parameter:**
- `token` (optional): Geräte-Pairing-Token für gefilterten Stream

**Antwort:** SSE-Stream mit JSON-Ereignissen:
```json
{
  "uid": "9CF22507",
  "device_id": "picow_nfc_01"
}
```

**Anwendungsfälle:**
- Echtzeit-Scan-Überwachung
    - Geräte-Pairing
    - Live-Dashboard-Updates

---

## Buchhaltung

### `GET /api/buchhaltung/summary`

**Beschreibung:** Gibt umfassende Buchhaltungsdaten für einen Zeitraum zurück einschließlich Verkäufen, Spenden und Steuer-Aufschlüsselung.

**Authentifizierung:** Erforderlich

**Query-Parameter:**
- `period` (optional): `week`, `month` (Standard), `year`
- `reference_date` (optional): ISO-8601-Datumsstring

**Antwort:**
```json
{
  "period": "month",
  "cutoff": "2024-06-01T00:00:00+00:00",
  "end": "2024-07-01T00:00:00+00:00",
  "material_total": 142.50,
  "spende_total": 25.00,
  "total": 167.50,
  "tax_totals": {
    "19": 120.00,
    "7": 15.00,
    "0": 7.50,
    "spende_katalog": 0.00,
    "spende_laufzettel": 0.00
  },
  "tax_groups": {...},
  "by_variant": [...],
  "spenden": [...],
  "verkauf_count": 34,
  "spende_count": 1
}
```

**Anwendungsfälle:**
- Monatliche Finanzberichterstattung
    - Steuer-Vorbereitung
    - Umsatzanalyse

---

### `GET /api/buchhaltung/spenden-total`

**Beschreibung:** Leichtgewichtiger Endpunkt, der nur Spenden-Summen für einen Zeitraum zurückgibt.

**Authentifizierung:** Erforderlich

**Query-Parameter:**
- `period` (optional): `week`, `month` (Standard), `year`
- `reference_date` (optional): ISO-8601-Datumsstring

**Antwort:**
```json
{
  "spende_total": 789.00,
  "spende_count": 5,
  "period": "month",
  "cutoff": "2024-06-01T00:00:00+00:00",
  "end": "2024-07-01T00:00:00+00:00"
}
```

**Anwendungsfälle:**
- Spenden-Dashboards
    - Externe Integrationen
    - Schnelle Spenden-Summen

---

### `POST /api/buchhaltung/spende`

**Beschreibung:** Zeichnet eine manuelle Spende auf (z.B. aus einer Spendenbox).

**Authentifizierung:** Erforderlich

**Request Body:**
```json
{
  "amount": 25.00,
  "donor_name": "Max Mustermann",
  "date": "2024-06-15T10:30:00+00:00",
  "notes": "Spendenbox-Beleg"
}
```

**Antwort:** Gibt das erstellte Spenden-Objekt zurück.

**Anwendungsfälle:**
- Manuelle Spenden-Aufzeichnung
    - Bar-Spenden-Tracking
    - Spendenbox-Management

---

### `DELETE /api/buchhaltung/spende/{id}`

**Beschreibung:** Löscht einen manuellen Spendeneintrag.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Spenden-Datenbank-ID

**Antwort:**
```json
{
  "success": true
}
```

**Anwendungsfälle:**
- Spendenkorrektur
    - Datenbereinigung
    - Fehlerkorrektur

---

## Materialkatalog

### `GET /api/katalog`

**Beschreibung:** Gibt den vollständigen Materialkatalog-Baum zurück (Standorte → Kategorien → Varianten).

**Authentifizierung:** Erforderlich

**Antwort:**
```json
{
  "locations": [
    {
      "id": 1,
      "name": "Hauptwerkstatt",
      "kategorien": [
        {
          "id": 1,
          "name": "Filamente",
          "varianten": [
            {
              "id": 1,
              "name": "PLA 1.75mm Schwarz",
              "price": 20.00,
              "pricing_model": "per_unit",
              "tax_rate": 19.0
            }
          ]
        }
      ]
    }
  ]
}
```

**Anwendungsfälle:**
- Material-Browsing
    - Preis-Lookup
    - Katalog-Anzeige

---

### `POST /api/katalog/bulk-import`

**Beschreibung:** Erstellt atomar Standorte, Kategorien und Varianten aus einem strukturierten Import.

**Authentifizierung:** Erforderlich

**Request Body:**
```json
{
  "locations": [
    {
      "name": "Neue Werkstatt",
      "kategorien": [
        {
          "name": "Neue Kategorie",
          "varianten": [
            {
              "name": "Neues Material",
              "price": 10.00,
              "pricing_model": "per_unit"
            }
          ]
        }
      ]
    }
  ]
}
```

**Antwort:** Gibt die erstellten Objekte zurück.

**Anwendungsfälle:**
- Bulk-Katalog-Import
    - Ersteinrichtung
    - Katalog-Migration

---

## Laufzettel

### `GET /api/laufzettel`

**Beschreibung:** Listet alle Laufzettel mit optionaler Filterung auf.

**Authentifizierung:** Erforderlich

**Query-Parameter:**
- `uid` (optional): Filter nach NFC-Tag-UID
- `date` (optional): Filter nach Datum (ISO 8601)
- `paid` (optional): Filter nach Zahlungsstatus (`true`/`false`)

**Antwort:**
```json
[
  {
    "id": 1,
    "uid": "9CF22507",
    "date": "2024-06-15",
    "payment_method": "karte",
    "total": 25.00,
    "materials": [...]
  }
]
```

**Anwendungsfälle:**
- Laufzettel-Historie
    - Zahlungs-Tracking
    - Nutzungsanalyse

---

### `POST /api/laufzettel`

**Beschreibung:** Erstellt manuell einen neuen Laufzettel.

**Authentifizierung:** Erforderlich

**Request Body:**
```json
{
  "uid": "9CF22507",
  "date": "2024-06-15",
  "notes": "Manuelle Erstellung"
}
```

**Antwort:** Gibt den erstellten Laufzettel zurück.

**Anwendungsfälle:**
- Manuelle Laufzettel-Erstellung
    - Testing
    - Notfall-Laufzettel

---

### `POST /api/laufzettel/{id}/material`

**Beschreibung:** Fügt einen Materialeintrag zu einem Laufzettel hinzu.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Laufzettel-Datenbank-ID

**Request Body:**
```json
{
  "variante_id": 1,
  "menge": 2.5,
  "unit": "kg"
}
```

**Antwort:** Gibt den erstellten Materialeintrag zurück.

**Anwendungsfälle:**
- Materialnutzungs-Tracking
    - Kostenberechnung
    - Inventar-Management

---

## Zahlungsabwicklung

### `POST /api/laufzettel/{id}/pay/bar`

**Beschreibung:** Zeichnet eine Barzahlung für einen Laufzettel auf und sperrt ihn.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Laufzettel-Datenbank-ID

**Antwort:**
```json
{
  "success": true,
  "payment_method": "bar",
  "paid_at": "2024-06-15T10:30:00+00:00"
}
```

**Anwendungsfälle:**
- Barzahlungs-Aufzeichnung
    - Manuelle Zahlungseingabe
    - Zahlungs-Tracking

---

### `POST /api/laufzettel/{id}/pay/karte`

**Beschreibung:** Initiiert eine Kartenzahlung über SumUp Solo Cloud API oder Payment Switch.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Laufzettel-Datenbank-ID

**Antwort:**
```json
{
  "mock": false,
  "mode": "solo",
  "client_transaction_id": "gc-...",
  "status": "PENDING"
}
```

Im Payment-Switch-Modus enthält die Antwort zusätzlich eine `payment_url` (das URL-Schema der SumUp-App).

**Anwendungsfälle:**
- Kartenzahlungs-Verarbeitung
    - SumUp-Integration
    - Digitale Zahlungen

---

### `GET /api/laufzettel/{id}/pay/karte/status`

**Beschreibung:** Pollt den Status einer ausstehenden Kartenzahlung. Im Payment-Switch-Modus erfolgt die Bestätigung automatisch durch Abgleich der SumUp-Transaktionshistorie.

**Authentifizierung:** Erforderlich

**Parameter:**
- `id` (path): Laufzettel-Datenbank-ID

**Antwort:**
```json
{
  "status": "SUCCESSFUL",
  "transaction_id": "txn_123456",
  "amount": 25.00
}
```

`status` ist einer von `SUCCESSFUL`, `NOT_FOUND`, `TIMEOUT` oder `PENDING`.

**Anwendungsfälle:**
- Zahlungsstatus-Überwachung
    - Transaktionsverifizierung
    - UI-Updates

---

## Gast-Laufzettel

### `POST /api/guest/laufzettel`

**Beschreibung:** Erstellt einen Gast-Laufzettel (kein Mitgliedskonto erforderlich).

**Authentifizierung:** Öffentlich

**Request Body:**
```json
{
  "name": "Gast Benutzer",
  "address": "Musterstraße 1, 12345 Stadt",
  "email": "gast@example.com",
  "date": "2026-07-15",
  "start": "2026-07-15T10:00:00"
}
```

`name` und `address` sind erforderlich; `email`, `date` und `start` sind optional.

**Antwort:** Gibt den erstellten Gast-Laufzettel mit Session-Token zurück.

**Anwendungsfälle:**
- Gastzugang
    - Einmal-Benutzer
    - Testing

---

### `GET /api/guest/session-check`

**Beschreibung:** Prüft, ob ein Gast eine aktive Session hat.

**Authentifizierung:** Öffentlich (verwendet Gast-Session-Cookie)

**Antwort:**
```json
{
  "guest_id": "<uuid-oder-null>"
}
```

**Anwendungsfälle:**
- Session-Validierung
    - Gast-UI-Status
    - Zugriffskontrolle

---

## Fehlerbehandlung

Alle Endpunkte folgen konsistenten Fehlerantwort-Mustern:

### HTTP-Statuscodes

| Code | Beschreibung |
|---|---|
| `200` | Erfolg |
| `400` | Bad Request (Validierungsfehler) |
| `401` | Unauthorized (Authentifizierung erforderlich) |
| `403` | Forbidden (unzureichende Berechtigungen) |
| `404` | Resource not found |
| `409` | Conflict (Duplikat, gesperrte Ressource, etc.) |
| `500` | Interner Serverfehler |

### Fehlerantwort-Format

```json
{
  "detail": "Fehlermeldung, die beschreibt, was schiefgelaufen ist"
}
```

### Häufige Fehler-Szenarien

- **401**: Nicht eingeloggt oder Session abgelaufen
- **403**: Admin-Verifizierung erforderlich für sensible Operationen
- **404**: Ressourcen-ID existiert nicht
- **409**: Ressource existiert bereits (doppelte UID), oder Laufzettel bereits bezahlt
- **500**: Datenbankfehler, unerwartete Ausnahme

---

## Rate Limiting

Derzeit ist kein Rate Limiting implementiert. Erwägen Sie die Implementierung von Rate Limiting für:
- Öffentliche Endpunkte
- Zahlungsverarbeitung
    - Bulk-Operationen

---

## Versionsinformationen

Die API-Versionierung folgt der Anwendungsversion. Überprüfen Sie `/api/status` für Systeminformationen.

---

## Interaktive Dokumentation

Für interaktives API-Testing und -Exploration verwenden Sie die automatisch generierte Swagger UI:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

Diese bieten Request/Response-Beispiele, Parameter-Validierung und die Möglichkeit, Endpunkte direkt im Browser zu testen.
