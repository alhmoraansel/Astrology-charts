# dynamic_settings_modules/zzlogger_mod.py

import sys, traceback, threading, logging, warnings, builtins
from PyQt6.QtWidgets import (QPushButton, QVBoxLayout, QTextBrowser, QWidget, QMainWindow, QApplication)
from PyQt6.QtCore import qInstallMessageHandler, QtMsgType, QObject, pyqtSignal, Qt, QEvent
from PyQt6.QtGui import QFont

import __main__
# Attempt to load SmoothScroller from the main application namespace
SmoothScroller = getattr(__main__, 'SmoothScroller', None)

# -------------------------------------------------------------------------
# 1. CORE LOGGER ENGINE (QObject for thread-safe signals)
# -------------------------------------------------------------------------
class AstroLoggerCore(QObject):
    # Signal: level, html_formatted_message
    new_log = pyqtSignal(str, str) 

    def __init__(self):
        super().__init__()
        self.logs = [] 
        self.orig_stdout = sys.__stdout__
        self.orig_stderr = sys.__stderr__

    def log(self, level, message):
        """Formats and routes the log to both the UI and the original terminal."""
        # Sanitize HTML tags so tracebacks format safely
        safe_msg = str(message).replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
        # Refined Dracula (log-optimized)
        color_map = {
            "DEFAULT":  "#FFDFDF",  "ERROR":    "#FF6E6E",  "CRITICAL": "#FF3B3B",  
            "FATAL":    "#FF2A2A",
            "WARNING":  "#FFB86C",  "INFO":     "#00FFEA",  "DEBUG":    "#FFE552",  
            "SYSTEM":   "#FF00DD",  
        }
        color = color_map.get(level, color_map["DEFAULT"])

        #############################################
        #======================MAIN LOGS=====================#
        
        html_msg = (
            f'<div style="margin-bottom: 0px; line-height: 1.0; '
            f'font-family: \'Cascadia Code\', \'JetBrains Mono\', Consolas, monospace; '
            f'font-size: 20px;">'
            f'<span style="color:{color}; font-weight: 1000; padding-right: 10px;">[{level}]</span>'
            f'<span style="color:{color};">{f"           "}{safe_msg}</span>'
            f'</div>')
        
        self.logs.append(html_msg)
        if len(self.logs) > 5000: # Prevent memory bloat
            self.logs.pop(0)
            
        # Emit safely across threads to the UI
        self.new_log.emit(level, html_msg)
        
        # Write to physical terminal if available
        try:
            if self.orig_stdout:
                self.orig_stdout.write(f"[{level}] {str(message)}\n")
        except Exception:
            pass

    def write(self, text):
        """Intercepts standard print() statements."""
        text = str(text)
        if text.strip():
            # Basic heuristic to colorize raw prints that look like errors
            level = "INFO"
            text_lower = text.lower()
            if "error" in text_lower or "exception" in text_lower or "traceback" in text_lower:
                level = "ERROR"
            self.log(level, text.strip())

    def flush(self):
        try:
            if self.orig_stdout: self.orig_stdout.flush()
        except Exception: pass

    def isatty(self): return False

# -------------------------------------------------------------------------
# 2. INSTANTIATION & OVERRIDES
# -------------------------------------------------------------------------
if getattr(sys, '_astro_logger', None) is None:
    sys._astro_logger = AstroLoggerCore()
    sys.stdout = sys._astro_logger
    sys.stderr = sys._astro_logger

