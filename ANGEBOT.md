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
| Repo aufsetzen + Webserver initial einrichten | 8h | Git-Setup, FastAPI-Struktur, Deployment-Scripts |
| NFC-Hardware + Pico W Integration | 10h | Pico W Firmware, MQTT-Verbindung, NFC-Reader-Treiber |
| Hardware-Aufbau & Installation | 10h | Kabelverlegung, Montage, Netzwerk, Stromversorgung |
| Gehäuse-Design | 4h | 3D-Modelle, Druck, Montage |
| **Subtotal Phase 1** | **32h** | |

### Phase 2: Backend-Systeme

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Authentifizierungssystem | 6h | User-Management, bcrypt-Passwords, Sessions |
| MQTT-Broker Integration | 4h | Mosquitto-Setup, Subscriber, Device-Discovery |
| Multi-Database Architektur | 6h | 7 SQLite-DBs, WAL-Mode, Integritäts-Monitoring |
| easyVerein API-Integration | 6h | Member-Sync (täglich), API-Wrapper, Upsert-Logik |
| API-Scheduler (APScheduler) | 3h | Background-Jobs, Cron-Trigger |
| **Subtotal Phase 2** | **25h** | |

### Phase 3: Laufzettel-System (Kernfunktionalität)

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Laufzettel CRUD API | 5h | Erstellen, Lesen, Aktualisieren |
| Auto-Erstellung bei NFC-Scan | 3h | MQTT-Handler, Member-Lookup |
| Material-Tracking pro Laufzettel | 4h | LaufzettelMaterial-Model, Mengenberechnung |
| Zahlungssystem | 6h | SumUp Solo, Payment Switch, Bar-Zahlung |
| PDF-Generierung & E-Mail | 5h | Receipt-PDF, E-Mail-Templates |
| Google Drive Integration | 3h | OAuth-Setup, PDF-Upload |
| Gast-Laufzettel (Public) | 3h | QR-Code, E-Mail-Suche |
| **Subtotal Phase 3** | **29h** | |

### Phase 4: Materialkatalog

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| 4-Level Hierarchie | 5h | Location → Kategorie → Unterkategorie → Variante |
| CSV-Bulk-Import | 3h | Parser, Validation, Batch-Insert |
| Pricing-Models | 4h | per_unit, per_gram, per_volume, per_minute |
| Frontend-Katalog-UI | 5h | Tree-View, Filter, CRUD-Forms |
| **Subtotal Phase 4** | **17h** | |

### Phase 5: Frontend & User Interfaces

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Admin-Dashboard | 5h | Stats-Overview, Health-Check |
| Laufzettel-List & Detail | 6h | Table, Filter, Modal-Forms |
| Member-Portal | 6h | Eigene Laufzettel, Konto-Übersicht |
| Gast-Landing Page | 2h | Public Form, QR-Scan |
| Responsive Design | 4h | Mobile-First, Touch-Optimized |
| PWA-Service Worker | 3h | Offline-Fallback, Cache-Strategie |
| **Subtotal Phase 5** | **26h** | |

### Phase 6: Sicherheit & Features

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| NFC-Signatur-Sicherheit | 4h | HMAC-SHA256, Card-Writer, Verifikation |
| RFID-Tag-Management | 3h | Tag CRUD, Card-Writer Integration |
| Web Push Notifications | 3h | VAPID-Keys, Push-Subscription |
| Shopify Gift Cards | 2h | API-Integration, Balance-Tracking |
| Buchhaltung (Accounting) | 3h | Spenden, Verkauf, Reports |
| Plane Bug-Report | 2h | Docker, Form-Integration |
| **Subtotal Phase 6** | **17h** | |

### Phase 7: Deployment & Dokumentation

| Aufgabe | Zeit | Beschreibung |
|---------|------|--------------|
| Pi-Setup-Scripts | 3h | Mosquitto, Docker, systemd |
| DB-Integrity Monitoring | 2h | Cron-Job, Auto-Recovery |
| Deployment-Workflow | 2h | Git-Deploy, Update-Deps |
| Dokumentation-Site | 6h | Markdown-Dokumente, FastAPI-Docs-App |
| **Subtotal Phase 7** | **13h** | |

---

## Zusammenfassung

| Kategorie | Stunden |
|-----------|---------|
| Phase 1: Infrastruktur & Setup | 32h |
| Phase 2: Backend-Systeme | 25h |
| Phase 3: Laufzettel-System | 29h |
| Phase 4: Materialkatalog | 17h |
| Phase 5: Frontend & UI | 26h |
| Phase 6: Sicherheit & Features | 17h |
| Phase 7: Deployment & Docs | 13h |
| **Gesamtstunden** | **159h** |

### Implementierte Features

**Authentifizierung:**
- Admin-Login (bcrypt)
- Member-Login (easyVerein-Sync oder lokal)
- RFID-Login (NFC-Tap)
- Admin-Verifikation (10-min Timeout)

**Laufzettel-System:**
- Automatische Erstellung bei NFC-Scan
- Manuelles Erstellen/Admin-UI
- Material-Tracking pro Laufzettel
- Zahlungssperre nach Bezahlung
- PDF-Receipts
- E-Mail-Versand
- Google Drive-Ablage

**Zahlungsintegration:**
- SumUp Solo Cloud API (Kartenterminal)
- Payment Switch (Deep-Link)
- Wero
- Barzahlung

**Materialkatalog:**
- 4-Level Hierarchie
- 5 Pricing-Models
- CSV-Bulk-Import

**Mitgliederverwaltung:**
- easyVerein API-Sync (täglich 03:00)
- NFC-Tag-Management
- HMAC-Signatur-Sicherheit
- Card-Writer Integration

**Self-Service:**
- Member-Portal (eigene Laufzettel, Konto)
- Gast-Laufzettel (Public + QR-Code)

**Monitoring & DevOps:**
- MQTT-Monitoring (Devices, Messages)
- DB-Integrity-Check (stündlich)
- Auto-Deploy-Timer
- Health-Check-Endpoints

**Extras:**
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
| Arbeitszeit (159h × 85€/h) | 13.515,00 € |
| **Gesamtbetrag (brutto)** | **13.936,75 €** |

**Hinweis:** Alle Preise verstehen sich gemäß Kleinunternehmerregelung (§ 19 UStG) brutto. Eine gesonderte Ausweisung von Umsatzsteuer erfolgt nicht.

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