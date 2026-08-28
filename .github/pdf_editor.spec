# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for PDF Editor.
#
# Build locally with:
#   pyinstaller --clean --noconfirm pdf_editor.spec
#
# On Windows this produces dist/PDF_Editor.exe
# On Linux/macOS it produces a native binary of the same name (useful for
# local smoke-testing the packaging step; it will NOT be a .exe).

block_cipher = None

a = Analysis(
    ['pdf_editor.py'],
    pathex=[],
    binaries=[],
    datas=[],
    # PyMuPDF and Pillow's Tk plumbing sometimes need a nudge from
    # PyInstaller's static import scanner.
    hiddenimports=['PIL._tkinter_finder', 'fitz'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
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
    name='PDF_Editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed app, no terminal popup
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # drop an .ico path here if you add one
)
