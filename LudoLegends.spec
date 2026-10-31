# -*- mode: python ; coding: utf-8 -*-
# Windows .exe build spec (also works on Linux/macOS to make a native binary).
#   pip install -r requirements-dev.txt
#   pyinstaller LudoLegends.spec --noconfirm
# Output: dist/LudoLegends.exe  (single file, no console window)
# Crash details are written to ludo_legends_crash.log next to the exe (see main.py).

a = Analysis(
    ['main.py'],
    pathex=['.'],
    datas=[('assets', 'assets')],          # put your own .ogg/.wav/.mp3 files in assets/sounds
    hiddenimports=[],
    excludes=['tkinter', 'unittest', 'pydoc', 'test', 'distutils'],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='LudoLegends',
    console=False,        # set True while debugging to see a console window
    upx=False,
    icon=None,            # e.g. icon='assets/images/icon.ico' once you have one
)
