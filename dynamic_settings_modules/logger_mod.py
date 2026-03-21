# dynamic_settings_modules/logger_mod.py
import sys, traceback
from PyQt6.QtWidgets import QPushButton, QDialog, QVBoxLayout, QTextBrowser, QLabel

class AstroLogger:
    def __init__(self):
        self.logs = []
        self.orig_stdout = sys.stdout
        self.orig_stderr = sys.stderr
        
    def write(self, text):
        if text.strip():
            self.logs.append(text)
            if len(self.logs) > 1000: 
                self.logs.pop(0)
        self.orig_stdout.write(text)
        
    def flush(self):
        self.orig_stdout.flush()

# Hook the system streams safely to avoid recursive reloading
if getattr(sys, '_astro_logger', None) is None:
    sys._astro_logger = AstroLogger()
    sys.stdout = sys._astro_logger
    sys.stderr = sys._astro_logger

def setup_ui(app, layout):
    lbl = QLabel("Logs & Errors")
    lbl.setStyleSheet("font-weight: bold; color: #d35400; margin-top: 10px;")
    
    btn = QPushButton("View System Logs")
    btn.setStyleSheet("background-color: #2c3e50; color: white; font-weight: bold;")
    
    def open_logs():
        dlg = QDialog(app)
        dlg.setWindowTitle("Live Event & Error Logs")
        dlg.resize(650, 450)
        l = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 13px;")
        
        log_text = "".join(sys._astro_logger.logs) if sys._astro_logger.logs else "No background errors detected."
        tb.setPlainText(log_text)
        
        # Scroll to bottom
        scrollbar = tb.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        l.addWidget(tb)
        dlg.exec()
        
    btn.clicked.connect(open_logs)
    layout.addWidget(lbl)
    layout.addWidget(btn)