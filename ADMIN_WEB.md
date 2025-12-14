# Kid Fax Admin Web Interface

**Manage contacts and security settings through a simple web browser interface.**

## Quick Start

### 1. Configure Admin Password

Edit your `.env` file and set a secure password:

```bash
cd ~/KID-FAX
nano .env
```

Add or update:
```bash
ADMIN_PASSWORD=your_secure_password_here
```

**Security tip**: Use a strong password (at least 12 characters, mix of letters/numbers/symbols).

### 2. Start Admin Web Server

```bash
cd ~/KID-FAX
python -m kidfax.admin_web
```

You should see:
```
============================================================
Kid Fax Admin Web Interface
============================================================
Running on: http://127.0.0.1:5000/admin
Access from this machine only (localhost)

Press Ctrl+C to stop
============================================================
```

### 3. Open in Browser

**On the Raspberry Pi**:
- Open browser (Chromium, Firefox, etc.)
- Go to: `http://localhost:5000/admin`

**From another device on same network** (optional):
- First, update `.env`: `ADMIN_HOST=0.0.0.0`
- Restart admin web server
- From laptop/phone browser: `http://raspberrypi.local:5000/admin`

### 4. Login

When prompted, enter:
- **Username**: (leave blank or type anything)
- **Password**: Your `ADMIN_PASSWORD` from `.env`

You should now see the Kid Fax Admin Panel!

---

## Features

### Managing Contacts

**Add a New Contact**:
1. Click "+ Add Contact"
2. Enter contact name (e.g., "grandma")
3. Enter phone number in E.164 format (e.g., "+15551234567")
4. Click "Add Contact"

**Edit Contact**:
1. Find the contact in the table
2. Click "Edit"
3. Modify name and/or phone number
4. Click "Save Changes"

**Delete Contact**:
1. Find the contact in the table
2. Click "Delete"
3. Confirm deletion

**F-Key Mapping**:
- Contacts are automatically assigned to F1-F12 in alphabetical order
- F1 = first contact alphabetically
- F2 = second contact alphabetically
- Maximum 12 contacts (keyboard mode limitation)

### Managing Allowlist

The allowlist controls which phone numbers can send messages to Kid Fax.

**Add Number to Allowlist**:
1. Click "+ Add Number" under Allowlist section
2. Enter phone number in E.164 format
3. Click "Add Number"

**Remove Number from Allowlist**:
1. Find the number in the list
2. Click "Remove"
3. Confirm removal

**Security Note**:
- If allowlist is empty, ALL numbers can send messages (not recommended for kids!)
- Keep allowlist limited to trusted family members only

### Saving Changes

- All changes are immediately saved to the `.env` file
- A backup is created at `.env.backup`
- Changes take effect on next service restart

### Restarting Kid Fax Service

After making changes, restart the service to apply them:

1. Click "🔄 Restart Kid Fax Service"
2. Wait for confirmation message

