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

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QTimeEdit, 
                             QTableWidget, QTableWidgetItem, QCheckBox,
                             QHeaderView, QMessageBox, QGroupBox, QFileDialog,
                             QScrollArea, QGridLayout, QSpinBox)
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygonF, QCursor
from PyQt6.QtCore import Qt, QDate, QTime, QThread, pyqtSignal, QRectF, QPointF, QObject, QTimer

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

import save_prefs
import animation
import astro_engine

# ==========================================
# 1. LOCATION WORKER
# ==========================================
class LocationWorker(QThread):
    result_ready = pyqtSignal(float, float, str, str) # lat, lon, tz_name, formatted_name
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
                    self.finished.emit(res["result_jd_utc"])
                    return
                elif res["status"] == "stopped":
                    self.stopped.emit()
                    return
                elif res["status"] == "not_found":
                    self.finished.emit(None)
                    return
                elif res["status"] == "progress":
                    self.progress.emit(res["date"])
                else:
                    self.error.emit(res.get("message", "Unknown error"))
                    return
            except queue.Empty: continue

        handled = False
        while not self.result_queue.empty():
            try:
                res = self.result_queue.get_nowait()
                if res["status"] == "success":
                    self.finished.emit(res["result_jd_utc"])
                    handled = True; break
                elif res["status"] == "stopped":
                    self.stopped.emit()
                    handled = True; break
                elif res["status"] == "not_found":
                    self.finished.emit(None)
                    handled = True; break
                elif res["status"] == "progress":
                    self.progress.emit(res["date"])
                else:
                    self.error.emit(res.get("message", "Unknown error"))
                    handled = True; break
            except queue.Empty: break
        
        if not handled and not self.isInterruptionRequested():
            self.error.emit("Background search terminated unexpectedly.")

    def stop(self): self.requestInterruption()


