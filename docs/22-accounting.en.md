# 22 · Accounting

This page describes the accounting view in MakerPi GroundControl — an aggregated revenue summary grouped by tax rate, designed for the makerspace's monthly bookkeeping.

---

## Overview

The `/buchhaltung` page collects all completed work-order payments within a selected period and groups them by tax category. Revenue at 19 %, 7 %, and 0 % VAT, plus donations, are visible at a glance.

Data comes from two sources:

| Source | Table | What is recorded |
|---|---|---|
| Completed work orders | `buchhaltung.db → verkauf` | Every paid material line item (snapshot taken at payment time) |
| Manual donations | `buchhaltung.db → spende` | Donation amounts entered directly in the UI |

> **Important:** Rows in the `verkauf` table are only created when a Laufzettel is closed (i.e. paid). Open work orders do not appear in the report.

---

## The Accounting Page

Accessible at `/buchhaltung` after login. The page shows:

- **Period selector** – week, month (default), or year; navigate into past periods
- **Total revenue** (material sales + manual donations)
- **Breakdown by tax rate** – one block each for 19 %, 7 %, 0 %, catalog donations, and work-order donations
- **Individual donation entries** – list of all manually recorded donations in the period
- **Revenue by variant** – sorted by revenue descending

---

## Tax Rate Categories

The tax rate is configured on the material catalog entry (`MaterialUnterkategorie.tax_rate`) and snapshotted into `LaufzettelMaterial.tax_rate` and `Verkauf.tax_rate` at payment time. If no value is present, **19 % is used as fallback**.

| Tax rate | Meaning | Typical use |
|---|---|---|
| **19 %** | Standard rate | Standard materials, filament, consumables |
| **7 %** | Reduced rate | Food, certain cultural goods |
| **0 %** | Exempt | Non-profit services etc. |

### Configuring the tax rate

In the material catalog at `/katalog`:

1. Select a sub-category → Edit
2. Set the `tax_rate` field to `0`, `7`, or `19`
3. The new rate is applied automatically on the next work order

> **Note:** Completed work orders keep the tax rate that was active at payment time (snapshot). Catalog changes only affect future sales.

---

## Donations (Spenden)

The system distinguishes three types of donations:

### 1. Catalog donations (`spende_katalog`)

Material variants where `MaterialUnterkategorie.is_spende = true`. These appear as normal line items on a work order but are treated as donations on the accounting side (no taxable revenue, no VAT).

Configuration: mark the sub-category as "Spende" in the catalog.

### 2. Work-order donations (`spende_laufzettel`)

Free-form donation entries added directly to a work order without a catalog link (`variante_id = null`, `is_spende = true`).

### 3. Manual donations (`spende` table)

Cash donation amounts recorded directly on the accounting page (e.g. from a donation box). These do **not** flow into the sales statistics — they appear separately as `spende_total`.

**Recording a manual donation:**

```
POST /api/buchhaltung/spende
{
  "amount": 25.00,
  "donor_name": "Doe",              // optional
  "date": "2026-05-31T18:00:00",   // optional, defaults to now
  "notes": "Donation box receipt"  // optional
}
```

---

## Period Filter

| Period | Time window |
|---|---|
| `week` | Monday 00:00 UTC through Sunday 23:59 UTC of the week that contains `reference_date` |
| `month` | First of the month 00:00 UTC through last day 23:59 UTC |
| `year` | 1 January 00:00 UTC through 31 December 23:59 UTC |

The `reference_date` parameter (ISO 8601 string) shifts the window into the past without changing the period type. If omitted, the current timestamp is used.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/buchhaltung` | HTML page (login required) |
| `GET` | `/api/buchhaltung/summary` | Aggregated report for a time window (login required) |
| `GET` | `/api/buchhaltung/spenden-total` | Lightweight donations-only endpoint (login required) |
| `POST` | `/api/buchhaltung/spende` | Record a manual donation (login required) |
| `DELETE` | `/api/buchhaltung/spende/{id}` | Delete a manual donation (login required) |

### `GET /api/buchhaltung/summary`

**Query parameters:**

| Parameter | Type | Default | Values |
|---|---|---|---|
| `period` | string | `month` | `week`, `month`, `year` |
| `reference_date` | string (ISO 8601) | now | e.g. `2026-04-15` |

**Example response:**

```json
{
  "period": "month",
  "cutoff": "2026-05-01T00:00:00+00:00",
  "end": "2026-06-01T00:00:00+00:00",
  "material_total": 142.50,
  "spende_total": 25.00,
  "total": 167.50,
  "tax_totals": {
    "19": 120.00,
    "7": 15.00,
    "0": 7.50,
    "spende_katalog": 0.00,
    "spende_laufzettel": 0.00
  },
  "tax_groups": {
    "19": [ { "name": "PLA 1.75mm black", "revenue": 80.00, "tax_rate": 19.0, "units": 8.0, "pricing_model": "per_unit", "unit": "piece" } ],
    "7":  [ { "name": "Beverage", "revenue": 15.00, "tax_rate": 7.0, "units": 5.0, "pricing_model": "per_unit", "unit": "piece" } ],
    "0":  [],
    "spende_katalog": [],
    "spende_laufzettel": []
  },
  "by_variant": [ ... ],
  "spenden": [
    { "id": 3, "amount": 25.00, "donor_name": "Doe", "date": "2026-05-31T18:00:00+00:00", "notes": "Donation box" }
  ],
  "verkauf_count": 34,
  "spende_count": 1
}
```

### `GET /api/buchhaltung/spenden-total`

A lightweight public endpoint that returns only the donation totals for a period. Useful for dashboards, external integrations, or when you don't need the full accounting breakdown.

**Query parameters:**

| Parameter | Type | Default | Values |
|---|---|---|---|
| `period` | string | `month` | `week`, `month`, `year` |
| `reference_date` | string (ISO 8601) | now | e.g. `2026-04-15` |

**Example response:**

```json
{
  "spende_total": 789.00,
  "spende_count": 5,
  "period": "month",
  "cutoff": "2026-06-01T00:00:00+00:00",
  "end": "2026-07-01T00:00:00+00:00"
}
```

**Example usage:**

```bash
# Get this month's donations
curl "http://localhost:8000/api/buchhaltung/spenden-total?period=month"

