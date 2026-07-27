[app]
title = Go Game
package.name = gogame
package.domain = org.example.gogame

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,cfg,bin.gz,txt.gz,json,txt
source.include_patterns = assets/*,images/*.png,data/*
source.exclude_exts = spec
source.exclude_dirs = tests, bin, .buildozer, .git, __pycache__

version = 1.0
requirements = python3,kivy==2.3.1

orientation = portrait
fullscreen = 0
android.minapi = 21
android.api = 33
android.archs = arm64-v8a
android.allow_backup = True

android.permissions = INTERNET

[buildozer]
log_level = 2
warn_on_root = 1