def global_exception_handler(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    sys._astro_logger.log("CRITICAL", f"UNCAUGHT EXCEPTION:<br>{error_msg}")
    sys.__excepthook__(exctype, value, tb)
sys.excepthook = global_exception_handler

def thread_exception_handler(args):
    error_msg = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
    sys._astro_logger.log("ERROR", f"THREAD EXCEPTION [{args.thread.name}]:<br>{error_msg}")
threading.excepthook = thread_exception_handler

def qt_message_handler(mode, context, message):
    level = "DEBUG"
    if mode == QtMsgType.QtInfoMsg: level = "INFO"
    elif mode == QtMsgType.QtWarningMsg: level = "WARNING"
    elif mode in [QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg]: level = "CRITICAL"
    sys._astro_logger.log(level, f"[Qt] {message}")
qInstallMessageHandler(qt_message_handler)

class AstroLogHandler(logging.Handler):
    def emit(self, record):
        sys._astro_logger.log(record.levelname, self.format(record))
if not any(isinstance(h, AstroLogHandler) for h in logging.getLogger().handlers):
    logging.getLogger().addHandler(AstroLogHandler())

def custom_showwarning(message, category, filename, lineno, file=None, line=None):
    msg = warnings.formatwarning(message, category, filename, lineno, line)
    sys._astro_logger.log("WARNING", msg.strip())
warnings.showwarning = custom_showwarning

# -------------------------------------------------------------------------
# 3. GLOBAL HELPER FUNCTIONS INJECTION
# -------------------------------------------------------------------------
def debug_print(*args): sys._astro_logger.log("DEBUG", " ".join(map(str, args)))
def info_print(*args): sys._astro_logger.log("INFO", " ".join(map(str, args)))
def error_print(*args): sys._astro_logger.log("ERROR", " ".join(map(str, args)))

builtins.debug_print = debug_print
builtins.info_print = info_print
builtins.error_print = error_print

# -------------------------------------------------------------------------
# 4. INDEPENDENT LIVE UI WINDOW
# -------------------------------------------------------------------------
class LiveLoggerWindow(QMainWindow):
    logs_read = pyqtSignal() # Emitted when window is viewed

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window) 
        self.setWindowTitle("Logs and Errors")
        self.resize(850,450)
        
        # Neutralized Dracula (less purple fatigue)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1E1F29;
            }
        """)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ------------------------------
        # Console Display
        # ------------------------------
        self.tb = QTextBrowser()
        font = QFont()
        font.setFamilies(["Cascadia Code", "Consolas","Courier New" ])
        font.setPointSize(12)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.tb.setFont(font)

        # High-contrast, log-optimized styling
        self.tb.setStyleSheet("""
            QTextBrowser {
                background-color: #1E1F29;
                color: #E6E6E6;
                border: none;
                padding: 6px;
                selection-background-color: #44475A;
                selection-color: #FFFFFF;
            }

            /* Smooth scrollbar (non-obnoxious) */
            QScrollBar:vertical {
                background: #1E1F29;
                width: 10px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #44475A;
                border-radius: 4px;
                min-height: 24px;
            }

            QScrollBar::handle:vertical:hover {
                background: #6272A4;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        # Behavior tuned for live logs
        self.tb.setReadOnly(True)
        self.tb.setOpenExternalLinks(True)

        # Slight performance + UX upgrades
        self.tb.setUndoRedoEnabled(False)
        
        if SmoothScroller:
            self.scroller = SmoothScroller(self.tb)
            
        layout.addWidget(self.tb)
        
        sys._astro_logger.new_log.connect(self.append_log)
        
        if sys._astro_logger.logs:
            self.tb.setHtml("".join(sys._astro_logger.logs))
            self.scroll_to_bottom()

    def append_log(self, level, html_msg):
        self.tb.append(html_msg)
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        scrollbar = self.tb.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # Window Event Overrides for Read State Tracking
    def showEvent(self, event):
        super().showEvent(event)
        self.logs_read.emit()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            self.logs_read.emit()

# -------------------------------------------------------------------------
# 5. PLUGIN UI INJECTION
# -------------------------------------------------------------------------
def setup_ui(app, layout):
    BTN_STYLE_NORMAL = """
        QPushButton {
            font-size: 13px; font-weight: bold; color: #50FA7B; background-color: #1E1F29; 
            border: 1px solid #50FA7B; border-radius: 4px; padding: 8px 15px;
            font-family: 'Consolas', monospace;
        }
        QPushButton:hover { background-color: #282A36; border-color: #8BE9FD; color: #8BE9FD; }
        QPushButton:pressed { background-color: #44475A; border-style: inset; }
    """
    
    BTN_STYLE_UNREAD = """
        QPushButton {
            font-size: 13px; font-weight: bold; color: #FFB86C; background-color: #1E1F29; 
            border: 1px solid #FFB86C; border-radius: 4px; padding: 8px 15px;
            font-family: 'Consolas', monospace;
        }
        QPushButton:hover { background-color: #282A36; border-color: #FFB86C; color: #FFB86C; }
        QPushButton:pressed { background-color: #44475A; border-style: inset; }
    """

    btn = QPushButton("Logs and Errors")
    btn.setStyleSheet(BTN_STYLE_NORMAL)
    
    if not hasattr(app, '_live_logger_window'):
        app._live_logger_window = None
    if not hasattr(app, '_unread_log_count'):
        app._unread_log_count = 0

    def mark_as_read():
        try:
            # Check if the C++ object still exists before updating
            btn.isEnabled()
        except RuntimeError:
            try:
                if app._live_logger_window:
                    app._live_logger_window.logs_read.disconnect(mark_as_read)
            except Exception:
                pass
            return

        if app._unread_log_count > 0:
            app._unread_log_count = 0
            btn.setText("Logs and Errors")
            btn.setStyleSheet(BTN_STYLE_NORMAL)

    def on_new_log_for_btn(level, html_msg):
        try:
            # Check if underlying C++ widget is deleted (e.g. dynamic UI reload)
            btn.isEnabled()
        except RuntimeError:
            # Button was deleted. Disconnect to prevent further RuntimeErrors and memory leaks
            try:
                sys._astro_logger.new_log.disconnect(on_new_log_for_btn)
            except Exception:
                pass
            return

        win = app._live_logger_window
        # Check if the user is currently looking at the logger window
        is_viewing = win and win.isVisible() and not win.isMinimized() and win.isActiveWindow()
        
        if not is_viewing:
            app._unread_log_count += 1
            btn.setText(f"Logs and Errors ({app._unread_log_count} Unread)")
            btn.setStyleSheet(BTN_STYLE_UNREAD)

    sys._astro_logger.new_log.connect(on_new_log_for_btn)
        
    def open_logs():
        if not app._live_logger_window:
            app._live_logger_window = LiveLoggerWindow(app)
            app._live_logger_window.logs_read.connect(mark_as_read)
        
        app._live_logger_window.showNormal()
        app._live_logger_window.raise_()
        app._live_logger_window.activateWindow()
        mark_as_read()
        
    btn.clicked.connect(open_logs)
    
    # Just the button goes into the layout now
    layout.addWidget(btn)