# Repository Guidelines

## Project Structure & Module Organization
- Core Flask app lives in `app.py` with templates in `templates/` and static single-page frontend assets in `frontend/`.
- `'backend/'` hosts the API-only deployment (Flask + CORS) plus its own requirements file.
- `kidfax/` contains shared helpers (printer abstraction) and the Twilio-driven `sms_poller` + `send_sms` tools; run them as Python modules.
- Documentation for deployment and hardware integration is under the assorted `README_*.md` and setup guides (Netlify, Convex, Bluetooth printers, etc.).

## Build, Test, and Development Commands
- `pip install -r requirements.txt` – install app + Kid Fax dependencies inside your venv on the Pi.
- `pip install -r backend/requirements.txt` – minimal deps if only deploying the backend API.
- `python app.py` – serve the combined UI/API on a Pi or dev machine.
- `python backend/api.py` – run the API-only service (pair with the Netlify frontend).
- `python -m kidfax.sms_poller` – start the Twilio polling loop that prints SMS messages.
- `python -m kidfax.send_sms grandma "Hi"` – send a reply via the configured Twilio number.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation; keep modules short and compose helpers inside `kidfax/` for shared logic.
- Environment variables are SCREAMING_SNAKE_CASE (see `.env.example`); paths are lowercase with hyphens or underscores.
- When adding printers or transports, extend `kidfax/printer.py` rather than duplicating configuration code.

## Testing Guidelines
- No automated suite exists yet; when contributing Python code, add `pytest` tests under `tests/` (create it if needed) named `test_*.py` and ensure they can run offline with `pytest`.
- For hardware-dependent features, provide a dummy backend path (`ALLOW_DUMMY_PRINTER=true`) so tests can simulate output without a printer.

## Commit & Pull Request Guidelines
- Prefer conventional, descriptive commit subjects (e.g., `feat: add Twilio poller service` or `fix: guard printer init on Pi`).
- Each PR should describe the feature/fix, list manual testing steps (commands run, hardware used), link any related issues, and include screenshots or logs when UI or print output changes.
- Keep changes scoped; split large efforts into smaller PRs touching one logical area (frontend, backend, or kidfax tooling).

## Security & Configuration Tips
- Never commit `.env` or real Twilio credentials; rely on `.env.example` for placeholders.
- When sharing logs, scrub phone numbers and auth tokens.
- Use allowlists (`ALLOWLIST`, `CONTACTS`) and rate limits when extending Kid Fax to keep the kid-friendly environment safe.
