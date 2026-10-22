@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  py -m venv .venv
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if "%P73_THREADS%"=="" set "P73_THREADS=8"
if "%PORT%"=="" set "PORT=5000"
.venv\Scripts\python.exe -m waitress --listen=127.0.0.1:%PORT% --threads=%P73_THREADS% app:app
