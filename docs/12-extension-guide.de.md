# Erweiterungs-Guide

Diese Seite beschreibt die aktuelle modulare Architektur und Richtlinien für Erweiterungen.

## Aktuelle Architektur

Das Backend ist nun als **modulare Monolith** organisiert – ein FastAPI-Prozess mit Domain-Modulen, die jeweils ihre eigene Datenbank besitzen:

```text
backend/
  main.py              # App-Factory, mounted alle Router
  config.py            # Gemeinsame Konfiguration
  docs_app.py          # Docs FastAPI-App
  auth/                # Nutzer, Login, Sessions
    models.py
    db.py
    routes.py
    dependencies.py
  members/             # Mitglieder + RFID-Tags
    models.py
    db.py
    routes.py
  laufzettel/          # Aufträge + Material-Tracking
    models.py
    db.py
    routes.py
  catalog/             # Material-Katalog
    models.py
    db.py
    routes.py
  core/                # MQTT, Geräte, Scans
    models.py
    db.py
    mqtt.py
    routes.py
```

## Stärken dieses Designs

- **Klare Grenzen** – jede Domäne besitzt ihre Daten und API
- **Unabhängige Datenbanken** – Module können Schema ändern ohne andere zu beeinflussen
- **Soft-Referenzen** – Cross-Modul-Links verwenden String-IDs, keine FK-Constraints
- **Single Deploy** – ein Prozess, kein Netzwerk-Overhead zwischen Modulen

## Neues Modul hinzufügen

Um eine neue Domäne hinzuzufügen (z.B. `inventory`):

1. **Erstelle `backend/inventory/`** mit `__init__.py`, `models.py`, `db.py`, `routes.py`
2. **Definiere deine Models** erbend von `declarative_base()`
3. **Erstelle Engine** mit `sqlite:///./inventory.db`
4. **Importiere und mounte Router** in `backend/main.py`
5. **Auth-Check hinzufügen** zu deinen Seiten-Routen mit `backend.auth.dependencies.check_auth`

## Cross-Modul-Referenzen

Wenn Modul A Daten von Modul B braucht:

- **Bevorzugt:** Speichere einen Soft-Key (z.B. `member_id` als String) und hole via API
- **Akzeptabel:** Importiere des anderen Moduls `SessionLocal` für read-only Queries
- **Vermeiden:** Direkte Cross-Modul-Schreibzugriffe – halte Transaktionen innerhalb einer DB

## Wann weiter aufteilen?

Erwäge Extraktion eines Services wenn:

- Ein Modul unabhängiges Scaling braucht
- Verschiedene Teams verschiedene Domänen besitzen
- Deploy-Rhythmen auseinanderlaufen
- Ein Modul einen anderen Datenbank-Typ braucht (Postgres, etc.)

## Dokumentations-Richtlinie

Wann immer du eines dieser Bereiche änderst, aktualisiere die Docs im selben PR/Change-Set:

- UI-Verhalten
- MQTT-Topic-Verträge
- DB-Schema
- Startup/Deploy-Anleitungen
- Material-Preisregeln
