# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KID-FAX is a Raspberry Pi-based ticket printing system with two main features:
1. Web-based ticket submission that prints on ESC/POS thermal printers
2. SMS mailbox ("Kid Fax") that receives texts via Twilio and prints them as physical receipts

The application supports flexible deployment: full-stack on Pi (app.py) or separated frontend/backend (frontend on Netlify + backend API on Pi).

## Essential Commands

### Development
```bash
# Install Python dependencies
pip3 install -r requirements.txt

# Run full-stack application (web UI + API + printer)
python3 app.py  # Runs on http://0.0.0.0:5000

# Run API-only backend (for separated deployment)
python3 backend/api.py  # Runs on http://0.0.0.0:5000

# Run SMS poller (Kid Fax mailbox)
python -m kidfax.sms_poller

# Send SMS reply from Pi
python -m kidfax.send_sms grandma "Hello!"
python -m kidfax.send_sms +15551234567 "Direct number example"
```

### Testing Printer Connection
```bash
# Find USB printer IDs
lsusb  # Look for vendor:product IDs (e.g., 0416:5011)

# Test printer directly
python3 << EOF
from escpos.printer import Usb
p = Usb(0x0416, 0x5011)
p.text("Test print\n")
p.cut()
EOF

# Test with dummy printer (no hardware)
export ALLOW_DUMMY_PRINTER=true
python3 app.py
```

### System Service Management
```bash
# View logs for systemd services
sudo journalctl -u ticket-printer -f
sudo journalctl -u kidfax -f

# Service control
sudo systemctl status ticket-printer
sudo systemctl restart ticket-printer
sudo systemctl enable ticket-printer  # Auto-start on boot
```

## Architecture & Code Structure

### Deployment Modes
The application has two deployment architectures:

1. **Full-stack on Pi** (`app.py`)
   - Flask serves both HTML templates and API endpoints
   - Everything runs on Raspberry Pi
   - Access via `http://[PI_IP]:5000`

2. **Separated deployment** (`backend/api.py` + `frontend/`)
   - Frontend: Static HTML/JS/CSS hosted on Netlify
   - Backend: Flask API on Pi exposed via ngrok/Cloudflare tunnel
   - CORS enabled for cross-origin requests

### Module Layout
- **`app.py`** - Full-stack Flask application (UI + API)
- **`backend/api.py`** - API-only Flask service (CORS enabled for Netlify frontend)
- **`kidfax/`** - Shared Python module containing:
  - `printer.py` - Printer abstraction layer (USB, Serial, Network, Bluetooth)
  - `sms_poller.py` - Twilio SMS polling service (infinite loop, systemd-ready)
  - `send_sms.py` - CLI tool for sending SMS replies
- **`frontend/`** - Static files (HTML, JS, CSS) for Netlify deployment
- **`templates/`** - Flask templates for full-stack mode

### Printer Abstraction
The `kidfax.printer` module provides a unified interface for multiple printer types:

**Printer Types:**
- `usb` - USB-connected printers (default, uses vendor/product IDs)
- `serial` - Serial/GPIO-connected printers (e.g., Adafruit Mini TTL)
- `network` - Network printers (IP address)
- `bluetooth` - Bluetooth printers (MAC address)
- `dummy` - Testing without hardware (set `ALLOW_DUMMY_PRINTER=true`)

**Key Functions:**
- `get_printer(allow_dummy=False)` - Returns printer instance or None
- `print_ticket(printer, from_name, message)` - Prints formatted ticket
- `DummyPrinter` class - Mock printer for testing

**Configuration Pattern:**
```python
from kidfax.printer import get_printer

# In development: allow_dummy=True for testing without hardware
printer = get_printer(allow_dummy=True)
if printer is None:
    logger.error("Printer not available")
    return
```

### SMS/Twilio Integration
The Kid Fax feature uses Twilio to receive and send SMS messages:

**Components:**
- `sms_poller.py` - Polls Twilio API every N seconds for new messages
- `send_sms.py` - CLI for sending replies from Pi keyboard
- State tracking in `~/.kidfax_state.json` to avoid duplicate prints
- Contact mapping via `CONTACTS` env var (e.g., `grandma:+15551112222`)
- Allowlist filtering via `ALLOWLIST` env var (kid safety)

