import sys
import datetime
import json
import os
import math
import pytz
import swisseph as swe
import time
import multiprocessing
import queue
import glob

# Ensure all PyQt6 imports strictly precede custom class definitions to prevent NameError
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QTimeEdit, 
                             QTableWidget, QTableWidgetItem, QCheckBox,
                             QHeaderView, QMessageBox, QGroupBox, QFileDialog,
                             QScrollArea, QGridLayout, QSpinBox, QDialog, QTextBrowser,
                             QDoubleSpinBox)
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygonF, QCursor, QIcon, QPainterPath
from PyQt6.QtCore import Qt, QDate, QTime, QThread, pyqtSignal, QRectF, QPointF, QObject, QTimer, QEvent

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

import save_prefs
import animation
import astro_engine

# ==========================================
# CUSTOM UI WIDGETS
# ==========================================
class NoScrollComboBox(QComboBox):
    """A ComboBox that ignores mouse wheel scrolling to prevent accidental adjustments."""
    def wheelEvent(self, event):
        event.ignore()

class ForecastDialog(QDialog):
    def __init__(self, main_app, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Detailed Predictive Forecast")
        self.resize(850, 800)
        self.main_app = main_app
        
        self.local_tz = pytz.timezone(self.main_app.current_tz)
        self.today_date = datetime.datetime.now(self.local_tz).date()
        self.current_offset = 0 # 0 = Today, -1 = Yesterday, +1 = Tomorrow, etc.
        
        layout = QVBoxLayout(self)
        
        # Setup Navigation
        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton("< Previous Day")
        self.btn_prev.setMinimumHeight(40)
        self.btn_prev.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.lbl_date = QLabel("Date")
        self.lbl_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_date.setStyleSheet("font-weight: bold; font-size: 18px; color: #2c3e50;")
        
        self.btn_next = QPushButton("Next Day >")
        self.btn_next.setMinimumHeight(40)
        self.btn_next.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        self.btn_prev.clicked.connect(self.go_prev)
        self.btn_next.clicked.connect(self.go_next)
        
        nav_layout.addWidget(self.btn_prev)
        nav_layout.addWidget(self.lbl_date, 1)
        nav_layout.addWidget(self.btn_next)
        layout.addLayout(nav_layout)
        
        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet("background-color: #f9f9f9; padding: 10px;")
        layout.addWidget(self.text_browser)
        
        self.update_view()
        
    def go_prev(self):
        self.current_offset -= 1
        self.update_view()
            
    def go_next(self):
        self.current_offset += 1
        self.update_view()
            
    def update_view(self):
        target_date = self.today_date + datetime.timedelta(days=self.current_offset)
        target_str = target_date.strftime("%B %d, %Y")
        
        if self.current_offset == 0: day_lbl = "Today"
        elif self.current_offset == -1: day_lbl = "Yesterday"
        elif self.current_offset == 1: day_lbl = "Tomorrow"
        else: day_lbl = f"{abs(self.current_offset)} Days {'Ahead' if self.current_offset > 0 else 'Back'}"
        
        self.lbl_date.setText(f"{target_str}  —  {day_lbl}")
        self.text_browser.setHtml("<h2 style='text-align:center; color:#555;'>Calculating Deep Analysis...</h2>")
        QApplication.processEvents() # Force UI refresh before heavy calculation
        
        # Calculate on the fly for infinite scrolling
        html_content = self.main_app.get_daily_forecast_html(target_date)
        self.text_browser.setHtml(html_content)

class BroadForecastDialog(QDialog):
    def __init__(self, html_content, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Broad Life Era (MD/AD/PD)")
        self.resize(850, 800)
        layout = QVBoxLayout(self)
        self.text_browser = QTextBrowser()
        self.text_browser.setStyleSheet("background-color: #fcfcfc; padding: 15px; font-size: 14px; line-height: 1.6;")
        self.text_browser.setHtml(html_content)
        layout.addWidget(self.text_browser)

class ChartBuilderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Visual Target Chart Builder")
        self.resize(350, 450)
        layout = QGridLayout(self)

        self.div_cb = NoScrollComboBox()
        self.div_cb.addItems(["D1", "D2", "D4", "D7", "D9", "D10", "D12", "D16", "D20", "D24", "D30", "D60"])
        self.div_cb.setCurrentText("D9")
        layout.addWidget(QLabel("Target Division:"), 0, 0)
        layout.addWidget(self.div_cb, 0, 1)

        zodiacs = ["Any / Ignore", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        self.planet_cbs = {}
        row = 1
        for p in ["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            cb = NoScrollComboBox()
            cb.addItems(zodiacs)
            layout.addWidget(QLabel(f"{p}:"), row, 0)
            layout.addWidget(cb, row, 1)
            self.planet_cbs[p] = cb
            row += 1

        btn_box = QHBoxLayout()
        ok_btn = QPushButton("Create Target Chart")
        ok_btn.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        
        btn_box.addWidget(ok_btn)
        btn_box.addWidget(cancel_btn)
        
        layout.addLayout(btn_box, row, 0, 1, 2)

    def get_chart_data(self):
        target_div = self.div_cb.currentText()
        target_asc = self.planet_cbs["Ascendant"].currentIndex() - 1
        if target_asc < 0: target_asc = None

        target_planets = {}
        for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            idx = self.planet_cbs[p].currentIndex() - 1
            if idx >= 0:
                target_planets[p] = idx

        return target_div, target_asc, target_planets

class CustomLocationDialog(QDialog):
    def __init__(self, lat, lon, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Coordinates")
        self.resize(250, 150)
        layout = QGridLayout(self)
        
        layout.addWidget(QLabel("Latitude:"), 0, 0)
        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(4)
        self.lat_spin.setValue(lat)
        layout.addWidget(self.lat_spin, 0, 1)

        layout.addWidget(QLabel("Longitude:"), 1, 0)
        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0)
        self.lon_spin.setDecimals(4)
        self.lon_spin.setValue(lon)
        layout.addWidget(self.lon_spin, 1, 1)

        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout, 2, 0, 1, 2)

    def get_coordinates(self):
        return self.lat_spin.value(), self.lon_spin.value()

# ==========================================
# 1. LOCATION WORKER
# ==========================================
class LocationWorker(QThread):
    result_ready = pyqtSignal(float, float, str, str)
    error_occurred = pyqtSignal(str)

    def __init__(self, location_name):
        super().__init__()
        self.location_name = location_name

    def run(self):
        try:
            geolocator = Nominatim(user_agent="vedic_astro_app_v1")
            location = geolocator.geocode(self.location_name, timeout=10)
            if location:
                tz_name = TimezoneFinder().timezone_at(lng=location.longitude, lat=location.latitude) or "UTC"
                self.result_ready.emit(location.latitude, location.longitude, tz_name, location.address)
            else: self.error_occurred.emit("Location not found.")
        except Exception as e: self.error_occurred.emit(f"Network Error: {str(e)}")

# ==========================================
# 2. TRANSIT WORKER THREAD
# ==========================================
class TransitWorkerThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    stopped = pyqtSignal()
    progress = pyqtSignal(str) 

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.stop_event = multiprocessing.Event()
        self.result_queue = multiprocessing.Queue()
        self.process = None

    def run(self):
        self.process = multiprocessing.Process(
            target=astro_engine.perform_transit_search,
            args=(self.params, self.result_queue, self.stop_event)
        )
        self.process.start()

        while self.process.is_alive():
            if self.isInterruptionRequested():
                self.stop_event.set()
                self.process.join(timeout=0.5)
                if self.process.is_alive(): self.process.terminate()
                self.stopped.emit()
                return
            try:
                res = self.result_queue.get(timeout=0.1)
                if res["status"] == "success":
                    self.finished.emit(res["result_jd_utc"]); return
                elif res["status"] == "stopped":
                    self.stopped.emit(); return
                elif res["status"] == "not_found":
                    self.finished.emit(None); return
                elif res["status"] == "progress":
                    self.progress.emit(res["date"])
                else:
                    self.error.emit(res.get("message", "Unknown error")); return
            except queue.Empty: continue

        handled = False
        while not self.result_queue.empty():
            try:
                res = self.result_queue.get_nowait()
                if res["status"] == "success":
                    self.finished.emit(res["result_jd_utc"]); handled = True; break
                elif res["status"] == "stopped":
                    self.stopped.emit(); handled = True; break
                elif res["status"] == "not_found":
                    self.finished.emit(None); handled = True; break
                elif res["status"] == "progress":
                    self.progress.emit(res["date"])
                else:
                    self.error.emit(res.get("message", "Unknown error")); handled = True; break
            except queue.Empty: break
        
        if not handled and not self.isInterruptionRequested():
            self.error.emit("Background search terminated unexpectedly.")

    def stop(self): self.requestInterruption()

# ==========================================
# 3. RECTIFICATION WORKER THREAD
# ==========================================
class RectificationWorkerThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params
        self.stop_event = multiprocessing.Event()
        self.result_queue = multiprocessing.Queue()
        self.process = None

    def run(self):
        self.process = multiprocessing.Process(
            target=astro_engine.perform_rectification_search,
            args=(self.params, self.result_queue, self.stop_event)
        )
        self.process.start()

        while self.process.is_alive():
            if self.isInterruptionRequested():
                self.stop_event.set()
                self.process.join(timeout=0.5)
                if self.process.is_alive(): self.process.terminate()
                return
            try:
                res = self.result_queue.get(timeout=0.1)
                if res["status"] in ["success", "not_found", "phase1_failed"]:
                    self.finished.emit(res); return
                elif res["status"] == "progress":
                    self.progress.emit(res["msg"])
                elif res["status"] == "error":
                    self.error.emit(res["message"]); return
            except queue.Empty: continue

    def stop(self): self.requestInterruption()


# ==========================================
# 4. CHART RENDERER (ANIMATION ENGINE)
# ==========================================
class ChartRenderer(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(350, 350)
        self.setMouseTracking(True)
        self.title = "" 
        self.d1_data = None
        
        self.hitboxes, self.house_polys, self.chart_data = [], {}, None
        self.use_symbols, self.show_rahu_ketu, self.highlight_asc_moon = False, True, True
        self.show_aspects, self.show_arrows, self.use_tint, self.use_circular = False, True, True, False
        self.visible_aspect_planets = set()

        self.tooltip_label = QLabel(None)
        self.tooltip_label.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("QLabel { background-color: #FDFDFD; color: #222222; border: 1px solid #BBBBBB; padding: 6px; font-size: 13px; }")
        self.tooltip_label.hide()

        self.unicode_syms = {"Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿", "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋"}
        
        self.bright_colors = {
            "Sun": QColor("#FF8C00"), "Moon": QColor("#00BCD4"), "Mars": QColor("#FF0000"), 
            "Mercury": QColor("#00C853"), "Jupiter": QColor("#FFD700"), "Venus": QColor("#FF1493"), 
            "Saturn": QColor("#0000CD"), "Rahu": QColor("#708090"), "Ketu": QColor("#8B4513"), 
            "Ascendant": QColor("#C0392B")
        }
        self.dark_colors = {
            "Sun": QColor("#CC5500"), "Moon": QColor("#007A8C"), "Mars": QColor("#AA0000"), 
            "Mercury": QColor("#008033"), "Jupiter": QColor("#A68A00"), "Venus": QColor("#B30066"), 
            "Saturn": QColor("#000080"), "Rahu": QColor("#444444"), "Ketu": QColor("#5C3A21"), 
            "Ascendant": QColor("#8B0000")
        }

        self.anim_timer = QTimer(self); self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_duration, self.anim_start_time = 500.0, 0
        self.source_layout, self.target_layout, self.current_layout, self.data_changed_flag = None, None, None, False

    def _get_house_polygon(self, h_num, x, y, w, h):
        p_tl, p_tr, p_bl, p_br = QPointF(x, y), QPointF(x+w, y), QPointF(x, y+h), QPointF(x+w, y+h)
        p_tc, p_bc, p_lc, p_rc = QPointF(x+w/2, y), QPointF(x+w/2, y+h), QPointF(x, y+h/2), QPointF(x+w, y+h/2)
        p_cc = QPointF(x+w/2, y+h/2)
        p_i_tl, p_i_tr = QPointF(x+w/4, y+h/4), QPointF(x+3*w/4, y+h/4)
        p_i_bl, p_i_br = QPointF(x+w/4, y+3*h/4), QPointF(x+3*w/4, y+3*h/4)

        polys = {1: [p_tc, p_i_tr, p_cc, p_i_tl], 2: [p_tl, p_tc, p_i_tl], 3: [p_tl, p_i_tl, p_lc], 4: [p_lc, p_i_tl, p_cc, p_i_bl], 5: [p_lc, p_i_bl, p_bl], 6: [p_i_bl, p_bc, p_bl], 7: [p_cc, p_i_br, p_bc, p_i_bl], 8: [p_bc, p_i_br, p_br], 9: [p_i_br, p_rc, p_br], 10: [p_i_tr, p_rc, p_i_br, p_cc], 11: [p_tr, p_rc, p_i_tr], 12: [p_tc, p_tr, p_i_tr]}
        return QPolygonF(polys[h_num])

    def update_chart(self, data, d1_data=None):
        self.chart_data = data
        self.d1_data = d1_data
        self.data_changed_flag = True
        self.update()
        if self.tooltip_label.isVisible(): self._update_tooltip(self.mapFromGlobal(QCursor.pos()))

    def _on_anim_tick(self):
        t = (time.time() * 1000 - self.anim_start_time) / self.anim_duration
        if t >= 1.0:
            self.anim_timer.stop()
            self.current_layout = self.target_layout
        else: self.current_layout = self._lerp_layout(self.source_layout, self.target_layout, t)
        self.update()
        if self.tooltip_label.isVisible(): self._update_tooltip(self.mapFromGlobal(QCursor.pos()))

    def _lerp_layout(self, src, tgt, t):
        e = (4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2) if getattr(self, "use_circular", False) else t
        cur = {"zodiacs": {}, "planets": {}, "houses": {}, "tints": []}
        
        for k, t_v in tgt["zodiacs"].items():
            s_v = src["zodiacs"].get(k, t_v)
            cur["zodiacs"][k] = {"x": s_v["x"] + (t_v["x"] - s_v["x"]) * e, "y": s_v["y"] + (t_v["y"] - s_v["y"]) * e, "val": t_v["val"]}
        for k, t_v in tgt["houses"].items():
            s_v = src["houses"].get(k, t_v)
            cur["houses"][k] = {"x": s_v["x"] + (t_v["x"] - s_v["x"]) * e, "y": s_v["y"] + (t_v["y"] - s_v["y"]) * e}
        for k, t_v in tgt["planets"].items():
            s_v = src["planets"].get(k, t_v)
            cur["planets"][k] = {"x": s_v["x"] + (t_v["x"] - s_v["x"]) * e, "y": s_v["y"] + (t_v["y"] - s_v["y"]) * e, "str": t_v["str"], "color_dark": t_v["color_dark"], "retro": t_v["retro"], "exalted": t_v["exalted"], "debilitated": t_v["debilitated"], "combust": t_v["combust"], "raw": t_v["raw"]}

        tgt_tints_pool = list(tgt.get("tints", []))
        for s_tint in src.get("tints", []):
            match_idx = next((i for i, t_tint in enumerate(tgt_tints_pool) if s_tint["h2"] == t_tint["h2"] and s_tint["color"].rgb() == t_tint["color"].rgb()), -1)
            if match_idx != -1:
                c = QColor(s_tint["color"])
                tgt_c = tgt_tints_pool[match_idx]["color"]
                c.setAlpha(int(c.alpha() + (tgt_c.alpha() - c.alpha()) * e))
                cur["tints"].append({"h2": s_tint["h2"], "color": c})
                tgt_tints_pool.pop(match_idx)
            else:
                c = QColor(s_tint["color"]); c.setAlpha(int(c.alpha() * (1.0 - e)))
                cur["tints"].append({"h2": s_tint["h2"], "color": c})
                
        for t_tint in tgt_tints_pool:
            c = QColor(t_tint["color"]); c.setAlpha(int(c.alpha() * e))
            cur["tints"].append({"h2": t_tint["h2"], "color": c})
        return cur

    def _compute_layout(self, x, y, w, h):
        layout = {"zodiacs": {}, "planets": {}, "houses": {}, "tints": []}
        if not self.chart_data: return layout

        asc_sign = self.chart_data["ascendant"]["sign_num"]
        asc_sign_idx = self.chart_data["ascendant"]["sign_index"]
        asc_deg_effective = self.chart_data["ascendant"].get("div_lon", self.chart_data["ascendant"]["degree"])

        all_bodies = []
        if self.highlight_asc_moon:
            is_varg = self.chart_data["ascendant"].get("vargottama", False)
            str_val = "Asc★" if is_varg and self.title and "D1" not in self.title else "Asc"
            all_bodies.append({"name": "Ascendant", "str": str_val, "color_dark": self.dark_colors.get("Ascendant", QColor("#000000")), "lon": asc_deg_effective, "retro": False, "exalted": False, "debilitated": False, "combust": False, "raw": {"name": "Ascendant", "sign_index": self.chart_data["ascendant"]["sign_index"], "deg_in_sign": self.chart_data["ascendant"]["degree"] % 30, "retro": False, "combust": False, "house": 1, "vargottama": is_varg}})

        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"] and not self.show_rahu_ketu: continue
            
            base_str = self.unicode_syms[p["name"]] if self.use_symbols else p["sym"]
            is_varg = p.get("vargottama", False)
            str_val = base_str + "★" if is_varg and self.title and "D1" not in self.title else base_str
            p_lon_effective = p.get("div_lon", p["lon"])
            
            all_bodies.append({"name": p["name"], "str": str_val, "color_dark": self.dark_colors.get(p["name"], QColor("#000000")), "lon": p_lon_effective, "retro": p["retro"], "exalted": p.get("exalted", False), "debilitated": p.get("debilitated", False), "combust": p.get("combust", False), "raw": p})

        bodies_by_house = {i: [] for i in range(1, 13)}
        for b in all_bodies: 
            p_sign_idx = b["raw"]["sign_index"]
            h_num = ((p_sign_idx - asc_sign_idx) % 12) + 1
            bodies_by_house[h_num].append(b)

        for h_num in range(1, 13):
            sign_num = (asc_sign_idx + h_num - 1) % 12 + 1
            sign_lon = ((asc_sign_idx + h_num - 1) % 12) * 30.0 + 15.0
            
            has_planets = len(bodies_by_house[h_num]) > 0
            if getattr(self, "use_circular", False):
                zx, zy = animation.get_circular_coords(sign_lon, asc_deg_effective, -3, w, h)
                hx, hy = animation.get_circular_coords(sign_lon, asc_deg_effective, -4, w, h)
            else:
                zx, zy = animation.get_diamond_zodiac_coords(h_num, w, h, has_planets)
                hx, hy = animation.get_diamond_house_center(h_num, w, h)
            layout["zodiacs"][sign_num] = {"x": zx + x, "y": zy + y, "val": str(sign_num)}
            layout["houses"][h_num] = {"x": hx + x, "y": hy + y}

        LANE_ORDER = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4, "Venus": 5, "Saturn": 6, "Rahu": 7, "Ketu": 8, "Ascendant": 9}

        for h_num, bodies in bodies_by_house.items():
            for idx, b in enumerate(bodies):
                if getattr(self, "use_circular", False):
                    px, py = animation.get_circular_coords(b["lon"], asc_deg_effective, LANE_ORDER.get(b["name"], 4.5), w, h)
                else: 
                    px, _ = animation.get_diamond_planet_coords(h_num, idx, len(bodies), w, h)
                    spacing = 0.065 * h 
                    start_y = -((len(bodies) - 1) * spacing) / 2.0
                    hx, hy = animation.get_diamond_house_center(h_num, w, h)
                    py = hy + start_y + (idx * spacing)
                layout["planets"][b["name"]] = {"x": px + x, "y": py + y, "str": b["str"], "color_dark": b["color_dark"], "retro": b["retro"], "exalted": b["exalted"], "debilitated": b["debilitated"], "combust": b["combust"], "raw": b["raw"]}

        if self.show_aspects and self.use_tint and self.chart_data and self.chart_data.get("aspects"):
            for aspect in self.chart_data["aspects"]:
                if aspect["aspecting_planet"] in self.visible_aspect_planets and (aspect["aspecting_planet"] not in ["Rahu", "Ketu"] or self.show_rahu_ketu):
                    c = QColor(self.bright_colors.get(aspect["aspecting_planet"], QColor(200, 200, 200)))
                    c.setAlpha(25)
                    layout["tints"].append({"h2": aspect["target_house"], "color": c})
        return layout

    def paintEvent(self, event):
        self.hitboxes = []
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        
        size = min(self.width(), self.height()) - 50 
        cx, cy = self.width() / 2, self.height() / 2
        x, y, w, h = cx - size / 2, cy - size / 2 + 10, size, size

        if self.title:
            painter.setPen(QColor("#BBBBBB"))
            font_size = min(15, max(10, int(size * 0.035)))
            painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Bold))
            painter.drawText(QRectF(0, 0, self.width(), y - 10), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, self.title)

        self.house_polys.clear()
        for h_num in range(1, 13): self.house_polys[h_num] = self._get_house_polygon(h_num, x, y, w, h)

        new_target_layout = self._compute_layout(x, y, w, h)
        if self.data_changed_flag:
            self.data_changed_flag = False
            if self.current_layout is None: self.source_layout = self.target_layout = self.current_layout = new_target_layout
            else:
                self.source_layout, self.target_layout = self.current_layout, new_target_layout
                self.anim_start_time = time.time() * 1000
                self.anim_timer.start(16)
        else:
            self.target_layout = new_target_layout
            if not self.anim_timer.isActive(): self.source_layout = self.current_layout = new_target_layout

        layout = self.current_layout
        if not layout:
            painter.setPen(QColor("#000000")); painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Chart Data")
            return

        for tint in layout["tints"]:
            painter.setBrush(QBrush(tint["color"])); painter.setPen(Qt.PenStyle.NoPen)
            if getattr(self, "use_circular", False):
                outer_r = (w - 40) / 2.0
                inner_r = w * 0.15
                
                asc_deg_effective = self.chart_data["ascendant"].get("div_lon", self.chart_data["ascendant"]["degree"])
                asc_sign_idx = self.chart_data["ascendant"]["sign_index"]
                
                h_num = tint["h2"]
                sign_lon_start = ((asc_sign_idx + h_num - 1) % 12) * 30.0
                
                delta = (sign_lon_start - asc_deg_effective) % 360.0
                start_angle = 270.0 - delta
                
                path = QPainterPath()
                path.arcMoveTo(QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2), start_angle)
                path.arcTo(QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2), start_angle, -30.0)
                path.arcTo(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2), start_angle - 30.0, 30.0)
                path.closeSubpath()
                painter.drawPath(path)
            else: painter.drawPolygon(self.house_polys[tint["h2"]])

        # ---------- DECORATIVE BORDERS ----------
        painter.setBrush(Qt.BrushStyle.NoBrush)
        chart_cx, chart_cy = x + w / 2, y + h / 2
        if getattr(self, "use_circular", False):
            outer_r = (w - 40) / 2
            painter.setPen(QPen(QColor("#DAA520"), 2))
            painter.drawEllipse(QPointF(chart_cx, chart_cy), outer_r + 4, outer_r + 4)
            painter.setPen(QPen(QColor("#8B4513"), 1.5))
            painter.drawEllipse(QPointF(chart_cx, chart_cy), outer_r + 8, outer_r + 8)
        else:
            painter.setPen(QPen(QColor("#DAA520"), 2))
            painter.drawRect(int(x - 4), int(y - 4), int(w + 8), int(h + 8))
            painter.setPen(QPen(QColor("#8B4513"), 1.5))
            painter.drawRect(int(x - 8), int(y - 8), int(w + 16), int(h + 16))
            painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QBrush(QColor("#8B4513")))
            for px in [x - 8, x + w + 8]:
                for py in [y - 8, y + h + 8]:
                    painter.drawRect(int(px - 2), int(py - 2), 4, 4)

        painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor("#222222"), max(1.0, w*0.005)))
        # ----------------------------------------

        if getattr(self, "use_circular", False):
            inner_r = w * 0.15
            painter.drawEllipse(QRectF(x + 20, y + 20, w - 40, h - 40))
            painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r*2, inner_r*2))
            for i in range(12):
                angle = math.radians(i * 30 + 15)
                painter.drawLine(int(cx + inner_r * math.cos(angle)), int(cy - inner_r * math.sin(angle)), int(cx + ((w - 40) / 2) * math.cos(angle)), int(cy - ((w - 40) / 2) * math.sin(angle)))
        else:
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.drawLine(int(x), int(y), int(x + w), int(y + h)); painter.drawLine(int(x + w), int(y), int(x), int(y + h))
            painter.drawLine(int(x + w/2), int(y), int(x + w), int(y + h/2)); painter.drawLine(int(x + w), int(y + h/2), int(x + w/2), int(y + h))
            painter.drawLine(int(x + w/2), int(y + h), int(x), int(y + h/2)); painter.drawLine(int(x), int(y + h/2), int(x + w/2), int(y))

        for z in layout["zodiacs"].values():
            planet_font_size = min(14, max(9, int(w * 0.035)))
            rashi_font_size = max(5, int(planet_font_size * 0.5))
            painter.setFont(QFont("Arial", rashi_font_size, QFont.Weight.Normal))
            painter.setPen(QColor("#000000"))
            painter.drawText(QRectF(z["x"] - 15, z["y"] - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, z["val"])

        for b in layout["planets"].values():
            if b["raw"].get("is_ak"):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 215, 0, 90)) 
                painter.drawEllipse(QPointF(b["x"], b["y"] - 4), 22, 22)

            painter.setPen(b["color_dark"]); painter.setFont(QFont("Arial", min(14, max(9, int(w * 0.035))), QFont.Weight.Bold))
            p_rect = QRectF(b["x"] - 40, b["y"] - 10, 80, 20)
            painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, b["str"])
            self.hitboxes.append((p_rect, b["raw"]))
            
            fm = painter.fontMetrics()
            text_width = fm.boundingRect(b["str"]).width()
            marker_x = b["x"] + text_width / 2.0 + 1
            t_y = b["y"] 
            
            g_s = min(5.0, max(2.0, w * 0.008)) 
            if b["retro"]:
                painter.setFont(QFont("Arial", min(9, max(6, int(w*0.022))), QFont.Weight.Bold))
                painter.drawText(int(marker_x), int(b["y"] - 3), "R")
                marker_x += painter.fontMetrics().horizontalAdvance("R") + 2
                
            if b["exalted"]:
                painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(0, 180, 0))
                painter.drawPolygon(QPolygonF([QPointF(marker_x, t_y+g_s), QPointF(marker_x+2*g_s, t_y+g_s), QPointF(marker_x+g_s, t_y-1.5*g_s)]))
                marker_x += 2.5*g_s
            elif b["debilitated"]:
                painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(220, 0, 0))
                painter.drawPolygon(QPolygonF([QPointF(marker_x, t_y-g_s), QPointF(marker_x+2*g_s, t_y-g_s), QPointF(marker_x+g_s, t_y+1.5*g_s)]))
                marker_x += 2.5*g_s
                
            if b["combust"]:
                painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(255, 140, 0))
                painter.drawPolygon(QPolygonF([QPointF(marker_x+g_s, t_y-1.5*g_s), QPointF(marker_x+2*g_s, t_y+g_s), QPointF(marker_x+g_s, t_y+2*g_s), QPointF(marker_x, t_y+g_s)]))
                painter.setBrush(QColor(255, 220, 0))
                painter.drawPolygon(QPolygonF([QPointF(marker_x+g_s, t_y-0.5*g_s), QPointF(marker_x+1.5*g_s, t_y+g_s), QPointF(marker_x+g_s, t_y+1.5*g_s), QPointF(marker_x+0.5*g_s, t_y+g_s)]))
            painter.setBrush(Qt.BrushStyle.NoBrush)
                
        if self.show_aspects and self.show_arrows and self.chart_data and self.chart_data.get("aspects"):
            for i, aspect in enumerate(self.chart_data["aspects"]):
                if aspect["aspecting_planet"] in self.visible_aspect_planets and (aspect["aspecting_planet"] not in ["Rahu", "Ketu"] or self.show_rahu_ketu):
                    p_v, h_v = layout["planets"].get(aspect["aspecting_planet"]), layout["houses"].get(aspect["target_house"])
                    if p_v and h_v:
                        c = QColor(self.bright_colors.get(aspect["aspecting_planet"], QColor(100, 100, 100)))
                        c.setAlpha(120)
                        x1, y1, x2, y2 = p_v["x"] + (i % 3 - 1) * 4, p_v["y"] + ((i + 1) % 3 - 1) * 4, h_v["x"] + (i % 3 - 1) * 4, h_v["y"] + ((i + 1) % 3 - 1) * 4
                        dx, dy = x2 - x1, y2 - y1
                        dist = math.hypot(dx, dy)
                        if dist >= 70:
                            sx, sy, ex, ey = x1 + (dx/dist) * 35, y1 + (dy/dist) * 35, x2 - (dx/dist) * 35, y2 - (dy/dist) * 35
                            painter.setPen(QPen(c, max(1.0, w*0.005), Qt.PenStyle.SolidLine)); painter.drawLine(int(sx), int(sy), int(ex), int(ey))
                            angle = math.atan2(ey - sy, ex - sx)
                            painter.setBrush(QBrush(c)); painter.setPen(Qt.PenStyle.NoPen)
                            painter.drawPolygon(QPolygonF([QPointF(ex, ey), QPointF(ex - 9 * math.cos(angle - math.pi / 6), ey - 9 * math.sin(angle - math.pi / 6)), QPointF(ex - 9 * math.cos(angle + math.pi / 6), ey - 9 * math.sin(angle + math.pi / 6))]))

    def mouseMoveEvent(self, event): self._update_tooltip(event.position())

    def _update_tooltip(self, pos):
        if not self.chart_data or not self.current_layout:
            if self.tooltip_label.isVisible(): self.tooltip_label.hide()
            return
            
        tooltip_html, pos_point = "", QPointF(pos.x(), pos.y())
        ordinal = lambda n: str(n) + ('th' if 11 <= (n % 100) <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        context_prefix = ""
        if self.title:
            context_prefix += f"<div style='color:#888; font-size:11px; margin-bottom:4px;'><b>[{self.title}]</b></div>"
            
            if getattr(self, 'd1_data', None) and "D1" not in self.title:
                chart_key = self.title.split()[0]
                div_meanings = {"D9": {"d1_house": 7}, "D10": {"d1_house": 10}, "D20": {"d1_house": 9}, "D30": {"d1_house": 6}, "D60": {"d1_house": 1}}
                if chart_key in div_meanings:
                    meaning = div_meanings[chart_key]
                    d1_h = meaning["d1_house"]
                    d1_asc_idx = self.d1_data["ascendant"]["sign_index"]
                    target_sign = (d1_asc_idx + d1_h - 1) % 12 + 1
                    ruler_map = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}
                    lord_name = ruler_map.get(target_sign)
                    
                    div_lord_p = next((p for p in self.chart_data["planets"] if p["name"] == lord_name), None)
                    if div_lord_p:
                        dig = [d for d, k in zip(["Exalted", "Debilitated", "Own Sign"], ["exalted", "debilitated", "own_sign"]) if div_lord_p.get(k)]
                        dig_str = f" ({', '.join(dig)})" if dig else ""
                        
                        context_prefix += (f"<div style='background-color:#FFF8DC; padding:5px; border:1px solid #EEDD82; border-radius:3px; margin-bottom:8px; font-size:12px; color:#555;'>"
                                           f"<b>D1 {ordinal(d1_h)} lord ({lord_name}) in {chart_key} {ordinal(div_lord_p['house'])} house{dig_str}</b>"
                                           f"</div>")

        for rect, p_raw in self.hitboxes:
            if rect.contains(pos_point):
                name, house = p_raw["name"], p_raw.get("house", "-")
                status_list = ["Retrograde"] if name in ["Rahu", "Ketu"] or (p_raw.get("retro") and name != "Ascendant") else (["Direct"] if name != "Ascendant" else [])
                if p_raw.get("combust"): status_list.append("Combust")
                
                dignity_list = [d for d, k in zip(["Exalted", "Debilitated", "Own Sign"], ["exalted", "debilitated", "own_sign"]) if p_raw.get(k)]
                if p_raw.get("vargottama") and self.title and "D1" not in self.title:
                    dignity_list.append("<span style='color: #d35400;'><b>Vargottama</b></span>")
                
                html = context_prefix
                if p_raw.get("is_ak"): html += f"<span style='color: #B8860B;'><b>★ Brightest Star / Atmakaraka</b></span><br>"
                
                lords = p_raw.get("lord_of", [])
                lord_str = ""
                if lords:
                    preferred_houses = {1, 2, 4, 5, 7, 9, 10, 11}
                    lord_texts = []
                    for l in lords:
                        l_ord = ordinal(l)
                        if l in preferred_houses:
                            lord_texts.append(f"<span style='color: #27ae60;'><b>{l_ord}</b></span>")
                        else:
                            lord_texts.append(f"<span style='color: #c0392b;'>{l_ord}</span>")
                    lord_str = f" &nbsp;&mdash;&nbsp; {' & '.join(lord_texts)} House Lord"

                html += f"<b>{name}</b>{lord_str}<hr style='margin: 4px 0;'/>Sign: {zodiac_names[p_raw['sign_index']]}<br>"
                if house != "-": html += f"House: {house}<br>"
                if status_list: html += f"Status: {', '.join(status_list)}<br>"
                if dignity_list: html += f"Dignity: {', '.join(dignity_list)}<br>"
                if p_raw.get("nakshatra"): html += f"Nakshatra: {p_raw['nakshatra']} (Swami: {p_raw['nakshatra_lord']})<br>"
                tooltip_html = html + f"Base Longitude: {int(p_raw['deg_in_sign'])}°{int((p_raw['deg_in_sign'] - int(p_raw['deg_in_sign'])) * 60):02d}'"
                break
                
        if not tooltip_html:
            size = min(self.width(), self.height()) - 50
            x, y, w, h = self.width() / 2 - size / 2, self.height() / 2 - size / 2 + 10, size, size
            for h_num in range(1, 13):
                is_hovered = False
                if getattr(self, "use_circular", False):
                    dx, dy = pos.x() - (x + w/2), pos.y() - (y + h/2)
                    if (w * 0.15) <= math.hypot(dx, dy) <= ((w - 40) / 2):
                        if abs((math.degrees(math.atan2(-dy, dx)) % 360 - ((90 + (h_num - 1) * 30) % 360) + 180) % 360 - 180) <= 15: is_hovered = True
                elif h_num in self.house_polys and self.house_polys[h_num].containsPoint(pos_point, Qt.FillRule.OddEvenFill): is_hovered = True

                if is_hovered:
                    sign_in_house = (self.chart_data["ascendant"]["sign_index"] + h_num - 1) % 12 + 1
                    html = context_prefix + f"<b>{ordinal(h_num)} House</b>" + (" <b style='color: red;'>NOT preferred</b>" if sign_in_house in {10, 12, 8, 2, 3} else "") + "<hr style='margin: 4px 0;'/>"
                    lord_name = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}.get(sign_in_house)
                    lord_p = next((p for p in self.chart_data["planets"] if p["name"] == lord_name), None)
                    if lord_p:
                        l_status = [s for s, k in zip(["combust", "retrograde", "exalted", "debilitated"], ["combust", "retro", "exalted", "debilitated"]) if lord_p.get(k) and (k != "retro" or lord_name not in ["Rahu", "Ketu"])]
                        varg_tag = " (Vargottama)" if lord_p.get("vargottama") and self.title and "D1" not in self.title else ""
                        html += f"=&gt; lord ({lord_name}{varg_tag}{', ' + ', '.join(l_status) if l_status else ''}) in {ordinal(lord_p['house'])} house"

                    aspects = [a["aspecting_planet"] for a in self.chart_data.get("aspects", []) if a["target_house"] == h_num]
                    if aspects:
                        html += f"<br><br>Aspected by:<br><br>"
                        blocks = []
                        for ap_name in aspects:
                            ap_p = next((p for p in self.chart_data["planets"] if p["name"] == ap_name), None)
                            if ap_p:
                                ap_st = [s for s, k in zip(["Combust", "Retrograde", "Retrograde", "Exalted", "Debilitated", "Own Sign"], ["combust", "retro", "r_k", "exalted", "debilitated", "own_sign"]) if (ap_p.get(k) and ap_name not in ["Rahu", "Ketu"]) or (k == "r_k" and ap_name in ["Rahu", "Ketu"])]
                                varg_tag2 = " (Vargottama)" if ap_p.get("vargottama") and self.title and "D1" not in self.title else ""
                                block = f"-&gt; <b>{ap_name}</b>{varg_tag2}" + (f" ({', '.join(ap_st)})" if ap_st else "")
                                lords = ap_p.get("lord_of", [])
                                if lords: block += f"<br><span style='color: #555;'>{' AND '.join([f'{ordinal(l)} house lord' for l in lords])}</span>"
                                blocks.append(block)
                        html += "<br><br>".join(blocks)
                    tooltip_html = html; break
                
        if tooltip_html:
            if self.tooltip_label.text() != tooltip_html: self.tooltip_label.setText(tooltip_html); self.tooltip_label.adjustSize()
            screen, global_pos = self.screen().availableGeometry() if self.screen() else QApplication.primaryScreen().availableGeometry(), self.mapToGlobal(pos.toPoint() if hasattr(pos, 'toPoint') else pos)
            l_w, l_h, t_x, t_y = self.tooltip_label.width(), self.tooltip_label.height(), global_pos.x() + 15, global_pos.y() + 15
            if t_x + l_w > screen.right(): t_x = global_pos.x() - l_w - 5
            if t_y + l_h > screen.bottom(): t_y = global_pos.y() - l_h - 5
            self.tooltip_label.move(t_x, t_y)
            if not self.tooltip_label.isVisible(): self.tooltip_label.show()
        else:
            if self.tooltip_label.isVisible(): self.tooltip_label.hide()

    def leaveEvent(self, event):
        if hasattr(self, 'tooltip_label') and self.tooltip_label.isVisible(): self.tooltip_label.hide()
        super().leaveEvent(event)


