# Angebot: Digitalisierung Laufzettel – H3cke MakerSpace

## Projektübersicht

Komplettes RFID-basiertes Work-Order-Tracking-System für einen Makerspace mit automatischer Laufzettel-Erstellung, Materialkatalog, Zahlungsabwicklung, Mitgliederverwaltung und Web-Interface.

**Technologie-Stack:**
- Backend: FastAPI (Python)
- Frontend: HTML/CSS/JavaScript (responsive)
- Datenbank: SQLite (7 modulare DBs)
- MQTT: Mosquitto Broker
- Hardware: Raspberry Pi Compute Module 4 + 15x NFC-Reader + 15x Pico W
- PWA-Unterstützung mit Offline-Funktionalität

---

## Hardware-Kosten

| Artikel | Menge | Preis (brutto) | Gesamt |
|---------|-------|----------------|--------|
| Raspberry Pi Compute Module 4GB | 1 | 196,00 € | 196,00 € |
| NFC-Reader (PN532) | 15 | 6,55 € | 98,25 € |
| Raspberry Pico W | 15 | 8,50 € | 127,50 € |
| **Hardware-Total** | | | **421,75 €** |

---

## Implementierungszeit (Arbeitsstunden)

### Phase 1: Infrastruktur & Setup

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Repo aufsetzen + Webserver initial einrichten | 12h | Git-Setup, FastAPI-Struktur,Deployment-Scripts, Monitoring |
| NFC-Hardware + Pico W Integration | 12h | Pico W Firmware, MQTT-Verbindung, NFC-Reader-Treiber |
| Hardware-Aufbau & Installation | 15h | Kabelverlegung, Montage, Netzwerk, Stromversorgung |
| Gehäuse-Design | 5h | 3D-Modelle, Druck, Montage |
| **Subtotal Phase 1** | **44h** | |

### Phase 2: Backend-Systeme

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Authentifizierungssystem | 8h | User-Management, bcrypt-Passwords, Sessions, Admin-Escalation |
| MQTT-Broker Integration | 6h | Mosquitto-Setup, Subscriber, Device-Discovery, Tag-Scan-Handling |
| Multi-Database Architektur | 8h | 7 SQLite-DBs, WAL-Mode, Integritäts-Monitoring, Backup-Scripts |
| easyVerein API-Integration | 8h | Member-Sync (täglich 03:00), API-Wrapper, Upsert-Logik |
| API-Scheduler (APScheduler) | 4h | Background-Jobs, Cron-Trigger, Health-Checks |
| **Subtotal Phase 2** | **34h** | |

### Phase 3: Laufzettel-System (Kernfunktionalität)

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Laufzettel CRUD API | 8h | Erstellen, Lesen, Aktualisieren, JSON-Schema |
| Auto-Erstellung bei NFC-Scan | 6h | MQTT-Handler, Member-Lookup, Validierung |
| Material-Tracking pro Laufzettel | 8h | LaufzettelMaterial-Model, Mengenberechnung |
| Zahlungssystem | 12h | SumUp Solo API, Payment Switch (Deep-Link), Wero, Bar-Zahlung, Mock-Mode |
| PDF-Generierung & E-Mail | 8h | Receipt-PDF, HTML-to-PDF, Gmail OAuth, E-Mail-Templates |
| Google Drive Integration | 8h | OAuth-Setup, PDF-Upload, Ordnerstruktur (Jahr/Monat) |
| Gast-Laufzettel (Public) | 8h | QR-Code, E-Mail-Suche, Captcha-Schutz |
| **Subtotal Phase 3** | **58h** | |

### Phase 4: Materialkatalog

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| 4-Level Hierarchie | 8h | Location → Kategorie → Unterkategorie → Variante |
| CSV-Bulk-Import | 4h | Parser, Validation, Batch-Insert |
| Pricing-Models | 6h | per_unit, per_gram, per_volume_cm3, per_volume_l, per_minute |
| Frontend-Katalog-UI | 8h | Tree-View, Filter, Search, CRUD-Forms |
| **Subtotal Phase 4** | **26h** | |

### Phase 5: Frontend & User Interfaces

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Admin-Dashboard | 8h | Stats-Overview, Health-Check, Device-Monitoring |
| Laufzettel-List & Detail | 10h | Table, Filter, Modal-Forms, Live-Updates (SSE) |
| Member-Portal | 12h | Eigene Laufzettel, Konto-Übersicht, Profil-Edit, Open-LZ-Management |
| Gast-Landing Page | 4h | Public Form, QR-Scan, Responsive |
| Responsive Design | 8h | Mobile-First, Touch-Optimized, Dark/Light-Theme |
| PWA-Service Worker | 6h | Offline-Fallback, Cache-Strategie, Install-Prompt |
| **Subtotal Phase 5** | **48h** | |

