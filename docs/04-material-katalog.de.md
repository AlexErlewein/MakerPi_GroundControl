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
| **Bulk Import** | **`⬆ Bulk Import`** | **Viele Einträge auf einmal hinzufügen** |

## Bulk Import

Der **„⬆ Bulk Import"**-Button (oben rechts auf der Katalog-Seite) erlaubt es, viele Einträge auf einmal anzulegen, ohne jeden Schritt einzeln durchklicken zu müssen. Es gibt zwei Modi.

### Browser-Eingabe

1. **⬆ Bulk Import** klicken → Modal öffnet sich auf dem Tab **Eingabe**.
2. Einen vorhandenen **Standort** aus der Dropdown-Liste wählen oder *„Neuen Standort erstellen"* auswählen und einen Namen eingeben.
3. **+ Kategorie hinzufügen** klicken. Für jede Kategorie ausfüllen:
   - Name
   - Preismodell (`per_unit`, `per_gram`, `per_volume_cm3`, `per_volume_l`, `per_minute`)
   - Einheit (optionale Anzeige-Einheit, z.B. `g`, `cm³`)
   - Steuersatz (0 / 7 / 19 %)
4. Mit **+ Variante** beliebig viele Varianten pro Kategorie anlegen (Name und Preis).
5. So viele Kategorien und Varianten hinzufügen wie nötig.
6. **Alles speichern** klicken – alle Einträge werden in einer einzigen atomaren Datenbank-Transaktion gespeichert.

> Existiert ein Standort mit dem eingegebenen Namen bereits, wird er wiederverwendet – nie doppelt angelegt.

### CSV-Import

1. **⬆ Bulk Import** klicken → Tab **CSV Import** auswählen.
2. Eine `.csv`-Datei vom Computer auswählen.
3. Die Datei wird **im Browser** geparst – es werden noch keine Daten übertragen.
4. Eine Vorschau-Tabelle zeigt die gruppierten Daten.
5. **CSV importieren** klicken, um alles in die Datenbank zu schreiben.

#### CSV-Format

Die Datei muss eine Kopfzeile mit genau diesen Spaltennamen haben (Reihenfolge fest):

```
standort,kategorie,preismodell,einheit,steuersatz,variante,preis
```

| Spalte | Pflicht | Werte / Hinweise |
|--------|---------|------------------|
| `standort` | ja | Name des Standorts |
| `kategorie` | ja | Name der Kategorie |
| `preismodell` | ja | `per_unit` · `per_gram` · `per_volume_cm3` · `per_volume_l` · `per_minute` |
| `einheit` | nein | Anzeige-Einheit, z.B. `g`, `cm³` – leer lassen wenn nicht benötigt |
| `steuersatz` | ja | `0`, `7` oder `19` |
| `variante` | ja | Name der Variante |
| `preis` | ja | Preis pro Einheit, Dezimalpunkt (kein Komma), z.B. `0.05` |

Mehrere Zeilen mit demselben `standort + kategorie + preismodell + einheit + steuersatz` werden zu einer Kategorie mit mehreren Varianten zusammengefasst.

#### Beispiel

```csv
standort,kategorie,preismodell,einheit,steuersatz,variante,preis
Töpferei,Ton,per_gram,g,19,fein,0.05
Töpferei,Ton,per_gram,g,19,grob,0.03
Töpferei,Glasur,per_unit,Stück,19,transparent,2.50
Holz-Werkstatt,Holz,per_volume_cm3,cm³,19,Eiche,0.0012
Holz-Werkstatt,Holz,per_volume_cm3,cm³,19,Altholz,0.0004
FabLab,Filament,per_gram,g,19,PLA,0.02
FabLab,Filament,per_gram,g,19,PETG,0.025
```

Dieses Beispiel erstellt:
- **Töpferei** → Ton (per_gram, 2 Varianten) + Glasur (per_unit, 1 Variante)
- **Holz-Werkstatt** → Holz (per_volume_cm3, 2 Varianten)
- **FabLab** → Filament (per_gram, 2 Varianten)

Eine größere, direkt einsatzbare Beispieldatei liegt im Repository unter `examples/katalog-bulk-import.csv`.

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
| `POST` | `/api/katalog/bulk-import` | Standort + Kategorien + Varianten auf einmal anlegen |

## Best Practices

1. **Klare Namen:** "PLA" statt "Filament Typ A"
2. **Konsistente Einheiten:** Immer Gramm für 3D-Druck, nicht gemischt
3. **Regelmäßige Updates:** Preise jährlich oder bei Lieferantenwechsel anpassen
4. **Kategorisierung:** Materialien am selben Standort gruppieren
