# Contributing to Kid Fax

Thank you for your interest in contributing to Kid Fax! This document provides guidelines and instructions for contributing.

## How to Contribute

### Reporting Bugs

If you find a bug, please create an issue with:
- A clear, descriptive title
- Steps to reproduce the bug
- Expected behavior vs actual behavior
- Your environment details (OS, Python version, printer model, Pi model, etc.)
- Any error messages or logs
- Whether using USB, Serial, Network, or Bluetooth printer

### Suggesting Features

Feature suggestions are welcome! Please create an issue with:
- A clear description of the feature
- Use case and why it would be useful (especially for kid/family context)
- Possible implementation approach (if you have ideas)
- Whether it relates to SMS, printing, or hardware integration

### Pull Requests

1. **Fork the repository** and create a new branch from `main`
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style guidelines below

3. **Test your changes** thoroughly:
   - Test with dummy printer mode: `ALLOW_DUMMY_PRINTER=true`
   - Test with actual printer if possible
   - Test SMS sending/receiving with Twilio test credentials
   - Verify different printer types (USB, Serial, Network, Bluetooth)

4. **Update documentation** if needed:
   - Update README.md for user-facing changes
   - Add comments to complex code sections
   - Update CHANGELOG.md with your changes
   - Update .env.example if adding new configuration

5. **Commit your changes** with conventional commit messages
   ```bash
   git commit -m "feat: add MMS image printing support"
   git commit -m "fix: handle printer disconnection gracefully"
   git commit -m "docs: improve Twilio setup guide"
   ```

6. **Push to your fork** and create a Pull Request
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Submit the PR** with:
   - Clear description of changes
   - Reference to related issues (if any)
   - Screenshots or examples (if applicable)
   - Hardware tested on (printer model, Pi model)

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints for function parameters and return types
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Use 4 spaces for indentation
- Use `from __future__ import annotations` for forward references
- Prefer `Optional[Type]` over `Type | None` for Python 3.7-3.9 compatibility

Example:
```python
from typing import Optional

def send_message(recipient: str, message: str) -> Optional[str]:
    """
    Send SMS message via Twilio.

    Args:
        recipient: Phone number in E.164 format
        message: Message text to send

    Returns:
        Twilio message SID if successful, None otherwise
    """
    try:
        # Implementation
        return message_sid
    except Exception as exc:
        logger.error(f"Failed to send: {exc}")
        return None
```

### Import Organization

```python
# Standard library imports
import os
import logging
from typing import Optional, Dict, List

# Third-party imports
from twilio.rest import Client
from escpos.printer import Usb

# Local imports
from kidfax.printer import get_printer
```

### Error Handling

- Always wrap hardware operations in try/except blocks
- Log errors with appropriate levels (ERROR, WARNING, INFO)
- Return meaningful error messages
- Never let hardware failures crash the application

Example:
```python
try:
    printer = get_printer()
    printer.text("Hello\n")
except Exception as exc:
    logger.error(f"Print failed: {exc}")
    return {"success": False, "error": str(exc)}
```

### Logging

- Use module-level loggers: `LOG = logging.getLogger(__name__)`
- Configure with timestamps
- Use appropriate log levels:
  - DEBUG: Development details
  - INFO: Normal operations
  - WARNING: Recoverable issues
  - ERROR: Failures

Example:
```python
LOG.info("Connecting to USB printer (vendor=%s, product=%s)", hex(vendor), hex(product))
```

### Environment Variables

- All configuration via `os.getenv()`
- Provide sensible defaults
- Document all env vars in `.env.example`
- Never hardcode sensitive values

Example:
```python
POLL_SECONDS = int(os.getenv("POLL_SECONDS", "15"))
```

## Project Structure

