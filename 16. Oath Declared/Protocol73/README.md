# Protocol 73 — Restricted Document Intake

## Windows local setup

1. Install Python 3.11 or 3.12 and ensure the Python launcher (`py`) is available.
2. Copy `.env.example` to `.env`.
3. Edit `.env` and set `P73_FLAG` to your real CTF flag, `P73_FLASK_SECRET` to a long random secret, and `P73_REQUIRED_COUNT=120`. Do not commit or share `.env`.
4. Double-click `run_windows.bat`.
5. Wait for the dependency installation and server startup to finish, then open <http://127.0.0.1:5000>.

The batch file changes to its own directory, creates `.venv` if needed, installs from `requirements.txt`, and runs Waitress. Keep the terminal open while using the site. Press Ctrl+C to stop it.

## Linux / Docker

Local Linux: copy `.env.example` to `.env`, edit it, then run `./run.sh` after installing dependencies. For Docker:

```bash
docker build -t protocol73 .
docker run --env-file .env -p 5000:5000 protocol73
```

The image excludes `.env`; pass it at runtime. For a public HTTPS deployment, use `P73_ENV=production`, a strong `P73_FLASK_SECRET`, and `P73_SECURE_COOKIE=1`.

## Troubleshooting

- **`ModuleNotFoundError: checks` or `requirements`:** run the batch file from this extracted folder; do not rename the Python modules.
- **`TemplateNotFound: review.html`:** make sure `templates/review.html` exists inside this folder.
- **Port already in use:** change `set "PORT=5000"` to `set "PORT=5001"` in `run_windows.bat`, restart, then open `http://127.0.0.1:5001`.
- **Browser looks blank / server error:** keep the terminal visible and inspect the traceback printed there. Do not close the terminal before checking it.

## Updated challenge behavior

The challenge runs **120 sequential conditions** by default, selected from the existing 500-item requirement bank. The four system-log stages always appear in this exact order: **document**, **audit**, **review**, **complete auditorial review**. Each stage name is bolded and followed by short status text. The separate four-stage boxes are removed.

The generated audit copy preserves the intentional second-render SSTI mechanic. A harmless expression such as `{{ 7*7 }}` visibly evaluates to `49`, and the requirement bank retains its staged clues for template rendering and the nested review object.
