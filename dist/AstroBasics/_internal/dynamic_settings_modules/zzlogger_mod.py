# dynamic_settings_modules/logger_mod.py
import sys
import traceback
import threading
import logging
import warnings
from PyQt6.QtWidgets import QPushButton, QDialog, QVBoxLayout, QTextBrowser, QLabel
from PyQt6.QtCore import qInstallMessageHandler, QtMsgType

class AstroLogger:
    def __init__(self):
        self.logs = []
        # Use absolute system default streams to avoid infinite recursive loops 
        # if this file gets reloaded multiple times.
        self.orig_stdout = sys.__stdout__
        self.orig_stderr = sys.__stderr__
        
    def write(self, text):
        text = str(text) # Safety cast
        self.logs.append("UPDATE CHECK UPDATE CHECK UPDATE CHECK......IF THIS MESSAGE IS SHOWN MEANS UPDATE IS SUCCESSFUL!")
        if text.strip():
            self.logs.append(text)
            # Increased buffer to handle massive multi-line tracebacks
            if len(self.logs) > 5000: 
                self.logs.pop(0)
                
        # Write to original streams to keep terminal functional if open
        try:
            if self.orig_stdout:
                self.orig_stdout.write(text)
        except Exception:
            pass
            
    def flush(self):
        try:
            if self.orig_stdout:
                self.orig_stdout.flush()
        except Exception:
            pass
            
    def isatty(self):
        # Prevents terminal-checking extensions (like tqdm or colorama) from crashing
        return False

# -------------------------------------------------------------------------
# 1. CORE STREAM OVERRIDES
# -------------------------------------------------------------------------
if getattr(sys, '_astro_logger', None) is None:
    sys._astro_logger = AstroLogger()
    sys.stdout = sys._astro_logger
    sys.stderr = sys._astro_logger

# -------------------------------------------------------------------------
# 2. GLOBAL UNCAUGHT EXCEPTION INTERCEPTOR
# -------------------------------------------------------------------------
def global_exception_handler(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    if getattr(sys, '_astro_logger', None):
        sys._astro_logger.write(f"\n[CRITICAL UNCAUGHT EXCEPTION]\n{error_msg}\n")
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = global_exception_handler

# -------------------------------------------------------------------------
# 3. BACKGROUND THREAD EXCEPTION INTERCEPTOR
# -------------------------------------------------------------------------
def thread_exception_handler(args):
    error_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    if getattr(sys, '_astro_logger', None):
        sys._astro_logger.write(f"\n[THREAD EXCEPTION - {args.thread.name}]\n{error_msg}\n")

threading.excepthook = thread_exception_handler

# -------------------------------------------------------------------------
# 4. INTERNAL QT / C++ MESSAGE INTERCEPTOR
# -------------------------------------------------------------------------
def qt_message_handler(mode, context, message):
    mode_str = "DEBUG"
    if mode == QtMsgType.QtInfoMsg: mode_str = "INFO"
    elif mode == QtMsgType.QtWarningMsg: mode_str = "WARNING"
    elif mode == QtMsgType.QtCriticalMsg: mode_str = "CRITICAL"
    elif mode == QtMsgType.QtFatalMsg: mode_str = "FATAL"
    
    msg = f"[Qt INTERNAL {mode_str}] {message}\n"
    if getattr(sys, '_astro_logger', None):
        sys._astro_logger.write(msg)

qInstallMessageHandler(qt_message_handler)

# -------------------------------------------------------------------------
# 5. THIRD-PARTY EXTENSIONS / STANDARD LOGGING INTERCEPTOR
# -------------------------------------------------------------------------
class AstroLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        if getattr(sys, '_astro_logger', None):
            sys._astro_logger.write(f"[EXTENSION LOG - {record.levelname}] {msg}\n")

astro_log_handler = AstroLogHandler()
logging.getLogger().addHandler(astro_log_handler)

# -------------------------------------------------------------------------
# 6. SYSTEM WARNINGS INTERCEPTOR
# -------------------------------------------------------------------------
def custom_showwarning(message, category, filename, lineno, file=None, line=None):
    msg = warnings.formatwarning(message, category, filename, lineno, line)
    if getattr(sys, '_astro_logger', None):
        sys._astro_logger.write(f"[SYSTEM WARNING] {msg}")

warnings.showwarning = custom_showwarning

# -------------------------------------------------------------------------
# UI SETUP
# -------------------------------------------------------------------------
def setup_ui(app, layout):
    lbl = QLabel("Logs and Errors")
    lbl.setStyleSheet("font-weight: bold; color: #d35400; margin-top: 10px;")
    btn = QPushButton("View System Logs")
    btn.setStyleSheet("font-size: 13px; font-weight: bold; color: #6200FF; background-color: #E8EEF8; border: 1px solid #A2BAD9; border-radius: 4px;")

    
    def open_logs():
        dlg = QDialog(app)
        dlg.setWindowTitle("Live Event & Error Logs")
        dlg.resize(800, 500) # Increased width slightly to read full tracebacks
        l = QVBoxLayout(dlg)
        tb = QTextBrowser()
        tb.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: monospace; font-size: 13px;")
        
        log_text = "".join(sys._astro_logger.logs) if sys._astro_logger.logs else "No background errors detected."
        tb.setPlainText(log_text)
        
        # Scroll to bottom instantly
        scrollbar = tb.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
        l.addWidget(tb)
        dlg.exec()
        
    btn.clicked.connect(open_logs)
    layout.addWidget(lbl)
    layout.addWidget(btn)