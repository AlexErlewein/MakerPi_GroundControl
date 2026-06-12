# 26 · Authentication System

This document provides a comprehensive technical deep-dive into the MakerPi GroundControl authentication system, designed for learning and understanding the security architecture.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Two-Level Authentication Model](#two-level-authentication-model)
4. [Session Management](#session-management)
5. [Login Flows](#login-flows)
6. [Admin Verification](#admin-verification)
7. [Security Features](#security-features)
8. [Timeout Mechanisms](#timeout-mechanisms)
9. [Database Schema](#database-schema)
10. [Code Deep Dive](#code-deep-dive)
11. [Security Best Practices](#security-best-practices)
12. [Extending the System](#extending-the-system)

---

## Overview

The MakerPi GroundControl authentication system is a **session-based, two-level authentication framework** that provides:

- **Basic authentication** for member access
- **Admin verification** for sensitive operations
- **RFID tag support** for physical access
- **Automatic timeout** for security
- **Role-based access control** (RBAC)

### Key Design Principles

1. **Session-based** - No API tokens, uses secure HTTP-only cookies
2. **Defense in depth** - Two-level authentication for sensitive operations
3. **Activity tracking** - Timestamp-based timeout enforcement
4. **Flexible user types** - Admin-only, member-only, and hybrid users
5. **Physical access** - RFID tag integration for makerspace environments

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Browser)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ Login Form   │  │ RFID Scanner  │  │ Admin Panel  │    │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘    │
└─────────┼──────────────────┼──────────────────┼─────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Session Middleware (Starlette)              │  │
│  │  - Cookie-based session storage                      │  │
│  │  - Secret key signing                                │  │
│  │  - Automatic cookie handling                          │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Auth Router (/auth, /login)              │  │
│  │  - Unified login endpoint                            │  │
│  │  - RFID login endpoint                               │  │
│  │  - Admin verification                                 │  │
│  │  - Session management                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Auth Dependencies (auth/dependencies.py)    │  │
│  │  - check_auth()                                       │  │
│  │  - is_admin_verified()                               │  │
│  │  - verify_admin_password()                           │  │
│  │  - is_member_session_valid()                          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                   Databases (SQLite)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  auth.db     │  │ members.db   │  │  core.db     │    │
│  │  - User      │  │  - Mitglied  │  │  - Device    │    │
│  │  - Password  │  │  - RFIDTag   │  │  - TagScan   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Request Flow

```
1. User Request
   ↓
2. Session Middleware (checks cookie)
   ↓
3. Route Handler (calls auth dependency)
   ↓
4. Auth Dependency (validates session)
   ↓
5. Business Logic (if auth passes)
   ↓
6. Response
```

---

## Two-Level Authentication Model

### Level 1: Basic Authentication

**Purpose:** Grant access to member areas and basic operations

**Implementation:** `check_auth(request: Request) -> bool`

**Requirements:**
- Valid session with `user` key
- Session not expired (3-minute timeout)

**Grants Access To:**
- Member area (`/member`)
- Member-specific data
- Basic API endpoints
- Personal work orders

**Code:**
```python
def check_auth(request: Request) -> bool:
    """Check if user is authenticated"""
    return request.session.get("user") is not None
```

### Level 2: Admin Verification

**Purpose:** Grant access to sensitive administrative operations

**Implementation:** `is_admin_verified(request: Request) -> bool`

**Requirements:**
- Valid session with `user` key
- User is admin-capable (`is_admin_capable = True`)
- Admin verification active (`admin_verified = True`)
- Verification not expired (10-minute timeout)

**Grants Access To:**
- Admin dashboard (`/dashboard`)
- User management (`/admin/users`)
- Device pairing
- System configuration
- Financial data access
- Gift card management

**Code:**
```python
def is_admin_verified(request: Request) -> bool:
    """Check if user has verified admin status (with 10min timeout)"""
    session = request.session
    if not session.get("admin_verified"):
        return False

    admin_verified_at = session.get("admin_verified_at")
    last_activity = session.get("last_activity")

    if not admin_verified_at or not last_activity:
        return False

    # Parse ISO format strings to datetime
    try:
        last_activity_dt = datetime.fromisoformat(last_activity)
        if last_activity_dt.tzinfo is None:
            last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return False

    # Check 10min timeout
    now = datetime.now(timezone.utc)
    if (now - last_activity_dt).total_seconds() > (ADMIN_TIMEOUT_MINUTES * 60):
        # Timeout expired, clear admin verification
        session["admin_verified"] = False
        session["admin_verified_at"] = None
        return False

    # Update last activity
    session["last_activity"] = now.isoformat()
    return True
```

### Access Control Matrix

| Operation | Level Required | Dependency | Timeout |
|---|---|---|---|
| View member area | Level 1 | `check_auth` | 3 min |
| Create work order | Level 1 | `check_auth` | 3 min |
| View accounting data | Level 1 | `check_auth` | 3 min |
| View admin dashboard | Level 2 | `is_admin_verified` | 10 min |
| Manage users | Level 2 | `is_admin_verified` | 10 min |
| Device pairing | Level 2 | `is_admin_verified` | 10 min |
| Gift card operations | Level 1 | `check_auth` | 3 min |

---

## Session Management

### Session Structure

Sessions are stored as HTTP-only cookies signed with a secret key. The session data structure:

```python
{
    # Basic Authentication
    "user": str,                    # Username (required for Level 1)
    "mitglied_id": int,             # Member database ID (optional)
    "login_method": str,            # "password" or "rfid"
    
    # Admin Capabilities
    "is_admin_capable": bool,       # Can become admin
    "admin_verified": bool,          # Currently in admin mode
    "admin_verified_at": str,        # ISO timestamp when verified
    
    # Activity Tracking
    "last_activity": str,           # ISO timestamp of last request
}
```

### Session Lifecycle

```
1. Login → Session Created
   ├─ user: "username"
   ├─ login_method: "password" or "rfid"
   ├─ is_admin_capable: determined from user type
   ├─ admin_verified: False
   └─ last_activity: current timestamp

2. Activity → Session Updated
   └─ last_activity: updated on each request

3. Admin Verification → Admin Mode Enabled
   ├─ admin_verified: True
   └─ admin_verified_at: current timestamp

4. Timeout → Session Cleared/Downgraded
   ├─ Level 1 timeout (3 min): Full session cleared
   └─ Level 2 timeout (10 min): admin_verified = False

5. Logout → Session Destroyed
   └─ All session data cleared
```

### Session Security Features

1. **HTTP-Only Cookies** - Not accessible via JavaScript
2. **Signed Cookies** - Cryptographically signed with secret key
3. **Secure Flag** - Only transmitted over HTTPS (in production)
4. **SameSite Protection** - CSRF protection
5. **Automatic Expiration** - Server-side timeout enforcement

---

## Login Flows

### Unified Login Flow

The system supports multiple user types through a single login endpoint:

```
POST /api/auth/login
{
    "username": "user",
    "password": "pass"
}
```

#### Flowchart

```
┌─────────────────────────────────────────────────────────┐
│                    Login Request                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ Check auth.db User     │
        │ (admin users)          │
        └──────────┬─────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼────┐         ┌─────▼─────┐
   │ Found?  │         │ Not found │
   └────┬────┘         └─────┬─────┘
        │ Yes                  │
        ▼                      │
┌──────────────────┐           │
│ Verify password │           │
└────────┬─────────┘           │
         │                     │
    ┌────┴────┐         ┌─────▼─────┐
    │ Valid?  │         │ Check     │
    └────┬────┘         │ members.db│
         │ No             │ Mitglied  │
         │               └─────┬─────┘
         │                     │
    ┌────▼────┐         ┌─────▼─────┐
    │ Return  │         │ Found?    │
    │ Error   │         └─────┬─────┘
    └─────────┘               │
                       ┌──────┴──────┐
                       │            │
                  ┌────▼────┐  ┌───▼────┐
                  │ Yes     │  │ No     │
                  └────┬────┘  └───┬────┘
                       │           │
                       ▼           ▼
              ┌──────────────┐  ┌──────────────┐
              │ Verify      │  │ Return error │
              │ member      │  │ Invalid      │
              │ password    │  │ credentials  │
              └──────┬───────┘  └──────────────┘
                     │
                ┌────┴────┐
                │ Valid?  │
                └────┬────┘
                     │ Yes
                     ▼
          ┌──────────────────────┐
          │ Create session       │
          │ Set user capabilities│
          │ Redirect to area     │
          └──────────────────────┘
```

### User Type 1: Admin-Only Users

**Source:** `auth.db` → `User` table

**Characteristics:**
- Created via admin panel
- Has `role = "admin"`
- No `mitglied_id` (not linked to member)
- Password stored in `auth.db`

**Login Process:**
```python
# 1. Check auth.db
user = get_user(db, username)
if user and verify_password(password, user.hashed_password):
    # 2. Check if admin-only
    if user.role == "admin" and not user.mitglied_id:
        # 3. Auto-verify (password just entered)
        request.session["admin_verified"] = True
        request.session["admin_verified_at"] = now.isoformat()
        # 4. Redirect to dashboard
        return RedirectResponse("/dashboard")
```

**Session Data:**
```python
{
    "user": "admin",
    "mitglied_id": None,
    "is_admin_capable": True,
    "admin_verified": True,  # Auto-verified
    "login_method": "password"
}
```

### User Type 2: Member Users

**Source:** `members.db` → `Mitglied` table

**Characteristics:**
- Created via member registration or easyVerein sync
- Has `login_username` and `login_password_hash`
- May have admin RFID tag
- Password stored in `members.db`

**Login Process:**
```python
# 1. Check members.db
mitglied = members_db.query(Mitglied).filter(
    Mitglied.login_username == username
).first()

if mitglied and verify_password(password, mitglied.login_password_hash):
    # 2. Check for admin RFID tag
    admin_tag = members_db.query(RFIDTag).filter(
        RFIDTag.member_id == mitglied.member_id,
        RFIDTag.is_admin == True,
        RFIDTag.active == 1
    ).first()
    
    # 3. Set capabilities
    has_admin = bool(admin_tag)
    request.session["is_admin_capable"] = has_admin
    
    # 4. Redirect to member area
    return RedirectResponse("/member")
```

**Session Data:**
```python
{
    "user": "member_username",
    "mitglied_id": 123,
    "is_admin_capable": True,  # If has admin tag
    "admin_verified": False,  # Requires manual verification
    "login_method": "password"
}
```

### User Type 3: Hybrid Users (Member + Admin)

**Source:** Both `auth.db` and `members.db`

**Characteristics:**
- Member with admin RFID tag
- Or member linked to admin user in `auth.db`
- Can access member area
- Can become admin with verification

**Login Process:**
```python
# 1. Check auth.db first (admin users)
user = get_user(db, username)
if user and verify_password(password, user.hashed_password):
    if user.role == "admin" and user.mitglied_id:
        # Hybrid: admin with member link
        request.session["is_admin_capable"] = True
        request.session["admin_verified"] = False  # Manual verify
        return RedirectResponse("/member")

# 2. Check members.db (member users)
mitglied = members_db.query(Mitglied).filter(
    Mitglied.login_username == username
).first()
if mitglied and verify_password(password, mitglied.login_password_hash):
    # Check for admin tag
    admin_tag = members_db.query(RFIDTag).filter(
        RFIDTag.member_id == mitglied.member_id,
        RFIDTag.is_admin == True
    ).first()
    
    has_admin = bool(admin_tag)
    request.session["is_admin_capable"] = has_admin
    return RedirectResponse("/member")
```

### RFID Login Flow

**Endpoint:** `POST /api/auth/login-rfid`

**Purpose:** Allow physical RFID tags to trigger login

**Process:**
```python
POST /api/auth/login-rfid
{
    "uid": "9CF22507"
}

# 1. Look up UID in members.db
#    a. Check Mitglied.nfc_uid (enrolled via member UI)
#    b. Check RFIDTag.uid (legacy tag table)

# 2. If found, create session
mitglied = members_db.query(Mitglied).filter(
    Mitglied.nfc_uid == uid.upper()
).first()

if mitglied:
    request.session["user"] = mitglied.login_username or str(mitglied.id)
    request.session["mitglied_id"] = mitglied.id
    request.session["login_method"] = "rfid"
    
    # 3. Check for admin tag
    admin_tag = members_db.query(RFIDTag).filter(
        RFIDTag.member_id == mitglied.member_id,
        RFIDTag.is_admin == True
    ).first()
    
    request.session["is_admin_capable"] = bool(admin_tag)
    request.session["admin_verified"] = False
```

**Important:** RFID login **cannot** use auto-verification. Must manually verify with password for admin access.

---

## Admin Verification

### Why Two-Level Authentication?

**Problem:** Single-level authentication is insufficient for sensitive operations:
- Users might leave their computer unlocked
- Session hijacking risk
- Accidental admin actions
- Need for explicit confirmation for critical operations

**Solution:** Two-level authentication adds an extra verification step for admin operations.

### Verification Methods

#### Method 1: Manual Password Verification

**Endpoint:** `POST /api/auth/verify-admin`

**Process:**
```python
POST /api/auth/verify-admin
{
    "password": "admin_password"
}

# 1. Check user is logged in
if not request.session.get("user"):
    return {"success": False, "error": "Not authenticated"}

# 2. Check user is admin-capable
if not request.session.get("is_admin_capable"):
    return {"success": False, "error": "Not admin capable"}

# 3. Verify password
username = request.session.get("user")
user = db.query(User).filter(User.username == username).first()

# Try auth.db password first
if user.hashed_password and verify_password(password, user.hashed_password):
    pass  # Valid
else:
    # Try member login password
    mitglied = members_db.query(Mitglied).filter(
        Mitglied.id == user.mitglied_id
    ).first()
    if not verify_password(password, mitglied.login_password_hash):
        return {"success": False, "error": "Invalid password"}

# 4. Set admin verified
request.session["admin_verified"] = True
request.session["admin_verified_at"] = now.isoformat()
return {"success": True}
```

**Use Cases:**
- Admin-only users (auto-verify not needed)
- RFID login (password not entered during login)
- Security-conscious environments

#### Method 2: Auto-Verification

**Endpoint:** `POST /api/auth/verify-admin-auto`

**Process:**
```python
POST /api/auth/verify-admin-auto

# 1. Check user is admin-capable
if not request.session.get("is_admin_capable"):
    return {"success": False, "error": "Not admin capable"}

# 2. Check login method was password
if request.session.get("login_method") != "password":
    return {"success": False, "error": "requires_password"}

# 3. Auto-verify without password
request.session["admin_verified"] = True
request.session["admin_verified_at"] = now.isoformat()
return {"success": True}
```

**Use Cases:**
- Admin-only users (password just entered)
- Streamlined admin workflow
- Reduced friction for trusted admins

**Restrictions:**
- Only works if `login_method == "password"`
- Cannot be used with RFID login
- Cannot be used if session timeout occurred

### Verification Flowchart

```
┌─────────────────────────────────────────────────────────┐
│              User Requests Admin Operation               │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │ is_admin_verified()?    │
        └──────────┬─────────────┘
                   │
          ┌────────┴────────┐
          │                 │
     ┌────▼────┐      ┌─────▼─────┐
     │  Yes    │      │   No      │
     └────┬────┘      └─────┬─────┘
          │                 │
          │                 ▼
          │      ┌──────────────────────┐
          │      │ Show verify password │
          │      │ prompt              │
          │      └──────────┬───────────┘
          │                 │
          │        ┌────────┴────────┐
          │        │                 │
          │   ┌────▼────┐      ┌─────▼─────┐
          │   │ Manual  │      │ Auto      │
          │   │ verify  │      │ verify    │
          │   └────┬────┘      └─────┬─────┘
          │        │                 │
          │        ▼                 ▼
          │  ┌──────────────┐  ┌──────────────┐
          │  │ Verify      │  │ Check       │
          │  │ password    │  │ login_method │
          │  └──────┬───────┘  └──────┬───────┘
          │         │                 │
          │    ┌────┴────┐         ┌────┴────┐
          │    │ Valid?   │         │ Password?│
          │    └────┬────┘         └────┬────┘
          │         │ Yes               │ Yes
          │         ▼                   ▼
          │  ┌──────────────────────────────┐
          │  │ Set admin_verified = True   │
          │  │ Set admin_verified_at = now  │
          │  └──────────┬───────────────────┘
          │             │
          └─────────────┴───────────────────
                        │
                        ▼
              ┌──────────────────────┐
              │ Execute operation   │
              └──────────────────────┘
```

---

## Security Features

### 1. Password Hashing

**Algorithm:** bcrypt (via passlib)

**Configuration:**
```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
```

**Hashing Process:**
```python
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**Properties:**
- **Slow by design** - Prevents brute force attacks
- **Salted automatically** - Prevents rainbow table attacks
- **Adaptive cost** - Can increase computational cost over time
- **Industry standard** - Battle-tested algorithm

### 2. Session Security

**Cookie Properties:**
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    max_age=None,  # Browser session
    httponly=True,  # Not accessible via JavaScript
    secure=True,   # Only over HTTPS (production)
    samesite="lax"  # CSRF protection
)
```

**Security Benefits:**
- **HTTP-Only:** Prevents XSS cookie theft
- **Secure:** Prevents man-in-the-middle attacks
- **SameSite:** Prevents CSRF attacks
- **Signed:** Prevents cookie tampering

### 3. Activity Tracking

**Implementation:**
```python
# Updated on every authenticated request
session["last_activity"] = datetime.now(timezone.utc).isoformat()

# Checked on auth dependency calls
if (now - last_activity_dt).total_seconds() > TIMEOUT_SECONDS:
    session.clear()  # or admin_verified = False
```

**Benefits:**
- Automatic session expiration
- Reduced window for session hijacking
- Inactivity detection
- Resource cleanup

### 4. Defense in Depth

**Layer 1: Network Security**
- HTTPS encryption (production)
- Secure cookie flags
- SameSite protection

**Layer 2: Authentication**
- Strong password hashing
- Session-based auth
- Activity tracking

**Layer 3: Authorization**
- Two-level authentication
- Role-based access control
- Admin verification for sensitive ops

**Layer 4: Application Security**
- Input validation
- SQL injection prevention (ORM)
- XSS protection (template escaping)

### 5. RFID Security

**Card Signature Verification:**
```python
# 3VL (Three-Level Verification) signature system
if card_signature and card_member_id:
    if verify_card_signature(
        verify_member_id, uid, verify_name, card_signature
    ):
        card_verified = 1  # Valid signature
    else:
        card_verified = 0  # Invalid - possible clone
```

**Security Features:**
- HMAC signature verification
- Card-side data validation
- Clone detection
- Legacy card support

---

## Timeout Mechanisms

### Member Session Timeout (3 Minutes)

**Purpose:** Protect member sessions from hijacking

**Implementation:**
```python
MEMBER_TIMEOUT_MINUTES = 3

def is_member_session_valid(request: Request) -> bool:
    session = request.session
    if not session.get("user"):
        return False

    last_activity = session.get("last_activity")
    if not last_activity:
        return False

    # Parse timestamp
    last_activity_dt = datetime.fromisoformat(last_activity)
    if last_activity_dt.tzinfo is None:
        last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)

    # Check timeout
    now = datetime.now(timezone.utc)
    if (now - last_activity_dt).total_seconds() > (MEMBER_TIMEOUT_MINUTES * 60):
        session.clear()  # Full logout
        return False

    # Update activity
    session["last_activity"] = now.isoformat()
    return True
```

**Behavior:**
- After 3 minutes of inactivity → **Full logout**
- User must re-authenticate
- All session data cleared

**Rationale:**
- Members often use shared computers in makerspace
- Short timeout reduces risk of unauthorized access
- Quick re-login is acceptable for member operations

### Admin Verification Timeout (10 Minutes)

**Purpose:** Protect admin operations while allowing reasonable workflow

**Implementation:**
```python
ADMIN_TIMEOUT_MINUTES = 10

def is_admin_verified(request: Request) -> bool:
    session = request.session
    if not session.get("admin_verified"):
        return False

    admin_verified_at = session.get("admin_verified_at")
    last_activity = session.get("last_activity")

    if not admin_verified_at or not last_activity:
        return False

    # Parse timestamp
    last_activity_dt = datetime.fromisoformat(last_activity)
    if last_activity_dt.tzinfo is None:
        last_activity_dt = last_activity_dt.replace(tzinfo=timezone.utc)

    # Check timeout
    now = datetime.now(timezone.utc)
    if (now - last_activity_dt).total_seconds() > (ADMIN_TIMEOUT_MINUTES * 60):
        session["admin_verified"] = False
        session["admin_verified_at"] = None
        return False  # Downgrade, not logout

    # Update activity
    session["last_activity"] = now.isoformat()
    return True
```

**Behavior:**
- After 10 minutes of inactivity → **Admin verification revoked**
- User stays logged in (member access retained)
- Must re-verify password for admin operations

**Rationale:**
- Admin operations are less frequent
- Longer timeout allows reasonable workflow
- Downgrade (not logout) reduces friction
- Re-verification adds security for sensitive ops

### Timeout Comparison

| Timeout | Duration | Effect | Use Case |
|---|---|---|---|
| Member Session | 3 min | Full logout | Member area, basic operations |
| Admin Verification | 10 min | Admin downgrade | Admin dashboard, sensitive ops |

### Heartbeat Mechanism

**Endpoint:** `POST /api/auth/heartbeat`

**Purpose:** Update activity timestamp and check session validity

**Implementation:**
```python
@router.post("/api/auth/heartbeat")
async def heartbeat(request: Request):
    """Update last activity timestamp and check session validity"""
    if not is_member_session_valid(request):
        return JSONResponse({"valid": False}, status_code=401)
    return {"valid": True}
```

**Usage:**
- Frontend calls this periodically (e.g., every 30 seconds)
- Keeps session alive during active use
- Provides early warning of session expiration
- Allows graceful logout before timeout

---

## Database Schema

### auth.db Schema

#### User Table
```sql
CREATE TABLE user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role VARCHAR NOT NULL,  -- 'admin' or 'member'
    mitglied_id INTEGER,     -- Foreign key to members.db (soft reference)
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_user_username ON user(username);
CREATE INDEX ix_user_mitglied_id ON user(mitglied_id);
```

**Relationship to members.db:**
- `mitglied_id` is a soft reference (no foreign key constraint)
- Links auth user to member record
- Allows hybrid users (admin + member)

### members.db Schema

#### Mitglied Table (Relevant Fields)
```sql
CREATE TABLE mitglieder (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id VARCHAR UNIQUE NOT NULL,
    name VARCHAR NOT NULL,
    email VARCHAR,
    login_username VARCHAR UNIQUE,
    login_password_hash VARCHAR,
    nfc_uid VARCHAR UNIQUE,
    -- ... other fields
);

CREATE INDEX ix_mitglieder_login_username ON mitglieder(login_username);
CREATE INDEX ix_mitglieder_nfc_uid ON mitglieder(nfc_uid);
```

#### RFIDTag Table
```sql
CREATE TABLE rfid_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uid VARCHAR UNIQUE NOT NULL,
    member_id VARCHAR,
    owner_name VARCHAR NOT NULL,
    is_admin BOOLEAN DEFAULT 0,
    active INTEGER DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_rfid_tags_uid ON rfid_tags(uid);
CREATE INDEX ix_rfid_tags_member_id ON rfid_tags(member_id);
```

**Admin Tag Detection:**
```python
admin_tag = members_db.query(RFIDTag).filter(
    RFIDTag.member_id == mitglied.member_id,
    RFIDTag.is_admin == True,
    RFIDTag.active == 1
).first()
```

---

## Code Deep Dive

### Authentication Dependency Usage

#### Basic Auth in Route Handler
```python
from backend.auth.dependencies import check_auth

@router.get("/api/buchhaltung/summary")
async def get_summary(
    request: Request,
    period: str = Query("month", pattern="^(week|month|year)$"),
    db: Session = Depends(get_db),
):
    # Check authentication
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Business logic here
    ...
```

#### Admin Verification in Route Handler
```python
from backend.auth.dependencies import is_admin_verified

@router.get("/admin/users")
async def admin_users_page(request: Request, db: Session = Depends(get_db)):
    # Check admin verification
    if not is_admin_verified(request):
        return RedirectResponse("/member?admin_required=1", status_code=302)
    
    # Business logic here
    ...
```

#### Dependency Injection Pattern
```python
# For use with FastAPI Depends()
def require_auth(request: Request):
    """Dependency: require authentication"""
    if not request.session.get("user"):
        raise HTTPException(status_code=401, detail="Not authenticated")

def require_admin(request: Request):
    """Dependency: require admin verification"""
    if not is_admin_verified(request):
        raise HTTPException(status_code=403, detail="Admin verification required")

# Usage in route
@router.get("/api/sensitive")
async def sensitive_endpoint(
    request: Request = Depends(require_admin)
):
    # Guaranteed to have admin verification
    ...
```

### Session Management Code

#### Login Session Creation
```python
@router.post("/api/auth/login")
async def unified_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # ... authentication logic ...
    
    # Create session
    request.session["user"] = user.username
    request.session["mitglied_id"] = user.mitglied_id
    request.session["is_admin_capable"] = user.role == "admin"
    request.session["login_method"] = "password"
    request.session["admin_verified"] = False
    request.session["admin_verified_at"] = None
    request.session["last_activity"] = datetime.now(timezone.utc).isoformat()
    
    # Redirect based on user type
    if user.role == "admin" and not user.mitglied_id:
        return RedirectResponse("/dashboard")
    else:
        return RedirectResponse("/member")
```

#### Logout
```python
@router.get("/logout")
async def logout(request: Request):
    """Clear session"""
    request.session.clear()
    return RedirectResponse("/", status_code=302)
```

#### Admin Logout (Downgrade)
```python
@router.post("/api/auth/logout-admin")
async def logout_admin(request: Request):
    """Drop admin verification, return to member view"""
    request.session["admin_verified"] = False
    request.session["admin_verified_at"] = None
    return RedirectResponse("/member", status_code=302)
```

### Password Management

#### Password Hashing
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """Hash a password for storage"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)
```

#### Admin User Seeding
```python
def seed_admin_user():
    """Seed default admin user if no users exist"""
    db = SessionLocal()
    try:
        existing = db.query(User).first()
        if existing:
            return  # Already seeded
        
        # Create default admin from config
        hashed = get_password_hash(ADMIN_PASSWORD)
        admin = User(
            username=ADMIN_USERNAME,
            hashed_password=hashed,
            role="admin",
            mitglied_id=None,
        )
        db.add(admin)
        db.commit()
    finally:
        db.close()
```

### RFID Authentication

#### RFID Login Handler
```python
@router.post("/api/auth/login-rfid")
async def login_rfid(request: Request, uid: str = Form(...)):
    """Login via RFID tag scan"""
    from backend.members.db import get_db as get_members_db
    from backend.members.models import Mitglied, RFIDTag

    members_db = next(get_members_db())
    try:
        uid_upper = uid.upper()
        
        # Check Mitglied.nfc_uid (enrolled via member UI)
        mitglied = members_db.query(Mitglied).filter(
            Mitglied.nfc_uid == uid_upper
        ).first()
        
        if not mitglied:
            # Check RFIDTag table (legacy)
            tag = members_db.query(RFIDTag).filter(
                RFIDTag.uid == uid_upper,
                RFIDTag.active == 1
            ).first()
            
            if tag:
                # Resolve to Mitglied via member_id
                mitglied = members_db.query(Mitglied).filter(
                    Mitglied.member_id == tag.member_id
                ).first()
        
        if mitglied:
            # Create session
            request.session["user"] = mitglied.login_username or str(mitglied.id)
            request.session["mitglied_id"] = mitglied.id
            request.session["login_method"] = "rfid"
            
            # Check for admin tag
            admin_tag = members_db.query(RFIDTag).filter(
                RFIDTag.member_id == mitglied.member_id,
                RFIDTag.is_admin == True,
                RFIDTag.active == 1
            ).first()
            
            request.session["is_admin_capable"] = bool(admin_tag)
            request.session["admin_verified"] = False
            request.session["last_activity"] = datetime.now(timezone.utc).isoformat()
            
            return {"success": True, "redirect": "/member"}
        
        return {"success": False, "error": "Tag not found"}
    finally:
        members_db.close()
```

---

## Security Best Practices

### 1. Password Requirements

**Current Implementation:**
- No explicit password complexity requirements
- Relies on bcrypt's computational cost for security

**Recommendations:**
```python
import re

def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password meets minimum requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain digit"
    
    return True, "Valid"
```

### 2. Session Configuration

**Current Implementation:**
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    max_age=None,
    httponly=True,
    secure=True,  # Production only
    samesite="lax"
)
```

**Recommendations:**
- Use strong, randomly generated `SECRET_KEY`
- Rotate `SECRET_KEY` periodically (requires session invalidation)
- Consider `max_age` for absolute session expiration
- Use `samesite="strict"` for higher security (may break some integrations)

### 3. Rate Limiting

**Current Implementation:**
- No rate limiting on authentication endpoints

**Recommendations:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@limiter.limit("5/minute")
@router.post("/api/auth/login")
async def unified_login(...):
    # Login logic
    ...
```

### 4. Audit Logging

**Current Implementation:**
- No audit logging for authentication events

**Recommendations:**
```python
import logging

auth_logger = logging.getLogger("auth")

@router.post("/api/auth/login")
async def unified_login(...):
    # ... authentication logic ...
    
    if success:
        auth_logger.info(
            f"Login success: user={username}, method=password, ip={request.client.host}"
        )
    else:
        auth_logger.warning(
            f"Login failed: user={username}, ip={request.client.host}"
        )
```

### 5. Failed Login Lockout

**Current Implementation:**
- No account lockout after failed attempts

**Recommendations:**
```python
from collections import defaultdict
import time

failed_attempts = defaultdict(list)

def check_login_attempts(username: str, ip: str) -> bool:
    """Check if user/IP is locked out"""
    key = f"{username}:{ip}"
    attempts = failed_attempts[key]
    
    # Remove attempts older than 15 minutes
    cutoff = time.time() - 900
    attempts = [t for t in attempts if t > cutoff]
    failed_attempts[key] = attempts
    
    # Lock out after 5 failed attempts
    if len(attempts) >= 5:
        return False  # Locked out
    
    return True  # Allowed

def record_failed_attempt(username: str, ip: str):
    """Record a failed login attempt"""
    key = f"{username}:{ip}"
    failed_attempts[key].append(time.time())
```

---

## Extending the System

### Adding a New User Role

**Step 1: Update User Model**
```python
# backend/auth/models.py
class User(Base):
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String)  # 'admin', 'moderator', 'member'
    mitglied_id = Column(Integer, nullable=True)
```

**Step 2: Add Role Check**
```python
# backend/auth/dependencies.py
def is_moderator(request: Request) -> bool:
    """Check if user has moderator role"""
    session = request.session
    if not session.get("user"):
        return False
    
    username = session.get("user")
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        return user and user.role == "moderator"
    finally:
        db.close()
```

**Step 3: Use in Routes**
```python
@router.get("/api/moderator/endpoint")
async def moderator_endpoint(request: Request):
    if not is_moderator(request):
        raise HTTPException(status_code=403, detail="Moderator access required")
    # Business logic
    ...
```

### Adding OAuth Integration

**Step 1: Install Dependencies**
```bash
uv add authlib python-multipart
```

**Step 2: Add OAuth Configuration**
```python
# backend/config.py
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")
```

**Step 3: Add OAuth Routes**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id=OAUTH_CLIENT_ID,
    client_secret=OAUTH_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@router.get("/login/google")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(request, OAUTH_REDIRECT_URI)

@router.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.parse_id_token(request, token)
    
    # Create session from OAuth user info
    request.session["user"] = user_info["email"]
    request.session["login_method"] = "oauth"
    # ... rest of session setup ...
    
    return RedirectResponse("/member")
```

### Adding Two-Factor Authentication (2FA)

**Step 1: Install Dependencies**
```bash
uv add pyotp
```

**Step 2: Add 2FA Fields to User Model**
```python
# backend/auth/models.py
class User(Base):
    # ... existing fields ...
    totp_secret = Column(String, nullable=True)  # TOTP secret
    totp_enabled = Column(Boolean, default=False)
```

**Step 3: Add 2FA Setup Endpoint**
```python
import pyotp

@router.post("/api/auth/2fa/setup")
async def setup_2fa(request: Request, db: Session = Depends(get_db)):
    username = request.session.get("user")
    user = db.query(User).filter(User.username == username).first()
    
    # Generate secret
    secret = pyotp.random_base32()
    user.totp_secret = secret
    db.commit()
    
    # Return QR code URL
    totp = pyotp.TOTP(secret)
    qr_url = totp.provisioning_uri(
        name=username,
        issuer_name="MakerPi GroundControl"
    )
    
    return {"qr_url": qr_url, "secret": secret}
```

**Step 4: Add 2FA Verification**
```python
@router.post("/api/auth/2fa/verify")
async def verify_2fa(request: Request, code: str, db: Session = Depends(get_db)):
    username = request.session.get("user")
    user = db.query(User).filter(User.username == username).first()
    
    if not user.totp_secret:
        return {"success": False, "error": "2FA not enabled"}
    
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(code):
        return {"success": False, "error": "Invalid code"}
    
    # Enable 2FA
    user.totp_enabled = True
    db.commit()
    
    return {"success": True}
```

**Step 5: Integrate into Login Flow**
```python
@router.post("/api/auth/login")
async def unified_login(...):
    # ... existing password verification ...
    
    # Check if 2FA enabled
    if user.totp_enabled:
        # Return requiring 2FA code
        return {"require_2fa": True}
    
    # Normal login flow
    ...
```

### Adding Session Storage Backend

**Current:** In-memory session storage (default Starlette)

**Option 1: Redis Session Storage**
```python
from starlette_session.backends.redis import RedisSessionBackend

app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    backend=RedisSessionBackend(
        redis_url="redis://localhost:6379",
        prefix="session:"
    )
)
```

**Option 2: Database Session Storage**
```python
from starlette_session.backends.redis import RedisSessionBackend

# Custom database backend
class DatabaseSessionBackend:
    def __init__(self, db_url: str):
        self.db_url = db_url
    
    async def get_session(self, session_id: str):
        # Fetch from database
        ...
    
    async def set_session(self, session_id: str, data: dict):
        # Store in database
        ...
    
    async def delete_session(self, session_id: str):
        # Delete from database
        ...
```

---

## Troubleshooting

### Common Issues

#### 1. Session Not Persisting

**Symptoms:** User gets logged out immediately after login

**Causes:**
- `SECRET_KEY` changes between restarts
- Cookie domain/path mismatch
- Browser blocking cookies

**Solutions:**
```python
# Use consistent SECRET_KEY
SECRET_KEY = os.getenv("SECRET_KEY") or "development-key-change-in-production"

# Check cookie configuration
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="session",
    domain=None,  # Use None for current domain
    path="/",     # Root path
)
```

#### 2. Admin Verification Fails

**Symptoms:** Admin users can't access admin dashboard

**Causes:**
- `is_admin_capable` not set correctly
- Admin verification timeout expired
- Password verification failing

**Debug:**
```python
# Check session state
@router.get("/api/auth/debug-session")
async def debug_session(request: Request):
    return {
        "session": dict(request.session),
        "admin_verified": is_admin_verified(request),
        "admin_capable": request.session.get("is_admin_capable"),
    }
```

#### 3. RFID Login Not Working

**Symptoms:** RFID scan doesn't log user in

**Causes:**
- UID not in database
- Tag not active
- Member has no login_username

**Debug:**
```python
# Check RFID tag status
@router.get("/api/auth/debug-rfid/{uid}")
async def debug_rfid(uid: str):
    from backend.members.db import get_db as get_members_db
    from backend.members.models import Mitglied, RFIDTag
    
    members_db = next(get_members_db())
    try:
        uid_upper = uid.upper()
        
        # Check Mitglied.nfc_uid
        mitglied = members_db.query(Mitglied).filter(
            Mitglied.nfc_uid == uid_upper
        ).first()
        
        if mitglied:
            return {
                "source": "Mitglied.nfc_uid",
                "found": True,
                "login_username": mitglied.login_username,
                "has_login": bool(mitglied.login_username)
            }
        
        # Check RFIDTag
        tag = members_db.query(RFIDTag).filter(
            RFIDTag.uid == uid_upper
        ).first()
        
        if tag:
            return {
                "source": "RFIDTag",
                "found": True,
                "active": bool(tag.active),
                "is_admin": bool(tag.is_admin)
            }
        
        return {"found": False}
    finally:
        members_db.close()
```

---

## Performance Considerations

### Database Query Optimization

**Current:**
```python
# Separate database queries for auth and member data
user = db.query(User).filter(User.username == username).first()
mitglied = members_db.query(Mitglied).filter(
    Mitglied.login_username == username
).first()
```

**Optimization:**
```python
# Single query with join (if databases were merged)
user = db.query(User).join(Mitglied).filter(
    User.username == username
).first()
```

### Session Storage Performance

**Current:** In-memory storage (fast but not scalable)

**Considerations:**
- Single server: In-memory is fine
- Multiple servers: Use Redis or database backend
- Session size: Keep session data minimal

### Password Hashing Performance

**Current:** bcrypt (intentionally slow)

**Trade-offs:**
- **Security:** Slow hashing prevents brute force
- **Performance:** Adds ~100-200ms per login
- **Acceptable:** Login is infrequent operation

**Optimization:**
```python
# Use Argon2id for better security/performance balance
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto"
)
```

---

## Testing Authentication

### Unit Tests

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_login_success():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    assert response.status_code == 200
    assert "session" in response.cookies

def test_login_failure():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrong"}
    )
    assert response.status_code == 302  # Redirect with error

def test_protected_endpoint_without_auth():
    response = client.get("/api/buchhaltung/summary")
    assert response.status_code == 401

def test_protected_endpoint_with_auth():
    # Login first
    client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin"}
    )
    # Access protected endpoint
    response = client.get("/api/buchhaltung/summary")
    assert response.status_code == 200
```

### Integration Tests

```python
def test_admin_verification_flow():
    client = TestClient(app)
    
    # 1. Login as admin
    client.post("/api/auth/login", data={
        "username": "admin",
        "password": "admin"
    })
    
    # 2. Try to access admin endpoint (should fail without verification)
    response = client.get("/admin/users")
    assert response.status_code == 302  # Redirect to verify
    
    # 3. Verify admin
    response = client.post("/api/auth/verify-admin", data={
        "password": "admin"
    })
    assert response.json()["success"] == True
    
    # 4. Access admin endpoint (should succeed)
    response = client.get("/admin/users")
    assert response.status_code == 200
```

---

## Summary

The MakerPi GroundControl authentication system provides:

✅ **Secure session-based authentication** with HTTP-only cookies
✅ **Two-level authentication** for sensitive operations
✅ **Multiple user types** (admin, member, hybrid)
✅ **RFID tag support** for physical access
✅ **Automatic timeout** for security
✅ **Activity tracking** for session management
✅ **Password hashing** with bcrypt
✅ **Flexible architecture** for extensions

The system balances security with usability, providing appropriate protection for different operation sensitivity levels while maintaining a smooth user experience for legitimate users.
