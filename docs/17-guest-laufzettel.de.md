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
   - Eindeutiger Gast-ID (in einem Browser-Cookie gespeichert)
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
