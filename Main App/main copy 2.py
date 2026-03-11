import sys
import datetime
import json
import os
import math
import pytz
import swisseph as swe

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QDateEdit, QTimeEdit, 
                             QTableWidget, QTableWidgetItem, QCheckBox,
                             QHeaderView, QMessageBox, QGroupBox, QFileDialog,
                             QScrollArea, QGridLayout)
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QDate, QTime, QThread, pyqtSignal, QRectF, QPointF, QObject

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

import save_prefs
import animation

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
# 2. EPHEMERIS ENGINE
# ==========================================
class EphemerisEngine:
    def __init__(self):
        swe.set_ephe_path('')
        self.ayanamsa_modes = {
            "Lahiri": swe.SIDM_LAHIRI,
            "Raman": swe.SIDM_RAMAN,
            "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY
        }
        self.current_ayanamsa = "Lahiri"

    def set_ayanamsa(self, name):
        if name in self.ayanamsa_modes:
            self.current_ayanamsa = name

    def calculate_chart(self, dt: datetime.datetime, lat: float, lon: float, tz_name: str):
        local_tz = pytz.timezone(tz_name)
        if dt.tzinfo is None: dt = local_tz.localize(dt)
        dt_utc = dt.astimezone(pytz.utc)
        
        decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        jd_utc = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)

        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        
        cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        asc_deg = ascmc[0]
        asc_sign_index = int(asc_deg / 30)
        
        chart_data = {
            "ascendant": {"degree": asc_deg, "sign_index": asc_sign_index, "sign_num": asc_sign_index + 1},
            "planets": []
        }

        exaltation_rules = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
        debilitation_rules = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
        sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}

        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            sign_in_house = (asc_sign_index + h - 1) % 12 + 1
            ruler = sign_rulers.get(sign_in_house)
            if ruler: planet_lordships[ruler].append(h)

        bodies = [
            ("Sun", "Su", swe.SUN), ("Moon", "Mo", swe.MOON), ("Mars", "Ma", swe.MARS), ("Mercury", "Me", swe.MERCURY),
            ("Jupiter", "Ju", swe.JUPITER), ("Venus", "Ve", swe.VENUS), ("Saturn", "Sa", swe.SATURN), ("Rahu", "Ra", swe.TRUE_NODE)
        ]

        for name, sym, body_id in bodies:
            res, _ = swe.calc_ut(jd_utc, body_id, calc_flag)
            lon_deg = res[0]
            speed = res[3]
            
            p_sign_idx = int(lon_deg / 30)
            p_sign_num = p_sign_idx + 1
            deg_in_sign = lon_deg % 30
            is_retro = speed < 0 if name not in ["Sun", "Moon", "Rahu", "Ketu"] else False
            if name == "Rahu": is_retro = True

            house_num = (p_sign_idx - asc_sign_index) % 12 + 1
            
            exalted = (p_sign_num == exaltation_rules.get(name))
            debilitated = (p_sign_num == debilitation_rules.get(name))
            own_sign = (sign_rulers.get(p_sign_num) == name)

            chart_data["planets"].append({
                "name": name, "sym": sym, "lon": lon_deg, "sign_index": p_sign_idx, "sign_num": p_sign_num,
                "deg_in_sign": deg_in_sign, "house": house_num, "retro": is_retro,
                "exalted": exalted, "debilitated": debilitated, "own_sign": own_sign, "lord_of": planet_lordships.get(name, [])
            })

        rahu = next(p for p in chart_data["planets"] if p["name"] == "Rahu")
        ketu_lon = (rahu["lon"] + 180.0) % 360.0
        ketu_sign_idx = int(ketu_lon / 30)
        ketu_sign_num = ketu_sign_idx + 1
        ketu_deg_in_sign = ketu_lon % 30
        ketu_house = (ketu_sign_idx - asc_sign_index) % 12 + 1
        
        chart_data["planets"].append({
            "name": "Ketu", "sym": "Ke", "lon": ketu_lon, "sign_index": ketu_sign_idx, "sign_num": ketu_sign_num,
            "deg_in_sign": ketu_deg_in_sign, "house": ketu_house, "retro": True,
            "exalted": (ketu_sign_num == exaltation_rules.get("Ketu")), "debilitated": (ketu_sign_num == debilitation_rules.get("Ketu")),
            "own_sign": False, "lord_of": []
        })

        sun_p = next((p for p in chart_data["planets"] if p["name"] == "Sun"), None)
        sun_lon = sun_p["lon"] if sun_p else 0.0
        combust_rules = {"Moon": {"dir": 12, "retro": 12}, "Mercury": {"dir": 14, "retro": 12}, "Venus": {"dir": 10, "retro": 8},
                         "Mars": {"dir": 17, "retro": 17}, "Jupiter": {"dir": 11, "retro": 11}, "Saturn": {"dir": 15, "retro": 15}}
        
        for p in chart_data["planets"]:
            if p["name"] in combust_rules:
                dist = abs(p["lon"] - sun_lon)
                dist = min(dist, 360.0 - dist)
                limit = combust_rules[p["name"]]["retro"] if p["retro"] else combust_rules[p["name"]]["dir"]
                p["combust"] = (dist <= limit)
            else: p["combust"] = False

        chart_data["aspects"] = self.calculate_vedic_aspects(chart_data["planets"])
        return chart_data

    def calculate_vedic_aspects(self, planets):
        aspects = []
        aspect_rules = {"Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7], "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10], "Rahu": [5, 7, 9], "Ketu": [5, 7, 9]}
        planet_colors = {"Sun": "orange", "Moon": "blue", "Mars": "red", "Mercury": "green", "Jupiter": "yellow", "Venus": "pink", "Saturn": "purple", "Rahu": "gray", "Ketu": "gray"}

        for p in planets:
            p_name = p["name"]
            p_house = p["house"]
            rules = aspect_rules.get(p_name, [])
            for aspect_count in rules:
                target_house = (p_house + aspect_count - 2) % 12 + 1
                aspects.append({"aspecting_planet": p_name, "source_house": p_house, "target_house": target_house, "aspect_count": aspect_count, "color": planet_colors.get(p_name, "white")})
        return aspects

    def find_next_transit(self, dt, lat, lon, tz_name, body_name):
        local_tz = pytz.timezone(tz_name)
        if dt.tzinfo is None: dt = local_tz.localize(dt)
        dt_utc = dt.astimezone(pytz.utc)
        
        decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        jd_start = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)
        
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        
        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE}
        
        def get_sign(j):
            if body_name == "Ascendant":
                cusps, ascmc = swe.houses_ex(j, lat, lon, b'P', calc_flag)
                return int(ascmc[0] / 30.0)
            elif body_name == "Ketu":
                res, _ = swe.calc_ut(j, swe.TRUE_NODE, calc_flag)
                return int((res[0] + 180.0) % 360.0 / 30.0)
            else:
                res, _ = swe.calc_ut(j, body_map[body_name], calc_flag)
                return int(res[0] / 30.0)

        start_sign = get_sign(jd_start)
        
        if body_name == "Ascendant": step = 0.01      
        elif body_name == "Moon": step = 0.1          
        elif body_name in ["Sun", "Mercury", "Venus"]: step = 1.0
        elif body_name == "Mars": step = 2.0
        elif body_name == "Jupiter": step = 5.0
        else: step = 10.0                             
        
        jd = jd_start + 0.001 
        for _ in range(1000):
            if get_sign(jd) != start_sign: break
            jd += step
        
        jd_low = jd - step
        jd_high = jd
        for _ in range(20): 
            jd_mid = (jd_low + jd_high) / 2.0
            if get_sign(jd_mid) == start_sign: jd_low = jd_mid
            else: jd_high = jd_mid
                
        jd_transit = jd_high
        year, month, day, hour = swe.revjul(jd_transit, 1)
        h = int(hour); m = int((hour - h) * 60); s = int((((hour - h) * 60) - m) * 60)
        
        try:
            dt_utc_transit = datetime.datetime(year, month, day, h, m, s, tzinfo=pytz.utc)
            return dt_utc_transit.astimezone(local_tz).replace(tzinfo=None)
        except ValueError:
            return dt


