import os
import sys
import json
import hashlib
import subprocess
import urllib.request
import time
from urllib.error import URLError

from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, QMessageBox, QProgressBar, QApplication
from PyQt6.QtCore import QThread, pyqtSignal, Qt

# --- CONFIGURATION ---
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
    finished = pyqtSignal(bool, dict, list, str) # success, files_to_update, files_to_delete, message
    
    def run(self):
        try:
            self.progress.emit(10, "Fetching update manifest...")
            
            # 1. Fetch remote manifest
            manifest_url = UPDATE_SERVER_URL + MANIFEST_FILENAME
            req = urllib.request.Request(manifest_url, headers={'User-Agent': 'AstroUpdater/1.2', 'Cache-Control': 'no-cache'})
            with urllib.request.urlopen(req, timeout=10) as response:
                remote_manifest = json.loads(response.read().decode('utf-8'))
                
            remote_files = remote_manifest.get("files", {})
            remote_version = remote_manifest.get("version", "Unknown")
            
            base_dir = get_base_dir()
            local_manifest_path = os.path.join(base_dir, MANIFEST_FILENAME)
            hash_cache_path = os.path.join(base_dir, ".hash_cache.json")
            
            self.progress.emit(30, f"Analyzing version {remote_version}...")
            
            # Load local hash cache to speed up deep checks
            local_hash_cache = {}
            if os.path.exists(hash_cache_path):
                try:
                    with open(hash_cache_path, 'r') as f:
                        local_hash_cache = json.load(f)
                except json.JSONDecodeError:
                    pass
            
            # 2. Compare hashes (Deep Check) & Find Deleted Files
            files_to_update = {}
            files_to_delete = []
            total_files = len(remote_files)
            
            if total_files == 0:
                self.finished.emit(True, {}, [], f"No files in remote update. (V{remote_version})")
                return

            # Scan local directory for files that no longer exist on remote
            exclude_dirs = {'update_cache', 'autosave', 'analysis_export', 'saves', '__pycache__'}
            exclude_files = {'manifest.json', 'astro_settings.json', 'apply_update.bat', 'apply_update.sh', '.hash_cache.json'}
            
            for root, dirs, files in os.walk(base_dir):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                for file in files:
                    if file in exclude_files or file.endswith(".pyc"):
                        continue
                        
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, base_dir)
                    rel_path_unix = rel_path.replace("\\", "/")
                    
                    if rel_path_unix not in remote_files:
                        files_to_delete.append(rel_path)
                
            for i, (rel_path, remote_hash) in enumerate(remote_files.items()):
                os_rel_path = os.path.normpath(rel_path)
                local_path = os.path.join(base_dir, os_rel_path)
                
                local_hash = None
                if os.path.exists(local_path):
                    try:
                        stat = os.stat(local_path)
                        mtime = stat.st_mtime
                        size = stat.st_size
                        
                        cached_data = local_hash_cache.get(rel_path)
                        if cached_data and cached_data.get('mtime') == mtime and cached_data.get('size') == size:
                            local_hash = cached_data.get('hash')
                        else:
                            local_hash = get_file_hash(local_path)
                            local_hash_cache[rel_path] = {'mtime': mtime, 'size': size, 'hash': local_hash}
                    except OSError:
                        local_hash = get_file_hash(local_path)
                
                if local_hash != remote_hash:
                    files_to_update[rel_path] = remote_hash
                    
                if i % max(1, total_files // 10) == 0:
                    self.progress.emit(30 + int((i / total_files) * 30), f"Checking file hashes...")
                    
            # Save the updated hash cache for the next run
            try:
                with open(hash_cache_path, 'w') as f:
                    json.dump(local_hash_cache, f)
            except Exception:
                pass

            if not files_to_update and not files_to_delete:
                # Edge Case: Files match but version differs. Update local manifest silently.
                with open(local_manifest_path, 'w') as f:
                    json.dump(remote_manifest, f, indent=4)
                self.progress.emit(100, "Up to date.")
                self.finished.emit(True, {}, [], f"No Updates Found! (V{remote_version})")
                return

            update_cache_dir = os.path.join(base_dir, "update_cache")
            os.makedirs(update_cache_dir, exist_ok=True)
            
            # Determine exactly what needs to be downloaded over the network
            files_to_download = {}
            for rel_path, remote_hash in files_to_update.items():
                os_rel_path = os.path.normpath(rel_path)
                target_path = os.path.join(update_cache_dir, os_rel_path)
                # If it's already in the cache with the correct hash, skip download
                if not (os.path.exists(target_path) and get_file_hash(target_path) == remote_hash):
                    files_to_download[rel_path] = remote_hash

            if files_to_download:
                self.progress.emit(60, f"Downloading {len(files_to_download)} required file(s)...")
                dl_count = 0
                for rel_path, remote_hash in files_to_download.items():
                    url_rel_path = rel_path.replace("\\", "/").replace(" ", "%20")
                    file_url = UPDATE_SERVER_URL + url_rel_path
                    
                    os_rel_path = os.path.normpath(rel_path)
                    target_path = os.path.join(update_cache_dir, os_rel_path)
                    part_path = target_path + ".part"
                    
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    # Download with retry logic
                    retries = 3
                    for attempt in range(retries):
                        try:
                            req = urllib.request.Request(file_url, headers={'User-Agent': 'AstroUpdater/1.2', 'Cache-Control': 'no-cache'})
                            with urllib.request.urlopen(req, timeout=15) as response, open(part_path, 'wb') as out_file:
                                out_file.write(response.read())
                            
                            if os.path.exists(target_path):
                                os.remove(target_path)
                            os.rename(part_path, target_path)
                            break
                        except Exception as e:
                            if os.path.exists(part_path):
                                os.remove(part_path)
                            if attempt == retries - 1:
                                raise e 
                            time.sleep(1)
                    
                    dl_count += 1
                    self.progress.emit(60 + int((dl_count / len(files_to_download)) * 35), f"Downloaded {dl_count}/{len(files_to_download)}...")
            
            # CRITICAL: Save the new manifest to the cache so it replaces the old one
            manifest_cache_path = os.path.join(update_cache_dir, MANIFEST_FILENAME)
            with open(manifest_cache_path, 'w') as f:
                json.dump(remote_manifest, f, indent=4)
                
            self.progress.emit(100, "Update processing complete.")
            self.finished.emit(True, files_to_update, files_to_delete, f"Ready to install v{remote_version}.")
            
        except URLError as e:
            self.finished.emit(False, {}, [], f"Network error: {str(e)}")
        except Exception as e:
            self.finished.emit(False, {}, [], f"Update failed: {str(e)}")

def setup_ui(app, layout):
    """Contract method for dynamic module loader"""
    app.pending_update_files_to_delete = None
    
    group = QGroupBox("Updater")
    v_layout = QVBoxLayout()
    v_layout.setContentsMargins(8, 8, 8, 8)
    
    status_label = QLabel("Click the button to check for updates.")
    status_label.setWordWrap(True)
    status_label.setStyleSheet("color: #555; font-size: 11px;")
    
    progress_bar = QProgressBar()
    progress_bar.setVisible(False)
    progress_bar.setFixedHeight(12)
    progress_bar.setTextVisible(False)
    
    btn_check = QPushButton("Check for Updates")
    btn_check.setStyleSheet("font-size: 13px; font-weight: bold; color: #1E8449; background-color: #E8F8F5; border: 1px solid #A2D9CE; border-radius: 4px;")
    btn_check.setFixedHeight(28)
    
    v_layout.addWidget(status_label)
    v_layout.addWidget(progress_bar)
    v_layout.addWidget(btn_check)
    group.setLayout(v_layout)
    layout.addWidget(group)
    
    app.updater_worker = None
    
    def on_progress(val, msg):
        try:
            progress_bar.setValue(val)
            status_label.setText(msg)
        except RuntimeError:
            pass # UI was destroyed, ignore updates

    def on_check_clicked():
        try:
            btn_check.setEnabled(False)
            progress_bar.setVisible(True)
            progress_bar.setValue(0)
        except RuntimeError:
            return
        
        app.updater_worker = UpdateWorker()
        app.updater_worker.progress.connect(on_progress)
        app.updater_worker.finished.connect(on_update_finished)
        app.updater_worker.start()

    def on_update_finished(success, files_to_update, files_to_delete, msg):
        try:
            btn_check.setEnabled(True)
            progress_bar.setVisible(False)
            status_label.setText(msg)
        except RuntimeError:
            return # UI has been deleted (app closed or reloaded), abort dialog logic
        
        if success and (files_to_update or files_to_delete):
            msg_text = ""
            if files_to_update:
                msg_text += f"Found {len(files_to_update)} file(s) changed/added.\n"
            if files_to_delete:
                msg_text += f"Found {len(files_to_delete)} obsolete file(s) to remove.\n"
                
            msg_text += "\nThe application needs to restart to apply changes.\n\nRestart now?"
            
            try:
                reply = QMessageBox.question(
                    app, "Update Ready", 
                    msg_text,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
            except RuntimeError:
                return # App window was deleted while waiting to show the dialog
            
            if reply == QMessageBox.StandardButton.Yes:
                app.pending_update_files_to_delete = None
                apply_update_and_restart(files_to_delete, relaunch=True)
            else:
                app.pending_update_files_to_delete = files_to_delete
                try:
                    status_label.setText("Update will be applied automatically on exit.")
                except RuntimeError:
                    pass

    def apply_update_and_restart(files_to_delete, relaunch=True):
        base_dir = get_base_dir()
        cache_dir = os.path.join(base_dir, "update_cache")
        
        is_frozen = getattr(sys, 'frozen', False)
        exe_name = os.path.basename(sys.executable) if is_frozen else "main.py"
        
        deletion_commands_bat = ""
        deletion_commands_sh = ""
        if files_to_delete:
            for f in files_to_delete:
                abs_path = os.path.join(base_dir, f)
                deletion_commands_bat += f'del /f /q "{abs_path}" 2>nul\n'
                deletion_commands_sh += f'rm -f "{abs_path}"\n'
        
        if sys.platform == "win32":
            bat_path = os.path.join(base_dir, "apply_update.bat")
            launch_cmd = f'start "" "{exe_name}"' if is_frozen else f'python "{exe_name}"'
            launch_str = f"{launch_cmd}\n" if relaunch else ""
            
            # timeout /t 2 ensures the python app completely releases locks on Windows before xcopy triggers
            bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
{deletion_commands_bat}xcopy /s /y /q "{cache_dir}\\*" "{base_dir}\\"
rmdir /s /q "{cache_dir}"
{launch_str}del "%~f0"
"""
            with open(bat_path, "w") as f:
                f.write(bat_content)
                
            subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit(0)
            
        else:
            # POSIX compliance for Mac/Linux
            sh_path = os.path.join(base_dir, "apply_update.sh")
            launch_cmd = f'"{sys.executable}" "{exe_name}"' if not is_frozen else f'./"{exe_name}"'
            launch_str = f"{launch_cmd} &\n" if relaunch else ""
            
            sh_content = f"""#!/bin/bash
sleep 2
{deletion_commands_sh}cp -R "{cache_dir}/"* "{base_dir}/"
rm -rf "{cache_dir}"
{launch_str}rm -- "$0"
"""
            with open(sh_path, "w") as f:
                f.write(sh_content)
            os.chmod(sh_path, 0o755)
            subprocess.Popen([sh_path], start_new_session=True)
            sys.exit(0)
            
    # Safely attach the restart function to the app instance in case of module reloads
    app._apply_update_func = apply_update_and_restart

    def on_app_quit():
        if getattr(app, 'pending_update_files_to_delete', None) is not None:
            app._apply_update_func(app.pending_update_files_to_delete, relaunch=False)

    q_app = QApplication.instance()
    if not hasattr(app, '_updater_quit_connected'):
        q_app.aboutToQuit.connect(on_app_quit)
        app._updater_quit_connected = True

    btn_check.clicked.connect(on_check_clicked)