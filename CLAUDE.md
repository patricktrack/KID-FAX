# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Kid Fax codebase.

## Project Overview

Kid Fax is a Raspberry Pi SMS mailbox that prints incoming text messages on thermal printers. Family members text a Twilio number, the Pi polls for messages, prints them, and kids can reply from the keyboard.

**Core Philosophy**: Pure SMS → Print → Reply. No web interfaces, no databases, no complex deployments. Just text in, paper out, keyboard replies.

## Essential Commands

### Development
```bash
# Install dependencies
pip3 install -r requirements.txt

# Run SMS poller (main application)
python -m kidfax.sms_poller

# Send reply from keyboard
python -m kidfax.send_sms grandma "Hi!"
python -m kidfax.send_sms +15551234567 "Direct number"

# Test printer without hardware
export ALLOW_DUMMY_PRINTER=true
python -m kidfax.sms_poller
```

### Testing
```bash
# Test printer connection
python3 << EOF
from kidfax.printer import get_printer
p = get_printer(allow_dummy=True)
p.text("Test print\n")
p.cut()
EOF

# Find USB printer IDs
lsusb

# Test Twilio credentials
python -m kidfax.send_sms +15551234567 "Test"
```

### System Service
```bash
# View logs
sudo journalctl -u kidfax -f

# Service control
sudo systemctl status kidfax
sudo systemctl restart kidfax
sudo systemctl enable kidfax
```

## Architecture

### Module Structure
```
kidfax/
├── __init__.py       # Package marker
├── printer.py        # Printer abstraction layer (154 lines)
├── sms_poller.py     # Main polling service (320 lines)
└── send_sms.py       # Outbound SMS CLI (65 lines)
```

### Design Principles

1. **Hardware Abstraction** (`printer.py`)
   - Single `get_printer()` function returns appropriate driver
   - Supports USB, Serial, Network, Bluetooth, Dummy
   - Environment-driven configuration
   - DummyPrinter for testing without hardware

2. **Stateful SMS Processing** (`sms_poller.py`)
   - Prevents duplicate prints via JSON state file
   - Tracks processed Twilio SIDs
   - Bounded growth (KIDFAX_STATE_LIMIT)
   - Crash-resistant (saves state frequently)

3. **Contact Mapping**
   - `CONTACTS=grandma:+15551112222,uncle:+15553334444`
   - Send via name: `send_sms grandma "Hi"`
   - Prints show contact labels

4. **Security by Allowlist**
   - `ALLOWLIST=+15551112222,+15553334444`
   - Only approved numbers can print
   - Kid safety: prevents spam/unwanted messages

## Key Files

### kidfax/printer.py:154
**Purpose**: Unified printer interface for multiple hardware types

**Key Functions**:
- `get_printer(allow_dummy=False)` - Returns configured printer or None
- `print_ticket(printer, from_name, question)` - Prints formatted message
- `DummyPrinter` class - Mock for testing

**Configuration**:
```python
PRINTER_TYPE = os.getenv("PRINTER_TYPE", "usb")
# Values: usb, serial, bluetooth, network, dummy
```

**Adding New Printer Types**:
1. Add condition in `get_printer()`
2. Import appropriate escpos driver
3. Add env vars to `.env.example`
4. Document in README

### kidfax/sms_poller.py:320
**Purpose**: Main SMS polling loop

**Architecture**:
- Infinite `while True` loop (systemd-friendly)
- Polls Twilio every `POLL_SECONDS`
- State tracking in `~/.kidfax_state.json`
- Graceful KeyboardInterrupt handling
- Printer re-initialization on errors

**Message Flow**:
```
Twilio API → Fetch → Filter allowlist → Check state → Print → Save state → Update e-ink
```

**State Management**:
```python
{
  "seen_sids": ["SM123abc...", "SM456def..."]  # Last N Twilio message SIDs
}
```

**Error Handling**:
- Printer failures → set `printer = None` → retry next loop
- Twilio errors → log warning → continue polling
- State file errors → start fresh (never crash)

### kidfax/send_sms.py:65
**Purpose**: CLI for sending SMS replies

**Usage**:
```bash
# Via contact name
python -m kidfax.send_sms grandma "Message"

# Via phone number
python -m kidfax.send_sms +15551234567 "Message"
```

**Returns**: Twilio SID of sent message

## Configuration via Environment

All settings via environment variables (see `.env.example`):

