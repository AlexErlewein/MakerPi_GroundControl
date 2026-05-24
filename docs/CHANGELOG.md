# Changelog

All notable changes to MakerPi GroundControl will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Member Registration API** - Public member registration form at `/register` with easyVerein integration
  - Web form for new member applications
  - Automatic creation of member records in easyVerein (if configured)
  - Local fallback when easyVerein is unavailable
  - Email validation and duplicate detection
  - Privacy policy acceptance requirement
  - Configurable membership groups and payment intervals

- **Email Enhancements**
  - H3cke logo SVG added to email templates
  - Welcome email with direct link when guests create Laufzettel
  - Gmail OAuth2 authentication support
  - Improved email sending with fallback mechanisms

- **Guest Laufzettel Improvements**
  - Public view-only Laufzettel page accessible via email link
  - QR code for guest access (PNG and SVG formats)
  - Session persistence for guest users
  - Previous day reminder for unpaid Laufzettel

- **Backup System**
  - Multi-database backup script in Database_Backup folder
  - Daily core.db backup with Google Drive 3-backup rotation
  - Proper SQLite backup API usage with integrity checks

- **MQTT Message Filtering**
  - Filter to skip heartbeat and status update messages in storage
  - Reduced database load from routine MQTT traffic

### Changed
- **Email URLs** - Use Pi IP address instead of public domain for email links
- **Google Drive** - Renamed folder from 'Laufzettel' to 'Digitale Laufzettel'
- **UI Cleanup** - Removed extra 'Open Google Drive' button from dashboard (use clickable tile link instead)

### Fixed
- Indentation error in Wero payment route
- Deploy.sh now installs uv automatically if missing
- Database corruption handling with proper backup API

### Configuration
- Added `easyverein_registration_mock` for testing member registration
- Added `membership_groups` configuration for registration form
- Added `easyverein_signup_redirect_url` for external signup flows
- Added Gmail OAuth2 configuration options
- Added Google Drive backup configuration

## [Previous Versions]

### Documentation
- Added comprehensive Gmail OAuth2 setup guide
- Added Gmail OAuth2 deployment guide for Raspberry Pi
- Added guest Laufzettel documentation
- Added backup documentation (Litestream + rclone)
- Added configuration reference documentation

### Infrastructure
- Auto-deploy timer installation script
- Manual auto-deploy trigger via systemctl
- OAuth token synchronization scripts
- Diagnostic tools for email and OAuth troubleshooting