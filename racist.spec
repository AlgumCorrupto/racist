# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files
)

block_cipher = None

# --- Collect assets folder recursively ---
assets_datas = []
for root, dirs, files in os.walk("assets"):
    for file in files:
        full_path = os.path.join(root, file)
        relative_path = os.path.relpath(root, "assets")
        assets_datas.append((full_path, os.path.join("assets", relative_path)))

# --- Collect PySide6 ---
pyside_hidden = collect_submodules("PySide6")
pyside_datas = collect_data_files("PySide6")

# --- Collect qt-themes ---
qt_themes_hidden = collect_submodules("qt_themes")
qt_themes_datas = collect_data_files("qt_themes")

# --- Collect mymcplus ---
mymcplus_hidden = collect_submodules("mymcplus")
mymcplus_datas = collect_data_files("mymcplus")

a = Analysis(
    ['racist.py'],
    pathex=['src'],
    binaries=[],
    datas=(
        assets_datas
        + pyside_datas
        + qt_themes_datas
        + mymcplus_datas
    ),
    hiddenimports=(
        pyside_hidden
        + qt_themes_hidden
        + mymcplus_hidden
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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
    upx=True,
    console=False,
    icon='assets/icon.ico', 
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='racist'
)
