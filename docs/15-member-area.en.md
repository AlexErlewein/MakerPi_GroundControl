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
- `GET /member/laufzettel` - Own Laufzettel
- `GET /member/laufzettel/{id}` - Laufzettel details
- `POST /api/member/laufzettel/{id}/material` - Add material
- `POST /api/auth/login-rfid` - RFID login

### Admin-specific
- `GET /dashboard` - Admin dashboard
- `GET /admin/*` - All admin functions
- `POST /admin/users/add` - Create user

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
  -d "password=password123" \
  -d "role=member"
```

### Assign RFID Card
1. Create member in database
2. Link RFID tag with member (via member management)
3. User then has automatic access via RFID

## Security

### Session Handling
- Session cookies signed with `SECRET_KEY`
- Session contains: `user`, `role`, `mitglied_id`
- Invalid session: automatic redirect to landing page

### Access Check
```python
# Example: Member endpoint
def require_member(request: Request):
    user = get_current_user(request)
    if user.role not in ["admin", "member"]:
        raise HTTPException(401, "Access denied")
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

## Files

- `backend/auth/models.py` - User model with role/mitglied_id
- `backend/member_routes.py` - Member-specific routes
- `backend/auth/routes.py` - Login/session routes
- `templates/landing.html` - Landing page with RFID
- `templates/member-laufzettel-list.html` - Member Laufzettel
- `templates/member-laufzettel-detail.html` - Member detail view
- `static/css/landing.css` - Landing page styling
