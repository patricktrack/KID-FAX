# Archive: Web Ticket Printer Interface

This directory contains the original web-based ticket printing functionality that was part of the KID-FAX project before v2.0.0.

## Why These Files Were Archived

As of v2.0.0, KID-FAX has been refocused exclusively on the "Kid Fax" SMS mailbox concept:
- **SMS → Print**: Family texts a Twilio number, messages print on thermal printer
- **Keyboard Replies**: Kids reply from Pi keyboard using CLI tool
- **No Web Interface**: Purely SMS-based, local-only operation

The web ticket printing system was the original forked project, but it created a "two-headed" architecture that diluted the Kid Fax vision. This archive preserves that work without cluttering the main project.

## What Was Archived

### Web Application Code (`web-app/`)
- **app.py** - Full-stack Flask application (web UI + API)
- **backend/** - Separated API-only Flask backend for Netlify deployment
- **frontend/** - Static HTML/JS/CSS frontend with reCAPTCHA integration
- **templates/** - Flask Jinja2 templates for server-side rendering
- **netlify/** - Netlify serverless functions for Convex database logging
- **config.py** - Early configuration file (superseded by environment variables)
- **netlify.toml** - Netlify deployment configuration

### Web Documentation (`web-docs/`)
- **RECAPTCHA_SETUP.md** - Google reCAPTCHA configuration for spam protection
- **CONVEX_SETUP.md** - Convex database integration for ticket logging
- **CONVEX_MANUAL_SETUP.md** - Alternative Convex setup instructions
- **CONVEX_STEP_BY_STEP.md** - Detailed Convex walkthrough
- **NETLIFY_DEPLOY_STEPS.md** - Netlify deployment guide
- **README_NETLIFY.md** - Comprehensive Netlify + Pi deployment
- **GITHUB_DEPLOYMENT.md** - GitHub repository + Netlify integration
- **README_DEPLOYMENT.md** - Various deployment options
- **QUICK_START.md** - Quick start for web deployment (replaced with Kid Fax version)
- **deploy.sh** - Deployment automation script
- **setup.sh** - Setup automation script

## Features of the Web System

The archived web system provided:
- **Web Form Submission** - Users submit tickets via browser
- **Multiple Deployment Modes** - Standalone on Pi or separated (Netlify + Pi)
- **reCAPTCHA Protection** - Spam prevention for public-facing forms
- **Database Logging** - Optional Convex integration for ticket history
- **CORS Support** - Cross-origin requests for separated deployment
- **Health Check Endpoints** - API monitoring and printer status

## Technical Architecture

The web system had two deployment patterns:

### Pattern 1: Full-Stack on Pi
```
User Browser → app.py (Flask) → kidfax.printer → Thermal Printer
```

### Pattern 2: Separated Deployment
```
User Browser → Netlify (frontend) → ngrok/tunnel → backend/api.py (Pi) → kidfax.printer → Thermal Printer
                     ↓
           Netlify Function → Convex Database
```

## How to Restore

If you need to restore the web functionality:

1. **Copy files back** to main project:
   ```bash
   cp -r archive/web-app/* /path/to/KID-FAX/
   cp -r archive/web-docs/*.md /path/to/KID-FAX/
   ```

2. **Restore dependencies** in `requirements.txt`:
   ```
   Flask==3.0.0
   Werkzeug==3.0.1
   flask-cors
   ```

3. **Add web configuration** to `.env`:
   ```
   HOST=0.0.0.0
   PORT=5000
   DEBUG=True
   RECAPTCHA_SITE_KEY=your_key
   CONVEX_DEPLOYMENT=your_deployment
   ```

4. **Run the web app**:
   ```bash
   python app.py
   # or
   python backend/api.py
   ```

## Fork for Web Version

If you want to maintain a web-enabled fork:

1. Restore these files to your fork
2. Keep Kid Fax SMS features alongside web interface
3. Update README to explain both modes
4. Consider creating separate branches for each use case

## Original Commit Reference

The web code was archived at commit: `a66dad5`

Before archiving commit: `2695dd8`

You can always checkout these commits to see the full web-enabled state:
```bash
git checkout 2695dd8
```

## Why Not Delete?

This code represents significant work and provides:
- **Reference Implementation** - Example of Flask + printer integration
- **Deployment Patterns** - Useful Netlify + Pi architecture
- **Learning Resource** - How to build distributed printing systems
- **Future Options** - Maybe you'll want a web UI someday!

## Contact

If you have questions about the archived web system or want to contribute a web interface as a separate project, please open an issue in the main repository.

---

**Archived**: December 2025
**Reason**: Kid Fax v2.0.0 focus on SMS mailbox functionality
**Status**: Preserved but not maintained
