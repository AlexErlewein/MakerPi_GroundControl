# OAuth Setup Guide

This guide explains how to set up Google OAuth 2.0 authentication for MakerPi GroundControl.

## Overview

OAuth allows users to log in using their Google account instead of a username/password. This provides:
- **Better UX**: One-click login
- **Security**: No password sharing with the application
- **Mobile-friendly**: Works seamlessly on mobile devices

## Prerequisites

- HTTPS must be configured (see `scripts/setup-https.sh`)
- Google Cloud Console account
- MakerPi GroundControl deployed on your Pi

## Step 1: Google Cloud Console Setup

### 1.1 Create OAuth 2.0 Client ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. Configure the consent screen if prompted:
   - **User Type**: External
   - **App Name**: MakerPi GroundControl
   - **User Support Email**: Your email
   - **Developer Contact**: Your email
6. Add authorized redirect URIs:
   ```
   https://<your-pi-ip>:8443/auth/google/callback
   https://<your-tailscale-domain>/auth/google/callback
   ```
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

### 1.2 Enable Google+ API (if needed)

1. Navigate to **APIs & Services** → **Library**
2. Search for "Google+ API"
3. Enable it (required for user profile access)

## Step 2: Configure MakerPi GroundControl

### 2.1 Update config.json

Edit `config/config.json` on your Pi:

```json
{
    "oauth_enabled": true,
    "oauth_google_client_id": "your-client-id.apps.googleusercontent.com",
    "oauth_google_client_secret": "your-client-secret",
    "oauth_google_redirect_uri": "https://192.168.178.47:8443/auth/google/callback"
}
```

**Important:** Replace `192.168.178.47` with your Pi's actual IP address.

### 2.2 Update Redirect URI in Google Cloud Console

Make sure the redirect URI in Google Cloud Console matches exactly:
- `https://<your-pi-ip>:8443/auth/google/callback`

For Tailscale access, also add:
- `https://<your-tailscale-domain>/auth/google/callback`

## Step 3: Deploy and Test

### 3.1 Sync Dependencies

```bash
cd /home/alex/MakerPi_GroundControl
uv sync
```

### 3.2 Restart Services

```bash
sudo systemctl restart groundcontrol
sudo systemctl restart groundcontrol-docs
```

### 3.3 Test OAuth

1. Open your browser to `https://<your-pi-ip>:8443`
2. You should see a "🔑 Mit Google anmelden" button
3. Click the button
4. You'll be redirected to Google's login page
5. Sign in with your Google account
6. Grant permission to MakerPi GroundControl
7. You should be redirected back to the member area

## Step 4: Verify User Creation

After the first OAuth login, check that the user was created in `auth.db`:

```bash
sqlite_web -H 0.0.0.0 auth.db
```

Navigate to the `users` table and verify:
- `username` = Google email address
- `role` = `member` (default)
- `hashed_password` = empty (OAuth users don't have passwords)

## Step 5: Configure Admin Access (Optional)

If you want OAuth users to have admin access:

### Option 1: Manually Set Role

```bash
sqlite3 auth.db "UPDATE users SET role='admin' WHERE username='your-email@gmail.com';"
```

### Option 2: Create Admin User First

1. Create an admin user via the password login first
2. Then log in via OAuth with the same email
3. The system will merge the accounts (OAuth + password)

## Troubleshooting

### OAuth Button Not Showing

**Problem:** The "Mit Google anmelden" button doesn't appear on the landing page.

**Solution:**
1. Check `config/config.json` has `oauth_enabled: true`
2. Check Client ID and Secret are set
3. Check browser console for errors
4. Verify `/auth/oauth/status` returns `enabled: true`

### Redirect URI Mismatch

**Problem:** Google returns "redirect_uri_mismatch" error.

**Solution:**
1. Check the redirect URI in Google Cloud Console matches exactly
2. Include the port number (e.g., `:8443`)
3. Use HTTPS, not HTTP
4. Check for trailing slashes

### OAuth Not Enabled Error

**Problem:** Browser shows "OAuth is not enabled" error.

**Solution:**
1. Check `config/config.json` has `oauth_enabled: true`
2. Restart the groundcontrol service
3. Check logs: `sudo journalctl -u groundcontrol -f`

### User Not Created

**Problem:** OAuth login succeeds but user is not created in database.

**Solution:**
1. Check database permissions
2. Check logs for database errors
3. Verify `auth.db` is writable
4. Check `backend/auth/oauth.py` for errors

### Session Not Created

**Problem:** OAuth login succeeds but session is not created.

**Solution:**
1. Check `SECRET_KEY` in config is set
2. Check session middleware is working
3. Check browser accepts cookies
4. Verify HTTPS is working (sessions require secure cookies)

## Security Considerations

### Client Secret Security

- Never commit `oauth_google_client_secret` to git
- Store in `config/config.json` (gitignored)
- Use environment variables for production
- Rotate secrets regularly

### HTTPS Requirement

- OAuth 2.0 requires HTTPS
- The system will reject OAuth over HTTP
- Ensure `scripts/setup-https.sh` has been run
- Verify HSTS header is set

### Scope Limitation

The system requests minimal scopes:
- `openid` - User identification
- `email` - Email address
- `profile` - Basic profile info

These are the minimum required for authentication.

### Token Storage

- OAuth tokens are not stored permanently
- Only session data is stored server-side
- Tokens are short-lived (1 hour)
- Session timeout applies (3 minutes inactivity)

## Advanced Configuration

### Multiple OAuth Providers

To add additional OAuth providers (e.g., GitHub, Facebook):

1. Add provider-specific config to `config.py`
2. Register provider in `backend/auth/oauth.py`
3. Add provider-specific routes
4. Update landing page with additional buttons

### Custom Redirect URI

If you use a custom domain:

```json
{
    "oauth_google_redirect_uri": "https://custom-domain.com/auth/google/callback"
}
```

Update the redirect URI in Google Cloud Console accordingly.

### Auto-Verify Admins

By default, OAuth users with `role='admin'` are auto-verified (no password re-entry required). To disable this:

Edit `backend/auth/oauth.py`:

```python
request.session["admin_verified"] = False  # Always require password
```

## Migration from Password-Only

If you have existing password users and want to enable OAuth:

1. Enable OAuth in config
2. Deploy the update
3. Users can choose either login method
4. If a user logs in via OAuth with the same email as their password account, the accounts are merged
5. Password login remains functional

## Testing

### Local Testing

To test OAuth locally:

1. Use `http://localhost:8000` (not HTTPS)
2. Note: OAuth requires HTTPS in production
3. For local testing, you may need to use a proxy or ngrok

### Production Testing

1. Test with a real Google account
2. Test on mobile devices
3. Test with different browsers
4. Test error scenarios (denied access, network error)

## Monitoring

### Check OAuth Status

```bash
curl https://<your-pi-ip>:8443/auth/oauth/status
```

Expected response:
```json
{
    "enabled": true,
    "google_configured": true,
    "redirect_uri": "https://192.168.178.47:8443/auth/google/callback"
}
```

### View OAuth Logs

```bash
sudo journalctl -u groundcontrol -f | grep -i oauth
```

## Summary

OAuth setup involves:
1. Creating OAuth 2.0 Client ID in Google Cloud Console
2. Configuring redirect URIs
3. Updating `config/config.json`
4. Deploying and testing
5. Verifying user creation

The system is designed to be additive - password login remains functional alongside OAuth.

## Additional Resources

- [OAuth 2.0 Documentation](/docs/27-oauth-guide.en.md)
- [Authentication System Documentation](/docs/26-authentication-system.en.md)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
