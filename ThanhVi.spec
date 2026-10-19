# -*- mode: python ; coding: utf-8 -*-
from pathlib import PureWindowsPath


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/fonts/DancingScript.ttf', 'assets/fonts'), ('assets/fonts/OFL.txt', 'assets/fonts'),
           ('assets/licenses', 'assets/licenses'), ('THIRD_PARTY_NOTICES.md', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['gradio', 'matplotlib', 'scipy', 'pandas', 'tkinter', 'PyQt5', 'PyQt6', 'PySide2'],
    noarchive=False,
    optimize=0,
)
# Qt on Windows uses the OS ICU API (unsuffixed exports). A Poppler install on
# PATH can fool dependency scanning into collecting its incompatible icuuc.dll.
# Leave this Windows system library to the OS loader, as in an unpackaged run.
a.binaries = [entry for entry in a.binaries
              if PureWindowsPath(entry[0]).name.lower() != 'icuuc.dll']
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ThanhVi',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
