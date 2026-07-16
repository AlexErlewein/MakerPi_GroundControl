# 25 · API Reference

This document provides detailed documentation for all MakerPi GroundControl API endpoints. For interactive testing, see the auto-generated Swagger UI at `/docs`.

---

## Authentication

Most API endpoints require authentication via session cookie. Some endpoints are publicly accessible for specific use cases (e.g., guest forms, donation totals).

### Authentication Methods

| Method | Description |
|---|---|
| **Session Cookie** | Standard web authentication - login via `/login` or `/api/auth/login-rfid` |
| **RFID Scan** | Automatic login via NFC tag scan at `/api/auth/login-rfid` |
| **Public** | Some endpoints (marked below) don't require authentication |

### Authentication Required

Most endpoints return `401 Unauthorized` if no valid session is present. Check authentication status by calling `/api/auth/session` (admin/auth session) or `/api/member/me` (member self-info).

---

## System Endpoints

### `GET /api/status`

**Description:** Returns device counts and MQTT message counts (24h and total).

**Authentication:** Public

**Response:**
```json
{
  "devices_total": 5,
  "devices_online": 3,
  "messages_24h": 1234,
  "messages_total": 5678,
  "status": "ok"
}
```

**Use Cases:**
- Health monitoring
- Dashboard status indicators

---

### `GET /api/database/stats`

**Description:** Returns the core database file info plus aggregate device and message stats.

**Authentication:** Public

**Response:**
```json
{
  "database": {
    "file_path": "/path/to/core.db",
    "size_human": "156.0 KB"
  },
  "devices": {
    "total": 5,
    "online": 3,
    "offline": 2,
    "nfc_ok": 4,
    "nfc_error": 1,
    "nfc_unknown": 0
  },
  "messages": {
    "total": 1234,
    "topics": 12,
    "oldest": "2026-01-01T00:00:00",
    "newest": "2026-07-15T12:00:00"
  },
  "devices_oldest_seen": "2026-01-01T00:00:00",
  "devices_newest_seen": "2026-07-15T12:00:00"
}
```

> Per-database health status (ok/error per DB file) is returned by the separate `GET /api/dashboard/db-health` endpoint.

**Use Cases:**
- Database health monitoring
- Storage usage tracking

---

## Device Management

### `GET /api/devices`

**Description:** Lists all known devices from MQTT discovery.

**Authentication:** Required

**Response:**
```json
[
  {
    "id": 1,
    "device_id": "picow_nfc_01",
    "name": "NFC Reader 1",
    "last_seen": "2024-06-15T10:30:00+00:00",
    "status": "online",
    "nfc_ok": true
  }
]
```

**Use Cases:**
- Device inventory
- Connection monitoring
- Status dashboard

---

### `GET /api/devices/{device_id}`

**Description:** Returns detailed information about a specific device including recent messages and topic statistics.

**Authentication:** Required

**Parameters:**
- `device_id` (path): Device identifier (e.g., "picow_nfc_01")

**Response:**
```json
{
  "device": {
    "id": 1,
    "device_id": "picow_nfc_01",
    "name": "NFC Reader 1",
    "last_seen": "2024-06-15T10:30:00+00:00",
    "status": "online"
  },
  "topic_counts": [
    {"topic": "picow_nfc_01/scan", "count": 123},
    {"topic": "picow_nfc_01/status", "count": 456}
  ],
  "recent_messages": [...]
}
```

**Use Cases:**
- Device troubleshooting
- Message analysis
- Activity monitoring

---

### `POST /api/devices/{device_id}/activate`

**Description:** Sends an activation command to a device indicating whether a member is allowed to use it.

**Authentication:** Admin verification required

**Parameters:**
- `device_id` (path): Device identifier

**Request Body:**
```json
{
  "member_id": 123,
  "member_name": "John Doe",
  "allowed": true
}
```

**Response:**
```json
{
  "success": true
}
```

**Use Cases:**
- Device access control
- Member permission enforcement
- Real-time access updates

---

## Member Management

### `GET /api/mitglieder`

**Description:** Lists all members with optional filtering.

**Authentication:** Required

**Query Parameters:**
- `search` (optional): Search by name, member ID, or email

**Response:**
```json
[
  {
    "id": 1,
    "member_id": "12345",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+49123456789",
    "status": "active",
    "nfc_uid": "9CF22507",
    "login_username": "johndoe",
    "has_login": true,
    "sync_locked": false
  }
]
```

**Use Cases:**
- Member directory
- Search and lookup
- Status monitoring

---

### `POST /api/mitglieder`

**Description:** Creates a new member manually.

**Authentication:** Required