```
KID-FAX/
├── kidfax/                 # Core Python module
│   ├── __init__.py         # Package marker
│   ├── printer.py          # Printer abstraction layer
│   ├── sms_poller.py       # Twilio SMS polling service
│   └── send_sms.py         # CLI for sending replies
├── .env.example            # Configuration template
├── requirements.txt        # Python dependencies
├── README.md               # Main documentation
├── QUICK_START.md          # Quick setup guide
├── TWILIO_SETUP.md         # Twilio configuration guide
├── SYSTEMD_SETUP.md        # Service setup guide
├── DEPLOYMENT.md           # Deployment documentation
└── archive/                # Archived web interface code
```

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/KID-FAX.git
   cd KID-FAX
   ```

2. **Set up Python environment** (optional but recommended)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Add your Twilio credentials
   ```

5. **Test without hardware**
   ```bash
   export ALLOW_DUMMY_PRINTER=true
   python -m kidfax.sms_poller
   ```

## Testing

### Manual Testing

**SMS Poller:**
```bash
# With dummy printer
ALLOW_DUMMY_PRINTER=true python -m kidfax.sms_poller

# With real printer
python -m kidfax.sms_poller
```

**SMS Sending:**
```bash
python -m kidfax.send_sms +15551234567 "Test message"
```

**Printer Direct Test:**
```python
from kidfax.printer import get_printer

printer = get_printer(allow_dummy=True)
printer.text("Test\n")
printer.cut()
```

### Hardware Testing

If you have hardware access:
- Test USB printer connection
- Test serial printer (Adafruit Mini TTL)
- Test network printer
- Test Bluetooth printer
- Test e-ink display updates

## Areas for Contribution

We're particularly interested in contributions for:

### Kid Fax SMS Features
- **MMS support**: Print images from text messages
- **Group messaging**: Send to multiple recipients
- **Message scheduling**: Delayed sends
- **Print history**: View past messages
- **Status notifications**: Alert when printer is out of paper

### Printer Support
- **New printer models**: Test and document compatibility
- **Connection types**: Improve Bluetooth, Network support
- **Print formatting**: Better text wrapping, fonts
- **Graphics**: Print emojis, logos, decorations

### Hardware Integration
- **E-ink improvements**: Better badge rendering
- **Button support**: Physical buttons to trigger actions
- **LED indicators**: Status lights
- **Buzzer**: Audio alerts for new messages

### Documentation
- **Setup guides**: Improve installation instructions
- **Troubleshooting**: Common issues and solutions
- **Hardware guides**: Specific printer models
- **Video tutorials**: Screen recordings of setup

### Testing
- **Unit tests**: Test individual functions
- **Integration tests**: Test SMS → Print flow
- **Hardware mocks**: Better dummy implementations
- **CI/CD**: Automated testing

### Security & Safety
- **Allowlist improvements**: Better phone number validation
- **Content filtering**: Inappropriate message detection
- **Rate limiting**: Prevent spam
- **Encryption**: Secure credential storage

## Printer Compatibility Testing

If testing a new printer model, please document:

**Printer Info:**
- Brand and model
- Connection type (USB, Serial, Network, Bluetooth)
- Vendor/Product IDs (for USB): `lsusb` output
- ESC/POS command set version

**Test Results:**
- Does it print? (Yes/No)
- Text formatting quality
- Cut command works?
- Image printing works?
- Special characters (emojis, international)?

**Configuration:**
```bash
PRINTER_TYPE=usb
USB_VENDOR=0x0416
USB_PRODUCT=0x5011
PRINTER_LINE_WIDTH=32
PRINTER_ENCODING=cp437
```

Add to README.md in a "Tested Printers" section!

## Kid Safety Considerations

When contributing features:
- **Privacy**: No cloud logging of messages
- **Safety**: Allowlist-first design
- **Age-appropriate**: Consider young users
- **Parental control**: Features should be parent-configurable
- **Content**: No exposure to inappropriate content

## Questions?

If you have questions about contributing, feel free to:
- Open an issue with the `question` label
- Ask in discussions (if enabled)
- Check [CLAUDE.md](CLAUDE.md) for architecture details

## Code of Conduct

Please be respectful and constructive in all interactions. See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) for details.

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for their specific contributions
- README.md acknowledgments section
- GitHub contributors page

Thank you for contributing to Kid Fax! 🎉

---

*Remember: Kid Fax is about creating magical communication experiences for kids and families. Keep contributions focused on that mission!*