# ==========================================
# 3. CHART RENDERER
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
        self.update()

    def paintEvent(self, event):
        self.hitboxes = []
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_color = QColor("#FFFFFF")
        line_color = QColor("#222222")
        text_color = QColor("#000000")
        
        bright_colors = {
            "Sun": QColor("#FFAA00"), "Moon": QColor("#0066CC"), "Mars": QColor("#CC0000"),
            "Mercury": QColor("#009900"), "Jupiter": QColor("#B8860B"), "Venus": QColor("#CC00CC"),
            "Saturn": QColor("#6600CC"), "Rahu": QColor("#666666"), "Ketu": QColor("#666666"), "Ascendant": QColor("#C0392B")
        }

        painter.fillRect(self.rect(), bg_color)
        size = min(self.width(), self.height()) - 40
        cx = self.width() / 2
        cy = self.height() / 2
        x = cx - size / 2
        y = cy - size / 2
        w = size
        h = size

        self.house_polys.clear()
        for h_num in range(1, 13):
            self.house_polys[h_num] = self._get_house_polygon(h_num, x, y, w, h)

        if self.show_aspects and self.use_tint and self.chart_data and "aspects" in self.chart_data:
            color_map = {"orange": QColor(255, 165, 0, 20), "blue": QColor(50, 150, 255, 20), "red": QColor(255, 50, 50, 20), "green": QColor(50, 255, 50, 20),
                         "yellow": QColor(200, 180, 0, 20), "pink": QColor(255, 105, 180, 20), "purple": QColor(160, 32, 240, 20), "gray": QColor(150, 150, 150, 20)}
            
            for aspect in self.chart_data["aspects"]:
                p_name = aspect["aspecting_planet"]
                if p_name not in self.visible_aspect_planets or (p_name in ["Rahu", "Ketu"] and not self.show_rahu_ketu): continue
                
                h2 = aspect["target_house"]
                painter.setBrush(QBrush(color_map.get(aspect["color"], QColor(255, 255, 255, 20))))
                painter.setPen(Qt.PenStyle.NoPen)
                
                if getattr(self, "use_circular", False):
                    margin = 20
                    rect = QRectF(x + margin, y + margin, w - 2*margin, h - 2*margin)
                    center_angle = (90 + (h2 - 1) * 30) % 360
                    painter.drawPie(rect, int((center_angle - 15) * 16), int(30 * 16))
                else:
                    painter.drawPolygon(self.house_polys[h2])

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

        if not self.chart_data:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Chart Data")
            return

        asc_deg = self.chart_data["ascendant"]["degree"]
        asc_sign = self.chart_data["ascendant"]["sign_num"]
        
        for sign_num in range(1, 13):
            sign_lon = (sign_num - 1) * 30.0 + 15.0
            zx, zy = animation.get_smooth_orbit_coords(sign_lon, asc_deg, -3, w, h, getattr(self, "use_circular", False))
            zx += x; zy += y
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.setPen(QColor("#777777"))
            painter.drawText(QRectF(zx - 15, zy - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, str(sign_num))

        LANE_ORDER = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4, "Venus": 5, "Saturn": 6, "Rahu": 7, "Ketu": 8, "Ascendant": 9}
        all_bodies = []
        
        if self.highlight_asc_moon:
            all_bodies.append({
                "name": "Ascendant", "str": "Asc", "color": bright_colors["Ascendant"], 
                "lon": asc_deg, "retro": False, "exalted": False, "debilitated": False, "combust": False,
                "raw": {"name": "Ascendant", "sign_index": self.chart_data["ascendant"]["sign_index"], "deg_in_sign": self.chart_data["ascendant"]["degree"] % 30, "retro": False, "combust": False, "house": 1}
            })

        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"] and not self.show_rahu_ketu: continue
            display_str = self.unicode_syms[p["name"]] if self.use_symbols else p["sym"]
            all_bodies.append({"name": p["name"], "str": display_str, "color": bright_colors.get(p["name"], text_color), "lon": p["lon"], "retro": p["retro"], "exalted": p.get("exalted", False), "debilitated": p.get("debilitated", False), "combust": p.get("combust", False), "raw": p})

        for b in all_bodies:
            lane_idx = LANE_ORDER.get(b["name"], 4.5)
            px, py = animation.get_smooth_orbit_coords(b["lon"], asc_deg, lane_idx, w, h, getattr(self, "use_circular", False))
            px += x; py += y
            
            b["px"] = px; b["py"] = py
            painter.setPen(b["color"])
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            p_rect = QRectF(px - 40, py - 10, 80, 20)
            painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, b["str"])
            
            self.hitboxes.append((p_rect, b["raw"]))
            
            fm = painter.fontMetrics()
            marker_x = px + fm.horizontalAdvance(b["str"]) / 2 + 2
            
            if b["retro"]:
                painter.setFont(QFont("Arial", 7, QFont.Weight.Bold))
                painter.drawText(int(marker_x), int(py + 5), "R")
                marker_x += fm.horizontalAdvance("R") + 2
                
            t_y = py + 8
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
                
        if self.show_aspects: self._draw_aspects(painter, all_bodies, asc_deg, x, y, w, h)

    def _draw_aspect_line(self, painter, x1, y1, x2, y2, color_name, offset_idx=0):
        color_map = {"orange": QColor(255, 165, 0, 160), "blue": QColor(50, 150, 255, 160), "red": QColor(255, 50, 50, 160), "green": QColor(50, 255, 50, 160),
                     "yellow": QColor(200, 180, 0, 180), "pink": QColor(255, 105, 180, 160), "purple": QColor(160, 32, 240, 160), "gray": QColor(150, 150, 150, 160)}
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

    def _draw_aspects(self, painter, all_bodies, asc_deg, x, y, w, h):
        if not self.show_arrows or "aspects" not in self.chart_data: return
            
        for i, aspect in enumerate(self.chart_data["aspects"]):
            p_name = aspect["aspecting_planet"]
            if p_name not in self.visible_aspect_planets or (p_name in ["Rahu", "Ketu"] and not self.show_rahu_ketu): continue
            
            p1_info = next((b for b in all_bodies if b["name"] == p_name), None)
            if not p1_info: continue
            
            target_sign_idx = (p1_info["raw"]["sign_index"] + aspect["aspect_count"] - 1) % 12
            tx, ty = animation.get_smooth_orbit_coords(target_sign_idx * 30.0 + 15.0, asc_deg, -3, w, h, getattr(self, "use_circular", False))
            self._draw_aspect_line(painter, p1_info["px"], p1_info["py"], tx + x, ty + y, aspect["color"], offset_idx=i)

    def mouseMoveEvent(self, event):
        if not self.chart_data:
            if self.tooltip_label.isVisible(): self.tooltip_label.hide()
            return
            
        pos, tooltip_html = event.position(), ""
        
        def ordinal(n): return str(n) + ('th' if 11 <= (n % 100) <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th'))
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        # 1. Check Planets
        for rect, p_raw in self.hitboxes:
            if rect.contains(pos):
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
                
        # 2. Check Houses 
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
                elif h_num in self.house_polys and self.house_polys[h_num].containsPoint(pos, Qt.FillRule.OddEvenFill):
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
            g_pos, l_w, l_h = event.globalPosition().toPoint(), self.tooltip_label.width(), self.tooltip_label.height()
            t_x, t_y = g_pos.x() + 15, g_pos.y() + 15
            if t_x + l_w > screen.right(): t_x = g_pos.x() - l_w - 5
            if t_y + l_h > screen.bottom(): t_y = g_pos.y() - l_h - 5
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

        self.ephemeris = EphemerisEngine()
        self.time_ctrl = animation.TimeController()
        
        self.current_lat, self.current_lon, self.current_tz = 28.6139, 77.2090, "Asia/Kolkata"
        self.is_updating_ui = False
        self.is_loading_settings = True 
        self.is_chart_saved = True

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
        
        transit_group = QGroupBox("Transit Tools"); transit_layout = QVBoxLayout()
        self.btn_next_lagna = QPushButton("Next Lagna (Ascendant)")
        planet_transit_layout = QHBoxLayout()
        self.cb_transit_planet = QComboBox(); self.cb_transit_planet.addItems(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
        self.btn_next_rashi = QPushButton("Next Rashi")
        planet_transit_layout.addWidget(self.cb_transit_planet); planet_transit_layout.addWidget(self.btn_next_rashi)
        transit_layout.addWidget(self.btn_next_lagna); transit_layout.addLayout(planet_transit_layout); transit_group.setLayout(transit_layout)

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
        
        self.table = QTableWidget(); self.table.setColumnCount(5); self.table.setHorizontalHeaderLabels(["Planet", "Sign", "Degree", "House", "Retrograde"])
        if self.table.horizontalHeader() is not None: self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_splitter.addWidget(self.table); right_splitter.setSizes([550, 200])
        self.table.setVisible(self.chk_details.isChecked())

        main_splitter.addWidget(left_scroll); main_splitter.addWidget(right_splitter); main_splitter.setSizes([380, 770])

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
        
        self.btn_next_lagna.clicked.connect(lambda: self.jump_to_transit("Ascendant"))
        self.btn_next_rashi.clicked.connect(lambda: self.jump_to_transit(self.cb_transit_planet.currentText()))
        
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

    def jump_to_transit(self, body_name):
        was_playing = self.time_ctrl.is_playing
        if was_playing: self.toggle_play()
        self.btn_next_lagna.setEnabled(False); self.btn_next_rashi.setEnabled(False)
        QApplication.processEvents() 
        try:
            next_dt = self.ephemeris.find_next_transit(self.time_ctrl.current_time, self.current_lat, self.current_lon, self.current_tz, body_name)
            self.time_ctrl.set_time(next_dt + datetime.timedelta(seconds=1))
        finally:
            self.btn_next_lagna.setEnabled(True); self.btn_next_rashi.setEnabled(True)

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
            self.chart.update_chart(chart_data)
            self.update_table(chart_data)
            if not self.is_loading_settings: self.is_chart_saved = False
        except Exception as e: print(f"Calculation Error: {e}")

    def update_table(self, chart_data):
        self.table.setRowCount(0)
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        asc = chart_data["ascendant"]
        self.table.insertRow(0)
        self.table.setItem(0, 0, QTableWidgetItem("Ascendant"))
        self.table.setItem(0, 1, QTableWidgetItem(zodiac_names[asc["sign_index"]]))
        self.table.setItem(0, 2, QTableWidgetItem(f"{asc['degree'] % 30:.2f}°"))
        self.table.setItem(0, 3, QTableWidgetItem("1")); self.table.setItem(0, 4, QTableWidgetItem("-"))

        for i, p in enumerate(chart_data["planets"]):
            row = i + 1
            if p["name"] in ["Rahu", "Ketu"] and not self.chk_rahu.isChecked(): continue
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(zodiac_names[p["sign_index"]]))
            self.table.setItem(row, 2, QTableWidgetItem(f"{p['deg_in_sign']:.2f}°"))
            self.table.setItem(row, 3, QTableWidgetItem(str(p["house"])))
            self.table.setItem(row, 4, QTableWidgetItem("Yes" if p["retro"] else "No"))

GLOBAL_FONT_FAMILY = "Segoe UI"
GLOBAL_FONT_SCALE = 11           
GLOBAL_PRIMARY_COLOR = "#4A90E2" 

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SCALE); app.setFont(font); app.setStyle("Fusion")
    app.setStyleSheet(f"QGroupBox::title {{ color: {GLOBAL_PRIMARY_COLOR}; font-weight: bold; }} QPushButton:checked {{ background-color: {GLOBAL_PRIMARY_COLOR}; color: white; }}")
    
    window = AstroApp()
    window.show()
    sys.exit(app.exec())