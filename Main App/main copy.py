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
                             QScrollArea, QGridLayout, QToolTip)
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QDate, QTime, QThread, pyqtSignal, QRectF, QPointF, QObject, QTimer

from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

import save_prefs

# ==========================================
# 1. TIME CONTROLLER
# ==========================================
class TimeController(QObject):
    time_changed = pyqtSignal(datetime.datetime)

    def __init__(self):
        super().__init__()
        self.current_time = datetime.datetime.now()
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.setInterval(100) # 10 FPS
        self.timer.timeout.connect(self._on_tick)
        
        self.is_playing = False
        self.speed_multiplier = 1.0 # 1 real sec = x virtual secs

    def set_time(self, dt: datetime.datetime):
        self.current_time = dt
        self.time_changed.emit(self.current_time)

    def step(self, delta: datetime.timedelta):
        self.current_time += delta
        self.time_changed.emit(self.current_time)

    def toggle_animation(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.timer.start()
        else:
            self.timer.stop()
        return self.is_playing

    def set_speed(self, multiplier: float):
        """Multiplier indicates how many virtual seconds pass per real second."""
        self.speed_multiplier = multiplier

    def _on_tick(self):
        # 100ms tick = 0.1 real seconds
        # virtual seconds to add = 0.1 * multiplier
        delta_seconds = 0.1 * self.speed_multiplier
        self.step(datetime.timedelta(seconds=delta_seconds))


# ==========================================
# 2. LOCATION WORKER
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
            # Initialize geocoder
            geolocator = Nominatim(user_agent="vedic_astro_app_v1")
            location = geolocator.geocode(self.location_name, timeout=10)
            
            if location:
                lat = location.latitude
                lon = location.longitude
                formatted_name = location.address
                
                # Find timezone
                tf = TimezoneFinder()
                tz_name = tf.timezone_at(lng=lon, lat=lat)
                
                if not tz_name:
                    tz_name = "UTC" # Fallback
                    
                self.result_ready.emit(lat, lon, tz_name, formatted_name)
            else:
                self.error_occurred.emit("Location not found.")
        except Exception as e:
            self.error_occurred.emit(f"Network or Geocoding Error: {str(e)}")


# ==========================================
# 3. EPHEMERIS ENGINE
# ==========================================
class EphemerisEngine:
    def __init__(self):
        # Using built-in swisseph ephemeris files (Moshier). 
        # For maximum precision, path to ephe files can be set here.
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
        """
        Calculates the Vedic chart (Sidereal positions).
        """
        # 1. Convert local time to UTC
        local_tz = pytz.timezone(tz_name)
        if dt.tzinfo is None:
            dt = local_tz.localize(dt)
        dt_utc = dt.astimezone(pytz.utc)
        
        # 2. Get Julian Day
        # swisseph julday expects UTC year, month, day, and decimal hours
        decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        jd_utc = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)

        # 3. Configure Ayanamsa & Flags
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        # Flags: Sidereal zodiac, Speed calculation (for retro), Swiss Ephemeris
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        
        # 4. Calculate Ascendant
        # houses_ex returns (cusps, ascmc). ascmc[0] is the Ascendant.
        # We use 'W' (Whole Sign) or 'P' (Placidus) but in Vedic, we just need the Asc degree.
        cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        asc_deg = ascmc[0]
        asc_sign_index = int(asc_deg / 30)
        
        chart_data = {
            "ascendant": {
                "degree": asc_deg,
                "sign_index": asc_sign_index,
                "sign_num": asc_sign_index + 1
            },
            "planets": []
        }

        # Vedic Exaltation & Debilitation Rules
        exaltation_rules = {
            "Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6,
            "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8
        }
        debilitation_rules = {
            "Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12,
            "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2
        }
        
        # Sign Rulers for House Lordship and Own Sign Dignity
        sign_rulers = {
            1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun",
            6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter",
            10: "Saturn", 11: "Saturn", 12: "Jupiter"
        }

        # Calculate lordships for the current ascendant
        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            sign_in_house = (asc_sign_index + h - 1) % 12 + 1
            ruler = sign_rulers.get(sign_in_house)
            if ruler:
                planet_lordships[ruler].append(h)

        # 5. Calculate Planets
        bodies = [
            ("Sun", "Su", swe.SUN), ("Moon", "Mo", swe.MOON),
            ("Mars", "Ma", swe.MARS), ("Mercury", "Me", swe.MERCURY),
            ("Jupiter", "Ju", swe.JUPITER), ("Venus", "Ve", swe.VENUS),
            ("Saturn", "Sa", swe.SATURN), ("Rahu", "Ra", swe.TRUE_NODE)
        ]

        for name, sym, body_id in bodies:
            res, _ = swe.calc_ut(jd_utc, body_id, calc_flag)
            lon_deg = res[0]
            speed = res[3]
            
            p_sign_idx = int(lon_deg / 30)
            p_sign_num = p_sign_idx + 1
            deg_in_sign = lon_deg % 30
            is_retro = speed < 0 if name not in ["Sun", "Moon", "Rahu", "Ketu"] else False
            if name == "Rahu":
                is_retro = True # Nodes are usually always retrograde in display

            house_num = (p_sign_idx - asc_sign_index) % 12 + 1
            
            exalted = (p_sign_num == exaltation_rules.get(name))
            debilitated = (p_sign_num == debilitation_rules.get(name))
            own_sign = (sign_rulers.get(p_sign_num) == name)

            chart_data["planets"].append({
                "name": name, "sym": sym, "lon": lon_deg,
                "sign_index": p_sign_idx, "sign_num": p_sign_num,
                "deg_in_sign": deg_in_sign, "house": house_num, "retro": is_retro,
                "exalted": exalted, "debilitated": debilitated, "own_sign": own_sign,
                "lord_of": planet_lordships.get(name, [])
            })

        # Calculate Ketu (Exactly 180 degrees from Rahu)
        rahu = next(p for p in chart_data["planets"] if p["name"] == "Rahu")
        ketu_lon = (rahu["lon"] + 180.0) % 360.0
        ketu_sign_idx = int(ketu_lon / 30)
        ketu_sign_num = ketu_sign_idx + 1
        ketu_deg_in_sign = ketu_lon % 30
        ketu_house = (ketu_sign_idx - asc_sign_index) % 12 + 1
        
        chart_data["planets"].append({
            "name": "Ketu", "sym": "Ke", "lon": ketu_lon,
            "sign_index": ketu_sign_idx, "sign_num": ketu_sign_num,
            "deg_in_sign": ketu_deg_in_sign, "house": ketu_house, "retro": True,
            "exalted": (ketu_sign_num == exaltation_rules.get("Ketu")),
            "debilitated": (ketu_sign_num == debilitation_rules.get("Ketu")),
            "own_sign": False,
            "lord_of": []
        })

        # Calculate Combustion
        sun_p = next((p for p in chart_data["planets"] if p["name"] == "Sun"), None)
        sun_lon = sun_p["lon"] if sun_p else 0.0
        
        combust_rules = {
            "Moon": {"dir": 12, "retro": 12},
            "Mercury": {"dir": 14, "retro": 12},
            "Venus": {"dir": 10, "retro": 8},
            "Mars": {"dir": 17, "retro": 17},
            "Jupiter": {"dir": 11, "retro": 11},
            "Saturn": {"dir": 15, "retro": 15}
        }
        
        for p in chart_data["planets"]:
            if p["name"] in combust_rules:
                dist = abs(p["lon"] - sun_lon)
                dist = min(dist, 360.0 - dist)
                limit = combust_rules[p["name"]]["retro"] if p["retro"] else combust_rules[p["name"]]["dir"]
                p["combust"] = (dist <= limit)
            else:
                p["combust"] = False

        chart_data["aspects"] = self.calculate_vedic_aspects(chart_data["planets"])

        return chart_data

    def calculate_vedic_aspects(self, planets):
        aspects = []
        # Vedic Aspect Rules: Planet -> List of houses it aspects (counting itself as 1)
        aspect_rules = {
            "Sun": [7],
            "Moon": [7],
            "Mercury": [7],
            "Venus": [7],
            "Mars": [4, 7, 8],
            "Jupiter": [5, 7, 9],
            "Saturn": [3, 7, 10],
            "Rahu": [5, 7, 9],
            "Ketu": [5, 7, 9]
        }
        
        # Colors associated with each planet's aspect line
        planet_colors = {
            "Sun": "orange", "Moon": "blue", "Mars": "red",
            "Mercury": "green", "Jupiter": "yellow", "Venus": "pink",
            "Saturn": "purple", "Rahu": "gray", "Ketu": "gray"
        }

        for p in planets:
            p_name = p["name"]
            p_house = p["house"]
            rules = aspect_rules.get(p_name, [])

            for aspect_count in rules:
                # Calculate target house counting clockwise (which maps linearly to our house numbers)
                # Formula: (Current House + Aspect Count - 2) % 12 + 1
                target_house = (p_house + aspect_count - 2) % 12 + 1
                
                aspects.append({
                    "aspecting_planet": p_name,
                    "source_house": p_house,
                    "target_house": target_house,
                    "aspect_count": aspect_count,
                    "color": planet_colors.get(p_name, "white")
                })
                
        return aspects


