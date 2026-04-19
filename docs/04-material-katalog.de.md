# Material-Katalog

Der **Katalog** speichert Materialpreise und ermöglicht automatische Preisberechnung beim Hinzufügen zu Laufzetteln.

## Hierarchie

```
Standort (z.B. "3D-Druck", "Laserschneiden")
  └── Kategorie (z.B. "PLA", "Acrylglas")
        └── Variante (z.B. "Weiß, 1kg", "3mm, transparent")
```

Jede **Kategorie** hat ein **Preismodell**, das bestimmt, wie der Preis berechnet wird:

| Preismodell | Berechnung | Beispiel |
|-------------|------------|----------|
| `pro_gramm` | Gewicht × Preis | 150g Filament |
| `pro_volumen_cm3` | L×B×H × Preis | Laser-Schnitt |
| `pro_stueck` | Anzahl × Preis | Schrauben, Bits |

## Katalog-Verwaltung

### Standorte

Standorte sind **Speicher-/Arbeitsbereiche** in deinem Workshop:

- **3D-Druck** – Drucker und Filamentlager
- **Laserschneiden** – Laserarbeitsplatz
- **Holzbearbeitung** – Werkstattbereich

### Kategorien

Jede Kategorie gehört zu einem Standort und hat:

- **Name** (z.B. "PLA", "Acrylglas 3mm")
- **Preismodell** (siehe Tabelle oben)
- **Einheit** (optional, für Anzeige)

### Varianten

Varianten sind **konkrete, preisgekrönte Optionen** innerhalb einer Kategorie:

```
Kategorie: "PLA"
├── Variante: "Weiß, 1kg" → 0.04 €/g
├── Variante: "Schwarz, 1kg" → 0.04 €/g
└── Variante: "Holz-Effekt, 500g" → 0.06 €/g
```

## Preisberechnung

Wenn Material zu einem Laufzettel hinzugefügt wird:

```
Katalog-Preis:      0.04 €/g
Gewicht:           150g
───────────────────────────
Gesamt:            6.00 €
```

Der berechnete Preis wird **eingefroren** – spätere Preisänderungen im Katalog wirken sich nicht auf bestehende Laufzettel aus.

## Seite: Katalog

Zugriff über `/katalog`.

### Oberfläche

```
┌─────────────────────────────────────────┐
│ 📍 3D-Druck              [+ Kategorie]  │  ← Standort
│ ─────────────────────────────────────── │
│ 🗂 PLA (pro Gramm)                      │  ← Kategorie
│ ─────────────────────────────────────── │
│ Variante              Preis      Akt.  │
│ ─────────────────────────────────────── │
│ Weiß, 1kg            0.04 €/g   [E][L] │  ← Varianten
│ Schwarz, 1kg         0.04 €/g   [E][L] │
└─────────────────────────────────────────┘
```

### Aktionen

| Aktion | Button | Beschreibung |
|--------|--------|--------------|
| Standort hinzufügen | `+ Standort` | Neuen Bereich erstellen |
| Kategorie hinzufügen | `+ Kategorie` | Preisgruppe erstellen |
| Variante hinzufügen | `+ Variante` | Konkrete Option erstellen |
| Bearbeiten | `Bearbeiten` | Name/Preis ändern |
| Löschen | `Löschen` | Element entfernen |

## API-Endpunkte

| Methode | Endpunkt | Beschreibung |
|---------|----------|--------------|
| `GET` | `/api/katalog` | Vollständiger Katalog-Tree |
| `GET` | `/api/katalog/locations` | Alle Standorte |
| `POST` | `/api/katalog/locations` | Standort erstellen |
| `GET` | `/api/katalog/kategorien` | Alle Kategorien |
| `POST` | `/api/katalog/kategorien` | Kategorie erstellen |
| `GET` | `/api/katalog/varianten` | Alle Varianten |
| `POST` | `/api/katalog/varianten` | Variante erstellen |

## Best Practices

1. **Klare Namen:** "PLA" statt "Filament Typ A"
2. **Konsistente Einheiten:** Immer Gramm für 3D-Druck, nicht gemischt
3. **Regelmäßige Updates:** Preise jährlich oder bei Lieferantenwechsel anpassen
4. **Kategorisierung:** Materialien am selben Standort gruppieren