**Note**: This requires sudo permissions. See [Setup Sudo Permissions](#setup-sudo-permissions) below.

---

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# ================================
# Admin Web Interface
# ================================

# Required: Password for admin access
ADMIN_PASSWORD=your_secure_password_here

# Optional: Network binding (default: 127.0.0.1 = localhost only)
# ADMIN_HOST=127.0.0.1  # Localhost only (most secure)
# ADMIN_HOST=0.0.0.0    # Allow access from local network

# Optional: Port (default: 5000)
# ADMIN_PORT=5000
```

### Network Access Options

**Option 1: Localhost Only (Default, Most Secure)**
```bash
ADMIN_HOST=127.0.0.1
```
- Only accessible from the Pi itself
- Must connect monitor/keyboard to Pi
- Highest security (no network exposure)

**Option 2: Local Network Access**
```bash
ADMIN_HOST=0.0.0.0
```
- Accessible from any device on same WiFi
- Parent can edit from laptop/phone
- Still password-protected
- Not exposed to internet (unless you forward ports - don't!)

### Setup Sudo Permissions

To enable the "Restart Service" button, allow the `pi` user to restart the kidfax service without a password:

```bash
sudo visudo -f /etc/sudoers.d/kidfax
```

Add this line:
```
pi ALL=(ALL) NOPASSWD: /bin/systemctl restart kidfax
```

Save and exit (Ctrl+X, Y, Enter).

Test it:
```bash
sudo systemctl restart kidfax
# Should work without asking for password
```

---

## Phone Number Format

All phone numbers must be in **E.164 format**:

✅ **Correct**:
- `+15551234567` (US)
- `+442071234567` (UK)
- `+33123456789` (France)

❌ **Incorrect**:
- `555-123-4567` (has dashes)
- `(555) 123-4567` (has parentheses)
- `15551234567` (missing +)
- `001-555-123-4567` (wrong prefix)

**Format**: `+` + country code + number (no spaces, dashes, or parentheses)

---

## Troubleshooting

### Can't Access Admin UI

**Problem**: Browser shows "Connection refused" or "Cannot connect"

**Solutions**:

1. **Check admin web server is running**:
   ```bash
   # Should see "Running on: http://..." message
   python -m kidfax.admin_web
   ```

2. **Verify correct URL**:
   - Localhost: `http://localhost:5000/admin`
   - From network: `http://raspberrypi.local:5000/admin`
   - Check port matches `ADMIN_PORT` in .env

3. **Check firewall** (if accessing from network):
   ```bash
   sudo ufw status
   # Should show port 5000 allowed (if using ADMIN_HOST=0.0.0.0)
   ```

### Login Fails / Wrong Password

**Problem**: "Login Required" keeps appearing

**Solutions**:

1. **Check ADMIN_PASSWORD in .env**:
   ```bash
   grep ADMIN_PASSWORD .env
   # Should show: ADMIN_PASSWORD=your_password
   ```

2. **Verify no typos**:
   - Password is case-sensitive
   - No extra spaces before/after password
   - Check for hidden characters

3. **Check browser credentials**:
   - Browser may have cached old password
   - Clear browser cache or use incognito/private mode

4. **Restart admin web server** after changing password:
   ```bash
   # Stop with Ctrl+C, then restart
   python -m kidfax.admin_web
   ```

### .env File Not Found

**Problem**: "Error: .env file not found"

**Solutions**:

1. **Create .env file**:
   ```bash
   cd ~/KID-FAX
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

2. **Check working directory**:
   ```bash
   # Admin web looks for .env in current directory
   cd ~/KID-FAX
   python -m kidfax.admin_web
   ```

3. **Specify custom path** (advanced):
   ```bash
   ENV_FILE_PATH=/path/to/.env python -m kidfax.admin_web
   ```

### Phone Number Validation Errors

**Problem**: "Invalid phone format" error

**Solutions**:

- Start with `+` (plus sign)
- Include country code (e.g., `+1` for US)
- No spaces, dashes, or parentheses
- Example US: `+15551234567`

### Service Restart Button Doesn't Work

**Problem**: "Service restart not available" or permission error

**Solutions**:

1. **Setup sudo permissions** (see [Setup Sudo Permissions](#setup-sudo-permissions))

2. **Verify systemd service exists**:
   ```bash
   sudo systemctl status kidfax
   # Should show service status
   ```

3. **Test manual restart**:
   ```bash
   sudo systemctl restart kidfax
   # Should work without password prompt
   ```

### Changes Not Appearing

**Problem**: Made changes in admin UI but contacts/allowlist unchanged

**Solutions**:

1. **Restart Kid Fax service**:
   ```bash
   sudo systemctl restart kidfax
   ```

2. **Check .env file was updated**:
   ```bash
   cat .env | grep CONTACTS
   cat .env | grep ALLOWLIST
   ```

3. **Check for .env.backup**:
   ```bash
   ls -la .env*
   # Should see .env.backup (backup before save)
   ```

4. **Check permissions**:
   ```bash
   ls -l .env
   # Should be writable by current user
   ```

---

## Security Best Practices

### 1. Use Strong Password

```bash
# Bad
ADMIN_PASSWORD=admin

# Good
ADMIN_PASSWORD=K1dF@x$ecur3P@ssw0rd!2024
```

### 2. Limit Network Access

```bash
# Most secure (default)
ADMIN_HOST=127.0.0.1  # Localhost only

# Less secure (use only if needed)
ADMIN_HOST=0.0.0.0    # Local network access
```

### 3. Don't Expose to Internet

- ❌ Never forward port 5000 to the internet
- ❌ Never run on public WiFi
- ✅ Only use on home network
- ✅ Stop admin server when not in use

### 4. Protect .env File

```bash
# Secure file permissions
chmod 600 .env

# Never commit to git
echo ".env" >> .gitignore
```

### 5. Regular Backups

```bash
# Backup .env file
cp .env .env.backup.$(date +%Y%m%d)
```

### 6. Audit Logs

Check admin access logs:
```bash
# View recent admin logins
tail -f /path/to/kidfax/logs
# Look for "Admin login from..." entries
```

---

## Advanced Usage

### Running as Systemd Service (Auto-Start)

Create `/etc/systemd/system/kidfax-admin.service`:

```ini
[Unit]
Description=Kid Fax Admin Web Interface
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/KID-FAX
EnvironmentFile=/home/pi/KID-FAX/.env
ExecStart=/usr/bin/python3 -m kidfax.admin_web
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable kidfax-admin
sudo systemctl start kidfax-admin
```

**Note**: Admin UI will run 24/7. Only recommended if you need frequent access.

### Custom Port

Use a different port (e.g., 8080):

```bash
# In .env
ADMIN_PORT=8080
```

Access at: `http://localhost:8080/admin`

### HTTPS (Future Enhancement)

Currently HTTP only. For HTTPS (SSL/TLS):
- Generate self-signed certificate
- Configure Flask with SSL context
- See Flask documentation: https://flask.palletsprojects.com/en/latest/deploying/

---

## Frequently Asked Questions

**Q: Can I access admin UI from my phone?**

A: Yes, if you set `ADMIN_HOST=0.0.0.0` and your phone is on the same WiFi. Access via `http://raspberrypi.local:5000/admin`.

**Q: Do I need to restart the service after every change?**

A: Yes, Kid Fax services read `.env` only at startup. Restart to apply changes.

**Q: Can I have more than 12 contacts?**

A: The `.env` file can store unlimited contacts, but keyboard mode (F1-F12) supports only 12. Extra contacts will be stored but not mapped to function keys.

**Q: What happens if I forget the admin password?**

A: Edit the `.env` file directly to set a new `ADMIN_PASSWORD`, then restart the admin web server.

**Q: Is the admin UI safe to use?**

A: Yes, on a trusted local network. Use a strong password and don't expose port 5000 to the internet.

**Q: Can multiple people use the admin UI at once?**

A: Technically yes, but changes from one person may overwrite another's. Best to coordinate edits.

**Q: Does the admin UI log my changes?**

A: Yes, changes are logged to console output. For persistent logs, redirect output to a file or configure Python logging.

---

## Keyboard Shortcuts

When using the admin UI in a browser:

- **F5 / Ctrl+R**: Reload page (refresh after service restart)
- **Escape**: Close modal dialogs
- **Tab**: Navigate between form fields

---

## Next Steps

- **Setup auto-start**: Configure systemd service for admin UI
- **Create backups**: Regular .env file backups
- **Monitor logs**: Track who's accessing admin UI
- **Test changes**: Verify contacts work in keyboard mode

For more information:
- [README.md](README.md) - Main Kid Fax documentation
- [KEYBOARD_MODE.md](KEYBOARD_MODE.md) - Interactive keyboard mode guide
- [TWILIO_SETUP.md](TWILIO_SETUP.md) - Twilio configuration

---

**Made with ❤️ for families**
