#dynamic_settings_module/zupdater.py

import os
from pickle import FALSE
import sys
import json
import hashlib
import subprocess
import urllib.request
import time
from urllib.error import URLError

from PyQt6.QtWidgets import (
    QGroupBox, QVBoxLayout, QPushButton, QLabel, QHBoxLayout, 
    QMessageBox, QProgressBar, QApplication, QCheckBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer


PLUGIN_GROUP = "UTILS"
PLUGIN_INDEX = 80

# --- CONFIGURATION ---
UPDATE_SERVER_URL = "https://raw.githubusercontent.com/alhmoraansel/Astrology-charts/main/dist/AstroBasics/"
MANIFEST_FILENAME = "manifest.json"

# --- PROTECTED PATHS ---
# These files and directories will NEVER be deleted or overwritten by remote files.
PROTECTED_DIRS = {'update_cache', 'autosave', 'analysis_export', 'created chart exports', 'saves', '__pycache__'}
PROTECTED_FILES = {
    'manifest.json', 'icon.ico', 'astro_settings.json', 'custom_vargas.json', 
    'apply_update.bat', 'apply_update.sh', '.hash_cache.json', 'csi_weights_prefs.json',
    'unins000.exe', 'unins000.dat', 'updater_config.json'
}

def get_base_dir():
    """Get the root directory of the application."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(".")

def get_file_hash(filepath):
    """Calculate SHA256 hash of a file, normalizing line endings and trailing whitespaces for text files."""
    if not os.path.exists(filepath):
        return None
    hasher = hashlib.sha256()
    
    text_extensions = {
        '.py', '.json', '.txt', '.md', '.bat', '.sh', '.csv', 
        '.ini', '.cfg', '.toml', '.xml', '.yml', '.yaml', '.rst', 
        '.html', '.css', '.js'
    }
    text_filenames = {
        'license', 'licence', 'record', 'installer', 'metadata', 
        'wheel', 'notice', 'readme', 'authors', 'contributors'
    }
    
    _, ext = os.path.splitext(filepath)
    filename = os.path.basename(filepath).lower()
    
    is_text = (ext.lower() in text_extensions) or \
              (filename in text_filenames) or \
              (filename.startswith('license')) or \
              (filename.startswith('readme'))
    
    if not is_text and not ext:
        try:
            with open(filepath, 'rb') as f:
                chunk = f.read(8192)
                if chunk and b'\x00' not in chunk:
                    is_text = True
        except Exception:
            pass
    
    try:
        with open(filepath, 'rb') as f:
            if is_text:
                content = f.read()
                content = content.replace(b'\r\n', b'\n').replace(b'\r', b'\n')
                # Robustly ignore trailing spaces on each line and blank lines at EOF
                # This counters Git's autocrlf and EOF-fixer pre-commit hooks
                lines = [line.rstrip(b' \t') for line in content.split(b'\n')]
                while lines and not lines[-1]:
                    lines.pop()
                content = b'\n'.join(lines)
                hasher.update(content)
            else:
                buf = f.read(65536)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = f.read(65536)
    except Exception:
        return None
        
    return hasher.hexdigest()

class UpdateWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, dict, list, str) 
    
    def __init__(self, full_update=False):
        super().__init__()
        self.full_update = full_update
    
    def run(self):
        try:
            mode_str = "FULL " if self.full_update else ""
            self.progress.emit(10, f"Fetching {mode_str}update manifest...")
            
            # 1. Fetch remote manifest with cache busting
            cache_buster = f"?t={int(time.time())}"
            manifest_url = UPDATE_SERVER_URL + MANIFEST_FILENAME + cache_buster
            req = urllib.request.Request(
                manifest_url, 
                headers={'User-Agent': 'AstroUpdater/1.5', 'Cache-Control': 'no-cache, no-store, must-revalidate'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                remote_manifest = json.loads(response.read().decode('utf-8'))
                
            remote_files = remote_manifest.get("files", {})
            remote_version = remote_manifest.get("version", "Unknown")
            
            base_dir = get_base_dir()
            local_manifest_path = os.path.join(base_dir, MANIFEST_FILENAME)
            hash_cache_path = os.path.join(base_dir, ".hash_cache.json")
            
            self.progress.emit(30, f"Analyzing version {remote_version}...")
            
            local_hash_cache = {}
            if os.path.exists(hash_cache_path) and not self.full_update:
                try:
                    with open(hash_cache_path, 'r') as f:
                        local_hash_cache = json.load(f)
                except json.JSONDecodeError:
                    pass
            
            files_to_update = {}
            files_to_delete = []
            total_files = len(remote_files)
            
            if total_files == 0:
                self.finished.emit(True, {}, [], f"No files in remote update. (V{remote_version})")
                return

            for root, dirs, files in os.walk(base_dir):
                dirs[:] = [d for d in dirs if d not in PROTECTED_DIRS]
                for file in files:
                    if file in PROTECTED_FILES or file.endswith(".pyc"):
                        continue
                        
                    filepath = os.path.join(root, file)
                    rel_path = os.path.relpath(filepath, base_dir)
                    rel_path_unix = rel_path.replace("\\", "/")
                    
                    if self.full_update:
                        files_to_delete.append(rel_path)
                    elif rel_path_unix not in remote_files:
                        files_to_delete.append(rel_path)
            
            if self.full_update:
                for rel_path, remote_hash in remote_files.items():
                    rel_path_unix = rel_path.replace("\\", "/")
                    if rel_path_unix.split("/")[0] in PROTECTED_DIRS or os.path.basename(rel_path_unix) in PROTECTED_FILES:
                        continue
                    files_to_update[rel_path] = remote_hash
            else:
                for i, (rel_path, remote_hash) in enumerate(remote_files.items()):
                    rel_path_unix = rel_path.replace("\\", "/")
                    if rel_path_unix.split("/")[0] in PROTECTED_DIRS or os.path.basename(rel_path_unix) in PROTECTED_FILES:
                        continue
                        
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
                        self.progress.emit(30 + int((i / total_files) * 30), "Checking file hashes...")
                    
            if not self.full_update:
                try:
                    with open(hash_cache_path, 'w') as f:
                        json.dump(local_hash_cache, f)
                except Exception:
                    pass

            if not files_to_update and not files_to_delete:
                with open(local_manifest_path, 'w') as f:
                    json.dump(remote_manifest, f, indent=4)
                self.progress.emit(100, "Up to date.")
                self.finished.emit(True, {}, [], f"No Updates Found! (V{remote_version})")
                return

            update_cache_dir = os.path.join(base_dir, "update_cache")
            os.makedirs(update_cache_dir, exist_ok=True)
            
            files_to_download = {}
            for rel_path, remote_hash in files_to_update.items():
                os_rel_path = os.path.normpath(rel_path)
                target_path = os.path.join(update_cache_dir, os_rel_path)
                if self.full_update or not (os.path.exists(target_path) and get_file_hash(target_path) == remote_hash):
                    files_to_download[rel_path] = remote_hash

            if files_to_download:
                self.progress.emit(60, f"Downloading {len(files_to_download)} required file(s)...")
                dl_count = 0
                for rel_path, remote_hash in files_to_download.items():
                    url_rel_path = rel_path.replace("\\", "/").replace(" ", "%20")
                    file_url = UPDATE_SERVER_URL + url_rel_path + cache_buster
                    
                    os_rel_path = os.path.normpath(rel_path)
                    target_path = os.path.join(update_cache_dir, os_rel_path)
                    part_path = target_path + ".part"
                    
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    
                    retries = 3
                    for attempt in range(retries):
                        try:
                            req = urllib.request.Request(
                                file_url, 
                                headers={'User-Agent': 'AstroUpdater/1.5', 'Cache-Control': 'no-cache, no-store, must-revalidate'}
                            )
                            with urllib.request.urlopen(req, timeout=15) as response, open(part_path, 'wb') as out_file:
                                out_file.write(response.read())
                            
                            if os.path.exists(target_path):
                                os.remove(target_path)
                            os.rename(part_path, target_path)
                            print(f"[DEBUG] Downloaded: {rel_path} -> {target_path}")
                            break
                        except Exception as e:
                            if os.path.exists(part_path):
                                os.remove(part_path)
                            if attempt == retries - 1:
                                raise e 
                            time.sleep(1)
                    
                    dl_count += 1
                    self.progress.emit(60 + int((dl_count / len(files_to_download)) * 35), f"Downloaded {dl_count}/{len(files_to_download)}...")
            
            manifest_cache_path = os.path.join(update_cache_dir, MANIFEST_FILENAME)
            with open(manifest_cache_path, 'w') as f:
                json.dump(remote_manifest, f, indent=4)
                
            self.progress.emit(100, "Update processing complete.")
            self.finished.emit(True, files_to_update, files_to_delete, f"Ready to install v{remote_version}.")
            
        except URLError as e:
            err_msg = str(e.reason) if hasattr(e, 'reason') else str(e)
            self.finished.emit(False, {}, [], f"Network error: {err_msg}")
        except Exception as e:
            self.finished.emit(False, {}, [], f"Update check failed: {str(e)}")

def setup_ui(app, layout):
    app.pending_update_files_to_delete = None
    
    # --- Load Updater Configurations ---
    config_path = os.path.join(get_base_dir(), "updater_config.json")
    auto_update_enabled = False
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                cfg = json.load(f)
                auto_update_enabled = cfg.get("auto_update", True)
        except Exception:
            pass
            
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
    btn_check.setFixedHeight(28)
    btn_check.setStyleSheet("""
        QPushButton {
            font-size: 13px; 
            font-weight: bold; 
            color: #1E8449; 
            background-color: #E8F8F5; 
            border: 1px solid #A2D9CE; 
            border-radius: 4px;
            padding: 0px 10px;
        }
        QPushButton:hover {
            background-color: #D1F2EB;
            border-color: #1E8449;
        }
        QPushButton:pressed {
            background-color: #A9DFBF;
            border-style: inset;
        }
    """)
    
    btn_full = QPushButton("UPDATE FULL")
    btn_full.setFixedHeight(28)
    btn_full.setStyleSheet("""
        QPushButton {
            font-size: 13px; 
            font-weight: bold; 
            color: #C0392B; 
            background-color: #FDEDEC; 
            border: 1px solid #F5B7B1; 
            border-radius: 4px;
            padding: 0px 10px;
        }
        QPushButton:hover {
            background-color: #FADBD8;
            border-color: #C0392B;
        }
        QPushButton:pressed {
            background-color: #F5B7B1;
            border-style: inset;
        }
    """)
    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(6)
    btn_layout.addWidget(btn_check)
    btn_layout.addWidget(btn_full)
    
    cb_auto_update = QCheckBox("Check for updates automatically on startup")
    cb_auto_update.setChecked(auto_update_enabled)
    cb_auto_update.setStyleSheet("font-size: 11px; color: #555;")
    
    def on_auto_update_toggled(checked):
        try:
            with open(config_path, 'w') as f:
                json.dump({"auto_update": checked}, f)
        except Exception:
            pass
            
    cb_auto_update.toggled.connect(on_auto_update_toggled)
    
    v_layout.addWidget(status_label)
    v_layout.addWidget(progress_bar)
    v_layout.addLayout(btn_layout)
    v_layout.addWidget(cb_auto_update)
    group.setLayout(v_layout)
    layout.addWidget(group)
    
    app.updater_worker = None
    
    def on_progress(val, msg):
        try:
            progress_bar.setValue(val)
            status_label.setText(msg)
        except RuntimeError:
            pass 

    def on_check_clicked(is_full=False, is_auto=False):
        if is_full:
            reply = QMessageBox.question(
                app, "Full Update Warning", 
                "This will redownload the ENTIRE application and wipe all local application files to give you a clean slate.\n\n(Your saves and settings will remain safe).\n\nContinue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return

        try:
            btn_check.setEnabled(False)
            btn_full.setEnabled(False)
            progress_bar.setVisible(True)
            progress_bar.setValue(0)
            if is_auto:
                status_label.setText("Checking for updates in background...")
        except RuntimeError:
            return
        
        app.updater_worker = UpdateWorker(full_update=is_full)
        app.updater_worker.progress.connect(on_progress)
        app.updater_worker.finished.connect(on_update_finished)
        app.updater_worker.start()

    def on_update_finished(success, files_to_update, files_to_delete, msg):
        try:
            btn_check.setEnabled(True)
            btn_full.setEnabled(True)
            progress_bar.setVisible(False)
            status_label.setText(msg)
        except RuntimeError:
            return 
        
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
                return
            
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
            
            # Using /h (hidden) and /r (read-only) overrides file permissions preventing updates
            bat_content = f"""@echo off
timeout /t 2 /nobreak > NUL
{deletion_commands_bat}xcopy /s /y /q /h /r "{cache_dir}\\*" "{base_dir}\\"
rmdir /s /q "{cache_dir}"
{launch_str}del "%~f0"
"""
            with open(bat_path, "w") as f:
                f.write(bat_content)
                
            subprocess.Popen(bat_path, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit(0)
            
        else:
            sh_path = os.path.join(base_dir, "apply_update.sh")
            launch_cmd = f'"{sys.executable}" "{exe_name}"' if not is_frozen else f'./"{exe_name}"'
            launch_str = f"{launch_cmd} &\n" if relaunch else ""
            
            sh_content = f"""#!/bin/bash
sleep 2
{deletion_commands_sh}cp -fR "{cache_dir}/"* "{base_dir}/"
rm -rf "{cache_dir}"
{launch_str}rm -- "$0"
"""
            with open(sh_path, "w") as f:
                f.write(sh_content)
            os.chmod(sh_path, 0o755)
            subprocess.Popen([sh_path], start_new_session=True)
            sys.exit(0)
            
    app._apply_update_func = apply_update_and_restart

    def on_app_quit():
        if getattr(app, 'pending_update_files_to_delete', None) is not None:
            app._apply_update_func(app.pending_update_files_to_delete, relaunch=False)

    q_app = QApplication.instance()
    if not hasattr(app, '_updater_quit_connected'):
        q_app.aboutToQuit.connect(on_app_quit)
        app._updater_quit_connected = True

    btn_check.clicked.connect(lambda: on_check_clicked(is_full=False))
    btn_full.clicked.connect(lambda: on_check_clicked(is_full=True))

    if auto_update_enabled and not getattr(app, '_has_auto_checked_updates', False):
        app._has_auto_checked_updates = False
        QTimer.singleShot(1000, lambda: on_check_clicked(is_full=False, is_auto=False))