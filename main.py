#main.py

import sys,datetime,json,os,math,pytz,swisseph as swe,time,multiprocessing,queue,glob,copy,importlib.util

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel, QLineEdit, QPushButton, QComboBox, QTimeEdit, QTableWidget, QTableWidgetItem, QCheckBox,QHeaderView, QMessageBox, QGroupBox, QFileDialog,QScrollArea, QGridLayout, QSpinBox, QDialog, QTextBrowser,QDoubleSpinBox, QTabWidget, QSizePolicy, QAbstractItemView, QMenu)
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygonF, QCursor, QIcon, QPainterPath, QPixmap
from PyQt6.QtCore import Qt, QDate, QTime, QThread, pyqtSignal, QRectF, QPointF, QObject, QTimer, QEvent, QFileSystemWatcher
from PyQt6.QtGui import QDrag
from PyQt6.QtCore import QMimeData, QPoint

from astral import LocationInfo
from astral.sun import sun
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

#own file dependencies, need not to be changed
import save_prefs,animation,astro_engine
import help_content
try:
    import custom_vargas
    HAS_CUSTOM_VARGAS = True
except ImportError:
    HAS_CUSTOM_VARGAS = False

# ==========================================
# GLOBAL SETTINGS & STYLES
# ==========================================
GLOBAL_FONT_FAMILY = "Segoe UI"
GLOBAL_UI_FONT_FAMILY = GLOBAL_FONT_FAMILY
GLOBAL_CHART_FONT_FAMILY = "Arial"
GLOBAL_RASHI_FONT_FAMILY = "Arial"
GLOBAL_HOUSE_FONT_FAMILY = "Arial"
GLOBAL_EMOJI_FONT_FAMILY = "Segoe UI Emoji"
GLOBAL_FONT_SCALE_MULTIPLIER = 1.0
GLOBAL_PRIMARY_COLOR = "#0026ff"

def resource_path(relative_path):
    try: base_path = sys._MEIPASS
    except Exception: base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==========================================
# CUSTOM UI WIDGETS & DIALOGS
# ==========================================

class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event): event.ignore()

class SmoothScroller(QObject):
    def __init__(self, scroll_area, speed=0.15, fps=60):
        super().__init__(scroll_area)
        self.scroll_area = scroll_area
        self.speed = speed
        self._is_animating_step = False
        
        # Required to make items in tables/lists scroll smoothly per pixel
        if isinstance(scroll_area, QAbstractItemView):
            scroll_area.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            scroll_area.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
            
        self._vbar = scroll_area.verticalScrollBar()
        self._hbar = scroll_area.horizontalScrollBar()
        
        self.target_v = float(self._vbar.value())
        self.target_h = float(self._hbar.value())
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        
        # Attach listener directly to viewport
        self.scroll_area.viewport().installEventFilter(self)
        
        self._vbar.valueChanged.connect(self._on_v_changed)
        self._hbar.valueChanged.connect(self._on_h_changed)
        
    def _on_v_changed(self, val):
        if not self._is_animating_step:
            self.target_v = float(val)
            
    def _on_h_changed(self, val):
        if not self._is_animating_step:
            self.target_h = float(val)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            v_delta = event.angleDelta().y()
            h_delta = event.angleDelta().x()
            
            if v_delta == 0 and h_delta == 0:
                return False
                
            # AngleDelta is typically 120 per notch. Set multiplier to ~0.8 to give approx 96px scrolls per notch.
            step_size = 0.8  
            self.target_v -= float(v_delta) * step_size
            self.target_h -= float(h_delta) * step_size
            
            # Constrain targets instantly
            self.target_v = max(float(self._vbar.minimum()), min(self.target_v, float(self._vbar.maximum())))
            self.target_h = max(float(self._hbar.minimum()), min(self.target_h, float(self._hbar.maximum())))
            
            if not self.timer.isActive():
                self.timer.start(1000 // 60)
            return True
        return super().eventFilter(obj, event)

    def _animate(self):
        # Allow dragging the physical scrollbar to halt animation immediately
        if self._vbar.isSliderDown() or self._hbar.isSliderDown():
            self.timer.stop()
            self.target_v = float(self._vbar.value())
            self.target_h = float(self._hbar.value())
            return
            
        # Re-constrain in case bounds changed while animating
        self.target_v = max(float(self._vbar.minimum()), min(self.target_v, float(self._vbar.maximum())))
        self.target_h = max(float(self._hbar.minimum()), min(self.target_h, float(self._hbar.maximum())))
        
        v_val = float(self._vbar.value())
        h_val = float(self._hbar.value())
        
        v_diff = self.target_v - v_val
        h_diff = self.target_h - h_val
        
        # Halt once comfortably close to target
        if abs(v_diff) < 0.5 and abs(h_diff) < 0.5:
            self._is_animating_step = True
            self._vbar.setValue(int(round(self.target_v)))
            self._hbar.setValue(int(round(self.target_h)))
            self._is_animating_step = False
            self.timer.stop()
            return
            
        new_v = v_val + v_diff * self.speed
        new_h = h_val + h_diff * self.speed
        
        self._is_animating_step = True
        self._vbar.setValue(int(round(new_v)))
        self._hbar.setValue(int(round(new_h)))
        self._is_animating_step = False

class VisualGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chart Visual Guide, Legend, credits and Privacy Policy")
        self.resize(850, 700)
        
        # Dynamically fetch the default system font
        sys_font = QApplication.font().family()
        
        # Global style for the dialog and text browser using the system font
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #f7fafc;
            }}
            QTextBrowser {{ 
                background-color: #ffffff; 
                padding: 20px; 
                font-family: "{sys_font}", system-ui, sans-serif;
                font-size: {int(14 * GLOBAL_FONT_SCALE_MULTIPLIER)}px; 
                line-height: 1.6; 
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        
        # --- Modernized Tab Widget Styling ---
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid #e2e8f0;background-color: #ffffff;border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;border-top-right-radius: 8px;
                top: -1px; /* Overlaps with the tab bar to hide the bottom border of the selected tab */
            }}
            QTabBar::tab {{
                font-family: "{sys_font}", sans-serif;font-size: {int(13 * GLOBAL_FONT_SCALE_MULTIPLIER)}px;
                background-color: #f7fafc;color: #718096;padding: 10px 24px;
                border: 1px solid #e2e8f0;border-bottom: none;border-top-left-radius: 8px;
                border-top-right-radius: 8px;margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: #ffffff;color: #2b6cb0;font-weight: bold;
                border-bottom: 1px solid #ffffff; /* Creates a seamless merge with the pane below */
            }}
            QTabBar::tab:hover:!selected {{
                background-color: #edf2f7;color: #2d3748;
            }}
        """)
        # --- Tab 1: Core Basics ---
        t1 = QTextBrowser()
        t1.setHtml(help_content.tab1_basics_html)
        self.t1_scroller = SmoothScroller(t1)
        tabs.addTab(t1, "Basics and Setup")

        # --- Tab 2: Visuals ---
        t2 = QTextBrowser()
        t2.setHtml(help_content.tab2_visuals_html)
        self.t2_scroller = SmoothScroller(t2)
        tabs.addTab(t2, "Visuals")

        # --- Tab 3: Animation ---
        t3 = QTextBrowser()
        t3.setHtml(help_content.tab3_animation_html)
        self.t3_scroller = SmoothScroller(t3)
        tabs.addTab(t3, "Animation")

        # --- Tab 4: Plugins ---
        t4 = QTextBrowser()
        t4.setHtml(help_content.tab4_plugins_html)
        self.t4_scroller = SmoothScroller(t4)
        tabs.addTab(t4, "Plugins")
        
        # --- Tab 5: Credits & Info  ---
        t5 = QTextBrowser()
        t5.setHtml(help_content.credits_html)
        self.t5_scroller = SmoothScroller(t5) 
        tabs.addTab(t5, "Credits")

        # --- Tab 6: Privacy ---
        t6 = QTextBrowser()
        t6.setHtml(help_content.privacy_html)
        self.t6_scroller = SmoothScroller(t6) 
        tabs.addTab(t6, "Privacy")
        
        layout.addWidget(tabs)
        
        # --- Bottom Button Box ---
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        
        # Modernize the button slightly to match the new UI
        close_btn = QPushButton("Close Guide")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                font-family: "{sys_font}", sans-serif;background-color: #e2e8f0;
                border: none;padding: 5px 10px;border-radius: 10px;
                font-weight: bold;color: #4a5568;
            }}
            QPushButton:hover {{
                background-color: #cbd5e0;
            }}
        """)
        close_btn.clicked.connect(self.accept)
        
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)

class CustomLocationDialog(QDialog):
    def __init__(self, lat, lon, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Custom Coordinates")
        self.resize(250, 150)
        layout = QGridLayout(self)
        
        layout.addWidget(QLabel("Latitude:"), 0, 0)
        self.lat_spin = QDoubleSpinBox(); self.lat_spin.setRange(-90.0, 90.0); self.lat_spin.setDecimals(4); self.lat_spin.setValue(lat)
        layout.addWidget(self.lat_spin, 0, 1)

        layout.addWidget(QLabel("Longitude:"), 1, 0)
        self.lon_spin = QDoubleSpinBox(); self.lon_spin.setRange(-180.0, 180.0); self.lon_spin.setDecimals(4); self.lon_spin.setValue(lon)
        layout.addWidget(self.lon_spin, 1, 1)

        btn_layout = QHBoxLayout()
        ok_btn, cancel_btn = QPushButton("OK"), QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept); cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn); btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout, 2, 0, 1, 2)

    def get_coordinates(self): return self.lat_spin.value(), self.lon_spin.value()

# ==========================================
# THREAD WORKERS & RENDERING ENGINE
# ==========================================

class LocationWorker(QThread):
    result_ready = pyqtSignal(float, float, str, str); error_occurred = pyqtSignal(str)
    def __init__(self, location_name): super().__init__(); self.location_name = location_name
    def run(self):
        try:
            location = Nominatim(user_agent="astro_basics").geocode(self.location_name, timeout=10)
            if location: self.result_ready.emit(location.latitude, location.longitude, TimezoneFinder().timezone_at(lng=location.longitude, lat=location.latitude) or "UTC", location.address)
            else: self.error_occurred.emit("Location not found.")
        except Exception as e: self.error_occurred.emit(f"Network Error: {str(e)}")

class ButtonTimeWorker(QThread):
    partial_result = pyqtSignal(str, object)
    results_ready = pyqtSignal(dict)
    
    def __init__(self, jd_utc, lat, lon, frozen_planets, transit_div, transit_planet, ayanamsa, custom_vargas):
        super().__init__()
        self.jd_utc, self.lat, self.lon = jd_utc, lat, lon
        self.frozen_planets = copy.deepcopy(frozen_planets)
        self.transit_div, self.transit_planet = transit_div, transit_planet
        self.ayanamsa, self.custom_vargas = ayanamsa, custom_vargas
        self.stop_flag = False

    def run(self):
        res = {'asc_prev': None, 'asc_next': None, 'p_prev': None, 'p_next': None}
        try:
            engine = astro_engine.EphemerisEngine()
            engine.set_ayanamsa(self.ayanamsa)
            engine.set_custom_vargas(self.custom_vargas)
            zodiacs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            
            class DummyStop:
                def __init__(self, worker): self.worker = worker
                def is_set(self): return self.worker.stop_flag
            ds = DummyStop(self)

            if "Ascendant" in self.frozen_planets and self.frozen_planets["Ascendant"]["div"] == self.transit_div:
                asc_tgt_sign = zodiacs[self.frozen_planets["Ascendant"]["sign_idx"]]
            else:
                asc_tgt_sign = "Any Rashi"

            res['asc_prev'] = engine.search_transit_core(self.jd_utc, self.lat, self.lon, "Ascendant", -1, self.transit_div, copy.deepcopy(self.frozen_planets), asc_tgt_sign, ds)
            if self.stop_flag: return
            self.partial_result.emit('asc_prev', res['asc_prev'])

            res['asc_next'] = engine.search_transit_core(self.jd_utc, self.lat, self.lon, "Ascendant", 1, self.transit_div, copy.deepcopy(self.frozen_planets), asc_tgt_sign, ds)
            if self.stop_flag: return
            self.partial_result.emit('asc_next', res['asc_next'])

            if self.transit_planet in self.frozen_planets and self.frozen_planets[self.transit_planet]["div"] == self.transit_div:
                p_tgt_sign = zodiacs[self.frozen_planets[self.transit_planet]["sign_idx"]]
            else:
                p_tgt_sign = "Any Rashi"

            res['p_prev'] = engine.search_transit_core(self.jd_utc, self.lat, self.lon, self.transit_planet, -1, self.transit_div, copy.deepcopy(self.frozen_planets), p_tgt_sign, ds)
            if self.stop_flag: return
            self.partial_result.emit('p_prev', res['p_prev'])

            res['p_next'] = engine.search_transit_core(self.jd_utc, self.lat, self.lon, self.transit_planet, 1, self.transit_div, copy.deepcopy(self.frozen_planets), p_tgt_sign, ds)
            if self.stop_flag: return
            self.partial_result.emit('p_next', res['p_next'])

        except Exception as e:
            print(f"Background Transit Worker error: {e}")
        finally:
            if not self.stop_flag:
                self.results_ready.emit(res)

class JumpSearchWorker(QThread):
    finished = pyqtSignal(object)
    
    def __init__(self, engine, jd_utc, lat, lon, body_name, direction, transit_div, frozen_planets, tgt_sign):
        super().__init__()
        self.engine = engine
        self.jd_utc = jd_utc
        self.lat = lat
        self.lon = lon
        self.body_name = body_name
        self.direction = direction
        self.transit_div = transit_div
        self.frozen_planets = copy.deepcopy(frozen_planets)
        self.tgt_sign = tgt_sign
        self.stop_flag = False

    def run(self):
        class DummyStop:
            def __init__(self, worker): self.worker = worker
            def is_set(self): return self.worker.stop_flag
        
        ds = DummyStop(self)
        result = self.engine.search_transit_core(
            self.jd_utc, self.lat, self.lon, self.body_name, self.direction, 
            self.transit_div, self.frozen_planets, self.tgt_sign, ds
        )
        if not self.stop_flag:
            self.finished.emit(result)

class ChartCalcWorker(QThread):
    calc_finished = pyqtSignal(dict, dict, bool, str, str)
    
    def __init__(self, ephemeris):
        super().__init__()
        self.ephemeris = ephemeris
        self.req_queue = queue.Queue()
        self.is_running = True

    def request_calc(self, time_dict, lat, lon, tz, real_now_jd, selected_div, selected_planet, active_divs, frozen_planets):
        # Empty queue heavily to jump right to the latest animation frame and not freeze UI
        while not self.req_queue.empty():
            try: self.req_queue.get_nowait()
            except queue.Empty: break
        self.req_queue.put((time_dict, lat, lon, tz, real_now_jd, selected_div, selected_planet, active_divs, frozen_planets))

    def run(self):
        while self.is_running:
            try:
                req = self.req_queue.get(timeout=0.1)
                time_dict, lat, lon, tz, real_now_jd, selected_div, selected_planet, active_divs, frozen_planets = req
                
                chart_data = self.ephemeris.calculate_chart(time_dict, lat, lon, tz, real_now_jd, selected_div, selected_planet)
                div_charts = {}
                for div in active_divs:
                    div_charts[div] = self.ephemeris.compute_divisional_chart(chart_data, div) if div != "D1" else chart_data
                    
                violation, violating_planet, violating_div = False, None, None
                if "Ascendant" in frozen_planets:
                    asc_f_info = frozen_planets["Ascendant"]
                    asc_f_div_chart = div_charts.get(asc_f_info["div"]) or (self.ephemeris.compute_divisional_chart(chart_data, asc_f_info["div"]) if asc_f_info["div"] != "D1" else chart_data)
                    if asc_f_div_chart["ascendant"]["sign_index"] != asc_f_info["sign_idx"]:
                        violation, violating_planet, violating_div = True, "Ascendant", asc_f_info["div"]

                if not violation:
                    for p in chart_data["planets"]:
                        if p["name"] in frozen_planets:
                            p_f_info = frozen_planets[p["name"]]
                            p_f_div_chart = div_charts.get(p_f_info["div"]) or (self.ephemeris.compute_divisional_chart(chart_data, p_f_info["div"]) if p_f_info["div"] != "D1" else chart_data)
                            p_in_div = next((x for x in p_f_div_chart["planets"] if x["name"] == p["name"]), None)
                            if p_in_div and p_in_div["sign_index"] != p_f_info["sign_idx"]:
                                violation, violating_planet, violating_div = True, p["name"], p_f_info["div"]
                                break
                                
                self.calc_finished.emit(chart_data, div_charts, violation, str(violating_planet), str(violating_div))
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Background calculation error: {e}")

    def stop(self):
        self.is_running = False
        self.wait()

