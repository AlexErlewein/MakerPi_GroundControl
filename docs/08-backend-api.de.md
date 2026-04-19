# Backend-API

Die API ist in domain-spezifische Router aufgeteilt. Alle Endpunkte geben JSON zurück (außer HTML-Seiten, die explizit als `text/html` markiert sind).

## Basis-URL

Alle API-Aufrufe sind relativ zur Basis:

```
http://localhost:8000
```

## Authentifizierung

- **Seiten:** Session-basiert via Cookie (gesetzt beim Login)
- **API:** Keine Authentifizierung erforderlich (Annahme: lokales Netzwerk)

### Session-Login

| Methode | Pfad | Body | Erfolg | Fehler |
|---|---|---|---|---|
| `POST` | `/api/auth/login` | `{"username":"...","password":"..."}` | `200` + Session-Cookie | `401` |
| `POST` | `/api/auth/logout` | — | `200` | — |

## Endpunkte

### Dashboard

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/status` | System-Health + aktive Geräte |
| `GET` | `/api/devices` | Alle bekannten Geräte |
| `GET` | `/api/messages` | Letzte MQTT-Nachrichten (Query: `limit`, `offset`) |
| `GET` | `/api/topics` | Alle gesehenen Topics |

### Tags

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/tags` | Alle RFID-Tags |
| `GET` | `/api/tags/{uid}` | Einzelnen Tag abrufen |
| `POST` | `/api/tags` | Neuen Tag erstellen |
| `PUT` | `/api/tags/{uid}` | Tag aktualisieren |
| `DELETE` | `/api/tags/{uid}` | Tag löschen |

**POST/PUT Body:**
```json
{
  "uid": "A4B2C3D4",
  "owner_name": "Max Mustermann",
  "member_id": "M-123",
  "notes": "Optional"
}
```

### Mitglieder

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/mitglieder` | Alle Mitglieder (Query: `status=active`) |
| `GET` | `/api/mitglieder/{id}` | Einzelnes Mitglied abrufen |
| `POST` | `/api/mitglieder` | Neues Mitglied erstellen |
| `PUT` | `/api/mitglieder/{id}` | Mitglied aktualisieren |
| `DELETE` | `/api/mitglieder/{id}` | Mitglied löschen |

### Laufzettel

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/laufzettel` | Alle Einträge (Query: `uid`, `date`) |
| `GET` | `/api/laufzettel/{id}` | Einzelnen Eintrag mit Materialien |
| `POST` | `/api/laufzettel` | Neuen Eintrag erstellen |
| `PUT` | `/api/laufzettel/{id}` | Eintrag aktualisieren |
| `GET` | `/api/tags/{uid}/laufzettel` | Alle Einträge für einen Tag |

**POST Body:**
```json
{
  "uid": "A4B2C3D4",
  "date": "2025-01-15",
  "owner_name": "Max Mustermann",
  "member_id": "M-123",
  "start": "2025-01-15T09:30:00"
}
```

### Laufzettel-Material

| Methode | Pfad | Beschreibung |
|---|---|---|
| `POST` | `/api/laufzettel/{id}/material` | Material hinzufügen |
| `PUT` | `/api/laufzettel/{id}/material/{mat_id}` | Material aktualisieren |
| `DELETE` | `/api/laufzettel/{id}/material/{mat_id}` | Material entfernen |

**POST Body:**
```json
{
  "name": "PLA Weiß",
  "menge": 150,
  "unit": "g",
  "variante_id": 3,
  "calculated_price": 6.00
}
```

### Zahlung

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/payment/config` | Welche Methoden konfiguriert sind (`sumup_configured`, `sumup_mock`) |
| `POST` | `/api/laufzettel/{id}/pay/bar` | Barzahlung erfassen — sperrt Laufzettel |
| `POST` | `/api/laufzettel/{id}/pay/karte` | Zahlung an SumUp-Terminal senden — sperrt Laufzettel |
| `DELETE` | `/api/laufzettel/{id}/pay` | Zahlungsstatus zurücksetzen (Admin) |

> Beide `POST /pay/...` Endpunkte geben `409` zurück, wenn der Laufzettel bereits bezahlt ist.

### Material-Katalog

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/api/katalog` | Vollständiger Katalog-Tree |
| `GET` | `/api/katalog/locations` | Alle Standorte |
| `POST` | `/api/katalog/locations` | Standort erstellen |
| `PUT` | `/api/katalog/locations/{id}` | Standort aktualisieren |
| `DELETE` | `/api/katalog/locations/{id}` | Standort löschen |
| `GET` | `/api/katalog/kategorien` | Alle Kategorien (Query: `location_id`) |
| `POST` | `/api/katalog/kategorien` | Kategorie erstellen |
| `PUT` | `/api/katalog/kategorien/{id}` | Kategorie aktualisieren |
| `DELETE` | `/api/katalog/kategorien/{id}` | Kategorie löschen |
| `GET` | `/api/katalog/varianten` | Alle Varianten (Query: `kategorie_id`) |
| `POST` | `/api/katalog/varianten` | Variante erstellen |
| `PUT` | `/api/katalog/varianten/{id}` | Variante aktualisieren |
| `DELETE` | `/api/katalog/varianten/{id}` | Variante löschen |

## Fehler-Antworten

Alle Fehler folgen diesem Schema:

```json
{
  "detail": "Klare Fehlerbeschreibung"
}
```

Häufige Status-Codes:

| Code | Bedeutung |
|---|---|
| `400` | Ungültige Eingabe / Validierungsfehler |
| `404` | Ressource nicht gefunden |
| `409` | Konflikt (z.B. bereits bezahlt) |
| `500` | Interner Serverfehler |

## Paginierung

Für listenartige Endpunkte:

```
GET /api/laufzettel?offset=0&limit=50
```

Antwort:
```json
{
  "items": [...],
  "total": 150,
  "offset": 0,
  "limit": 50
}
```

## Filter

Query-Parameter für Filter:

```
GET /api/laufzettel?uid=A4B2C3D4&date=2025-01-15
GET /api/mitglieder?status=active
GET /api/messages?topic=makerpi/devices/+/status
```

## Beispiel: Kompletter Flow

**Laufzettel erstellen und bezahlen:**

```bash
# 1. Laufzettel erstellen
curl -X POST http://localhost:8000/api/laufzettel \
  -H "Content-Type: application/json" \
  -d '{"uid":"A4B2C3D4","date":"2025-01-15"}'
# → Antwort: {"id": 42, ...}

# 2. Material hinzufügen
curl -X POST http://localhost:8000/api/laufzettel/42/material \
  -H "Content-Type: application/json" \
  -d '{"name":"PLA","menge":150,"unit":"g","calculated_price":6.00}'

# 3. Als bar bezahlt markieren
curl -X POST http://localhost:8000/api/laufzettel/42/pay/bar
# → Antwort: {"payment_method":"bar","paid_at":"2025-01-15T14:30:00Z"}
```
