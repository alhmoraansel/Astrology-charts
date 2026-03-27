import subprocess
import sys
import os
import ast

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

# Base list of explicit hidden imports just in case
BASE_HIDDEN_IMPORTS = [
    "urllib.request",
    "urllib.error",
    "subprocess",
    "hashlib"
]

def get_dynamic_imports(directory="dynamic_settings_modules"):
    """Scans the dynamic modules directory for imported libraries."""
    found_imports = set()
    if not os.path.exists(directory):
        print(f"Directory '{directory}' not found. Skipping dynamic import scan.")
        return []

    print(f"🔍 Scanning '{directory}' for dynamic imports...")
    for filename in os.listdir(directory):
        if filename.endswith(".py") and not filename.startswith("__"):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=filepath)
                    
                for node in ast.walk(tree):
                    # Catch 'import x'
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            found_imports.add(alias.name)
                    # Catch 'from x import y'
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            found_imports.add(node.module)
            except Exception as e:
                print(f"⚠️ Warning: Failed to parse {filename} for imports: {e}")
    
    return list(found_imports)

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
        "--collect-data", "timezonefinder", "--onedir"
    ]
    
    # Combine baseline hidden imports with dynamically discovered ones
    dynamic_imports = get_dynamic_imports()
    all_hidden_imports = set(BASE_HIDDEN_IMPORTS + dynamic_imports)
    
    if dynamic_imports:
        print(f"📦 Discovered plugin dependencies: {', '.join(dynamic_imports)}")

    # Add hidden imports so dynamic modules don't crash from missing dependencies
    for hi in all_hidden_imports:
        # Safety check: Don't import something we explicitly excluded
        if hi not in EXCLUDES:
            command.extend(["--hidden-import", hi])

    # Append all our exclusions to the command
    for exc in EXCLUDES:
        command.extend(["--exclude-module", exc])

    # Target script
    command.append("main.py")

    print("\n🚀 Running highly optimized PyInstaller build...\n")
    print("Command executing:\n" + " ".join(command) + "\n")
    
    # Run the build
    subprocess.run(command, check=True)
    print("\n✅ Build complete! Check the 'dist' folder.")

if __name__ == "__main__":
    build_app()