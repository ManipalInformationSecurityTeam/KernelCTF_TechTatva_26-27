# The Midnight Gallery

## Layout

```
challenge/
├── README.md                  this file
├── DEPLOY.md                  hosting guide (for whoever deploys)
├── .gitignore
├── run_local.py               starts the site on this machine (Windows & Linux)
├── docker-compose.yml         two containers (for hosting)
├── deploy.sh                  build, start, verify (for hosting)
├── teardown.sh                stop and remove containers (for hosting)
├── app/                       PUBLIC: gateway web app
│   ├── Dockerfile
│   └── app.py
├── diag/                      PUBLIC: internal diagnostics service
│   ├── Dockerfile
│   ├── diag_service.py
│   └── shard3.txt
├── solve/                     PRIVATE: reference solver
│   └── solve.py
└── docs/
    └── WRITEUP.md             problem description, then full solution (distribute to players)
```

## Run locally

Requires Python 3.9 or newer. On Linux, `ping` must be on PATH (package `iputils-ping`).
Windows includes `ping`.

```
python run_local.py           # from inside challenge/; open http://localhost:8080
python solve/solve.py         # in another terminal; must print PASS
```

Press Ctrl+C in the launcher terminal to stop.

## Verify

`solve/solve.py [URL]` runs the full five-step chain and prints `PASS` when the flag
matches. The default URL is `http://127.0.0.1:8080`.

## Hosting

See `DEPLOY.md`.
