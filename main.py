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

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QDateEdit, QTimeEdit, 
                             QTableWidget, QTableWidgetItem, QCheckBox,
                             QHeaderView, QMessageBox, QGroupBox, QFileDialog,
                             QScrollArea, QGridLayout)
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
    """
    Runs location geocoding and timezone resolution in a background thread
    to prevent the GUI from freezing.
    """
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
                lat = location.latitude
                lon = location.longitude
                formatted_name = location.address
                
                tf = TimezoneFinder()
                tz_name = tf.timezone_at(lng=lon, lat=lat)
                if not tz_name: tz_name = "UTC"
                    
                self.result_ready.emit(lat, lon, tz_name, formatted_name)
            else:
                self.error_occurred.emit("Location not found.")
        except Exception as e:
            self.error_occurred.emit(f"Network or Geocoding Error: {str(e)}")


# ==========================================
# 2. TRANSIT WORKER THREAD
# ==========================================
class TransitWorkerThread(QThread):
    """Bridges PyQt thread with Python MultiProcessing to keep the GUI fluid."""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    stopped = pyqtSignal()
    progress = pyqtSignal(str) # Emits live dates during deep searches

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
                if self.process.is_alive():
                    self.process.terminate()
                self.stopped.emit()
                return
            
            try:
                res = self.result_queue.get(timeout=0.1)
                if res["status"] == "success":
                    self.finished.emit(datetime.datetime.fromisoformat(res["result"]))
                    return
                elif res["status"] == "stopped":
                    self.stopped.emit()
                    return
                elif res["status"] == "not_found":
                    self.finished.emit(None)
                    return
                elif res["status"] == "progress":
                    self.progress.emit(res["date"])
                    # Continue looping cleanly, do not return yet!
                else:
                    self.error.emit(res.get("message", "Unknown error"))
                    return
            except queue.Empty:
                continue

        # Safely catch silent OS/Memory process deaths and clear lingering queues
        handled = False
        while not self.result_queue.empty():
            try:
                res = self.result_queue.get_nowait()
                if res["status"] == "success":
                    self.finished.emit(datetime.datetime.fromisoformat(res["result"]))
                    handled = True
                    break
                elif res["status"] == "stopped":
                    self.stopped.emit()
                    handled = True
                    break
                elif res["status"] == "not_found":
                    self.finished.emit(None)
                    handled = True
                    break
                elif res["status"] == "progress":
                    self.progress.emit(res["date"])
                else:
                    self.error.emit(res.get("message", "Unknown error"))
                    handled = True
                    break
            except queue.Empty:
                break
        
        # If the background process dropped dead silently without telling us anything:
        if not handled and not self.isInterruptionRequested():
            self.error.emit("Background search terminated unexpectedly.")

    def stop(self):
        self.requestInterruption()


