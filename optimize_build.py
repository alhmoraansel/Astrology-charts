import subprocess
import sys

# The absolute bare minimum excludes to strip out PyQt6 bloat and unused standard libraries
EXCLUDES = [
    # Massive PyQt6 modules we do NOT need
    "PyQt6.QtWebEngine", "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtNetwork", "PyQt6.QtSql", "PyQt6.QtMultimedia",
    "PyQt6.QtMultimediaWidgets", "PyQt6.QtQml", "PyQt6.QtQuick",
    "PyQt6.QtQuickWidgets", "PyQt6.QtDBus", "PyQt6.QtBluetooth",
    "PyQt6.QtOpenGL", "PyQt6.QtSensors", "PyQt6.QtSerialPort",
    "PyQt6.QtTest", "PyQt6.QtXml", "PyQt6.QtWebChannel",
    "PyQt6.QtWebSockets", "PyQt6.Qt3DCore", "PyQt6.Qt3DRender",
    "PyQt6.QtPrintSupport", "PyQt6.QtDesigner",
    
    # Unused heavy Python standard/external libraries
    "tkinter", "unittest", "pydoc", "sqlite3", "pdb",
    "matplotlib", "scipy", "PyQt5", "PySide2", "PySide6",
    "IPython", "notebook", "jupyter"
]

def build_app():
    command = [
        "pyinstaller",
        "--noconfirm",
        "--name", "AstroBasics",
        "--windowed",
        "--icon", "icon.ico",
        "--add-data", "icon.ico;.",
        "--add-data", "ephe;ephe",
        "--add-data", "dynamic_settings_modules;dynamic_settings_modules",
        "--collect-data", "timezonefinder", "--onedir",
        "--hidden-import", "pyjhora",
        "--collect-all", "pyjhora",
        "--collect-all", "jhora"
    ]
#"--collect-all" , "jhora"
    # Append all our exclusions to the command
    for exc in EXCLUDES:
        command.extend(["--exclude-module", exc])

    # Target script
    command.append("main.py")

    print("🚀 Running highly optimized PyInstaller build...\n")
    print("Command executing:\n" + " ".join(command) + "\n")
    
    # Run the build
    subprocess.run(command, check=True)
    print("\n✅ Build complete! Check the 'dist' folder.")

if __name__ == "__main__":
    build_app()