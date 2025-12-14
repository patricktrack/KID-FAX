# Kid Fax - SMS Mailbox for Raspberry Pi

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-Compatible-C51A4A.svg)](https://www.raspberrypi.org/)

A delightful SMS-to-printer mailbox for kids. Family members text a Twilio number, and messages magically print on a thermal receipt printer connected to a Raspberry Pi. Kids can reply using the keyboard!

## What is Kid Fax?

Kid Fax turns a Raspberry Pi into a physical mailbox for text messages:

📱 **Family texts** → 🖨️ **Instant print** → 📧 **Physical message**

- ⌨️ Kids reply from the keyboard
- 🛡️ Safe: Only approved phone numbers can send messages
- 🎨 Optional: E-ink display shows unread message count
- 🏠 No screens, no web interface - just simple, magical communication

Perfect for:
- Kids too young for smartphones
- Grandparents who love sending messages
- Teaching communication without screens
- Physical keepsakes of family messages

## Hardware Requirements

### Required

**Raspberry Pi** (any model with GPIO, tested on Pi 400)
- Buy: [Raspberry Pi Kit](https://amzn.to/3XoAZli)

**Thermal Printer** (58mm ESC/POS compatible)
- Buy: [Netum 58mm Printer](https://amzn.to/43Vx9DT)
- Alternative: Adafruit Mini Thermal Receipt Printer

**Printer Paper**
- Buy: [58mm Receipt Paper](https://amzn.to/4ag6q8Y)

**Twilio Account** (for SMS)
- Sign up at [twilio.com](https://www.twilio.com)
- SMS messaging service with pay-as-you-go pricing

### Optional

**E-ink Display** (2.9" Waveshare HAT for message counter)
- Shows "You have 3 new messages!" badge

**Keyboard & Monitor** for replies
- Buy: [Bluetooth Keyboard/Mouse](https://amzn.to/4akjutW)
- Buy: [HDMI Monitor](https://amzn.to/4rsK620)

## Quick Start

### 1. Hardware Assembly (5 minutes)

**USB Printer:**
1. Connect thermal printer to Raspberry Pi via USB
2. Power on the printer

**Serial Printer (Adafruit Mini TTL):**
1. Connect TX→RX, RX→TX, GND→GND
2. Connect separate 5-9V power supply to printer
3. Enable serial: `sudo raspi-config` → Interface Options → Serial Port → Enable

**Optional E-ink Display:**
1. Attach Waveshare 2.9" HAT to GPIO pins
2. Enable SPI: `sudo raspi-config` → Interface Options → SPI → Enable

### 2. Twilio Account Setup (3 minutes)

1. Create account at [twilio.com](https://www.twilio.com)
2. Purchase a phone number (SMS-enabled)
3. Note your Account SID and Auth Token
4. See [TWILIO_SETUP.md](TWILIO_SETUP.md) for detailed instructions

### 3. Software Installation (5 minutes)

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-dev libusb-1.0-0-dev

# Clone the repository
git clone https://github.com/yourusername/KID-FAX.git
cd KID-FAX

# Install Python dependencies
pip3 install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with your Twilio credentials and settings
```

### 4. Test Message (2 minutes)

```bash
# Start the SMS poller
python -m kidfax.sms_poller

# From another device, text your Twilio number
# Watch it print!
```

## How It Works

**Receiving Messages:**
```
📱 Family Member's Phone
    ↓
    Text to Twilio Number
    ↓
☁️  Twilio Cloud API
    ↓
🔄 Kid Fax SMS Poller (checks every 15 seconds)
    ↓
🛡️  Allowlist Check (kid safety)
    ↓
🖨️  Thermal Printer
    ↓
📄 Physical Receipt

🎨 Optional: E-ink badge updates
```

**Sending Replies:**
```
⌨️  Option 1: CLI
    python -m kidfax.send_sms grandma "Hi!"

🎹 Option 2: Interactive Keyboard Mode
    Press F1 (Grandma) → Type message → Press Enter → Send!
    📺 E-ink display shows recipient and message in real-time
```

## Configuration

Copy `.env.example` to `.env` and configure:

### Required Settings

```bash
# Twilio credentials
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_NUMBER=+15551234567

# Security: Only these numbers can send messages (kid safety!)
ALLOWLIST=+15551112222,+15553334444

# Friendly names for contacts
CONTACTS=grandma:+15551112222,uncle:+15553334444

# Printer type: usb, serial, network, bluetooth
PRINTER_TYPE=usb
```

### USB Printer Configuration

```bash
# Find your printer's vendor and product IDs
lsusb  # Look for your printer (e.g., ID 0416:5011)

# In .env:
USB_VENDOR=0x0416
USB_PRODUCT=0x5011
```

### Serial Printer Configuration

```bash
# In .env:
PRINTER_TYPE=serial
SERIAL_PORT=/dev/serial0
SERIAL_BAUD=19200
```

See `.env.example` for all configuration options.

## Usage

### Receiving Messages (Auto-Start)

Set up Kid Fax to run automatically on boot:

```bash
# Create systemd service
sudo nano /etc/systemd/system/kidfax.service
```

See [SYSTEMD_SETUP.md](SYSTEMD_SETUP.md) for complete service configuration.

**Start the service:**
```bash
sudo systemctl enable kidfax
sudo systemctl start kidfax
```

**View logs:**
```bash
sudo journalctl -u kidfax -f
```

### Sending Replies

**Option 1: Command Line** (quick replies)

```bash
# Reply by contact name
python -m kidfax.send_sms grandma "Thanks for the message!"

# Reply by phone number
python -m kidfax.send_sms +15551112222 "Hi Grandma!"
```

**Option 2: Interactive Keyboard Mode** (kid-friendly!)

Press function keys to select recipients - perfect for kids on Raspberry Pi 400!

```bash
# Start interactive keyboard mode
python -m kidfax.interactive_keyboard
```

**How it works:**
1. Press **F1-F12** to select a recipient (each key = family member)
2. **Type your message** and watch it appear on e-ink display
3. Press **Enter** to send
4. ✓ Message sent! (optional receipt prints)

**Physical Setup:**
- Add stickers above F1-F12 keys with contact names
- Perfect for Raspberry Pi 400 Computer Kit (built-in keyboard)
- E-ink display shows recipient and message in real-time

See [KEYBOARD_MODE.md](KEYBOARD_MODE.md) for complete interactive mode guide including:
- Physical sticker templates
- F-key contact mapping
- E-ink display layouts
- Troubleshooting keyboard shortcuts

## Safety & Privacy

### Kid Safety Features

- **Allowlist**: Only approved phone numbers can send messages
- **No web exposure**: Everything runs locally on your Pi
- **No screen time**: Physical receipts instead of screens
- **Supervised**: Parents control who can communicate

### Privacy Considerations

- **SMS not encrypted**: Avoid sharing sensitive information
- **Twilio security**: Industry-standard SMS gateway
- **Local storage**: Message state stored on Pi only
- **No cloud logging**: Messages aren't stored in databases

### Configuration for Safety

```bash
# Strict allowlist (recommended)
ALLOWLIST=+15551112222,+15553334444

# Empty allowlist accepts all (NOT recommended for kids)
# ALLOWLIST=
```

## Troubleshooting

### Printer Not Found

**USB Printer:**
```bash
# Check if printer is detected
lsusb

# Check permissions
sudo usermod -a -G lp,dialout pi
# Log out and log back in

# Try different USB ports
```

**Serial Printer:**
```bash
# Check serial port exists
ls /dev/serial*

# Enable serial interface
sudo raspi-config
```

### No Messages Printing

1. **Check Twilio credentials**: Test with `python -m kidfax.send_sms +1... "test"`
2. **Check allowlist**: Ensure sender is in `ALLOWLIST`
3. **Check state file**: May have already processed message - delete `~/.kidfax_state.json` to reset
4. **Check printer**: `python -c "from kidfax.printer import get_printer; print(get_printer())"`

### Test Without Printer

```bash
# Use dummy printer mode for testing
export ALLOW_DUMMY_PRINTER=true
python -m kidfax.sms_poller
```

See full troubleshooting guide in [DEPLOYMENT.md](DEPLOYMENT.md)

## Project Structure

```
KID-FAX/
├── kidfax/                 # Core Kid Fax module
│   ├── printer.py          # Printer abstraction (USB/Serial/Network/Bluetooth)
│   ├── sms_poller.py       # Twilio SMS polling service
│   ├── send_sms.py         # CLI tool for sending replies
│   ├── interactive_keyboard.py  # Interactive keyboard messaging mode
│   ├── keyboard_input.py   # Keyboard event handling and F-key mapping
│   └── eink_display.py     # E-ink display utilities
├── .env.example            # Configuration template
├── requirements.txt        # Python dependencies
├── QUICK_START.md          # 15-minute setup guide
├── KEYBOARD_MODE.md        # Interactive keyboard mode guide
├── TWILIO_SETUP.md         # Twilio configuration
├── SYSTEMD_SETUP.md        # Auto-start service setup
├── DEPLOYMENT.md           # Complete deployment guide
├── SETUP_BLUETOOTH.md      # Bluetooth printer setup
└── CONFIGURE_BLUETOOTH_PRINTER.md
```

## Advanced Topics

### Bluetooth Printer Setup
See [SETUP_BLUETOOTH.md](SETUP_BLUETOOTH.md) and [CONFIGURE_BLUETOOTH_PRINTER.md](CONFIGURE_BLUETOOTH_PRINTER.md)

### E-ink Display Setup
Configure optional status display:
```bash
EINK_STATUS_ENABLED=true
EINK_DRIVER_PACKAGE=e-Paper.RaspberryPi_JetsonNano.python.lib.waveshare_epd
EINK_DRIVER_MODULE=epd2in9d
```

Requires Waveshare e-Paper library installed.

### Multiple Printer Types
Kid Fax supports:
- **USB** - Plug and play (most common)
- **Serial/TTL** - GPIO pins (Adafruit Mini)
- **Network** - WiFi/Ethernet printers
- **Bluetooth** - Wireless printers
- **Dummy** - Testing without hardware

See [DEPLOYMENT.md](DEPLOYMENT.md) for configuration details.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas for contribution:**
- Testing with different printer models
- E-ink display improvements
- MMS support (print images)
- Group messaging features
- Message scheduling
- Additional hardware integrations

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and migration guides.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built on [python-escpos](https://github.com/python-escpos/python-escpos) for printer support
- SMS powered by [Twilio](https://www.twilio.com)
- Inspired by the joy of receiving physical mail
- Created for kids who deserve magical communication experiences

## Support

- 📖 **Documentation**: Start with [QUICK_START.md](QUICK_START.md)
- 🐛 **Issues**: [GitHub Issues](https://github.com/yourusername/KID-FAX/issues)
- 💬 **Discussions**: [GitHub Discussions](https://github.com/yourusername/KID-FAX/discussions)

---

**Made with ❤️ for kids and families who love staying connected**

*Note: As of v2.0.0, Kid Fax is focused exclusively on SMS mailbox functionality. The previous web ticket printing interface has been archived in `archive/` directory.*
