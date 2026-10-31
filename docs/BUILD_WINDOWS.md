# Building the Windows executable (.exe)

PyInstaller cannot cross-compile, so this must be done **on a Windows PC**.

## Automatic (recommended)
Open `cmd` or PowerShell in the project folder and run:
```
build_windows.bat
```
It creates a `.venv`, installs `requirements-dev.txt`, runs all tests, then builds. Result: `dist\LudoLegends.exe`.

## Manual
```
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python run_tests.py
pyinstaller LudoLegends.spec --noconfirm
```

## Notes
- Single file, no console window. If it fails to start, a traceback is written to `ludo_legends_crash.log` next to the exe.
  To see a console while debugging, set `console=True` in `LudoLegends.spec`.
- Custom sounds: put `.ogg/.wav/.mp3` files in `assets/sounds/` **before** building (they are bundled).
- Antivirus/SmartScreen may warn about unsigned PyInstaller exes; that is normal for unsigned apps.

## Status
The spec was verified by building and starting a **Linux** binary from it (PyInstaller 6.22). A real `.exe`
has **not** been built or run yet, because that needs a Windows machine.
