# Übersicht

**MakerPi GroundControl** ist eine webbasierte Steuerungs- und Monitoring-Software für Raspberry Pi, entwickelt für den Einsatz in Makerspaces und Werkstätten.

## Was es macht

- **Erfasst Workflows** über NFC/RFID-Karten (Laufzettel-System)
- **Zeichnet Gerätenutzung** auf (3D-Drucker, Laser, Fräsen, etc.)
- **Verfolgt Materialverbrauch** mit einem einfachen Katalog-System
- **Empfängt Sensordaten** über MQTT von Pico W und anderen Geräten
- **Bietet eine Web-Oberfläche** für Admins und Workshop-Besucher

## Wichtigste Konzepte

| Konzept | Beschreibung |
|---------|--------------|
| **Laufzettel** | Ein Datensatz pro Person/Tag mit Materialverbrauch und Zahlungsstatus |
| **Tags** | NFC/RFID-Karten, die Workshop-Mitgliedern zugewiesen sind |
| **Katalog** | Hierarchie: Standort → Kategorie → Variante (z.B. "3D-Druck" → "PLA" → "Weiß, 1kg") |
| **Geräte** | MQTT-fähige Geräte, die Status-Updates senden (automatisch erkannt) |

## Schnelle Navigation

- [Schnellstart](./01-quickstart) – In 5 Minuten zum Laufen bringen
- [Tags & Laufzettel](./03-tags-and-laufzettel) – Wie das NFC-System funktioniert
- [Material-Katalog](./04-material-katalog) – Preise und Verbrauch verwalten
- [System-Architektur](./05-system-architecture) – Komponenten und Datenfluss

## Für wen ist das gedacht?

- **Makerspace-Betreiber**, die eine einfache Methode zur Workshopeintragserfassung benötigen
- **Workshop-Verantwortliche**, die Materialverbrauch verfolgen möchten
- **Jeder mit einem Raspberry Pi**, der NFC-Kartenleser und MQTT-Sensoren betreiben möchte

## Minimal-Setup

1. Raspberry Pi mit Raspberry Pi OS
2. NFC-Reader (RC522) angeschlossen
3. Diese Software läuft auf Port 8000
4. Mosquitto MQTT Broker (optional, für Sensor-Daten)

Weiter zum [Schnellstart](./01-quickstart) für detaillierte Einrichtungsschritte.
