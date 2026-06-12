# 22 · Buchhaltung

Diese Seite beschreibt die Buchhaltungsansicht von MakerPi GroundControl — eine aggregierte Umsatzübersicht nach Steuersatz für die monatliche Kassenbuchführung im Makerspace.

---

## Übersicht

Die Seite `/buchhaltung` fasst alle abgeschlossenen Laufzettel-Zahlungen eines Zeitraums zusammen und gruppiert sie nach steuerlicher Kategorie. So lassen sich Umsätze mit 19 %, 7 % und 0 % MwSt. sowie Spenden auf einen Blick ablesen.

Die Daten stammen aus zwei Quellen:

| Quelle | Tabelle | Was wird erfasst |
|---|---|---|
| Abgeschlossene Laufzettel | `buchhaltung.db → verkauf` | Jede bezahlte Materialposition (Snapshot bei Zahlung) |
| Manuelle Spenden | `buchhaltung.db → spende` | Direkt in der UI erfasste Spendenbeträge |

> **Wichtig:** In der `verkauf`-Tabelle werden Einträge erst beim Abschließen eines Laufzettels (Zahlung) erstellt — offene Laufzettel erscheinen nicht in der Auswertung.

---

## Die Buchhaltungsseite

Nach dem Login unter `/buchhaltung` erreichbar. Die Seite zeigt:

- **Periodenauswahl** – Woche, Monat (Standard) oder Jahr; Navigation durch vergangene Perioden möglich
- **Gesamtumsatz** (Materialverkäufe + manuelle Spenden)
- **Aufschlüsselung nach Steuersatz** – je ein Block für 19 %, 7 %, 0 %, Katalog-Spenden und Laufzettel-Spenden
- **Einzelne Spendeneinträge** – Liste aller manuell erfassten Spenden im Zeitraum
- **Umsatz nach Variante** – sortiert nach Umsatz (höchster zuerst)

---

## Steuersatzkategorien

Der Steuersatz wird am Materialkatalogeintrag (`MaterialUnterkategorie.tax_rate`) konfiguriert und beim Bezahlen als Snapshot in `LaufzettelMaterial.tax_rate` sowie `Verkauf.tax_rate` gespeichert. Fehlt ein Wert, gilt **19 % als Fallback**.

| Steuersatz | Bedeutung | Typische Verwendung |
|---|---|---|
| **19 %** | Voller Steuersatz | Standardmaterialien, Filament, Verbrauchsmaterial |
| **7 %** | Ermäßigter Steuersatz | Lebensmittel, bestimmte kulturelle Güter |
| **0 %** | Steuerbefreit | Gemeinnützige Leistungen o.ä. |

### Steuersatz konfigurieren

Im Materialkatalog unter `/katalog`:

1. Unterkategorie auswählen → Bearbeiten
2. Feld `tax_rate` auf `0`, `7` oder `19` setzen
3. Beim nächsten Laufzettel wird der neue Satz automatisch übernommen

> **Hinweis:** Bereits abgeschlossene Laufzettel behalten den Steuersatz, der zum Zahlungszeitpunkt galt (Snapshot). Änderungen am Katalog wirken sich nur auf zukünftige Verkäufe aus.

---

## Spenden

Das System unterscheidet drei Arten von Spenden:

### 1. Katalog-Spenden (`spende_katalog`)

Materialvarianten, bei denen `MaterialUnterkategorie.is_spende = true` gesetzt ist. Diese erscheinen im Laufzettel als normale Positionen, werden aber buchhaltungsseitig als Spende gewertet (kein Umsatz, keine MwSt.).

Konfiguration: Im Katalog die Unterkategorie als „Spende" markieren.

### 2. Laufzettel-Spenden (`spende_laufzettel`)

Freie Spendeneinträge, die direkt in einem Laufzettel ohne Katalogbezug hinzugefügt wurden (`variante_id = null`, `is_spende = true`).

### 3. Manuelle Spenden (`spende`-Tabelle)

Direkt auf der Buchhaltungsseite erfasste Barspendenbeträge (z.B. Spendenbox). Diese fließen **nicht** in die Verkaufsstatistik, sondern erscheinen separat als `spende_total`.