# ==========================================
# 4. CHART RENDERER
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
        self.visible_aspect_planets = set() # Store which planets' aspects to draw

        # Custom Tooltip Label for instant display
        self.tooltip_label = QLabel(self)
        self.tooltip_label.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""
            QLabel {
                background-color: #FDFDFD; 
                color: #222222; 
                border: 1px solid #BBBBBB; 
                padding: 6px; 
                font-size: 13px;
            }
        """)
        self.tooltip_label.hide()

        # Unicode astrology symbols mapping
        self.unicode_syms = {
            "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
            "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", 
            "Rahu": "☊", "Ketu": "☋"
        }

        # The relative center coordinates for the 12 houses in a standard North Indian Chart
        # H1 is top-center, going counter-clockwise
        self.house_centers = {
            1: (0.5, 0.25), 2: (0.25, 0.125), 3: (0.125, 0.25),
            4: (0.25, 0.5), 5: (0.125, 0.75), 6: (0.25, 0.875),
            7: (0.5, 0.75), 8: (0.75, 0.875), 9: (0.875, 0.75),
            10: (0.75, 0.5), 11: (0.875, 0.25), 12: (0.75, 0.125)
        }
        
        # Zodiac number positions (slightly offset from the dead center)
        self.sign_offsets = {
            1: (0.5, 0.1), 2: (0.1, 0.05), 3: (0.05, 0.1),
            4: (0.1, 0.5), 5: (0.05, 0.9), 6: (0.1, 0.95),
            7: (0.5, 0.9), 8: (0.9, 0.95), 9: (0.95, 0.9),
            10: (0.9, 0.5), 11: (0.95, 0.1), 12: (0.9, 0.05)
        }

    def _get_house_polygon(self, h_num, x, y, w, h):
        """Returns a QPolygonF representing the exact geometric bounds of a given house."""
        p_tl = QPointF(x, y)
        p_tr = QPointF(x+w, y)
        p_bl = QPointF(x, y+h)
        p_br = QPointF(x+w, y+h)
        p_tc = QPointF(x+w/2, y)
        p_bc = QPointF(x+w/2, y+h)
        p_lc = QPointF(x, y+h/2)
        p_rc = QPointF(x+w, y+h/2)
        p_cc = QPointF(x+w/2, y+h/2)
        
        p_i_tl = QPointF(x+w/4, y+h/4)
        p_i_tr = QPointF(x+3*w/4, y+h/4)
        p_i_bl = QPointF(x+w/4, y+3*h/4)
        p_i_br = QPointF(x+3*w/4, y+3*h/4)

        polys = {
            1: [p_tc, p_i_tr, p_cc, p_i_tl],
            2: [p_tl, p_tc, p_i_tl],
            3: [p_tl, p_i_tl, p_lc],
            4: [p_lc, p_i_tl, p_cc, p_i_bl],
            5: [p_lc, p_i_bl, p_bl],
            6: [p_i_bl, p_bc, p_bl],
            7: [p_cc, p_i_br, p_bc, p_i_bl],
            8: [p_bc, p_i_br, p_br],
            9: [p_i_br, p_rc, p_br],
            10: [p_i_tr, p_rc, p_i_br, p_cc],
            11: [p_tr, p_rc, p_i_tr],
            12: [p_tc, p_tr, p_i_tr]
        }
        return QPolygonF(polys[h_num])

    def update_chart(self, data):
        self.chart_data = data
        self.update()

    def paintEvent(self, event):
        self.hitboxes = []
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Setup Colors
        bg_color = QColor("#FFFFFF")
        line_color = QColor("#222222")
        text_color = QColor("#000000")
        
        # Bright Planet Colors mapping
        bright_colors = {
            "Sun": QColor("#FFAA00"),     # Gold/Orange
            "Moon": QColor("#0066CC"),    # Blue/Cyan
            "Mars": QColor("#CC0000"),    # Red
            "Mercury": QColor("#009900"), # Green
            "Jupiter": QColor("#B8860B"), # Yellow/Gold
            "Venus": QColor("#CC00CC"),   # Pink/Magenta
            "Saturn": QColor("#6600CC"),  # Purple
            "Rahu": QColor("#666666"),    # Gray
            "Ketu": QColor("#666666"),    # Gray
            "Asc": QColor("#C0392B")
        }

        # Fill background
        painter.fillRect(self.rect(), bg_color)

        # Calculate square boundaries
        size = min(self.width(), self.height()) - 40
        cx = self.width() / 2
        cy = self.height() / 2
        
        # Draw the chart geometry
        x = cx - size / 2
        y = cy - size / 2
        w = size
        h = size

        # Cache house polygons for mouse hover
        self.house_polys.clear()
        for h_num in range(1, 13):
            self.house_polys[h_num] = self._get_house_polygon(h_num, x, y, w, h)

        # 0. Draw Tinted Aspected Houses (underneath the grid lines)
        if self.show_aspects and self.use_tint and self.chart_data and "aspects" in self.chart_data:
            color_map = {
                # Reduced alpha from 45 to 20 for softer coloring that doesn't bleed out the whole chart
                "orange": QColor(255, 165, 0, 20),
                "blue": QColor(50, 150, 255, 20),
                "red": QColor(255, 50, 50, 20),
                "green": QColor(50, 255, 50, 20),
                "yellow": QColor(200, 180, 0, 20),
                "pink": QColor(255, 105, 180, 20),
                "purple": QColor(160, 32, 240, 20),
                "gray": QColor(150, 150, 150, 20)
            }
            
            for aspect in self.chart_data["aspects"]:
                p_name = aspect["aspecting_planet"]
                if p_name not in self.visible_aspect_planets: continue
                if p_name in ["Rahu", "Ketu"] and not self.show_rahu_ketu: continue
                
                h2 = aspect["target_house"]
                tint_color = color_map.get(aspect["color"], QColor(255, 255, 255, 20))
                
                painter.setBrush(QBrush(tint_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(self._get_house_polygon(h2, x, y, w, h))

        # --- FIX: Clear the brush before drawing grid lines so the whole chart isn't filled! ---
        painter.setBrush(Qt.BrushStyle.NoBrush)

        pen = QPen(line_color, 2)
        painter.setPen(pen)

        # 1. Outer Square
        painter.drawRect(int(x), int(y), int(w), int(h))
        # 2. X diagonals
        painter.drawLine(int(x), int(y), int(x + w), int(y + h))
        painter.drawLine(int(x + w), int(y), int(x), int(y + h))
        # 3. Inner Diamond
        painter.drawLine(int(x + w/2), int(y), int(x + w), int(y + h/2))
        painter.drawLine(int(x + w), int(y + h/2), int(x + w/2), int(y + h))
        painter.drawLine(int(x + w/2), int(y + h), int(x), int(y + h/2))
        painter.drawLine(int(x), int(y + h/2), int(x + w/2), int(y))

        if not self.chart_data:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Chart Data")
            return

        # Prepare planets per house
        houses = {i: [] for i in range(1, 13)}
        
        # Add Ascendant mark to 1st house
        if self.highlight_asc_moon:
            houses[1].append({
                "str": "Asc", "color": bright_colors["Asc"], 
                "retro": False, "exalted": False, "debilitated": False,
                "combust": False,
                "raw": {
                    "name": "Ascendant",
                    "sign_index": self.chart_data["ascendant"]["sign_index"],
                    "deg_in_sign": self.chart_data["ascendant"]["degree"] % 30,
                    "retro": False,
                    "combust": False,
                    "house": 1
                }
            })

        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"] and not self.show_rahu_ketu:
                continue
                
            display_str = self.unicode_syms[p["name"]] if self.use_symbols else p["sym"]
                
            # Use bright color for planet
            col = bright_colors.get(p["name"], text_color)
                
            houses[p["house"]].append({
                "str": display_str,
                "color": col,
                "retro": p["retro"],
                "exalted": p.get("exalted", False),
                "debilitated": p.get("debilitated", False),
                "combust": p.get("combust", False),
                "raw": p
            })

        # Draw House Numbers and Planets
        asc_sign = self.chart_data["ascendant"]["sign_num"]
        
        for h_num in range(1, 13):
            # Calculate sign number for this house
            zodiac_num = (asc_sign + h_num - 2) % 12 + 1
            
            # Draw Zodiac number
            z_rx, z_ry = self.sign_offsets[h_num]
            zx = x + z_rx * w
            zy = y + z_ry * h
            
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.setPen(QColor("#777777"))
            
            # Adjust minor alignment based on corner
            align = Qt.AlignmentFlag.AlignCenter
            rect = QRectF(zx - 15, zy - 15, 30, 30)
            painter.drawText(rect, align, str(zodiac_num))

            # Draw Planets
            p_rx, p_ry = self.house_centers[h_num]
            px = x + p_rx * w
            py = y + p_ry * h
            
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold)) # Slightly larger, bold font for planets
            
            # Stack planets vertically in the house center
            y_offset = - (len(houses[h_num]) * 16) / 2
            for p_info in houses[h_num]:
                p_str = p_info["str"]
                p_color = p_info["color"]
                
                painter.setPen(p_color)
                painter.setFont(QFont("Arial", 12, QFont.Weight.Bold))
                p_rect = QRectF(px - 40, py + y_offset, 80, 20)
                painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, p_str)
                
                self.hitboxes.append((p_rect, p_info["raw"]))
                
                fm = painter.fontMetrics()
                text_width = fm.horizontalAdvance(p_str)
                marker_x = px + text_width / 2 + 2
                
                # Draw Retrograde "R"
                if p_info["retro"]:
                    painter.setFont(QFont("Arial", 7, QFont.Weight.Bold))
                    painter.drawText(int(marker_x), int(py + y_offset + 9), "R")
                    marker_x += fm.horizontalAdvance("R") + 2
                    
                # Draw Exaltation / Debilitation
                if p_info["exalted"]:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(0, 180, 0)) # Green
                    t_y = py + y_offset + 10
                    poly = QPolygonF([
                        QPointF(marker_x, t_y + 3),
                        QPointF(marker_x + 6, t_y + 3),
                        QPointF(marker_x + 3, t_y - 4)
                    ])
                    painter.drawPolygon(poly)
                    marker_x += 8
                elif p_info["debilitated"]:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(220, 0, 0)) # Red
                    t_y = py + y_offset + 10
                    poly = QPolygonF([
                        QPointF(marker_x, t_y - 3),
                        QPointF(marker_x + 6, t_y - 3),
                        QPointF(marker_x + 3, t_y + 4)
                    ])
                    painter.drawPolygon(poly)
                    marker_x += 8
                    
                # Draw Combustion Flame
                if p_info["combust"]:
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.setBrush(QColor(255, 140, 0)) # Dark Orange
                    t_y = py + y_offset + 10
                    poly = QPolygonF([
                        QPointF(marker_x + 4, t_y - 5),
                        QPointF(marker_x + 8, t_y + 2),
                        QPointF(marker_x + 4, t_y + 6),
                        QPointF(marker_x, t_y + 2)
                    ])
                    painter.drawPolygon(poly)
                    
                    painter.setBrush(QColor(255, 220, 0)) # Inner yellow
                    poly_inner = QPolygonF([
                        QPointF(marker_x + 4, t_y - 1),
                        QPointF(marker_x + 6, t_y + 3),
                        QPointF(marker_x + 4, t_y + 5),
                        QPointF(marker_x + 2, t_y + 3)
                    ])
                    painter.drawPolygon(poly_inner)
                    
                    marker_x += 10
                    
                painter.setBrush(Qt.BrushStyle.NoBrush)
                y_offset += 16
                
        # Draw Aspects lines
        if self.show_aspects:
            self._draw_aspects(painter, x, y, w, h)

    def _get_planet_coord(self, house, w, h):
        rx, ry = self.house_centers[house]
        return rx * w, ry * h

    def _draw_aspect_line(self, painter, x1, y1, x2, y2, color_name, offset_idx=0):
        color_map = {
            "orange": QColor(255, 165, 0, 160),
            "blue": QColor(50, 150, 255, 160),
            "red": QColor(255, 50, 50, 160),
            "green": QColor(50, 255, 50, 160),
            "yellow": QColor(200, 180, 0, 180),
            "pink": QColor(255, 105, 180, 160),
            "purple": QColor(160, 32, 240, 160),
            "gray": QColor(150, 150, 150, 160)
        }
        
        color = color_map.get(color_name, QColor(255, 255, 255, 160))
            
        # Add slight visual offset so aspects from different planets in the same house don't perfectly overlap
        ox = (offset_idx % 3 - 1) * 4
        oy = ((offset_idx + 1) % 3 - 1) * 4
        x1 += ox; y1 += oy
        x2 += ox; y2 += oy
            
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0: return
        
        # Shrink lines at start and end so they don't block the house contents
        padding = 35
        if dist < padding * 2: return
        
        sx = x1 + (dx/dist) * padding
        sy = y1 + (dy/dist) * padding
        ex = x2 - (dx/dist) * padding
        ey = y2 - (dy/dist) * padding
        
        # Draw transparent line
        pen = QPen(color, 2.0, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawLine(int(sx), int(sy), int(ex), int(ey))
        
        # Draw Arrowhead
        angle = math.atan2(ey - sy, ex - sx)
        arrow_size = 9
        p1_x = ex - arrow_size * math.cos(angle - math.pi / 6)
        p1_y = ey - arrow_size * math.sin(angle - math.pi / 6)
        p2_x = ex - arrow_size * math.cos(angle + math.pi / 6)
        p2_y = ey - arrow_size * math.sin(angle + math.pi / 6)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(ex, ey), QPointF(p1_x, p1_y), QPointF(p2_x, p2_y)]))

    def _draw_aspects(self, painter, x, y, w, h):
        if not self.show_arrows or "aspects" not in self.chart_data:
            return
            
        for i, aspect in enumerate(self.chart_data["aspects"]):
            p_name = aspect["aspecting_planet"]
            
            # Filter based on user checkboxes
            if p_name not in self.visible_aspect_planets:
                continue
            if p_name in ["Rahu", "Ketu"] and not self.show_rahu_ketu:
                continue
            
            h1 = aspect["source_house"]
            h2 = aspect["target_house"]
            
            if h1 == h2:
                continue 
                
            rx1, ry1 = self._get_planet_coord(h1, w, h)
            rx2, ry2 = self._get_planet_coord(h2, w, h)
            
            self._draw_aspect_line(painter, x + rx1, y + ry1, x + rx2, y + ry2, aspect["color"], offset_idx=i)

    def mouseMoveEvent(self, event):
        if not self.chart_data:
            if self.tooltip_label.isVisible():
                self.tooltip_label.hide()
            return
            
        pos = event.position()
        tooltip_html = ""
        
        # Helper for ordinal numbers
        def ordinal(n):
            if 11 <= (n % 100) <= 13: return str(n) + 'th'
            return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        # 1. Check Planets (Highest Priority)
        for rect, p_raw in self.hitboxes:
            if rect.contains(pos):
                name = p_raw["name"]
                sign_name = zodiac_names[p_raw["sign_index"]]
                house = p_raw.get("house", "-")
                
                # Status
                status_list = []
                if name in ["Rahu", "Ketu"]:
                    status_list.append("Retrograde")
                elif p_raw.get("retro") and name != "Ascendant":
                    status_list.append("Retrograde")
                elif name != "Ascendant":
                    status_list.append("Direct")
                    
                if p_raw.get("combust"):
                    status_list.append("Combust")
                    
                status_str = ", ".join(status_list)
                
                # Dignity
                dignity_list = []
                if p_raw.get("exalted"): dignity_list.append("Exalted")
                if p_raw.get("debilitated"): dignity_list.append("Debilitated")
                if p_raw.get("own_sign"): dignity_list.append("Own Sign")
                dignity_str = ", ".join(dignity_list)
                
                # Longitude
                deg = int(p_raw["deg_in_sign"])
                mins = int((p_raw["deg_in_sign"] - deg) * 60)
                long_str = f"{deg}°{mins:02d}'"
                
                html = f"<b>{name}</b><hr style='margin: 4px 0;'/>"
                html += f"Sign: {sign_name}<br>"
                if house != "-": html += f"House: {house}<br>"
                if status_str: html += f"Status: {status_str}<br>"
                if dignity_str: html += f"Dignity: {dignity_str}<br>"
                html += f"Longitude: {long_str}"
                
                tooltip_html = html
                break
                
        # 2. Check Houses (If no planet was hovered)
        if not tooltip_html:
            for h_num, poly in self.house_polys.items():
                if poly.containsPoint(pos, Qt.FillRule.OddEvenFill):
                    # Calculate which sign is in this house
                    sign_in_house = (self.chart_data["ascendant"]["sign_index"] + h_num - 1) % 12 + 1
                    
                    # Determine Moolatrikona / Lordship Preferences
                    # 10=Capricorn, 12=Pisces, 8=Scorpio, 2=Taurus, 3=Gemini are the non-preferred signs
                    non_preferred_signs = {10, 12, 8, 2, 3}
                    is_not_preferred = sign_in_house in non_preferred_signs
                    
                    # 1. House Title & Preference
                    html = f"<b>{ordinal(h_num)} House</b>"
                    if is_not_preferred:
                        html += " <b style='color: red;'>NOT preferred</b>"
                    html += "<hr style='margin: 4px 0;'/>"
                    
                    # 2. Lord Placement
                    sign_rulers = {
                        1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun",
                        6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter",
                        10: "Saturn", 11: "Saturn", 12: "Jupiter"
                    }
                    lord_name = sign_rulers.get(sign_in_house)
                    lord_p = next((p for p in self.chart_data["planets"] if p["name"] == lord_name), None)
                    
                    if lord_p:
                        lord_status = []
                        if lord_p.get("combust"): lord_status.append("combust")
                        if lord_p.get("retro") and lord_name not in ["Rahu", "Ketu"]: lord_status.append("retrograde")
                        if lord_p.get("exalted"): lord_status.append("exalted")
                        if lord_p.get("debilitated"): lord_status.append("debilitated")
                        
                        status_str = f", {', '.join(lord_status)}" if lord_status else ""
                        html += f"=&gt; lord ({lord_name}{status_str}) in {ordinal(lord_p['house'])} house"

                    # 3. Aspecting Planets
                    aspecting_planets = []
                    for aspect in self.chart_data.get("aspects", []):
                        if aspect["target_house"] == h_num:
                            aspecting_planets.append(aspect["aspecting_planet"])
                            
                    if aspecting_planets:
                        html += f"<br><br>Aspected by:<br><br>"
                        
                        aspect_blocks = []
                        for ap_name in aspecting_planets:
                            ap_p = next((p for p in self.chart_data["planets"] if p["name"] == ap_name), None)
                            if ap_p:
                                ap_status = []
                                if ap_p.get("combust"): ap_status.append("Combust")
                                if ap_p.get("retro") and ap_name not in ["Rahu", "Ketu"]: ap_status.append("Retrograde")
                                if ap_name in ["Rahu", "Ketu"]: ap_status.append("Retrograde")
                                if ap_p.get("exalted"): ap_status.append("Exalted")
                                if ap_p.get("debilitated"): ap_status.append("Debilitated")
                                if ap_p.get("own_sign"): ap_status.append("Own Sign")
                                
                                status_part = f" ({', '.join(ap_status)})" if ap_status else ""
                                block = f"-&gt; <b>{ap_name}</b>{status_part}"
                                
                                lords = ap_p.get("lord_of", [])
                                if lords:
                                    lords_str = " AND ".join([f"{ordinal(l)} house lord" for l in lords])
                                    block += f"<br><span style='color: #555;'>{lords_str}</span>"
                                aspect_blocks.append(block)
                                
                        html += "<br><br>".join(aspect_blocks)
                        
                    tooltip_html = html
                    break
                
        if tooltip_html:
            # Update text only if it changes to avoid unnecessary layout recalculations
            if self.tooltip_label.text() != tooltip_html:
                self.tooltip_label.setText(tooltip_html)
                self.tooltip_label.adjustSize()
                
            global_pos = event.globalPosition().toPoint()
            
            # Use screen geometry to avoid going off-screen
            screen = self.screen().availableGeometry() if self.screen() else QApplication.primaryScreen().availableGeometry()
            label_w = self.tooltip_label.width()
            label_h = self.tooltip_label.height()
            
            x = global_pos.x() + 15
            y = global_pos.y() + 15
            
            # Adjust to keep tooltip inside the screen boundaries
            if x + label_w > screen.right():
                x = global_pos.x() - label_w - 5
            if y + label_h > screen.bottom():
                y = global_pos.y() - label_h - 5
                
            self.tooltip_label.move(x, y)
            
            if not self.tooltip_label.isVisible():
                self.tooltip_label.show()
        else:
            if self.tooltip_label.isVisible():
                self.tooltip_label.hide()

    def leaveEvent(self, event):
        if hasattr(self, 'tooltip_label') and self.tooltip_label.isVisible():
            self.tooltip_label.hide()
        super().leaveEvent(event)


# ==========================================
# 5. MAIN APPLICATION GUI
# ==========================================
class AstroApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vedic Astrology Diamond Chart Pro")
        self.resize(1100, 700)

        # Core Engines
        self.ephemeris = EphemerisEngine()
        self.time_ctrl = TimeController()
        
        # State variables
        self.current_lat = 28.6139
        self.current_lon = 77.2090
        self.current_tz = "Asia/Kolkata"
        self.is_updating_ui = False
        self.is_loading_settings = True # Guard to prevent saving while initializing
        self.is_chart_saved = True # Tracks if the chart has unsaved changes

        self._init_ui()
        self._connect_signals()
        
        # Load user preferences from JSON
        self.load_settings()
        self.is_loading_settings = False
        
        # Initialize default chart if time isn't set yet
        self.time_ctrl.set_time(datetime.datetime.now())

    def load_settings(self):
        settings_file = "astro_settings.json"
        if not os.path.exists(settings_file):
            return
            
        try:
            with open(settings_file, "r") as f:
                prefs = json.load(f)
                
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
            
            if "aspect_planets" in prefs:
                for p, is_checked in prefs["aspect_planets"].items():
                    if p in self.aspect_cb:
                        self.aspect_cb[p].setChecked(is_checked)
                        
            self.update_settings()
            self.toggle_details()
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def save_settings(self):
        if getattr(self, 'is_loading_settings', True): return
        
        prefs = {
            "location": self.loc_input.text(),
            "lat": self.current_lat,
            "lon": self.current_lon,
            "tz": self.current_tz,
            "ayanamsa": self.cb_ayanamsa.currentText(),
            "use_symbols": self.chk_symbols.isChecked(),
            "show_rahu_ketu": self.chk_rahu.isChecked(),
            "show_arrows": self.chk_arrows.isChecked(),
            "use_tint": self.chk_tint.isChecked(),
            "show_aspects": self.chk_aspects.isChecked(),
            "show_details": self.chk_details.isChecked(),
            "aspect_planets": {p: cb.isChecked() for p, cb in self.aspect_cb.items()}
        }
        try:
            with open("astro_settings.json", "w") as f:
                json.dump(prefs, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create Main Splitter for Horizontal Resizing
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        # Left Panel wrapped in a Scroll Area (fixes geometry warnings)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(320)
        
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # 1. Location Group
        loc_group = QGroupBox("Location Settings")
        loc_layout = QVBoxLayout()
        
        search_layout = QHBoxLayout()
        self.loc_input = QLineEdit("New Delhi, India")
        self.loc_btn = QPushButton("Search")
        search_layout.addWidget(self.loc_input)
        search_layout.addWidget(self.loc_btn)
        
        self.loc_status = QLabel("Lat: 28.61, Lon: 77.21\nTZ: Asia/Kolkata")
        
        loc_layout.addLayout(search_layout)
        loc_layout.addWidget(self.loc_status)
        loc_group.setLayout(loc_layout)

        # 2. Date & Time Group
        dt_group = QGroupBox("Date & Time")
        dt_layout = QVBoxLayout()
        
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        
        dt_layout.addWidget(QLabel("Date:"))
        dt_layout.addWidget(self.date_edit)
        dt_layout.addWidget(QLabel("Time:"))
        dt_layout.addWidget(self.time_edit)
        dt_group.setLayout(dt_layout)

        # 3. Time Navigation Group
        nav_group = QGroupBox("Time Animation")
        nav_layout = QVBoxLayout()
        
        btn_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ Play")
        btn_layout.addWidget(self.btn_play)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1x (Realtime)", "60x (1m/s)", "3600x (1h/s)", "86400x (1d/s)"])
        btn_layout.addWidget(self.speed_combo)
        
        step_layout1 = QHBoxLayout()
        self.btn_sub_d = QPushButton("-1d")
        self.btn_sub_h = QPushButton("-1h")
        self.btn_sub_m = QPushButton("-1m")
        step_layout1.addWidget(self.btn_sub_d)
        step_layout1.addWidget(self.btn_sub_h)
        step_layout1.addWidget(self.btn_sub_m)
        
        step_layout2 = QHBoxLayout()
        self.btn_add_m = QPushButton("+1m")
        self.btn_add_h = QPushButton("+1h")
        self.btn_add_d = QPushButton("+1d")
        step_layout2.addWidget(self.btn_add_m)
        step_layout2.addWidget(self.btn_add_h)
        step_layout2.addWidget(self.btn_add_d)

        nav_layout.addLayout(btn_layout)
        nav_layout.addLayout(step_layout1)
        nav_layout.addLayout(step_layout2)
        nav_group.setLayout(nav_layout)

        # 4. Settings Group
        set_group = QGroupBox("Chart Settings")
        set_layout = QVBoxLayout()
        
        self.cb_ayanamsa = QComboBox()
        self.cb_ayanamsa.addItems(["Lahiri", "Raman", "Fagan/Bradley"])
        
        self.chk_symbols = QCheckBox("Use Astro Symbols")
        self.chk_rahu = QCheckBox("Show Rahu/Ketu")
        self.chk_rahu.setChecked(True)
        self.chk_aspects = QCheckBox("Show Planetary Aspects (Drishti)")
        self.chk_arrows = QCheckBox("Show Aspect Lines & Arrows")
        self.chk_arrows.setChecked(True)
        self.chk_tint = QCheckBox("Use Aspect Tint")
        self.chk_tint.setChecked(True)
        self.chk_details = QCheckBox("Show Details (Table)")
        self.chk_details.setChecked(True)
        
        self.btn_save_chart = QPushButton("Save Chart...")
        self.btn_load_chart = QPushButton("Load Chart...")
        self.btn_export = QPushButton("Export PNG...")

        set_layout.addWidget(QLabel("Ayanamsa:"))
        set_layout.addWidget(self.cb_ayanamsa)
        set_layout.addWidget(self.chk_symbols)
        set_layout.addWidget(self.chk_rahu)
        set_layout.addWidget(self.chk_aspects)
        set_layout.addWidget(self.chk_arrows)
        set_layout.addWidget(self.chk_tint)
        set_layout.addWidget(self.chk_details)
        
        file_btns = QHBoxLayout()
        file_btns.addWidget(self.btn_save_chart)
        file_btns.addWidget(self.btn_load_chart)
        set_layout.addLayout(file_btns)
        
        set_layout.addWidget(self.btn_export)
        set_group.setLayout(set_layout)

        # 5. Aspect Planet Filters Group
        self.aspects_group = QGroupBox("Aspects From:")
        aspects_layout = QGridLayout()
        self.aspect_cb = {}
        
        planets_data = [
            ("Sun", "#FFA500"), ("Moon", "#3399FF"), ("Mars", "#FF3333"),
            ("Mercury", "#33AA33"), ("Jupiter", "#CCCC00"), ("Venus", "#FF66B2"),
            ("Saturn", "#800080"), ("Rahu", "#888888"), ("Ketu", "#888888")
        ]
        
        for i, (p, color) in enumerate(planets_data):
            cb = QCheckBox(p)
            cb.setStyleSheet(f"color: {color}; font-weight: bold;")
            cb.setChecked(True) # Enabled by default
            cb.stateChanged.connect(self.update_settings)
            self.aspect_cb[p] = cb
            aspects_layout.addWidget(cb, i // 3, i % 3)
            
        self.aspects_group.setLayout(aspects_layout)
        self.aspects_group.setVisible(False)

        # Add to left layout
        left_layout.addWidget(loc_group)
        left_layout.addWidget(dt_group)
        left_layout.addWidget(nav_group)
        left_layout.addWidget(set_group)
        left_layout.addWidget(self.aspects_group)
        left_layout.addStretch()
        
        # Set the left panel inside the scroll area
        left_scroll.setWidget(left_panel)

        # Right Panel (Splitter for Chart and Table)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Chart
        self.chart = ChartRenderer()
        right_splitter.addWidget(self.chart)
        
        # Info Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Planet", "Sign", "Degree", "House", "Retrograde"])
        
        header = self.table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            
        right_splitter.addWidget(self.table)
        right_splitter.setSizes([500, 200])

        self.table.setVisible(self.chk_details.isChecked())

        # Add scroll area and right panel to main splitter
        main_splitter.addWidget(left_scroll)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([350, 750])

    def _connect_signals(self):
        # Location
        self.loc_btn.clicked.connect(self.search_location)
        self.loc_input.returnPressed.connect(self.search_location)
        
        # Time Controller
        self.time_ctrl.time_changed.connect(self.on_time_changed)
        
        # UI Time Edits
        self.date_edit.dateChanged.connect(self.on_ui_datetime_changed)
        self.time_edit.timeChanged.connect(self.on_ui_datetime_changed)
        
        # Animation
        self.btn_play.clicked.connect(self.toggle_play)
        self.speed_combo.currentIndexChanged.connect(self.change_speed)
        
        # Step buttons
        self.btn_add_m.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(minutes=1)))
        self.btn_add_h.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(hours=1)))
        self.btn_add_d.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(days=1)))
        self.btn_sub_m.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(minutes=-1)))
        self.btn_sub_h.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(hours=-1)))
        self.btn_sub_d.clicked.connect(lambda: self.time_ctrl.step(datetime.timedelta(days=-1)))
        
        # Settings
        self.cb_ayanamsa.currentTextChanged.connect(self.update_settings)
        self.chk_symbols.stateChanged.connect(self.update_settings)
        self.chk_rahu.stateChanged.connect(self.update_settings)
        self.chk_aspects.stateChanged.connect(self.toggle_aspects)
        self.chk_arrows.stateChanged.connect(self.update_settings)
        self.chk_tint.stateChanged.connect(self.update_settings)
        self.chk_details.stateChanged.connect(self.toggle_details)
        self.btn_save_chart.clicked.connect(self.save_chart_dialog)
        self.btn_load_chart.clicked.connect(self.load_chart_dialog)
        self.btn_export.clicked.connect(self.export_chart)

    def search_location(self):
        self.loc_btn.setEnabled(False)
        self.loc_btn.setText("Searching...")
        self.loc_worker = LocationWorker(self.loc_input.text())
        self.loc_worker.result_ready.connect(self.on_location_found)
        self.loc_worker.error_occurred.connect(self.on_location_error)
        self.loc_worker.start()

    def on_location_found(self, lat, lon, tz_name, name):
        self.current_lat = lat
        self.current_lon = lon
        self.current_tz = tz_name
        self.loc_status.setText(f"Lat: {lat:.2f}, Lon: {lon:.2f}\nTZ: {tz_name}")
        self.loc_btn.setEnabled(True)
        self.loc_btn.setText("Search")
        self.save_settings()
        self.recalculate()

    def on_location_error(self, err_msg):
        QMessageBox.warning(self, "Location Error", err_msg)
        self.loc_btn.setEnabled(True)
        self.loc_btn.setText("Search")

    def on_time_changed(self, dt):
        self.is_updating_ui = True
        self.date_edit.setDate(QDate(dt.year, dt.month, dt.day))
        self.time_edit.setTime(QTime(dt.hour, dt.minute, dt.second))
        self.is_updating_ui = False
        self.recalculate()

    def on_ui_datetime_changed(self):
        if self.is_updating_ui: return
        d = self.date_edit.date()
        t = self.time_edit.time()
        dt = datetime.datetime(d.year(), d.month(), d.day(), t.hour(), t.minute(), t.second())
        self.time_ctrl.set_time(dt)

    def toggle_play(self):
        playing = self.time_ctrl.toggle_animation()
        self.btn_play.setText("⏸ Pause" if playing else "▶ Play")

    def change_speed(self):
        idx = self.speed_combo.currentIndex()
        speeds = [1.0, 60.0, 3600.0, 86400.0]
        self.time_ctrl.set_speed(speeds[idx])

    def update_settings(self):
        if self.is_updating_ui: return
        self.ephemeris.set_ayanamsa(self.cb_ayanamsa.currentText())
        self.chart.use_symbols = self.chk_symbols.isChecked()
        self.chart.show_rahu_ketu = self.chk_rahu.isChecked()
        self.chart.show_aspects = self.chk_aspects.isChecked()
        self.chart.show_arrows = self.chk_arrows.isChecked()
        self.chart.use_tint = self.chk_tint.isChecked()
        
        # Update which planets are selected for aspect drawing
        visible_aspects = set()
        for p, cb in self.aspect_cb.items():
            if cb.isChecked():
                visible_aspects.add(p)
        self.chart.visible_aspect_planets = visible_aspects
        
        self.save_settings()
        self.recalculate()

    def toggle_aspects(self):
        is_checked = self.chk_aspects.isChecked()
        self.aspects_group.setVisible(is_checked)
        self.chk_arrows.setVisible(is_checked)
        self.chk_tint.setVisible(is_checked)
        self.update_settings()

    def toggle_details(self):
        self.table.setVisible(self.chk_details.isChecked())
        self.save_settings()

    def get_current_chart_info(self):
        return {
            "location": self.loc_input.text(),
            "lat": self.current_lat,
            "lon": self.current_lon,
            "tz": self.current_tz,
            "datetime": self.time_ctrl.current_time.isoformat()
        }

    def save_chart_dialog(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "", "JSON Files (*.json);;All Files (*)")
        if path:
            if save_prefs.save_chart_to_file(path, self.get_current_chart_info()):
                self.is_chart_saved = True
                QMessageBox.information(self, "Success", "Chart saved successfully.")

    def load_chart_dialog(self):
        path, _ = QFileDialog.getOpenFileName(self, "Load Chart", "", "JSON Files (*.json);;All Files (*)")
        if path:
            data = save_prefs.load_chart_from_file(path)
            if data:
                self.is_updating_ui = True
                self.loc_input.setText(data.get("location", "New Delhi, India"))
                self.current_lat = data.get("lat", 28.6139)
                self.current_lon = data.get("lon", 77.2090)
                self.current_tz = data.get("tz", "Asia/Kolkata")
                self.loc_status.setText(f"Lat: {self.current_lat:.2f}, Lon: {self.current_lon:.2f}\nTZ: {self.current_tz}")
                
                try:
                    dt = datetime.datetime.fromisoformat(data["datetime"])
                    self.time_ctrl.set_time(dt)
                except Exception as e:
                    print(f"Error parsing date from file: {e}")
                    
                self.is_updating_ui = False
                self.save_settings()
                self.recalculate()
                self.is_chart_saved = True
            else:
                QMessageBox.warning(self, "Error", "Failed to load chart data.")

    def closeEvent(self, event):
        if not getattr(self, "is_chart_saved", True):
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            tmp_filename = f"tmp_001_saveon_{now_str}.json"
            save_prefs.save_chart_to_file(tmp_filename, self.get_current_chart_info())
            print(f"Unsaved changes auto-saved to {tmp_filename}")
        super().closeEvent(event)

    def export_chart(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart", "", "PNG Files (*.png);;All Files (*)")
        if path:
            pixmap = self.chart.grab()
            pixmap.save(path, "PNG")

    def recalculate(self):
        dt = self.time_ctrl.current_time
        try:
            chart_data = self.ephemeris.calculate_chart(dt, self.current_lat, self.current_lon, self.current_tz)
            self.chart.update_chart(chart_data)
            self.update_table(chart_data)
            
            # Mark chart as modified (unsaved) whenever it recalculates
            if not self.is_loading_settings:
                self.is_chart_saved = False
        except Exception as e:
            print(f"Calculation Error: {e}")

    def update_table(self, chart_data):
        self.table.setRowCount(0)
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
                        "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        
        # Add Ascendant row
        asc = chart_data["ascendant"]
        self.table.insertRow(0)
        self.table.setItem(0, 0, QTableWidgetItem("Ascendant"))
        self.table.setItem(0, 1, QTableWidgetItem(zodiac_names[asc["sign_index"]]))
        self.table.setItem(0, 2, QTableWidgetItem(f"{asc['degree'] % 30:.2f}°"))
        self.table.setItem(0, 3, QTableWidgetItem("1"))
        self.table.setItem(0, 4, QTableWidgetItem("-"))

        # Add Planets
        for i, p in enumerate(chart_data["planets"]):
            row = i + 1
            if p["name"] in ["Rahu", "Ketu"] and not self.chk_rahu.isChecked():
                continue
                
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p["name"]))
            self.table.setItem(row, 1, QTableWidgetItem(zodiac_names[p["sign_index"]]))
            self.table.setItem(row, 2, QTableWidgetItem(f"{p['deg_in_sign']:.2f}°"))
            self.table.setItem(row, 3, QTableWidgetItem(str(p["house"])))
            self.table.setItem(row, 4, QTableWidgetItem("Yes" if p["retro"] else "No"))


# ==========================================
# 6. APP EXECUTION
# ==========================================
GLOBAL_FONT_FAMILY = "Segoe UI"  # Change this to your preferred font
GLOBAL_FONT_SCALE = 11           # Base font size for the whole app
GLOBAL_PRIMARY_COLOR = "#4A90E2" # Main theme/accent color code

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Apply Global Font and Style
    font = QFont(GLOBAL_FONT_FAMILY, GLOBAL_FONT_SCALE)
    app.setFont(font)
    app.setStyle("Fusion")
    
    # Inject primary color into UI elements
    app.setStyleSheet(f"""
        QGroupBox::title {{ color: {GLOBAL_PRIMARY_COLOR}; font-weight: bold; }}
        QPushButton:checked {{ background-color: {GLOBAL_PRIMARY_COLOR}; color: white; }}
    """)
    
    window = AstroApp()
    window.show()
    sys.exit(app.exec())