**Required**:
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_NUMBER`
- `ALLOWLIST` (recommended for kid safety)
- `CONTACTS` (optional but convenient)

**Printer** (choose one type):
- USB: `PRINTER_TYPE=usb`, `USB_VENDOR=0x0416`, `USB_PRODUCT=0x5011`
- Serial: `PRINTER_TYPE=serial`, `SERIAL_PORT=/dev/serial0`, `SERIAL_BAUD=19200`
- Network: `PRINTER_TYPE=network`, `NETWORK_HOST=192.168.1.100`
- Bluetooth: `PRINTER_TYPE=bluetooth`, `BLUETOOTH_SERIAL_PORT=/dev/rfcomm0`

**Optional**:
- `POLL_SECONDS=15` - How often to check Twilio
- `PRINTER_LINE_WIDTH=32` - Character wrapping
- `PRINTER_ENCODING=cp437` - For special characters
- `EINK_STATUS_ENABLED=true` - Enable e-ink display

## Important Patterns

### Text Sanitization
```python
# Sanitize for printer encoding
def _sanitize(text: str) -> str:
    return text.encode(ENCODING, "ignore").decode(ENCODING)
```

### Text Wrapping
```python
import textwrap
wrapped = textwrap.wrap(text, width=LINE_WIDTH)
for line in wrapped:
    printer.text(line + "\n")
```

### Contact Resolution
```python
CONTACTS = {"grandma": "+15551112222", "uncle": "+15553334444"}
recipient = CONTACTS.get(name_or_number, name_or_number)
```

### State Management
```python
# Load state (list preserves order, set for fast lookup)
order, seen = _load_state()  # Returns (List[str], Set[str])

# Add new message
seen.add(message.sid)
order.append(message.sid)

# Enforce limit
if len(order) > MAX_STATE:
    oldest = order.pop(0)
    seen.discard(oldest)

# Save atomically
_save_state(order)
```

## Hardware Integration

### USB Printer
1. Connect via USB
2. Find IDs: `lsusb` → `ID 0416:5011`
3. Set env: `USB_VENDOR=0x0416`, `USB_PRODUCT=0x5011`
4. Permissions: `sudo usermod -a -G lp,dialout pi`

### Serial Printer (Adafruit Mini TTL)
1. Connect TX→RX, RX→TX, GND→GND
2. Separate 5-9V power supply
3. Enable: `sudo raspi-config` → Serial
4. Set env: `SERIAL_PORT=/dev/serial0`, `SERIAL_BAUD=19200`

### E-ink Display (Waveshare 2.9")
1. Connect HAT to Pi GPIO
2. Enable SPI: `sudo raspi-config`
3. Install Waveshare drivers
4. Set env: `EINK_STATUS_ENABLED=true`

## Systemd Service Pattern

Create `/etc/systemd/system/kidfax.service`:
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
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Security Considerations

- **Never commit `.env`** - Contains Twilio credentials
- **Use ALLOWLIST** - Prevents spam/unwanted messages
- **SMS not encrypted** - Avoid sensitive information
- **State file permissions** - Should be user-readable only
- **Rate limiting** - Twilio bills per message

## Common Tasks

### Adding a Contact
```bash
# Edit .env
CONTACTS=grandma:+15551112222,uncle:+15553334444,mom:+15555555555

# Restart service
sudo systemctl restart kidfax
```

### Changing Polling Interval
```bash
# Edit .env
POLL_SECONDS=30

# Restart service
sudo systemctl restart kidfax
```

### Switching Printer Types
```bash
# Edit .env
PRINTER_TYPE=network
NETWORK_HOST=192.168.1.100

# Restart service
sudo systemctl restart kidfax
```

## Troubleshooting

### No Messages Printing
1. Check Twilio credentials: `python -m kidfax.send_sms +1... "test"`
2. Check allowlist: Ensure sender in `ALLOWLIST`
3. Check state file: May have already processed message
4. Check printer: `python -c "from kidfax.printer import get_printer; print(get_printer())"`

### Printer Not Found
1. USB: Check `lsusb` output
2. Permissions: `sudo usermod -a -G lp,dialout pi` + logout
3. Try dummy: `ALLOW_DUMMY_PRINTER=true`
4. Check logs: `sudo journalctl -u kidfax -n 50`

### Duplicate Prints
- Should not happen (state tracking prevents)
- If it does: Check state file permissions
- Clear state: `rm ~/.kidfax_state.json` (will re-print recent messages)

## Dependencies

- **python-escpos 3.0a8** - ESC/POS printer protocol
- **twilio 9.0.1** - SMS API client
- **pyusb 1.2.1** - USB printer communication
- **Pillow 10.3.0** - E-ink display rendering
