# Gast-Laufzettel (Nicht-Mitglied-Nutzung)

## Übersicht

Die Gast-Laufzettel-Funktion ermöglicht es Nicht-Mitgliedern, einen Laufzettel zu erstellen, indem sie einen QR-Code mit ihrem Smartphone scannen. Dies ermöglicht Besuchern des Makerspaces, ihre Materialnutzung zu verfolgen, ohne einen RFID-Tag oder ein Mitgliedskonto zu benötigen.

## QR-Code-Dateien

Zwei QR-Code-Dateien sind im Projektstammverzeichnis verfügbar:
- `guest-laufzettel-qr.png` - PNG-Format (Raster)
- `guest-laufzettel-qr.svg` - SVG-Format (Vektor)

Beide Dateien verwenden die Corporate Identity Akzentfarbe (#d04417 - orange-rot) für den QR-Code-Vordergrund.

### QR-Code-Vorschau

![Gast-Laufzettel QR-Code (PNG)](/guest-laufzettel-qr.png)

Der oben gezeigte QR-Code zeigt auf:
```
http://192.168.3.228:8000/guest/laufzettel
```

## QR-Code-URL

Der QR-Code zeigt auf:
```
http://192.168.3.228:8000/guest/laufzettel
```

**Hinweis**: Aktualisieren Sie die IP-Adresse (192.168.3.228) auf Ihre tatsächliche Raspberry Pi IP-Adresse, bevor Sie den QR-Code drucken/anzeigen.

## Funktionsweise

1. **QR-Code scannen**: Wenn ein Gast den QR-Code scannt, wird er zur Gast-Laufzettel-Formularseite weitergeleitet.

2. **Formularübermittlung**: Der Gast füllt aus:
   - Name (erforderlich)
   - E-Mail (optional)
   - Datum und Uhrzeit (automatisch ausgefüllt)
   - Klick auf "Fertig" zum Absenden

3. **Laufzettel-Erstellung**: Ein neuer Laufzettel wird erstellt mit:
   - Eindeutiger Gast-ID (UUID, in einem Browser-Cookie gespeichert)
   - Generierte UID (Format: GUEST-XXXXXX)
   - Der angegebene Name und E-Mail

4. **Materialverfolgung**: Der Gast kann dann:
   - Materialien zu seinem Laufzettel hinzufügen
   - Spenden (Spende) hinzufügen
   - Seine Materialnutzung anzeigen
   - Kann keine Zahlung selbst initiieren

5. **Sitzungspersistenz**: Das Gast-Sitzungs-Cookie bleibt bestehen, bis der Laufzettel bezahlt ist. Wenn sie den QR-Code am selben Tag erneut scannen, sehen sie ihren vorhandenen Laufzettel.

6. **Erinnerung an Vortag**: Wenn sie an einem neuen Tag erneut scannen mit einem unbezahlten Laufzettel vom Vortag, erscheint eine Erinnerungs-Popup-Meldung.

7. **Zahlung**: Gäste teilen einem Admin ihren Namen mit, und der Admin kann:
   - Den Laufzettel über den Namensfilter auf der `/laufzettel`-Seite finden
   - Zahlung manuell verarbeiten
   - Den Laufzettel als bezahlt markieren

## Session-Verwaltung (API-Endpunkte)

### Session-Check: `GET /api/guest/session-check`

Prüft, ob der Browser bereits eine aktive Gast-Session hat (d.h. ob ein `guest_id`-Cookie gesetzt ist).

**Antwort (aktive Session):**
```json
{ "guest_id": "550e8400-e29b-41d4-a716-446655440000" }
```

**Antwort (keine Session):**
```json
{ "guest_id": null }
```

Das Frontend nutzt diesen Endpunkt beim Laden der Formularseite, um zu entscheiden, ob ein neues Formular angezeigt oder direkt auf den bestehenden Laufzettel weitergeleitet werden soll.

---

### Heutigen Laufzettel abrufen: `GET /api/guest/laufzettel/{guest_id}`

Gibt den aktuellen **unbezahlten** Laufzettel des Gastes für **heute** zurück.

**Pfad-Parameter:** `guest_id` — die UUID aus dem Session-Cookie.

**Erfolgreiche Antwort (200):**
```json
{
  "id": 42,
  "uid": "GUEST-A3F9C1",
  "date": "2026-06-03",
  "owner_name": "Max Mustermann",
  "guest_email": "max@example.com",
  "payment_method": null,
  "material": [...]
}
```

**Fehler (404):** Kein unbezahlter Laufzettel für heute vorhanden.

---

### Vorherige unbezahlte Laufzettel prüfen: `GET /api/guest/laufzettel/{guest_id}/previous`

Prüft, ob der Gast einen **unbezahlten Laufzettel von einem früheren Tag** hat (Datum strikt vor heute).

**Pfad-Parameter:** `guest_id` — die UUID aus dem Session-Cookie.

**Antwort (vorhanden):**
```json
{
  "has_previous_unpaid": true,
  "laufzettel": {
    "id": 37,
    "date": "2026-06-01",
    "owner_name": "Max Mustermann",
    ...
  }
}
```

**Antwort (keiner vorhanden):**
```json
{ "has_previous_unpaid": false }
```

Das Frontend zeigt bei `has_previous_unpaid: true` ein Hinweis-Popup an, das den Gast darauf aufmerksam macht, dass noch ein offener Betrag aus einem früheren Besuch existiert.

## Offene Laufzettel vom Vortag (Carry-Forward)

Wenn ein Gast an einem neuen Tag die Formularseite aufruft und noch einen unbezahlten Laufzettel vom Vortag hat, läuft folgender Ablauf ab:

1. Das Frontend prüft über `GET /api/guest/laufzettel/{guest_id}/previous`, ob ein älterer offener Laufzettel existiert.
2. Falls ja, erscheint ein Popup mit dem Hinweis und dem Betrag des alten Laufzettels.
3. Der Gast wird gebeten, den offenen Betrag bei einem Admin zu begleichen.
4. Danach kann ein neuer Laufzettel für den aktuellen Tag erstellt werden.

**Wichtig:** Der Carry-Forward ist nur eine Erinnerungsfunktion. Das System löscht oder schließt alte Laufzettel nicht automatisch — sie bleiben offen, bis ein Admin die Zahlung erfasst.

## E-Mail nach Laufzettel-Erstellung

Wenn der Gast beim Ausfüllen des Formulars eine E-Mail-Adresse angibt, werden nach der Laufzettel-Erstellung **zwei E-Mails** automatisch (fire-and-forget) versandt:

### 1. Willkommens-E-Mail mit Laufzettel-Link

**Betreff:** `Dein H3cke Laufzettel #{id} ist erstellt!`

Enthält einen direkten Link zur öffentlichen Laufzettel-Ansicht:
```
{PUBLIC_BASE_URL}/laufzettel/view/{laufzettel_id}
```

Über diesen Link kann der Gast seinen Laufzettel jederzeit einsehen — auch nach dem Schließen des Browsers, solange er die URL hat. Die Ansicht benötigt keine Authentifizierung.

### 2. Mitgliedschafts-Einladung (easyVerein)

**Betreff:** `Willkommen in der H3cke! Jetzt Mitglied werden`

Enthält einen Link zur Mitgliedschafts-Anmeldung bei easyVerein. Die URL wird aus der Konfigurationsvariable `EASYVEREIN_SIGNUP_URL` gelesen. Falls diese nicht gesetzt ist, wird keine Einladungs-E-Mail gesendet.

**Konfiguration:**
```json
{
  "easyverein_signup_url": "https://easyverein.com/public/h3cke/applicationform/"
}
```

Beide E-Mails werden nur gesendet, wenn das E-Mail-Modul (`backend/email_utils.py`) konfiguriert ist.

## Öffentliche Laufzettel-Ansicht

### `GET /laufzettel/view/{laufzettel_id}`

Eine **öffentliche, schreibgeschützte** Ansicht eines Laufzettels — **keine Authentifizierung erforderlich**. Sie ist für bezahlte Laufzettel gedacht und wird per E-Mail-Link an Gäste und Mitglieder gesendet.

**Was angezeigt wird:**
- Name des Gastes / Mitglieds
- Datum des Besuchs
- Uhrzeit (Start)
- Materialien, gruppiert nach Katalog-Standort (Location)
- Einzelpreise und Gesamtsumme
- Zahlungsmethode und Zahlungszeitpunkt (falls bezahlt)

**Datenbankzugriff:** Das System baut eine `variante_id → Location`-Zuordnung aus `catalog.db` auf, um Materialien nach Standort zu gruppieren. Falls `catalog.db` nicht erreichbar ist, wird die Gruppierung übersprungen.

**Template:** `templates/public-laufzettel.html`

**Beispiel-URL:**
```
https://h3cke.de/laufzettel/view/42
```

Diese URL ist stabil und kann sicher per E-Mail, QR-Code oder Druckbeleg weitergegeben werden.

## Drucken des QR-Codes

Für beste Ergebnisse beim Drucken:
- Verwenden Sie die SVG-Version für Skalierbarkeit
- Stellen Sie sicher, dass der QR-Code mindestens 2cm x 2cm groß ist
- Drucken Sie auf ein langlebiges Material oder laminieren Sie es
- Zeigen Sie es prominent am Eingang oder in den Werkstattbereichen an

## Aktualisieren der IP-Adresse

Um die QR-Code-URL auf eine andere IP-Adresse zu ändern:

1. Bearbeiten Sie das `generate_qr.py`-Skript (falls Python verwendet wird):
   ```python
   GUEST_URL = "http://IHRE-NEUE-IP:8000/guest/laufzettel"
   ```

2. Oder verwenden Sie den curl-Befehl mit der neuen URL:
   ```bash
   curl -o guest-laufzettel-qr.png "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=http://IHRE-NEUE-IP:8000/guest/laufzettel&color=d04417&bgcolor=ffffff"
   curl -o guest-laufzettel-qr.svg "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=http://IHRE-NEUE-IP:8000/guest/laufzettel&color=d04417&bgcolor=ffffff&format=svg"
   ```

## Corporate Identity Farben

Der QR-Code verwendet die H3cke MakerSpace Corporate Identity Farben:
- **Akzent (Vordergrund)**: #d04417 (orange-rot)
- **Hintergrund**: #ffffff (weiß)

Diese Farben entsprechen der Hauptakzentfarbe, die in `static/css/style.css` definiert ist.

## Relevante Dateien

- `backend/laufzettel/routes.py` - Alle Gast-Endpunkte und öffentliche Ansicht
- `backend/config.py` - `PUBLIC_BASE_URL`, `EASYVEREIN_SIGNUP_URL`
- `backend/email_utils.py` - E-Mail-Versand
- `backend/email_templates.py` - HTML-Templates für Gast-E-Mails
- `templates/guest-laufzettel-form.html` - Formularseite (QR-Code-Landingpage)
- `templates/guest-laufzettel-detail.html` - Gast-Detailansicht (mit Session-Cookie)
- `templates/public-laufzettel.html` - Öffentliche Quittungsansicht (ohne Auth)