# ==========================================
# 3. CHART RENDERER (ANIMATION ENGINE)
# ==========================================
class ChartRenderer(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(200, 200)
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
            "Sun": QColor("#FF8C00"),"Moon": QColor("#00FFFF"),"Mars": QColor("#FF0000"),"Mercury": QColor("#00FF00"),"Jupiter": QColor("#FFFF00"),
            "Venus": QColor("#FF00FF"),"Saturn": QColor("#0000FF"),"Rahu": QColor("#616A6B"),"Ketu": QColor("#8D6E63"),"Ascendant": QColor("#C0392B")
        }

        self.dark_colors = {
            "Sun": QColor("#C9A200"),"Moon": QColor("#39BFC0"),"Mars": QColor("#C31400"),"Mercury": QColor("#1FC76B"), "Jupiter": QColor("#D6D22A"), 
            "Venus": QColor("#C91AB1"),"Saturn": QColor("#2327B8"),"Rahu": QColor("#4B5253"),"Ketu": QColor("#6E564F"),"Ascendant": QColor("#8E2A21") 
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
        
        # Dynamically map the ascendant degree to the divisional longitude exclusively for circular chart proportionality
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
        
        # UI rendering bug isolated: Now grouping exactly by 'sign_index' mapped securely during the astro-engine step
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
                    # Increase vertical spacing between planets in the same house
                    spacing = 0.065 * h 
                    start_y = -((len(bodies) - 1) * spacing) / 2.0
                    hx, hy = animation.get_diamond_house_center(h_num, w, h)
                    py = hy + start_y + (idx * spacing)
                layout["planets"][b["name"]] = {"x": px + x, "y": py + y, "str": b["str"], "color_dark": b["color_dark"], "retro": b["retro"], "exalted": b["exalted"], "debilitated": b["debilitated"], "combust": b["combust"], "raw": b["raw"]}

        if self.show_aspects and self.use_tint and "aspects" in self.chart_data:
            for aspect in self.chart_data["aspects"]:
                if aspect["aspecting_planet"] in self.visible_aspect_planets and (aspect["aspecting_planet"] not in ["Rahu", "Ketu"] or self.show_rahu_ketu):
                    c = QColor(self.bright_colors.get(aspect["aspecting_planet"], QColor(200, 200, 200)))
                    c.setAlpha(30)
                    layout["tints"].append({"h2": aspect["target_house"], "color": c})
        return layout

    def paintEvent(self, event):
        self.hitboxes = []
        painter = QPainter(self); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#FFFFFF"))
        
        size = min(self.width(), self.height()) - 50 
        cx, cy = self.width() / 2, self.height() / 2
        x, y, w, h = cx - size / 2, cy - size / 2 + 10, size, size

        # Smart font bounding ensures fonts don't infinitely explode in single-chart view
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
                painter.drawPie(QRectF(x + 20, y + 20, w - 40, h - 40), int((((90 + (tint["h2"] - 1) * 30) % 360) - 15) * 16), int(30 * 16))
            else: painter.drawPolygon(self.house_polys[tint["h2"]])

        # ---------- DECORATIVE BORDERS ----------
        chart_cx = x + w / 2
        chart_cy = y + h / 2
        
        if getattr(self, "use_circular", False):
            outer_r = (w - 40) / 2
            painter.setPen(QPen(QColor("#DAA520"), 2))
            painter.drawEllipse(QPointF(chart_cx, chart_cy), outer_r + 4, outer_r + 4)
            painter.setPen(QPen(QColor("#8B4513"), 1.5))
            painter.drawEllipse(QPointF(chart_cx, chart_cy), outer_r + 8, outer_r + 8)
        else:
            painter.setPen(QPen(QColor("#DAA520"), 2)); painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(int(x - 4), int(y - 4), int(w + 8), int(h + 8))
            painter.setPen(QPen(QColor("#8B4513"), 1.5))
            painter.drawRect(int(x - 8), int(y - 8), int(w + 16), int(h + 16))
            
            # Corner accents
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
            # Rashi number text is 0.5 times the main planet text, lighter, and strictly non-bold
            planet_font_size = min(14, max(9, int(w * 0.035)))
            rashi_font_size = max(5, int(planet_font_size * 0.5))
            painter.setFont(QFont("Arial", rashi_font_size, QFont.Weight.Normal))
            painter.setPen(QColor("#000000"))
            painter.drawText(QRectF(z["x"] - 15, z["y"] - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, z["val"])

        for b in layout["planets"].values():
            # Clamped min 9, max 14 
            painter.setPen(b["color_dark"]); painter.setFont(QFont("Arial", min(14, max(9, int(w * 0.035))), QFont.Weight.Bold))
            p_rect = QRectF(b["x"] - 40, b["y"] - 10, 80, 20)
            painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, b["str"])
            self.hitboxes.append((p_rect, b["raw"]))
            
            fm = painter.fontMetrics()
            # Tighter bounds to prevent symbols from appearing too far from text
            text_width = fm.boundingRect(b["str"]).width()
            marker_x = b["x"] + text_width / 2.0 + 1
            
            # Center the symbols vertically at the exact same level as the main planet name
            t_y = b["y"] 
            
            g_s = min(5.0, max(2.0, w * 0.008)) 
            if b["retro"]:
                painter.setFont(QFont("Arial", min(9, max(6, int(w*0.022))), QFont.Weight.Bold))
                # Superscript 'R': shift baseline up
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
                
        if self.show_aspects and self.show_arrows and "aspects" in self.chart_data:
            for i, aspect in enumerate(self.chart_data["aspects"]):
                if aspect["aspecting_planet"] in self.visible_aspect_planets and (aspect["aspecting_planet"] not in ["Rahu", "Ketu"] or self.show_rahu_ketu):
                    p_v, h_v = layout["planets"].get(aspect["aspecting_planet"]), layout["houses"].get(aspect["target_house"])
                    if p_v and h_v:
                        c = QColor(self.bright_colors.get(aspect["aspecting_planet"], QColor(100, 100, 100)))
                        c.setAlpha(200)
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
            
            # --- HIGHER DIVISION SIGNIFICATOR LOGIC ---
            if getattr(self, 'd1_data', None) and "D1" not in self.title:
                chart_key = self.title.split()[0]
                div_meanings = {
                    "D9": {"d1_house": 7},
                    "D10": {"d1_house": 10},
                    "D20": {"d1_house": 9},
                    "D30": {"d1_house": 6},
                    "D60": {"d1_house": 1}
                }
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
                
                html = context_prefix + f"<b>{name}</b><hr style='margin: 4px 0;'/>Sign: {zodiac_names[p_raw['sign_index']]}<br>"
                if house != "-": html += f"House: {house}<br>"
                if status_list: html += f"Status: {', '.join(status_list)}<br>"
                if dignity_list: html += f"Dignity: {', '.join(dignity_list)}<br>"
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

        self.ephemeris = astro_engine.EphemerisEngine()
        self.time_ctrl = animation.TimeController()
        
        self.current_lat, self.current_lon, self.current_tz = 28.6139, 77.2090, "Asia/Kolkata"
        self.is_updating_ui = False
        self.is_loading_settings = True 
        self.is_chart_saved = True
        self.frozen_planets = {}
        
        self.renderers = {}
        self.div_titles = {
            "D1": "D1 (Rashi)", "D9": "D9 (Navamsha)", "D10": "D10 (Dashamsha)", 
            "D20": "D20 (Vimshamsha)", "D30": "D30 (Trimshamsha)", "D60": "D60 (Shashtiamsha)"
        }

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
            self.loc_status.setText(f"Lat: {self.current_lat:.2f}, Lon: {self.current_lon:.2f}\nTZ: {self.current_tz}")

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
                existing = glob.glob("tmp_*_saveon_*.json")
                num = len(existing) + 1
                filename = f"tmp_{num:03d}_saveon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                save_prefs.save_chart_to_file(filename, current_state)
                self.last_autosaved_state = current_state

    def _init_ui(self):
        central_widget = QWidget(); self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget); main_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Orientation.Horizontal); main_layout.addWidget(main_splitter)

        left_scroll = QScrollArea(); left_scroll.setWidgetResizable(True); left_scroll.setMinimumWidth(340)
        left_panel = QWidget(); left_layout = QVBoxLayout(left_panel)

        loc_group = QGroupBox("Location Settings"); loc_layout = QVBoxLayout()
        search_layout = QHBoxLayout()
        self.loc_input, self.loc_btn = QLineEdit("New Delhi, India"), QPushButton("Search")
        search_layout.addWidget(self.loc_input); search_layout.addWidget(self.loc_btn)
        self.loc_status = QLabel("Lat: 28.61, Lon: 77.21\nTZ: Asia/Kolkata")
        loc_layout.addLayout(search_layout); loc_layout.addWidget(self.loc_status); loc_group.setLayout(loc_layout)

        dt_group = QGroupBox("Date & Time"); dt_layout = QVBoxLayout()
        
        date_layout = QHBoxLayout()
        self.year_spin = QSpinBox(); self.year_spin.setRange(-9999, 9999); self.year_spin.setToolTip("Year (0 = 1 BCE, -1 = 2 BCE)")
        self.month_spin = QSpinBox(); self.month_spin.setRange(1, 12); self.month_spin.setToolTip("Month")
        self.day_spin = QSpinBox(); self.day_spin.setRange(1, 31); self.day_spin.setToolTip("Day")
        
        date_layout.addWidget(QLabel("Y:")); date_layout.addWidget(self.year_spin)
        date_layout.addWidget(QLabel("M:")); date_layout.addWidget(self.month_spin)
        date_layout.addWidget(QLabel("D:")); date_layout.addWidget(self.day_spin)

        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        
        dt_layout.addWidget(QLabel("Date:")); dt_layout.addLayout(date_layout)
        dt_layout.addWidget(QLabel("Time:")); dt_layout.addWidget(self.time_edit)
        dt_group.setLayout(dt_layout)
        
        div_group = QGroupBox("Divisional Charts")
        div_layout = QGridLayout()
        self.div_cbs = {}
        for i, (d_id, d_name) in enumerate(self.div_titles.items()):
            cb = QCheckBox(f"{d_id} ({d_name.split(' ')[1].replace('(','').replace(')','')})")
            if d_id == "D1": cb.setChecked(True)
            cb.stateChanged.connect(self.update_grid_layout)
            self.div_cbs[d_id] = cb
            div_layout.addWidget(cb, i // 2, i % 2)
        div_group.setLayout(div_layout)

        nav_group = QGroupBox("Time Animation"); nav_layout = QVBoxLayout()
        step_layout = QHBoxLayout()
        self.btn_sub_d, self.btn_sub_h, self.btn_sub_m = QPushButton("<< -1d"), QPushButton("< -1h"), QPushButton("< -1m")
        self.btn_add_m, self.btn_add_h, self.btn_add_d = QPushButton("+1m >"), QPushButton("+1h >"), QPushButton("+1d >>")
        for btn in [self.btn_sub_d, self.btn_sub_h, self.btn_sub_m, self.btn_add_m, self.btn_add_h, self.btn_add_d]: step_layout.addWidget(btn)
        
        btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.speed_combo = QComboBox(); self.speed_combo.addItems(["1x (Realtime)", "60x (1m/s)", "3600x (1h/s)", "7200x (2h/s)", "86400x (1d/s)", "604800x (1w/s)"])
        btn_layout.addWidget(self.btn_play); btn_layout.addWidget(self.speed_combo)
        nav_layout.addLayout(step_layout); nav_layout.addLayout(btn_layout); nav_group.setLayout(nav_layout)
        
        transit_group = QGroupBox("Transit Tools")
        transit_layout = QGridLayout(); transit_layout.setSpacing(4)
        
        transit_layout.addWidget(QLabel("Lagna:"), 0, 0)
        self.btn_prev_lagna, self.btn_next_lagna = QPushButton("< Prev"), QPushButton("Next >")
        transit_layout.addWidget(self.btn_prev_lagna, 0, 1); transit_layout.addWidget(self.btn_next_lagna, 0, 2)
        
        transit_layout.addWidget(QLabel("Planet:"), 1, 0)
        self.cb_transit_planet = QComboBox(); self.cb_transit_planet.addItems(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
        transit_layout.addWidget(self.cb_transit_planet, 1, 1, 1, 2)
        
        transit_layout.addWidget(QLabel("Rashi:"), 2, 0)
        self.cb_transit_rashi = QComboBox()
        self.cb_transit_rashi.addItems(["Any Rashi", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"])
        transit_layout.addWidget(self.cb_transit_rashi, 2, 1, 1, 2)

        transit_layout.addWidget(QLabel("Jump:"), 3, 0)
        self.btn_prev_rashi, self.btn_next_rashi = QPushButton("< Prev"), QPushButton("Next >")
        transit_layout.addWidget(self.btn_prev_rashi, 3, 1); transit_layout.addWidget(self.btn_next_rashi, 3, 2)

        self.btn_stop_transit = QPushButton("Stop Search")
        self.btn_stop_transit.setStyleSheet("color: red; font-weight: bold;"); self.btn_stop_transit.hide()
        transit_layout.addWidget(self.btn_stop_transit, 4, 0, 1, 3); transit_group.setLayout(transit_layout)

        set_group = QGroupBox("Chart Settings"); set_layout = QVBoxLayout()
        self.cb_ayanamsa = QComboBox(); self.cb_ayanamsa.addItems(["Lahiri", "Raman", "Fagan/Bradley"])
        
        self.chk_symbols = QCheckBox("Use Astro Symbols")
        self.chk_rahu, self.chk_arrows, self.chk_tint, self.chk_details, self.chk_circular = QCheckBox("Show Rahu/Ketu"), QCheckBox("Show Aspect Lines & Arrows"), QCheckBox("Use Aspect Tint"), QCheckBox("Show Details (Table)"), QCheckBox("Use Circular Chart Shape")
        self.chk_rahu.setChecked(True); self.chk_arrows.setChecked(True); self.chk_tint.setChecked(True); self.chk_details.setChecked(True); self.chk_circular.setChecked(False)
        self.chk_aspects = QCheckBox("Show Planetary Aspects (Drishti)")
        self.btn_save_chart, self.btn_load_chart, self.btn_export = QPushButton("Save Chart..."), QPushButton("Load Chart..."), QPushButton("Export PNG...")

        set_layout.addWidget(QLabel("Ayanamsa:")); set_layout.addWidget(self.cb_ayanamsa)
        for w in [self.chk_symbols, self.chk_rahu, self.chk_aspects, self.chk_arrows, self.chk_tint, self.chk_details, self.chk_circular]: set_layout.addWidget(w)
        file_btns = QHBoxLayout(); file_btns.addWidget(self.btn_save_chart); file_btns.addWidget(self.btn_load_chart)
        set_layout.addLayout(file_btns); set_layout.addWidget(self.btn_export); set_group.setLayout(set_layout)

        self.aspects_group = QGroupBox("Aspects From:")
        aspects_layout = QGridLayout(); self.aspect_cb = {}
        
        planets_data = [
            ("Sun", "#FF8C00"), ("Moon", "#00BCD4"), ("Mars", "#FF0000"), 
            ("Mercury", "#00C853"), ("Jupiter", "#FFD700"), ("Venus", "#FF1493"), 
            ("Saturn", "#0000CD"), ("Rahu", "#708090"), ("Ketu", "#8B4513")
        ]
        for i, (p, color) in enumerate(planets_data):
            cb = QCheckBox(p); cb.setStyleSheet(f"color: {color}; font-weight: bold;"); cb.setChecked(True); cb.stateChanged.connect(self.update_settings)
            self.aspect_cb[p] = cb; aspects_layout.addWidget(cb, i // 3, i % 3)
        self.aspects_group.setLayout(aspects_layout); self.aspects_group.setVisible(False)

        for g in [loc_group, dt_group, div_group, nav_group, transit_group, set_group, self.aspects_group]: left_layout.addWidget(g)
        left_layout.addStretch(); left_scroll.setWidget(left_panel)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.charts_container = QWidget()
        self.chart_layout = QGridLayout(self.charts_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_layout.setSpacing(10)
        right_splitter.addWidget(self.charts_container)
        
        table_container = QWidget()
        tc_layout = QVBoxLayout(table_container)
        tc_top = QHBoxLayout()
        tc_top.addWidget(QLabel("Explore Details For:"))
        self.table_view_cb = QComboBox()
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

        main_splitter.addWidget(left_scroll); main_splitter.addWidget(right_splitter); main_splitter.setSizes([350, 850])

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
            if item.widget():
                item.widget().setParent(None)
                
        cols = 3 if len(active_divs) >= 3 else len(active_divs)
        
        for i, div in enumerate(active_divs):
            row, col = i // cols, i % cols
            if div not in self.renderers:
                r = ChartRenderer()
                r.title = self.div_titles[div]
                self.renderers[div] = r
                
            self.chart_layout.addWidget(self.renderers[div], row, col)
            
        self.update_settings()

    def set_transit_buttons_enabled(self, enabled):
        for btn in [self.btn_prev_lagna, self.btn_next_lagna, self.btn_prev_rashi, self.btn_next_rashi]: btn.setEnabled(enabled)
        self.cb_transit_planet.setEnabled(enabled); self.cb_transit_rashi.setEnabled(enabled)
        if enabled: self.btn_stop_transit.hide()
        else: self.btn_stop_transit.setText("Stop (Initializing...)"); self.btn_stop_transit.show()

    def _connect_signals(self):
        self.loc_btn.clicked.connect(self.search_location); self.loc_input.returnPressed.connect(self.search_location)
        self.time_ctrl.time_changed.connect(self.on_time_changed)
        
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
        
        self.cb_ayanamsa.currentTextChanged.connect(self.update_settings)
        for chk in [self.chk_symbols, self.chk_rahu, self.chk_arrows, self.chk_tint, self.chk_circular]: chk.stateChanged.connect(self.update_settings)
        self.chk_aspects.stateChanged.connect(self.toggle_aspects); self.chk_details.stateChanged.connect(self.toggle_details)
        self.btn_save_chart.clicked.connect(self.save_chart_dialog); self.btn_load_chart.clicked.connect(self.load_chart_dialog)
        self.btn_export.clicked.connect(self.export_chart)

    def search_location(self):
        self.loc_btn.setEnabled(False); self.loc_btn.setText("Searching...")
        self.loc_worker = LocationWorker(self.loc_input.text())
        self.loc_worker.result_ready.connect(self.on_location_found)
        self.loc_worker.error_occurred.connect(self.on_location_error)
        self.loc_worker.start()

    def on_location_found(self, lat, lon, tz_name, name):
        self.current_lat, self.current_lon, self.current_tz = lat, lon, tz_name
        self.loc_status.setText(f"Lat: {lat:.2f}, Lon: {lon:.2f}\nTZ: {tz_name}")
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
        
        if body_name in self.frozen_planets:
            frozen_sign_name = zodiac_names[self.frozen_planets[body_name]]
            if target_sign == "Any Rashi" or target_sign != frozen_sign_name:
                ans = QMessageBox.question(self, "Unfreeze Required", f"'{body_name}' is currently frozen in {frozen_sign_name}.\nTo search for its next transit, it must be automatically unfrozen.\n\nUnfreeze {body_name} to proceed?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ans == QMessageBox.StandardButton.Yes: 
                    del self.frozen_planets[body_name]
                    self.recalculate() 
                else: 
                    return

        self.set_transit_buttons_enabled(False)
        params = {'dt': self.time_ctrl.current_time, 'lat': self.current_lat, 'lon': self.current_lon, 'tz_name': self.current_tz, 'body_name': body_name, 'direction': direction, 'target_sign_name': target_sign, 'frozen_planets': self.frozen_planets.copy(), 'ayanamsa': self.cb_ayanamsa.currentText()}

        self.transit_worker = TransitWorkerThread(params)
        self.transit_worker.finished.connect(lambda jd, d=direction: self.on_transit_finished(jd, d))
        self.transit_worker.error.connect(self.on_transit_error)
        self.transit_worker.stopped.connect(self.on_transit_stopped)
        self.transit_worker.progress.connect(self.on_transit_progress)
        self.transit_worker.start()

    def on_transit_progress(self, date_str): self.btn_stop_transit.setText(f"Stop Search (Scanning ~{date_str})")

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

    def change_speed(self): self.time_ctrl.set_speed([1.0, 60.0, 3600.0, 7200.0, 86400.0, 604800.0][self.speed_combo.currentIndex()])

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
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "", "JSON Files (*.json);;All Files (*)")
        if path and save_prefs.save_chart_to_file(path, self.get_current_chart_info()):
            self.is_chart_saved = True; QMessageBox.information(self, "Success", "Chart saved successfully.")

    def load_chart_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Chart", "", "JSON Files (*.json);;All Files (*)")
        if path:
            data = save_prefs.load_chart_from_file(path)
            if data:
                self.is_updating_ui = True; self.frozen_planets.clear()
                self.loc_input.setText(data.get("location", "New Delhi, India"))
                self.current_lat, self.current_lon, self.current_tz = data.get("lat", 28.6139), data.get("lon", 77.2090), data.get("tz", "Asia/Kolkata")
                self.loc_status.setText(f"Lat: {self.current_lat:.2f}, Lon: {self.current_lon:.2f}\nTZ: {self.current_tz}")
                
                if "datetime_dict" in data: self.time_ctrl.set_time(data["datetime_dict"])
                elif "datetime" in data:
                    try:
                        dt = datetime.datetime.fromisoformat(data["datetime"])
                        self.time_ctrl.set_time({'year': dt.year, 'month': dt.month, 'day': dt.day, 'hour': dt.hour, 'minute': dt.minute, 'second': dt.second})
                    except Exception as e: print(f"Error parsing date from file: {e}")
                
                self.is_updating_ui = False; self.save_settings(); self.recalculate(); self.is_chart_saved = True
            else: QMessageBox.warning(self, "Error", "Failed to load chart data.")

    def closeEvent(self, event):
        self.do_autosave()
        super().closeEvent(event)

    def export_chart(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "", "PNG Files (*.png);;All Files (*)")
        if path: self.charts_container.grab().save(path, "PNG")

    def recalculate(self):
        try:
            chart_data = self.ephemeris.calculate_chart(self.time_ctrl.current_time, self.current_lat, self.current_lon, self.current_tz)
            violation, violating_planet = False, None
            for p in chart_data["planets"]:
                if p["name"] in self.frozen_planets and p["sign_index"] != self.frozen_planets[p["name"]]:
                    violation = True; violating_planet = p["name"]; break
            if not violation and "Ascendant" in self.frozen_planets and chart_data["ascendant"]["sign_index"] != self.frozen_planets["Ascendant"]:
                violation = True; violating_planet = "Ascendant"
            
            if violation:
                zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                if hasattr(self, 'last_good_time'):
                    self.time_ctrl.set_time(dict(self.last_good_time))
                    if self.time_ctrl.is_playing: self.toggle_play()
                    if not getattr(self, "freeze_msg_shown", False):
                        self.freeze_msg_shown = True
                        QMessageBox.warning(self, "Freeze Boundary Reached", f"{violating_planet} is frozen in {zodiac_names[self.frozen_planets[violating_planet]]}. Cannot step further.")
                        QTimer.singleShot(1500, lambda: setattr(self, "freeze_msg_shown", False))
                    return
                    
            self.last_good_time = dict(self.time_ctrl.current_time)

            if "current_jd" in chart_data and "next_asc_jd" in chart_data and "prev_asc_jd" in chart_data:
                curr_jd, next_jd, prev_jd = chart_data["current_jd"], chart_data["next_asc_jd"], chart_data["prev_asc_jd"]
                diff_next_mins, diff_prev_mins = max(0, int((next_jd - curr_jd) * 1440)), max(0, int((curr_jd - prev_jd) * 1440))
                def fmt_time(m): return f"{m}m" if m < 60 else f"{m//60}h {m%60}m"
                self.btn_next_lagna.setText(f"Next >\n(in {fmt_time(diff_next_mins)})")
                self.btn_prev_lagna.setText(f"< Prev\n({fmt_time(diff_prev_mins)} ago)")

            # ALWAYS compute the table view chart even if not displayed on grid
            table_div = self.table_view_cb.currentData()
            if table_div == "D1":
                table_data = chart_data
            else:
                table_data = self.ephemeris.compute_divisional_chart(chart_data, table_div)
            self.update_table(table_data)

            for div, renderer in self.renderers.items():
                if renderer.parent() is not None:
                    div_data = self.ephemeris.compute_divisional_chart(chart_data, div) if div != "D1" else chart_data
                    renderer.update_chart(div_data, chart_data)  # Pass the base D1 chart in for Tooltip Logic!
                        
            if not self.is_loading_settings: self.is_chart_saved = False
        except Exception as e: print(f"Calculation Error: {e}")

    def toggle_freeze(self, name, sign_idx, checked):
        if checked: self.frozen_planets[name] = sign_idx
        elif name in self.frozen_planets: del self.frozen_planets[name]

    def update_table(self, chart_data):
        self.table.setRowCount(0)
        is_d1 = (self.table_view_cb.currentData() == "D1")
        
        self.table.setColumnCount(6 if is_d1 else 5)
        headers = ["Planet", "Sign", "Degree", "House", "Retrograde"]
        if is_d1: headers.append("Freeze D1 Rashi")
        self.table.setHorizontalHeaderLabels(headers)
        
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        asc = chart_data["ascendant"]
        
        def add_freeze_cb(row, name, sign_idx):
            cb = QCheckBox(f"Freeze in {zodiac_names[sign_idx]}")
            cb.setChecked(name in self.frozen_planets)
            cb.toggled.connect(lambda checked, n=name, s=sign_idx: self.toggle_freeze(n, s, checked))
            w = QWidget(); l = QHBoxLayout(w); l.addWidget(cb); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(row, 5, w)

        def make_name(name_str, is_vargottama):
            return f"{name_str} ★" if is_vargottama and not is_d1 else name_str
            
        self.table.insertRow(0)
        self.table.setItem(0, 0, QTableWidgetItem(make_name("Ascendant", asc.get("vargottama", False))))
        self.table.setItem(0, 1, QTableWidgetItem(zodiac_names[asc["sign_index"]]))
        self.table.setItem(0, 2, QTableWidgetItem(f"{asc['degree'] % 30:.2f}°"))
        self.table.setItem(0, 3, QTableWidgetItem("1")); self.table.setItem(0, 4, QTableWidgetItem("-"))
        if is_d1: add_freeze_cb(0, "Ascendant", asc["sign_index"])

        for i, p in enumerate(chart_data["planets"]):
            row = i + 1
            if p["name"] in ["Rahu", "Ketu"] and not self.chk_rahu.isChecked(): continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(make_name(p["name"], p.get("vargottama", False))))
            self.table.setItem(row, 1, QTableWidgetItem(zodiac_names[p["sign_index"]]))
            self.table.setItem(row, 2, QTableWidgetItem(f"{p['deg_in_sign']:.2f}°"))
            self.table.setItem(row, 3, QTableWidgetItem(str(p["house"])))
            self.table.setItem(row, 4, QTableWidgetItem("Yes" if p["retro"] else "No"))
            if is_d1: add_freeze_cb(row, p["name"], p["sign_index"])

GLOBAL_FONT_FAMILY, GLOBAL_FONT_SCALE, GLOBAL_PRIMARY_COLOR = "Segoe UI", 11, "#4A90E2" 

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    app.setFont(QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SCALE)); app.setStyle("Fusion")
    app.setStyleSheet(f"QGroupBox::title {{ color: {GLOBAL_PRIMARY_COLOR}; font-weight: bold; }} QPushButton {{ padding: 4px 8px; }} QPushButton:checked {{ background-color: {GLOBAL_PRIMARY_COLOR}; color: white; }}")
    window = AstroApp(); window.show(); sys.exit(app.exec())