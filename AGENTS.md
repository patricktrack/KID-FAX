# Repository Guidelines

## Project Structure & Module Organization
- **`kidfax/`** - Core Python module containing:
  - `printer.py` - Printer abstraction for USB, Serial, Network, Bluetooth
  - `sms_poller.py` - Twilio SMS polling service (main application)
  - `send_sms.py` - CLI tool for sending SMS replies
- **`.env.example`** - Configuration template for Twilio, printer, and Kid Fax settings
- **`requirements.txt`** - Python dependencies (python-escpos, twilio, pyusb, Pillow)
- **Documentation** - README, QUICK_START, SYSTEMD_SETUP, TWILIO_SETUP, DEPLOYMENT guides
- **`archive/`** - Archived web interface code (not part of current project)

## Build, Test, and Development Commands
- `pip install -r requirements.txt` – Install Kid Fax dependencies
- `python -m kidfax.sms_poller` – Start SMS polling service (main application)
- `python -m kidfax.send_sms grandma "Hi"` – Send SMS reply via contact name
- `python -m kidfax.send_sms +15551234567 "Hi"` – Send SMS reply via phone number
- `ALLOW_DUMMY_PRINTER=true python -m kidfax.sms_poller` – Test without hardware
- `sudo systemctl status kidfax` – Check service status (if running as systemd service)
- `sudo journalctl -u kidfax -f` – View service logs

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation
- Use type hints for function parameters and return types
- Environment variables are SCREAMING_SNAKE_CASE (see `.env.example`)
- Module functions prefixed with underscore for internal use (`_load_state`, `_sanitize`)
- Hardware interactions always wrapped in try/except blocks
- Use `logging.getLogger(__name__)` for module-level loggers

## Testing Guidelines
- Test with dummy printer mode: `ALLOW_DUMMY_PRINTER=true`
- Hardware tests require actual printer connected
- Integration tests need Twilio test credentials
- State management tests use temporary state files
- Manual testing workflow:
  1. Start poller with dummy printer
  2. Send test SMS to Twilio number
  3. Verify console output (dummy printer mode)
  4. Test reply: `python -m kidfax.send_sms +1... "test"`

## Commit & Pull Request Guidelines
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Examples:
  - `feat: add MMS image printing support`
  - `fix: handle printer disconnection gracefully`
  - `docs: improve Twilio setup guide`
- Each PR should describe:
  - Feature/fix summary
  - Manual testing steps (commands run, hardware used)
  - Link to related issues
  - Hardware tested on (printer model, Pi model)
- Test on actual hardware when possible
- Include SMS flow diagrams for feature changes
- Document new environment variables in `.env.example`

## Security & Configuration Tips
- **Never commit `.env`** with real credentials
- Use Twilio test credentials for development
- Keep ALLOWLIST restrictive (kid safety)
- Scrub phone numbers from logs before sharing
- All configuration via environment variables
- Use allowlists (`ALLOWLIST`, `CONTACTS`) for kid safety
- SMS messages not logged to files (privacy)

## Kid Fax Specific Guidelines
- **Philosophy**: SMS → Print → Reply. No web, no databases, local-only.
- **Safety first**: Allowlist filtering is critical for kid safety
- **Graceful degradation**: Always provide fallbacks (dummy printer, empty state, defaults)
- **Never crash**: Hardware failures should log and continue, not crash the poller
- **State tracking**: Prevent duplicate prints via JSON state file
- **Contact mapping**: Support both names and raw phone numbers

## Hardware Integration Notes
- When extending printer support, update `kidfax/printer.py`
- Add printer type to `get_printer()` function
- Update `.env.example` with new configuration variables
- Document in README.md and DEPLOYMENT.md
- Test with actual hardware if possible
- Provide dummy mode fallback for testing
