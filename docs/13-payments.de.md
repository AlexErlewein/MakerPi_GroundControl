# Zahlungen

Diese Seite beschreibt die Zahlungsintegration auf der Laufzettel-Detailseite.

## Übersicht

Sobald ein Laufzettel Materialeinträge mit einem Gesamtbetrag > 0 hat, erscheinen Zahlungsschaltflächen:

| Methode | Integration | Ablauf |
|---------|-------------|--------|
| **Bar** | Nativ | Admin bestätigt Bareingang manuell |
| **Karte (Solo)** | SumUp Cloud API | Betrag wird direkt ans gepaarte Solo-Terminal gesendet |
| **Karte (Payment Switch)** | SumUp URL-Scheme | App-Link öffnet SumUp-App mit vorausgefülltem Betrag |

Nach jeder Zahlung wird der Laufzettel gesperrt: keine Bearbeitung mehr möglich.

---

## Konfiguration

In `config/config.json`:

```json
{
  "sumup_api_key": "sup_sk_...",
  "sumup_merchant_code": "MC...",
  "sumup_reader_id": "",
  "sumup_affiliate_key": "dein-affiliate-key",
  "sumup_mock": false
}
```

Das System wählt den Zahlungsmodus **automatisch** anhand der vorhandenen Konfiguration:

| Modus | Bedingung | Verhalten |
|-------|-----------|-----------|
| **Mock** | `sumup_mock: true` | Kein echter API-Call, sofortige Bestätigung |
| **Solo** | `sumup_reader_id` gesetzt | Checkout wird per Cloud API ans Terminal geschickt |
| **Payment Switch** | `sumup_affiliate_key` gesetzt, kein Reader | `sumupmerchant://`-Deeplink zur SumUp-App |

Den **Affiliate Key** erstellt man unter [developer.sumup.com](https://developer.sumup.com) → *Affiliate Keys*.

Alle Werte können auch als Umgebungsvariablen gesetzt werden: `SUMUP_API_KEY`, `SUMUP_MERCHANT_CODE`, `SUMUP_READER_ID`, `SUMUP_AFFILIATE_KEY`.

---

## Barzahlung

- Admin klickt „Bar bezahlen", bestätigt den angezeigten Betrag
- Sofortige Verbuchung, kein externer Service nötig

---

## Kartenzahlung – Solo Terminal (Cloud API)

Voraussetzung: ein **SumUp Solo**-Gerät, das über die SumUp App oder API gepaart wurde.

### Flow

```mermaid
sequenceDiagram
    participant Admin
    participant UI
    participant API
    participant SumUp
    participant Terminal

    Admin->>UI: "Mit Karte zahlen" klicken
    UI->>API: POST /pay/karte
    API->>SumUp: Checkout ans Terminal senden
    SumUp->>Terminal: Betrag anzeigen
    API-->>UI: client_transaction_id

    loop Polling (alle 3s, max 2 min)
        UI->>API: GET /pay/karte/status
        API-->>UI: PENDING / SUCCESSFUL / FAILED
    end

    Note over Terminal: Kunde tippt Karte
    API->>DB: payment_method="karte"
    UI->>UI: Laufzettel gesperrt
```

---

## Kartenzahlung – Payment Switch (SumUp App auf Handy)

Für alle anderen SumUp-Terminals (Air, 3G, Air Lite) oder wenn die SumUp-App auf dem Kassiergerät installiert ist.

### Flow

```mermaid
sequenceDiagram
    participant Admin
    participant UI
    participant API
    participant SumUpApp

    Admin->>UI: "Mit Karte zahlen" klicken
    UI->>API: POST /pay/karte
    API-->>UI: payment_url (sumupmerchant://...)
    UI->>UI: "SumUp App öffnen"-Button anzeigen
    Admin->>SumUpApp: App-Link tippen
    SumUpApp->>SumUpApp: Betrag vorausgefüllt, Zahlung durchführen
    Note over Admin: Zahlung am Terminal abschließen
    Admin->>UI: "Zahlung bestätigen" klicken
    UI->>API: POST /pay/karte/confirm-mock
    API->>DB: payment_method="karte"
    UI->>UI: Laufzettel gesperrt
```

> **Hinweis:** Die manuelle Bestätigung ist nötig, da SumUp keinen Callback-Mechanismus für die Handy-App bietet.

---

## Mock-Modus

Für Tests ohne echtes Terminal:

```json
{ "sumup_mock": true }
```

- Keine echten API-Calls
- Laufzettel wird sofort als „per Karte bezahlt" gesperrt

---

## API-Endpunkte

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/api/payment/config` | Konfigurationsstatus inkl. `payment_mode` |
| `POST` | `/api/laufzettel/{id}/pay/bar` | Barzahlung erfassen |
| `POST` | `/api/laufzettel/{id}/pay/karte` | Kartenzahlung initiieren |
| `GET` | `/api/laufzettel/{id}/pay/karte/status` | Zahlungsstatus prüfen (Solo-Modus) |
| `POST` | `/api/laufzettel/{id}/pay/karte/confirm-mock` | Zahlung manuell bestätigen (Mock / Payment Switch) |
| `DELETE` | `/api/laufzettel/{id}/pay/karte` | Laufende Kartenzahlung abbrechen |
| `DELETE` | `/api/laufzettel/{id}/pay` | Zahlungsstatus zurücksetzen (Admin) |

### `/api/payment/config` Antwort

```json
{
  "sumup_configured": true,
  "sumup_mock": false,
  "payment_mode": "payment_switch"
}
```

Mögliche Werte für `payment_mode`: `"solo"`, `"payment_switch"`, `"mock"`, `null`.

---

## Sicherheit

- API-Keys nie im Frontend exponieren
- Keys in `config/config.json` (gitignored) oder als Umgebungsvariablen

## Tagesabschluss

SumUp-Transaktionen erscheinen im SumUp-Dashboard und in der SumUp-App. GroundControl speichert nur den Status (bezahlt/nicht bezahlt), keine Transaktionsdetails. Für detaillierte Auswertungen den SumUp-Export verwenden.
