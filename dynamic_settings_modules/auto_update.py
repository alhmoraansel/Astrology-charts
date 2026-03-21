import os
import sys
import json
import urllib.request
import tempfile
import subprocess
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# =========================================================
# CONFIGURATION - UPDATE THESE FOR YOUR APP
# =========================================================
CURRENT_VERSION = "1.0.0"
# URL to a JSON file on your server/GitHub containing update info.
# Example JSON: {"latest_version": "1.0.1", "download_url": "https://example.com/AstroApp_Setup_1.0.1.exe", "release_notes": "Bug fixes."}
UPDATE_CHECK_URL = "https://raw.githubusercontent.com/YourUser/YourRepo/main/update_info.json" 

class UpdateCheckerThread(QThread):
    result_ready = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def run(self):
        try:
            req = urllib.request.Request(UPDATE_CHECK_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                self.result_ready.emit(data)
        except Exception as e:
            self.error_occurred.emit(str(e))

class DownloadUpdateThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            req = urllib.request.Request(self.url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                total_size = int(response.info().get('Content-Length', -1))
                
                # Save to user's temporary directory
                tmp_dir = tempfile.gettempdir()
                installer_path = os.path.join(tmp_dir, "AstroApp_Update_Setup.exe")
                
                with open(installer_path, 'wb') as f:
                    downloaded = 0
                    block_size = 8192
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        f.write(buffer)
                        downloaded += len(buffer)
                        if total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            self.progress.emit(percent)
                            
                self.finished.emit(installer_path)
        except Exception as e:
            self.error.emit(str(e))


class UpdaterWidget(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.latest_info = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        info_layout = QHBoxLayout()
        self.lbl_status = QLabel(f"Current Version: {CURRENT_VERSION}")
        self.lbl_status.setStyleSheet("color: #555; font-size: 12px;")
        
        self.btn_check = QPushButton("Check for Updates")
        self.btn_check.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
        self.btn_check.clicked.connect(self.check_for_updates)

        info_layout.addWidget(self.lbl_status)
        info_layout.addStretch()
        info_layout.addWidget(self.btn_check)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)

        layout.addLayout(info_layout)
        layout.addWidget(self.progress_bar)

    def check_for_updates(self):
        self.btn_check.setEnabled(False)
        self.lbl_status.setText("Checking for updates...")
        
        self.checker_thread = UpdateCheckerThread()
        self.checker_thread.result_ready.connect(self.on_check_finished)
        self.checker_thread.error_occurred.connect(self.on_check_error)
        self.checker_thread.start()

    def on_check_error(self, err):
        self.lbl_status.setText("Update check failed.")
        QMessageBox.warning(self, "Update Error", f"Could not check for updates:\n{err}")
        self.btn_check.setEnabled(True)

    def on_check_finished(self, data):
        self.btn_check.setEnabled(True)
        latest_version = data.get("latest_version")
        
        if latest_version and latest_version != CURRENT_VERSION:
            self.lbl_status.setText(f"New version {latest_version} available!")
            self.latest_info = data
            
            # Change button to Download mode
            self.btn_check.setText("Download & Install Update")
            self.btn_check.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
            self.btn_check.clicked.disconnect()
            self.btn_check.clicked.connect(self.download_and_install)
        else:
            self.lbl_status.setText("You are on the latest version.")

    def download_and_install(self):
        download_url = self.latest_info.get("download_url")
        if not download_url: return

        self.btn_check.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("Downloading installer...")

        self.download_thread = DownloadUpdateThread(download_url)
        self.download_thread.progress.connect(self.progress_bar.setValue)
        self.download_thread.finished.connect(self.on_download_finished)
        self.download_thread.error.connect(self.on_download_error)
        self.download_thread.start()

    def on_download_error(self, err):
        self.progress_bar.setVisible(False)
        self.lbl_status.setText("Download failed.")
        QMessageBox.critical(self, "Download Error", f"Failed to download update:\n{err}")
        self.btn_check.setEnabled(True)

    def on_download_finished(self, installer_path):
        self.progress_bar.setValue(100)
        self.lbl_status.setText("Launching installer...")
        
        reply = QMessageBox.question(self, "Update Ready", 
                                     "The update has been downloaded. The application will now close to install the update.\n\nContinue?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Launch the Inno Setup installer. 
                # Use "/SILENT" or "/VERYSILENT" if you want it to install in the background without UI.
                subprocess.Popen([installer_path, "/SILENT"])
                
                # Immediately quit the PyQt application to release file locks
                self.parent_app.close()
                sys.exit(0)
            except Exception as e:
                QMessageBox.critical(self, "Launch Error", f"Failed to launch installer:\n{e}")
        else:
            self.btn_check.setEnabled(True)
            self.lbl_status.setText("Update cancelled.")
            self.progress_bar.setVisible(False)


# Required entry point for your dynamic_settings_modules architecture
def setup_ui(app, layout):
    updater_widget = UpdaterWidget(app)
    layout.addWidget(updater_widget)