### Phase 6: Sicherheit & Features

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| NFC-Signatur-Sicherheit | 8h | HMAC-SHA256, Signatur-Generierung (Card-Writer), Verifikation, Anti-Clone |
| RFID-Tag-Management | 6h | Tag CRUD, Card-Writer Integration, Permissive/Strict-Mode |
| Web Push Notifications | 8h | VAPID-Keys, Push-Subscription, Notifications |
| Shopify Gift Cards | 4h | API-Integration, Balance-Tracking |
| Buchhaltung (Accounting) | 6h | Spenden, Verkauf, Period-Reports (Woche/Monat/Jahr) |
| Plane Bug-Report | 4h | Self-hosted Docker, Form-Integration |
| **Subtotal Phase 6** | **36h** | |

### Phase 7: Deployment & Dokumentation

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Pi-Setup-Scripts | 6h | Mosquitto, Docker, systemd, Auto-Deploy-Timer |
| DB-Integrity Monitoring | 4h | Cron-Job, Auto-Recovery (REINDEX, Dump/Reload) |
| Deployment-Workflow | 4h | Git-Deploy, Update-Deps, Rollback |
| Dokumentation-Site | 12h | Markdown-Dokumente, FastAPI-Docs-App, Multilang (DE/EN) |
| **Subtotal Phase 7** | **26h** |

---

## Zusammenfassung

| Kategorie | Stunden |
|-----------|---------|
| Phase 1: Infrastruktur & Setup | 44h |
| Phase 2: Backend-Systeme | 34h |
| Phase 3: Laufzettel-System | 58h |
| Phase 4: Materialkatalog | 26h |
| Phase 5: Frontend & UI | 48h |
| Phase 6: Sicherheit & Features | 36h |
| Phase 7: Deployment & Docs | 26h |
| **Gesamtstunden** | **272h** |

### Implementierte Features (Lieferscope)

✅ **Authentifizierung:**
- Admin-Login (bcrypt)
- Member-Login (easyVerein-Sync oder lokal)
- RFID-Login (NFC-Tap)
- Admin-Verifikation (10-min Timeout)

✅ **Laufzettel-System:**
- Automatische Erstellung bei NFC-Scan
- Manuelles Erstellen/Admin-UI
- Material-Tracking pro Laufzettel
- Zahlungssperre nach Bezahlung
- PDF-Receipts
- E-Mail-Versand
- Google Drive-Ablage

✅ **Zahlungsintegration:**
- SumUp Solo Cloud API (Kartenterminal)
- Payment Switch (Deep-Link)
- Wero
- Barzahlung

✅ **Materialkatalog:**
- 4-Level Hierarchie
- 5 Pricing-Models
- CSV-Bulk-Import

✅ **Mitgliederverwaltung:**
- easyVerein API-Sync (täglich 03:00)
- NFC-Tag-Management
- HMAC-Signatur-Sicherheit
- Card-Writer Integration

✅ **Self-Service:**
- Member-Portal (eigene Laufzettel, Konto)
- Gast-Laufzettel (Public + QR-Code)

✅ **Monitoring & DevOps:**
- MQTT-Monitoring (Devices, Messages)
- DB-Integrity-Check (stündlich)
- Auto-Deploy-Timer
- Health-Check-Endpoints

✅ **Extras:**
- Shopify Gift Cards
- Buchhaltung (Spenden/Verkauf)
- Web Push Notifications
- PWA mit Offline-Mode
- Dokumentation-Site (DE/EN)
- Plane Bug-Report-Integration

---

## Gesamtkosten

| Position | Betrag |
|----------|--------|
| Hardware (Material) | 421,75 € |
| Arbeitszeit (272h × 85€/h) | 23.120,00 € |
| **Gesamt netto** | 23.541,75 € |
| **+ 19% MwSt** | 4.472,93 € |
| **Gesamt brutto** | **28.014,68 €** |

---

## Laufzeit & Meilensteine

| Meilenstein | Dauer |
|-------------|-------|
| Phase 1-2: Infrastruktur & Backend | 3 Wochen |
| Phase 3: Laufzettel-System (Kern) | 2 Wochen |
| Phase 4-5: Katalog & Frontend | 2 Wochen |
| Phase 6-7: Features & Deployment | 2 Wochen |
| **Gesamtprojektzeit** | **9 Wochen** |

---

## Wartung & Support (Optional)

| Paket | Inklusiv | Preis/Monat |
|-------|----------|-------------|
| Basic | Bugfixes, Updates | 200 € |
| Premium | + Feature-Requests, Priority-Support | 350 € |

---

## Projektstatus

**Status:** ✅ Vollständig implementiert und in Betrieb

Das System ist produktiv auf einem Raspberry Pi Compute Module 4 installiert mit:
- 15x NFC-Readern an verschiedenen Standorten
- Echtzeit-MQTT-Verbindung zu Pico W-Geräten
- 7 modularen SQLite-Datenbanken
- Automated Member-Sync aus easyVerein
- Web-Interface (http://<pi-ip>:8000)
- Dokumentation-Site (http://<pi-ip>:8001)

---

**Datum:** 28. Mai 2026
**Projekt:** H3cke MakerSpace – Digitalisierung Laufzettel
**Anbieter:** MakerPi Solutions