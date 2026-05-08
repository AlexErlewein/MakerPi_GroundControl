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

1. **Scanning the QR Code**: When a guest scans the QR code, they're redirected to the guest Laufzettel form page.

2. **Form Submission**: The guest fills in:
   - Name (required)
   - Email (optional)
   - Date and time (auto-filled)
   - Clicks "Fertig" to submit

3. **Laufzettel Creation**: A new Laufzettel is created with:
   - A unique guest ID (stored in a browser cookie)
   - A generated UID (format: GUEST-XXXXXX)
   - The provided name and email

4. **Material Tracking**: The guest can then:
   - Add materials to their Laufzettel
   - Add donations (Spende)
   - View their material usage
   - Cannot initiate payment themselves

5. **Session Persistence**: The guest session cookie persists until the Laufzettel is paid. If they rescan the QR code on the same day, they'll see their existing Laufzettel.

6. **Previous Day Reminder**: If they rescan on a new day with an unpaid Laufzettel from a previous day, a reminder popup will appear.

7. **Payment**: Guests tell an admin their name, and the admin can:
   - Find the Laufzettel using the name filter on the `/laufzettel` page
   - Process payment manually
   - Mark the Laufzettel as paid

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
