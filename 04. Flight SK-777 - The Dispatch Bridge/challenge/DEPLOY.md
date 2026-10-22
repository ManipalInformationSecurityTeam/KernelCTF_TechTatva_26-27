# Deployment guide

This guide is for whoever hosts the challenge. Docker and the hosting setup are handled separately.

## What the app needs

- Python 3.10 or newer
- The packages in `requirements.txt`
- Nothing else. No environment variables are required.

## Start command (production)

Run from the `challenge/` folder:

```
gunicorn -w 1 --threads 8 -b 127.0.0.1:8000 wsgi:app
```

Use exactly one worker process (`-w 1`). The app keeps each player's session key in
memory, so a second worker process would not recognise sessions created by the first.
Threads (`--threads 8`) provide the concurrency.

Put a reverse proxy (nginx or Caddy) in front of it for HTTPS and the public port.
Forward all traffic to `127.0.0.1:8000`.

Health check: `GET /robots.txt` returns 200.

Restarting the server logs every player out. That is expected.

## Local start (testing only)

```
python3 app/app.py            # http://localhost:8080
```

## What to publish, and what not to

Players need only:

- `app/` (includes `app.py`, `templates/`, `static/`)
- `wsgi.py`
- `requirements.txt`

Do not publish these. They contain the full solution:

- `solve/`
- `docs/`
- `skynet_ctf.ipynb`
- this file

## Verification after deploy

From a copy of the full project on a different machine, run the solve against the public address:

```
python3 solve/solve.py https://<public-address>
```

It prints `PASS` when the flag matches.