**Spende manuell erfassen:**

```
POST /api/buchhaltung/spende
{
  "amount": 25.00,
  "donor_name": "Mustermann",        // optional
  "date": "2026-05-31T18:00:00",     // optional, Standard: jetzt
  "notes": "Spendenbox Eingang"      // optional
}
```

---

## Periodenfilter

| Periode | Zeitraum |
|---|---|
| `week` | Montag 00:00 UTC bis Sonntag 23:59 UTC der Woche, die das `reference_date` enthält |
| `month` | Erster des Monats 00:00 UTC bis letzter Tag 23:59 UTC |
| `year` | 1. Januar 00:00 UTC bis 31. Dezember 23:59 UTC |

Der Parameter `reference_date` (ISO-8601-String) verschiebt das Betrachtungsfenster in die Vergangenheit, ohne die Periode zu ändern. Fehlt er, wird der aktuelle Zeitpunkt verwendet.

---

## API-Endpunkte

| Methode | Endpunkt | Beschreibung |
|---|---|---|
| `GET` | `/buchhaltung` | HTML-Seite (Login erforderlich) |
| `GET` | `/api/buchhaltung/summary` | Aggregierte Auswertung für einen Zeitraum |
| `GET` | `/api/buchhaltung/spenden-total` | Leichter Spenden-Endpunkt (öffentlich) |
| `POST` | `/api/buchhaltung/spende` | Manuelle Spende erfassen |
| `DELETE` | `/api/buchhaltung/spende/{id}` | Manuelle Spende löschen |

### `GET /api/buchhaltung/summary`

**Query-Parameter:**

| Parameter | Typ | Standard | Werte |
|---|---|---|---|
| `period` | string | `month` | `week`, `month`, `year` |
| `reference_date` | string (ISO-8601) | jetzt | z.B. `2026-04-15` |

**Beispielantwort:**

```json
{
  "period": "month",
  "cutoff": "2026-05-01T00:00:00+00:00",
  "end": "2026-06-01T00:00:00+00:00",
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
  "tax_groups": {
    "19": [ { "name": "PLA 1.75mm schwarz", "revenue": 80.00, "tax_rate": 19.0, "units": 8.0, ... } ],
    "7":  [ { "name": "Getränk", "revenue": 15.00, "tax_rate": 7.0, ... } ],
    "0":  [],
    "spende_katalog": [],
    "spende_laufzettel": []
  },
  "by_variant": [ ... ],
  "spenden": [
    { "id": 3, "amount": 25.00, "donor_name": "Mustermann", "date": "2026-05-31T18:00:00+00:00", "notes": "Spendenbox" }
  ],
  "verkauf_count": 34,
  "spende_count": 1
}
```

### `GET /api/buchhaltung/spenden-total`

Ein leichtgewichtiger öffentlicher Endpunkt, der nur die Spenden-Summen für einen Zeitraum zurückgibt. Nützlich für Dashboards, externe Integrationen oder wenn Sie die vollständige Buchhaltungsübersicht nicht benötigen.

**Query-Parameter:**

| Parameter | Typ | Standard | Werte |
|---|---|---|---|
| `period` | string | `month` | `week`, `month`, `year` |
| `reference_date` | string (ISO-8601) | jetzt | z.B. `2026-04-15` |

**Beispielantwort:**

```json
{
  "spende_total": 789.00,
  "spende_count": 5,
  "period": "month",
  "cutoff": "2026-06-01T00:00:00+00:00",
  "end": "2026-07-01T00:00:00+00:00"
}
```

**Beispielverwendung:**

```bash
# Spenden dieses Monats abrufen
curl "http://localhost:8000/api/buchhaltung/spenden-total?period=month"

# Spenden dieser Woche abrufen
curl "http://localhost:8000/api/buchhaltung/spenden-total?period=week"

# Spenden für einen bestimmten Monat abrufen
curl "http://localhost:8000/api/buchhaltung/spenden-total?period=month&reference_date=2024-05-15"
```

> **Hinweis:** Dieser Endpunkt ist öffentlich zugänglich und erfordert keine Authentifizierung.

### `POST /api/buchhaltung/spende`

