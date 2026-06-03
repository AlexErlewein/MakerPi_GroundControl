# 15 - Member Area

## Overview

The system distinguishes between two user types:
- **Admins**: Full access to all features
- **Members**: Restricted access to own work orders (Laufzettel)

## Role System

### Admin (`role: "admin"`)
- Access to Dashboard (`/dashboard`)
- Manage all Laufzettel
- Member management
- Catalog management
- Admin user management
- Payment functions

### Member (`role: "member"`)
- Access to Member Dashboard (`/member`)
- View own Laufzettel only
- Add materials to own Laufzettel
- No edit/delete of entries
- No payment functions

## Login

### Option 1: RFID Card (Members)
1. Member holds card to RFID reader
2. System recognizes card and logs in automatically
3. Redirect to member area

### Option 2: Username/Password
- Members: Access to `/member`
- Admins: Access to `/dashboard`

## Database Schema

```sql
-- Users table with roles
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT DEFAULT 'member',  -- 'admin' or 'member'
    mitglied_id INTEGER,          -- Link to members table
    created_at TIMESTAMP
);
```

## API Endpoints

### Member-specific
- `GET /member` - Member dashboard
- `GET /member/laufzettel` - Current open (unpaid) Laufzettel
- `GET /member/laufzettel/historie` - Paid Laufzettel history
- `GET /member/laufzettel/{id}` - Laufzettel detail view (read-only)
- `GET /member/konto` - Account info and password management
- `GET /api/member/me` - Fetch own profile data (JSON)
- `POST /api/member/laufzettel/{id}/material` - Add material
- `GET /api/member/laufzettel/{id}/pdf` - Download PDF of own Laufzettel
- `POST /api/member/password` - Change password
- `POST /api/auth/login-rfid` - RFID login

### Admin-specific
- `GET /dashboard` - Admin dashboard
- `GET /admin/*` - All admin functions
- `POST /admin/users/add` - Create user

## Password Management

### Change Password: `POST /api/member/password`

Members can change their password via the account form at `/member/konto`.

**Request body** (form-encoded):

| Field | Type | Required | Description |
|---|---|---|---|
| `current_password` | string | No* | Current password |
| `new_password` | string | Yes | New password (minimum 4 characters) |

*For new members who have not yet set a password, `current_password` may be omitted or sent as `H3cke`.

**Default password for new members**

Members imported via the easyVerein sync start without a login password. In this case the system treats `H3cke` as an implicit default password — it is not stored in the database but is generated dynamically during verification. On the first password change:

1. `current_password` is optional or `"H3cke"`
2. The new password must be at least 4 characters long
3. If no `login_username` was set yet, one is derived automatically from the member's name (fallback: `member_{id}`)
4. The new password hash is written to both `members.db` (`login_password_hash`) and `auth.db` (`hashed_password`)

**Success response:**

```json
{
  "success": true,
  "has_password": true
}
```

**Error cases:**

| HTTP status | Error |
|---|---|
| 400 | No member profile linked |
| 400 | Password too short (fewer than 4 characters) |
| 400 | `current_password` missing (when a password is already set) |
| 403 | Current password is incorrect |
| 404 | Member not found |

**Example request:**

```bash
curl -X POST http://localhost:8000/api/member/password \
  -b "session=..." \
  -d "current_password=H3cke" \
  -d "new_password=MyNewPassword"
```

### Account Page (`GET /member/konto`)

The account page shows:
- Username
- Linked member profile (name, email, member number)
- Whether a password has already been set (`has_password`)
- Form for changing the password

## Account Provisioning (Admin)

When a member needs to log in for the first time via username/password (rather than RFID), a login account must be provisioned.

### Automatically on RFID Login

On a member's first RFID scan, the system automatically creates a `User` record in `auth.db`:

```python
user = User(
    username=mitglied.name,  # fallback: "member_{id}"
    hashed_password="",      # empty — RFID login only
    role="admin" if is_admin_card else "member",
    mitglied_id=mitglied.id,
)
```

### Manually via Admin UI

Admins can create a user with a password via `POST /admin/users/add`:

```bash
curl -X POST http://localhost:8000/admin/users/add \
  -d "username=firstname.lastname" \
  -d "password=H3cke" \
  -d "role=member"
```

After creation the member can change their password themselves at `/member/konto`.

### Member with Own Login (`login_username` / `login_password_hash`)

Members can also log in directly using their `members.db` credentials — without a dedicated `User` record in `auth.db`. The login flow checks `auth.db` first, then falls back to `members.db`. The fields `login_username` and `login_password_hash` on the `Mitglied` table are populated when the member sets a password via `POST /api/member/password`.

## Configuration

### Create First Admin
On first startup, an admin user is created automatically:
- Username: `admin` (or `ADMIN_USERNAME` from config)
- Password: `changeme` (or `ADMIN_PASSWORD` from config)
- Role: `admin`

### Create Member User
```bash
curl -X POST http://localhost:8000/admin/users/add \
  -d "username=member1" \
  -d "password=H3cke" \
  -d "role=member"
```

### Assign RFID Card
1. Create member in database
2. Link RFID tag with member (via member management)
3. User then has automatic access via RFID

## Security

### Session Handling
- Session cookies signed with `SECRET_KEY`
- Session contains: `user`, `role`, `mitglied_id`, `last_activity`
- Invalid session: automatic redirect to landing page
- `last_activity` is updated on every API call (keep-alive)

### Access Check
```python
# Example: Member endpoint
def require_member(request: Request):
    username = request.session.get("user")
    if not username:
        raise HTTPException(401, "Not authenticated")
    user = db.query(User).filter(User.username == username).first()
    if not user or user.role not in ["admin", "member"]:
        raise HTTPException(403, "Access denied")
    return user
```

### Laufzettel Security
Members can only see Laufzettel matching their `mitglied_id`:
```python
laufzettel = db.query(Laufzettel).filter(
    Laufzettel.mitglied_id == current_user.mitglied_id
).all()
```

## Frontend

### Landing Page (`/`)
- RFID scan area for members
- Link to admin login
- Documentation link

### Member UI
- Simplified view without admin functions
- No "Pay" buttons
- No "Delete" buttons
- Only "Add material" for open Laufzettel

### Admin UI
- Full functionality
- All Laufzettel visible
- Payment functions active

## Troubleshooting

### "User not found" Error
- Delete old session cookies
- Clear browser cache
- Test in incognito window

### RFID Not Working
- Is MQTT broker running?
- Is RFID reader connected correctly?
- Is tag registered in system?
- Is member linked to tag?

### Access Problems
- Does user have correct `role`?
- Does member have `mitglied_id` set?
- Is session valid (not expired)?

### Forgotten Password
Admins can reset a member's password by deleting and recreating the `User` record in `auth.db`. Alternatively, `login_password_hash` can be cleared directly in `members.db` — on the next password change `H3cke` will be treated as the default again.

## Files

- `backend/auth/models.py` - User model with role/mitglied_id
- `backend/member_routes.py` - Member-specific routes including password change
- `backend/auth/routes.py` - Login/session routes
- `templates/landing.html` - Landing page with RFID
- `templates/member-laufzettel-open.html` - Member's open Laufzettel
- `templates/member-laufzettel-historie.html` - Member payment history
- `templates/member-laufzettel-detail.html` - Member detail view
- `templates/member-konto.html` - Account and password page
- `static/css/member.css` - Member area styling
