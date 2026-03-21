# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = [('icon.ico', '.'), ('ephe', 'ephe'), ('dynamic_settings_modules', 'dynamic_settings_modules')]
binaries = []
hiddenimports = ['pyjhora']
datas += collect_data_files('timezonefinder')
tmp_ret = collect_all('pyjhora')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('jhora')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6.QtWebEngine', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtNetwork', 'PyQt6.QtSql', 'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets', 'PyQt6.QtQml', 'PyQt6.QtQuick', 'PyQt6.QtQuickWidgets', 'PyQt6.QtDBus', 'PyQt6.QtBluetooth', 'PyQt6.QtOpenGL', 'PyQt6.QtSensors', 'PyQt6.QtSerialPort', 'PyQt6.QtTest', 'PyQt6.QtXml', 'PyQt6.QtWebChannel', 'PyQt6.QtWebSockets', 'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender', 'PyQt6.QtPrintSupport', 'PyQt6.QtDesigner', 'tkinter', 'unittest', 'pydoc', 'sqlite3', 'pdb', 'matplotlib', 'scipy', 'PyQt5', 'PySide2', 'PySide6', 'IPython', 'notebook', 'jupyter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AstroBasics',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AstroBasics',
)
