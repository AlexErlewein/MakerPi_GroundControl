# GroundControl Übersicht

MakerPi GroundControl ist das zentrale Web- und Datenbanksystem für die Verwaltung von MQTT-verbundenen Werkstattgeräten, RFID-Tags, Laufzettel (Nutzungsaufzeichnungen) und Materialverfolgung.

## Wie das System zusammenhängt

```mermaid
graph LR
    subgraph Workshop
        D1["🖥 Pico W #1\n(NFC-Leser)"]
        D2["🖥 Pico W #2\n(Sensor-Knoten)"]
    end
    subgraph Server["Raspberry Pi / Server"]
        MB["Mosquitto\nBroker :1883"]
        GC["GroundControl\nFastAPI :8000"]
        DB["SQLite DB\ngroundcontrol.db"]
        DOCS["Docs Site\nFastAPI :8001"]
    end
    subgraph Operator
        UI["🌐 Web-Browser"]
    end
    D1 & D2 -->|"MQTT publish"| MB
    MB -->|"paho-mqtt subscribe"| GC
    GC <-->|"SQLAlchemy"| DB
    GC -->|"HTML/JSON"| UI
    DOCS -->|"Markdown"| UI
```

## Wichtige benutzerseitige Konzepte

### Geräte

Ein Gerät ist ein Pico W oder jeder MQTT-sprechende Knoten, der Status- oder Sensordaten veröffentlicht. Geräte werden automatisch aus MQTT-Topics entdeckt und im Dashboard angezeigt.

### RFID-Tags

Ein registrierter NFC-Tag, optional mit einem Mitglied (Mitglied) über `member_id` verknüpft.

| Feld | Beschreibung |
|---|---|
| `uid` | Hardware-UID vom NFC-Tag |
| `member_id` | Soft-Referenz zu `mitglieder.member_id` |
| `owner_name` | Name des Karteninhabers |
| `owner_email` | E-Mail-Adresse |
| `active` | Ob Scans akzeptiert werden |
| `is_admin` | Wenn true, gewährt Admin-Zugriff via RFID-Login |
| `notes` | Freitext-Notizen |

### Laufzettel

Ein **Laufzettel** ist ein tagesspezifischer Nutzungsaufzeichnung. Er wird automatisch erstellt, wenn ein bekannter Tag oder Mitglied an einem bestimmten Tag zum ersten Mal scannt. Nicht-Mitglieder können auch einen Laufzettel erstellen, indem sie einen QR-Code scannen.

| Feld | Beschreibung |
|---|---|
| `uid` | Tag-UID (Legacy-Verknüpfung) |
| `date` | Nutzungsdatum |
| `start` | Erste Scan-Zeit |
| `owner_name` | Zum Zeitpunkt des Scans aus Tag kopiert |
| `member_id` | Zum Zeitpunkt des Scans aus Tag kopiert (Legacy) |
| `mitglied_id` | FK zu `mitglieder.id` — bevorzugte Verknüpfung |
| `guest_id` | UUID für Gast-Sitzungen (Nicht-Mitglieder) |
| `guest_email` | Optionale E-Mail für Gäste |
| `nodes` | Liste der besuchten Geräte/Stationen |

### Materialeinträge

Material wird auf einem Laufzettel in zwei Modi erfasst:

| Modus | Wann verwenden |
|---|---|
| **Sonstiges** | Schnelle einmalige Eingabe, kein Katalog benötigt |
| **Aus Katalog** | Katalog-basierte Eingabe mit automatischer Preisberechnung |

### Materialkatalog

