# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - Kid Fax Focus - 2025-12-14

### Breaking Changes
- **Removed web interface**: Kid Fax is now SMS-only (no Flask web server)
- **Removed Flask dependency**: Simplified to core SMS mailbox functionality
- **Removed Netlify/Convex integration**: Local-only application
- **Removed reCAPTCHA**: Not needed for SMS-based system

### Added
- Dedicated Kid Fax README with SMS mailbox focus
- QUICK_START.md - 15-minute setup guide
- SYSTEMD_SETUP.md - Comprehensive systemd service configuration
- TWILIO_SETUP.md - Step-by-step Twilio account setup
- Enhanced printer abstraction documentation in CLAUDE.md
- Better systemd service examples
- Improved configuration guide with section headers
- Archive directory preserving web interface code

### Changed
- README.md completely rewritten for SMS mailbox concept
- CLAUDE.md rewritten for Kid Fax architecture (removed incorrect LibreChat template)
- CONTRIBUTING.md updated for Kid Fax focus (printer testing, SMS features, kid safety)
- AGENTS.md updated to remove web app references
- Simplified `requirements.txt` (removed Flask==3.0.0, Werkzeug==3.0.1)
- Cleaned `.env.example` (removed HOST, PORT, DEBUG web variables)
- Project tagline: "SMS Mailbox for Raspberry Pi" instead of "Ticket Printer"

### Removed
- `app.py` - Full-stack Flask web application
- `backend/api.py` - Separated API-only Flask backend
- `backend/requirements.txt` - Separate backend dependencies
- `backend/ticket-printer.service` - Old systemd service file
- `frontend/` directory - Static HTML/JS/CSS frontend
- `templates/` directory - Flask Jinja2 templates
- `netlify/` directory - Serverless functions
- `config.py` - Old configuration file
- `netlify.toml` - Netlify deployment config
- `env.example` - Duplicate of `.env.example`
- Web-focused documentation:
  - RECAPTCHA_SETUP.md
  - CONVEX_SETUP.md
  - CONVEX_MANUAL_SETUP.md
  - CONVEX_STEP_BY_STEP.md
  - NETLIFY_DEPLOY_STEPS.md
  - README_NETLIFY.md
  - GITHUB_DEPLOYMENT.md
  - README_DEPLOYMENT.md
  - Old QUICK_START.md (replaced with Kid Fax version)

### Migration Guide

**If you were using the web interface:**

1. **Web code is preserved** in `archive/` directory
2. **Read `archive/README_ARCHIVE.md`** for restoration instructions
3. **Kid Fax SMS core** functionality is unchanged
4. **Consider forking** if you want both web and SMS features

**Updating from v1.x:**

```bash
# Backup your .env file
cp .env .env.backup

# Pull v2.0.0 changes
git pull origin main

# Update .env (remove web vars: HOST, PORT, DEBUG)
nano .env

# Reinstall dependencies (Flask removed)
pip install -r requirements.txt

# Switch to SMS poller instead of app.py
# Old: python app.py
# New: python -m kidfax.sms_poller
```

**What's Preserved:**
- `kidfax/` module (printer.py, sms_poller.py, send_sms.py)
- Printer abstraction (USB, Serial, Network, Bluetooth)
- Twilio SMS functionality
- E-ink display support
- Hardware setup guides

**What Changed:**
- No web interface (web code archived)
- Simplified dependencies
- Kid Fax-focused documentation

---

## [1.0.0] - Initial Release - 2024

### Added
- Core ticket printing functionality
- Web interface for ticket submission
- ESC/POS thermal printer support (USB, Serial, Network, Bluetooth)
- Kid Fax SMS mailbox feature (sms_poller.py, send_sms.py)
- Timestamp and date stamping
- Health check endpoint
- Error handling and logging
- Netlify deployment support
- reCAPTCHA spam protection
- Optional Convex database integration
- Systemd service configuration
- Comprehensive documentation

### Features
- **Printer Support**: USB, Serial/GPIO, Network, and Bluetooth connections
- **Multiple Deployment Options**:
  - Standalone Flask app on Raspberry Pi
  - Frontend on Netlify + Backend on Raspberry Pi
- **Kid Fax SMS**: Text-to-print mailbox with reply functionality
- **Database Integration**: Optional Convex database logging
- **Spam Protection**: Google reCAPTCHA integration
- **Auto-restart**: Systemd service with auto-restart on failure

### Documentation
- Main README with setup instructions
- Netlify deployment guide
- GitHub deployment guide
- Bluetooth printer setup guide
- Convex database setup guides
- Quick start guide
- Environment variable examples

---

## Release Philosophy

**v2.0.0**: Kid Fax is now focused exclusively on creating magical SMS mailbox experiences for kids and families. The web ticket printer was the original forked project, but it created a "two-headed" architecture. This release brings clarity and focus to the Kid Fax mission: **Text in, Paper out, Keyboard replies.**

**v1.0.0**: Dual-purpose application supporting both web-based ticket printing and Kid Fax SMS mailbox functionality.

---

**Note**: Archived web interface code is available in `archive/` directory with full restoration instructions.
