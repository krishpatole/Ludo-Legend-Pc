# Building the Android APK

Use **Linux, WSL2 (Ubuntu) or macOS** - Buildozer does not run natively on Windows. The first build downloads the
Android SDK/NDK (several GB) and takes a long time.

## Commands (Ubuntu / WSL2)
```
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev \
    libncurses-dev cmake libffi-dev libssl-dev
pip install --user buildozer cython
cd LUDO_LEGENDS
buildozer android debug
```
Output: `bin/ludolegends-1.0-*-debug.apk`. Install it on a phone with USB debugging:
```
buildozer android deploy run logcat
```
or copy the apk to the phone and open it (allow "install unknown apps").

## What the project already does for phones
- Fixed 1366x768 canvas, scaled and letter-boxed to the screen; taps are mapped back to canvas coordinates.
- Android sends taps as mouse events (SDL2), so no touch-specific code path is needed. The Android Back button returns to the menu.
- Landscape, fullscreen (`buildozer.spec`).
- Sounds are synthesised at startup (a few seconds on slower phones); real files in `assets/sounds/` replace them.

## Known risks (not yet verified)
- python-for-android's `pygame` recipe is **pygame 2.1.0** and its own docs call it "usable, but not complete"
  (no freetype - this game only uses `pygame.font`, which is included). Rendering/performance on real devices is untested.
- Portrait phones show the game letter-boxed and small; a dedicated portrait layout does not exist yet.

## Status
`buildozer.spec` is written but **no APK has been built and nothing has been tested on a real phone** yet.