```mermaid
graph TD
    L["📍 Standort\ne.g. Töpferei"] --> K["🗂 Kategorie\ne.g. Ton"]
    K --> U1["📁 Unterkategorie: Rot\npricing: per_gram\nunit: g\ntax: 19%"]
    K --> U2["📁 Unterkategorie: Weiß\npricing: per_gram\nunit: g\ntax: 19%"]
    U1 --> V1["🔷 Variante: fein\n0,05 €/g"]
    U1 --> V2["🔷 Variante: grob\n0,03 €/g"]
    U2 --> V3["🔷 Variante: weiß-fein\n0,04 €/g"]
    L2["📍 Holz-Werkstatt"] --> K2["🗂 Holz"]
    K2 --> U3["📁 Unterkategorie: Hartholz\npricing: per_volume_cm3\nunit: cm³\ntax: 19%"]
    U3 --> V4["🔷 Eiche\n0,12 €/cm³"]
    U3 --> V5["🔷 Esche\n0,09 €/cm³"]
```

## Typischer Operator-Workflow

```mermaid
flowchart LR
    A["Dashboard öffnen\n/ "] --> B["Geräte prüfen\nsind online"]
    B --> C["Tags registrieren\n/tags"]
    C --> D["Tag im Workshop\nbenutzt"]
    D -->|"automatisch"| E["Laufzettel\nerstellt"]
    D -->|"manueller Fallback"| E
    E --> F["Überprüfen & bearbeiten\n/laufzettel/id"]
    F --> G["Material hinzufügen\n(Sonstiges oder Katalog)"]
    G --> H["Fertig ✓"]
```

## Wichtige Seiten

| URL | Zweck |
|---|---|
| `/` | Dashboard — Geräte-Status, aktuelle Nachrichten, System-Health |
| `/database` | Nachrichtenverlauf und DB-Statistiken |
| `/tags` | RFID-Tag-Administration |
| `/laufzettel` | Laufzettel-Liste und manuelle Erstellung |
| `/laufzettel/{id}` | Laufzettel-Details und Material-Bearbeitung |
| `/katalog` | Materialkatalog-Verwaltung |
| `/register` | Öffentliches Mitglied-Registrierungsformular |
| `/guest/laufzettel` | Gast-Eingabeformular für Nicht-Mitglieder (QR-Code) |
| `/buchhaltung` | Umsatz-Übersicht nach Steuersatz und Spenden |
| `/kasse` | Kassenseite für Kartenzahlung und RFID-Login |
| `/admin/device-pairings` | Gerätekopplungen verwalten |

## Ports auf einen Blick

| Service | Port | URL |
|---|---|---|
| Haupt-App | 8000 | `http://localhost:8000` |
| Docs-Site | 8001 | `http://localhost:8001` |
| MQTT-Broker | 1883 | `localhost:1883` |
| Zigbee2MQTT (nur Pi) | 8090 | `http://localhost:8090` |

## Wohin als Nächstes

- [Schnellstart](./01-quickstart.de.md) — In 2 Minuten zum Laufen bringen
- [Web-UI Guide](./02-web-ui.de.md) — Was jede Seite tut
- [Tags und Laufzettel](./03-tags-and-laufzettel.de.md) — Kern-User-Workflow im Detail
- [Gast-Laufzettel](./17-guest-laufzettel.de.md) — Nicht-Mitglied-Nutzung über QR-Code
- [Mitglied-Registrierung](./19-member-registration.de.md) — Öffentliche Mitglied-Anmeldung und easyVerein-Integration
- [Konfigurationsreferenz](./18-configuration-reference.de.md) — Alle Konfigurationsschlüssel, wo man API-Zugangsdaten bekommt
- [Gerätekopplung](./20-device-pairing.de.md) — NFC-Lesegeräte koppeln und Rollen zuweisen
- [Shopify-Gutscheine](./21-shopify-gift-cards.de.md) — Gutschein-Verwaltung und Laufzettel-Zahlung
- [Buchhaltung](./22-accounting.de.md) — Umsatz nach Steuersatz, Spenden
- [Kasse & RFID-Login](./24-kasse.de.md) — Kassenseite und kartenbasierter Login
- [Changelog](./CHANGELOG.md) — Änderungen und neue Funktionen
