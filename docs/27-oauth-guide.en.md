# OAuth (Open Authorization) - Comprehensive Guide

This document provides a comprehensive overview of OAuth 2.0, covering concepts, flows, security, and best practices for learning purposes.

---

## Table of Contents

1. [What is OAuth?](#what-is-oauth)
2. [History and Motivation](#history-and-motivation)
3. [OAuth 2.0 vs OAuth 1.0](#oauth-20-vs-oauth-10)
4. [Core Concepts](#core-concepts)
5. [OAuth 2.0 Architecture](#oauth-20-architecture)
6. [Grant Types](#grant-types)
7. [Security Considerations](#security-considerations)
8. [Best Practices](#best-practices)
9. [Common Pitfalls](#common-pitfalls)
10. [Real-World Examples](#real-world-examples)
11. [Implementing OAuth](#implementing-oauth)
12. [Testing OAuth](#testing-oauth)

---

## What is OAuth?

**OAuth (Open Authorization)** is an open standard for access delegation. It provides a secure and standardized way for users to grant third-party applications limited access to their resources without sharing their credentials.

### Key Characteristics

- **Delegation-based**: Users authorize applications to act on their behalf
- **Token-based**: Uses access tokens instead of credentials
- **Standardized**: RFC 6749 / RFC 6750 (OAuth 2.0)
- **Flexible**: Supports multiple authorization flows
- **Secure**: Designed with security best practices

### What OAuth Solves

**Problem: Password Anti-Pattern**

Before OAuth, applications used this insecure pattern:

```
┌─────────────┐
│  User       │  "Here's my password"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  App        │  Stores password
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Third-Party │  Uses password to access resources
└─────────────┘
```

**Risks:**
- Password stored in multiple places
- If app is compromised, attacker gets password
- User must change password everywhere
- No granular control over permissions
- No way to revoke access without changing password

**OAuth Solution:**

```
┌─────────────┐
│  User       │  "I authorize this app to access my data"
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  App        │  Receives authorization code
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  OAuth      │  Exchanges code for access token
│  Server     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  App        │  Uses access token to access resources
└─────────────┘
```

**Benefits:**
- User never shares password with app
- Access can be revoked without changing password
- Granular permissions (scopes)
- Time-limited access
- Can revoke access anytime

---

## History and Motivation

### Before OAuth (2007)

**The Problem:**
- Every application needed full credentials
- Users had to share passwords with many apps
- Security risk was proportional to number of apps
- No standard way to delegate limited access

**Example Scenario:**
```
User wants to use:
- Photo printing service
- Calendar integration
- Social media sharing

Before OAuth:
- Must give each service full email password
- If any service is compromised, email is compromised
- No way to revoke access without changing password
```

### OAuth 1.0 (2007)

**First OAuth Standard**
- Introduced signature-based security
- Complex cryptographic requirements
- Difficult to implement correctly
- Security vulnerabilities discovered

**Issues:**
- Required cryptographic signatures
- Complex to implement correctly
- Session fixation attacks
- Token leakage vulnerabilities

### OAuth 2.0 (2012)

**Simplified OAuth**
- Removed signatures
- Added bearer tokens
- Simplified implementation
- Added new grant types
- Became industry standard

**Key Improvements:**
- Easier to implement
- Better security profile
- More flexible grant types
- Mobile-friendly

---

## OAuth 2.0 vs OAuth 1.0

### Comparison Table

| Feature | OAuth 1.0 | OAuth 2.0 |
|---|---|---|
| Tokens | Request tokens + access tokens | Access tokens + refresh tokens |
| Security | Cryptographic signatures | TLS (HTTPS) + bearer tokens |
| Complexity | High (signatures, callbacks) | Low (simple HTTP) |
| Mobile Support | Difficult | Native support |
| Revocation | Token revocation endpoint | Token revocation endpoint |
| Standard | RFC 5849 | RFC 6749 |

### OAuth 1.0 Flow (Simplified)

```
1. Request Token
   ┌─────────┐
   │  App     │ → Consumer Key + Secret
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  OAuth   │ → Request Token (signed)
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  App     │ → Redirects user to OAuth
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  User     │ → Approves request
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  OAuth   │ → Access Token (signed)
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  App     │ → Uses access token
   └─────────┘
```

### OAuth 2.0 Flow (Simplified)

```
1. Authorization Code
   ┌─────────┐
   │  App     │ → Client ID + Redirect URI
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  OAuth   │ → Redirects user to login
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  User     │ → Approves request
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  OAuth   │ → Authorization Code
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  App     │ → Exchanges code for access token
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  App     │ → Uses access token
   └─────────┘
```

**Key Difference:** OAuth 2.0 removed cryptographic signatures and relies on HTTPS for security.

---

## Core Concepts

### 1. Roles

OAuth defines four roles:

#### Resource Owner
- The entity that owns the protected resources
- Typically an end-user
- Grants access to their resources

Example: A user who owns their Google Calendar data

#### Client
- The application requesting access to resources
- Can be a web app, mobile app, or desktop app
- Must be registered with the OAuth server

Example: A calendar integration app

#### Authorization Server
- The server that issues access tokens
- Validates resource owner consent
- Manages client registrations
- Can be the same as the resource server

Example: Google's OAuth 2.0 server

#### Resource Server
- The server hosting the protected resources
- Validates access tokens
- Serves the requested resources

Example: Google Calendar API

### 2. Tokens

#### Access Token
- Short-lived token used to access resources
- Represents the authorization grant
- Sent in HTTP Authorization header
- Has associated scopes (permissions)

**Example:**
```
Authorization: Bearer ya29.a0AfH6S2W...
```

#### Refresh Token
- Long-lived token used to obtain new access tokens
- Stored securely by the client
- Allows access without user re-authorization
- Can be revoked

**Example:**
```json
{
  "access_token": "ya29.a0AfH6S2W...",
  "refresh_token": "1//0fG...",
  "expires_in": 3600
}
```

#### ID Token (OpenID Connect)
- Represents user identity
- Contains user information (name, email, etc.)
- Signed by the authorization server
- Used for authentication

**Example:**
```json
{
  "iss": "https://accounts.google.com",
  "sub": "123456789",
  "name": "John Doe",
  "email": "john@example.com"
}
```

### 3. Scopes

Scopes define the level of access requested:

**Example Scopes:**
```
- read:calendar - Read calendar events
- write:calendar - Create/update calendar events
- profile - Access user profile information
- email - Access user email address
```

**Scope Format:**
```
scope1 scope2 scope3
```

### 4. Authorization Code

- Temporary code issued by authorization server
- Exchanged for access token
- Single-use (expires after use)
- Prevents token interception

**Example:**
```
https://example.com/callback?code=4/A0AfH6S2W...
```

### 5. State Parameter

- Random string generated by client
- Sent to authorization server and returned in callback
- Prevents CSRF attacks
- Verifies callback is legitimate

**Example:**
```
https://example.com/callback?code=...&state=xyz123
```

---

## OAuth 2.0 Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Resource Owner (User)                     │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Browser / Mobile App                              │    │
│  │  - User sees authorization screen                    │    │
│  │  - Approves or denies request                         │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Authorization Server (OAuth)                │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Client Registration Database                          │    │
│  │  - Client ID, Client Secret                          │    │
│  │  - Redirect URIs                                      │    │
│  │  - Allowed Scopes                                    │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Authorization Endpoint                             │    │
│  │  - /authorize                                       │    │
│  │  - Shows consent screen to user                      │    │
│  │  - Issues authorization code                         │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Token Endpoint                                     │    │
│  │  - /token                                            │    │
│  │  - Exchanges code for access token                  │    │
│  │  - Issues refresh token                              │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                         Client (App)                          │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Client Credentials                                 │    │
│  │  - Client ID (public)                                 │    │
│  │  - Client Secret (private)                            │    │
│  │  - Redirect URI                                        │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Token Storage                                        │    │
│  │  - Access token (memory, session, database)          │    │
│  │  - Refresh token (secure storage)                     │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  API Client                                          │    │
│  │  - Makes API requests with access token               │    │
│  │  - Handles token refresh                            │    │
│  └──────────────────────────────────────────────────────┘    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Resource Server (API)                       │
│  ┌──────────────────────────────────────────────────────┐    │
│  │  Protected Resources                                  │    │
│  │  - User data, calendar, files, etc.                 │    │
│  └──────────────────────────────────────────────────────┘    │
│  │  ┌─────────────────────────────────────────────────┐    │
│  │  │ Token Validation Endpoint               │    │
│  │  │ - Validates access token                │    │
│  │  │ - Checks scopes                            │    │
│  │  │ - Returns resource if valid              │    │
│  │  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow

```
┌─────────┐         ┌──────────────┐         ┌──────────────┐
│  Client │         │   OAuth      │         │  Resource     │
└────┬────┘         └──────┬───────┘         └──────┬───────┘
     │                     │                      │
     │ 1. Redirect         │                      │
     ├─────────────────────►                      │
     │                     │                      │
     │                     │ 2. Show consent   │
     │                     ├─────────────────────►
     │                     │                      │
     │                     │ 3. Authorization │
     │                     │      Code          │
     │                     ├─────────────────────►
     │                     │                      │
     │ 4. Authorization     │                      │
     │    Code              │                      │
     │◄────────────────────┤                      │
     │                     │                      │
     │ 5. Exchange Code for   │                      │
     │    Access Token       │                      │
     ├─────────────────────►                      │
     │                     │                      │
     │ 6. Access Token       │                      │
     │◄────────────────────┤                      │
     │                     │                      │
     │ 7. Access Resource    │                      │
     │    with Token        ├─────────────────────►
     │                     │                      │
     │ 8. Resource Data      │                      │
     │◄────────────────────┤                      │
```

---

## Grant Types

OAuth 2.0 defines several grant types for different scenarios:

### 1. Authorization Code Grant

**Use Case:** Web applications with server-side backend

**Best For:**
- Traditional web apps
- Applications that can store client secrets securely
- When user is present during authorization

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. Redirect to /authorize
     │    params: client_id, redirect_uri, scope, state
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 2. Show consent screen
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  User        │
└──────┬───────┘
     │
     │ 3. Approve
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 4. Authorization Code
     │    redirect_uri?code=...&state=...
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 5. POST /token
     │    params: code, client_id, client_secret, redirect_uri
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 6. Access Token + Refresh Token
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 7. Use Access Token to access resources
     ├──────────────────────────────────────────────►
```

**Code Example:**
```python
# Step 1: Redirect to authorization
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id="your-client-id",
    client_secret="your-client-secret",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@app.get("/login")
async def login(request: Request):
    return await oauth.google.authorize_redirect(request, "https://example.com/callback")

# Step 2: Handle callback
@app.get("/callback")
async def callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.parse_id_token(request, token)
    # Use access token to make API requests
```

### 2. Implicit Grant

**Use Case:** Browser-based apps (SPAs) without backend

**Best For:**
- Single-page applications
- JavaScript applications
- When client secret cannot be stored securely

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. Redirect to /authorize
     │    params: client_id, redirect_uri, scope, response_type=token
     ├──────────────────────────────────────────────►
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 2. Show consent screen
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  User        │
└──────┬─────┘
     │
     │ 3. Approve
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 4. Access Token
     │    redirect_uri#access_token=...
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 5. Extract access token from URL fragment
     │    Use token to access resources
```

**Note:** Implicit grant is deprecated in favor of Authorization Code with PKCE for SPAs.

### 3. Resource Owner Password Credentials Grant

**Use Case: Legacy applications, trusted first-party apps

**Best For:**
- Legacy applications
- Highly trusted first-party applications
- When user credentials are already known

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. POST /token
     │    params: grant_type=password, username, password, scope
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────┘
     │
     │ 2. Validate credentials
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬─────┘
     │
     │ 3. Access Token
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 4. Use access token to access resources
```

**Security Note:** This grant type should only be used for highly trusted applications. Never use it for third-party apps.

### 4. Client Credentials Grant

**Use Case: Machine-to-machine authentication (no user interaction)

**Best For:**
- Service accounts
   - Background workers
   - CLI tools
   - Daemons

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. POST /token
     │    params: grant_type=client_credentials, client_id, client_secret, scope
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬───────�
     │
     │ 2. Validate client credentials
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└────┬─────┘
     │
     │ 3. Access Token
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 4. Use access token to access resources
```

**Code Example:**
```python
from requests_oauthlib import OAuth2Session

oauth = OAuth2Session("https://oauth.example.com/token",
                          client_id="client_id",
                          client_secret="client_secret")

token = oauth.fetch_token(token_url="https://api.example.com/oauth/token",
                        scope="read write")

# Use token to access API
response = oauth.get("https://api.example.com/resource")
```

### 5. Authorization Code with PKCE

**Use Case: Mobile and native apps, SPAs

**Best For:**
- Mobile applications
- Single-page applications
- Apps that cannot store client secrets
- Apps running on untrusted devices

**Additional Security:**
- Uses Proof Key for Code Exchange (PKCE)
- Prevents authorization code interception attacks
- Requires code verifier and challenge

**Flow:**
```
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 1. Generate code verifier and challenge
     │    code_verifier = random_string()
     │    code_challenge = random_string()
     │    code_challenge_method = "S256"
     │
     │ 2. Redirect to /authorize
     │    params: client_id, redirect_uri, scope, state,
     │             code_challenge, code_challenge_method
     ├──────────────────────────────────────────────►
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└──────┬─────┘
     │
     │ 3. Show consent screen
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  User        │
└──────┬─────┘
     │
     │ 4. Approve
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└────┬─────┘
     │
     │ 5. Authorization Code
     │    redirect_uri?code=...&state=...
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 6. POST /token
     │    params: code, code_verifier, client_id, redirect_uri
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└────┬─────┘
     │
     │ 7. Validate code verifier
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌──────────────┐
│  OAuth       │
│  Server      │
└────┬─────┘
     │
     │ 8. Access Token + Refresh Token
     ├──────────────────────────────────────────────►
     │
     │
     │
     ▼
┌─────────┐
│  Client  │
└────┬────┘
     │
     │ 9. Use access token to access resources
```

### Grant Type Comparison

| Grant Type | User Presence | Client Secret | Use Case | Security |
|---|---|---|---|---|
| Authorization Code | Yes | Yes | Web apps | High |
| Implicit | Yes | No | SPAs (deprecated) | Medium |
| Password | Yes | Yes | Legacy apps | Low (credentials shared) |
| Client Credentials | No | Yes | Service accounts | High (if secrets protected) |
| PKCE | Yes | No | Mobile/SPAs | Very High |

---

## Security Considerations

### 1. HTTPS/TLS

**Critical Requirement:** OAuth 2.0 requires HTTPS for all communications.

**Why:**
- Prevents token interception
- Prevents man-in-the-middle attacks
- Protects sensitive data in transit

**Example:**
```
❌ http://example.com/oauth/authorize
✅ https://example.com/oauth/authorize
```

### 2. State Parameter

**Purpose:** Prevent CSRF (Cross-Site Request Forgery) attacks

**How it works:**
1. Client generates random state string
2. State sent to authorization server
3. Authorization server returns state in callback
4. Client verifies state matches

**Example:**
```python
import secrets

# Generate state
state = secrets.token_urlsafe(16)

# Redirect with state
redirect_uri = f"https://oauth.example.com/authorize?state={state}&..."

# Verify state in callback
if request.args.get("state") != state:
    raise HTTPException(status_code=400, detail="Invalid state")
```

### 3. Token Storage

**Access Token Storage:**
- **Web Apps:** Server-side session or database
- **Mobile Apps:** Secure storage (Keychain/Keystore)
- **SPAs:** Memory (short-lived)

**Refresh Token Storage:**
- **Web Apps:** Encrypted database
- **Mobile Apps:** Secure storage (Keychain/Keystore)
- **Never:** Local storage (localStorage, cookies)

**Example:**
```python
# ✅ Good: Server-side session
request.session["access_token"] = token

# ❌ Bad: Local storage (XSS vulnerable)
localStorage.setItem("access_token", token)
```

### 4. Token Expiration

**Access Token:** Short-lived (typically 1 hour)
**Refresh Token:** Long-lived (days to months)

**Why:**
- Limit exposure if access token is compromised
- Force regular re-authorization
- Allows revocation

**Example:**
```json
{
  "access_token": "ya29.a0AfH6S2W...",
  "expires_in": 3600,
  "refresh_token": "1//0fG...",
  "expires_in": 2592000
}
```

### 5. Scope Limitation

**Principle of Least Privilege:** Request only the scopes you need.

**Example:**
```
❌ Bad: scope="read write delete admin"
✅ Good: scope="read"
```

### 6. PKCE (Proof Key for Code Exchange)

**Purpose:** Prevents authorization code interception attacks

**How it works:**
1. Client generates code verifier
2. Client generates code challenge
3. Authorization server binds code to challenge
4. Only client with verifier can exchange code for token

**Required for:**
- Mobile apps
- SPAs
- Native apps

---

## Best Practices

### 1. Use Authorization Code Grant

**When:** Web applications with server-side backend

**Why:** Most secure, widely supported

**Example:**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```

### 2. Use PKCE for Mobile/SPAs

**When:** Mobile apps, SPAs, native apps

**Why:** Prevents code interception attacks

**Example:**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# PKCE enabled automatically for mobile apps
```

### 3. Validate State Parameter

**Always:** Validate state in callback to prevent CSRF

**Example:**
```python
@app.get("/callback")
async def callback(request: Request):
    # Verify state
    state = request.args.get("state")
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state")
    
    # Process callback
    token = await oauth.google.authorize_access_token(request)
    ...
```

### 4. Store Refresh Tokens Securely

**Web Apps:** Encrypted database
**Mobile Apps:** Keychain/Keystore

**Example:**
```python
# ✅ Good: Encrypted database
from cryptography.fernet import Fernet

f = Fernet(ENCRYPTION_KEY)
encrypted_token = f.encrypt(refresh_token)
db.save(encrypted_token)

# ❌ Bad: Plain text database
db.save(refresh_token)
```

### 5. Implement Token Refresh

**Handle token expiration gracefully:**

```python
def get_access_token():
    if not access_token or access_token_expired():
        refresh_token = get_refresh_token()
        access_token = exchange_refresh_token(refresh_token)
    return access_token
```

### 6. Revoke Tokens on Logout

**Clear tokens when user logs out:**

```python
@app.post("/logout")
async def logout():
    # Revoke token at authorization server
    await oauth.revoke_token(access_token)
    
    # Clear local tokens
    request.session.clear()
```

### 7. Use HTTPS Everywhere

**Never use OAuth over HTTP:**

```python
# ✅ Good
OAUTH_SERVER = "https://accounts.google.com"

# ❌ Bad
OAUTH_SERVER = "http://accounts.google.com"
```

### 8. Validate Tokens

**Validate tokens before use:**

```python
def validate_token(token):
    # Introspect token at authorization server
    response = requests.post(
        "https://oauth.example.com/introspect",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()["active"]
```

### 9. Use Short-Lived Access Tokens

**Typical expiration:** 1 hour or less

**Example:**
```python
# ✅ Good: 1 hour expiration
expires_in=3600

# ❌ Bad: 30 day expiration
expires_in=2592000
```

### 10. Request Minimal Scopes

**Only request what you need:**

```python
# ✅ Good: Minimal scopes
scope="read calendar"

# ❌ Bad: Overly broad scopes
scope="read write delete admin"
```

---

## Common Pitfalls

### 1. Using Implicit Grant for SPAs

**Problem:** Implicit grant is deprecated, less secure

**Solution:** Use Authorization Code with PKCE

**Example:**
```python
# ❌ Deprecated
response_type="token"

# ✅ Modern
response_type="code"
code_challenge=S256
code_verifier=...
```

### 2. Storing Tokens in Local Storage

**Problem:** XSS vulnerabilities, token theft

**Solution:** Store tokens server-side or in secure storage

**Example:**
```python
# ❌ Vulnerable
localStorage.setItem("access_token", token)

# ✅ Secure
request.session["access_token"] = token
```

### 3. Not Validating State Parameter

**Problem:** CSRF attacks

**Solution:** Always validate state in callback

**Example:**
```python
# ❌ Vulnerable
@app.get("/callback")
async def callback(request: Request):
    code = request.args.get("code")
    # Process callback without state validation

# ✅ Secure
@app.get("/callback")
async def callback(request: Request):
    state = request.args.get("state")
    if state != request.session.get("oauth_state"):
        raise HTTPException(status_code=400, detail="Invalid state")
    code = request.args.get("code")
    # Process callback
```

### 4. Using HTTP Instead of HTTPS

**Problem:** Token interception, man-in-the-middle attacks

**Solution:** Always use HTTPS

**Example:**
```python
# ❌ Insecure
OAUTH_SERVER = "http://accounts.google.com"

# ✅ Secure
OAUTH_SERVER = "https://accounts.google.com"
```

### 5. Not Implementing Token Refresh

**Problem:** Poor UX, users must re-authorize frequently

**Solution:** Implement automatic token refresh

**Example:**
```python
def refresh_access_token_if_expired():
    if token_expired():
        new_token = refresh_token_endpoint()
        update_stored_token(new_token)
```

### 6. Hardcoding Client Secrets

**Problem:** Secrets exposed in code, difficult to rotate

**Solution:** Use environment variables

**Example:**
```python
# ❌ Insecure
CLIENT_SECRET = "abc123xyz"

# ✅ Secure
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
```

### 7. Not Revoking Tokens on Logout

**Problem:** Tokens remain valid until expiration

**Solution:** Revoke tokens at authorization server

**Example:**
```python
@app.post("/logout")
async def logout():
    # Revoke at authorization server
    await oauth.revoke_token(access_token)
    # Clear local tokens
    request.session.clear()
```

### 8. Requesting Too Many Scopes

**Problem:** Over-privileged tokens, security risk

**Solution:** Request minimal scopes

**Example:**
```python
# ❌ Over-privileged
scope="read write delete admin"

# ✅ Minimal
scope="read"
```

### 9. Not Validating Tokens

**Problem:** Invalid tokens may be used if not validated

**Solution:** Validate tokens at authorization server

**Example:**
```python
def validate_token(token):
    response = requests.post(
        "https://oauth.example.com/introspect",
        headers={"Authorization": f"Bearer {token}"}
    )
    if not response.json()["active"]:
        raise Exception("Invalid token")
```

### 10. Using Password Grant for Third-Party Apps

**Problem:** Credentials shared with third party

**Solution:** Use Authorization Code Grant

**Example:**
```python
# ❌ Insecure for third-party
grant_type="password"

# ✅ Secure for third-party
grant_type="authorization_code"
```

---

## Real-World Examples

### Example 1: Google OAuth 2.0

**Scenario:** Web app wants to access user's Google Calendar

**Implementation:**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "google",
    client_id="your-client-id.apps.googleusercontent.com",
    client_secret="your-client-secret",
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

@app.get("/login/google")
async def login_google(request: Request):
    return await oauth.google.authorize_redirect(
        request,
        redirect_uri="https://example.com/auth/callback"
    )

@app.get("/auth/callback")
async def auth_callback(request: Request):
    token = await oauth.google.authorize_access_token(request)
    user_info = await oauth.google.parse_id_token(request, token)
    
    # Create or update user in database
    user = get_or_create_user(user_info)
    
    # Create session
    request.session["user"] = user.email
    request.session["login_method"] = "oauth"
    
    return RedirectResponse("/dashboard")
```

### Example 2: GitHub OAuth 2.0

**Scenario:** App wants to access user's GitHub repositories

**Implementation:**
```python
oauth.register(
    "github",
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    authorize_url="https://github.com/login/oauth/authorize",
    authorize_params={"scope": "user repo"},
    access_token_url="https://github.com/login/oauth/access_token",
)
```

### Example 3: Service Account (Client Credentials)

**Scenario:** Background worker needs to access Google Cloud Storage

**Implementation:**
```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    "service-account.json",
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# Use credentials to access API
storage_client = storage.Client(credentials=credentials)
```

### Example 4: Mobile App with PKCE

**Scenario:** iOS app needs to access user's data

**Implementation:**
```swift
import OAuth2Client
import CryptoSwift

// Generate PKCE verifier and challenge
let verifier = Data.randomBytes(32).base64EncodedString()
let challenge = Data.randomBytes(32).base64EncodedString()

// Redirect to authorization
let authURL = oauth2Client.authorize(
    provider: "google",
    clientID: clientID,
    redirectURI: redirectURI,
    scope: ["openid", "email", "profile"],
    codeChallenge: challenge,
    codeChallengeMethod: "S256",
    codeVerifier: verifier
)
```

---

## Implementing OAuth

### Step 1: Register Application

1. Go to OAuth provider's developer console
2. Create new OAuth 2.0 application
3. Get client ID and client secret
4. Configure redirect URIs
5. Configure scopes

### Step 2: Choose Grant Type

- **Web App:** Authorization Code
- **Mobile App:** Authorization Code with PKCE
- **Service Account:** Client Credentials
- **Legacy App:** Password (if necessary)

### Step 3: Implement OAuth Flow

**For Web App (Authorization Code):**
```python
from authlib.integrations.fastapi_oauthclient import OAuth

oauth = OAuth()
oauth.register(
    "provider",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    server_metadata_url="https://provider.example.com/.well-known/openid-configuration",
    client_kwargs={"scope": "scope1 scope2"},
)

@app.get("/login")
async def login(request: Request):
    return await oauth.provider.authorize_redirect(request, REDIRECT_URI)

@app.get("/callback")
async def callback(request: Request):
    token = await oauth.provider.authorize_access_token(request)
    # Create session, redirect to app
```

**For Mobile App (PKCE):**
```python
# PKCE is automatic for mobile apps
oauth.register(
    "provider",
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    # PKCE is automatic
)
```

### Step 4: Handle Token Refresh

```python
def refresh_access_token():
    refresh_token = get_stored_refresh_token()
    new_token = oauth.provider.refresh_token(refresh_token)
    update_stored_tokens(new_token)
```

### Step 5: Use Access Token

```python
def get_api_data():
    access_token = get_stored_access_token()
    response = requests.get(
        "https://api.example.com/resource",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    return response.json()
```

---

## Testing OAuth

### Unit Tests

```python
def test_oauth_redirect():
    response = client.get("/login")
    assert response.status_code == 302
    assert "accounts.google.com" in response.headers["location"]

def test_oauth_callback():
    # Mock OAuth provider
    with patch("authlib.integrations.fastapi_oauthclient") as mock_oauth:
        mock_oauth.google.authorize_access_token.return_value = {
            "access_token": "test_token"
        }
        
        response = client.get("/callback?code=test_code")
        assert response.status_code == 200
```

### Integration Tests

```python
def test_full_oauth_flow():
    # 1. Start authorization
    response = client.get("/login")
    assert response.status_code == 302
    
    # 2. Simulate user approval (in test environment)
    # 3. Simulate callback
    # 4. Verify token is stored
    # 5. Verify API access works with token
```

### Security Tests

```python
def test_state_parameter():
    # Test CSRF protection
    response = client.get("/callback?code=test&state=invalid")
    assert response.status_code == 400

def test_https_required():
    # Test that HTTP is required
    with pytest.raises(Exception):
        oauth.register(
            "provider",
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            server_metadata_url="http://provider.example.com"  # HTTP!
        )

def test_token_storage():
    # Test tokens are stored securely
    # Check for plaintext tokens in database
    # Check for tokens in logs
    # Check for tokens in frontend code
```

---

## Summary

OAuth 2.0 is a powerful standard for secure authorization delegation. Key takeaways:

### ✅ Benefits
- **Security:** No password sharing, token-based access
- **Flexibility:** Multiple grant types for different scenarios
- **Control:** Granular scopes, revocable access
- **Standardization:** Industry-wide support

### ⚠️ Key Security Requirements
- **HTTPS:** Required for all communications
- **State Parameter:** Prevents CSRF attacks
- **PKCE:** Required for mobile/SPAs
- **Secure Storage:** Protect refresh tokens
- **Token Validation:** Validate tokens at authorization server

### 🎯 Best Practices
- Use Authorization Code for web apps
- Use PKCE for mobile/SPAs
- Use Client Credentials for service accounts
- Always validate state parameter
- Store tokens securely
- Implement token refresh
- Request minimal scopes
- Revoke tokens on logout

### 🚀 When to Use OAuth
- Third-party app integration
- Mobile app authentication
- Service account authentication
- API access delegation
- Social login (Google, Facebook, etc.)

OAuth 2.0 is the industry standard for secure authorization and should be used whenever an application needs to access user resources on behalf of the user.
