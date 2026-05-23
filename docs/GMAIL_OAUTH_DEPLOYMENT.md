# Gmail OAuth2 Deployment Guide for Raspberry Pi

This guide explains how to deploy the Gmail OAuth2 email functionality to the Raspberry Pi.

## What Needs to Be Deployed

### 1. Code Changes (deployed via git)
- `backend/email_utils.py` - OAuth2 support with Gmail API fallback
- `backend/config.py` - OAuth2 configuration parameters
- `static/js/app.js` - Google Drive dashboard link
- `backend/core/routes.py` - Google Drive URL in status

### 2. Configuration Files (must be manually synced)
These files are NOT tracked by git (security reasons) and need to be manually copied:

- `config/config.json` - Updated with Gmail OAuth2 settings
- `config/gmail_oauth_token.json` - OAuth access/refresh tokens
- `config/gmail_oauth_client_secrets.json` - OAuth client credentials
- `config/gdrive_token.json` - Google Drive access tokens
- `config/gdrive_client_secrets.json` - Google Drive OAuth client

## Deployment Steps

### Step 1: Sync OAuth Config Files

```bash
# Make the sync script executable
chmod +x scripts/sync-oauth-config.sh

# Run the sync script
./scripts/sync-oauth-config.sh
```

This will copy all OAuth configuration files to the Pi using SCP.

### Step 2: Commit and Push Code Changes

```bash
# Commit your changes
git add -A
git commit -m "Add Gmail OAuth2 support with noreply@h3cke.de"

# Push to origin
git push
```

### Step 3: Deploy to Pi

```bash
# Deploy with dependency updates (recommended)
./scripts/deploy.sh --update-deps
```

This will:
1. Pull the latest code from git
2. Update Python dependencies (includes google-api-python-client)
3. Restart the GroundControl service

### Step 4: Verify Deployment

```bash
# SSH into the Pi
ssh dev@192.168.3.228  # or your Pi's IP

# Check service status
sudo systemctl status groundcontrol

# Check logs for email sending
sudo journalctl -u groundcontrol -f | grep -i email

# Test on the Pi (optional)
cd /home/dev/Code/MakerPi_GroundControl
.venv/bin/python scripts/test_gmail_oauth.py
```

## Troubleshooting

### Email Not Sending on Pi

**Check config files exist:**
```bash
ssh dev@192.168.3.228 "ls -la ~/Code/MakerPi_GroundControl/config/gmail_oauth*.json"
```

**Check config.json has correct settings:**
```bash
ssh dev@192.168.3.228 "cat ~/Code/MakerPi_GroundControl/config/config.json" | jq '.gmail_oauth_enabled, .gmail_oauth_username, .smtp_from_email'
```

**Check logs:**
```bash
ssh dev@192.168.3.228 "sudo journalctl -u groundcontrol -n 50 | grep -A 5 -i email"
```

### Google Drive Not Working

**Re-authenticate on Pi:**
```bash
ssh dev@192.168.3.228
cd ~/Code/MakerPi_GroundControl
.venv/bin/python scripts/gdrive_auth.py
```

### Dependencies Missing

**Update dependencies:**
```bash
ssh dev@192.168.3.228
cd ~/Code/MakerPi_GroundControl
uv sync
```

## Quick Reference

| What | How |
|------|-----|
| Sync config files | `./scripts/sync-oauth-config.sh` |
| Deploy code | `./scripts/deploy.sh --update-deps` |
| Check status | `ssh pi@ip 'sudo systemctl status groundcontrol'` |
| View logs | `ssh pi@ip 'sudo journalctl -u groundcontrol -f'` |
| Test email | `ssh pi@ip 'cd ~/Code/MakerPi_GroundControl && .venv/bin/python scripts/test_gmail_oauth.py'` |

## Security Notes

- **Never commit** OAuth token files to git
- The token files are already in `.gitignore`
- If tokens are compromised, revoke access at:
  - Gmail: https://myaccount.google.com/permissions
  - Re-run: `python scripts/generate_gmail_oauth_token.py`
- Keep `config/` directory permissions restricted (only Pi user should have read access)

## What Happens During Email Sending

1. **Application tries Gmail API first** (supports aliases like noreply@h3cke.de)
2. **If API fails**, falls back to SMTP XOAUTH2 (traditional OAuth2)
3. **Token refresh** is automatic when tokens expire
4. **All failures** are logged but don't crash the application

## Files Changed

### Modified
- `backend/email_utils.py` - Added OAuth2 support and Gmail API integration
- `backend/config.py` - Added GMAIL_OAUTH_* parameters
- `static/js/app.js` - Added Google Drive link functionality
- `backend/core/routes.py` - Added Google Drive URL to status
- `config.json` - Added Gmail OAuth2 settings
- `.gitignore` - Added OAuth token files
- `config.json.example` - Updated with OAuth2 example

### New
- `scripts/generate_gmail_oauth_token.py` - OAuth token generator
- `scripts/test_gmail_oauth.py` - Email testing script
- `scripts/diagnose_gmail_oauth.py` - Diagnostic tool
- `scripts/sync-oauth-config.sh` - Config sync script
- `docs/GMAIL_OAUTH_SETUP.md` - Setup documentation
- `config/gmail_oauth_token.json` - OAuth tokens (gitignored)
- `config/gmail_oauth_client_secrets.json` - OAuth credentials (gitignored)

## Support

If issues arise:
1. Check logs: `sudo journalctl -u groundcontrol -f`
2. Run diagnostic: `scripts/diagnose_gmail_oauth.py`
3. Test email: `scripts/test_gmail_oauth.py`
4. Re-auth: `scripts/generate_gmail_oauth_token.py`