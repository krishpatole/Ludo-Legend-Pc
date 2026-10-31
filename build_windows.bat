@echo off
REM Builds dist\LudoLegends.exe.  Run this on a WINDOWS machine (PyInstaller cannot cross-compile).
cd /d "%~dp0"
where py >nul 2>nul || (echo Python launcher "py" not found. Install Python 3.9+ from python.org & exit /b 1)
if not exist .venv (py -3 -m venv .venv || exit /b 1)
call .venv\Scripts\activate.bat || exit /b 1
python -m pip install --upgrade pip || exit /b 1
pip install -r requirements-dev.txt || exit /b 1
python run_tests.py || (echo Tests failed - not building. & exit /b 1)
pyinstaller LudoLegends.spec --noconfirm || exit /b 1
echo.
echo Done: dist\LudoLegends.exe
