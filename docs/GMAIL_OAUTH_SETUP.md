# Gmail OAuth2 Setup Guide for H3cke GroundControl

This guide explains how to set up Gmail OAuth2 authentication for sending emails from H3cke GroundControl using a `noreply@h3cke.de` address.

## Overview

OAuth2 is Google's recommended authentication method for Gmail SMTP. It's more secure than password authentication and is now required by Google.

## Prerequisites

- Google Workspace admin access (for h3cke.de domain)
- Ability to create/edit users in Google Workspace
- Google Cloud Console access

## Step 1: Create noreply@h3cke.de Address

### Option A: Email Alias (Recommended)
1. Go to [Google Workspace Admin Console](https://admin.google.com/)
2. Navigate to **Directory > Users**
3. Find your main account (e.g., `alex@h3cke.de`)
4. Click the user → **User information** → **Email aliases**
5. Click **Add alias** and enter `noreply@h3cke.de`
6. Click **Save**

### Option B: Dedicated User
1. Go to **Directory > Users** → **Add new user**
2. Fill in:
   - First name: "No", Last name: "Reply"
   - Primary email: `noreply@h3cke.de`
   - Set a temporary password (you'll need this for OAuth setup)
3. Assign licenses and groups as needed
4. Click **Add user**

## Step 2: Google Cloud Console Setup

1. **Create Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create new project or select existing one

2. **Enable Gmail API**
   - Navigate to **APIs & Services > Library**
   - Search for "Gmail API"
   - Click **Enable**

3. **Configure OAuth Consent Screen**
   - Go to **Google Auth Platform > Branding**
   - Click **Get Started** or **Edit App**
   - **App Information**:
     - App name: "H3cke GroundControl"
     - User support email: `noreply@h3cke.de` (or your admin email)
     - Developer contact: your email
   - **Audience**: Select **Internal** (easiest for Google Workspace)
   - **Data Access**: Click **Add or Remove Scopes**
   - Add scope: `https://www.googleapis.com/auth/gmail.send`
   - Complete the consent screen setup

4. **Create OAuth Credentials**
   - Go to **Google Auth Platform > Clients**
   - Click **Create Client**
   - **Application type**: Web application
   - **Name**: "H3cke GroundControl OAuth"
   - **Authorized redirect URIs**: Add `http://localhost:8080`
   - Click **Create**
   - **Download the client secret JSON** immediately - it's only shown once!

## Step 3: Store OAuth Client Secrets

1. Create file: `config/gmail_oauth_client_secrets.json`
2. Paste the downloaded JSON content
3. The file should look like this:
   ```json
   {
     "web": {
       "client_id": "123456789-abc123def456.apps.googleusercontent.com",
       "client_secret": "GOCSPX-AbCdEfGhIjKlMnOpQrStUvWxYz",
       "redirect_uris": ["http://localhost:8080"],
       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
       "token_uri": "https://oauth2.googleapis.com/token"
     }
   }
   ```
4. **Important**: This file is already in `.gitignore`, so it won't be committed

## Step 4: Generate OAuth2 Token

1. **Install required packages** (if not already installed):
   ```bash
   uv sync
   ```

2. **Run the token generator script**:
   ```bash
   python scripts/generate_gmail_oauth_token.py
   ```

3. **Follow the prompts**:
   - A browser window will open with Google's OAuth consent screen
   - Sign in with `noreply@h3cke.de` (or the account that has the noreply alias)
   - Grant permission to send email
   - Copy the authorization code from the redirected URL
   - Paste it into the terminal when prompted

4. The script will create `config/gmail_oauth_token.json` with your credentials

## Step 5: Configure GroundControl

1. Copy `config.json.example` to `config/config.json` (if not already done)
2. Add/update these settings:
   ```json
   {
     "smtp_host": "smtp.gmail.com",
     "smtp_port": 587,
     "smtp_from_email": "noreply@h3cke.de",
     "smtp_starttls": true,
     "gmail_oauth_enabled": true,
     "gmail_oauth_token_file": "config/gmail_oauth_token.json"
   }
   ```

## Step 6: Test Email Sending

Run the test script:
```bash
python scripts/test_gmail_oauth.py your-email@example.com
```

If no email is provided, it will send to `noreply@h3cke.de`.

## How It Works

1. **Initial Setup**: The token generator script creates a refresh token via OAuth flow
2. **Stored Credentials**: The refresh token is stored in `config/gmail_oauth_token.json`
3. **Email Sending**: When sending email:
   - The app loads the refresh token
   - Exchanges it for an access token (valid for 1 hour)
   - Uses the access token to authenticate with Gmail SMTP
   - Automatically refreshes the access token when it expires

## Security Considerations

- **Refresh tokens are long-lived**: Keep `gmail_oauth_token.json` secure
- **Don't commit secrets**: Both `*_client_secrets.json` and `*_token.json` are in `.gitignore`
- **Access tokens rotate**: The app automatically updates the token file with new access tokens
- **Revoke if lost**: If the token file is lost, revoke the app's access and re-run the token generator

## Troubleshooting

### No refresh token received
- Ensure you're using `prompt="consent"` in the OAuth flow
- Revoke existing app permissions: https://myaccount.google.com/permissions
- Re-run the token generator

### Token refresh fails
- Check that the token file exists and is valid JSON
- Verify the refresh token hasn't been revoked
- Re-run the token generator

### Email sending fails
- Check that `gmail_oauth_enabled` is `true` in config
- Verify `smtp_host` is `smtp.gmail.com`
- Check logs for detailed error messages
- Ensure the OAuth app has the `gmail.send` scope

### "redirect_uri_mismatch" error
- Verify the redirect URI matches exactly in Google Cloud Console
- Must be `http://localhost:8080` for the token generator script

## OAuth2 vs Traditional SMTP Auth

The implementation supports both methods:

| Method | When Used | Configuration |
|--------|-----------|---------------|
| OAuth2 | When `gmail_oauth_enabled: true` | Requires `gmail_oauth_token_file` |
| Traditional | When `gmail_oauth_enabled: false` | Requires `smtp_username` and `smtp_password` |

For Gmail, OAuth2 is the recommended method. Traditional auth (app passwords) may be deprecated.

## Additional Resources

- [Google Gmail API Authentication](https://developers.google.com/gmail/api/auth)
- [OAuth2 Consent Screen Setup](https://support.google.com/cloud/answer/10311615)
- [Google Cloud Console](https://console.cloud.google.com/)