**Request Body:**
```json
{
  "member_id": "12345",
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+49123456789",
  "status": "active"
}
```

**Response:** Returns the created member object.

**Use Cases:**
- Manual member registration
- Testing and development
- Emergency member creation

---

### `GET /api/mitglieder/{id}`

**Description:** Returns detailed information about a specific member.

**Authentication:** Required

**Parameters:**
- `id` (path): Member database ID

**Response:** Full member object including all fields.

**Use Cases:**
- Member profile display
- Detailed member information
- Permission checking

---

### `PUT /api/mitglieder/{id}`

**Description:** Updates member information. All fields are optional.

**Authentication:** Required

**Parameters:**
- `id` (path): Member database ID

**Request Body:**
```json
{
  "name": "John Doe Updated",
  "email": "john.new@example.com",
  "phone": "+49123456789",
  "notes": "Updated notes",
  "sync_locked": true
}
```

**Response:** Returns the updated member object.

**Use Cases:**
- Member information updates
- Status changes
- Sync lock management

---

### `DELETE /api/mitglieder/{id}`

**Description:** Deletes a member from the database.

**Authentication:** Required

**Parameters:**
- `id` (path): Member database ID

**Response:**
```json
{
  "success": true
}
```

**Use Cases:**
- Member removal
- Data cleanup
- GDPR compliance

---

## Device Permissions

### `GET /api/mitglieder/{id}/permissions`

**Description:** Lists all device permissions for a specific member.

**Authentication:** Required

**Parameters:**
- `id` (path): Member database ID

**Response:**
```json
[
  {
    "id": 1,
    "device_id": "laser_cutter_01",
    "granted_at": "2024-06-15T10:30:00+00:00"
  },
  {
    "id": 2,
    "device_id": "*",
    "granted_at": "2024-06-15T10:30:00+00:00"
  }
]
```

**Use Cases:**
- Permission audit
- Access control verification
- Member capability checking

---

### `POST /api/mitglieder/{id}/permissions`

**Description:** Grants a member permission to use a specific device.

**Authentication:** Required

**Parameters:**
- `id` (path): Member database ID

**Request Body:**
```json
{
  "device_id": "laser_cutter_01"
}
```

**Special Values:**
- `"*"` - Grants access to all devices

**Response:** Returns the created permission object.

**Use Cases:**
- Granting device access
- Training completion certification
- Safety training verification

---

### `DELETE /api/mitglieder/{id}/permissions/{permission_id}`

**Description:** Removes a device permission from a member.

**Authentication:** Required

**Parameters:**
- `id` (path): Member database ID
- `permission_id` (path): Permission database ID

**Response:**
```json
{
  "success": true
}
```

**Use Cases:**
- Revoking device access
- Safety training expiration
- Membership termination

---

## NFC Tag Management

### `GET /api/tags`

**Description:** Lists all registered RFID tags, including those enrolled via member profiles.

**Authentication:** Required

**Response:**
```json
[
  {
    "id": 1,
    "uid": "9CF22507",
    "owner_name": "John Doe",
    "member_id": "12345",
    "owner_email": "john@example.com",
    "active": true,
    "is_admin": false,
    "created_at": "2024-06-15T10:30:00+00:00",
    "source": "rfid_tag"
  }
]
```

**Use Cases:**
- Tag inventory
- Owner lookup
- Active tag monitoring

---

### `POST /api/tags`

**Description:** Registers a new RFID tag.

**Authentication:** Required

**Request Body:**
```json
{
  "uid": "9CF22507",
  "owner_name": "John Doe",
  "member_id": "12345",
  "owner_email": "john@example.com",
  "notes": "Primary tag",
  "active": true
}
```

**Response:** Returns the created tag object.

**Use Cases:**
- New tag registration
- Guest tag management
- Temporary tag assignment

---

### `PUT /api/tags/{uid}`

**Description:** Updates an existing RFID tag.

**Authentication:** Required

**Parameters:**
- `uid` (path): Tag UID (uppercase)

**Request Body:**
```json
{
  "owner_name": "John Doe Updated",
  "active": false
}
```

**Response:** Returns the updated tag object.

**Use Cases:**
- Tag ownership changes
- Status updates
- Information corrections

---

### `DELETE /api/tags/{uid}`

**Description:** Deletes an RFID tag from the system.

**Authentication:** Required

**Parameters:**
- `uid` (path): Tag UID (uppercase)

**Response:**
```json
{
  "success": true
}
```

**Use Cases:**
- Tag removal
- Lost tag deactivation
- System cleanup

---

## NFC Scans

### `GET /api/scans`

**Description:** Returns recent NFC scan events with validation status.

**Authentication:** Required

