Set-Location $PSScriptRoot
if (!(Test-Path .venv\Scripts\python.exe)) { py -m venv .venv }
.venv\Scripts\python.exe -m pip install -r requirements.txt
if (-not $env:P73_THREADS) { $env:P73_THREADS = "8" }
if (-not $env:PORT) { $env:PORT = "5000" }
.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:$env:PORT --threads=$env:P73_THREADS app:app
