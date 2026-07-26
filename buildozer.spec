[app]
title = 围棋对弈
package.name = gogame
package.domain = org.example.gogame

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,cfg,bin.gz,txt.gz
source.include_patterns = assets/*,images/*.png

version = 1.0
requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0
android.minapi = 21
android.api = 34
android.archs = arm64-v8a, armeabi-v7a

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

icon.filename = %(source.dir)s/data/icon.png
presplash.filename = %(source.dir)s/data/presplash.png

[buildozer]
log_level = 2
warn_on_root = 1