**Query Parameters:**
- `limit` (optional): Maximum number of results (default: 100)

**Response:**
```json
[
  {
    "id": 1,
    "uid": "9CF22507",
    "device_id": "picow_nfc_01",
    "validated": true,
    "owner_name": "John Doe",
    "card_verified": 1,
    "atqa": "0400",
    "sak": "08",
    "timestamp": "2024-06-15T10:30:00+00:00"
  }
]
```

**Use Cases:**
- Access log review
- Security monitoring
- Usage statistics

---

### `GET /api/scans/stream`

**Description:** Server-Sent Events (SSE) stream for live NFC scan events.

**Authentication:** Optional (public for device pairing)

**Query Parameters:**
- `token` (optional): Device pairing token for filtered stream

**Response:** SSE stream with JSON events:
```json
{
  "uid": "9CF22507",
  "device_id": "picow_nfc_01"
}
```

**Use Cases:**
- Real-time scan monitoring
- Device pairing
- Live dashboard updates

---

## Accounting / Buchhaltung

### `GET /api/buchhaltung/summary`

**Description:** Returns comprehensive accounting data for a time period including sales, donations, and tax breakdowns.

**Authentication:** Required

**Query Parameters:**
- `period` (optional): `week`, `month` (default), `year`
- `reference_date` (optional): ISO 8601 date string

**Response:**
```json
{
  "period": "month",
  "cutoff": "2024-06-01T00:00:00+00:00",
  "end": "2024-07-01T00:00:00+00:00",
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
  "tax_groups": {...},
  "by_variant": [...],
  "spenden": [...],
  "verkauf_count": 34,
  "spende_count": 1
}
```

**Use Cases:**
- Monthly financial reporting
- Tax preparation
- Revenue analysis

---

### `GET /api/buchhaltung/spenden-total`

**Description:** Lightweight endpoint returning only donation totals for a period.

**Authentication:** Required

**Query Parameters:**
- `period` (optional): `week`, `month` (default), `year`
- `reference_date` (optional): ISO 8601 date string

**Response:**
```json
{
  "spende_total": 789.00,
  "spende_count": 5,
  "period": "month",
  "cutoff": "2024-06-01T00:00:00+00:00",
  "end": "2024-07-01T00:00:00+00:00"
}
```

**Use Cases:**
- Donation dashboards
- External integrations
- Quick donation totals

---

### `POST /api/buchhaltung/spende`

**Description:** Records a manual donation (e.g., from a donation box).

**Authentication:** Required

**Request Body:**
```json
{
  "amount": 25.00,
  "donor_name": "John Doe",
  "date": "2024-06-15T10:30:00+00:00",
  "notes": "Donation box receipt"
}
```

**Response:** Returns the created donation object.

**Use Cases:**
- Manual donation recording
- Cash donation tracking
- Donation box management

---

### `DELETE /api/buchhaltung/spende/{id}`

**Description:** Deletes a manual donation entry.

**Authentication:** Required

**Parameters:**
- `id` (path): Donation database ID

**Response:**
```json
{
  "success": true
}
```

**Use Cases:**
- Donation correction
- Data cleanup
- Error correction

---

## Material Catalog

### `GET /api/katalog`

**Description:** Returns the complete material catalog tree (locations → categories → variants).

**Authentication:** Required

**Response:**
```json
{
  "locations": [
    {
      "id": 1,
      "name": "Main Workshop",
      "kategorien": [
        {
          "id": 1,
          "name": "Filaments",
          "varianten": [
            {
              "id": 1,
              "name": "PLA 1.75mm Black",
              "price": 20.00,
              "pricing_model": "per_unit",
              "tax_rate": 19.0
            }
          ]
        }
      ]
    }
  ]
}
```

**Use Cases:**
- Material browsing
- Price lookup
- Catalog display

---

### `POST /api/katalog/bulk-import`

**Description:** Atomically creates locations, categories, and variants from a structured import.

**Authentication:** Required

**Request Body:**
```json
{
  "locations": [
    {
      "name": "New Workshop",
      "kategorien": [
        {
          "name": "New Category",
          "varianten": [
            {
              "name": "New Material",
              "price": 10.00,
              "pricing_model": "per_unit"
            }
          ]
        }
      ]
    }
  ]
}
```

**Response:** Returns the created objects.

**Use Cases:**
- Bulk catalog import
- Initial setup
- Catalog migration

---

## Laufzettel (Work Orders)

### `GET /api/laufzettel`

**Description:** Lists all work orders with optional filtering.

**Authentication:** Required

**Query Parameters:**
- `uid` (optional): Filter by NFC tag UID
- `date` (optional): Filter by date (ISO 8601)
- `paid` (optional): Filter by payment status (`true`/`false`)

