# Guest Laufzettel (Non-Member Usage)

## Overview

The guest Laufzettel feature allows non-members to create a Laufzettel by scanning a QR code with their smartphone. This enables visitors to the makerspace to track their material usage without requiring an RFID tag or member account.

## QR Code Files

Two QR code files are available in the project root directory:
- `guest-laufzettel-qr.png` - PNG format (raster)
- `guest-laufzettel-qr.svg` - SVG format (vector)

Both files use the Corporate Identity accent color (#d04417 - orange-red) for the QR code foreground.

### QR Code Preview

![Guest Laufzettel QR Code (PNG)](/guest-laufzettel-qr.png)

The QR code shown above links to:
```
http://192.168.3.228:8000/guest/laufzettel
```

## QR Code URL

The QR code points to:
```
http://192.168.3.228:8000/guest/laufzettel
```

**Note**: Update the IP address (192.168.3.228) to match your actual Raspberry Pi IP address before printing/displaying the QR code.

## How It Works

1. **Scanning the QR Code**: When a guest scans the QR code, they are redirected to the guest Laufzettel form page.

2. **Form Submission**: The guest fills in:
   - Name (required)
   - Email (optional)
   - Date and time (auto-filled)
   - Clicks "Fertig" to submit

3. **Laufzettel Creation**: A new Laufzettel is created with:
   - A unique guest ID (UUID, stored in a browser cookie)
   - A generated UID (format: GUEST-XXXXXX)
   - The provided name and email

4. **Material Tracking**: The guest can then:
   - Add materials to their Laufzettel
   - Add donations (Spende)
   - View their material usage
   - Cannot initiate payment themselves

5. **Session Persistence**: The guest session cookie persists until the Laufzettel is paid. If they rescan the QR code on the same day, they will see their existing Laufzettel.

6. **Previous Day Reminder**: If they rescan on a new day with an unpaid Laufzettel from a previous day, a reminder popup will appear.

7. **Payment**: Guests tell an admin their name, and the admin can:
   - Find the Laufzettel using the name filter on the `/laufzettel` page
   - Process payment manually
   - Mark the Laufzettel as paid

## Session Management (API Endpoints)

### Session Check: `GET /api/guest/session-check`

Checks whether the browser already has an active guest session (i.e. whether a `guest_id` cookie is set).

**Response (active session):**
```json
{ "guest_id": "550e8400-e29b-41d4-a716-446655440000" }
```

**Response (no session):**
```json
{ "guest_id": null }
```

The frontend uses this endpoint when loading the form page to decide whether to show a new form or redirect directly to the existing Laufzettel.

---

### Fetch Today's Laufzettel: `GET /api/guest/laufzettel/{guest_id}`

Returns the current **unpaid** Laufzettel for the guest for **today**.

**Path parameter:** `guest_id` — the UUID from the session cookie.

**Success response (200):**
```json
{
  "id": 42,
  "uid": "GUEST-A3F9C1",
  "date": "2026-06-03",
  "owner_name": "Jane Smith",
  "guest_email": "jane@example.com",
  "payment_method": null,
  "material": [...]
}
```

**Error (404):** No unpaid Laufzettel found for today.

---

### Check for Previous Unpaid Orders: `GET /api/guest/laufzettel/{guest_id}/previous`

Checks whether the guest has an **unpaid Laufzettel from an earlier day** (date strictly before today).

**Path parameter:** `guest_id` — the UUID from the session cookie.

**Response (found):**
```json
{
  "has_previous_unpaid": true,
  "laufzettel": {
    "id": 37,
    "date": "2026-06-01",
    "owner_name": "Jane Smith",
    ...
  }
}
```

**Response (none found):**
```json
{ "has_previous_unpaid": false }
```

When `has_previous_unpaid` is `true`, the frontend displays a notice popup informing the guest that an open balance from a previous visit still exists.

## Carry-Forward of Unpaid Orders

When a guest opens the form page on a new day and still has an unpaid Laufzettel from a previous day, the following flow runs:

1. The frontend calls `GET /api/guest/laufzettel/{guest_id}/previous` to check for an older open Laufzettel.
2. If one exists, a popup appears showing the date and amount of the old Laufzettel.
3. The guest is asked to settle the outstanding amount with an admin.
4. A new Laufzettel for the current day can then be created.

**Important:** The carry-forward is a reminder only. The system does not automatically close or delete old Laufzettel — they remain open until an admin records payment.

## Email After Laufzettel Creation

If the guest provides an email address when filling in the form, **two emails** are sent automatically (fire-and-forget) after the Laufzettel is created:

### 1. Welcome Email with Laufzettel Link

**Subject:** `Dein H3cke Laufzettel #{id} ist erstellt!`

Contains a direct link to the public Laufzettel view:
```
{PUBLIC_BASE_URL}/laufzettel/view/{laufzettel_id}
```

The guest can use this link to view their Laufzettel at any time — even after closing the browser — as long as they have the URL. The view requires no authentication.

### 2. Membership Invitation (easyVerein)

**Subject:** `Willkommen in der H3cke! Jetzt Mitglied werden`

Contains a link to the easyVerein membership sign-up page. The URL is read from the configuration variable `EASYVEREIN_SIGNUP_URL`. If this variable is not set, no invitation email is sent.

**Configuration:**
```json
{
  "easyverein_signup_url": "https://easyverein.com/public/h3cke/applicationform/"
}
```

Both emails are only sent when the email module (`backend/email_utils.py`) is configured.

## Public Laufzettel View

### `GET /laufzettel/view/{laufzettel_id}`

A **public, read-only** view of a Laufzettel — **no authentication required**. It is intended for paid Laufzettel and is sent via email link to guests and members.

**What is displayed:**
- Guest or member name
- Visit date
- Start time
- Materials grouped by catalog location
- Unit prices and total
- Payment method and payment timestamp (if paid)

**Database access:** The system builds a `variante_id → location name` map from `catalog.db` to group materials by location. If `catalog.db` is unavailable, grouping is skipped gracefully.

**Template:** `templates/public-laufzettel.html`

**Example URL:**
```
https://h3cke.de/laufzettel/view/42
```

This URL is stable and can safely be shared via email, QR code, or printed receipt.

## Printing the QR Code

For best results when printing:
- Use the SVG version for scalability
- Ensure the QR code is at least 2cm x 2cm
- Print on a durable material or laminate
- Display prominently near the entrance or workshop areas

## Updating the IP Address

To change the QR code URL to a different IP address:

1. Edit the `generate_qr.py` script (if using Python):
   ```python
   GUEST_URL = "http://YOUR-NEW-IP:8000/guest/laufzettel"
   ```

2. Or use the curl command with the new URL:
   ```bash
   curl -o guest-laufzettel-qr.png "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=http://YOUR-NEW-IP:8000/guest/laufzettel&color=d04417&bgcolor=ffffff"
   curl -o guest-laufzettel-qr.svg "https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=http://YOUR-NEW-IP:8000/guest/laufzettel&color=d04417&bgcolor=ffffff&format=svg"
   ```

## Corporate Identity Colors

The QR code uses the H3cke MakerSpace Corporate Identity colors:
- **Accent (foreground)**: #d04417 (orange-red)
- **Background**: #ffffff (white)

These colors match the main accent color defined in `static/css/style.css`.

## Relevant Files

- `backend/laufzettel/routes.py` - All guest endpoints and public view
- `backend/config.py` - `PUBLIC_BASE_URL`, `EASYVEREIN_SIGNUP_URL`
- `backend/email_utils.py` - Email sending
- `backend/email_templates.py` - HTML templates for guest emails
- `templates/guest-laufzettel-form.html` - Form page (QR code landing page)
- `templates/guest-laufzettel-detail.html` - Guest detail view (requires session cookie)
- `templates/public-laufzettel.html` - Public receipt view (no auth required)