Body (JSON):

| Feld | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `amount` | float | ja | Betrag in Euro (muss > 0 sein) |
| `donor_name` | string | nein | Name des Spenders |
| `date` | string (ISO-8601) | nein | Datum der Spende; Standard: jetzt |
| `notes` | string | nein | Freitext-Notiz |

**Antwort:** Das angelegte `Spende`-Objekt als JSON.

**Fehler:**
- `400` – `amount` ist ≤ 0
- `401` – nicht eingeloggt

### `DELETE /api/buchhaltung/spende/{id}`

Löscht einen manuellen Spendeneintrag anhand seiner ID.

**Antwort:** `{ "success": true }`

**Fehler:**
- `401` – nicht eingeloggt
- `404` – ID nicht gefunden

---

## Zahlen verstehen: Umsatz vs. Spende

| Begriff | Definition | Quelle |
|---|---|---|
| **Umsatz** (`material_total`) | Summe aller bezahlten Materialpreise in der Periode | `verkauf.calculated_price` (nur `is_spende = false`) |
| **Spenden** (`spende_total`) | Summe aller manuell erfassten Spendenbeträge | `spende.amount` |
| **Gesamt** (`total`) | `material_total + spende_total` | — |

> Katalog-Spenden und Laufzettel-Spenden fließen in `material_total` ein (sie sind Teil von Laufzetteln), erscheinen aber in eigenen Buckets (`spende_katalog`, `spende_laufzettel`) und tragen **nicht** zu den steuerpflichtigen Summen (19/7/0) bei.

### Rechenbeispiel

Ein Mitglied kauft folgendes Material und zahlt bar:

| Position | Menge | Preis | Steuersatz | is_spende |
|---|---|---|---|---|
| PLA 1.75mm schwarz | 1 | **10,00 €** | 19 % | nein |
| Spendenbox-Beitrag | 1 | 5,00 € | — | ja (Laufzettel-Spende) |

Nach der Zahlung erscheint in der Monatsauswertung:

```
tax_totals.19          = 10,00 €   ← steuerpflichtiger Umsatz
tax_totals.spende_laufzettel = 5,00 €    ← Laufzettel-Spende, kein steuerpfl. Umsatz
material_total         = 15,00 €   ← beides zusammen
spende_total           =  0,00 €   ← keine manuelle Spende in diesem Beispiel
total                  = 15,00 €
```

Die 10,00 € tauchen auch unter `tax_groups.19` als Variante auf und können ans Kassenbuch übergeben werden. Für die MwSt.-Abführung gilt: **10,00 € × 19/119 = 1,60 € MwSt.** (Bruttorechnung).

---

## Praktischer Admin-Workflow: Monatsabschluss

1. `/buchhaltung` öffnen, Periode **Monat** wählen, zum Vormonat navigieren
2. **Umsatz 19 %** ablesen → ans Kassenbuch oder Steuerberater übergeben
3. **Umsatz 7 %** und **0 %** separat notieren (falls vorhanden)
4. **Spenden** prüfen: manuelle Spendeneinträge auf Vollständigkeit prüfen; ggf. fehlende Einträge via `POST /api/buchhaltung/spende` nachtragen
5. **Katalog- und Laufzettel-Spenden** separat ausweisen (kein steuerpflichtiger Umsatz)
6. Screenshot oder Export der Zusammenfassung für die Ablage

> **Tipp:** Die `by_variant`-Liste zeigt welche Materialien am meisten Umsatz erzeugt haben — nützlich für Nachbestellungen und Preisüberprüfungen.

---

## Datenbankdetails

| Tabelle | Datenbank | Inhalt |
|---|---|---|
| `verkauf` | `buchhaltung.db` | Snapshot jeder bezahlten Materialposition: Preis, Steuersatz, `is_spende`, Zeitstempel, Zahlungsmethode |
| `spende` | `buchhaltung.db` | Manuell erfasste Spendenbeträge |

Die `verkauf`-Einträge werden beim Abschließen eines Laufzettels aus `laufzettel_material` erzeugt. Änderungen am Katalog nach der Zahlung haben **keinen** Einfluss auf bereits gebuchte Positionen.
