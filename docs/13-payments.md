# Payments

This page describes the payment integration on the Laufzettel detail page.

## Overview

Once a Laufzettel has material entries with a non-zero total, three payment buttons appear below the total row:

| Button | Method | What happens |
|---|---|---|
| **Bar bezahlen** | Cash | Shows total in a large pop-up. Operator confirms after receiving cash. |
| **mit Karte bezahlen** | SumUp card reader | Sends a checkout request to the paired SumUp terminal. Locks immediately on success. |

After any payment is confirmed:
- `payment_method` and `paid_at` are written to the Laufzettel record.
- A green **locked banner** replaces the payment buttons, showing method and timestamp.
- All edit actions (info fields, add/edit/delete material) are blocked in the UI **and** rejected by the API with `409 Conflict`.

> The lock is intentionally permanent — there is no unlock or undo flow.

---

## Configuration

Copy `config.json.example` to `config/config.json` (gitignored) and fill in the relevant keys:

```json
{
    "sumup_api_key": "sup_sk_...",
    "sumup_merchant_code": "XXXXXXXX",
    "sumup_reader_id": "your-reader-id",
    "sumup_mock": false
}
```

All values can also be provided as environment variables:

| Config key | Env var |
|---|---|
| `sumup_api_key` | `SUMUP_API_KEY` |
| `sumup_merchant_code` | `SUMUP_MERCHANT_CODE` |
| `sumup_reader_id` | `SUMUP_READER_ID` |

Config file values take precedence over environment variables.

---

## SumUp setup

### Get your credentials

1. Sign up or log in at [developer.sumup.com](https://developer.sumup.com).
2. Generate an API key (`sup_sk_...`) under **API Keys**.
3. Find your **Merchant Code** (8-character alphanumeric) under **Business > Account**.
4. Pair a Solo reader via the SumUp app or Cloud API. Then fetch the reader ID:

```bash
curl -H "Authorization: Bearer sup_sk_..." \
  "https://api.sumup.com/v0.1/merchants/MERCHANT_CODE/readers"
```

Copy the `id` field from the response into `sumup_reader_id`.

### Mock mode (no physical reader)

Set `"sumup_mock": true` in `config/config.json`. Card payments will:
- Skip the SumUp API call entirely.
- Lock the Laufzettel as if paid by card.
- Show **"(Mock-Modus – kein echtes Terminal)"** in the confirmation modal.

Switch to `false` and add a real `sumup_reader_id` when hardware is available.

### Important SumUp notes

- The target reader must be **online** when the checkout is sent.
- SumUp gives **60 seconds** to start the transaction on the device after a checkout is accepted.
- Only one active checkout per reader at a time.

---

## API endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/payment/config` | Returns configured flags (no secrets exposed) |
| `POST` | `/api/laufzettel/{id}/pay/bar` | Mark as cash-paid, lock |
| `POST` | `/api/laufzettel/{id}/pay/karte` | Initiate SumUp checkout, lock on success |

### `GET /api/payment/config` response

```json
{
    "sumup_configured": true,
    "sumup_mock": false
}
```

The frontend uses this to show/hide the **Karte** button (hidden if `sumup_configured` is false).

---

## Lock behaviour

Once `payment_method` is set on a Laufzettel, the following API endpoints return `409 Conflict`:

- `PUT /api/laufzettel/{id}` (edit info fields)
- `POST /api/laufzettel/{id}/material` (add material)
- `PUT /api/laufzettel/{id}/material/{mid}` (edit material)
- `DELETE /api/laufzettel/{id}/material/{mid}` (delete material)
- Any subsequent `POST /api/laufzettel/{id}/pay/*`

The UI enforces the same: edit and add buttons are hidden, table action buttons are visually disabled.