**Response:**
```json
[
  {
    "id": 1,
    "uid": "9CF22507",
    "date": "2024-06-15",
    "payment_method": "karte",
    "total": 25.00,
    "materials": [...]
  }
]
```

**Use Cases:**
- Work order history
- Payment tracking
- Usage analysis

---

### `POST /api/laufzettel`

**Description:** Creates a new work order manually.

**Authentication:** Required

**Request Body:**
```json
{
  "uid": "9CF22507",
  "date": "2024-06-15",
  "notes": "Manual creation"
}
```

**Response:** Returns the created work order.

**Use Cases:**
- Manual work order creation
- Testing
- Emergency work orders

---

### `POST /api/laufzettel/{id}/material`

**Description:** Adds a material entry to a work order.

**Authentication:** Required

**Parameters:**
- `id` (path): Work order database ID

**Request Body:**
```json
{
  "variante_id": 1,
  "menge": 2.5,
  "unit": "kg"
}
```

**Response:** Returns the created material entry.

**Use Cases:**
- Material usage tracking
- Cost calculation
- Inventory management

---

## Payment Processing

### `POST /api/laufzettel/{id}/pay/bar`

**Description:** Records a cash payment for a work order and locks it.

**Authentication:** Required

**Parameters:**
- `id` (path): Work order database ID

**Response:**
```json
{
  "success": true,
  "payment_method": "bar",
  "paid_at": "2024-06-15T10:30:00+00:00"
}
```

**Use Cases:**
- Cash payment recording
- Manual payment entry
- Payment tracking

---

### `POST /api/laufzettel/{id}/pay/karte`

**Description:** Initiates a card payment via SumUp Solo Cloud API or Payment Switch.

**Authentication:** Required

**Parameters:**
- `id` (path): Work order database ID

**Response:**
```json
{
  "mock": false,
  "mode": "solo",
  "client_transaction_id": "gc-...",
  "status": "PENDING"
}
```

For Payment Switch mode, the response also includes a `payment_url` (the SumUp mobile-app URL scheme).

**Use Cases:**
- Card payment processing
- SumUp integration
- Digital payments

---

### `GET /api/laufzettel/{id}/pay/karte/status`

**Description:** Polls the status of a pending card payment. For Payment Switch mode, auto-confirms by matching the SumUp transaction history.

**Authentication:** Required

**Parameters:**
- `id` (path): Work order database ID

**Response:**
```json
{
  "status": "SUCCESSFUL",
  "transaction_id": "txn_123456",
  "amount": 25.00
}
```

`status` is one of `SUCCESSFUL`, `NOT_FOUND`, `TIMEOUT`, or `PENDING`.

**Use Cases:**
- Payment status monitoring
- Transaction verification
- UI updates

---

## Guest Work Orders

### `POST /api/guest/laufzettel`

**Description:** Creates a guest work order (no member account required).

**Authentication:** Public

**Request Body:**
```json
{
  "name": "Guest User",
  "address": "Musterstraße 1, 12345 Stadt",
  "email": "guest@example.com",
  "date": "2026-07-15",
  "start": "2026-07-15T10:00:00"
}
```

`name` and `address` are required; `email`, `date`, and `start` are optional.

**Response:** Returns the created guest work order with session token.

**Use Cases:**
- Guest access
- One-time users
- Testing

---

### `GET /api/guest/session-check`

**Description:** Checks if a guest has an active session.

**Authentication:** Public (uses guest session cookie)

**Response:**
```json
{
  "guest_id": "<uuid-or-null>"
}
```

**Use Cases:**
- Session validation
- Guest UI state
- Access control

---

## Error Handling

All endpoints follow consistent error response patterns:

### HTTP Status Codes

| Code | Description |
|---|---|
| `200` | Success |
| `400` | Bad request (validation failure) |
| `401` | Unauthorized (authentication required) |
| `403` | Forbidden (insufficient permissions) |
| `404` | Resource not found |
| `409` | Conflict (duplicate, locked resource, etc.) |
| `500` | Internal server error |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Common Error Scenarios

- **401**: Not logged in or session expired
- **403**: Admin verification required for sensitive operations
- **404**: Resource ID doesn't exist
- **409**: Resource already exists (duplicate UID), or Laufzettel already paid
- **500**: Database error, unexpected exception

---

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting for:
- Public endpoints
- Payment processing
- Bulk operations

---

## Version Information

API versioning follows the application version. Check `/api/status` for system information.

---

## Interactive Documentation

For interactive API testing and exploration, use the auto-generated Swagger UI:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

These provide request/response examples, parameter validation, and the ability to test endpoints directly in the browser.
