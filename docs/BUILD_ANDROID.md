# Building the Android APK

Use **Linux, WSL2 (Ubuntu) or macOS** - Buildozer does not run natively on Windows. The first build downloads the
Android SDK/NDK (several GB) and takes a long time.

## Option A - build in the cloud (no Android tools on your PC)
1. Create a GitHub repository and upload the whole `LUDO_LEGENDS` folder (it contains `.github/workflows/android-apk.yml`).
2. GitHub -> **Actions** -> **Build Android APK** -> **Run workflow**.
3. When it turns green (the first run takes roughly 20-40 minutes), download the **ludolegends-apk** artifact, unzip it,
   copy the `.apk` to your phone and open it (allow "install unknown apps").

## Option B - build on Ubuntu / WSL2 (commands)
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

## Android pygame compatibility fix

The Android build uses a project-local python-for-android recipe at
`p4a-recipes/pygame/`. It builds pygame 2.6.1 from the upstream GitHub source
archive instead of the bundled pygame 2.1.0 recipe. This is needed because the
old generated C source includes `longintrepr.h`, which is not available as a
public header in CPython 3.12 and later.

The local recipe also omits pygame's optional `_sprite.pyx` accelerator when
building with Cython 3.1 and adds the SIMD blitter sources to the Android
surface module. These are build compatibility changes; they do not change
LUDO LEGENDS gameplay code.

A successful GitHub Actions build only confirms that the APK was packaged.
Install and launch it on a real Android device to verify rendering, sound,
touch input, and portrait layout.

## What the project already does for phones
- **Portrait phone layout (720x1280)** - chosen automatically on Android (also: `python main.py --portrait` or the
  environment variable `LUDO_LAYOUT=portrait` on a PC to preview it). Red/Green zones sit above the board, Yellow/Blue
  below it, the turn panel is a strip at the top and every setup screen is re-laid out for a narrow screen.
  Windows/desktop keeps the 1366x768 landscape layout (`--landscape` forces it).
- The canvas is scaled and letter-boxed to the screen; taps are mapped back to canvas coordinates.
- Android sends taps as mouse events (SDL2), so no touch-specific code path is needed. The Android Back button returns to the menu.
- Portrait, fullscreen (`orientation = portrait` in `buildozer.spec`).
- Sounds are synthesised at startup (a few seconds on slower phones); real files in `assets/sounds/` replace them.

## Known risks (not yet verified)
- python-for-android's `pygame` recipe is **pygame 2.1.0** and its own docs call it "usable, but not complete"
  (no freetype - this game only uses `pygame.font`, which is included). Rendering/performance on real devices is untested.
- Typing names uses the phone's on-screen keyboard (SDL text input); this is untested on a real phone.

## Status
`buildozer.spec` and the GitHub workflow are written but **no APK has been built and nothing has been tested on a real
phone**. The environment this game was developed in cannot reach the Android SDK/NDK download servers, so building
the APK has to happen with Option A or B above. The portrait *layout* is tested headlessly (`tests/test_portrait.py`).
