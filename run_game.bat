@echo off
REM One-click launcher for Windows: creates .venv on first run, installs pygame, starts the game.
cd /d "%~dp0"
where py >nul 2>nul || (echo Python not found. Install Python 3.9+ from https://www.python.org/downloads/ and tick "Add python.exe to PATH". & pause & exit /b 1)
if not exist .venv\Scripts\python.exe (py -3 -m venv .venv || (pause & exit /b 1))
.venv\Scripts\python.exe -m pip install -q -r requirements.txt || (pause & exit /b 1)
.venv\Scripts\python.exe main.py
if errorlevel 1 (echo. & echo The game crashed - see ludo_legends_crash.log & pause)