**State Management:**
- Processed Twilio message SIDs stored in JSON file
- State limit prevents unbounded growth
- Re-initializes printer on errors (sets `printer = None`)
- Handles KeyboardInterrupt gracefully

### Configuration
All configuration via environment variables (see `.env.example`):

**Required for SMS:**
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_NUMBER`
- `ALLOWLIST` - Comma-separated phone numbers (e.g., `+15551112222,+15553334444`)
- `CONTACTS` - Name:number pairs (e.g., `grandma:+15551112222,uncle:+15553334444`)

**Printer Configuration:**
- `PRINTER_TYPE` - One of: usb, serial, network, bluetooth, dummy
- USB: `USB_VENDOR`, `USB_PRODUCT` (hex strings like `0x0416`)
- Serial: `SERIAL_PORT` (e.g., `/dev/serial0`), `SERIAL_BAUD` (default 19200)
- Network: `NETWORK_HOST` (IP address)
- `ALLOW_DUMMY_PRINTER` - Set to `true` for testing without hardware

**Optional:**
- `POLL_SECONDS` - SMS polling interval (default 15)
- `PRINTER_LINE_WIDTH` - Characters per line (default 32 for 58mm)
- `PRINTER_ENCODING` - Default `cp437` for ESC/POS printers
- `KIDFAX_STATE_FILE` - Path to state file (default `~/.kidfax_state.json`)
- `EINK_STATUS_ENABLED` - Enable e-ink display updates

## Important Patterns

### Error Handling
- Always wrap hardware operations in try/except
- Never let printer failures crash the application
- Log errors with appropriate levels (ERROR, WARNING, INFO)
- Return meaningful JSON error responses in API endpoints

### Logging
```python
import logging
LOG = logging.getLogger(__name__)

# Use descriptive log messages with context
LOG.info("Connecting to USB printer (vendor=%s, product=%s)", hex(vendor), hex(product))
LOG.error("Failed to print ticket: %s", exc)
```

### Environment Variables
```python
# With default
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "15"))

# Required value
def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value
```

### Text Processing for Printers
```python
import textwrap

# Sanitize for printer encoding
text = value.encode("cp437", "ignore").decode("cp437")

# Wrap to printer width
wrapped_lines = textwrap.wrap(text, width=32)
```

### API Response Pattern
```python
try:
    # operation
    return jsonify({'success': True, 'message': 'Success'})
except Exception as e:
    logger.error(f"Error: {e}")
    return jsonify({'success': False, 'error': str(e)}), 500
```

## Hardware Setup Notes

### USB Printer Setup
1. Connect printer via USB
2. Find vendor/product IDs: `lsusb`
3. Set permissions: `sudo usermod -a -G lp,dialout pi`
4. Configure environment: `USB_VENDOR=0x0416`, `USB_PRODUCT=0x5011`

### Serial Printer Setup (Adafruit Mini TTL)
1. Connect to Pi UART (TX↔RX, common ground)
2. Requires separate 5–9V ≥1.5A power supply
3. Enable serial: `sudo raspi-config` → Interface Options → Serial
4. Configure: `PRINTER_TYPE=serial`, `SERIAL_PORT=/dev/serial0`, `SERIAL_BAUD=19200`

### E-ink Display (Optional)
- Waveshare 2.9" HAT uses SPI interface
- Enable SPI: `sudo raspi-config` → Interface Options → SPI
- Requires Waveshare driver library
- Set `EINK_STATUS_ENABLED=true` to enable badge updates

## Systemd Service Pattern

For long-running processes (SMS poller, web app):

```ini
[Unit]
Description=Kid Fax SMS poller
After=network-online.target

[Service]
User=pi
EnvironmentFile=/home/pi/kidfax/.env
WorkingDirectory=/home/pi/kidfax
ExecStart=/home/pi/kidfax/bin/python -m kidfax.sms_poller
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Security Considerations

- Never commit `.env` files or credentials
- Use `ALLOWLIST` for SMS filtering (kid safety)
- Enable reCAPTCHA for web form submissions
- SMS is not end-to-end encrypted - avoid sensitive info
- Keep Twilio credentials in environment variables only

## Key Dependencies

- **Flask 3.0.0** - Web framework
- **python-escpos 3.0a8** - ESC/POS printer protocol
- **twilio 9.0.1** - SMS API client
- **pyusb 1.2.1** - USB printer communication
- **flask-cors** - CORS support for separated deployment
