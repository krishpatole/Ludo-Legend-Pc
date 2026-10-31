# Android build config (phone/tablet). See docs/BUILD_ANDROID.md.
# NOT yet built or tested on a device by the author.
[app]
title = Ludo Legends
package.name = ludolegends
package.domain = org.ludolegends
source.dir = .
source.include_exts = py,png,jpg,ogg,wav,mp3,ttf
source.exclude_dirs = tests, docs, bin, .buildozer, __pycache__, dist, build, .venv
version = 1.0
# Use a local pygame 2.6.1 recipe: the bundled p4a pygame 2.1.0 recipe fails with CPython 3.14.
p4a.local_recipes = ./p4a-recipes
requirements = python3,pygame
orientation = portrait
fullscreen = 1
android.permissions =
android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
