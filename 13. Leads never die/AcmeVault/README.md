# Acme Parser Differential - v8

Organizer package for the Acme Investigations web challenge.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
source .env
python security_data_audit.py
python differential_probe.py
python app.py
```

The real `forge_token.py`, `differential_probe.py`, and `security_data_audit.py` are organizer-only.

The player-facing app keeps passwords, the restricted flag, the signing key, and all sealed addendum contents server-side.