# Get this week's donations
curl "http://localhost:8000/api/buchhaltung/spenden-total?period=week"

# Get donations for a specific month
curl "http://localhost:8000/api/buchhaltung/spenden-total?period=month&reference_date=2024-05-15"
```

> **Note:** This endpoint requires authentication.

### `POST /api/buchhaltung/spende`

Request body (JSON):

| Field | Type | Required | Description |
|---|---|---|---|
| `amount` | float | yes | Amount in EUR (must be > 0) |
| `donor_name` | string | no | Donor name |
| `date` | string (ISO 8601) | no | Date of donation; defaults to now |
| `notes` | string | no | Free-text note |

**Response:** The newly created `Spende` object as JSON.

**Errors:**
- `400` – `amount` is ≤ 0
- `401` – not authenticated

### `DELETE /api/buchhaltung/spende/{id}`

Deletes a manual donation entry by its ID.

**Response:** `{ "success": true }`

**Errors:**
- `401` – not authenticated
- `404` – ID not found

---

## Understanding the Numbers: Revenue vs. Donations

| Term | Definition | Source |
|---|---|---|
| **Revenue** (`material_total`) | Sum of all paid material prices in the period | `verkauf.calculated_price` (only `is_spende = false`) |
| **Donations** (`spende_total`) | Sum of all manually recorded donation amounts | `spende.amount` |
| **Total** (`total`) | `material_total + spende_total` | — |

> Catalog donations and work-order donations flow into `material_total` (they are part of work orders), but appear in their own buckets (`spende_katalog`, `spende_laufzettel`) and do **not** contribute to the taxable totals (19 / 7 / 0).

### Worked example

A member purchases the following items and pays cash:

| Item | Qty | Price | Tax rate | is_spende |
|---|---|---|---|---|
| PLA 1.75mm black | 1 | **€10.00** | 19 % | no |
| Donation box contribution | 1 | €5.00 | — | yes (work-order donation) |

After payment, the monthly report shows:

```
tax_totals.19                = €10.00   ← taxable revenue
tax_totals.spende_laufzettel =  €5.00   ← work-order donation, not taxable
material_total               = €15.00   ← both combined
spende_total                 =  €0.00   ← no manual donation in this example
total                        = €15.00
```

The €10.00 also appears under `tax_groups.19` as a variant entry and can be forwarded to the cash book. For VAT calculation: **€10.00 × 19/119 = €1.60 VAT** (gross method).

---

## Practical Admin Workflow: Month-End Closing

1. Open `/buchhaltung`, select period **Month**, navigate to the previous month
2. Read off **Revenue 19 %** → forward to cash book or tax advisor
3. Note **Revenue 7 %** and **0 %** separately (if applicable)
4. **Check donations:** verify manual donation entries are complete; add any missing entries via `POST /api/buchhaltung/spende`
5. **Catalog and work-order donations** should be reported separately (not taxable revenue)
6. Take a screenshot or export of the summary for your records

> **Tip:** The `by_variant` list shows which materials generated the most revenue — useful for reorder planning and price reviews.

---

## Database Details

| Table | Database | Contents |
|---|---|---|
| `verkauf` | `buchhaltung.db` | Snapshot of every paid material line: price, tax rate, `is_spende`, timestamp, payment method |
| `spende` | `buchhaltung.db` | Manually recorded donation amounts |

`verkauf` rows are created when a Laufzettel is closed (paid), copying data from `laufzettel_material`. Changes to the catalog after payment have **no effect** on already-booked line items.
