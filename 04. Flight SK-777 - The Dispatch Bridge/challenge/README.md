# SkyNet Flight SK-777: The Dispatch Bridge

Web exploitation (broken access control + header-based client check).
Flag format: `kernel{...}`.

## Layout

```
challenge/
├── README.md
├── requirements.txt          Flask
├── app/
│   ├── app.py                the web application
│   ├── templates/
│   │   └── dashboard.html
│   └── static/
│       ├── css/dashboard.css
│       └── js/dashboard.js
├── solve/
│   └── solve.py              reference solver; prints PASS when the flag matches
└── docs/
    └── WRITEUP.md            player writeup
```

## Run

```
pip install -r requirements.txt
python3 app/app.py            # serves http://localhost:8080
python3 solve/solve.py        # in another terminal; must print PASS
```

Environment variables (local play only): `PORT` (default 8080) and `BIND` (default 127.0.0.1).

For hosting, see `DEPLOY.md`.