# ==========================================
# 3. CHART RENDERER (ANIMATION ENGINE)
# ==========================================
class ChartRenderer(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)
        self.hitboxes = []
        self.house_polys = {}
        self.chart_data = None
        
        self.use_symbols = False
        self.show_rahu_ketu = True
        self.highlight_asc_moon = True
        self.show_aspects = False
        self.show_arrows = True
        self.use_tint = True
        self.use_circular = False
        self.visible_aspect_planets = set()

        self.tooltip_label = QLabel(self)
        self.tooltip_label.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""
            QLabel { background-color: #FDFDFD; color: #222222; border: 1px solid #BBBBBB; padding: 6px; font-size: 13px; }
        """)
        self.tooltip_label.hide()

        self.unicode_syms = {
            "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿", "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋"
        }
        self.bright_colors = {
            "Sun": QColor("#FFAA00"), "Moon": QColor("#0066CC"), "Mars": QColor("#CC0000"),
            "Mercury": QColor("#009900"), "Jupiter": QColor("#B8860B"), "Venus": QColor("#CC00CC"),
            "Saturn": QColor("#6600CC"), "Rahu": QColor("#666666"), "Ketu": QColor("#666666"), "Ascendant": QColor("#C0392B")
        }

        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_duration = 500.0 
        self.anim_start_time = 0
        self.source_layout = None
        self.target_layout = None
        self.current_layout = None
        self.data_changed_flag = False

    def _get_house_polygon(self, h_num, x, y, w, h):
        p_tl = QPointF(x, y); p_tr = QPointF(x+w, y); p_bl = QPointF(x, y+h); p_br = QPointF(x+w, y+h)
        p_tc = QPointF(x+w/2, y); p_bc = QPointF(x+w/2, y+h); p_lc = QPointF(x, y+h/2); p_rc = QPointF(x+w, y+h/2)
        p_cc = QPointF(x+w/2, y+h/2)
        p_i_tl = QPointF(x+w/4, y+h/4); p_i_tr = QPointF(x+3*w/4, y+h/4)
        p_i_bl = QPointF(x+w/4, y+3*h/4); p_i_br = QPointF(x+3*w/4, y+3*h/4)

        polys = {
            1: [p_tc, p_i_tr, p_cc, p_i_tl], 2: [p_tl, p_tc, p_i_tl], 3: [p_tl, p_i_tl, p_lc],
            4: [p_lc, p_i_tl, p_cc, p_i_bl], 5: [p_lc, p_i_bl, p_bl], 6: [p_i_bl, p_bc, p_bl],
            7: [p_cc, p_i_br, p_bc, p_i_bl], 8: [p_bc, p_i_br, p_br], 9: [p_i_br, p_rc, p_br],
            10: [p_i_tr, p_rc, p_i_br, p_cc], 11: [p_tr, p_rc, p_i_tr], 12: [p_tc, p_tr, p_i_tr]
        }
        return QPolygonF(polys[h_num])

    def update_chart(self, data):
        self.chart_data = data
        self.data_changed_flag = True
        self.update()

        if self.tooltip_label.isVisible():
            self._update_tooltip(self.mapFromGlobal(QCursor.pos()))

    def _on_anim_tick(self):
        elapsed = time.time() * 1000 - self.anim_start_time
        t = elapsed / self.anim_duration
        if t >= 1.0:
            t = 1.0
            self.anim_timer.stop()
            self.current_layout = self.target_layout
            self.update()
        else:
            self.current_layout = self._lerp_layout(self.source_layout, self.target_layout, t)
            self.update()
        
        if self.tooltip_label.isVisible():
            self._update_tooltip(self.mapFromGlobal(QCursor.pos()))

    def _lerp_layout(self, src, tgt, t):
        if getattr(self, "use_circular", False):
            e = 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2
        else:
            e = t
            
        cur = {"zodiacs": {}, "planets": {}, "houses": {}, "tints": []}
        
        for k, t_v in tgt["zodiacs"].items():
            s_v = src["zodiacs"].get(k, t_v)
            cur["zodiacs"][k] = {"x": s_v["x"] + (t_v["x"] - s_v["x"]) * e, "y": s_v["y"] + (t_v["y"] - s_v["y"]) * e, "val": t_v["val"]}
            
        for k, t_v in tgt["houses"].items():
            s_v = src["houses"].get(k, t_v)
            cur["houses"][k] = {"x": s_v["x"] + (t_v["x"] - s_v["x"]) * e, "y": s_v["y"] + (t_v["y"] - s_v["y"]) * e}
            
        for k, t_v in tgt["planets"].items():
            s_v = src["planets"].get(k, t_v)
            cur["planets"][k] = {
                "x": s_v["x"] + (t_v["x"] - s_v["x"]) * e, "y": s_v["y"] + (t_v["y"] - s_v["y"]) * e,
                "str": t_v["str"], "color": t_v["color"], "retro": t_v["retro"],
                "exalted": t_v["exalted"], "debilitated": t_v["debilitated"],
                "combust": t_v["combust"], "raw": t_v["raw"]
            }

        tgt_tints_pool = list(tgt.get("tints", []))
        for s_tint in src.get("tints", []):
            match_idx = -1
            for i, t_tint in enumerate(tgt_tints_pool):
                if s_tint["h2"] == t_tint["h2"] and s_tint["color"].rgba() == t_tint["color"].rgba():
                    match_idx = i
                    break
            
            if match_idx != -1:
                cur["tints"].append(s_tint)
                tgt_tints_pool.pop(match_idx)
            else:
                c = QColor(s_tint["color"])
                c.setAlpha(int(c.alpha() * (1.0 - e)))
                cur["tints"].append({"h2": s_tint["h2"], "color": c})
                
        for t_tint in tgt_tints_pool:
            c = QColor(t_tint["color"])
            c.setAlpha(int(c.alpha() * e))
            cur["tints"].append({"h2": t_tint["h2"], "color": c})
            
        return cur

    def _compute_layout(self, x, y, w, h):
        layout = {"zodiacs": {}, "planets": {}, "houses": {}, "tints": []}
        if not self.chart_data: return layout

        asc_deg = self.chart_data["ascendant"]["degree"]
        asc_sign = self.chart_data["ascendant"]["sign_num"]

        for h_num in range(1, 13):
            sign_num = (asc_sign + h_num - 2) % 12 + 1
            sign_lon = (sign_num - 1) * 30.0 + 15.0
            
            if getattr(self, "use_circular", False):
                zx, zy = animation.get_circular_coords(sign_lon, asc_deg, -3, w, h)
                hx, hy = animation.get_circular_coords(sign_lon, asc_deg, -4, w, h)
            else:
                zx, zy = animation.get_diamond_zodiac_coords(h_num, w, h)
                hx, hy = animation.get_diamond_house_center(h_num, w, h)
            
            layout["zodiacs"][sign_num] = {"x": zx + x, "y": zy + y, "val": str(sign_num)}
            layout["houses"][h_num] = {"x": hx + x, "y": hy + y}

        all_bodies = []
        
        if self.highlight_asc_moon:
            all_bodies.append({
                "name": "Ascendant", "str": "Asc", "color": self.bright_colors["Ascendant"], 
                "lon": asc_deg, "retro": False, "exalted": False, "debilitated": False, "combust": False,
                "raw": {"name": "Ascendant", "sign_index": self.chart_data["ascendant"]["sign_index"], "deg_in_sign": self.chart_data["ascendant"]["degree"] % 30, "retro": False, "combust": False, "house": 1}
            })

        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"] and not self.show_rahu_ketu: continue
            display_str = self.unicode_syms[p["name"]] if self.use_symbols else p["sym"]
            all_bodies.append({"name": p["name"], "str": display_str, "color": self.bright_colors.get(p["name"], QColor("#000000")), "lon": p["lon"], "retro": p["retro"], "exalted": p.get("exalted", False), "debilitated": p.get("debilitated", False), "combust": p.get("combust", False), "raw": p})

        bodies_by_house = {i: [] for i in range(1, 13)}
        asc_sign_idx = int(asc_deg / 30.0)
        
        for b in all_bodies:
            p_sign = int(b["lon"] / 30.0)
            h_num = ((p_sign - asc_sign_idx) % 12) + 1
            bodies_by_house[h_num].append(b)

        LANE_ORDER = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4, "Venus": 5, "Saturn": 6, "Rahu": 7, "Ketu": 8, "Ascendant": 9}

        for h_num, bodies in bodies_by_house.items():
            for idx, b in enumerate(bodies):
                if getattr(self, "use_circular", False):
                    lane_idx = LANE_ORDER.get(b["name"], 4.5)
                    px, py = animation.get_circular_coords(b["lon"], asc_deg, lane_idx, w, h)
                else:
                    px, py = animation.get_diamond_planet_coords(h_num, idx, len(bodies), w, h)
                
                layout["planets"][b["name"]] = {
                    "x": px + x, "y": py + y,
                    "str": b["str"], "color": b["color"], "retro": b["retro"],
                    "exalted": b["exalted"], "debilitated": b["debilitated"],
                    "combust": b["combust"], "raw": b["raw"]
                }

        if self.show_aspects and self.use_tint and "aspects" in self.chart_data:
            color_map = {"orange": QColor(255, 165, 0, 20), "blue": QColor(50, 150, 255, 20), "red": QColor(255, 50, 50, 20), "green": QColor(50, 255, 50, 20),
                         "yellow": QColor(200, 180, 0, 20), "pink": QColor(255, 105, 180, 20), "purple": QColor(160, 32, 240, 20), "gray": QColor(150, 150, 150, 20)}
            for aspect in self.chart_data["aspects"]:
                p_name = aspect["aspecting_planet"]
                if p_name not in self.visible_aspect_planets or (p_name in ["Rahu", "Ketu"] and not self.show_rahu_ketu): continue
                layout["tints"].append({"h2": aspect["target_house"], "color": color_map.get(aspect["color"], QColor(255, 255, 255, 20))})

        return layout

    def paintEvent(self, event):
        self.hitboxes = []
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color, line_color, text_color = QColor("#FFFFFF"), QColor("#222222"), QColor("#000000")

        painter.fillRect(self.rect(), bg_color)
        size = min(self.width(), self.height()) - 40
        cx, cy = self.width() / 2, self.height() / 2
        x, y, w, h = cx - size / 2, cy - size / 2, size, size

        self.house_polys.clear()
        for h_num in range(1, 13):
            self.house_polys[h_num] = self._get_house_polygon(h_num, x, y, w, h)

        new_target_layout = self._compute_layout(x, y, w, h)
        
        if self.data_changed_flag:
            self.data_changed_flag = False
            if self.current_layout is None:
                self.source_layout = new_target_layout
                self.target_layout = new_target_layout
                self.current_layout = new_target_layout
            else:
                self.source_layout = self.current_layout
                self.target_layout = new_target_layout
                self.anim_start_time = time.time() * 1000
                self.anim_timer.start(16)
        else:
            self.target_layout = new_target_layout
            if not self.anim_timer.isActive():
                self.source_layout = new_target_layout
                self.current_layout = new_target_layout

        layout = self.current_layout
        if not layout:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Chart Data")
            return

        for tint in layout["tints"]:
            painter.setBrush(QBrush(tint["color"]))
            painter.setPen(Qt.PenStyle.NoPen)
            if getattr(self, "use_circular", False):
                margin = 20
                rect = QRectF(x + margin, y + margin, w - 2*margin, h - 2*margin)
                center_angle = (90 + (tint["h2"] - 1) * 30) % 360
                painter.drawPie(rect, int((center_angle - 15) * 16), int(30 * 16))
            else:
                painter.drawPolygon(self.house_polys[tint["h2"]])

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(line_color, 2))

        if getattr(self, "use_circular", False):
            margin = 20
            inner_r = w * 0.15
            painter.drawEllipse(QRectF(x + margin, y + margin, w - 2*margin, h - 2*margin))
            painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r*2, inner_r*2))
            for i in range(12):
                angle = math.radians(i * 30 + 15)
                r_out = (w - 2*margin) / 2
                painter.drawLine(int(cx + inner_r * math.cos(angle)), int(cy - inner_r * math.sin(angle)), int(cx + r_out * math.cos(angle)), int(cy - r_out * math.sin(angle)))
        else:
            painter.drawRect(int(x), int(y), int(w), int(h))
            painter.drawLine(int(x), int(y), int(x + w), int(y + h))
            painter.drawLine(int(x + w), int(y), int(x), int(y + h))
            painter.drawLine(int(x + w/2), int(y), int(x + w), int(y + h/2))
            painter.drawLine(int(x + w), int(y + h/2), int(x + w/2), int(y + h))
            painter.drawLine(int(x + w/2), int(y + h), int(x), int(y + h/2))
            painter.drawLine(int(x), int(y + h/2), int(x + w/2), int(y))

        for z in layout["zodiacs"].values():
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.setPen(QColor("#777777"))
            painter.drawText(QRectF(z["x"] - 15, z["y"] - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, z["val"])

        for b in layout["planets"].values():
            painter.setPen(b["color"])
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            p_rect = QRectF(b["x"] - 40, b["y"] - 10, 80, 20)
            painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, b["str"])
            
            self.hitboxes.append((p_rect, b["raw"]))
            
            fm = painter.fontMetrics()
            marker_x = b["x"] + fm.horizontalAdvance(b["str"]) / 2 + 2
            
            if b["retro"]:
                painter.setFont(QFont("Arial", 7, QFont.Weight.Bold))
                painter.drawText(int(marker_x), int(b["y"] + 5), "R")
                marker_x += fm.horizontalAdvance("R") + 2
                
            t_y = b["y"] + 8
            if b["exalted"]:
                painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(0, 180, 0))
                painter.drawPolygon(QPolygonF([QPointF(marker_x, t_y+3), QPointF(marker_x+6, t_y+3), QPointF(marker_x+3, t_y-4)]))
                marker_x += 8
            elif b["debilitated"]:
                painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(220, 0, 0))
                painter.drawPolygon(QPolygonF([QPointF(marker_x, t_y-3), QPointF(marker_x+6, t_y-3), QPointF(marker_x+3, t_y+4)]))
                marker_x += 8
                
            if b["combust"]:
                painter.setPen(Qt.PenStyle.NoPen); painter.setBrush(QColor(255, 140, 0))
                painter.drawPolygon(QPolygonF([QPointF(marker_x+4, t_y-5), QPointF(marker_x+8, t_y+2), QPointF(marker_x+4, t_y+6), QPointF(marker_x, t_y+2)]))
                painter.setBrush(QColor(255, 220, 0))
                painter.drawPolygon(QPolygonF([QPointF(marker_x+4, t_y-1), QPointF(marker_x+6, t_y+3), QPointF(marker_x+4, t_y+5), QPointF(marker_x+2, t_y+3)]))
                
            painter.setBrush(Qt.BrushStyle.NoBrush)
                
        if self.show_aspects: self._draw_aspects(painter, layout)

    def _draw_aspect_line(self, painter, x1, y1, x2, y2, color_name, offset_idx=0):
        color_map = {"orange": QColor(255, 165, 0, 160), "blue": QColor(50, 150, 255, 160), "red": QColor(255, 50, 50, 160), "green": QColor(50, 255, 50, 160),
                     "yellow": QColor(200, 180, 0, 180), "pink": QColor(255, 105, 180, 160), "purple": QColor(160, 32, 240, 160), "gray": QColor(150, 150, 160, 160)}
        color = color_map.get(color_name, QColor(255, 255, 255, 160))
            
        ox, oy = (offset_idx % 3 - 1) * 4, ((offset_idx + 1) % 3 - 1) * 4
        x1 += ox; y1 += oy; x2 += ox; y2 += oy
            
        dx, dy = x2 - x1, y2 - y1
        dist = math.hypot(dx, dy)
        if dist < 70: return
        
        sx, sy = x1 + (dx/dist) * 35, y1 + (dy/dist) * 35
        ex, ey = x2 - (dx/dist) * 35, y2 - (dy/dist) * 35
        
        painter.setPen(QPen(color, 2.0, Qt.PenStyle.SolidLine))
        painter.drawLine(int(sx), int(sy), int(ex), int(ey))
        
        if self.show_arrows:
            angle = math.atan2(ey - sy, ex - sx)
            p1_x, p1_y = ex - 9 * math.cos(angle - math.pi / 6), ey - 9 * math.sin(angle - math.pi / 6)
            p2_x, p2_y = ex - 9 * math.cos(angle + math.pi / 6), ey - 9 * math.sin(angle + math.pi / 6)
            painter.setBrush(QBrush(color)); painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPolygon(QPolygonF([QPointF(ex, ey), QPointF(p1_x, p1_y), QPointF(p2_x, p2_y)]))

    def _draw_aspects(self, painter, layout):
        if not self.show_arrows or "aspects" not in self.chart_data: return
            
        for i, aspect in enumerate(self.chart_data["aspects"]):
            p_name = aspect["aspecting_planet"]
            if p_name not in self.visible_aspect_planets or (p_name in ["Rahu", "Ketu"] and not self.show_rahu_ketu): continue
            
            p_visual = layout["planets"].get(p_name)
            h_visual = layout["houses"].get(aspect["target_house"])
            
            if p_visual and h_visual:
                self._draw_aspect_line(painter, p_visual["x"], p_visual["y"], h_visual["x"], h_visual["y"], aspect["color"], offset_idx=i)

    def mouseMoveEvent(self, event):
        self._update_tooltip(event.position())

    def _update_tooltip(self, pos):
        if not self.chart_data or not self.current_layout:
            if self.tooltip_label.isVisible(): self.tooltip_label.hide()
            return
            
        tooltip_html = ""
        pos_point = QPointF(pos.x(), pos.y())
        
        def ordinal(n): return str(n) + ('th' if 11 <= (n % 100) <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        for rect, p_raw in self.hitboxes:
            if rect.contains(pos_point):
                name, house = p_raw["name"], p_raw.get("house", "-")
                status_list = ["Retrograde"] if name in ["Rahu", "Ketu"] or (p_raw.get("retro") and name != "Ascendant") else (["Direct"] if name != "Ascendant" else [])
                if p_raw.get("combust"): status_list.append("Combust")
                
                dignity_list = [d for d, k in zip(["Exalted", "Debilitated", "Own Sign"], ["exalted", "debilitated", "own_sign"]) if p_raw.get(k)]
                deg, mins = int(p_raw["deg_in_sign"]), int((p_raw["deg_in_sign"] - int(p_raw["deg_in_sign"])) * 60)
                
                html = f"<b>{name}</b><hr style='margin: 4px 0;'/>Sign: {zodiac_names[p_raw['sign_index']]}<br>"
                if house != "-": html += f"House: {house}<br>"
                if status_list: html += f"Status: {', '.join(status_list)}<br>"
                if dignity_list: html += f"Dignity: {', '.join(dignity_list)}<br>"
                tooltip_html = html + f"Longitude: {deg}°{mins:02d}'"
                break
                
        if not tooltip_html:
            size = min(self.width(), self.height()) - 40
            x, y, w, h = self.width() / 2 - size / 2, self.height() / 2 - size / 2, size, size
            
            for h_num in range(1, 13):
                is_hovered = False
                if getattr(self, "use_circular", False):
                    dx, dy = pos.x() - (x + w/2), pos.y() - (y + h/2)
                    if (w * 0.15) <= math.hypot(dx, dy) <= ((w - 40) / 2):
                        angle = math.degrees(math.atan2(-dy, dx)) % 360
                        if abs((angle - ((90 + (h_num - 1) * 30) % 360) + 180) % 360 - 180) <= 15: is_hovered = True
                elif h_num in self.house_polys and self.house_polys[h_num].containsPoint(pos_point, Qt.FillRule.OddEvenFill):
                    is_hovered = True

                if is_hovered:
                    sign_in_house = (self.chart_data["ascendant"]["sign_index"] + h_num - 1) % 12 + 1
                    html = f"<b>{ordinal(h_num)} House</b>" + (" <b style='color: red;'>NOT preferred</b>" if sign_in_house in {10, 12, 8, 2, 3} else "") + "<hr style='margin: 4px 0;'/>"
                    
                    lord_name = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}.get(sign_in_house)
                    lord_p = next((p for p in self.chart_data["planets"] if p["name"] == lord_name), None)
                    
                    if lord_p:
                        l_status = [s for s, k in zip(["combust", "retrograde", "exalted", "debilitated"], ["combust", "retro", "exalted", "debilitated"]) if lord_p.get(k) and (k != "retro" or lord_name not in ["Rahu", "Ketu"])]
                        html += f"=&gt; lord ({lord_name}{', ' + ', '.join(l_status) if l_status else ''}) in {ordinal(lord_p['house'])} house"

                    aspects = [a["aspecting_planet"] for a in self.chart_data.get("aspects", []) if a["target_house"] == h_num]
                    if aspects:
                        html += f"<br><br>Aspected by:<br><br>"
                        blocks = []
                        for ap_name in aspects:
                            ap_p = next((p for p in self.chart_data["planets"] if p["name"] == ap_name), None)
                            if ap_p:
                                ap_st = [s for s, k in zip(["Combust", "Retrograde", "Retrograde", "Exalted", "Debilitated", "Own Sign"], ["combust", "retro", "r_k", "exalted", "debilitated", "own_sign"]) if (ap_p.get(k) and ap_name not in ["Rahu", "Ketu"]) or (k == "r_k" and ap_name in ["Rahu", "Ketu"])]
                                block = f"-&gt; <b>{ap_name}</b>" + (f" ({', '.join(ap_st)})" if ap_st else "")
                                lords = ap_p.get("lord_of", [])
                                if lords: block += f"<br><span style='color: #555;'>{' AND '.join([f'{ordinal(l)} house lord' for l in lords])}</span>"
                                blocks.append(block)
                        html += "<br><br>".join(blocks)
                    tooltip_html = html; break
                
        if tooltip_html:
            if self.tooltip_label.text() != tooltip_html: self.tooltip_label.setText(tooltip_html); self.tooltip_label.adjustSize()
            
            screen = self.screen().availableGeometry() if self.screen() else QApplication.primaryScreen().availableGeometry()
            global_pos = self.mapToGlobal(pos.toPoint() if hasattr(pos, 'toPoint') else pos)
            l_w, l_h = self.tooltip_label.width(), self.tooltip_label.height()
            t_x, t_y = global_pos.x() + 15, global_pos.y() + 15
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
        self.setWindowTitle("Vedic Astrology Diamond Chart Pro")
        self.resize(1150, 750)

        self.ephemeris = astro_engine.EphemerisEngine()
        self.time_ctrl = animation.TimeController()
        
        self.current_lat, self.current_lon, self.current_tz = 28.6139, 77.2090, "Asia/Kolkata"
        self.is_updating_ui = False
        self.is_loading_settings = True 
        self.is_chart_saved = True
        self.frozen_planets = {}

        self._init_ui()
        self._connect_signals()
        self.load_settings()
        self.is_loading_settings = False
        
        self.time_ctrl.set_time(datetime.datetime.now())

    def load_settings(self):
        settings_file = "astro_settings.json"
        if not os.path.exists(settings_file): return
            
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
                        
            self.update_settings()
            self.toggle_details()
        except Exception as e: print(f"Failed to load settings: {e}")

    def save_settings(self):
        if getattr(self, 'is_loading_settings', True): return
        
        prefs = {
            "location": self.loc_input.text(), "lat": self.current_lat, "lon": self.current_lon, "tz": self.current_tz,
            "ayanamsa": self.cb_ayanamsa.currentText(), "use_symbols": self.chk_symbols.isChecked(),
            "show_rahu_ketu": self.chk_rahu.isChecked(), "show_arrows": self.chk_arrows.isChecked(),
            "use_tint": self.chk_tint.isChecked(), "show_aspects": self.chk_aspects.isChecked(),
            "show_details": self.chk_details.isChecked(), "use_circular": self.chk_circular.isChecked(),
            "aspect_planets": {p: cb.isChecked() for p, cb in self.aspect_cb.items()}
        }
        try:
            with open("astro_settings.json", "w") as f: json.dump(prefs, f, indent=4)
        except Exception as e: print(f"Failed to save settings: {e}")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(340)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        loc_group = QGroupBox("Location Settings"); loc_layout = QVBoxLayout()
        search_layout = QHBoxLayout()
        self.loc_input = QLineEdit("New Delhi, India"); self.loc_btn = QPushButton("Search")
        search_layout.addWidget(self.loc_input); search_layout.addWidget(self.loc_btn)
        self.loc_status = QLabel("Lat: 28.61, Lon: 77.21\nTZ: Asia/Kolkata")
        loc_layout.addLayout(search_layout); loc_layout.addWidget(self.loc_status); loc_group.setLayout(loc_layout)

        dt_group = QGroupBox("Date & Time"); dt_layout = QVBoxLayout()
        self.date_edit = QDateEdit(); self.date_edit.setCalendarPopup(True)
        self.time_edit = QTimeEdit(); self.time_edit.setDisplayFormat("HH:mm:ss")
        self.date_edit.setDateRange(QDate(-9999, 1, 1), QDate(9999, 12, 31))
        self.date_edit.setMinimumDate(QDate(-4712, 1, 1))
        self.date_edit.setMaximumDate(QDate(9999, 12, 31))
        dt_layout.addWidget(QLabel("Date:")); dt_layout.addWidget(self.date_edit)
        dt_layout.addWidget(QLabel("Time:")); dt_layout.addWidget(self.time_edit)
        dt_group.setLayout(dt_layout)

        nav_group = QGroupBox("Time Animation"); nav_layout = QVBoxLayout()
        step_layout = QHBoxLayout()
        self.btn_sub_d = QPushButton("<< -1d"); self.btn_sub_h = QPushButton("< -1h"); self.btn_sub_m = QPushButton("< -1m")
        self.btn_add_m = QPushButton("+1m >"); self.btn_add_h = QPushButton("+1h >"); self.btn_add_d = QPushButton("+1d >>")
        for btn in [self.btn_sub_d, self.btn_sub_h, self.btn_sub_m, self.btn_add_m, self.btn_add_h, self.btn_add_d]: step_layout.addWidget(btn)
        
        btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        self.speed_combo = QComboBox(); self.speed_combo.addItems(["1x (Realtime)", "60x (1m/s)", "3600x (1h/s)", "7200x (2h/s)", "86400x (1d/s)", "604800x (1w/s)"])
        btn_layout.addWidget(self.btn_play); btn_layout.addWidget(self.speed_combo)

        nav_layout.addLayout(step_layout); nav_layout.addLayout(btn_layout); nav_group.setLayout(nav_layout)
        
        transit_group = QGroupBox("Transit Tools")
        transit_layout = QGridLayout()
        transit_layout.setSpacing(4)
        
        transit_layout.addWidget(QLabel("Lagna:"), 0, 0)
        self.btn_prev_lagna = QPushButton("< Prev")
        self.btn_next_lagna = QPushButton("Next >")
        transit_layout.addWidget(self.btn_prev_lagna, 0, 1)
        transit_layout.addWidget(self.btn_next_lagna, 0, 2)
        
        transit_layout.addWidget(QLabel("Planet:"), 1, 0)
        self.cb_transit_planet = QComboBox()
        self.cb_transit_planet.addItems(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
        transit_layout.addWidget(self.cb_transit_planet, 1, 1, 1, 2)
        
        transit_layout.addWidget(QLabel("Rashi:"), 2, 0)
        self.cb_transit_rashi = QComboBox()
        self.cb_transit_rashi.addItems(["Any Rashi", "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"])
        transit_layout.addWidget(self.cb_transit_rashi, 2, 1, 1, 2)

        transit_layout.addWidget(QLabel("Jump:"), 3, 0)
        self.btn_prev_rashi = QPushButton("< Prev")
        self.btn_next_rashi = QPushButton("Next >")
        transit_layout.addWidget(self.btn_prev_rashi, 3, 1)
        transit_layout.addWidget(self.btn_next_rashi, 3, 2)

        # Stop button is initially completely hidden to keep UI clean
        self.btn_stop_transit = QPushButton("Stop Search")
        self.btn_stop_transit.setStyleSheet("color: red; font-weight: bold;")
        self.btn_stop_transit.hide()
        transit_layout.addWidget(self.btn_stop_transit, 4, 0, 1, 3)
        
        transit_group.setLayout(transit_layout)

        set_group = QGroupBox("Chart Settings"); set_layout = QVBoxLayout()
        self.cb_ayanamsa = QComboBox(); self.cb_ayanamsa.addItems(["Lahiri", "Raman", "Fagan/Bradley"])
        
        self.chk_symbols = QCheckBox("Use Astro Symbols")
        self.chk_rahu = QCheckBox("Show Rahu/Ketu"); self.chk_rahu.setChecked(True)
        self.chk_aspects = QCheckBox("Show Planetary Aspects (Drishti)")
        self.chk_arrows = QCheckBox("Show Aspect Lines & Arrows"); self.chk_arrows.setChecked(True)
        self.chk_tint = QCheckBox("Use Aspect Tint"); self.chk_tint.setChecked(True)
        self.chk_details = QCheckBox("Show Details (Table)"); self.chk_details.setChecked(True)
        self.chk_circular = QCheckBox("Use Circular Chart Shape"); self.chk_circular.setChecked(False)
        
        self.btn_save_chart = QPushButton("Save Chart...")
        self.btn_load_chart = QPushButton("Load Chart...")
        self.btn_export = QPushButton("Export PNG...")

        set_layout.addWidget(QLabel("Ayanamsa:")); set_layout.addWidget(self.cb_ayanamsa)
        for w in [self.chk_symbols, self.chk_rahu, self.chk_aspects, self.chk_arrows, self.chk_tint, self.chk_details, self.chk_circular]: set_layout.addWidget(w)
        
        file_btns = QHBoxLayout(); file_btns.addWidget(self.btn_save_chart); file_btns.addWidget(self.btn_load_chart)
        set_layout.addLayout(file_btns); set_layout.addWidget(self.btn_export); set_group.setLayout(set_layout)

        self.aspects_group = QGroupBox("Aspects From:")
        aspects_layout = QGridLayout(); self.aspect_cb = {}
        planets_data = [("Sun", "#FFA500"), ("Moon", "#3399FF"), ("Mars", "#FF3333"), ("Mercury", "#33AA33"), ("Jupiter", "#CCCC00"), ("Venus", "#FF66B2"), ("Saturn", "#800080"), ("Rahu", "#888888"), ("Ketu", "#888888")]
        for i, (p, color) in enumerate(planets_data):
            cb = QCheckBox(p); cb.setStyleSheet(f"color: {color}; font-weight: bold;"); cb.setChecked(True); cb.stateChanged.connect(self.update_settings)
            self.aspect_cb[p] = cb; aspects_layout.addWidget(cb, i // 3, i % 3)
        self.aspects_group.setLayout(aspects_layout); self.aspects_group.setVisible(False)

        for g in [loc_group, dt_group, nav_group, transit_group, set_group, self.aspects_group]: left_layout.addWidget(g)
        left_layout.addStretch(); left_scroll.setWidget(left_panel)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        self.chart = ChartRenderer(); right_splitter.addWidget(self.chart)
        
        self.table = QTableWidget(); self.table.setColumnCount(6); self.table.setHorizontalHeaderLabels(["Planet", "Sign", "Degree", "House", "Retrograde", "Freeze Rashi"])
        if self.table.horizontalHeader() is not None: self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_splitter.addWidget(self.table); right_splitter.setSizes([550, 200])
        self.table.setVisible(self.chk_details.isChecked())

        main_splitter.addWidget(left_scroll); main_splitter.addWidget(right_splitter); main_splitter.setSizes([380, 770])

    def set_transit_buttons_enabled(self, enabled):
        """Dynamically hides the Stop button unless processing is actually active."""
        self.btn_prev_lagna.setEnabled(enabled)
        self.btn_next_lagna.setEnabled(enabled)
        self.btn_prev_rashi.setEnabled(enabled)
        self.btn_next_rashi.setEnabled(enabled)
        self.cb_transit_planet.setEnabled(enabled)
        self.cb_transit_rashi.setEnabled(enabled)
        
        if enabled:
            self.btn_stop_transit.hide()
        else:
            self.btn_stop_transit.setText("Stop (Initializing...)")
            self.btn_stop_transit.show()

    def _connect_signals(self):
        self.loc_btn.clicked.connect(self.search_location); self.loc_input.returnPressed.connect(self.search_location)
        self.time_ctrl.time_changed.connect(self.on_time_changed)
        self.date_edit.dateChanged.connect(self.on_ui_datetime_changed); self.time_edit.timeChanged.connect(self.on_ui_datetime_changed)
        self.btn_play.clicked.connect(self.toggle_play); self.speed_combo.currentIndexChanged.connect(self.change_speed)
        
        self.btn_add_m.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(minutes=1)))
        self.btn_add_h.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(hours=1)))
        self.btn_add_d.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(days=1)))
        self.btn_sub_m.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(minutes=-1)))
        self.btn_sub_h.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(hours=-1)))
        self.btn_sub_d.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(days=-1)))
        
        self.btn_prev_lagna.clicked.connect(lambda: self.jump_to_transit("Ascendant", -1))
        self.btn_next_lagna.clicked.connect(lambda: self.jump_to_transit("Ascendant", 1))
        self.btn_prev_rashi.clicked.connect(lambda: self.jump_to_transit(self.cb_transit_planet.currentText(), -1))
        self.btn_next_rashi.clicked.connect(lambda: self.jump_to_transit(self.cb_transit_planet.currentText(), 1))
        self.btn_stop_transit.clicked.connect(self.stop_transit_search)
        
        self.cb_ayanamsa.currentTextChanged.connect(self.update_settings)
        self.chk_symbols.stateChanged.connect(self.update_settings); self.chk_rahu.stateChanged.connect(self.update_settings)
        self.chk_aspects.stateChanged.connect(self.toggle_aspects); self.chk_arrows.stateChanged.connect(self.update_settings)
        self.chk_tint.stateChanged.connect(self.update_settings); self.chk_details.stateChanged.connect(self.toggle_details)
        self.chk_circular.stateChanged.connect(self.update_settings)
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
        self.date_edit.setDate(QDate(dt.year, dt.month, dt.day)); self.time_edit.setTime(QTime(dt.hour, dt.minute, dt.second))
        self.is_updating_ui = False; self.recalculate()

    def on_ui_datetime_changed(self):
        if self.is_updating_ui: return
        d, t = self.date_edit.date(), self.time_edit.time()
        self.time_ctrl.set_time(datetime.datetime(d.year(), d.month(), d.day(), t.hour(), t.minute(), t.second()))

    def stop_transit_search(self):
        if hasattr(self, 'transit_worker') and self.transit_worker.isRunning():
            self.transit_worker.stop()

    def jump_to_transit(self, body_name, direction):

        if hasattr(self, 'transit_worker') and self.transit_worker.isRunning():
            self.transit_worker.stop()
            self.transit_worker.wait()
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        was_playing = self.time_ctrl.is_playing
        current_qdate = self.date_edit.date()
        current_qtime = self.time_edit.time()
        if was_playing: self.toggle_play()
        
        target_sign = self.cb_transit_rashi.currentText()
        
        if body_name in self.frozen_planets:
            frozen_sign_idx = self.frozen_planets[body_name]
            frozen_sign_name = zodiac_names[frozen_sign_idx]
            if target_sign != "Any Rashi" and target_sign != frozen_sign_name:
                ans = QMessageBox.question(self, "Inconsistent Options", f"{body_name.lower()} is freezed in {frozen_sign_name.lower()}, wish to unfreeze it?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if ans == QMessageBox.StandardButton.Yes:
                    del self.frozen_planets[body_name]
                    self.recalculate()
                else:
                    return

        self.set_transit_buttons_enabled(False)
        
        params = {
            'dt': self.time_ctrl.current_time.isoformat(),
            'lat': self.current_lat,
            'lon': self.current_lon,
            'tz_name': self.current_tz,
            'body_name': body_name,
            'direction': direction,
            'target_sign_name': target_sign,
            'frozen_planets': self.frozen_planets.copy(),
            'ayanamsa': self.cb_ayanamsa.currentText()
        }

        self.transit_worker = TransitWorkerThread(params)
        self.transit_worker.finished.connect(lambda dt, d=direction: self.on_transit_finished(dt, d))
        self.transit_worker.error.connect(self.on_transit_error)
        self.transit_worker.stopped.connect(self.on_transit_stopped)
        self.transit_worker.progress.connect(self.on_transit_progress)
        self.transit_worker.start()

    def on_transit_progress(self, date_str):
        self.btn_stop_transit.setText(f"Stop Search (Scanning ~{date_str})")

    def on_transit_finished(self, next_dt, direction):
        self.set_transit_buttons_enabled(True)
        if next_dt is None:
            QMessageBox.warning(self, "Transit Blocked", "Could not find transit without breaking freeze constraints.")
            return
            
        offset = 1 if direction == 1 else -1
        self.time_ctrl.set_time(next_dt + datetime.timedelta(seconds=offset))

    # def on_transit_error(self, err_msg):
    #     self.set_transit_buttons_enabled(True)
    #     QMessageBox.warning(self, "Transit Error", str(err_msg))

    def on_transit_error(self, err_msg):
        self.set_transit_buttons_enabled(True)
        # Stop the worker thread properly so a new one can start
        if hasattr(self, 'transit_worker') and self.transit_worker.isRunning():
            self.transit_worker.stop()
        
        QMessageBox.warning(self, "Transit Error", f"Search Limit Reached: {err_msg}")
        


    def on_transit_stopped(self):
        self.set_transit_buttons_enabled(True)

    def toggle_play(self):
        playing = self.time_ctrl.toggle_animation()
        self.btn_play.setText("⏸ Pause" if playing else "▶ Play")

    def change_speed(self):
        speeds = [1.0, 60.0, 3600.0, 7200.0, 86400.0, 604800.0]
        self.time_ctrl.set_speed(speeds[self.speed_combo.currentIndex()])

    def update_settings(self):
        if self.is_updating_ui: return
        self.ephemeris.set_ayanamsa(self.cb_ayanamsa.currentText())
        self.chart.use_symbols, self.chart.show_rahu_ketu = self.chk_symbols.isChecked(), self.chk_rahu.isChecked()
        self.chart.show_aspects, self.chart.show_arrows = self.chk_aspects.isChecked(), self.chk_arrows.isChecked()
        self.chart.use_tint = self.chk_tint.isChecked()
        self.chart.use_circular = self.chk_circular.isChecked()
        self.chart.visible_aspect_planets = {p for p, cb in self.aspect_cb.items() if cb.isChecked()}
        self.save_settings(); self.recalculate()

    def toggle_aspects(self):
        self.aspects_group.setVisible(self.chk_aspects.isChecked()); self.chk_arrows.setVisible(self.chk_aspects.isChecked())
        self.chk_tint.setVisible(self.chk_aspects.isChecked()); self.update_settings()

    def toggle_details(self):
        self.table.setVisible(self.chk_details.isChecked()); self.save_settings()

    def get_current_chart_info(self):
        return {"location": self.loc_input.text(), "lat": self.current_lat, "lon": self.current_lon, "tz": self.current_tz, "datetime": self.time_ctrl.current_time.isoformat()}

    def save_chart_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "", "JSON Files (*.json);;All Files (*)")
        if path and save_prefs.save_chart_to_file(path, self.get_current_chart_info()):
            self.is_chart_saved = True; QMessageBox.information(self, "Success", "Chart saved successfully.")

    def load_chart_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Chart", "", "JSON Files (*.json);;All Files (*)")
        if path:
            data = save_prefs.load_chart_from_file(path)
            if data:
                self.is_updating_ui = True
                self.frozen_planets.clear() # CLEARS ALL CONSTRAINTS UPON LOAD
                self.loc_input.setText(data.get("location", "New Delhi, India"))
                self.current_lat, self.current_lon, self.current_tz = data.get("lat", 28.6139), data.get("lon", 77.2090), data.get("tz", "Asia/Kolkata")
                self.loc_status.setText(f"Lat: {self.current_lat:.2f}, Lon: {self.current_lon:.2f}\nTZ: {self.current_tz}")
                try: self.time_ctrl.set_time(datetime.datetime.fromisoformat(data["datetime"]))
                except Exception as e: print(f"Error parsing date from file: {e}")
                self.is_updating_ui = False; self.save_settings(); self.recalculate(); self.is_chart_saved = True
            else: QMessageBox.warning(self, "Error", "Failed to load chart data.")

    def closeEvent(self, event):
        if not getattr(self, "is_chart_saved", True):
            tmp_filename = f"tmp_001_saveon_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            save_prefs.save_chart_to_file(tmp_filename, self.get_current_chart_info())
            print(f"Unsaved changes auto-saved to {tmp_filename}")
        super().closeEvent(event)

    def export_chart(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "", "PNG Files (*.png);;All Files (*)")
        if path: self.chart.grab().save(path, "PNG")

    def recalculate(self):
        dt = self.time_ctrl.current_time
        try:
            chart_data = self.ephemeris.calculate_chart(dt, self.current_lat, self.current_lon, self.current_tz)
            
            violation = False
            violating_planet = None
            for p in chart_data["planets"]:
                if p["name"] in self.frozen_planets:
                    if p["sign_index"] != self.frozen_planets[p["name"]]:
                        violation = True
                        violating_planet = p["name"]
                        break
                        
            if not violation and "Ascendant" in self.frozen_planets:
                if chart_data["ascendant"]["sign_index"] != self.frozen_planets["Ascendant"]:
                    violation = True
                    violating_planet = "Ascendant"
            
            if violation:
                zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
                if hasattr(self, 'last_good_time'):
                    self.time_ctrl.current_time = self.last_good_time
                    if self.time_ctrl.is_playing:
                        self.toggle_play()
                    if getattr(self, "freeze_msg_shown", False) == False:
                        self.freeze_msg_shown = True
                        QMessageBox.warning(self, "Freeze Boundary Reached", f"{violating_planet} is frozen in {zodiac_names[self.frozen_planets[violating_planet]]}. Cannot step further.")
                        QTimer.singleShot(1500, lambda: setattr(self, "freeze_msg_shown", False))
                    return
                    
            self.last_good_time = dt

            self.chart.update_chart(chart_data)
            self.update_table(chart_data)
            if not self.is_loading_settings: self.is_chart_saved = False
        except Exception as e: print(f"Calculation Error: {e}")

    def toggle_freeze(self, name, sign_idx, checked):
        if checked:
            self.frozen_planets[name] = sign_idx
        else:
            if name in self.frozen_planets:
                del self.frozen_planets[name]

    def update_table(self, chart_data):
        self.table.setRowCount(0)
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        asc = chart_data["ascendant"]
        
        def add_freeze_cb(row, name, sign_idx):
            cb = QCheckBox(f"Freeze in {zodiac_names[sign_idx]}")
            cb.setChecked(name in self.frozen_planets)
            cb.toggled.connect(lambda checked, n=name, s=sign_idx: self.toggle_freeze(n, s, checked))
            w = QWidget(); l = QHBoxLayout(w); l.addWidget(cb); l.setAlignment(Qt.AlignmentFlag.AlignCenter); l.setContentsMargins(0,0,0,0)
            self.table.setCellWidget(row, 5, w)
            
        self.table.insertRow(0)
        self.table.setItem(0, 0, QTableWidgetItem("Ascendant"))
        self.table.setItem(0, 1, QTableWidgetItem(zodiac_names[asc["sign_index"]]))
        self.table.setItem(0, 2, QTableWidgetItem(f"{asc['degree'] % 30:.2f}°"))
        self.table.setItem(0, 3, QTableWidgetItem("1")); self.table.setItem(0, 4, QTableWidgetItem("-"))
        add_freeze_cb(0, "Ascendant", asc["sign_index"])

        for i, p in enumerate(chart_data["planets"]):
            row = i + 1
            if p["name"] in ["Rahu", "Ketu"] and not self.chk_rahu.isChecked(): continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(zodiac_names[p["sign_index"]]))
            self.table.setItem(row, 2, QTableWidgetItem(f"{p['deg_in_sign']:.2f}°"))
            self.table.setItem(row, 3, QTableWidgetItem(str(p["house"])))
            self.table.setItem(row, 4, QTableWidgetItem("Yes" if p["retro"] else "No"))
            add_freeze_cb(row, p["name"], p["sign_index"])

GLOBAL_FONT_FAMILY = "Segoe UI"
GLOBAL_FONT_SCALE = 11           
GLOBAL_PRIMARY_COLOR = "#4A90E2" 

if __name__ == "__main__":
    multiprocessing.freeze_support() # Crucial for Windows multiprocess executable building
    app = QApplication(sys.argv)
    font = QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SCALE); app.setFont(font); app.setStyle("Fusion")
    app.setStyleSheet(f"QGroupBox::title {{ color: {GLOBAL_PRIMARY_COLOR}; font-weight: bold; }} QPushButton {{ padding: 4px 8px; }} QPushButton:checked {{ background-color: {GLOBAL_PRIMARY_COLOR}; color: white; }}")
    
    window = AstroApp()
    window.show()
    sys.exit(app.exec())