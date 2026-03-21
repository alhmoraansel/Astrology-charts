import os
import sys
import json
import hashlib
import subprocess
import urllib.request
from urllib.error import URLError

from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QMessageBox, QProgressBar
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# --- CONFIGURATION ---
# Points directly to the raw files of your PyInstaller 'dist/Astro Basics' folder on GitHub
# Note: '%20' handles the space in 'Astro Basics'
UPDATE_SERVER_URL = "https://raw.githubusercontent.com/alhmoraansel/Astrology-charts/main/dist/AstroBasics/"
MANIFEST_FILENAME = "manifest.json"

def get_base_dir():
    """Get the root directory of the application."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file."""
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read(65536)
        while len(buf) > 0:
            hasher.update(buf)
            buf = f.read(65536)
    return hasher.hexdigest()

class UpdateWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, dict, str) # success, files_to_update, message
    
    def run(self):
        try:
            self.progress.emit(10, "Fetching update manifest...")
            
            # 1. Fetch remote manifest
            manifest_url = UPDATE_SERVER_URL + MANIFEST_FILENAME
            req = urllib.request.Request(manifest_url, headers={'User-Agent': 'AstroUpdater/1.0', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req) as response:
                remote_manifest = json.loads(response.read().decode())
                
            remote_files = remote_manifest.get("files", {})
            remote_version = remote_manifest.get("version", "Unknown")
            
            self.progress.emit(30, f"Analyzing version {remote_version}...")
            
            # 2. Compare hashes
            base_dir = get_base_dir()
            files_to_update = {}
            total_files = len(remote_files)
            
            for i, (rel_path, remote_hash) in enumerate(remote_files.items()):
                local_path = os.path.join(base_dir, rel_path)
                local_hash = get_file_hash(local_path)
                
                if local_hash != remote_hash:
                    files_to_update[rel_path] = remote_hash
                    
                self.progress.emit(30 + int((i / total_files) * 30), f"Checking files...")
            if not files_to_update:
                self.finished.emit(True, {}, f"No Updates Found! (V{remote_version})")
                return
                # 3. Download differing files
            self.progress.emit(60, f"Downloading {len(files_to_update)} updated files...")
            update_cache_dir = os.path.join(base_dir, "update_cache")
            os.makedirs(update_cache_dir, exist_ok=True)
            
            dl_count = 0
            for rel_path, remote_hash in files_to_update.items():
                url_rel_path = rel_path.replace("\\", "/").replace(" ", "%20")
                file_url = UPDATE_SERVER_URL + url_rel_path
                target_path = os.path.join(update_cache_dir, rel_path)
                print(target_path)
                part_path = target_path + ".part" # Temporary download path
                
                # 1. Check if the FULL file already exists and matches hash
                if os.path.exists(target_path):
                    if get_file_hash(target_path) == remote_hash:
                        dl_count += 1
                        self.progress.emit(60 + int((dl_count / len(files_to_update)) * 40), f"Verified {dl_count}/{len(files_to_update)}...")
                        continue

                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # 2. Download to the .part file
                try:
                    req = urllib.request.Request(file_url, headers={'User-Agent': 'AstroUpdater/1.0', 'Cache-Control': 'no-cache'})
                    with urllib.request.urlopen(req) as response, open(part_path, 'wb') as out_file:
                        # You could even do chunks here for better progress tracking
                        out_file.write(response.read())
                    
                    # 3. Download finished successfully? Rename it to the final name.
                    # os.replace is "atomic" on most systems, preventing corruption.
                    if os.path.exists(target_path):
                        os.remove(target_path) # Clean up old version if it existed
                    os.rename(part_path, target_path)
                    
                except Exception as e:
                    # Clean up the partial file if it fails so it doesn't clutter
                    if os.path.exists(part_path):
                        os.remove(part_path)
                    raise e 
                
                dl_count += 1
                self.progress.emit(60 + int((dl_count / len(files_to_update)) * 40), f"Downloaded {dl_count}/{len(files_to_update)}...")
            dl_count = 0
            for rel_path in files_to_update.keys():
                print(UPDATE_SERVER_URL + rel_path)
                # Ensure spaces and slashes are formatted cleanly for the web request
                url_rel_path = rel_path.replace("\\", "/").replace(" ", "%20")
                file_url = UPDATE_SERVER_URL + url_rel_path
                target_path = os.path.join(update_cache_dir, rel_path)
                
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                req = urllib.request.Request(file_url, headers={'User-Agent': 'AstroUpdater/1.0', 'Cache-Control': 'no-cache'})
                with urllib.request.urlopen(req) as response, open(target_path, 'wb') as out_file:
                    out_file.write(response.read())
                
                dl_count += 1
                self.progress.emit(60 + int((dl_count / len(files_to_update)) * 40), f"Downloaded file {dl_count}/{len(files_to_update)}...")
                
            self.finished.emit(True, files_to_update, "Download complete! Ready to install.")
            
        except URLError as e:
            self.finished.emit(False, {}, f"Update failed: {str(e)}")
        except Exception as e:
            self.finished.emit(False, {}, f"Update failed: {str(e)}")

def setup_ui(app, layout):
    """Contract method for dynamic module loader"""
    group = QGroupBox("Updater")
    v_layout = QVBoxLayout()
    v_layout.setContentsMargins(8, 8, 8, 8)
    
    status_label = QLabel("Click the button to check for updates.")
    status_label.setWordWrap(True)
    status_label.setStyleSheet("color: #555; font-size: 10px;")
    
    progress_bar = QProgressBar()
    progress_bar.setVisible(False)
    progress_bar.setFixedHeight(10)
    
    btn_check = QPushButton("Check for Updates")
    btn_check.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E8449; background-color: #E8F8F5; border: 1px solid #A2D9CE; border-radius: 4px;")
    btn_check.setFixedHeight(28)
    
    v_layout.addWidget(status_label)
    v_layout.addWidget(progress_bar)
    v_layout.addWidget(btn_check)
    group.setLayout(v_layout)
    layout.addWidget(group)
    
    app.updater_worker = None
    
    def on_check_clicked():
        btn_check.setEnabled(False)
        progress_bar.setVisible(True)
        progress_bar.setValue(0)
        
        app.updater_worker = UpdateWorker()
        app.updater_worker.progress.connect(
            lambda val, msg: (progress_bar.setValue(val), status_label.setText(msg))
        )
        app.updater_worker.finished.connect(on_update_finished)
        app.updater_worker.start()

    def on_update_finished(success, files_to_update, msg):
        btn_check.setEnabled(True)
        progress_bar.setVisible(False)
        status_label.setText(msg)
        
        if success and files_to_update:
            reply = QMessageBox.question(
                app, "Update Ready", 
                f"Downloaded {len(files_to_update)} updated file(s).\nThe application needs to restart to apply them.\n\nRestart now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                apply_update_and_restart()

    def apply_update_and_restart():
        base_dir = get_base_dir()
        cache_dir = os.path.join(base_dir, "update_cache")
        
        if sys.platform == "win32":
            bat_path = os.path.join(base_dir, "apply_update.bat")
            exe_name = os.path.basename(sys.executable) if getattr(sys, 'frozen', False) else "main.py"
            launch_cmd = f'start "" "{exe_name}"' if getattr(sys, 'frozen', False) else f'python "{exe_name}"'
            
            bat_content = f"""@echo off
/nobreak > NUL
xcopy /s /y /q "{cache_dir}\\*" "{base_dir}\\"
rmdir /s /q "{cache_dir}"
{launch_cmd}
del "%~f0"
"""
            with open(bat_path, "w") as f:
                f.write(bat_content)
                
            subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit(0)
            
    btn_check.clicked.connect(on_check_clicked)