class ChartRenderer(QWidget):
    def __init__(self):
        super().__init__()
        
        # --- Widget Configuration ---
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        
        # --- State Initialization ---
        self.title = ""
        self.d1_data = None
        self.outline_mode = "Vitality (Lords)"
        self.rotated_asc_sign_idx = None
        self.hitboxes = []
        self.house_polys = {}
        self.chart_data = None
        
        # --- Display Flags ---
        self.use_symbols = False
        self.show_rahu_ketu = True
        self.highlight_asc_moon = True
        self.show_aspects = False
        self.show_arrows = True
        self.use_tint = True
        self.use_circular = False
        self.visible_aspect_planets = set()
        
        # --- Tooltip Configuration ---
        self.tooltip_label = QLabel(self)
        self.tooltip_label.setWindowFlags(
            Qt.WindowType.ToolTip | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Assuming GLOBAL_FONT_SCALE_MULTIPLIER exists in the environment
        font_size = int(13 * GLOBAL_FONT_SCALE_MULTIPLIER) if 'GLOBAL_FONT_SCALE_MULTIPLIER' in globals() else 13
        self.tooltip_label.setStyleSheet(
            f"QLabel {{ background-color: #FDFDFD; color: #222222; border: 1px solid #BBBBBB; padding: 6px; font-size: {font_size}px; }}"
        )
        self.tooltip_label.hide()
        
        # --- Visual Dictionaries ---
        self.unicode_syms = {
            "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿", 
            "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", 
            "Rahu": "☊", "Ketu": "☋"
        }
        
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
        
        # --- Animation State ---
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_duration = 300.0
        self.anim_start_time = 0
        self.source_layout = None
        self.target_layout = None
        self.current_layout = None
        self.data_changed_flag = False

    def _get_dynamic_functional_nature(self, p_name, base_lords, base_asc_idx, current_asc_idx):
        """Calculates the functional benefic/malefic nature of a planet."""
        # Nodes are always treated as neutral for this logic
        if p_name in ["Rahu", "Ketu"]: 
            return "#7f8c8d", "Neutral (Node)"
            
        if not base_lords: 
            return "#7f8c8d", "Neutral"
            
        # Calculate visual houses relative to current ascendant
        visual_lords = [((base_asc_idx + l - 1 - current_asc_idx) % 12) + 1 for l in base_lords]
        
        # --- Determine Astrological Functional Nature ---
        # In Vedic astrology, a planet's functional nature (benefic/malefic) depends on the houses it rules.
        
        # Kendra (Angular) houses represent foundational pillars and situational neutrality (4, 7, 10). 
        # Note: House 1 is both Kendra and Trine, but grouped with Trines for benefic calculations.
        has_kendra = any(h in [4, 7, 10] for h in visual_lords)
        
        # Trikona (Trine) houses represent dharma, luck, and are always auspicious (1, 5, 9).
        has_trine = any(h in [1, 5, 9] for h in visual_lords)
        
        # Dusthana houses represent obstacles, delays, and losses (6, 8, 12).
        has_malefic = any(h in [6, 8, 12] for h in visual_lords)
        
        # Trishadaya houses represent desires and gains but create functionally malefic lords (3, 11).
        has_upachaya_malefic = any(h in [3, 11] for h in visual_lords)
        
        # --- Evaluate Rulership Combinations ---
        if has_kendra and has_trine:
            # Ruling both a Kendra and a Trine makes a planet a highly auspicious "Yoga Karaka"
            return "#FFD700", "Yoga Karaka (Gold)"
        elif has_trine:
            # Ruling a Trine makes the planet a Functional Benefic
            return "#27ae60", "Functional Benefic (Trine)"
        elif has_upachaya_malefic:
            # Ruling a 3rd or 11th house makes it malefic, or mixed if it also rules another neutral house
            if has_malefic:
                return "#c0392b", "Functional Malefic"
            else:
                return "#f1c40f", "Mixed/Opportunistic"
        elif has_malefic:
            # Strictly ruling a Dusthana house makes it a Functional Malefic
            return "#c0392b", "Functional Malefic"
        elif has_kendra:
            # Ruling only a Kendra house strips natural benefics of their goodness (Kendradhipati Dosha)
            # making them act as situational neutrals
            return "#000000", "Situational/Neutral (Kendra)"
            
        return "#7f8c8d", "Neutral"

    def _get_house_polygon(self, h_num, x, y, w, h):
        """Generates the QPolygonF for the Vedic Diamond Chart houses."""
        # Key reference points of the bounding square
        p_tl, p_tr = QPointF(x, y), QPointF(x + w, y)
        p_bl, p_br = QPointF(x, y + h), QPointF(x + w, y + h)
        p_tc, p_bc = QPointF(x + w / 2, y), QPointF(x + w / 2, y + h)
        p_lc, p_rc = QPointF(x, y + h / 2), QPointF(x + w, y + h / 2)
        p_cc = QPointF(x + w / 2, y + h / 2)
        
        # Inner diagonal midpoints
        p_i_tl = QPointF(x + w / 4, y + h / 4)
        p_i_tr = QPointF(x + 3 * w / 4, y + h / 4)
        p_i_bl = QPointF(x + w / 4, y + 3 * h / 4)
        p_i_br = QPointF(x + 3 * w / 4, y + 3 * h / 4)
        
        # Map visual house number (1-12) to its respective diamond shape
        polygons = {
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
        return QPolygonF(polygons[h_num])
    
    def update_chart(self, data, d1_data=None):
        """Triggered from outside to inject new chart data."""
        self.chart_data = data
        self.d1_data = d1_data
        self.rotated_asc_sign_idx = None
        self.data_changed_flag = True

        current_time = time.time() * 1000
        time_since_last = current_time - getattr(self, 'last_update_time', current_time)
        self.last_update_time = current_time
        
        # Decoupled Animation Logic:
        # If updates are coming in continuously (e.g., every 250ms),
        # dynamically stretch the 60fps UI tween to perfectly bridge the time gap.
        if 0 < time_since_last < 1000:
            self.instant_snap = False
            self.anim_duration = time_since_last
            self.use_linear_easing = True
        else:
            self.instant_snap = False
            self.anim_duration = 350.0
            self.use_linear_easing = False
            
        self.update()  
    
    def _on_anim_tick(self):
        """Handles the frame-by-frame interpolation during a chart update."""
        elapsed = (time.time() * 1000) - self.anim_start_time
        
        # Prevent division by zero just in case
        if self.anim_duration <= 0:
            self.anim_duration = 1.0 
            
        t = elapsed / self.anim_duration
        
        # --- THE HARD CLAMP FIX ---
        if t >= 1.0:
            t = 1.0 # Cap progress perfectly at 100%
            if self.anim_timer.isActive():
                self.anim_timer.stop() # Kill the timer
            # Discard the interpolation math and lock the coordinates exactly to the target
            self.current_layout = self.target_layout 
        else:
            # Only run the complex Ease-Out/Linear math if we are actively animating
            self.current_layout = self._lerp_layout(self.source_layout, self.target_layout, t)
            
        self.update()
    
    def _lerp_layout(self, src, tgt, t):
        """Interpolates between two layouts (coordinates, scales, alpha tints)."""
        if getattr(self, 'use_linear_easing', False):
            e = t  # Pure linear for perfectly smooth continuous playback bridging
        else:
            e = 1 - (1 - t)**1  # (linear -> change to 2 for quad and 3 for cubic)
            
        def lerp(a, b):
            return a + (b - a) * e
        
        cur = {"zodiacs": {}, "houses": {}, "planets": {}, "tints": []}

        # Interpolate spatial properties
        for cat in ["zodiacs", "houses", "planets"]:
            for k, t_v in tgt[cat].items():
                s_v = src[cat].get(k, t_v)
                cur[cat][k] = t_v.copy() 
                cur[cat][k]["x"] = lerp(s_v["x"], t_v["x"])
                cur[cat][k]["y"] = lerp(s_v["y"], t_v["y"])
                
                if cat == "planets":
                    cur[cat][k]["scale"] = lerp(s_v.get("scale", 1.0), t_v.get("scale", 1.0))

        # Interpolate tint alphas for cross-fading
        tgt_tints = list(tgt.get("tints", []))
        for s_tint in src.get("tints", []):
            c = QColor(s_tint["color"])
            
            # Find matching tint in target
            match = -1
            for i, t_t in enumerate(tgt_tints):
                if s_tint["h2"] == t_t["h2"] and c.rgb() == t_t["color"].rgb():
                    match = i
                    break
            
            if match != -1:
                # Fade towards target alpha
                c.setAlpha(int(lerp(c.alpha(), tgt_tints[match]["color"].alpha())))
                tgt_tints.pop(match)
            else:
                # Fade out entirely
                c.setAlpha(int(c.alpha() * (1.0 - e)))
            
            cur["tints"].append({"h2": s_tint["h2"], "color": c})
            
        # Fade in new target tints
        for t_tint in tgt_tints:
            c = QColor(t_tint["color"])
            c.setAlpha(int(c.alpha() * e))
            cur["tints"].append({"h2": t_tint["h2"], "color": c})
            
        return cur

    def _compute_layout(self, x, y, w, h):
        """Calculates the absolute target positions of all chart elements."""
        layout = {"zodiacs": {}, "planets": {}, "houses": {}, "tints": []}
        if not self.chart_data: return layout
        
        base_asc_sign_idx = self.chart_data["ascendant"]["sign_index"]
        
        # Support interactive chart rotation
        if getattr(self, 'rotated_asc_sign_idx', None) is not None:
            asc_sign_idx = self.rotated_asc_sign_idx
            asc_deg_effective = asc_sign_idx * 30.0 + 15.0
        else:
            asc_sign_idx = base_asc_sign_idx
            asc_deg_effective = self.chart_data["ascendant"].get("div_lon", self.chart_data["ascendant"]["degree"])
            
        all_bodies = []
        
        # 1. Add Ascendant (if highlighted)
        if self.highlight_asc_moon: 
            is_vargottama = self.chart_data["ascendant"].get("vargottama", False)
            asc_str = "Asc*" if is_vargottama and self.title and "D1" not in self.title else "Asc"
            all_bodies.append({
                "name": "Ascendant", 
                "str": asc_str, 
                "color_dark": self.dark_colors.get("Ascendant", QColor("#000000")), 
                "lon": asc_deg_effective, 
                "retro": False, "exalted": False, "debilitated": False, "combust": False, 
                "raw": {
                    "name": "Ascendant", 
                    "sign_index": base_asc_sign_idx, 
                    "deg_in_sign": self.chart_data["ascendant"]["degree"] % 30, 
                    "retro": False, "combust": False, "house": 1, 
                    "vargottama": is_vargottama
                }
            })
            
        # 2. Add Planets
        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"] and not self.show_rahu_ketu: 
                continue
                
            p_str = self.unicode_syms[p["name"]] if self.use_symbols else p["sym"]
            if p.get("vargottama", False) and self.title and "D1" not in self.title:
                p_str += "*"
                
            all_bodies.append({
                "name": p["name"], 
                "str": p_str, 
                "color_dark": self.dark_colors.get(p["name"], QColor("#000000")), 
                "lon": p.get("div_lon", p["lon"]), 
                "retro": p["retro"], 
                "exalted": p.get("exalted", False), 
                "debilitated": p.get("debilitated", False), 
                "combust": p.get("combust", False), 
                "raw": p
            })

        # Group bodies into houses visually
        bodies_by_house = {i: [] for i in range(1, 13)}
        for b in all_bodies: 
            visual_h_num = ((b["raw"]["sign_index"] - asc_sign_idx) % 12) + 1
            bodies_by_house[visual_h_num].append(b)

        # 3. Calculate Layout Coordinates
        for visual_h_num in range(1, 13):
            sign_idx = (asc_sign_idx + visual_h_num - 1) % 12
            sign_num = sign_idx + 1
            sign_lon = sign_idx * 30.0 + 15.0
            original_h_num = ((sign_idx - base_asc_sign_idx) % 12) + 1
            
            # Position calculations (Circular vs Diamond)
            if getattr(self, "use_circular", False): 
                zx, zy = animation.get_circular_coords(sign_lon, asc_deg_effective, -3, w, h)
                hx, hy = animation.get_circular_coords(sign_lon, asc_deg_effective, -4, w, h)
            else: 
                has_bodies = len(bodies_by_house[visual_h_num]) > 0
                zx, zy = animation.get_diamond_zodiac_coords(visual_h_num, w, h, has_bodies)
                hx, hy = animation.get_diamond_house_center(visual_h_num, w, h)
                
            # --- House Outline Display Logic ---
            # Depending on the selected 'outline_mode', we style the house borders to reflect different astrological data:
            # - Pressure (Aspects): Colors/widths indicate how heavily aspected the house is from other planets.
            # - Regime (Forces): Uses multiple colored borders (regime_colors) to show multiple simultaneous ruling influences.
            # - Vitality (Lords): Colors/widths indicate the inherent strength of the house based on its lord's condition.
            
            info = self.chart_data.get("houses_info", {}).get(original_h_num, {})
            
            if self.outline_mode == "Pressure (Aspects)":
                o_col = info.get("pressure_color", "#BDC3C7")
                o_wid = info.get("pressure_width", 1.0)
                r_cols = []
            elif self.outline_mode == "Regime (Forces)":
                o_col = "#BDC3C7"
                o_wid = 1.0
                r_cols = info.get("regime_colors", [])
            elif self.outline_mode == "Vitality (Lords)":
                o_col = info.get("vitality_color", "#BDC3C7")
                o_wid = info.get("vitality_width", 1.0)
                r_cols = []
            else:
                o_col = "#BDC3C7"
                o_wid = 1.0
                r_cols = []
                
            layout["houses"][visual_h_num] = {
                "x": hx + x, 
                "y": hy + y, 
                "outline_color": o_col, 
                "outline_width": o_wid, 
                "regime_colors": r_cols, 
                "original_h_num": original_h_num
            }
            
            # Zodiac string generation
            elem_emoji = {1: '🔥', 2: '🌍', 3: '💨', 4: '💧', 5: '🔥', 6: '🌍', 
                          7: '💨', 8: '💧', 9: '🔥', 10: '🌍', 11: '💨', 12: '💧'}[sign_num]
            layout["zodiacs"][sign_num] = {"x": zx + x, "y": zy + y, "val": f"{sign_num}{elem_emoji}"}

        # Lane Order for circular layouts to prevent planet overlap
        LANE_ORDER = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4, 
                      "Venus": 5, "Saturn": 6, "Rahu": 7, "Ketu": 8, "Ascendant": 9}
                      
        for visual_h_num, bodies in bodies_by_house.items():
            num_b = len(bodies)
            # Dynamic scaling to fit multiple planets in a single diamond/house
            if num_b <= 2:
                scale, spacing = 1.0, 0.08 * h
            elif num_b <= 4:
                scale, spacing = 0.85, 0.06 * h
            elif num_b <= 6:
                scale, spacing = 0.70, 0.045 * h
            else:
                scale, spacing = 0.55, 0.03 * h
                
            for idx, b in enumerate(bodies):
                if getattr(self, "use_circular", False): 
                    px, py = animation.get_circular_coords(b["lon"], asc_deg_effective, LANE_ORDER.get(b["name"], 4.5), w, h)
                else: 
                    px, _ = animation.get_diamond_planet_coords(visual_h_num, idx, num_b, w, h)
                    py = animation.get_diamond_house_center(visual_h_num, w, h)[1] - ((num_b - 1) * spacing) / 2.0 + (idx * spacing)
                    
                layout["planets"][b["name"]] = {
                    "x": px + x, "y": py + y, "str": b["str"], 
                    "color_dark": b["color_dark"], "retro": b["retro"], 
                    "exalted": b["exalted"], "debilitated": b["debilitated"], 
                    "combust": b["combust"], "raw": b["raw"], "scale": scale
                }

        # Calculate house tints for aspects
        if self.show_aspects and self.use_tint and self.chart_data and self.chart_data.get("aspects"):
            for aspect in self.chart_data["aspects"]:
                is_node = aspect["aspecting_planet"] in ["Rahu", "Ketu"]
                if aspect["aspecting_planet"] in self.visible_aspect_planets and (not is_node or self.show_rahu_ketu):
                    c = QColor(self.bright_colors.get(aspect["aspecting_planet"], QColor(200, 200, 200)))
                    c.setAlpha(25)
                    # Convert target aspect house to visual rendering house
                    target_visual_house = ((((base_asc_sign_idx + aspect["target_house"] - 1) % 12) - asc_sign_idx) % 12) + 1
                    layout["tints"].append({"h2": target_visual_house, "color": c})
                    
        return layout

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 1. Base Dimensions & Initialization
        size = min(self.width(), self.height()) - 50
        cx, cy = self.width() / 2, self.height() / 2
        x, y, w, h = cx - size / 2, cy - size / 2 + 10, size, size
        
        # 2. Animation & Layout State Setup
        new_target_layout = self._compute_layout(x, y, w, h)
        if self.data_changed_flag:
            self.data_changed_flag = False
            self.bg_cache = None  # Invalidate background cache to force redraw
            
            if getattr(self, 'instant_snap', False) or self.current_layout is None:
                # Snap instantly for fast playback (flipbook style)
                self.source_layout = self.target_layout = self.current_layout = new_target_layout
                if self.anim_timer.isActive():
                    self.anim_timer.stop()
            else:
                # Smooth 350ms tween for manual steps or rotations
                self.source_layout, self.target_layout = self.current_layout, new_target_layout
                self.anim_start_time = time.time() * 1000
                self.anim_timer.start(16)
        else:
            self.target_layout = new_target_layout
            if not self.anim_timer.isActive():
                self.source_layout = self.current_layout = new_target_layout

        if not self.current_layout:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Chart Data")
            return

        # 3. STATIC CACHE LAYER: Only draw grid, houses, and titles when resizing or data changes
        if getattr(self, '_last_bg_size', None) != self.size() or not getattr(self, 'bg_cache', None):
            self._last_bg_size = self.size()
            self.bg_cache = QPixmap(self.size())
            self.bg_cache.fill(Qt.GlobalColor.white)
            
            bg_p = QPainter(self.bg_cache)
            bg_p.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw Title
            if self.title:
                bg_p.setPen(QColor("#BBBBBB"))
                font_fam = GLOBAL_UI_FONT_FAMILY if 'GLOBAL_UI_FONT_FAMILY' in globals() else "Arial"
                font_mult = GLOBAL_FONT_SCALE_MULTIPLIER if 'GLOBAL_FONT_SCALE_MULTIPLIER' in globals() else 1.0
                calc_size = int(min(15, max(10, int(size * 0.035))) * font_mult)
                bg_p.setFont(QFont(font_fam, calc_size, QFont.Weight.Bold))
                bg_p.drawText(QRectF(0, 0, self.width(), y - 10), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, self.title)

            # Pre-compute house polygons for hitboxes and tints
            self.house_polys.clear()
            for h_num in range(1, 13):
                self.house_polys[h_num] = self._get_house_polygon(h_num, x, y, w, h)

            # Draw the base chart skeleton (Circular vs Diamond)
            if getattr(self, "use_circular", False):
                outer_r, inner_r = (w - 40) / 2, w * 0.15
                bg_p.setPen(QPen(QColor("#DAA520"), 2))
                bg_p.drawEllipse(QPointF(cx, cy), outer_r + 4, outer_r + 4)
                
                bg_p.setPen(QPen(QColor("#8B4513"), 1.5))
                bg_p.drawEllipse(QPointF(cx, cy), outer_r + 8, outer_r + 8)
                
                bg_p.setPen(QPen(QColor("#222222"), max(1.0, w * 0.005)))
                bg_p.drawEllipse(QRectF(x + 20, y + 20, w - 40, h - 40))
                bg_p.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))
                
                for i in range(12):
                    angle = math.radians(i * 30 + 15)
                    bg_p.drawLine(
                        int(cx + inner_r * math.cos(angle)), int(cy - inner_r * math.sin(angle)), 
                        int(cx + outer_r * math.cos(angle)), int(cy - outer_r * math.sin(angle))
                    )
            else:
                bg_p.setPen(QPen(QColor("#DAA520"), 2))
                bg_p.drawRect(int(x - 4), int(y - 4), int(w + 8), int(h + 8))
                
                bg_p.setPen(QPen(QColor("#8B4513"), 1.5))
                bg_p.drawRect(int(x - 8), int(y - 8), int(w + 16), int(h + 16))
                
                bg_p.setPen(Qt.PenStyle.NoPen)
                bg_p.setBrush(QBrush(QColor("#8B4513")))
                for px in [x - 8, x + w + 8]:
                    for py in [y - 8, y + h + 8]: 
                        bg_p.drawRect(int(px - 2), int(py - 2), 4, 4)
                        
                bg_p.setBrush(Qt.BrushStyle.NoBrush)
                bg_p.setPen(QPen(QColor("#222222"), max(1.0, w * 0.005)))
                bg_p.drawRect(int(x), int(y), int(w), int(h))
                
                lines = [
                    (x, y, x + w, y + h), 
                    (x + w, y, x, y + h), 
                    (x + w/2, y, x + w, y + h/2), 
                    (x + w, y + h/2, x + w/2, y + h), 
                    (x + w/2, y + h, x, y + h/2), 
                    (x, y + h/2, x + w/2, y)
                ]
                for L in lines:
                    bg_p.drawLine(int(L[0]), int(L[1]), int(L[2]), int(L[3]))
                    
            bg_p.end()

        # Instantly slap the static background onto the canvas
        painter.drawPixmap(0, 0, self.bg_cache)

        # 4. Tints and Dynamic Outlines
        for tint in self.current_layout["tints"]:
            if not getattr(self, "use_circular", False) and tint["h2"] in self.house_polys:
                painter.setBrush(QBrush(tint["color"]))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(self.house_polys[tint["h2"]])
        
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if not getattr(self, "use_circular", False):
            for h_num in range(1, 13):
                h_data = self.current_layout["houses"].get(h_num)
                if not h_data: 
                    continue
                    
                if self.outline_mode == "Regime (Forces)" and h_data.get("regime_colors", []):
                    # Multi-color outlines for regime forces
                    for i, col_hex in enumerate(h_data["regime_colors"]):
                        c = QColor(col_hex)
                        c.setAlpha(230)
                        inset_dist = (max(1.0, w * 0.005) / 2.0) + 4.25 + (i * 4.5)
                        
                        # Calculate inset polygon points to prevent outline overlap
                        pts = []
                        for pt in self.house_polys[h_num]:
                            dx = h_data["x"] - pt.x()
                            dy = h_data["y"] - pt.y()
                            dist = max(1, math.hypot(dx, dy))
                            nx = pt.x() + (dx / dist) * inset_dist
                            ny = pt.y() + (dy / dist) * inset_dist
                            pts.append(QPointF(nx, ny))
                            
                        inset_poly = QPolygonF(pts)
                        painter.setPen(QPen(c, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                        painter.drawPolygon(inset_poly)
                        
                elif self.outline_mode != "Regime (Forces)" and h_data.get("outline_width", 1.0) > 1.05:
                    # Standard bold outlines
                    c = QColor(h_data["outline_color"])
                    c.setAlpha(220)
                    inset_dist = (max(1.0, w * 0.005) / 2.0) + 4.25
                    
                    pts = []
                    for pt in self.house_polys[h_num]:
                        dx = h_data["x"] - pt.x()
                        dy = h_data["y"] - pt.y()
                        dist = max(1, math.hypot(dx, dy))
                        nx = pt.x() + (dx / dist) * inset_dist
                        ny = pt.y() + (dy / dist) * inset_dist
                        pts.append(QPointF(nx, ny))
                        
                    inset_poly = QPolygonF(pts)
                    painter.setPen(QPen(c, 3.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                    painter.drawPolygon(inset_poly)

        # 5. Zodiacs
        font_mult = GLOBAL_FONT_SCALE_MULTIPLIER if 'GLOBAL_FONT_SCALE_MULTIPLIER' in globals() else 1.0
        z_font_fam = GLOBAL_RASHI_FONT_FAMILY if 'GLOBAL_RASHI_FONT_FAMILY' in globals() else "Arial"
        z_font = QFont(z_font_fam, int(max(7, min(14, max(9, w * 0.035)) * 0.5) * font_mult))
        painter.setFont(z_font)
        painter.setPen(QColor("#000000"))
        
        for z in self.current_layout["zodiacs"].values():
            painter.drawText(QRectF(z["x"] - 15, z["y"] - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, z["val"])

        # 6. Planets
        self.hitboxes.clear()
        is_animating = self.anim_timer.isActive()
        p_base_font_size = min(14, max(9, int(w * 0.035))) * font_mult * 1.15
        marker_base_fs = max(4, min(9, max(6, int(w * 0.022))))
        chart_font_fam = GLOBAL_CHART_FONT_FAMILY if 'GLOBAL_CHART_FONT_FAMILY' in globals() else "Arial"
        emoji_font_fam = GLOBAL_EMOJI_FONT_FAMILY if 'GLOBAL_EMOJI_FONT_FAMILY' in globals() else "Segoe UI Emoji"
        
        for b in self.current_layout["planets"].values():
            scale = b.get("scale", 1.0)
            
            # Atmakaraka Highlighting Background
            if b["raw"].get("is_ak"):
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor(255, 215, 0, 90))
                painter.drawEllipse(QPointF(b["x"], b["y"] - 4 * scale), 22 * scale, 22 * scale)
                
            # Planet Text
            painter.setPen(b["color_dark"])
            painter.setFont(QFont(chart_font_fam, int(p_base_font_size * scale), QFont.Weight.Bold))
            p_rect = QRectF(b["x"] - 40 * scale, b["y"] - 10 * scale, 80 * scale, 20 * scale)
            painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, b["str"])
            
            # Hitboxes are only built when the animation finishes to ensure precision clicking
            if not is_animating:
                self.hitboxes.append((p_rect, b["raw"]))
                
            # Render special status markers (R, ▲, ▼, 🔥)
            marker_x = b["x"] + painter.fontMetrics().horizontalAdvance(b["str"]) / 2.0 + 2 * scale
            marker_y, marker_h = b["y"] - 10 * scale, 20 * scale
            marker_fs = max(4, int(marker_base_fs * scale))
            
            if b["retro"]:
                painter.setFont(QFont(chart_font_fam, max(4, marker_fs - 1), QFont.Weight.Bold))
                painter.drawText(QRectF(marker_x, marker_y - 5 * scale, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "R")
                marker_x += painter.fontMetrics().horizontalAdvance("R") + 1
                
            if b.get("exalted"):
                painter.setPen(QColor("#27ae60"))
                painter.setFont(QFont(chart_font_fam, marker_fs, QFont.Weight.Bold))
                painter.drawText(QRectF(marker_x, marker_y, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "▲")
                marker_x += painter.fontMetrics().horizontalAdvance("▲") + 2
            elif b.get("debilitated"):
                painter.setPen(QColor("#c0392b"))
                painter.setFont(QFont(chart_font_fam, marker_fs, QFont.Weight.Bold))
                painter.drawText(QRectF(marker_x, marker_y, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "▼")
                marker_x += painter.fontMetrics().horizontalAdvance("▼") + 2
                
            if b.get("combust"):
                painter.setFont(QFont(emoji_font_fam, marker_fs))
                painter.drawText(QRectF(marker_x, marker_y, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "🔥")

        # 7. Aspect Lines
        if self.show_aspects and self.show_arrows and self.chart_data and self.chart_data.get("aspects"):
            asc_sign_idx = self.rotated_asc_sign_idx if getattr(self, 'rotated_asc_sign_idx', None) is not None else self.chart_data["ascendant"]["sign_index"]
            
            for i, aspect in enumerate(self.chart_data["aspects"]):
                is_node = aspect["aspecting_planet"] in ["Rahu", "Ketu"]
                if aspect["aspecting_planet"] in self.visible_aspect_planets and (not is_node or self.show_rahu_ketu):
                    
                    target_h_visual = ((((self.chart_data["ascendant"]["sign_index"] + aspect["target_house"] - 1) % 12) - asc_sign_idx) % 12) + 1
                    p_v = self.current_layout["planets"].get(aspect["aspecting_planet"])
                    h_v = self.current_layout["houses"].get(target_h_visual)
                    
                    if p_v and h_v:
                        c = QColor(self.bright_colors.get(aspect["aspecting_planet"], QColor(100, 100, 100)))
                        c.setAlpha(150)
                        
                        # Apply slight offsets based on index to separate multiple incoming arrows
                        offset_x = (i % 3 - 1) * 4
                        offset_y = ((i + 1) % 3 - 1) * 4
                        x1, y1 = p_v["x"] + offset_x, p_v["y"] + offset_y
                        x2, y2 = h_v["x"] + offset_x, h_v["y"] + offset_y
                        
                        dist = math.hypot(x2 - x1, y2 - y1)
                        if dist >= 70:
                            # Shorten line slightly to not completely cover endpoints
                            sx = x1 + ((x2 - x1) / dist) * 35
                            sy = y1 + ((y2 - y1) / dist) * 35
                            ex = x2 - ((x2 - x1) / dist) * 35
                            ey = y2 - ((y2 - y1) / dist) * 35
                            
                            painter.setPen(QPen(c, max(1.5, w * 0.005), Qt.PenStyle.SolidLine))
                            painter.drawLine(int(sx), int(sy), int(ex), int(ey))
                            
                            # Draw arrowhead
                            angle = math.atan2(ey - sy, ex - sx)
                            painter.setBrush(QBrush(c))
                            painter.setPen(Qt.PenStyle.NoPen)
                            
                            arrow_pts = [
                                QPointF(ex, ey), 
                                QPointF(ex - 9 * math.cos(angle - math.pi / 6), ey - 9 * math.sin(angle - math.pi / 6)), 
                                QPointF(ex - 9 * math.cos(angle + math.pi / 6), ey - 9 * math.sin(angle + math.pi / 6))
                            ]
                            painter.drawPolygon(QPolygonF(arrow_pts))

    def mouseDoubleClickEvent(self, event):
        """Allows users to rotate the chart context by double-clicking a house."""
        if not self.chart_data: return
        
        for h_num, poly in self.house_polys.items():
            if poly.containsPoint(event.position(), Qt.FillRule.OddEvenFill):
                curr_asc = self.rotated_asc_sign_idx if getattr(self, 'rotated_asc_sign_idx', None) is not None else self.chart_data["ascendant"]["sign_index"]
                target_asc = (curr_asc + h_num - 1) % 12
                
                # If clicking the house that is already the 1st, reset to actual ascendant
                if target_asc == curr_asc and curr_asc != self.chart_data["ascendant"]["sign_index"]:
                    self.rotated_asc_sign_idx = None
                else:
                    self.rotated_asc_sign_idx = target_asc
                
                # Force the smooth animation for double-click rotations
                self.instant_snap = False
                self.anim_duration = 350.0
                self.use_linear_easing = False
                self.data_changed_flag = True
                
                self.update()
                self.tooltip_label.hide()
                break
    
    def mouseMoveEvent(self, event): 
        self._update_tooltip(event.position())

    def _update_tooltip(self, pos):
        """Builds and displays contextual HTML information based on mouse position."""
        if not self.chart_data or not self.current_layout: 
            self.tooltip_label.hide()
            return
            
        tooltip_html = ""
        pos_point = QPointF(pos.x(), pos.y())
        
        # --- Helper Constants / Functions ---
        def ordinal(n):
            if 11 <= (n % 100) <= 13: return str(n) + 'th'
            return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        zodiac_elements = ["🔥 Fire", "🌍 Earth", "💨 Air", "💧 Water"] * 3
        zodiac_natures = ["Movable", "Fixed", "Dual"] * 4

        font_mult = GLOBAL_FONT_SCALE_MULTIPLIER if 'GLOBAL_FONT_SCALE_MULTIPLIER' in globals() else 1.0
        fs_11, fs_12, fs_14, fs_18 = int(11 * font_mult), int(12 * font_mult), int(14 * font_mult), int(18 * font_mult)
        
        base_asc_sign_idx = self.chart_data["ascendant"]["sign_index"]
        asc_sign_idx = getattr(self, 'rotated_asc_sign_idx', None) if getattr(self, 'rotated_asc_sign_idx', None) is not None else base_asc_sign_idx

        # --- Context Header Formatting ---
        context_prefix = ""
        if self.title and "D1" not in self.title:
            context_prefix += f"<div style='color:#888; font-size:{fs_11}px; margin-bottom:4px;'><b>[{self.title}]</b></div>"
            
            # Map D1 lords for Varga charts
            d1_house_map = {"D9": 7, "D10": 10, "D20": 9, "D30": 6, "D60": 1}
            chart_prefix = self.title.split()[0]
            
            if getattr(self, 'd1_data', None) and chart_prefix in d1_house_map:
                d1_h = d1_house_map[chart_prefix]
                
                if 'astro_engine' in globals():
                    d1_lord_name = astro_engine.SIGN_RULERS.get((self.d1_data["ascendant"]["sign_index"] + d1_h - 1) % 12 + 1)
                    div_lord_p = next((p for p in self.chart_data["planets"] if p["name"] == d1_lord_name), None)
                    
                    if div_lord_p:
                        dig_flags = []
                        if div_lord_p.get("exalted"): dig_flags.append("Exalted")
                        if div_lord_p.get("debilitated"): dig_flags.append("Debilitated")
                        if div_lord_p.get("own_sign"): dig_flags.append("Own Sign")
                        
                        dig_str = f" ({', '.join(dig_flags)})" if dig_flags else ""
                        context_prefix += (
                            f"<div style='background-color:#FFF8DC; padding:5px; border:1px solid #EEDD82; "
                            f"border-radius:3px; margin-bottom:8px; font-size:{fs_12}px; color:#555;'>"
                            f"<b>D1 {ordinal(d1_h)} lord ({d1_lord_name}) in {chart_prefix} {ordinal(div_lord_p['house'])} house{dig_str}</b>"
                            f"</div>"
                        )

        # --- Check Hitboxes for Planet Intersect ---
        for rect, p_raw in self.hitboxes:
            if rect.contains(pos_point):
                name = p_raw["name"]
                house = ((p_raw["sign_index"] - asc_sign_idx) % 12) + 1 if "house" in p_raw else "-"
                
                # Extract Statuses
                status_items = []
                if name in ["Rahu", "Ketu"] or (p_raw.get("retro") and name != "Ascendant"):
                    status_items.append("<span style='color:#d35400;'><b>Retrograde</b></span>")
                if p_raw.get("combust"):
                    status_items.append("<span style='color:#c0392b;'><b>Combust</b></span>")
                    
                # Extract Dignities
                dignity_list = []
                if p_raw.get("exalted"): dignity_list.append("<span style='color:#27ae60;'><b>Exalted</b></span>")
                if p_raw.get("debilitated"): dignity_list.append("<span style='color:#c0392b;'><b>Debilitated</b></span>")
                if p_raw.get("own_sign"): dignity_list.append("<span style='color:#27ae60;'><b>Own Sign</b></span>")
                if p_raw.get("vargottama") and self.title and "D1" not in self.title:
                    dignity_list.append("<span style='color:#27ae60;'><b>Vargottama</b></span>")
                
                html = context_prefix
                if p_raw.get("is_ak"):
                    html += f"<span style='color: #B8860B;'><b>* Brightest Star / Atmakaraka</b></span><br>"
                    
                # Format Lord indicators
                visual_lords = sorted([((base_asc_sign_idx + l - 1 - asc_sign_idx) % 12) + 1 for l in p_raw.get("lord_of", [])])
                lord_texts = []
                for l in visual_lords:
                    if l in {1, 2, 4, 5, 7, 9, 10, 11}:
                        lord_texts.append(f"<span style='color: #27ae60;'><b>{ordinal(l)}</b></span>")
                    else:
                        lord_texts.append(f"<span style='color: #c0392b;'><b>{ordinal(l)}</b></span>")
                
                # Planet specific colors
                if name in {"Moon", "Mercury", "Jupiter", "Venus"}: p_color = "#27ae60"
                elif name in {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}: p_color = "#c0392b"
                else: p_color = "#000000"
                
                func_color, func_label = self._get_dynamic_functional_nature(name, p_raw.get("lord_of", []), base_asc_sign_idx, asc_sign_idx)
                
                # Core identity string
                html += f"<b style='color: {p_color}; font-size: {fs_14}px;'>{name}</b>"
                if name != 'Ascendant':
                    html += f" <span style='color: {func_color}; font-size: {fs_18}px;'>*</span>"
                    html += f" <span style='font-size:{fs_11}px; color:#555;'>({func_label})</span>"
                html += "<hr style='margin: 4px 0;'/>"
                
                # Info Strings
                html += f"Sign: {zodiac_names[p_raw['sign_index']]} ({zodiac_elements[p_raw['sign_index']]})<br>"
                if house != "-": 
                    html += f"House: {house}<br>"
                if visual_lords: 
                    html += f"Lord of: <b>{' & '.join(lord_texts)} House</b><br>"
                if status_items: 
                    html += f"Status: {', '.join(status_items)}<br>"
                if dignity_list: 
                    html += f"Dignity: {', '.join(dignity_list)}<br>"
                if p_raw.get("nakshatra"): 
                    html += f"Nakshatra: <b>{p_raw['nakshatra']}</b> (Lord: <b style='color: #8e44ad;'>{p_raw['nakshatra_lord']}</b>)<br>"
                    
                deg, minute = int(p_raw['deg_in_sign']), int((p_raw['deg_in_sign'] - int(p_raw['deg_in_sign'])) * 60)
                tooltip_html = html + f"Base Longitude: {deg}°{minute:02d}'"
                break
                
        # --- Check Background House Intersect if No Planet Hit ---
        if not tooltip_html:
            hovered_visual_house = None
            for h, poly in self.house_polys.items():
                if poly.containsPoint(pos_point, Qt.FillRule.OddEvenFill):
                    hovered_visual_house = h
                    break
                    
            if hovered_visual_house and hovered_visual_house in self.current_layout.get("houses", {}):
                sign_idx = (asc_sign_idx + hovered_visual_house - 1) % 12
                original_h_num = self.current_layout["houses"][hovered_visual_house]["original_h_num"]
                s_name, s_elem, s_nat = zodiac_names[sign_idx], zodiac_elements[sign_idx], zodiac_natures[sign_idx]
                
                # Format occupants
                occ_colored = []
                for p in self.chart_data["planets"]:
                    if p["sign_index"] == sign_idx:
                        pn = p["name"]
                        if pn in {'Moon', 'Mercury', 'Jupiter', 'Venus'}: c_col = '#27ae60'
                        elif pn in {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}: c_col = '#c0392b'
                        else: c_col = '#000000'
                        occ_colored.append(f"<b style='color: {c_col};'>{pn}</b>")
                
                # House base info string
                base_str = f" | Base: {ordinal(original_h_num)}" if hovered_visual_house != original_h_num else ""
                tooltip_html = context_prefix + f"<b style='color: #2980b9; font-size: {fs_14}px;'>{ordinal(hovered_visual_house)} House (from {zodiac_names[asc_sign_idx][:3]}){base_str}</b><hr style='margin: 4px 0;'/>"
                
                nat_color = {'Movable': '#e67e22', 'Fixed': '#2980b9', 'Dual': '#8e44ad'}.get(s_nat, '#000000')
                tooltip_html += f"Sign: <b>{sign_idx + 1} - {s_name}</b><br>"
                tooltip_html += f"Nature: <b style='color: {nat_color};'>{s_nat}</b><br>"
                tooltip_html += f"Element: <b>{s_elem}</b><br>"
                
                # --- House Metadata (Vitality, Pressure, Regime) ---
                # Retrieve the pre-computed metrics for the original (base) house to display in the tooltip.
                h_info = self.chart_data.get("houses_info", {}).get(original_h_num, {})
                
                # 1. Vitality: Indicates the core strength of the house (e.g., is the lord exalted or debilitated?)
                v_lbl = h_info.get("vitality_label", "Background Scenery (Neutral)")
                if v_lbl != "Background Scenery (Neutral)": 
                    tooltip_html += f"Vitality (Lords): <b style='color: {h_info.get('vitality_color', '#555')};'>{v_lbl}</b><br>"
                    
                # 2. Pressure: Indicates external stress or focus on the house from incoming planetary aspects.
                p_lbl = h_info.get("pressure_label", "Quiet (0 influences)")
                if p_lbl != "Quiet (0 influences)": 
                    tooltip_html += f"Pressure (Aspects): <b style='color: {h_info.get('pressure_color', '#555')};'>{p_lbl}</b><br>"
                    
                # 3. Regime: Indicates the active ruling forces occupying or dominating the house.
                r_lbls = h_info.get("regime_labels", [])
                if r_lbls: 
                    tooltip_html += f"Regime Forces: {'<br>&nbsp;&nbsp;&nbsp;&bull; '.join([''] + r_lbls)}<br>"
                
                # House Lord logic
                if 'astro_engine' in globals():
                    lord_name = astro_engine.SIGN_RULERS.get(sign_idx + 1)
                    if lord_name:
                        lord_p = next((p for p in self.chart_data["planets"] if p["name"] == lord_name), None)
                        if lord_p:
                            l_status = []
                            if lord_p.get("retro"): l_status.append("Retrograde")
                            if lord_p.get("combust"): l_status.append("Combust")
                            if lord_p.get("exalted"): l_status.append("Exalted")
                            if lord_p.get("debilitated"): l_status.append("Own Sign") # Note: original code explicitly put 'Own Sign' for debilitated here
                            
                            if lord_name in {'Moon', 'Mercury', 'Jupiter', 'Venus'}: l_col = '#27ae60'
                            elif lord_name in {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}: l_col = '#c0392b'
                            else: l_col = '#000000'
                            
                            house_idx = ordinal(((lord_p['sign_index'] - asc_sign_idx) % 12) + 1)
                            stat_str = f" <span style='font-size:{fs_12}px; color:#555;'>({', '.join(l_status)})</span>" if l_status else ""
                            tooltip_html += f"House Lord: <b style='color: {l_col};'>{lord_name}</b> went to <b>{house_idx} House</b>{stat_str}<br>"

                if occ_colored: 
                    tooltip_html += f"Occupants: {', '.join(occ_colored)}<br>"

                # Aspects logic formatting
                aspecting_strs = []
                for asp in self.chart_data.get("aspects", []):
                    if asp["target_house"] == original_h_num:
                        asp_p = next((p for p in self.chart_data["planets"] if p["name"] == asp["aspecting_planet"]), None)
                        if asp_p:
                            asp_name = asp["aspecting_planet"]
                            if asp_name in {'Moon', 'Mercury', 'Jupiter', 'Venus'}: a_col = '#27ae60'
                            elif asp_name in {'Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu'}: a_col = '#c0392b'
                            else: a_col = '#000000'
                            
                            elem_str = zodiac_elements[asp_p['sign_index']].split()[1] + ' sign'
                            
                            lord_nums = [ordinal(l) for l in sorted([((base_asc_sign_idx + l - 1 - asc_sign_idx) % 12) + 1 for l in asp_p.get('lord_of', [])])]
                            lord_str = [f"{' & '.join(lord_nums)} lord"] if lord_nums else []
                            
                            stat_flags = []
                            if asp_p.get('retro'): stat_flags.append('Retro')
                            if asp_p.get('exalted'): stat_flags.append('Exalted')
                            if asp_p.get('debilitated'): stat_flags.append('Debilitated')
                            
                            meta_parts = [elem_str] + lord_str + stat_flags
                            meta_str = f" <span style='font-size:{fs_11}px; color:#555;'>({', '.join(meta_parts)})</span>"
                            aspecting_strs.append(f"<b style='color: {a_col};'>{asp_name}</b>{meta_str}")
                
                if aspecting_strs:
                    tooltip_html += f"Aspected by: {'<br>&nbsp;&nbsp;&nbsp;&bull; '.join([''] + aspecting_strs)}"

        # --- Position and Show Tooltip ---
        if tooltip_html:
            self.tooltip_label.setText(tooltip_html)
            self.tooltip_label.adjustSize()
            
            global_pos = self.mapToGlobal(pos_point.toPoint())
            new_x, new_y = global_pos.x() + 15, global_pos.y() + 15
            
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): 
                    new_x = global_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): 
                    new_y = global_pos.y() - self.tooltip_label.height() - 5
                    
            self.tooltip_label.move(new_x, new_y)
            self.tooltip_label.show()
            self.tooltip_label.raise_()
        else: 
            self.tooltip_label.hide()

    def leaveEvent(self, event):
        if hasattr(self, 'tooltip_label') and self.tooltip_label.isVisible(): 
            self.tooltip_label.hide()
        super().leaveEvent(event)
        
    def hideEvent(self, event):
        if hasattr(self, 'tooltip_label') and self.tooltip_label.isVisible(): 
            self.tooltip_label.hide()
        super().hideEvent(event)

# ==========================================
# MAIN APPLICATION LOGIC
# ==========================================

class DraggableSidebarWidget(QWidget):
    """
    A helper container widget that allows vertical drag-and-drop reordering 
    of its registered child groups (like QGroupBox).
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(4, 4, 4, 4)
        self.main_layout.setSpacing(6)
        
        self.drag_item = None
        self.drag_start_pos = None
        self.draggable_widgets = []
        
        self.placeholder = None
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.do_autoscroll)
        self.scroll_direction = 0
        self.scroll_speed = 15

    def add_group(self, widget):
        self.main_layout.addWidget(widget)
        widget.installEventFilter(self)
        self.draggable_widgets.append(widget)

    def add_layout(self, layout):
        self.main_layout.addLayout(layout)
        
    def add_stretch(self):
        self.main_layout.addStretch()

    def eventFilter(self, obj, event):
        # Only intercept mouse events if the object is one of our draggable groups
        if obj in self.draggable_widgets:
            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self.drag_start_pos = event.pos()
                self.drag_item = obj
                
            elif event.type() == QEvent.Type.MouseMove and self.drag_start_pos is not None:
                # Initiate drag if moved beyond threshold
                if (event.pos() - self.drag_start_pos).manhattanLength() > QApplication.startDragDistance():
                    self.start_drag(obj)
                    self.drag_start_pos = None
                    
            elif event.type() == QEvent.Type.MouseButtonRelease:
                self.drag_start_pos = None
                
        return super().eventFilter(obj, event)

    def start_drag(self, widget):
        self.drag_item = widget
        
        # Create a visual placeholder to indicate where it will drop
        self.placeholder = QWidget()
        self.placeholder.setFixedHeight(widget.height())
        self.placeholder.setStyleSheet("background-color: #E5E7EB; border: 2px dashed #9CA3AF; border-radius: 6px;")
        
        # Crucial for preventing flicker: the placeholder shouldn't intercept the drag event raycasts
        self.placeholder.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # Swap the widget with the placeholder initially
        idx = self.main_layout.indexOf(widget)
        self.main_layout.insertWidget(idx, self.placeholder)
        widget.hide()
        
        drag = QDrag(self)
        mime_data = QMimeData()
        drag.setMimeData(mime_data)
        
        # Create visual representation of dragged widget
        pixmap = widget.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, 10))
        
        # Execute drag (blocking call)
        action = drag.exec(Qt.DropAction.MoveAction)
        
        # Clean up after the drop finishes
        self.scroll_timer.stop()
        if self.placeholder:
            # Safely remove drag_item first so placeholder's index accurately reflects the gap
            self.main_layout.removeWidget(self.drag_item)
            final_idx = self.main_layout.indexOf(self.placeholder)
            
            self.main_layout.removeWidget(self.placeholder)
            self.placeholder.deleteLater()
            self.placeholder = None
            
            # Apply the final position
            if final_idx >= 0:
                self.main_layout.insertWidget(final_idx, self.drag_item)
                
        self.drag_item.show()
        self.drag_item = None

    def get_scroll_area(self):
        parent = self.parentWidget()
        while parent:
            if hasattr(parent, 'verticalScrollBar') and hasattr(parent, 'viewport'):
                return parent
            parent = parent.parentWidget()
        return None

    def dragEnterEvent(self, event):
        if event.source() == self:
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.scroll_timer.stop()
        super().dragLeaveEvent(event)

    def dragMoveEvent(self, event):
        if event.source() == self and self.drag_item and self.placeholder:
            pos = event.position().toPoint() if hasattr(event, 'position') else event.pos()
            drop_y = pos.y()
            
            # 1. Determine relative visual order based on the CURRENT layout order
            visible_widgets = []
            for i in range(self.main_layout.count()):
                item = self.main_layout.itemAt(i)
                w = item.widget()
                # Only look at registered draggable groups that are visible and aren't the one we are dragging
                if w and w in self.draggable_widgets and w != self.drag_item and w.isVisible():
                    visible_widgets.append(w)
            
            target_idx = len(visible_widgets)
            for i, w in enumerate(visible_widgets):
                center_y = w.y() + (w.height() / 2)
                if drop_y < center_y:
                    target_idx = i
                    break
                    
            target_widget = visible_widgets[target_idx] if target_idx < len(visible_widgets) else None
            
            # 2. Check current physical layout position
            current_placeholder_idx = self.main_layout.indexOf(self.placeholder)
            next_visible = None
            for i in range(current_placeholder_idx + 1, self.main_layout.count()):
                item = self.main_layout.itemAt(i)
                w = item.widget()
                if w and w in visible_widgets:
                    next_visible = w
                    break

            # 3. Only update layout if the placeholder needs to cross a visible widget
            if next_visible != target_widget:
                self.main_layout.removeWidget(self.placeholder)
                if target_widget:
                    insert_idx = self.main_layout.indexOf(target_widget)
                else:
                    # Insert at the end, but safely BEFORE the bottom stretch spacer
                    if visible_widgets:
                        insert_idx = self.main_layout.indexOf(visible_widgets[-1]) + 1
                    else:
                        insert_idx = 0
                self.main_layout.insertWidget(insert_idx, self.placeholder)

            event.acceptProposedAction()

            # Autoscrolling logic
            scroll_area = self.get_scroll_area()
            if scroll_area:
                global_pos = self.mapToGlobal(pos)
                viewport_pos = scroll_area.viewport().mapFromGlobal(global_pos)
                
                margin = 80 # Increased threshold so it triggers earlier
                viewport_height = scroll_area.viewport().height()
                
                if viewport_pos.y() < margin:
                    self.scroll_direction = -1
                    speed_factor = max(1, int((margin - max(0, viewport_pos.y())) / 10))
                    self.scroll_speed = speed_factor * 2
                    if not self.scroll_timer.isActive():
                        self.scroll_timer.start(16) # ~60 FPS
                elif viewport_pos.y() > viewport_height - margin:
                    self.scroll_direction = 1
                    speed_factor = max(1, int((viewport_pos.y() - (viewport_height - margin)) / 10))
                    self.scroll_speed = speed_factor * 2
                    if not self.scroll_timer.isActive():
                        self.scroll_timer.start(16)
                else:
                    self.scroll_timer.stop()

    def do_autoscroll(self):
        scroll_area = self.get_scroll_area()
        if scroll_area:
            bar = scroll_area.verticalScrollBar()
            bar.setValue(bar.value() + self.scroll_direction * self.scroll_speed)

    def dropEvent(self, event):
        if event.source() == self:
            event.acceptProposedAction()
            # The actual widget placement occurs in `start_drag` cleanup after execution.

class AstroApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AstroBasics Diamond Chart Pro")
        self.resize(1300, 800)
        
        if os.path.exists(resource_path("icon.ico")): 
            self.setWindowIcon(QIcon(resource_path("icon.ico")))

        self.current_file_path = None
        self.last_load_dir = os.path.join(os.getcwd(), "saves")
        
        self.ephemeris = astro_engine.EphemerisEngine()
        self.time_ctrl = animation.TimeController()
        
        self.current_lat = 28.6139
        self.current_lon = 77.2090
        self.current_tz = "Asia/Kolkata"
        
        self.is_updating_ui = False
        self.is_loading_settings = True
        self.is_chart_saved = True
        
        self.frozen_planets = {}
        self.active_charts_order = []
        self.renderers = {}
        self.current_base_chart = None

        self.div_titles = {
            "D1": "D1 (Rashi)", "D2": "D2 (Hora)", "D3": "D3 (Drekkana)", 
            "D4": "D4 (Chaturthamsha)", "D5": "D5 (Panchamsha)", "D6": "D6 (Shashthamsha)", 
            "D7": "D7 (Saptamsha)", "D8": "D8 (Ashtamsha)", "D9": "D9 (Navamsha)", 
            "D10": "D10 (Dashamsha)", "D11": "D11 (Rudramsha)", "D12": "D12 (Dwadashamsha)", 
            "D16": "D16 (Shodashamsha)", "D20": "D20 (Vimshamsha)", "D24": "D24 (Chaturvimshamsha)", 
            "D27": "D27 (Bhamsha)", "D30": "D30 (Trimshamsha)", "D40": "D40 (Khavedamsha)", 
            "D45": "D45 (Akshavedamsha)", "D60": "D60 (Shashtiamsha)"
        }
        
        if HAS_CUSTOM_VARGAS: 
            self.div_titles.update(custom_vargas.get_all_extra_vargas())

        try:
            if os.path.exists("custom_vargas.json"):
                with open("custom_vargas.json", "r") as f:
                    self.ephemeris.set_custom_vargas(json.load(f))
        except: 
            pass

        self.calc_worker = ChartCalcWorker(self.ephemeris)
        self.calc_worker.calc_finished.connect(self.on_calc_finished)
        self.calc_worker.start()

        self.jump_worker = None

        self._init_ui()
        self._connect_signals()
        self.load_settings()
        
        # --- DYNAMIC MODULES INIT ---
        self.module_reload_timer = QTimer(self)
        self.module_reload_timer.setSingleShot(True)
        self.module_reload_timer.setInterval(500) # 500ms debounce
        self.module_reload_timer.timeout.connect(self._load_dynamic_modules)
        
        self.module_watcher = QFileSystemWatcher(self)
        self._setup_module_watcher()
        self._load_dynamic_modules()
        # ----------------------------
        
        self.is_loading_settings = False
        
        now = datetime.datetime.now()
        self.time_ctrl.set_time({
            'year': now.year, 'month': now.month, 'day': now.day, 
            'hour': now.hour, 'minute': now.minute, 'second': now.second
        })

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(60000)
        self.autosave_timer.timeout.connect(self.do_autosave)
        self.autosave_timer.start()

    # --- DYNAMIC MODULE METHODS ---
    def _setup_module_watcher(self):
        modules_dir = resource_path("dynamic_settings_modules")
        os.makedirs(modules_dir, exist_ok=True)
        if modules_dir not in self.module_watcher.directories():
            self.module_watcher.addPath(modules_dir)
        self.module_watcher.directoryChanged.connect(self._trigger_module_reload)
        self.module_watcher.fileChanged.connect(self._trigger_module_reload)

    def _trigger_module_reload(self, path=None):
        self.module_reload_timer.start()

    def _load_dynamic_modules(self):
        # 1. Clear out the old UI elements generated by plugins
        while self.dynamic_modules_layout.count():
            item = self.dynamic_modules_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget(): 
                        sub.widget().deleteLater()
                item.layout().deleteLater()
        
        modules_dir = resource_path("dynamic_settings_modules")
        os.makedirs(modules_dir, exist_ok=True)
        
        # Unwatch old specific files (we'll re-watch what exists now)
        if self.module_watcher.files():
            self.module_watcher.removePaths(self.module_watcher.files())

        added_modules = 0
        for filename in os.listdir(modules_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                module_name = filename[:-3]
                file_path = os.path.join(modules_dir, filename)
                
                # Monitor specifically for content edits
                self.module_watcher.addPath(file_path) 
                try:
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    
                    # Contract: Target module MUST have `setup_ui(app, layout)`
                    if hasattr(mod, "setup_ui"):
                        mod.setup_ui(self, self.dynamic_modules_layout)
                        added_modules += 1
                except Exception as e:
                    print(f"Failed to load dynamic module {filename}: {e}")

        # Hide the box entirely if no modules are valid
        self.dynamic_modules_group.setVisible(added_modules > 0)
    # ------------------------------

    def load_settings(self):
        settings_file = "astro_settings.json"
        if not os.path.exists(settings_file): 
            self.update_grid_layout()
            return
            
        try:
            with open(settings_file, "r") as f: 
                prefs = json.load(f)
                
            if "location" in prefs: self.loc_input.setText(prefs["location"])
            if "lat" in prefs: self.current_lat = prefs["lat"]
            if "lon" in prefs: self.current_lon = prefs["lon"]
            if "tz" in prefs: self.current_tz = prefs["tz"]
            
            self.loc_status.setText(f"Lat: {self.current_lat:.4f}, Lon: {self.current_lon:.4f} | {self.current_tz}")

            combos = [
                ("ayanamsa", self.cb_ayanamsa), 
                ("outline_mode", self.cb_outline_mode), 
                ("layout_mode", self.cb_layout_mode)
            ]
            for k, w in combos:
                if k in prefs: 
                    w.setCurrentText(prefs[k])
                    
            checkboxes = [
                ("use_symbols", self.chk_symbols), 
                ("show_rahu_ketu", self.chk_rahu), 
                ("show_arrows", self.chk_arrows), 
                ("use_tint", self.chk_tint), 
                ("show_aspects", self.chk_aspects), 
                ("show_details", self.chk_details), 
                ("use_circular", self.chk_circular)
            ]
            for k, w in checkboxes:
                if k in prefs: 
                    w.setChecked(prefs[k])
            
            if "aspect_planets" in prefs:
                for p, is_checked in prefs["aspect_planets"].items():
                    if p in self.aspect_cb: 
                        self.aspect_cb[p].setChecked(is_checked)
                        
            if "active_charts_order" in prefs: 
                self.active_charts_order = prefs["active_charts_order"]
                
            if "div_charts" in prefs:
                self.is_updating_ui = True
                for k, is_checked in prefs["div_charts"].items():
                    if k in self.div_cbs: 
                        self.div_cbs[k].setChecked(is_checked)
                        if is_checked and k not in self.active_charts_order: 
                            self.active_charts_order.append(k)
                        elif not is_checked and k in self.active_charts_order: 
                            self.active_charts_order.remove(k)
                self.is_updating_ui = False
                
            self.update_grid_layout()
            self.update_settings()
            self.toggle_details()
            
        except Exception as e: 
            print(f"Failed to load settings: {e}")

    def save_settings(self):
        if getattr(self, 'is_loading_settings', True): 
            return
            
        try:
            settings_dict = {
                "location": self.loc_input.text(),
                "lat": self.current_lat,
                "lon": self.current_lon,
                "tz": self.current_tz,
                "ayanamsa": self.cb_ayanamsa.currentText(),
                "outline_mode": self.cb_outline_mode.currentText(),
                "layout_mode": self.cb_layout_mode.currentText(),
                "use_symbols": self.chk_symbols.isChecked(),
                "show_rahu_ketu": self.chk_rahu.isChecked(),
                "show_arrows": self.chk_arrows.isChecked(),
                "use_tint": self.chk_tint.isChecked(),
                "show_aspects": self.chk_aspects.isChecked(),
                "show_details": self.chk_details.isChecked(),
                "use_circular": self.chk_circular.isChecked(),
                "aspect_planets": {p: cb.isChecked() for p, cb in self.aspect_cb.items()},
                "div_charts": {k: v.isChecked() for k, v in self.div_cbs.items()} if hasattr(self, 'div_cbs') else {},
                "active_charts_order": getattr(self, "active_charts_order", [])
            }
            with open("astro_settings.json", "w") as f:
                json.dump(settings_dict, f, indent=4)
        except Exception as e: 
            print(f"Failed to save settings: {e}")

    def do_autosave(self):
        if not getattr(self, "is_chart_saved", True):
            current_state = self.get_current_chart_info()
            if not hasattr(self, "last_autosaved_state") or self.last_autosaved_state != current_state:
                os.makedirs("autosave", exist_ok=True)
                
                existing_count = len(glob.glob(os.path.join('autosave', 'tmp_*_saveon_*.json')))
                timestamp = datetime.datetime.now().strftime('%d%m%Y_%H%M%S')
                filename = f"tmp_{existing_count + 1:03d}_saveon_{timestamp}.json"
                filepath = os.path.join("autosave", filename)
                
                save_prefs.save_chart_to_file(filepath, current_state)
                self.last_autosaved_state = current_state

    def update_window_title(self): 
        if self.current_file_path:
            base_name = os.path.basename(self.current_file_path)
            self.setWindowTitle(f"{base_name} - AstroBasics Diamond Chart Pro")
        else:
            self.setWindowTitle("AstroBasics Diamond Chart Pro")

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet(
            "QWidget { font-family: 'Segoe UI', sans-serif; font-size: 14px; color: #1A1A1A; } "
            "QGroupBox { background-color: #F3F4F6; border: 1px solid #D1D5DB; border-radius: 6px; margin-top: 12px; padding-top: 12px; padding-bottom: 4px; } "
            "QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 4px; left: 6px; color: #374151; font-weight: bold; } "
            "QLineEdit, QTableWidget { background-color: #FAFAFA; border: 1px solid #D1D5DB; border-radius: 4px; padding: 3px 5px; } "
            "QPushButton { background-color: #FFFFFF; border: 1px solid #D1D5DB; border-radius: 4px; padding: 4px 8px; } "
            "QPushButton:hover { background-color: #F3F4F6; border-color: #9CA3AF; } "
            "QPushButton:pressed { background-color: #E5E7EB; } "
            "QSpinBox, QTimeEdit { background-color: #FAFAFA; border: 1px solid #D1D5DB; border-radius: 4px; padding: 3px 5px; } "
            "QSpinBox:hover, QTimeEdit:hover { border-color: #9CA3AF; } "
            "QSpinBox::up-button, QTimeEdit::up-button, QSpinBox::down-button, QTimeEdit::down-button { background-color: #F3F4F6; border-left: 1px solid #D1D5DB; width: 16px; } "
            "QSpinBox::up-button:hover, QTimeEdit::up-button:hover, QSpinBox::down-button:hover, QTimeEdit::down-button:hover { background-color: #E5E7EB; } "
            "QSpinBox::up-button, QTimeEdit::up-button { border-top-right-radius: 3px; } "
            "QSpinBox::down-button, QTimeEdit::down-button { border-bottom-right-radius: 3px; border-top: 1px solid #D1D5DB; } "
            "QComboBox { background-color: #FAFAFA; border: 1px solid #D1D5DB; border-radius: 4px; padding: 3px 5px; } "
            "QComboBox:hover { border-color: #9CA3AF; } "
            "QComboBox::drop-down { border-left: 1px solid #D1D5DB; background-color: #F3F4F6; border-top-right-radius: 3px; border-bottom-right-radius: 3px; width: 18px; } "
            "QComboBox::drop-down:hover { background-color: #E5E7EB; } "
            "QComboBox QAbstractItemView { border: 1px solid #D1D5DB; background-color: #FAFAFA; selection-background-color: #0078D4; selection-color: white; } "
            "QSplitter::handle { background: #E5E7EB; } "
            "QScrollArea { border: none; background-color: transparent; }"
        )

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(300)
        self.left_smooth_scroller = SmoothScroller(left_scroll)
        
        # Replace normal QWidget with DraggableSidebarWidget for reorderable groups
        self.left_panel = DraggableSidebarWidget()

        # Location Group
        loc_group = QGroupBox("Location Settings")
        loc_layout = QVBoxLayout()
        loc_layout.setContentsMargins(4, 4, 4, 4)
        
        search_layout = QHBoxLayout()
        search_layout.setSpacing(4)
        self.loc_input = QLineEdit("New Delhi")
        self.loc_btn = QPushButton("Search")
        
        self.btn_custom_loc = QPushButton("...")
        self.btn_custom_loc.setFixedSize(30, 25)
        self.btn_custom_loc.setStyleSheet("border-radius: 4px; font-weight: bold; background-color: #DAA520; color: white; border: none;")
        self.btn_custom_loc.setToolTip("Enter Custom Coordinates")
        
        search_layout.addWidget(self.loc_input)
        search_layout.addWidget(self.loc_btn)
        search_layout.addWidget(self.btn_custom_loc)
        
        self.loc_status = QLabel("Lat: 28.61, Lon: 77.21 | TZ: Asia/Kolkata")
        loc_layout.addLayout(search_layout)
        loc_layout.addWidget(self.loc_status)
        loc_group.setLayout(loc_layout)

        # Date Time Group
        dt_group = QGroupBox("Date Time")
        dt_layout = QVBoxLayout()
        dt_layout.setContentsMargins(4, 4, 4, 4)
        dt_layout.setSpacing(6)
        
        date_layout = QHBoxLayout()
        date_layout.setSpacing(4)
        self.year_spin = QSpinBox()
        self.month_spin = QSpinBox()
        self.day_spin = QSpinBox()
        self.year_spin.setRange(-999999, 999999)
        self.month_spin.setRange(1, 12)
        self.day_spin.setRange(1, 31)
        
        date_layout.addWidget(QLabel("D:"))
        date_layout.addWidget(self.day_spin)
        date_layout.addWidget(QLabel("M:"))
        date_layout.addWidget(self.month_spin)
        date_layout.addWidget(QLabel("Y:"))
        date_layout.addWidget(self.year_spin)
        
        self.btn_panchang = QPushButton("...")
        self.btn_panchang.setFixedSize(30, 25)
        self.btn_panchang.setStyleSheet("border-radius: 4px; font-weight: bold; background-color: #DAA520; color: white; border: none;")
        self.btn_panchang.setToolTip("Show Panchang Info")
        date_layout.addWidget(self.btn_panchang)

        time_layout = QHBoxLayout()
        time_layout.setSpacing(4)
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        time_layout.addWidget(QLabel("T:"))
        time_layout.addWidget(self.time_edit)
        time_layout.setSpacing(20)
        
        self.dasha_label = QLabel("Now: -   ")
        self.dasha_label.setStyleSheet("color: #8B4513; font-weight: bold; font-size: 11px; margin-top: 4px;")
        
        dt_layout.addLayout(date_layout)
        dt_layout.addLayout(time_layout)
        dt_layout.addWidget(self.dasha_label)
        dt_group.setLayout(dt_layout)
        
        # Divisional Charts Group
        div_group = QGroupBox("Divisional Charts")
        div_layout = QGridLayout()
        div_layout.setContentsMargins(4, 4, 4, 4)
        div_layout.setSpacing(4)
        
        self.div_cbs = {}
        for i, (d_id, _) in enumerate(self.div_titles.items()):
            cb = QCheckBox(f"{d_id}")
            self.div_cbs[d_id] = cb
            if d_id == "D1": 
                cb.setChecked(True)
                if "D1" not in self.active_charts_order: 
                    self.active_charts_order.append("D1")
            
            # Using lambda carefully to bind values
            cb.toggled.connect(lambda checked, did=d_id: self.on_div_toggled(checked, did))
            div_layout.addWidget(cb, i // 4, i % 4)

        if HAS_CUSTOM_VARGAS:
            self.btn_add_custom_varga = QPushButton("Manage Custom Vargas")
            self.btn_add_custom_varga.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
            div_layout.addWidget(self.btn_add_custom_varga, len(self.div_titles) // 4 + 1, 0, 1, 4)
            
        div_group.setLayout(div_layout)

        # Animation Group
        nav_group = QGroupBox("Animation")
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(4, 4, 4, 4)
        nav_layout.setSpacing(4)
        
        step_layout = QHBoxLayout()
        step_layout.setSpacing(2)
        
        self.btn_sub_d = QPushButton("<<d")
        self.btn_sub_h = QPushButton("<h")
        self.btn_sub_m = QPushButton("<m")
        self.btn_add_m = QPushButton("m>")
        self.btn_add_h = QPushButton("h>")
        self.btn_add_d = QPushButton("d>>")
        
        for btn in [self.btn_sub_d, self.btn_sub_h, self.btn_sub_m, self.btn_add_m, self.btn_add_h, self.btn_add_d]: 
            step_layout.addWidget(btn)
            
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        self.btn_play = QPushButton("▶ Play")
        self.speed_combo = NoScrollComboBox()
        self.speed_combo.addItems(["1x", "10x", "60x", "120x", "300x", "600x", "1800x", "3600x", "14400x", "86400x", "604800x"])
        self.speed_combo.setMaxVisibleItems(20)
        
        btn_layout.addWidget(self.btn_play)
        btn_layout.addWidget(self.speed_combo)
        
        nav_layout.addLayout(step_layout)
        nav_layout.addLayout(btn_layout)
        nav_group.setLayout(nav_layout)
        
        # Transit Group
        transit_group = QGroupBox("Transit Constraints")
        transit_layout = QGridLayout()
        transit_layout.setContentsMargins(4, 4, 4, 4)
        transit_layout.setSpacing(4)
        
        transit_layout.addWidget(QLabel("Lagna (Asc.):"), 0, 0)
        self.btn_prev_lagna = QPushButton("<") 
        self.btn_next_lagna = QPushButton(">")
        transit_layout.addWidget(self.btn_prev_lagna, 0, 1)
        transit_layout.addWidget(self.btn_next_lagna, 0, 2)
        
        transit_layout.addWidget(QLabel("Plnt:"), 1, 0)
        self.cb_transit_planet = NoScrollComboBox()
        self.cb_transit_planet.addItems(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
        self.cb_transit_div = NoScrollComboBox()
        self.cb_transit_div.addItems(list(self.div_titles.keys()))
        self.cb_transit_planet.setMaxVisibleItems(20)
        self.cb_transit_div.setMaxVisibleItems(20)
        
        p_layout = QHBoxLayout()
        p_layout.setContentsMargins(0, 0, 0, 0)
        p_layout.setSpacing(4)
        p_layout.addWidget(self.cb_transit_planet)
        p_layout.addWidget(self.cb_transit_div)
        transit_layout.addLayout(p_layout, 1, 1, 1, 2)
        
        transit_layout.addWidget(QLabel("Jump:"), 2, 0)
        self.btn_prev_rashi = QPushButton("<")
        self.btn_next_rashi = QPushButton(">")
        transit_layout.addWidget(self.btn_prev_rashi, 2, 1)
        transit_layout.addWidget(self.btn_next_rashi, 2, 2)
        
        self.btn_stop_transit = QPushButton("⏹ Stop Search")
        self.btn_stop_transit.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
        self.btn_stop_transit.setVisible(False)
        transit_layout.addWidget(self.btn_stop_transit, 3, 0, 1, 3)
        
        transit_group.setLayout(transit_layout)

        # Settings Group
        set_group = QGroupBox("Settings")
        set_layout = QVBoxLayout()
        set_layout.setContentsMargins(4, 4, 4, 4)
        set_layout.setSpacing(4)
        
        self.cb_ayanamsa = NoScrollComboBox()
        self.cb_ayanamsa.addItems(["Lahiri", "Raman", "Fagan/Bradley"])
        
        self.cb_outline_mode = NoScrollComboBox()
        self.cb_outline_mode.addItems(["Vitality (Lords)", "Pressure (Aspects)", "Regime (Forces)", "None"])
        
        self.cb_layout_mode = NoScrollComboBox()
        self.cb_layout_mode.addItems(["3 Columns", "2 Columns", "1 Left, 2 Right (Stacked)"])
        self.cb_layout_mode.currentIndexChanged.connect(self.update_grid_layout)
        
        self.cb_ayanamsa.setMaxVisibleItems(20)
        self.cb_outline_mode.setMaxVisibleItems(20)
        self.cb_layout_mode.setMaxVisibleItems(20)
        
        self.chk_symbols = QCheckBox("Symb")
        self.chk_rahu = QCheckBox("Ra/Ke")
        self.chk_arrows = QCheckBox("Arrows")
        self.chk_tint = QCheckBox("Tints")
        self.chk_details = QCheckBox("Table")
        self.chk_circular = QCheckBox("Circ UI")
        
        self.chk_rahu.setChecked(True)
        self.chk_arrows.setChecked(True)
        self.chk_tint.setChecked(True)
        self.chk_details.setChecked(True)
        self.chk_circular.setChecked(False)
        
        self.chk_aspects = QCheckBox("Aspects")
        
        self.btn_save_chart = QPushButton("Save")
        self.btn_load_chart = QPushButton("Load")
        self.btn_export_png = QPushButton("PNG")
        self.btn_export_json = QPushButton("Export Detailed")

        chk_grid = QGridLayout()
        chk_grid.setSpacing(4)
        chk_grid.addWidget(QLabel("Ayanamsa:"), 0, 0)
        chk_grid.addWidget(self.cb_ayanamsa, 0, 1)
        chk_grid.addWidget(QLabel("Outlines:"), 1, 0)
        chk_grid.addWidget(self.cb_outline_mode, 1, 1)
        chk_grid.addWidget(QLabel("Layout:"), 2, 0)
        chk_grid.addWidget(self.cb_layout_mode, 2, 1)
        chk_grid.addWidget(self.chk_symbols, 3, 0)
        chk_grid.addWidget(self.chk_rahu, 3, 1)
        chk_grid.addWidget(self.chk_aspects, 4, 0)
        chk_grid.addWidget(self.chk_arrows, 4, 1)
        chk_grid.addWidget(self.chk_tint, 5, 0)
        chk_grid.addWidget(self.chk_circular, 5, 1)
        chk_grid.addWidget(self.chk_details, 6, 0, 1, 2)
        set_layout.addLayout(chk_grid)
        
        file_btns = QHBoxLayout()
        exp_btns = QHBoxLayout()
        file_btns.setSpacing(4)
        exp_btns.setSpacing(4)
        
        file_btns.addWidget(self.btn_save_chart)
        file_btns.addWidget(self.btn_load_chart)
        exp_btns.addWidget(self.btn_export_png)
        exp_btns.addWidget(self.btn_export_json)
        
        set_layout.addLayout(file_btns)
        set_layout.addLayout(exp_btns)
        set_group.setLayout(set_layout)

        # Aspects Group
        self.aspects_group = QGroupBox("Aspects From:")
        aspects_layout = QGridLayout()
        aspects_layout.setContentsMargins(4, 4, 4, 4)
        self.aspect_cb = {}
        
        aspect_planets = [
            ("Sun", "#FF8C00"), ("Moon", "#00BCD4"), ("Mars", "#FF0000"), 
            ("Mercury", "#00C853"), ("Jupiter", "#FFD700"), ("Venus", "#FF1493"), 
            ("Saturn", "#0000CD"), ("Rahu", "#708090"), ("Ketu", "#8B4513")
        ]
        
        for i, (p, color) in enumerate(aspect_planets):
            cb = QCheckBox(p[:3])
            cb.setStyleSheet(f"color: {color}; font-weight: bold;")
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_settings)
            self.aspect_cb[p] = cb
            aspects_layout.addWidget(cb, i // 3, i % 3)
            
        self.aspects_group.setLayout(aspects_layout)
        self.aspects_group.setVisible(False)

        # Extensions and Plugins Group
        self.dynamic_modules_group = QGroupBox("Extensions and Plugins")
        self.dynamic_modules_layout = QVBoxLayout()
        self.dynamic_modules_layout.setContentsMargins(4, 4, 4, 4)
        self.dynamic_modules_layout.setSpacing(4)
        self.dynamic_modules_group.setLayout(self.dynamic_modules_layout)
        self.dynamic_modules_group.setVisible(False)

        # Add all groups to the draggable panel
        draggable_groups = [
            loc_group, dt_group, div_group, nav_group, 
            transit_group, set_group, self.aspects_group, 
            self.dynamic_modules_group
        ]
        
        for g in draggable_groups: 
            self.left_panel.add_group(g)
            
        self.left_panel.add_stretch()

        # Visual Guide Button (Not draggable, added to layout bottom)
        self.btn_visual_guide = QPushButton("Guide, Legend, Credits and Privacy")
        self.btn_visual_guide.setStyleSheet("font-size: 11px; font-weight: bold; color: #1E8449; background-color: #E8F8F5; border: 1px solid #A2D9CE; border-radius: 4px;")
        self.btn_visual_guide.setFixedSize(260, 24)
        
        guide_lay = QHBoxLayout()
        guide_lay.addStretch()
        guide_lay.addWidget(self.btn_visual_guide)
        self.left_panel.add_layout(guide_lay)
        
        left_scroll.setWidget(self.left_panel)

        # Right Splitter setup
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.charts_scroll = QScrollArea()
        self.charts_scroll.setWidgetResizable(True)
        self.charts_container = QWidget()
        
        self.chart_layout = QGridLayout(self.charts_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_layout.setSpacing(10)
        self.charts_scroll.setWidget(self.charts_container)
        self.charts_smooth_scroller = SmoothScroller(self.charts_scroll)
        
        right_splitter.addWidget(self.charts_scroll)
        
        # Table container setup
        table_container = QWidget()
        tc_layout = QVBoxLayout(table_container)
        tc_layout.setContentsMargins(4, 4, 4, 4)
        
        tc_top = QHBoxLayout()
        tc_top.addWidget(QLabel("Explore Details For:"))
        
        self.table_view_cb = NoScrollComboBox()
        for d_id, d_name in self.div_titles.items(): 
            self.table_view_cb.addItem(d_name, d_id)
            
        self.table_view_cb.setMaxVisibleItems(25)
        self.table_view_cb.currentIndexChanged.connect(self.populate_table)
        
        tc_top.addWidget(self.table_view_cb)
        tc_top.addStretch()
        tc_layout.addLayout(tc_top)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Planet", "Sign", "Degree", "House", "Retrograde", "Freeze Rashi"])
        self.table_smooth_scroller = SmoothScroller(self.table)
        
        if self.table.horizontalHeader() is not None: 
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            
        tc_layout.addWidget(self.table)
        self.table_container = table_container
        
        right_splitter.addWidget(self.table_container)
        right_splitter.setSizes([750, 200])
        self.table_container.setVisible(self.chk_details.isChecked())
        
        main_splitter.addWidget(left_scroll)
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([370, 930])
    
    def on_div_toggled(self, checked, d_id):
        if getattr(self, "is_updating_ui", False): 
            return
            
        if checked and d_id not in self.active_charts_order: 
            self.active_charts_order.append(d_id)
        elif not checked and d_id in self.active_charts_order: 
            self.active_charts_order.remove(d_id)
            
        if hasattr(self, "chart_layout"): 
            self.update_grid_layout()

    def update_grid_layout(self):
        if getattr(self, "is_updating_ui", False) or not hasattr(self, "chart_layout"): 
            return
        
        v_scroll = self.charts_scroll.verticalScrollBar().value() if hasattr(self, 'charts_scroll') else 0
        h_scroll = self.charts_scroll.horizontalScrollBar().value() if hasattr(self, 'charts_scroll') else 0

        active_divs = self.active_charts_order.copy()
        if not active_divs:
            self.is_updating_ui = True
            if "D1" in self.div_cbs: 
                self.div_cbs["D1"].setChecked(True)
            self.is_updating_ui = False
            self.active_charts_order = ["D1"]
            active_divs = ["D1"]
            
        for i in reversed(range(self.chart_layout.count())):
            if item := self.chart_layout.itemAt(i):
                if item.widget(): 
                    item.widget().setParent(None)
                
        mode_str = self.cb_layout_mode.currentText() if getattr(self, "cb_layout_mode", None) else "3 Columns"
        viewport_h = max(100, self.charts_scroll.viewport().height())
        min_h = max(200, (viewport_h // 2 if mode_str == "1 Left, 2 Right (Stacked)" else viewport_h // 3) - 15)
        
        for i, div in enumerate(active_divs):
            if div not in self.renderers: 
                self.renderers[div] = ChartRenderer()
                self.renderers[div].title = self.div_titles[div]
                self.renderers[div].setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                self.renderers[div].customContextMenuRequested.connect(lambda pos, d=div: self.show_chart_context_menu(pos, d))
                
            renderer = self.renderers[div]
            renderer.setMinimumHeight(min_h)
            
            if mode_str == "1 Left, 2 Right (Stacked)": 
                if i == 0:
                    self.chart_layout.addWidget(renderer, 0, 0, 2, 1)
                elif i == 1:
                    self.chart_layout.addWidget(renderer, 0, 1, 1, 1)
                elif i == 2:
                    self.chart_layout.addWidget(renderer, 1, 1, 1, 1)
                else:
                    self.chart_layout.addWidget(renderer, 2 + (i - 3) // 2, (i - 3) % 2, 1, 1)
            elif mode_str == "2 Columns": 
                self.chart_layout.addWidget(renderer, i // 2, i % 2)
            else: 
                self.chart_layout.addWidget(renderer, i // 3, i % 3)
            
        self.update_settings()
        
        if hasattr(self, 'charts_scroll'):
            QTimer.singleShot(0, lambda: self.charts_scroll.verticalScrollBar().setValue(v_scroll))
            QTimer.singleShot(0, lambda: self.charts_scroll.horizontalScrollBar().setValue(h_scroll))

    def show_chart_context_menu(self, pos, old_div):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #FAFAFA; border: 1px solid #D1D5DB; border-radius: 4px; } "
                           "QMenu::item { padding: 6px 24px 6px 24px; color: #1A1A1A; } "
                           "QMenu::item:selected { background-color: #0078D4; color: white; }")
        
        title_action = menu.addAction(f"--- Swap {old_div} With ---")
        title_action.setEnabled(False)
        menu.addSeparator()
        
        for d_id, d_name in self.div_titles.items():
            if d_id != old_div:
                action = menu.addAction(f"{d_name}")
                action.triggered.connect(lambda checked, new_d=d_id: self.swap_charts(old_div, new_d))
        
        renderer = self.renderers[old_div]
        menu.exec(renderer.mapToGlobal(pos))

    def swap_charts(self, old_div, new_div):
        self.is_updating_ui = True
        
        if old_div in self.active_charts_order:
            old_idx = self.active_charts_order.index(old_div)
            if new_div in self.active_charts_order:
                # Swap positions if both are already visible
                new_idx = self.active_charts_order.index(new_div)
                self.active_charts_order[old_idx], self.active_charts_order[new_idx] = self.active_charts_order[new_idx], self.active_charts_order[old_idx]
            else:
                # Replace old_div with new_div completely
                self.active_charts_order[old_idx] = new_div
                if old_div in self.div_cbs: 
                    self.div_cbs[old_div].setChecked(False)
                if new_div in self.div_cbs: 
                    self.div_cbs[new_div].setChecked(True)
        
        self.is_updating_ui = False
        self.update_grid_layout()
        self.recalculate()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        if not hasattr(self, 'charts_scroll') or (viewport_h := self.charts_scroll.viewport().height()) < 100: 
            return
            
        mode_str = self.cb_layout_mode.currentText() if getattr(self, "cb_layout_mode", None) else "3 Columns"
        min_h = max(200, (viewport_h // 2 if mode_str == "1 Left, 2 Right (Stacked)" else viewport_h // 3) - 15)
        
        for div in getattr(self, 'active_charts_order', []):
            if div in self.renderers: 
                self.renderers[div].setMinimumHeight(min_h)

    def _connect_signals(self):
        self.loc_btn.clicked.connect(self.search_location)
        self.loc_input.returnPressed.connect(self.search_location)
        self.time_ctrl.time_changed.connect(self.on_time_changed)
        
        self.btn_custom_loc.clicked.connect(self.show_custom_loc_dialog)
        self.btn_panchang.clicked.connect(self.show_panchang)
        
        for w in [self.year_spin, self.month_spin, self.day_spin]: 
            w.valueChanged.connect(self.on_ui_datetime_changed)
            
        self.time_edit.timeChanged.connect(self.on_ui_datetime_changed)
        self.btn_play.clicked.connect(self.toggle_play)
        self.speed_combo.currentIndexChanged.connect(self.change_speed)
        
        self.btn_add_m.clicked.connect(lambda: self.time_ctrl.step(60))
        self.btn_add_h.clicked.connect(lambda: self.time_ctrl.step(3600))
        self.btn_add_d.clicked.connect(lambda: self.time_ctrl.step(86400))
        
        self.btn_sub_m.clicked.connect(lambda: self.time_ctrl.step(-60))
        self.btn_sub_h.clicked.connect(lambda: self.time_ctrl.step(-3600))
        self.btn_sub_d.clicked.connect(lambda: self.time_ctrl.step(-86400))
        
        self.btn_next_rashi.clicked.connect(lambda: self.jump_to_transit(self.cb_transit_planet.currentText(), 1))
        self.cb_transit_planet.currentIndexChanged.connect(self.recalculate)
        self.cb_transit_div.currentIndexChanged.connect(self.recalculate)
        
        self.cb_ayanamsa.currentTextChanged.connect(self.update_settings)
        self.cb_outline_mode.currentIndexChanged.connect(self.update_settings)
        
        for chk in [self.chk_symbols, self.chk_rahu, self.chk_arrows, self.chk_tint, self.chk_circular]: 
            chk.stateChanged.connect(self.update_settings)
            
        self.chk_aspects.stateChanged.connect(self.toggle_aspects)
        self.chk_details.stateChanged.connect(self.toggle_details)
        
        self.btn_save_chart.clicked.connect(self.save_chart_dialog)
        self.btn_load_chart.clicked.connect(self.load_chart_dialog)
        self.btn_export_png.clicked.connect(self.export_chart_png)
        self.btn_export_json.clicked.connect(self.export_analysis_json)
        self.btn_visual_guide.clicked.connect(self.show_visual_guide)
        
        if HAS_CUSTOM_VARGAS and hasattr(self, 'btn_add_custom_varga'): 
            self.btn_add_custom_varga.clicked.connect(self.open_custom_varga_dialog)
            
        self.btn_stop_transit.clicked.connect(self.stop_transit_worker)

    def open_custom_varga_dialog(self):
        if not HAS_CUSTOM_VARGAS: 
            return
            
        if custom_vargas.CustomVargaDialog(self).exec(): 
            QMessageBox.information(self, "Restart Required", "Custom Vargas saved successfully!\nPlease restart the application to enable/remove them.")



# ... [inside your class] ...

    def show_panchang(self):
        if not getattr(self, "current_base_chart", None) or "panchang" not in self.current_base_chart: 
            QMessageBox.warning(self, "Not Ready", "Please wait for chart calculation.")
            return
            
        p = self.current_base_chart["panchang"]
        
        # --- NEW LOCATION-BASED CALCULATION ---
        try:
            # Note: Replace datetime.now() with your chart's target date if you have one (e.g., self.chart_date)
            target_date = datetime.datetime.now().date() 
            
            # Create a location object using your class's current coordinates
            loc = LocationInfo(timezone=self.current_tz, latitude=self.current_lat, longitude=self.current_lon)
            
            # Calculate sun events
            s = sun(loc.observer, date=target_date, tzinfo=pytz.timezone(self.current_tz))
            
            # Format to a readable string (e.g., "06:15 AM")
            real_sunrise = s['sunrise'].strftime('%I:%M %p')
            real_sunset = s['sunset'].strftime('%I:%M %p')
        except Exception as e:
            # Fallback to the chart's original data if something goes wrong
            print(f"Sunrise/Sunset calculation failed: {e}")
            real_sunrise = p.get('sunrise_str', 'Unknown')
            real_sunset = p.get('sunset_str', 'Unknown')
        # --------------------------------------

        dlg = QDialog(self)
        dlg.setWindowTitle("Panchang")
        dlg.setMinimumWidth(350)
        
        lay = QVBoxLayout(dlg)
        lbl = QTextBrowser()
        
        # Update the HTML to use the new real_sunrise and real_sunset variables
        lbl.setHtml(
            f"<h3>Panchang Details</h3>"
            f"<p><b>Nakshatra:</b> {p['nakshatra']} (Swami: {p['nakshatra_lord']}), Pada {p['nakshatra_pada']}</p>"
            f"<p><b>Tithi:</b> {p['paksha']} Paksha {p['tithi']}</p>"
            f"<p><b>Sunrise:</b> {real_sunrise}</p>"
            f"<p><b>Sunset:</b> {real_sunset}</p>"
        )
        lay.addWidget(lbl)
        
        # Assuming SmoothScroller is a custom class you've imported
        dlg.panchang_scroller = SmoothScroller(lbl) 
        
        btn = QPushButton("Close")
        btn.clicked.connect(dlg.accept)
        lay.addWidget(btn)
        dlg.exec()


    def show_custom_loc_dialog(self):
        dlg = CustomLocationDialog(self.current_lat, self.current_lon, self)
        if dlg.exec():
            lat, lon = dlg.get_coordinates()
            self.current_lat = lat
            self.current_lon = lon
            self.current_tz = TimezoneFinder().timezone_at(lng=lon, lat=lat) or "UTC"
            
            self.loc_input.setText(f"{lat:.4f}, {lon:.4f}")
            self.loc_status.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} | TZ: {self.current_tz}")
            
            self.save_settings()
            self.recalculate()

    def search_location(self): 
        self.loc_btn.setEnabled(False)
        self.loc_btn.setText("Search...")
        
        self.loc_worker = LocationWorker(self.loc_input.text())
        self.loc_worker.result_ready.connect(self.on_location_found)
        self.loc_worker.error_occurred.connect(self.on_location_error)
        self.loc_worker.start()
        
    def on_location_found(self, lat, lon, tz_name, name): 
        self.current_lat = lat
        self.current_lon = lon
        self.current_tz = tz_name
        
        self.loc_status.setText(f"Lat: {lat:.4f}, Lon: {lon:.4f} | TZ: {tz_name}")
        self.loc_btn.setEnabled(True)
        self.loc_btn.setText("Search")
        
        self.save_settings()
        self.recalculate()
        
    def on_location_error(self, err_msg): 
        QMessageBox.warning(self, "Location Error", err_msg)
        self.loc_btn.setEnabled(True)
        self.loc_btn.setText("Search")
        
    def get_days_in_month(self, year, month): 
        if month in {4, 6, 9, 11}:
            return 30
        if month == 2:
            if year > 1582:
                if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                    return 29
                return 28
            else:
                if year % 4 == 0:
                    return 29
                return 28
        return 31

    def on_time_changed(self, dt):
        self.is_updating_ui = True
        self.day_spin.setMaximum(self.get_days_in_month(dt['year'], dt['month']))
        self.year_spin.setValue(dt['year'])
        self.month_spin.setValue(dt['month'])
        self.day_spin.setValue(dt['day'])
        self.time_edit.setTime(QTime(dt['hour'], dt['minute'], int(dt['second'])))
        self.is_updating_ui = False
        
        self.recalculate()

    def on_ui_datetime_changed(self):
        if self.is_updating_ui: 
            return
            
        max_days = self.get_days_in_month(self.year_spin.value(), self.month_spin.value())
        if self.day_spin.maximum() != max_days: 
            self.is_updating_ui = True
            self.day_spin.setMaximum(max_days)
            self.is_updating_ui = False
            
        t = self.time_edit.time()
        self.time_ctrl.set_time({
            'year': self.year_spin.value(), 
            'month': self.month_spin.value(), 
            'day': self.day_spin.value(), 
            'hour': t.hour(), 
            'minute': t.minute(), 
            'second': t.second()
        })

    def toggle_play(self): 
        self.btn_play.setText("⏸ Pause" if self.time_ctrl.toggle_animation() else "▶ Play")
        
    def change_speed(self): 
        speeds = [1.0, 10.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0, 14400.0, 86400.0, 604800.0]
        self.time_ctrl.set_speed(speeds[self.speed_combo.currentIndex()])
        
    def update_settings(self):
        if self.is_updating_ui: 
            return
            
        self.ephemeris.set_ayanamsa(self.cb_ayanamsa.currentText())
        
        for r in self.renderers.values(): 
            r.outline_mode = self.cb_outline_mode.currentText()
            r.use_symbols = self.chk_symbols.isChecked()
            r.show_rahu_ketu = self.chk_rahu.isChecked()
            r.show_aspects = self.chk_aspects.isChecked()
            r.show_arrows = self.chk_arrows.isChecked()
            r.use_tint = self.chk_tint.isChecked()
            r.use_circular = self.chk_circular.isChecked()
            r.visible_aspect_planets = {p for p, cb in self.aspect_cb.items() if cb.isChecked()}
            
        self.save_settings()
        self.recalculate()
        
    def toggle_aspects(self): 
        self.aspects_group.setVisible(self.chk_aspects.isChecked())
        self.chk_arrows.setVisible(self.chk_aspects.isChecked())
        self.chk_tint.setVisible(self.chk_aspects.isChecked())
        self.update_settings()
    
    def toggle_details(self): 
        self.table_container.setVisible(self.chk_details.isChecked())
        if self.chk_details.isChecked(): 
            self.populate_table()
        self.save_settings()
        
    def get_current_chart_info(self): 
        return {
            "location": self.loc_input.text(), 
            "lat": self.current_lat, 
            "lon": self.current_lon, 
            "tz": self.current_tz, 
            "datetime_dict": self.time_ctrl.current_time
        }

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
                
                self.is_updating_ui = True
                self.frozen_planets = {}
                
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
                        
                    data["tz"] = TimezoneFinder().timezone_at(lng=data["lon"], lat=data["lat"]) or "UTC"
                    
                self.loc_input.setText(data.get("location", "New Delhi, India"))
                self.current_lat = data.get("lat", 28.6139)
                self.current_lon = data.get("lon", 77.2090)
                self.current_tz = data.get("tz", "Asia/Kolkata")
                
                self.loc_status.setText(f"Lat: {self.current_lat:.4f}, Lon: {self.current_lon:.4f}\nTZ: {self.current_tz}")
                
                if "datetime_dict" in data and isinstance(data["datetime_dict"], dict): 
                    self.time_ctrl.set_time(data["datetime_dict"])
                elif "datetime" in data:
                    try: 
                        dt_val = data["datetime"]
                        if isinstance(dt_val, dict):
                            self.time_ctrl.set_time(dt_val)
                        else:
                            parsed = datetime.datetime.fromisoformat(dt_val)
                            self.time_ctrl.set_time({
                                'year': parsed.year, 'month': parsed.month, 'day': parsed.day, 
                                'hour': parsed.hour, 'minute': parsed.minute, 'second': parsed.second
                            })
                    except Exception as e: 
                        print(f"Error parsing date from file: {e}")
                        
                self.is_updating_ui = False
                self.is_chart_saved = True
                
                self.save_settings()
                self.recalculate()
            else: 
                QMessageBox.warning(self, "Error", "Failed to load chart data.")

    def export_chart_png(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart PNG", "", "PNG Files (*.png);;All Files (*)")
        if path: 
            self.charts_container.grab().save(path, "PNG")

    def export_analysis_json(self):
        os.makedirs("analysis_export", exist_ok=True)
        
        default_file = "Final_Analysis.json"
        if getattr(self, "current_file_path", None):
            default_file = f"{os.path.splitext(os.path.basename(self.current_file_path))[0]}_analysis.json"
            
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Analysis JSON", 
            os.path.join("analysis_export", default_file), 
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not path: 
            return
            
        try:
            chart_data = self.ephemeris.calculate_chart(self.time_ctrl.current_time, self.current_lat, self.current_lon, self.current_tz)
            
            export_data = {
                "metadata": {
                    "location": self.loc_input.text(), 
                    "latitude": self.current_lat, 
                    "longitude": self.current_lon, 
                    "datetime": self.time_ctrl.current_time, 
                    "ayanamsa": self.cb_ayanamsa.currentText()
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
                jd_utc = astro_engine.dt_dict_to_utc_jd(self.time_ctrl.current_time, self.current_tz)
                export_data["vimshottari_dasha_timeline"] = self.ephemeris.get_dasha_export_list(jd_utc, moon_p["lon"])
            
            def get_ordinal(n):
                if 11 <= (n % 100) <= 13: return f"{n}th"
                return f"{n}" + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            
            for div in self.div_titles.keys():
                div_data = self.ephemeris.compute_divisional_chart(chart_data, div) if div != "D1" else chart_data
                
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
                
                auspicious_analysis = []
                auspicious_houses = {1, 2, 4, 5, 7, 9, 10, 11}
                for p in div_data["planets"]:
                    if not p.get("lord_of"): continue
                    
                    for ruled_house in p["lord_of"]:
                        if ruled_house in auspicious_houses and p["house"] in auspicious_houses:
                            status = "Neutral"
                            if p.get("exalted"): status = "Exalted"
                            elif p.get("debilitated"): status = "Debilitated"
                            elif p.get("own_sign"): status = "Own Sign"
                            
                            analysis_str = f"{get_ordinal(ruled_house)} lord ({p['name']}) is in {get_ordinal(p['house'])} house ({status})"
                            auspicious_analysis.append(analysis_str)
                
                export_data["divisional_charts"][div] = {
                    "ascendant": {
                        "sign_index": div_data["ascendant"]["sign_index"], 
                        "degree_in_sign": div_data["ascendant"]["degree"] % 30, 
                        "nakshatra": div_data["ascendant"].get("nakshatra"), 
                        "nakshatra_lord": div_data["ascendant"].get("nakshatra_lord"), 
                        "nakshatra_pada": div_data["ascendant"].get("nakshatra_pada")
                    }, 
                    "planets": planets_list, 
                    "auspicious_analysis": auspicious_analysis
                }
                
            with open(path, 'w') as f: 
                json.dump(export_data, f, indent=4)
                
            QMessageBox.information(self, "Export Successful", "Extensive Analysis JSON exported successfully!")
        except Exception as e: 
            QMessageBox.critical(self, "Export Error", f"Failed to export JSON:\n{str(e)}")

    def show_visual_guide(self): 
        VisualGuideDialog(self).exec()

    def closeEvent(self, event): 
        self.do_autosave()
        if hasattr(self, 'calc_worker'):
            self.calc_worker.stop()
        if self.jump_worker and self.jump_worker.isRunning():
            self.jump_worker.stop_flag = True
            self.jump_worker.wait()
        super().closeEvent(event)

    def stop_transit_worker(self):
        if hasattr(self, 'btn_worker') and self.btn_worker.isRunning():
            self.btn_worker.stop_flag = True
        if self.jump_worker and self.jump_worker.isRunning():
            self.jump_worker.stop_flag = True
            
        self.btn_stop_transit.setVisible(False)
        self.cached_btn_jds = {'asc_prev': None, 'asc_next': None, 'p_prev': None, 'p_next': None}
        self.update_btn_labels()

    def check_and_launch_btn_worker(self, jd_utc, selected_div, selected_planet):
        if len(self.frozen_planets) > 4:
            if hasattr(self, 'btn_worker') and self.btn_worker.isRunning():
                self.btn_worker.stop_flag = True
            self.btn_stop_transit.setVisible(False)
            self.cached_btn_jds = {'asc_prev': None, 'asc_next': None, 'p_prev': None, 'p_next': None}
            self.last_worker_state = "OVER_LIMIT_RESET"
            self.update_btn_labels()
            return

        sorted_frozen = sorted([(k, v['sign_idx'], v['div']) for k, v in self.frozen_planets.items()])
        state_hash = f"{sorted_frozen}_{selected_div}_{selected_planet}_{self.cb_ayanamsa.currentText()}"
        
        if not hasattr(self, 'last_worker_state') or self.last_worker_state != state_hash:
            self.last_worker_state = state_hash
            self.launch_btn_worker(jd_utc, selected_div, selected_planet)
            return

        if hasattr(self, 'cached_btn_jds') and self.cached_btn_jds:
            if self.cached_btn_jds.get('asc_next') and jd_utc > self.cached_btn_jds['asc_next']:
                self.launch_btn_worker(jd_utc, selected_div, selected_planet)
            elif self.cached_btn_jds.get('asc_prev') and jd_utc < self.cached_btn_jds['asc_prev']:
                self.launch_btn_worker(jd_utc, selected_div, selected_planet)
            elif self.cached_btn_jds.get('p_next') and jd_utc > self.cached_btn_jds['p_next']:
                self.launch_btn_worker(jd_utc, selected_div, selected_planet)
            elif self.cached_btn_jds.get('p_prev') and jd_utc < self.cached_btn_jds['p_prev']:
                self.launch_btn_worker(jd_utc, selected_div, selected_planet)

    def launch_btn_worker(self, jd_utc, selected_div, selected_planet):
        if hasattr(self, 'btn_worker') and self.btn_worker.isRunning():
            self.btn_worker.stop_flag = True
            try: 
                self.btn_worker.results_ready.disconnect()
            except: 
                pass
            try: 
                self.btn_worker.partial_result.disconnect()
            except: 
                pass
            
        self.cached_btn_jds = {'asc_prev': None, 'asc_next': None, 'p_prev': None, 'p_next': None} 
        
        self.btn_worker = ButtonTimeWorker(
            jd_utc, self.current_lat, self.current_lon, 
            copy.deepcopy(self.frozen_planets), selected_div, selected_planet, 
            self.cb_ayanamsa.currentText(), self.ephemeris.custom_vargas
        )
        self.btn_worker.partial_result.connect(self.on_btn_partial_ready)
        self.btn_worker.results_ready.connect(self.on_btn_times_ready)
        self.btn_worker.start()
        self.btn_stop_transit.setVisible(True)

    def on_btn_partial_ready(self, key, val):
        if hasattr(self, 'cached_btn_jds'):
            self.cached_btn_jds[key] = val
            self.update_btn_labels()

    def on_btn_times_ready(self, res):
        self.cached_btn_jds = res
        self.update_btn_labels()
        if not (self.jump_worker and self.jump_worker.isRunning()):
            self.btn_stop_transit.setVisible(False)

    def update_btn_labels(self):
        if len(self.frozen_planets) > 4:
            if hasattr(self, 'btn_prev_lagna'):
                self.btn_prev_lagna.setText("< ...")
                self.btn_next_lagna.setText("... >")
                self.btn_prev_rashi.setText("< ...")
                self.btn_next_rashi.setText("... >")
            return

        jd_utc = astro_engine.dt_dict_to_utc_jd(self.time_ctrl.current_time, self.current_tz)
        if not hasattr(self, 'cached_btn_jds'): 
            return
        
        def format_btn_time(jd, is_prev=True):
            if not jd: return "< Calc..." if is_prev else "Calc... >"
            delta = abs(jd - jd_utc)
                
            y = int(delta // 365.25)
            rem = delta % 365.25
            mo = int(rem // 30.436875)
            d = int(rem % 30.436875)
            h = int((delta * 24) % 24)
            mi = int((delta * 1440) % 60)
            
            time_str = ""
            if y > 0: time_str += f"{y}y "
            if mo > 0: time_str += f"{mo}m "
            if d > 0: time_str += f"{d}d "
            if y == 0 and mo == 0 and h > 0: time_str += f"{h}h "
            if not time_str: time_str = f"{mi}m"
            
            return f"< {time_str.strip()}" if is_prev else f"{time_str.strip()} >"

        if hasattr(self, 'btn_prev_lagna'):
            self.btn_prev_lagna.setText(format_btn_time(self.cached_btn_jds.get('asc_prev'), True))
            self.btn_next_lagna.setText(format_btn_time(self.cached_btn_jds.get('asc_next'), False))
            self.btn_prev_rashi.setText(format_btn_time(self.cached_btn_jds.get('p_prev'), True))
            self.btn_next_rashi.setText(format_btn_time(self.cached_btn_jds.get('p_next'), False))

    def jump_to_transit(self, body_name, direction):
        if self.time_ctrl.is_playing: 
            self.toggle_play()
        
        jd_utc = astro_engine.dt_dict_to_utc_jd(self.time_ctrl.current_time, self.current_tz)
        jd_target = None
        
        if hasattr(self, 'cached_btn_jds') and self.cached_btn_jds:
            if body_name == "Ascendant":
                jd_target = self.cached_btn_jds.get('asc_next' if direction == 1 else 'asc_prev')
            else:
                jd_target = self.cached_btn_jds.get('p_next' if direction == 1 else 'p_prev')
                
        if jd_target:
            target_dt = astro_engine.utc_jd_to_dt_dict(jd_target + ((1 if direction == 1 else -1) / 86400.0), self.current_tz)
            self.time_ctrl.set_time(target_dt)
        else:
            if self.jump_worker and self.jump_worker.isRunning():
                return
            
            self.btn_prev_lagna.setText("< Wait...")
            self.btn_next_lagna.setText("Wait... >")
            self.btn_prev_rashi.setText("< Wait...")
            self.btn_next_rashi.setText("Wait... >")
            
            transit_div = getattr(self, 'cb_transit_div', None) and self.cb_transit_div.currentText() or "D1"
            
            engine = astro_engine.EphemerisEngine()
            engine.set_ayanamsa(self.cb_ayanamsa.currentText())
            engine.set_custom_vargas(self.ephemeris.custom_vargas)
            
            zodiacs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
            tgt_sign = "Any Rashi"
            actual_body_name = "Ascendant" if body_name == "Ascendant" else body_name
            
            if actual_body_name in self.frozen_planets and self.frozen_planets[actual_body_name]["div"] == transit_div:
                tgt_sign = zodiacs[self.frozen_planets[actual_body_name]["sign_idx"]]

            self.jump_worker = JumpSearchWorker(
                engine, jd_utc, self.current_lat, self.current_lon, 
                actual_body_name, direction, transit_div, self.frozen_planets, tgt_sign
            )
            self.jump_worker.finished.connect(lambda jd: self.on_jump_search_finished(jd, direction))
            self.jump_worker.start()
            self.btn_stop_transit.setVisible(True)

    def on_jump_search_finished(self, jd_target, direction):
        if not (self.btn_worker and self.btn_worker.isRunning()):
            self.btn_stop_transit.setVisible(False)
            
        if jd_target:
            target_dt = astro_engine.utc_jd_to_dt_dict(jd_target + ((1 if direction == 1 else -1) / 86400.0), self.current_tz)
            self.time_ctrl.set_time(target_dt)
        else:
            QMessageBox.warning(self, "Not Found", "Could not find a valid transit match.")
            
        self.update_btn_labels()

    def recalculate(self):
        if getattr(self, 'is_loading_settings', False): 
            return
            
        try:
            real_now = datetime.datetime.now(datetime.timezone.utc)
            real_now_jd = swe.julday(real_now.year, real_now.month, real_now.day, real_now.hour + real_now.minute/60.0 + real_now.second/3600.0)
            
            selected_div = getattr(self, 'cb_transit_div', None) and self.cb_transit_div.currentText() or "D1"
            selected_planet = getattr(self, 'cb_transit_planet', None) and self.cb_transit_planet.currentText() or "Sun"
            active_divs = getattr(self, 'active_charts_order', []).copy()
            
            self.calc_worker.request_calc(
                self.time_ctrl.current_time.copy(), 
                self.current_lat, 
                self.current_lon, 
                self.current_tz, 
                real_now_jd, 
                selected_div, 
                selected_planet, 
                active_divs, 
                copy.deepcopy(self.frozen_planets)
            )
        except Exception as e: 
            print(f"Recalculation dispatch error: {e}")

    def on_calc_finished(self, chart_data, div_charts, violation, violating_planet, violating_div):
        self.current_base_chart = chart_data
        
        if violation:
            for p_name, f_info in self.frozen_planets.items():
                d = f_info["div"]
                c = div_charts.get(d) or (self.ephemeris.compute_divisional_chart(chart_data, d) if d != "D1" else chart_data)
                
                if p_name == "Ascendant":
                    f_info["sign_idx"] = c["ascendant"]["sign_index"]
                else:
                    if p_in_c := next((x for x in c["planets"] if x["name"] == p_name), None):
                        f_info["sign_idx"] = p_in_c["sign_index"]

            if getattr(self.time_ctrl, 'is_playing', False):
                self.time_ctrl.timer.stop()
                self.btn_play.setText("▶ Play")
                self.time_ctrl.is_playing = False
                QMessageBox.information(self, "Animation Paused", f"{violating_planet} entered a new sign in {violating_div}.")

        jd_utc = chart_data.get("current_jd")
        selected_planet = getattr(self, 'cb_transit_planet', None) and self.cb_transit_planet.currentText() or "Sun"
        selected_div = getattr(self, 'cb_transit_div', None) and self.cb_transit_div.currentText() or "D1"

        if jd_utc is not None:
            self.check_and_launch_btn_worker(jd_utc, selected_div, selected_planet)
        
        self.update_btn_labels()

        for div in getattr(self, 'active_charts_order', []):
            if div in self.renderers and div in div_charts:
                self.renderers[div].update_chart(div_charts[div], chart_data if div != "D1" else None)
        
        self.populate_table()
        
        if dasha := chart_data.get("dasha_sequence"):
            self.dasha_label.setText("Now: " + " -> ".join([f"<b style='color:#8B4513;'>{p}</b>" for p in dasha]))

    def populate_table(self):
        if not getattr(self, 'table_container', None) or not self.table_container.isVisible() or not getattr(self, 'current_base_chart', None): 
            return
            
        div_view = self.table_view_cb.currentData() or "D1"
        chart = self.ephemeris.compute_divisional_chart(self.current_base_chart, div_view) if div_view != "D1" else self.current_base_chart
        
        v_scroll = self.table.verticalScrollBar().value()
        zodiacs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        
        bodies = [("Lagna (Asc.)", chart["ascendant"])] + [(p["name"], p) for p in chart["planets"]]
        
        if self.table.rowCount() != len(bodies):
            self.table.setRowCount(len(bodies))

        for row, (b_name, b_data) in enumerate(bodies):
            s_idx = b_data["sign_index"]
            is_asc = (b_name == "Lagna (Asc.)")
            actual_name = "Ascendant" if is_asc else b_name
            deg = b_data.get("degree", 0.0) % 30.0 if is_asc else b_data['deg_in_sign']
            house = "1" if is_asc else str(b_data["house"])
            retro = "No" if is_asc else ("Yes" if b_data.get("retro") else "No")
            
            deg_str = f"{int(deg)}° {int((deg % 1) * 60):02d}'"
            columns_data = [b_name, zodiacs[s_idx], deg_str, house, retro]
            
            for col, text in enumerate(columns_data):
                item = self.table.item(row, col)
                if not item:
                    self.table.setItem(row, col, QTableWidgetItem(text))
                else:
                    item.setText(text)
                    
            is_frozen = actual_name in self.frozen_planets and self.frozen_planets[actual_name]["div"] == div_view
            
            w = self.table.cellWidget(row, 5)
            if not w:
                cb = QCheckBox("Freeze")
                cb.setProperty("p_name", actual_name)
                
                def on_toggle(checked, cb_ref=cb):
                    pn = cb_ref.property("p_name")
                    si = cb_ref.property("s_idx")
                    if checked: 
                        self.frozen_planets[pn] = {"sign_idx": si, "div": div_view}
                    else: 
                        self.frozen_planets.pop(pn, None)
                    self.recalculate()
                    
                cb.toggled.connect(on_toggle)
                
                w = QWidget()
                l = QHBoxLayout(w)
                l.setContentsMargins(0,0,0,0)
                l.setAlignment(Qt.AlignmentFlag.AlignCenter)
                l.addWidget(cb)
                self.table.setCellWidget(row, 5, w)
            
            cb = self.table.cellWidget(row, 5).findChild(QCheckBox)
            cb.blockSignals(True)
            cb.setProperty("s_idx", s_idx)
            cb.setChecked(is_frozen)
            cb.blockSignals(False)

        self.table.verticalScrollBar().setValue(v_scroll)

GLOBAL_FONT_FAMILY, GLOBAL_FONT_SCALE, GLOBAL_PRIMARY_COLOR = "Segoe UI", 11, "#4A90E2" 

if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    
    # Calculate global scalable base font
    base_font_size = int(11 * GLOBAL_FONT_SCALE_MULTIPLIER)
    
    app.setFont(QFont(GLOBAL_UI_FONT_FAMILY, base_font_size))
    app.setStyle("Fusion")
    
    # Apply Primary Color to buttons explicitly
    app.setStyleSheet(f"QGroupBox::title {{ color: {GLOBAL_PRIMARY_COLOR}; font-weight: bold; }} "
                      f"QPushButton {{ padding: 4px 8px; }} "
                      f"QPushButton:checked {{ background-color: {GLOBAL_PRIMARY_COLOR}; color: white; }}")
    
    window = AstroApp()
    window.showMaximized() 
    sys.exit(app.exec())