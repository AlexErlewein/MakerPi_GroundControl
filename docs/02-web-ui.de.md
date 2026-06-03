# Web-Oberfläche

Diese Seite erklärt die Hauptwebseiten aus der Perspektive einer Person, die das System bedient.

## Dashboard (`/`)

Das Dashboard ist die Einstiegsseite.

Verwenden Sie es, um:

- zu prüfen, ob das Backend verbunden und aktiv ist (MQTT-Status)
- offene Laufzettel anzuzeigen
- offline Geräte anzuzeigen
- Spenden (Spenden) für den aktuellen Monat anzuzeigen
- anzuzeigen, wie viele Mitglieder heute anwesend sind (basierend auf offenen Laufzettel mit Mitglied-ID)
- den Systemstatus zu prüfen für:
  - Docs-Server (Port 8001)
  - Zigbee-Bridge (Port 8090 + USB-Verbindung)
  - Datenbanken/BackBlaze (Litestream + B2-Verbindung)
  - Google Drive-Verbindung

Die Systemstatus-Indikatoren zeigen farbige Punkte:
- **Grün** = OK/verbunden
- **Rot** = Fehler/offline
- **Gelb** = Warnung/teilweise Probleme
- **Grau** = Unbekannt

Jedes Systemstatus-Label ist klickbar und verlinkt auf den jeweiligen Dienst.

## Datenbank-Seite (`/database`)

Die Datenbank-Seite ist hauptsächlich für Inspektion und Debugging.

Verwenden Sie sie, um:

- Nachrichtenverlauf zu überprüfen
- Topic-Vielfalt und Systemnutzung zu inspizieren
- Datenbankstatistiken zu prüfen

Diese Seite ist technischer als das Dashboard.

## Tags-Seite (`/tags`)

Diese Seite ist für RFID-Tag-Administration.

Sie können:

- einen Tag erstellen
- den Eigentümernamen bearbeiten
- die Mitglieds-ID bearbeiten
- Notizen hinzufügen
- Tags aktivieren/deaktivieren
- aktuelle Scan-Ereignisse inspizieren

Diese Seite ist der primäre Ort zur Pflege von Karteninhaber-Identitätsdaten.

## Laufzettel-Liste (`/laufzettel`)

Diese Seite zeigt alle Laufzettel-Einträge.

Sie können:

- Einträge filtern
- inspizieren, welcher Tag an welchem Datum von wem verwendet wurde
- einen neuen Laufzettel manuell mit dem **Neuer Laufzettel**-Button erstellen

Bei manueller Erstellung kann die UI den Eigentümer und die Mitglieds-ID für bekannte UIDs automatisch ausfüllen.

## Laufzettel-Details (`/laufzettel/{id}`)

Diese Seite ist der detaillierte Editor für einen Laufzettel.

Sie können:

- den Eigentümernamen bearbeiten
- die Mitglieds-ID bearbeiten
- die Startzeit bearbeiten
- die beteiligten Knoten/Geräte sehen
- Materialeinträge hinzufügen, bearbeiten und löschen

Materialeintrag-Modi:

- **Freitext** — manueller Name + Menge + optionale Einheit
- **Aus Katalog** — Standort/Kategorie/Variante auswählen und das System den Preis berechnen lassen

## Katalog-Seite (`/katalog`)

Diese Seite verwaltet die vordefinierte Materialstruktur.

Hierarchie:

- Standort
- Kategorie
- Variante

Beispiele:

- `Töpferei` → `Ton` → `fein`
- `Holz-Werkstatt` → `Holz` → `Esche`

Für jede Kategorie definieren Sie:

- Preismodell
- Anzeigeeinheit

Für jede Variante definieren Sie:

- Variantenname
- Einheitspreis

## Mitglieder-Seite (`/mitglieder`)

Verwaltung der Mitgliederdatenbank.

Sie können:

- alle Mitglieder anzeigen (aus easyVerein synchronisiert oder manuell angelegt)
- den NFC-Karten-Einschreibungsstatus jedes Mitglieds einsehen
- eine NFC-Karte für ein Mitglied einschreiben (sendet einen Schreibbefehl an das Kartenlesegerät)
- Mitgliedsdaten manuell anlegen oder bearbeiten

## Kasse-Seite (`/kasse`)

Schnellzugriff-Zahlungsbildschirm. Ermöglicht das Auslösen von Kartenzahlungen aus einer dedizierten Kassiereransicht, ohne die vollständige Laufzettel-Detailseite zu öffnen.

## Geräte-Detail (`/devices/{device_id}`)

Detailansicht eines einzelnen MQTT-Geräts.

Zeigt:

- Zeitstempel der letzten Aktivität
- NFC-Status (OK / Fehler)
- Aktuelle Nachrichten vom Gerät

## Mitgliederbereich (`/member`)

Self-Service-Bereich für Mitglieder mit einem Benutzerkonto mit `role="member"`.

Mitglieder können:

- ihre eigenen offenen und vergangenen Laufzettel einsehen
- Materialien zu ihrem offenen Laufzettel hinzufügen

Mitglieder können **keine** Zahlungen auslösen, Einträge löschen oder Daten anderer Mitglieder einsehen.

## Fehlerbericht-Formular (`/bug-report`)

Öffentliches Formular, das mit dem Plane-Issue-Tracker verknüpft ist. Jeder im lokalen Netzwerk kann einen Fehlerbericht einreichen. Erfordert die Konfiguration von `plane_url` und `plane_api_token`.

## Shopify-Seite (`/shopify`)

Integrationsseite für Shopify-Bestandsabfragen. Erfordert die Konfiguration von `shopify_store` und `shopify_access_token`.

## Buchhaltung (`/buchhaltung`)

Umsatz-Übersicht für Buchhaltungszwecke.

Zeigt: Umsatz aufgeschlüsselt nach Steuersatz (0 %, 7 %, 19 %), Spenden (is_spende-Materialien und manuelle Einträge), Filterung nach Zeitraum (Woche / Monat / Jahr).

Siehe [Buchhaltung](./22-accounting.md) für vollständige Dokumentation.

## Docs-Site

Die Docs-Site ist getrennt von der Haupt-UI und sollte auf Port `8001` laufen.

Die Haupt-UI kann als ausführliches Handbuch für Operatoren und Entwickler darauf verlinken.

