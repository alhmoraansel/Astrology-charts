# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('icon.ico', '.'), ('ephe', 'ephe'), ('dynamic_settings_modules', 'dynamic_settings_modules')]
datas += collect_data_files('timezonefinder')


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['save_prefs', 'queue', 'threading', 'PyQt6.QtCore', 'traceback', 'warnings', 'chart_renderer', 'pickle', 'os', 'urllib.error', 'PyQt6.QtGui', 'builtins', 'subprocess', 'copy', 'rectification_engine', 'PyQt6.QtWidgets', 'datetime', 'timezonefinder', 'astro_engine', 'urllib.request', 'dynamic_settings_modules', 'main', 'math', 'time', 'swisseph', 'dynamic_settings_modules.composite_strength_module', 'hashlib', 'logging', 'sys', 'importlib', 'json', 'dateutil.relativedelta'],
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
