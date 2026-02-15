# -*- mode: python ; coding: utf-8 -*-

import os

block_cipher = None

# --- Collect assets recursively ---
assets_datas = []
for root, dirs, files in os.walk("assets"):
    for file in files:
        full_path = os.path.join(root, file)
        relative_path = os.path.relpath(root, "assets")
        assets_datas.append((full_path, os.path.join("assets", relative_path)))

a = Analysis(
    ['racist.py'],
    pathex=['src'],
    binaries=[],
    datas=assets_datas,
    hiddenimports=[],   # let PyInstaller auto-detect Qt modules
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtNetwork",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.QtWebEngine",
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtMultimedia",
        "PySide6.QtPositioning",
        "PySide6.QtBluetooth",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='racist',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='assets/icon.ico',
)