# ==========================================
# 4. MAIN APPLICATION GUI
# ==========================================
class AstroApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vedic Astrology Diamond Chart Pro - Divisional System")
        self.resize(1300, 800)

        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))

        self.current_file_path = None
        self.last_load_dir = os.path.join(os.getcwd(), "saves")
        self.update_window_title()

        self.ephemeris = astro_engine.EphemerisEngine()
        self.time_ctrl = animation.TimeController()
        
        self.current_lat, self.current_lon, self.current_tz = 28.6139, 77.2090, "Asia/Kolkata"
        self.is_updating_ui = False
        self.is_loading_settings = True 
        self.is_chart_saved = True
        self.frozen_planets = {}
        
        self.renderers = {}
        self.div_titles = {
            "D1": "D1 (Rashi)", "D2": "D2 (Hora)", "D4": "D4 (Chaturthamsha)", "D7": "D7 (Saptamsha)",
            "D9": "D9 (Navamsha)", "D10": "D10 (Dashamsha)", "D12": "D12 (Dwadashamsha)", 
            "D16": "D16 (Shodashamsha)", "D20": "D20 (Vimshamsha)", "D24": "D24 (Chaturvimshamsha)",
            "D30": "D30 (Trimshamsha)", "D60": "D60 (Shashtiamsha)"
        }
        
        self.current_base_chart = None

        self._init_ui()
        self._connect_signals()
        self.load_settings()
        self.is_loading_settings = False
        
        now = datetime.datetime.now()
        self.time_ctrl.set_time({'year': now.year, 'month': now.month, 'day': now.day, 'hour': now.hour, 'minute': now.minute, 'second': now.second})

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(60000)
        self.autosave_timer.timeout.connect(self.do_autosave)
        self.autosave_timer.start()

    def load_settings(self):
        settings_file = "astro_settings.json"
        if not os.path.exists(settings_file): 
            self.update_grid_layout()
            return
        try:
            with open(settings_file, "r") as f: prefs = json.load(f)
            if "location" in prefs: self.loc_input.setText(prefs["location"])
            if "lat" in prefs: self.current_lat = prefs["lat"]
            if "lon" in prefs: self.current_lon = prefs["lon"]
            if "tz" in prefs: self.current_tz = prefs["tz"]
            self.loc_status.setText(f"Lat: {self.current_lat:.4f}, Lon: {self.current_lon:.4f} | {self.current_tz}")

            if "ayanamsa" in prefs: self.cb_ayanamsa.setCurrentText(prefs["ayanamsa"])
            if "use_symbols" in prefs: self.chk_symbols.setChecked(prefs["use_symbols"])
            if "show_rahu_ketu" in prefs: self.chk_rahu.setChecked(prefs["show_rahu_ketu"])
            if "show_arrows" in prefs: self.chk_arrows.setChecked(prefs["show_arrows"])
            if "use_tint" in prefs: self.chk_tint.setChecked(prefs["use_tint"])
            if "show_aspects" in prefs: self.chk_aspects.setChecked(prefs["show_aspects"])
            if "show_details" in prefs: self.chk_details.setChecked(prefs["show_details"])
            if "use_circular" in prefs: self.chk_circular.setChecked(prefs["use_circular"])
            if "aspect_planets" in prefs:
                for p, is_checked in prefs["aspect_planets"].items():
                    if p in self.aspect_cb: self.aspect_cb[p].setChecked(is_checked)
            
            if "div_charts" in prefs:
                self.is_updating_ui = True
                for k, is_checked in prefs["div_charts"].items():
                    if k in self.div_cbs: self.div_cbs[k].setChecked(is_checked)
                self.is_updating_ui = False
                
            self.update_grid_layout()
            self.update_settings()
            self.toggle_details()
        except Exception as e: print(f"Failed to load settings: {e}")

    def save_settings(self):
        if getattr(self, 'is_loading_settings', True): return
        prefs = {"location": self.loc_input.text(), "lat": self.current_lat, "lon": self.current_lon, "tz": self.current_tz,
                 "ayanamsa": self.cb_ayanamsa.currentText(), "use_symbols": self.chk_symbols.isChecked(),
                 "show_rahu_ketu": self.chk_rahu.isChecked(), "show_arrows": self.chk_arrows.isChecked(),
                 "use_tint": self.chk_tint.isChecked(), "show_aspects": self.chk_aspects.isChecked(),
                 "show_details": self.chk_details.isChecked(), "use_circular": self.chk_circular.isChecked(),
                 "aspect_planets": {p: cb.isChecked() for p, cb in self.aspect_cb.items()},
                 "div_charts": {k: v.isChecked() for k, v in self.div_cbs.items()} if hasattr(self, 'div_cbs') else {}}
        try:
            with open("astro_settings.json", "w") as f: json.dump(prefs, f, indent=4)
        except Exception as e: print(f"Failed to save settings: {e}")

    def do_autosave(self):
        if not getattr(self, "is_chart_saved", True):
            current_state = self.get_current_chart_info()
            if not hasattr(self, "last_autosaved_state") or self.last_autosaved_state != current_state:
                os.makedirs("autosave", exist_ok=True)
                existing = glob.glob(os.path.join("autosave", "tmp_*_saveon_*.json"))
                num = len(existing) + 1
                filename = os.path.join("autosave", f"tmp_{num:03d}_saveon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                save_prefs.save_chart_to_file(filename, current_state)
                self.last_autosaved_state = current_state

    def update_window_title(self):
        base_title = "Vedic Astrology Diamond Chart Pro - Divisional System"
        if self.current_file_path:
            filename = os.path.basename(self.current_file_path)
            self.setWindowTitle(f"{filename} - {base_title}")
        else:
            self.setWindowTitle(base_title)

    def _init_ui(self):
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Orientation.Horizontal); main_layout.addWidget(main_splitter)

        # Increased minimum width to ensure controls are fully visible without squishing
        left_scroll = QScrollArea(); left_scroll.setWidgetResizable(True); left_scroll.setMinimumWidth(420)
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 4, 4, 4); left_layout.setSpacing(4)

        loc_group = QGroupBox("Location Settings"); loc_layout = QVBoxLayout(); loc_layout.setContentsMargins(4, 4, 4, 4)
        search_layout = QHBoxLayout()
        self.loc_input, self.loc_btn = QLineEdit("New Delhi"), QPushButton("Search")
        
        self.btn_custom_loc = QPushButton("...")
        self.btn_custom_loc.setFixedSize(30, 25)
        self.btn_custom_loc.setStyleSheet("border-radius: 12px; font-weight: bold; background-color: #DAA520; color: white;")
        self.btn_custom_loc.setToolTip("Enter Custom Coordinates")
        
        search_layout.addWidget(self.loc_input)
        search_layout.addWidget(self.loc_btn)
        search_layout.addWidget(self.btn_custom_loc)
        
        self.loc_status = QLabel("Lat: 28.61, Lon: 77.21 | TZ: Asia/Kolkata")
        loc_layout.addLayout(search_layout); loc_layout.addWidget(self.loc_status); loc_group.setLayout(loc_layout)

        dt_group = QGroupBox("Date & Time"); dt_layout = QVBoxLayout(); dt_layout.setContentsMargins(4, 4, 4, 4)
        date_layout = QHBoxLayout()
        self.year_spin, self.month_spin, self.day_spin = QSpinBox(), QSpinBox(), QSpinBox()
        
        # INCREASED BOUNDARIES (Safely Allows +/- 1 Million Years)
        self.year_spin.setRange(-999999, 999999) 
        self.month_spin.setRange(1, 12); self.day_spin.setRange(1, 31)
        
        date_layout.addWidget(QLabel("Y:")); date_layout.addWidget(self.year_spin)
        date_layout.addWidget(QLabel("M:")); date_layout.addWidget(self.month_spin)
        date_layout.addWidget(QLabel("D:")); date_layout.addWidget(self.day_spin)

        self.btn_panchang = QPushButton("...")
        self.btn_panchang.setFixedSize(30, 25)
        self.btn_panchang.setStyleSheet("border-radius: 12px; font-weight: bold; background-color: #DAA520; color: white;")
        self.btn_panchang.setToolTip("Show Panchang Info")
        date_layout.addWidget(self.btn_panchang)

        time_layout = QHBoxLayout()
        self.time_edit = QTimeEdit(); self.time_edit.setDisplayFormat("HH:mm:ss")
        time_layout.addWidget(QLabel("T:")); time_layout.addWidget(self.time_edit)
        
        self.dasha_label = QLabel("Now: -")
        self.dasha_label.setStyleSheet("color: #8B4513; font-weight: bold; font-size: 11px; margin-top: 4px;")
        
        self.btn_today_forecast = QPushButton("Today's Forecast")
        self.btn_today_forecast.setStyleSheet("font-weight: bold; color: #8B4513; height: 30px;")
        self.btn_broad_forecast = QPushButton("Broad Era Forecast")
        self.btn_broad_forecast.setStyleSheet("font-weight: bold; color: #2980b9; height: 30px;")

        fc_layout = QHBoxLayout()
        fc_layout.setContentsMargins(0, 5, 0, 0)
        fc_layout.addWidget(self.btn_today_forecast)
        fc_layout.addWidget(self.btn_broad_forecast)

        dt_layout.addLayout(date_layout); dt_layout.addLayout(time_layout)
        dt_layout.addWidget(self.dasha_label); dt_layout.addLayout(fc_layout)
        dt_group.setLayout(dt_layout)
        
        div_group = QGroupBox("Divisional Charts")
        div_layout = QGridLayout(); div_layout.setContentsMargins(4, 4, 4, 4)
        self.div_cbs = {}
        for i, (d_id, d_name) in enumerate(self.div_titles.items()):
            cb = QCheckBox(f"{d_id}")
            if d_id == "D1": cb.setChecked(True)
            cb.stateChanged.connect(self.update_grid_layout)
            self.div_cbs[d_id] = cb
            div_layout.addWidget(cb, i // 3, i % 3)
        div_group.setLayout(div_layout)

        nav_group = QGroupBox("Animation"); nav_layout = QVBoxLayout(); nav_layout.setContentsMargins(4, 4, 4, 4)
        step_layout = QHBoxLayout()
        self.btn_sub_d, self.btn_sub_h, self.btn_sub_m = QPushButton("<<d"), QPushButton("<h"), QPushButton("<m")
        self.btn_add_m, self.btn_add_h, self.btn_add_d = QPushButton("m>"), QPushButton("h>"), QPushButton("d>>")
        for btn in [self.btn_sub_d, self.btn_sub_h, self.btn_sub_m, self.btn_add_m, self.btn_add_h, self.btn_add_d]: step_layout.addWidget(btn)
        
        btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        
        self.speed_combo = NoScrollComboBox()
        self.speed_combo.addItems([
            "1x", "10x", "60x (1m/s)", "120x (2m/s)", "300x (5m/s)", 
            "600x (10m/s)", "1800x (30m/s)", "3600x (1h/s)", 
            "14400x (4h/s)", "86400x (1d/s)", "604800x (1w/s)"
        ])
        
        btn_layout.addWidget(self.btn_play); btn_layout.addWidget(self.speed_combo)
        nav_layout.addLayout(step_layout); nav_layout.addLayout(btn_layout); nav_group.setLayout(nav_layout)
        
        transit_group = QGroupBox("Transit")
        transit_layout = QGridLayout(); transit_layout.setContentsMargins(4, 4, 4, 4); transit_layout.setSpacing(4)
        
        transit_layout.addWidget(QLabel("Lagna:"), 0, 0)
        self.btn_prev_lagna, self.btn_next_lagna = QPushButton("<"), QPushButton(">")
        transit_layout.addWidget(self.btn_prev_lagna, 0, 1); transit_layout.addWidget(self.btn_next_lagna, 0, 2)
        
        transit_layout.addWidget(QLabel("Plnt:"), 1, 0)
        self.cb_transit_planet = NoScrollComboBox(); self.cb_transit_planet.addItems(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
        self.cb_transit_div = NoScrollComboBox(); self.cb_transit_div.addItems(["D1", "D2", "D4", "D7", "D9", "D10", "D12", "D16", "D20", "D24", "D30", "D60"])
        
        p_layout = QHBoxLayout()
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.addWidget(self.cb_transit_planet)
        p_layout.addWidget(self.cb_transit_div)
        transit_layout.addLayout(p_layout, 1, 1, 1, 2)
        
        transit_layout.addWidget(QLabel("Rshi:"), 2, 0)
        self.cb_transit_rashi = NoScrollComboBox()
        self.cb_transit_rashi.addItems(["Any", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"])
        transit_layout.addWidget(self.cb_transit_rashi, 2, 1, 1, 2)

        transit_layout.addWidget(QLabel("Jump:"), 3, 0)
        self.btn_prev_rashi, self.btn_next_rashi = QPushButton("<"), QPushButton(">")
        transit_layout.addWidget(self.btn_prev_rashi, 3, 1); transit_layout.addWidget(self.btn_next_rashi, 3, 2)

        self.btn_stop_transit = QPushButton("Stop")
        self.btn_stop_transit.setStyleSheet("color: red; font-weight: bold;"); self.btn_stop_transit.hide()
        transit_layout.addWidget(self.btn_stop_transit, 4, 0, 1, 3); transit_group.setLayout(transit_layout)

        set_group = QGroupBox("Settings"); set_layout = QVBoxLayout(); set_layout.setContentsMargins(4, 4, 4, 4)
        self.cb_ayanamsa = NoScrollComboBox(); self.cb_ayanamsa.addItems(["Lahiri", "Raman", "Fagan/Bradley"])
        
        self.chk_symbols, self.chk_rahu, self.chk_arrows = QCheckBox("Symb"), QCheckBox("Ra/Ke"), QCheckBox("Arrows")
        self.chk_tint, self.chk_details, self.chk_circular = QCheckBox("Tints"), QCheckBox("Table"), QCheckBox("Circ UI")
        self.chk_rahu.setChecked(True); self.chk_arrows.setChecked(True); self.chk_tint.setChecked(True); self.chk_details.setChecked(True); self.chk_circular.setChecked(False)
        self.chk_aspects = QCheckBox("Aspects")
        self.btn_save_chart, self.btn_load_chart = QPushButton("Save"), QPushButton("Load")
        self.btn_export_png, self.btn_export_json = QPushButton("PNG"), QPushButton("JSON")
        
        self.btn_load_json_rectify = QPushButton("Load JSON (Rectify Time)")
        self.btn_load_json_rectify.setStyleSheet("font-weight: bold; color: #8e44ad;")
        
        self.btn_build_chart_rectify = QPushButton("Build Target Chart...")
        self.btn_build_chart_rectify.setStyleSheet("font-weight: bold; color: #2980b9;")

        chk_grid = QGridLayout()
        chk_grid.addWidget(QLabel("Ayanamsa:"), 0, 0); chk_grid.addWidget(self.cb_ayanamsa, 0, 1)
        chk_grid.addWidget(self.chk_symbols, 1, 0); chk_grid.addWidget(self.chk_rahu, 1, 1)
        chk_grid.addWidget(self.chk_aspects, 2, 0); chk_grid.addWidget(self.chk_arrows, 2, 1)
        chk_grid.addWidget(self.chk_tint, 3, 0); chk_grid.addWidget(self.chk_circular, 3, 1)
        chk_grid.addWidget(self.chk_details, 4, 0, 1, 2)
        set_layout.addLayout(chk_grid)
        
        file_btns = QHBoxLayout(); file_btns.addWidget(self.btn_save_chart); file_btns.addWidget(self.btn_load_chart)
        exp_btns = QHBoxLayout(); exp_btns.addWidget(self.btn_export_png); exp_btns.addWidget(self.btn_export_json)
        rect_btns = QHBoxLayout(); rect_btns.addWidget(self.btn_load_json_rectify); rect_btns.addWidget(self.btn_build_chart_rectify)
        
        set_layout.addLayout(file_btns); set_layout.addLayout(exp_btns)
        set_layout.addLayout(rect_btns)
        set_group.setLayout(set_layout)

        self.aspects_group = QGroupBox("Aspects From:")
        aspects_layout = QGridLayout(); aspects_layout.setContentsMargins(4, 4, 4, 4); self.aspect_cb = {}
        planets_data = [("Sun", "#FF8C00"), ("Moon", "#00BCD4"), ("Mars", "#FF0000"), ("Mercury", "#00C853"), ("Jupiter", "#FFD700"), ("Venus", "#FF1493"), ("Saturn", "#0000CD"), ("Rahu", "#708090"), ("Ketu", "#8B4513")]
        for i, (p, color) in enumerate(planets_data):
            cb = QCheckBox(p[:3]); cb.setStyleSheet(f"color: {color}; font-weight: bold;"); cb.setChecked(True); cb.stateChanged.connect(self.update_settings)
            self.aspect_cb[p] = cb; aspects_layout.addWidget(cb, i // 3, i % 3)
        self.aspects_group.setLayout(aspects_layout); self.aspects_group.setVisible(False)

        for g in [loc_group, dt_group, div_group, nav_group, transit_group, set_group, self.aspects_group]: left_layout.addWidget(g)
        left_layout.addStretch(); left_scroll.setWidget(left_panel)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.charts_scroll = QScrollArea()
        self.charts_scroll.setWidgetResizable(True)
        self.charts_container = QWidget()
        self.chart_layout = QGridLayout(self.charts_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_layout.setSpacing(10)
        self.charts_scroll.setWidget(self.charts_container)
        right_splitter.addWidget(self.charts_scroll)
        
        table_container = QWidget()
        tc_layout = QVBoxLayout(table_container)
        tc_top = QHBoxLayout()
        tc_top.addWidget(QLabel("Explore Details For:"))
        self.table_view_cb = NoScrollComboBox()
        for d_id, d_name in self.div_titles.items():
            self.table_view_cb.addItem(d_name, d_id)
        self.table_view_cb.currentIndexChanged.connect(self.recalculate)
        tc_top.addWidget(self.table_view_cb)
        tc_top.addStretch()
        tc_layout.addLayout(tc_top)
        
        self.table = QTableWidget(); self.table.setColumnCount(6); self.table.setHorizontalHeaderLabels(["Planet", "Sign", "Degree", "House", "Retrograde", "Freeze Rashi"])
        if self.table.horizontalHeader() is not None: self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tc_layout.addWidget(self.table)
        
        self.table_container = table_container
        right_splitter.addWidget(self.table_container)
        right_splitter.setSizes([750, 200])
        self.table_container.setVisible(self.chk_details.isChecked())

        # Give the left panel a wider default size on startup to ensure visibility
        main_splitter.addWidget(left_scroll); main_splitter.addWidget(right_splitter); main_splitter.setSizes([420, 880])

    def update_grid_layout(self):
        if self.is_updating_ui: return
        
        active_divs = [div for div, cb in self.div_cbs.items() if cb.isChecked()]
        if not active_divs:
            self.is_updating_ui = True
            self.div_cbs["D1"].setChecked(True)
            self.is_updating_ui = False
            active_divs.append("D1")
            
        for i in reversed(range(self.chart_layout.count())):
            item = self.chart_layout.itemAt(i)
            if item.widget(): item.widget().setParent(None)
                
        cols = 3 
        
        for i, div in enumerate(active_divs):
            row, col = i // cols, i % cols
            if div not in self.renderers:
                r = ChartRenderer()
                r.title = self.div_titles[div]
                self.renderers[div] = r
                
            self.chart_layout.addWidget(self.renderers[div], row, col)
            self.renderers[div].setMinimumSize(350, 350)
            
        self.update_settings()

    def set_transit_buttons_enabled(self, enabled):
        for btn in [self.btn_prev_lagna, self.btn_next_lagna, self.btn_prev_rashi, self.btn_next_rashi]: btn.setEnabled(enabled)
        self.cb_transit_planet.setEnabled(enabled); self.cb_transit_rashi.setEnabled(enabled)
        if enabled: self.btn_stop_transit.hide()
        else: self.btn_stop_transit.setText("Stop..."); self.btn_stop_transit.show()

    def _connect_signals(self):
        self.loc_btn.clicked.connect(self.search_location); self.loc_input.returnPressed.connect(self.search_location)
        self.time_ctrl.time_changed.connect(self.on_time_changed)
        
        self.btn_custom_loc.clicked.connect(self.show_custom_loc_dialog)
        self.btn_panchang.clicked.connect(self.show_panchang)

        self.year_spin.valueChanged.connect(self.on_ui_datetime_changed)
        self.month_spin.valueChanged.connect(self.on_ui_datetime_changed)
        self.day_spin.valueChanged.connect(self.on_ui_datetime_changed)
        self.time_edit.timeChanged.connect(self.on_ui_datetime_changed)
        
        self.btn_play.clicked.connect(self.toggle_play); self.speed_combo.currentIndexChanged.connect(self.change_speed)
        
        self.btn_add_m.clicked.connect(lambda: self.time_ctrl.step(60))
        self.btn_add_h.clicked.connect(lambda: self.time_ctrl.step(3600))
        self.btn_add_d.clicked.connect(lambda: self.time_ctrl.step(86400))
        self.btn_sub_m.clicked.connect(lambda: self.time_ctrl.step(-60))
        self.btn_sub_h.clicked.connect(lambda: self.time_ctrl.step(-3600))
        self.btn_sub_d.clicked.connect(lambda: self.time_ctrl.step(-86400))
        
        self.btn_prev_lagna.clicked.connect(lambda: self.jump_to_transit("Ascendant", -1))
        self.btn_next_lagna.clicked.connect(lambda: self.jump_to_transit("Ascendant", 1))
        self.btn_prev_rashi.clicked.connect(lambda: self.jump_to_transit(self.cb_transit_planet.currentText(), -1))
        self.btn_next_rashi.clicked.connect(lambda: self.jump_to_transit(self.cb_transit_planet.currentText(), 1))
        self.btn_stop_transit.clicked.connect(self.stop_transit_search)
        
        self.cb_transit_planet.currentIndexChanged.connect(self.recalculate)
        self.cb_transit_div.currentIndexChanged.connect(self.recalculate)
        
        self.cb_ayanamsa.currentTextChanged.connect(self.update_settings)
        for chk in [self.chk_symbols, self.chk_rahu, self.chk_arrows, self.chk_tint, self.chk_circular]: chk.stateChanged.connect(self.update_settings)
        self.chk_aspects.stateChanged.connect(self.toggle_aspects); self.chk_details.stateChanged.connect(self.toggle_details)
        self.btn_save_chart.clicked.connect(self.save_chart_dialog); self.btn_load_chart.clicked.connect(self.load_chart_dialog)
        self.btn_export_png.clicked.connect(self.export_chart_png)
        self.btn_export_json.clicked.connect(self.export_analysis_json)
        self.btn_load_json_rectify.clicked.connect(self.load_json_rectify_dialog)
        self.btn_build_chart_rectify.clicked.connect(self.open_chart_builder_dialog)
        
        self.btn_today_forecast.clicked.connect(self.show_today_forecast)
        self.btn_broad_forecast.clicked.connect(self.show_broad_forecast)

    def show_panchang(self):
        if not getattr(self, "current_base_chart", None) or "panchang" not in self.current_base_chart:
            QMessageBox.warning(self, "Not Ready", "Please wait for chart calculation.")
            return
        
        p = self.current_base_chart["panchang"]
        msg = f"<h2>Daily Panchang Details</h2>"
        msg += f"<p><b>Nakshatra:</b> {p['nakshatra']} (Swami: {p['nakshatra_lord']}), Pada {p['nakshatra_pada']}</p>"
        msg += f"<p><b>Tithi:</b> {p['paksha']} Paksha {p['tithi']}</p>"
        msg += f"<p><b>Sunrise:</b> {p['sunrise_str']}</p>"
        msg += f"<p><b>Sunset:</b> {p['sunset_str']}</p>"
        
        dlg = QDialog(self)
        dlg.setWindowTitle("Panchang Info")
        dlg.setMinimumWidth(350)
        lay = QVBoxLayout(dlg)
        lbl = QTextBrowser()
        lbl.setHtml(msg)
        lay.addWidget(lbl)
        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)
        dlg.exec()

    def show_custom_loc_dialog(self):
        dlg = CustomLocationDialog(self.current_lat, self.current_lon, self)
        if dlg.exec():
            lat, lon = dlg.get_coordinates()
            tz_name = TimezoneFinder().timezone_at(lng=lon, lat=lat) or "UTC"
            self.current_lat, self.current_lon, self.current_tz = lat, lon, tz_name
            self.loc_input.setText(f"{lat:.4f}, {lon:.4f}")
            self.loc_status.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} | TZ: {tz_name}")
            self.save_settings()
            self.recalculate()

    def search_location(self):
        self.loc_btn.setEnabled(False); self.loc_btn.setText("Search...")
        self.loc_worker = LocationWorker(self.loc_input.text())
        self.loc_worker.result_ready.connect(self.on_location_found)
        self.loc_worker.error_occurred.connect(self.on_location_error)
        self.loc_worker.start()

    def on_location_found(self, lat, lon, tz_name, name):
        self.current_lat, self.current_lon, self.current_tz = lat, lon, tz_name
        self.loc_status.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} | TZ: {tz_name}")
        self.loc_btn.setEnabled(True); self.loc_btn.setText("Search")
        self.save_settings(); self.recalculate()

    def on_location_error(self, err_msg):
        QMessageBox.warning(self, "Location Error", err_msg)
        self.loc_btn.setEnabled(True); self.loc_btn.setText("Search")

    def on_time_changed(self, dt):
        self.is_updating_ui = True
        self.year_spin.setValue(dt['year'])
        self.month_spin.setValue(dt['month'])
        self.day_spin.setValue(dt['day'])
        self.time_edit.setTime(QTime(dt['hour'], dt['minute'], int(dt['second'])))
        self.is_updating_ui = False; self.recalculate()

    def on_ui_datetime_changed(self):
        if self.is_updating_ui: return
        t = self.time_edit.time()
        self.time_ctrl.set_time({
            'year': self.year_spin.value(), 'month': self.month_spin.value(), 'day': self.day_spin.value(), 
            'hour': t.hour(), 'minute': t.minute(), 'second': t.second()
        })

    def stop_transit_search(self):
        if hasattr(self, 'transit_worker') and self.transit_worker.isRunning(): self.transit_worker.stop()

    def jump_to_transit(self, body_name, direction):
        if hasattr(self, 'transit_worker') and self.transit_worker.isRunning():
            self.transit_worker.stop(); self.transit_worker.wait()
            
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        if self.time_ctrl.is_playing: self.toggle_play()
        target_sign = self.cb_transit_rashi.currentText()
        if target_sign == "Any": target_sign = "Any Rashi"
        
        # Grab the currently selected division for transit calculation
        div_type = getattr(self, 'cb_transit_div', None) and self.cb_transit_div.currentText() or "D1"
        
        if body_name in self.frozen_planets:
            f_info = self.frozen_planets[body_name]
            frozen_sign_name = zodiac_names[f_info["sign_idx"]]
            if target_sign == "Any Rashi" or target_sign != frozen_sign_name or div_type != f_info["div"]:
                ans = QMessageBox.question(self, "Unfreeze Required", f"'{body_name}' is currently frozen in {frozen_sign_name} ({f_info['div']}).\nTo search for its next transit, it must be automatically unfrozen.\n\nUnfreeze {body_name} to proceed?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ans == QMessageBox.StandardButton.Yes: 
                    del self.frozen_planets[body_name]
                    self.recalculate() 
                else: 
                    return

        self.set_transit_buttons_enabled(False)
        params = {
            'dt': self.time_ctrl.current_time, 
            'lat': self.current_lat, 'lon': self.current_lon, 'tz_name': self.current_tz, 
            'body_name': body_name, 'direction': direction, 
            'target_sign_name': target_sign, 'frozen_planets': self.frozen_planets.copy(), 
            'ayanamsa': self.cb_ayanamsa.currentText(),
            'div_type': div_type
        }

        self.transit_worker = TransitWorkerThread(params)
        self.transit_worker.finished.connect(lambda jd, d=direction: self.on_transit_finished(jd, d))
        self.transit_worker.error.connect(self.on_transit_error)
        self.transit_worker.stopped.connect(self.on_transit_stopped)
        self.transit_worker.progress.connect(self.on_transit_progress)
        self.transit_worker.start()

    def on_transit_progress(self, date_str): self.btn_stop_transit.setText(f"Stop (~{date_str})")

    def on_transit_finished(self, next_jd_utc, direction):
        self.set_transit_buttons_enabled(True)
        if next_jd_utc is None:
            QMessageBox.warning(self, "Transit Blocked", "Could not find transit without breaking freeze constraints.")
            return
            
        offset_sec = 1 if direction == 1 else -1
        local_dict = astro_engine.utc_jd_to_dt_dict(next_jd_utc + (offset_sec / 86400.0), self.current_tz)
        self.time_ctrl.set_time(local_dict)

    def on_transit_error(self, err_msg):
        self.set_transit_buttons_enabled(True)
        if hasattr(self, 'transit_worker') and self.transit_worker.isRunning(): self.transit_worker.stop()
        QMessageBox.warning(self, "Transit Error", f"Search Limit Reached: {err_msg}")

    def on_transit_stopped(self): self.set_transit_buttons_enabled(True)

    def toggle_play(self): self.btn_play.setText("⏸ Pause" if self.time_ctrl.toggle_animation() else "▶ Play")

    def change_speed(self): 
        speeds = [1.0, 10.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0, 14400.0, 86400.0, 604800.0]
        self.time_ctrl.set_speed(speeds[self.speed_combo.currentIndex()])

    def update_settings(self):
        if self.is_updating_ui: return
        self.ephemeris.set_ayanamsa(self.cb_ayanamsa.currentText())
        for r in self.renderers.values():
            r.use_symbols = self.chk_symbols.isChecked()
            r.show_rahu_ketu = self.chk_rahu.isChecked()
            r.show_aspects = self.chk_aspects.isChecked()
            r.show_arrows = self.chk_arrows.isChecked()
            r.use_tint = self.chk_tint.isChecked()
            r.use_circular = self.chk_circular.isChecked()
            r.visible_aspect_planets = {p for p, cb in self.aspect_cb.items() if cb.isChecked()}
        self.save_settings(); self.recalculate()

    def toggle_aspects(self):
        self.aspects_group.setVisible(self.chk_aspects.isChecked()); self.chk_arrows.setVisible(self.chk_aspects.isChecked())
        self.chk_tint.setVisible(self.chk_aspects.isChecked()); self.update_settings()

    def toggle_details(self): self.table_container.setVisible(self.chk_details.isChecked()); self.save_settings()

    def get_current_chart_info(self): return {"location": self.loc_input.text(), "lat": self.current_lat, "lon": self.current_lon, "tz": self.current_tz, "datetime_dict": self.time_ctrl.current_time}

    def save_chart_dialog(self):
        os.makedirs("saves", exist_ok=True)
        default_dir = self.current_file_path if self.current_file_path else os.path.join("saves", "")
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", default_dir, "JSON Files (*.json);;All Files (*)")
        if path and save_prefs.save_chart_to_file(path, self.get_current_chart_info()):
            self.is_chart_saved = True
            self.current_file_path = path
            self.update_window_title()
            QMessageBox.information(self, "Success", "Chart saved successfully.")

    def load_chart_dialog(self):
        os.makedirs("saves", exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(self, "Load Chart", self.last_load_dir, "JSON Files (*.json);;All Files (*)")
        if path:
            self.last_load_dir = os.path.dirname(path)
            data = save_prefs.load_chart_from_file(path)
            if data:
                self.current_file_path = path
                self.update_window_title()
                
                self.is_updating_ui = True; self.frozen_planets.clear()
                
                # --- COMPATIBILITY: Import large Analysis JSON as standard save ---
                if "metadata" in data:
                    meta = data["metadata"]
                    data = {
                        "location": meta.get("location", "Imported Analysis"),
                        "lat": meta.get("latitude", 28.6139),
                        "lon": meta.get("longitude", 77.2090),
                        "datetime_dict": meta.get("datetime")
                    }
                    if "ayanamsa" in meta:
                        self.cb_ayanamsa.setCurrentText(meta["ayanamsa"])
                        
                    tz = TimezoneFinder().timezone_at(lng=data["lon"], lat=data["lat"])
                    data["tz"] = tz or "UTC"

                self.loc_input.setText(data.get("location", "New Delhi, India"))
                self.current_lat, self.current_lon, self.current_tz = data.get("lat", 28.6139), data.get("lon", 77.2090), data.get("tz", "Asia/Kolkata")
                self.loc_status.setText(f"Lat: {self.current_lat:.4f}, Lon: {self.current_lon:.4f}\nTZ: {self.current_tz}")
                
                if "datetime_dict" in data and isinstance(data["datetime_dict"], dict): 
                    self.time_ctrl.set_time(data["datetime_dict"])
                elif "datetime" in data:
                    try:
                        if isinstance(data["datetime"], dict):
                            self.time_ctrl.set_time(data["datetime"])
                        else:
                            dt = datetime.datetime.fromisoformat(data["datetime"])
                            self.time_ctrl.set_time({'year': dt.year, 'month': dt.month, 'day': dt.day, 'hour': dt.hour, 'minute': dt.minute, 'second': dt.second})
                    except Exception as e: print(f"Error parsing date from file: {e}")
                
                self.is_updating_ui = False; self.save_settings(); self.recalculate(); self.is_chart_saved = True
            else: QMessageBox.warning(self, "Error", "Failed to load chart data.")

    def open_chart_builder_dialog(self):
        dlg = ChartBuilderDialog(self)
        if dlg.exec():
            target_div, target_asc, target_planets = dlg.get_chart_data()
            if not target_planets and target_asc is None:
                QMessageBox.warning(self, "Empty Chart", "Please specify at least one planetary position or Ascendant.")
                return
            self.initiate_rectification_flow(target_div, target_asc, target_planets, metadata=None)

    def load_json_rectify_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load JSON for Rectification", self.last_load_dir, "JSON Files (*.json);;All Files (*)")
        if not path: return
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
                
            target_div = None
            chart_node = None
            
            if "divisional_charts" in data: charts = data["divisional_charts"]
            else: charts = data
                
            for div in ["D60", "D30", "D24", "D20", "D16", "D12", "D10", "D9", "D7", "D4", "D2", "D1"]:
                if div in charts:
                    target_div = div; chart_node = charts[div]; break

            if not target_div or not chart_node:
                QMessageBox.warning(self, "Invalid JSON", "Could not find a valid divisional chart block (e.g. 'D60') in JSON.")
                return
                
            target_asc = chart_node.get("ascendant", {}).get("sign_index")
            target_planets = {p["name"]: p["sign_index"] for p in chart_node.get("planets", []) if "name" in p and "sign_index" in p}
            
            meta = data.get("metadata", {})
            self.initiate_rectification_flow(target_div, target_asc, target_planets, metadata=meta)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Load Error", f"Failed to parse JSON:\n{str(e)}")

    def initiate_rectification_flow(self, target_div, target_asc, target_planets, metadata=None):
        # --- Extract Location/TZ (JSON Metadata overrides current UI settings) ---
        rectify_lat = self.current_lat
        rectify_lon = self.current_lon
        rectify_tz = self.current_tz
        rectify_ayanamsa = self.cb_ayanamsa.currentText()

        if metadata:
            rectify_lat = metadata.get("latitude", self.current_lat)
            rectify_lon = metadata.get("longitude", self.current_lon)
            if "ayanamsa" in metadata:
                rectify_ayanamsa = metadata["ayanamsa"]
                self.cb_ayanamsa.setCurrentText(rectify_ayanamsa) 
            rectify_tz = TimezoneFinder().timezone_at(lng=rectify_lon, lat=rectify_lat) or "UTC"

        # --- CONSTRUCT HYPOTHETICAL CHART DATA FOR VISUAL VERIFICATION ---
        synthetic_chart = {
            "ascendant": {
                "sign_index": target_asc if target_asc is not None else 0,
                "sign_num": (target_asc if target_asc is not None else 0) + 1,
                "degree": (target_asc if target_asc is not None else 0) * 30 + 15.0,
                "div_lon": (target_asc if target_asc is not None else 0) * 30 + 15.0,
                "vargottama": False
            },
            "planets": [],
            "aspects": []
        }
        
        exaltation_rules = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
        debilitation_rules = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
        sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}

        for p_name, s_idx in target_planets.items():
            sign_num = s_idx + 1
            synthetic_chart["planets"].append({
                "name": p_name,
                "sym": p_name[:2],
                "lon": s_idx * 30 + 15.0,
                "div_lon": s_idx * 30 + 15.0,
                "sign_index": s_idx,
                "sign_num": sign_num,
                "deg_in_sign": 15.0, 
                "house": ((s_idx - (target_asc if target_asc is not None else 0)) % 12) + 1,
                "retro": False,
                "exalted": (sign_num == exaltation_rules.get(p_name)),
                "debilitated": (sign_num == debilitation_rules.get(p_name)),
                "combust": False,
                "own_sign": (sign_rulers.get(sign_num) == p_name),
                "vargottama": False,
                "is_ak": False
            })

        base_year = self.year_spin.value()
        
        params = {
            "div_type": target_div, "target_asc": target_asc, "target_planets": target_planets,
            "base_year": base_year, "lat": rectify_lat, "lon": rectify_lon,
            "tz": rectify_tz, "ayanamsa": rectify_ayanamsa,
            "search_mode": "speed"
        }
        
        self.rectify_dialog = QDialog(self)
        self.rectify_dialog.setWindowTitle(f"Verify & Rectify Target ({target_div})")
        self.rectify_dialog.resize(500, 600)
        
        layout = QVBoxLayout()
        
        info_lbl = QLabel(f"Please verify the hypothetical {target_div} chart.\nClick 'Search Birth Time' to find the exact timestamp.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-weight: bold; color: #2c3e50;")
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_lbl)
        
        renderer = ChartRenderer()
        renderer.title = f"Hypothetical Target {target_div}"
        renderer.setMinimumSize(400, 400)
        
        renderer.use_symbols = self.chk_symbols.isChecked()
        renderer.show_rahu_ketu = self.chk_rahu.isChecked()
        renderer.show_aspects = self.chk_aspects.isChecked()
        renderer.show_arrows = self.chk_arrows.isChecked()
        renderer.use_tint = self.chk_tint.isChecked()
        renderer.use_circular = self.chk_circular.isChecked()
        
        renderer.update_chart(synthetic_chart)
        layout.addWidget(renderer)
        
        self.rectify_lbl = QLabel("Ready to search.")
        self.rectify_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rectify_lbl.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(self.rectify_lbl)
        
        btn_layout = QHBoxLayout()
        self.rectify_btn_search = QPushButton("Search Birth Time")
        self.rectify_btn_search.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        
        export_btn = QPushButton("Export JSON")
        export_btn.setStyleSheet("font-weight: bold; color: #8e44ad; padding: 8px;")
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 8px;")
        
        self.rectify_worker = RectificationWorkerThread(params)
        
        def start_search():
            self.rectify_btn_search.setEnabled(False)
            self.rectify_btn_search.setText("Searching... Please wait.")
            self.rectify_worker.start()
            
        def export_target_chart():
            os.makedirs("created chart exports", exist_ok=True)
            default_path = os.path.join("created chart exports", f"tmp_created_{target_div}_chart.json")
            path, _ = QFileDialog.getSaveFileName(self.rectify_dialog, "Export Target Chart JSON", default_path, "JSON Files (*.json);;All Files (*)")
            if not path: return
            
            export_data = {
                "divisional_charts": {
                    target_div: {
                        "ascendant": {"sign_index": target_asc} if target_asc is not None else {},
                        "planets": [{"name": p, "sign_index": s} for p, s in target_planets.items()]
                    }
                }
            }
            if metadata:
                export_data["metadata"] = metadata
                
            try:
                with open(path, 'w') as f:
                    json.dump(export_data, f, indent=4)
                QMessageBox.information(self.rectify_dialog, "Export Successful", f"Chart saved successfully to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self.rectify_dialog, "Export Error", f"Failed to save JSON:\n{str(e)}")
            
        def cancel_rect():
            if self.rectify_worker.isRunning(): self.rectify_worker.stop()
            self.rectify_dialog.reject()
            
        self.rectify_btn_search.clicked.connect(start_search)
        export_btn.clicked.connect(export_target_chart)
        cancel_btn.clicked.connect(cancel_rect)
        
        btn_layout.addWidget(self.rectify_btn_search)
        btn_layout.addWidget(export_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.rectify_dialog.setLayout(layout)
        
        self.rectify_worker.progress.connect(lambda msg: self.rectify_lbl.setText(msg))
        self.rectify_worker.error.connect(lambda err: QMessageBox.warning(self, "Error", err))
        self.rectify_worker.finished.connect(self.on_rectify_finished)
        
        self.rectify_dialog.exec()

    def on_rectify_finished(self, res):
        if res["status"] == "success":
            self.rectify_dialog.accept() 
            blocks = res["blocks"]
            year = res["year"]
            
            msg = f"Found {len(blocks)} precise match window(s) in {year}:\n\n"
            months_found = set()
            
            for i, b in enumerate(blocks):
                s_dt, e_dt = b["start"], b["end"]
                m_name = datetime.date(2000, s_dt['month'], 1).strftime('%B')
                months_found.add(m_name)
                msg += f"{i+1}. {m_name} {s_dt['day']}, {s_dt['hour']:02d}:{s_dt['minute']:02d} to {e_dt['hour']:02d}:{e_dt['minute']:02d}\n"
                
            msg += f"\nMatches found in months: {', '.join(sorted(list(months_found)))}\n"
            msg += "\nAutomatically applied the chronologically closest match to the timeline."
            
            QMessageBox.information(self, "Rectification Success", msg)
            
            target_dt = astro_engine.utc_jd_to_dt_dict(blocks[0]["mid_jd"], self.current_tz)
            self.time_ctrl.set_time(target_dt)
            
        elif res["status"] == "phase1_failed":
            ans = QMessageBox.question(
                self.rectify_dialog, 
                "Speed Search Missed", 
                "Cascading lock-pick search completely swept +/- 1000 years but found no matches.\n\nThis is extremely rare and usually indicates a planet's retrograde loop barely grazed a fractional boundary.\n\nDo you want to engage Phase 2: Deep Brute-Force? (This will rigorously check every single minute, radiating outward from the origin target year up to 1000 years. It may take longer.)",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans == QMessageBox.StandardButton.Yes:
                self.rectify_btn_search.setEnabled(False)
                self.rectify_btn_search.setText("Brute-Forcing... Please wait.")
                params = self.rectify_worker.params.copy()
                params["search_mode"] = "brute"
                
                # Resurrect the worker in brute force mode
                self.rectify_worker = RectificationWorkerThread(params)
                self.rectify_worker.progress.connect(lambda msg: self.rectify_lbl.setText(msg))
                self.rectify_worker.error.connect(lambda err: QMessageBox.warning(self, "Error", err))
                self.rectify_worker.finished.connect(self.on_rectify_finished)
                self.rectify_worker.start()
            else:
                self.rectify_dialog.accept()

        elif res["status"] == "not_found":
            self.rectify_dialog.accept()
            QMessageBox.warning(self, "Not Found", res["message"])

    def export_chart_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart PNG", "", "PNG Files (*.png);;All Files (*)")
        if path: self.charts_container.grab().save(path, "PNG")

    def export_analysis_json(self):
        os.makedirs("analysis_export", exist_ok=True)
        
        default_name = "Vedic_Analysis.json"
        if getattr(self, "current_file_path", None):
            base_name = os.path.splitext(os.path.basename(self.current_file_path))[0]
            default_name = f"{base_name}_analysis.json"
            
        default_path = os.path.join("analysis_export", default_name)
        
        path, _ = QFileDialog.getSaveFileName(self, "Export Analysis JSON", default_path, "JSON Files (*.json);;All Files (*)")
        if not path: return
        
        try:
            chart_data = self.ephemeris.calculate_chart(self.time_ctrl.current_time, self.current_lat, self.current_lon, self.current_tz)
            
            export_data = {
                "metadata": {
                    "location": self.loc_input.text(),
                    "latitude": self.current_lat,
                    "longitude": self.current_lon,
                    "datetime": self.time_ctrl.current_time,
                    "ayanamsa": self.cb_ayanamsa.currentText(),
                },
                "divisional_charts": {}
            }
            
            if "panchang" in chart_data:
                export_data["metadata"]["panchang"] = {
                    "nakshatra": chart_data["panchang"]["nakshatra"],
                    "nakshatra_lord": chart_data["panchang"]["nakshatra_lord"],
                    "nakshatra_pada": chart_data["panchang"]["nakshatra_pada"],
                    "tithi": f"{chart_data['panchang']['paksha']} {chart_data['panchang']['tithi']}",
                    "sunrise": chart_data["panchang"]["sunrise_str"],
                    "sunset": chart_data["panchang"]["sunset_str"]
                }
            
            moon_p = next((p for p in chart_data["planets"] if p["name"] == "Moon"), None)
            if moon_p:
                birth_jd = astro_engine.dt_dict_to_utc_jd(self.time_ctrl.current_time, self.current_tz)
                export_data["vimshottari_dasha_timeline"] = self.ephemeris.get_dasha_export_list(birth_jd, moon_p["lon"])
            
            ordinal = lambda n: str(n) + ('th' if 11 <= (n % 100) <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))
            preferred_houses = {1, 2, 4, 5, 7, 9, 10, 11}
            
            for div in self.div_titles.keys():
                div_data = self.ephemeris.compute_divisional_chart(chart_data, div) if div != "D1" else chart_data
                
                analysis_items = []
                for p in div_data["planets"]:
                    if not p.get("lord_of"): continue
                    for ruled_house in p["lord_of"]:
                        if ruled_house in preferred_houses and p["house"] in preferred_houses:
                            dignity = "Exalted" if p.get("exalted") else "Debilitated" if p.get("debilitated") else "Own Sign" if p.get("own_sign") else "Neutral"
                            analysis_items.append(f"{ordinal(ruled_house)} lord ({p['name']}) is in {ordinal(p['house'])} house ({dignity})")
                
                planets_list = []
                for p in div_data["planets"]:
                    planets_list.append({
                        "name": p["name"],
                        "sign_index": p["sign_index"],
                        "house": p["house"],
                        "degree_in_sign": p["deg_in_sign"],
                        "is_retrograde": p["retro"],
                        "is_brightest_ak": p.get("is_ak", False),
                        "nakshatra": p.get("nakshatra"),
                        "nakshatra_lord": p.get("nakshatra_lord"),
                        "nakshatra_pada": p.get("nakshatra_pada")
                    })
                export_data["divisional_charts"][div] = {
                    "ascendant": {
                        "sign_index": div_data["ascendant"]["sign_index"],
                        "degree_in_sign": div_data["ascendant"]["degree"] % 30,
                        "nakshatra": div_data["ascendant"].get("nakshatra"),
                        "nakshatra_lord": div_data["ascendant"].get("nakshatra_lord"),
                        "nakshatra_pada": div_data["ascendant"].get("nakshatra_pada")
                    },
                    "planets": planets_list, 
                    "auspicious_analysis": analysis_items
                }
                
            with open(path, 'w') as f: json.dump(export_data, f, indent=4)
            QMessageBox.information(self, "Export Successful", "Extensive Analysis JSON exported successfully!")
        except Exception as e: QMessageBox.critical(self, "Export Error", f"Failed to export JSON:\n{str(e)}")

    def get_daily_forecast_html(self, target_date):
        if not self.current_base_chart:
            return "<h2 style='color:red; text-align:center;'>Chart calculation error. Check settings.</h2>"
            
        dt_start = {'year': target_date.year, 'month': target_date.month, 'day': target_date.day, 'hour': 0, 'minute': 0, 'second': 0.0}
        start_jd = astro_engine.dt_dict_to_utc_jd(dt_start, self.current_tz)
        end_jd = start_jd + 1.0
        
        moon_p = next((p for p in self.current_base_chart["planets"] if p["name"] == "Moon"), None)
        if not moon_p: return "<h2>Moon not found in chart. Cannot calculate Dasha.</h2>"
        
        birth_jd = astro_engine.dt_dict_to_utc_jd(self.time_ctrl.current_time, self.current_tz)
        
        dasha_info = self.ephemeris.calculate_vimshottari_dasha(birth_jd, moon_p["lon"], start_jd, start_jd, end_jd)
        
        d9_chart = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D9")
        d10_chart = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D10")
        d20_chart = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D20")
        d30_chart = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D30")
        d60_chart = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D60")
        
        short = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
        
        html = ""
        for pr in dasha_info["pran_forecast"]:
            sd = astro_engine.utc_jd_to_dt_dict(pr["start_jd"], self.current_tz)
            ed = astro_engine.utc_jd_to_dt_dict(pr["end_jd"], self.current_tz)
            time_str = f"{sd['hour']:02d}:{sd['minute']:02d} to {ed['hour']:02d}:{ed['minute']:02d}"
            seq_str = " &rarr; ".join([short.get(d, d) for d in pr["sequence"]])
            
            insight_html = self.ephemeris.generate_prana_insight(pr["sequence"], self.current_base_chart, d9_chart, d10_chart, d20_chart, d30_chart, d60_chart)
            
            html += f"""
            <div style="margin-bottom: 25px; padding: 15px; border: 1px solid #dcdcdc; border-radius: 8px; background-color: #ffffff;">
                <h3 style="color: #c0392b; margin-top: 0; font-size: 16px; border-bottom: 2px solid #f0f0f0; padding-bottom: 5px;">Time: {time_str}</h3>
                <p style="font-size: 14px; margin-bottom: 15px;"><b>Sequence:</b> {seq_str}</p>
                {insight_html}
            </div>
            """
            
        if not html: html = "<h2>No forecast data found for this range.</h2>"
        return html

    def show_today_forecast(self):
        if hasattr(self, 'current_base_chart') and self.current_base_chart:
            dlg = ForecastDialog(self, self)
            dlg.exec()
        else: QMessageBox.warning(self, "Notice", "Forecast not ready. Please wait for charts to render.")
        
    def show_broad_forecast(self):
        if hasattr(self, 'current_base_chart') and self.current_base_chart:
            now = datetime.datetime.now()
            birth_jd = astro_engine.dt_dict_to_utc_jd(self.time_ctrl.current_time, self.current_tz)
            
            moon_p = next((p for p in self.current_base_chart["planets"] if p["name"] == "Moon"), None)
            if not moon_p:
                QMessageBox.warning(self, "Notice", "Moon not found in chart. Cannot calculate Dasha.")
                return
                
            now_dict = {'year': now.year, 'month': now.month, 'day': now.day, 'hour': now.hour, 'minute': now.minute, 'second': now.second}
            target_jd = astro_engine.dt_dict_to_utc_jd(now_dict, self.current_tz)
            
            dasha_info = self.ephemeris.calculate_vimshottari_dasha(birth_jd, moon_p["lon"], target_jd)
            seq = dasha_info["current_sequence"]
            
            d9 = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D9")
            d10 = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D10")
            d20 = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D20")
            d30 = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D30")
            d60 = self.ephemeris.compute_divisional_chart(self.current_base_chart, "D60")
            
            html_content = self.ephemeris.generate_broad_dasha_insight(seq, self.current_base_chart, d9, d10, d20, d30, d60)
            
            dlg = BroadForecastDialog(html_content, self)
            dlg.exec()
        else:
            QMessageBox.warning(self, "Notice", "Chart not ready. Please wait for charts to render.")

    def closeEvent(self, event):
        self.do_autosave()
        super().closeEvent(event)

    def recalculate(self):
        try:
            real_now = datetime.datetime.now(datetime.timezone.utc)
            real_now_jd = swe.julday(real_now.year, real_now.month, real_now.day, real_now.hour + real_now.minute/60.0 + real_now.second/3600.0)
            
            transit_div = getattr(self, 'cb_transit_div', None) and self.cb_transit_div.currentText() or "D1"
            transit_planet = getattr(self, 'cb_transit_planet', None) and self.cb_transit_planet.currentText() or "Sun"
            
            chart_data = self.ephemeris.calculate_chart(self.time_ctrl.current_time, self.current_lat, self.current_lon, self.current_tz, real_now_jd, transit_div, transit_planet)
            self.current_base_chart = chart_data
            
            violation, violating_planet, violating_div = False, None, None
            for p in chart_data["planets"]:
                if p["name"] in self.frozen_planets:
                    f_info = self.frozen_planets[p["name"]]
                    p_div_data = self.ephemeris.compute_divisional_chart(chart_data, f_info["div"]) if f_info["div"] != "D1" else chart_data
                    p_div_p = next(x for x in p_div_data["planets"] if x["name"] == p["name"])
                    if p_div_p["sign_index"] != f_info["sign_idx"]:
                        violation = True; violating_planet = p["name"]; violating_div = f_info["div"]; break
            
            if not violation and "Ascendant" in self.frozen_planets:
                f_info = self.frozen_planets["Ascendant"]
                p_div_data = self.ephemeris.compute_divisional_chart(chart_data, f_info["div"]) if f_info["div"] != "D1" else chart_data
                if p_div_data["ascendant"]["sign_index"] != f_info["sign_idx"]:
                    violation = True; violating_planet = "Ascendant"; violating_div = f_info["div"]
            
            if violation:
                zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                if hasattr(self, 'last_good_time'):
                    self.time_ctrl.set_time(dict(self.last_good_time))
                    if self.time_ctrl.is_playing: self.toggle_play()
                    if not getattr(self, "freeze_msg_shown", False):
                        self.freeze_msg_shown = True
                        f_info = self.frozen_planets[violating_planet]
                        QMessageBox.warning(self, "Freeze Boundary Reached", f"{violating_planet} is frozen in {zodiac_names[f_info['sign_idx']]} ({violating_div}). Cannot step further.")
                        QTimer.singleShot(1500, lambda: setattr(self, "freeze_msg_shown", False))
                    return
                    
            self.last_good_time = dict(self.time_ctrl.current_time)

            if "current_jd" in chart_data and "next_asc_jd" in chart_data and "prev_asc_jd" in chart_data:
                curr_jd = chart_data["current_jd"]
                next_asc_jd, prev_asc_jd = chart_data["next_asc_jd"], chart_data["prev_asc_jd"]
                
                diff_next_asc = max(0, int((next_asc_jd - curr_jd) * 1440))
                diff_prev_asc = max(0, int((curr_jd - prev_asc_jd) * 1440))
                
                def fmt_time(m): 
                    if m < 60: return f"{m}m"
                    elif m < 1440: return f"{m//60}h {m%60}m"
                    elif m < 10080: return f"{m//1440}d {(m%1440)//60}h"
                    elif m < 43200: return f"{m//1440}d"
                    elif m < 525600: return f"{m//43200}mo {(m%43200)//1440}d"
                    else: return f"{m//525600}y {(m%525600)//43200}mo"
                    
                self.btn_next_lagna.setText(f">\n({fmt_time(diff_next_asc)})")
                self.btn_prev_lagna.setText(f"<\n({fmt_time(diff_prev_asc)})")

                if "next_p_jd" in chart_data and "prev_p_jd" in chart_data:
                    next_p_jd, prev_p_jd = chart_data["next_p_jd"], chart_data["prev_p_jd"]
                    diff_next_p = max(0, int((next_p_jd - curr_jd) * 1440))
                    diff_prev_p = max(0, int((curr_jd - prev_p_jd) * 1440))
                    self.btn_next_rashi.setText(f">\n({fmt_time(diff_next_p)})")
                    self.btn_prev_rashi.setText(f"<\n({fmt_time(diff_prev_p)})")

            if "dasha_sequence" in chart_data and chart_data["dasha_sequence"]:
                short = {"Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me", "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"}
                seq = " → ".join([short.get(d, d) for d in chart_data["dasha_sequence"]])
                self.dasha_label.setText(f"Now: {seq}")
            else:
                self.dasha_label.setText("Now: Out of Bounds")

            table_div = self.table_view_cb.currentData()
            if table_div == "D1": table_data = chart_data
            else: table_data = self.ephemeris.compute_divisional_chart(chart_data, table_div)
            self.update_table(table_data)

            for div, renderer in self.renderers.items():
                if renderer.parent() is not None:
                    div_data = self.ephemeris.compute_divisional_chart(chart_data, div) if div != "D1" else chart_data
                    renderer.update_chart(div_data, chart_data)
                        
            if not self.is_loading_settings: self.is_chart_saved = False
        except Exception as e: print(f"Calculation Error: {e}")

    def toggle_freeze(self, name, sign_idx, checked, div_type):
        if checked: self.frozen_planets[name] = {"sign_idx": sign_idx, "div": div_type}
        elif name in self.frozen_planets: del self.frozen_planets[name]

    def update_table(self, chart_data):
        self.table.setRowCount(0)
        current_div = self.table_view_cb.currentData()
        is_d1 = (current_div == "D1")
        
        self.table.setColumnCount(6)
        headers = ["Planet", "Sign", "Degree", "House", "Retrograde", f"Freeze {current_div} Rashi"]
        self.table.setHorizontalHeaderLabels(headers)
        
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        asc = chart_data["ascendant"]
        
        def add_freeze_cb(row, name, sign_idx):
            cb = QCheckBox(f"Freeze in {zodiac_names[sign_idx][:3]}")
            is_frozen = name in self.frozen_planets and self.frozen_planets[name]["div"] == current_div
            cb.setChecked(is_frozen)
            cb.toggled.connect(lambda checked, n=name, s=sign_idx, d=current_div: self.toggle_freeze(n, s, checked, d))
            w = QWidget(); l = QHBoxLayout(w); l.addWidget(cb); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(row, 5, w)

        def make_name(name_str, is_vargottama, is_ak):
            base = f"{name_str} ★" if is_vargottama and not is_d1 else name_str
            return f"AK: {base}" if is_ak else base
            
        self.table.insertRow(0)
        self.table.setItem(0, 0, QTableWidgetItem(make_name("Ascendant", asc.get("vargottama", False), False)))
        self.table.setItem(0, 1, QTableWidgetItem(zodiac_names[asc["sign_index"]]))
        self.table.setItem(0, 2, QTableWidgetItem(f"{asc['degree'] % 30:.2f}°" if is_d1 else f"{asc.get('div_lon', asc['degree']) % 30:.2f}°"))
        self.table.setItem(0, 3, QTableWidgetItem("1")); self.table.setItem(0, 4, QTableWidgetItem("-"))
        add_freeze_cb(0, "Ascendant", asc["sign_index"])

        for i, p in enumerate(chart_data["planets"]):
            row = i + 1
            if p["name"] in ["Rahu", "Ketu"] and not self.chk_rahu.isChecked(): continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(make_name(p["name"], p.get("vargottama", False), p.get("is_ak", False))))
            self.table.setItem(row, 1, QTableWidgetItem(zodiac_names[p["sign_index"]]))
            self.table.setItem(row, 2, QTableWidgetItem(f"{p['deg_in_sign']:.2f}°" if is_d1 else f"{p.get('div_lon', p['deg_in_sign']) % 30:.2f}°"))
            self.table.setItem(row, 3, QTableWidgetItem(str(p["house"])))
            self.table.setItem(row, 4, QTableWidgetItem("Yes" if p["retro"] else "No"))
            add_freeze_cb(row, p["name"], p["sign_index"])

GLOBAL_FONT_FAMILY, GLOBAL_FONT_SCALE, GLOBAL_PRIMARY_COLOR = "Segoe UI", 11, "#4A90E2" 

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setFont(QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SCALE)); app.setStyle("Fusion")
    app.setStyleSheet(f"QGroupBox::title {{ color: {GLOBAL_PRIMARY_COLOR}; font-weight: bold; }} QPushButton {{ padding: 4px 8px; }} QPushButton:checked {{ background-color: {GLOBAL_PRIMARY_COLOR}; color: white; }}")
    
    window = AstroApp()
    window.showMaximized() 
    sys.exit(app.exec())