# Web-Oberfläche

Die MakerPi GroundControl-Web-Oberfläche ist für Desktop und Mobilgeräte optimiert.

## Hauptseiten

| Seite | URL | Zweck |
|-------|-----|-------|
| **Dashboard** | `/dashboard` | System-Status, aktive Geräte, letzte Nachrichten |
| **Login** | `/login` | Authentifizierung (benutzergesteuert) |
| **Tags** | `/tags` | NFC/RFID-Karten verwalten |
| **Laufzettel** | `/laufzettel` | Workshopeinträge und Materialverbrauch |
| **Katalog** | `/katalog` | Materialpreise und Kategorien |
| **Mitglieder** | `/mitglieder` | Workshop-Mitglieder verwalten |

## Seitenaufbau

Jede Seite folgt einem konsistenten Layout:

```
┌─────────────────────────────────────┐
│  Logo    Navigation        Aktionen │  ← Header
├─────────────────────────────────────┤
│                                     │
│         Seiteninhalt                │  ← Hauptbereich
│                                     │
└─────────────────────────────────────┘
```

## Navigation

Die Hauptnavigation ist oben rechts verfügbar:

- **Dashboard** – Zurück zur Hauptübersicht
- **Tags** – Karten verwalten
- **Laufzettel** – Workshopeinträge anzeigen/bearbeiten
- **Katalog** – Materialpreise konfigurieren
- **Mitglieder** – Personen verwalten

## Responsive Design

- **Desktop:** Volle Breite mit Seitenleisten
- **Tablet:** Angepasste Tabellen und Buttons
- **Mobil:** Kompakte Ansicht mit priorisierten Aktionen

## UI-Komponenten

### Buttons

| Stil | Verwendung |
|------|-----------|
| Primary (Blau) | Hauptaktionen (Speichern, Erstellen) |
| Secondary (Grau) | Sekundäre Aktionen (Abbrechen, Zurück) |
| Success (Grün) | Erfolgsaktionen (Zahlung, Abschluss) |
| Danger (Rot) | Destruktive Aktionen (Löschen) |

### Tabellen

- Sortierbar nach Datum/Name
- Filter nach Status (offen/bezahlt)
- Direkte Aktionen pro Zeile

### Formulare

- Validierung vor dem Absenden
- Hilfetexte bei komplexen Feldern
- Autovervollständigung wo sinnvoll

## Tastenkürzel

| Taste | Aktion |
|-------|--------|
| `/` | Suche fokussieren (wo verfügbar) |
| `Esc` | Modal schließen / Suche zurücksetzen |

## Fehlerbehandlung

- Klare Fehlermeldungen in Deutsch
- Keine technischen Details für Endnutzer
- Bestätigungsdialoge bei wichtigen Aktionen
