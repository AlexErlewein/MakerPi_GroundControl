# Authentication

GroundControl has a login-protected admin area. The public welcome page is accessible to anyone; all other pages require a valid session.

## How it works

- Login state is stored in a **signed session cookie** using Starlette's `SessionMiddleware` and `itsdangerous`.
- Passwords are stored as **bcrypt hashes** (`passlib`) in the `users` table in `auth.db`.
- Only **HTML page routes** check for a session. `/api/` endpoints are left open — this is intentional for a local network deployment.
- The `secret_key` in `config/config.json` signs the cookie. If you change this key, all existing sessions are invalidated.

## Route overview

| Route | Public? | Description |
|---|---|---|
| `GET /` | ✅ Yes | Welcome / login page (redirects to `/dashboard` if already logged in) |
| `GET /login` | ✅ Yes | Same as `/` |
| `POST /login` | ✅ Yes | Form submit — sets session, redirects to `/dashboard` |
| `GET /logout` | — | Clears session, redirects to `/` |
| `GET /dashboard` | 🔒 Login | Main dashboard (former `/`) |
| `GET /tags` | 🔒 Login | RFID tag management |
| `GET /laufzettel` | 🔒 Login | Laufzettel list |
| `GET /laufzettel/{id}` | 🔒 Login | Laufzettel detail |
| `GET /katalog` | 🔒 Login | Material catalog |
| `GET /mitglieder` | 🔒 Login | Member database |
| `GET /database` | 🔒 Login | DB overview |
| `GET /admin/users` | 🔒 Login | User management |
| `POST /admin/users/add` | 🔒 Login | Add a new user |
| `POST /admin/users/delete` | 🔒 Login | Delete a user |

## First login

On first startup, if no users exist in the database, a default admin user is created from `config/config.json`:

```json
{
  "admin_username": "admin",
  "admin_password": "changeme"
}
```

**Change this immediately** after first login. The quickest way is to create a new user at `/admin/users`, then delete the default `admin` account.

## User management

Navigate to **Benutzer** in the nav bar (or `/admin/users`) to:

- See all existing users and their creation date
- Add a new user with a username and password
- Delete any user (you cannot delete yourself or the last remaining user)

Two roles exist: **admin** (full access) and **member** (access to own Laufzettel only). Users with `role="member"` and a `mitglied_id` can log in via RFID card or username/password and access `/member` to view and manage their own work orders.

## Config keys

All auth settings live in `config/config.json`:

```json
{
  "secret_key": "change-me-to-a-long-random-string",
  "admin_username": "admin",
  "admin_password": "changeme",
  "easyverein_api_key": "",
  "easyverein_org_id": "",
  "enrollment_reader_id": ""
}
```

| Key | Purpose |
|---|---|
| `secret_key` | Session signing key — **change in production** |
| `admin_username` / `admin_password` | Seeded on first startup if no users exist |
| `easyverein_api_key` / `easyverein_org_id` | Member sync from easyVerein |
| `enrollment_reader_id` | Device ID for dedicated NFC enrollment reader |

To generate a strong secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Security notes

- Sessions expire when the browser closes (no persistent cookie expiry is set).
- API endpoints (`/api/...`) are **not** protected — any device on the network can call them. This is acceptable for a trusted local network. If you need API protection, add a bearer token check to the API routes.
- The docs app on port `8001` has **no authentication** — if exposed via nginx it would be publicly readable. Restrict it at the nginx layer if needed.
