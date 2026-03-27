#main.py
import pkgutil, sys,datetime,json,os,math,pytz,swisseph as swe,time,multiprocessing,queue,glob,copy,importlib.util

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
import dynamic_settings_modules
from dynamic_settings_modules.zzlogger_mod import info_print
import save_prefs,animation,astro_engine
import help_content
from chart_renderer import ChartRenderer

try:
    import custom_vargas
    HAS_CUSTOM_VARGAS = True
except ImportError:
    HAS_CUSTOM_VARGAS = False

# ==========================================
# ASTROLOGICAL REFERENCE DICTIONARIES
# ==========================================
ZODIAC_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

DIV_TITLES = {
    "D1": "D1 (Rashi)", "D2": "D2 (Hora)", "D3": "D3 (Drekkana)",
    "D4": "D4 (Chaturthamsha)", "D5": "D5 (Panchamsha)", "D6": "D6 (Shashthamsha)",
    "D7": "D7 (Saptamsha)", "D8": "D8 (Ashtamsha)", "D9": "D9 (Navamsha)",
    "D10": "D10 (Dashamsha)", "D11": "D11 (Rudramsha)", "D12": "D12 (Dwadashamsha)",
    "D16": "D16 (Shodashamsha)", "D20": "D20 (Vimshamsha)", "D24": "D24 (Chaturvimshamsha)",
    "D27": "D27 (Bhamsha)", "D30": "D30 (Trimshamsha)", "D40": "D40 (Khavedamsha)",
    "D45": "D45 (Akshavedamsha)", "D60": "D60 (Shashtiamsha)"
}

AUSPICIOUS_HOUSES = {1, 2, 4, 5, 7, 9, 10, 11}

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
    """Robust path resolution for PyInstaller, Nuitka, and standard Python."""
    try: 
        # PyInstaller temp folder
        base_path = sys._MEIPASS
        mode = "PyInstaller"
    except AttributeError:
        # Nuitka and standard Python
        base_path = os.path.dirname(os.path.abspath(__file__))
        mode = "Standard/Nuitka"
        
    final_path = os.path.join(base_path, relative_path)
    #print(f"[DEBUG] resource_path ({mode}): {final_path}")
    return final_path

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
            
            class DummyStop:
                def __init__(self, worker): self.worker = worker
                def is_set(self): return self.worker.stop_flag
            ds = DummyStop(self)

            if "Ascendant" in self.frozen_planets and self.frozen_planets["Ascendant"]["div"] == self.transit_div:
                asc_tgt_sign = ZODIAC_NAMES[self.frozen_planets["Ascendant"]["sign_idx"]]
            else:
                asc_tgt_sign = "Any Rashi"

            res['asc_prev'] = engine.search_transit_core(self.jd_utc, self.lat, self.lon, "Ascendant", -1, self.transit_div, copy.deepcopy(self.frozen_planets), asc_tgt_sign, ds)
            if self.stop_flag: return
            self.partial_result.emit('asc_prev', res['asc_prev'])

            res['asc_next'] = engine.search_transit_core(self.jd_utc, self.lat, self.lon, "Ascendant", 1, self.transit_div, copy.deepcopy(self.frozen_planets), asc_tgt_sign, ds)
            if self.stop_flag: return
            self.partial_result.emit('asc_next', res['asc_next'])

            if self.transit_planet in self.frozen_planets and self.frozen_planets[self.transit_planet]["div"] == self.transit_div:
                p_tgt_sign = ZODIAC_NAMES[self.frozen_planets[self.transit_planet]["sign_idx"]]
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
            app_icon = QIcon(resource_path("icon.ico"))
            self.setWindowIcon(app_icon)
            # This magic line applies the icon globally to ALL windows, including plugins
            QApplication.instance().setWindowIcon(app_icon)

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

        self.div_titles = dict(DIV_TITLES)

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
        self.module_reload_timer.setInterval(500)  # 500ms debounce
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




    def _setup_module_watcher(self):
        modules_dir = resource_path("dynamic_settings_modules")
        os.makedirs(modules_dir, exist_ok=True)
        
        if modules_dir not in self.module_watcher.directories():
            self.module_watcher.addPath(modules_dir)
            #print(f"[DEBUG] Watcher activated on: {modules_dir}")
            
        self.module_watcher.directoryChanged.connect(self._trigger_module_reload)
        self.module_watcher.fileChanged.connect(self._trigger_module_reload)

    def _load_dynamic_modules(self):
            import importlib
            import sys
            import os
            
            # 1. Clear out old UI
            while self.dynamic_modules_layout.count():
                item = self.dynamic_modules_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    while item.layout().count():
                        sub = item.layout().takeAt(0)
                        if sub.widget(): sub.widget().deleteLater()
                    item.layout().deleteLater()

            modules_dir = resource_path("dynamic_settings_modules")
            discovered_modules = set()

            # 2. Discover Baked-in Modules via __init__.py mapping
            try:
                import dynamic_settings_modules
                if hasattr(dynamic_settings_modules, '__all__'):
                    for baked_mod in dynamic_settings_modules.__all__:
                        discovered_modules.add(baked_mod)
            except Exception as e:
                print(f"[DEBUG] Failed to read baked-in map: {e}")

            # 3. Discover loose files (Allows users to drop in new plugins later)
            if os.path.exists(modules_dir):
                for f in os.listdir(modules_dir):
                    name, ext = os.path.splitext(f)
                    if ext in ('.py', '.pyc', '.pyd', '.so') and not name.startswith("__"):
                        discovered_modules.add(name)

            # 4. Pre-load and Extract Metadata
            loaded_mods = {}
            for mod_name in discovered_modules:
                full_name = f"dynamic_settings_modules.{mod_name}"
                try:
                    if full_name in sys.modules:
                        mod = importlib.reload(sys.modules[full_name])
                    else:
                        mod = importlib.import_module(full_name)
                    
                    if hasattr(mod, "setup_ui"):
                        # Extract variables, fallback to defaults if absent
                        group = getattr(mod, "PLUGIN_GROUP", "Ungrouped")
                        index = getattr(mod, "PLUGIN_INDEX", 999)
                        loaded_mods[mod_name] = {
                            "mod": mod, 
                            "group": str(group), 
                            "index": int(index)
                        }
                    else:
                        print(f"[DEBUG] Skipped (No setup_ui): {mod_name}")
                        
                except Exception as e:
                    print(f"[DEBUG] ERROR importing {mod_name}: {e}")

            # 5. Sorting Logic
            # Determine the lowest index claimed by any plugin in each group
            group_master_index = {}
            for data in loaded_mods.values():
                g = data["group"]
                idx = data["index"]
                if g not in group_master_index or idx < group_master_index[g]:
                    group_master_index[g] = idx

            # Sort strictly by Group Priority -> Group Name -> Plugin Priority -> Plugin Name
            sorted_mod_names = sorted(
                loaded_mods.keys(),
                key=lambda k: (
                    group_master_index[loaded_mods[k]["group"]], 
                    loaded_mods[k]["group"],                      
                    loaded_mods[k]["index"],                      
                    k                                             
                )
            )

            # 6. Inject into UI sequentially
            added_modules = 0
            for mod_name in sorted_mod_names:
                data = loaded_mods[mod_name]
                mod = data["mod"]
                try:
                    mod.setup_ui(self, self.dynamic_modules_layout)
                    added_modules += 1
                    #print(f"[DEBUG] UI Setup: {mod_name} (Group: '{data['group']}', Index: {data['index']})")
                except Exception as e:
                    print(f"[DEBUG] ERROR in setup_ui for {mod_name}: {e}")

            self.dynamic_modules_group.setVisible(added_modules > 0)

    def _trigger_module_reload(self, path=None):
        self.module_reload_timer.start()

    
    def get_current_location(self):
        """Returns the current location info dictionary for plugins."""
        return {
            "name": self.loc_input.text(),
            "lat": self.current_lat,
            "lon": self.current_lon,
            "tz": self.current_tz
        }
        
    def get_current_datetime(self):
        """Returns the current date and time dictionary for plugins."""
        return self.time_ctrl.current_time

    def get_chart_data(self, div="D1"):
        """Returns the computed chart data for a specific divisional chart."""
        if not getattr(self, "current_base_chart", None):
            return None
        if div == "D1":
            return self.current_base_chart
        return self.ephemeris.compute_divisional_chart(self.current_base_chart, div)
    # ------------------------------

    def load_settings(self):
        settings_file = "astro_settings.json"
        if not os.path.exists(settings_file):
            self.update_grid_layout()
            return

        try:
            with open(settings_file, "r") as f:
                prefs = json.load(f)

            if "location" in prefs:
                self.loc_input.setText(prefs["location"])
            if "lat" in prefs:
                self.current_lat = prefs["lat"]
            if "lon" in prefs:
                self.current_lon = prefs["lon"]
            if "tz" in prefs:
                self.current_tz = prefs["tz"]

            self.loc_status.setText(
                f"Lat: {self.current_lat:.4f}, Lon: {self.current_lon:.4f} | {self.current_tz}")

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
                ("use_circular", self.chk_circular),
                ("show_tooltips", self.show_tooltips)
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
                "show_tooltips": self.show_tooltips.isChecked(),
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

                existing_count = len(
                    glob.glob(os.path.join('autosave', 'tmp_*_saveon_*.json')))
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
        self.btn_custom_loc.setStyleSheet(
            "border-radius: 4px; font-weight: bold; background-color: #DAA520; color: white; border: none;")
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
        self.btn_panchang.setStyleSheet(
            "border-radius: 4px; font-weight: bold; background-color: #DAA520; color: white; border: none;")
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
        self.dasha_label.setStyleSheet(
            "color: #8B4513; font-weight: bold; font-size: 11px; margin-top: 4px;")

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
            cb.toggled.connect(
                lambda checked, did=d_id: self.on_div_toggled(checked, did))
            div_layout.addWidget(cb, i // 4, i % 4)

        if HAS_CUSTOM_VARGAS:
            self.btn_add_custom_varga = QPushButton("Manage Custom Vargas")
            self.btn_add_custom_varga.setStyleSheet(
                "background-color: #2980b9; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
            div_layout.addWidget(self.btn_add_custom_varga, len(
                self.div_titles) // 4 + 1, 0, 1, 4)

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
        self.speed_combo.addItems(
            ["1x", "10x", "60x", "120x", "300x", "600x", "1800x", "3600x", "14400x", "86400x", "604800x"])
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
        self.cb_transit_planet.addItems(
            ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
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
        self.btn_stop_transit.setStyleSheet(
            "background-color: #c0392b; color: white; font-weight: bold; border-radius: 4px; padding: 4px;")
        self.btn_stop_transit.setVisible(False)
        transit_layout.addWidget(self.btn_stop_transit, 3, 0, 1, 3)

        transit_group.setLayout(transit_layout)

        # Settings Group
        set_group = QGroupBox("Settings")
        set_layout = QVBoxLayout()
        set_layout.setContentsMargins(4, 4, 4, 4)
        set_layout.setSpacing(4)

        self.cb_ayanamsa = NoScrollComboBox()
        self.cb_ayanamsa.addItems([
            "True Lahiri (Chitrapaksha)", "Lahiri", "Raman", "Fagan/Bradley", 
            "Krishnamurti (KP)", "True Revati", "True Pushya", 
            "Suryasiddhanta", "Yukteshwar", "Usha/Shashi", "Bhasin"
        ])

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
        self.show_tooltips = QCheckBox("Tooltips")

        self.chk_rahu.setChecked(True)
        self.chk_arrows.setChecked(True)
        self.chk_tint.setChecked(True)
        self.chk_details.setChecked(True)
        self.chk_circular.setChecked(False)
        self.show_tooltips.setChecked(True)

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
        chk_grid.addWidget(self.chk_details, 6, 0)
        chk_grid.addWidget(self.show_tooltips, 6, 1)
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
        self.btn_visual_guide = QPushButton(
            "Guide, Legend, Credits and Privacy")
        self.btn_visual_guide.setFixedSize(260, 24)
        # --- Visual Guide Button (Help/Green Theme) ---
        self.btn_visual_guide.setStyleSheet("""
            QPushButton {
                font-size: 11px; 
                font-weight: bold; 
                color: #1E8449; 
                background-color: #E8F8F5; 
                border: 1px solid #A2D9CE; 
                border-radius: 4px;
                padding: 2px 5px;
            }
            QPushButton:hover {
                background-color: #D1F2EB;
                border-color: #1E8449;
            }
            QPushButton:pressed {
                background-color: #A9DFBF;
                border-style: inset;
            }
        """)

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
        self.table.setHorizontalHeaderLabels(
            ["Planet", "Sign", "Degree", "House", "Retrograde", "Freeze Rashi"])
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

# OLD:
        # for i in reversed(range(self.chart_layout.count())):
        #     if item := self.chart_layout.itemAt(i):
        #         if item.widget():
        #             item.widget().setParent(None)

        # NEW:
        for i in reversed(range(self.chart_layout.count())):
            item = self.chart_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                self.chart_layout.removeWidget(widget)
                widget.hide() # Safely tuck it away until it's added back

        mode_str = self.cb_layout_mode.currentText() if getattr(
            self, "cb_layout_mode", None) else "3 Columns"
        viewport_h = max(100, self.charts_scroll.viewport().height())
        min_h = max(200, (viewport_h // 2 if mode_str ==
                    "1 Left, 2 Right (Stacked)" else viewport_h // 3) - 15)

        for i, div in enumerate(active_divs):
            if div not in self.renderers:
                self.renderers[div] = ChartRenderer()
                self.renderers[div].title = self.div_titles[div]
                self.renderers[div].setContextMenuPolicy(
                    Qt.ContextMenuPolicy.CustomContextMenu)
                self.renderers[div].customContextMenuRequested.connect(
                    lambda pos, d=div: self.show_chart_context_menu(pos, d))

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
                    self.chart_layout.addWidget(
                        renderer, 2 + (i - 3) // 2, (i - 3) % 2, 1, 1)
            elif mode_str == "2 Columns":
                self.chart_layout.addWidget(renderer, i // 2, i % 2)
            else:
                self.chart_layout.addWidget(renderer, i // 3, i % 3)
            renderer.show()  # <--- ADD THIS LINE HERE

        self.update_settings()

        if hasattr(self, 'charts_scroll'):
            QTimer.singleShot(
                0, lambda: self.charts_scroll.verticalScrollBar().setValue(v_scroll))
            QTimer.singleShot(
                0, lambda: self.charts_scroll.horizontalScrollBar().setValue(h_scroll))

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
                action.triggered.connect(
                    lambda checked, new_d=d_id: self.swap_charts(old_div, new_d))

        renderer = self.renderers[old_div]
        menu.exec(renderer.mapToGlobal(pos))

    def swap_charts(self, old_div, new_div):
        self.is_updating_ui = True

        if old_div in self.active_charts_order:
            old_idx = self.active_charts_order.index(old_div)
            if new_div in self.active_charts_order:
                # Swap positions if both are already visible
                new_idx = self.active_charts_order.index(new_div)
                self.active_charts_order[old_idx], self.active_charts_order[
                    new_idx] = self.active_charts_order[new_idx], self.active_charts_order[old_idx]
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

        mode_str = self.cb_layout_mode.currentText() if getattr(
            self, "cb_layout_mode", None) else "3 Columns"
        min_h = max(200, (viewport_h // 2 if mode_str ==
                    "1 Left, 2 Right (Stacked)" else viewport_h // 3) - 15)

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

        self.btn_prev_lagna.clicked.connect(lambda: self.jump_to_transit("Ascendant", -1))
        self.btn_next_lagna.clicked.connect(lambda: self.jump_to_transit("Ascendant", 1))
        
        self.btn_prev_rashi.clicked.connect(lambda: self.jump_to_transit(self.cb_transit_planet.currentText(), -1))
        self.btn_next_rashi.clicked.connect(lambda: self.jump_to_transit(self.cb_transit_planet.currentText(), 1))

        self.cb_transit_planet.currentIndexChanged.connect(self.recalculate)
        self.cb_transit_div.currentIndexChanged.connect(self.recalculate)

        self.cb_ayanamsa.currentTextChanged.connect(self.update_settings)
        self.cb_outline_mode.currentIndexChanged.connect(self.update_settings)

        for chk in [self.chk_symbols, self.chk_rahu, self.chk_arrows, self.chk_tint, self.chk_circular, self.show_tooltips]:
            chk.stateChanged.connect(self.update_settings)

        self.chk_aspects.stateChanged.connect(self.toggle_aspects)
        self.chk_details.stateChanged.connect(self.toggle_details)

        self.btn_save_chart.clicked.connect(self.save_chart_dialog)
        self.btn_load_chart.clicked.connect(self.load_chart_dialog)
        self.btn_export_png.clicked.connect(self.export_chart_png)
        self.btn_export_json.clicked.connect(self.export_analysis_json)
        self.btn_visual_guide.clicked.connect(self.show_visual_guide)

        if HAS_CUSTOM_VARGAS and hasattr(self, 'btn_add_custom_varga'):
            self.btn_add_custom_varga.clicked.connect(
                self.open_custom_varga_dialog)

        self.btn_stop_transit.clicked.connect(self.stop_transit_worker)

    def open_custom_varga_dialog(self):
        if not HAS_CUSTOM_VARGAS:
            return

        if custom_vargas.CustomVargaDialog(self).exec():
            QMessageBox.information(
                self, "Restart Required", "Custom Vargas saved successfully!\nPlease restart the application to enable/remove them.")


    def show_panchang(self):
        if not getattr(self, "current_base_chart", None) or "panchang" not in self.current_base_chart: 
            QMessageBox.warning(self, "Not Ready", "Please wait for chart calculation.")
            return
            
        p = self.current_base_chart["panchang"]
        
        try:
            target_date = datetime.datetime.now().date() 
            loc = LocationInfo(timezone=self.current_tz, latitude=self.current_lat, longitude=self.current_lon)
            s = sun(loc.observer, date=target_date, tzinfo=pytz.timezone(self.current_tz))
            
            real_sunrise = s['sunrise'].strftime('%I:%M %p')
            real_sunset = s['sunset'].strftime('%I:%M %p')
        except Exception as e:
            print(f"Sunrise/Sunset calculation failed: {e}")
            real_sunrise = p.get('sunrise_str', 'Unknown')
            real_sunset = p.get('sunset_str', 'Unknown')

        dlg = QDialog(self)
        dlg.setWindowTitle("Panchang")
        dlg.setMinimumWidth(350)
        
        lay = QVBoxLayout(dlg)
        lbl = QTextBrowser()
        
        lbl.setHtml(
            f"<h3>Panchang Details</h3>"
            f"<p><b>Nakshatra:</b> {p['nakshatra']} (Swami: {p['nakshatra_lord']}), Pada {p['nakshatra_pada']}</p>"
            f"<p><b>Tithi:</b> {p['paksha']} Paksha {p['tithi']}</p>"
            f"<p><b>Sunrise:</b> {real_sunrise}</p>"
            f"<p><b>Sunset:</b> {real_sunset}</p>"
        )
        lay.addWidget(lbl)
        
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
            r.set_tooltips_status(self.show_tooltips.isChecked())
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
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QInputDialog
        from PyQt6.QtGui import QPainter, QPixmap, QRegion
        from PyQt6.QtCore import Qt, QPoint

        # 1. Ask the user for Quality Level
        options = ["Standard Quality (1x)", "High Quality (2x) - Recommended", "Ultra Quality (4x) - Massive"]
        quality_str, ok = QInputDialog.getItem(self, "Export Quality", "Select export quality:", options, 1, False)
        if not ok: 
            return
            
        scale_factor = 1.0
        if "High" in quality_str: scale_factor = 2.0
        elif "Ultra" in quality_str: scale_factor = 4.0

        # 2. Ask for the File Path
        path, _ = QFileDialog.getSaveFileName(self, "Save Chart PNG", "", "PNG Files (*.png);;All Files (*)")
        if not path: 
            return

        try:
            # 3. Setup the Progress Bar
            charts_to_render = [div for div in getattr(self, 'active_charts_order', []) if div in self.renderers]
            total_steps = len(charts_to_render) + 1 # +1 for the final disk save
            
            progress = QProgressDialog("Initializing export...", "Cancel", 0, total_steps, self)
            progress.setWindowTitle("Exporting Image")
            progress.setWindowModality(Qt.WindowModality.WindowModal) # Blocks interaction with the app while exporting
            progress.setMinimumDuration(0)
            progress.setValue(0)
            
            # Force the layout to update so off-screen charts have the correct geometrical coordinates
            self.charts_container.layout().activate()
            target_size = self.charts_container.size()

            # 4. Create the massive high-resolution canvas
            high_res_pixmap = QPixmap(target_size * int(scale_factor))
            high_res_pixmap.fill(Qt.GlobalColor.white) 
            
            painter = QPainter(high_res_pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            
            # Scale the drawing instructions up
            painter.scale(scale_factor, scale_factor)

            # 5. Render charts one by one (This completely bypasses the scroll area bug!)
            for i, div in enumerate(charts_to_render):
                if progress.wasCanceled():
                    painter.end()
                    return
                
                chart_name = self.div_titles.get(div, div)
                progress.setLabelText(f"Drawing {chart_name}...")
                
                renderer = self.renderers[div]
                geo = renderer.geometry()
                
                painter.save()
                # Move the painter's brush to where this specific chart lives in the grid layout
                painter.translate(geo.topLeft())
                
                # Command the widget to paint itself directly onto our canvas
                renderer.render(painter, QPoint(0, 0), QRegion(), QWidget.RenderFlag.DrawChildren)
                painter.restore()
                
                # Tick the progress bar forward
                progress.setValue(i + 1)
                
                # Keep the UI from freezing so the progress bar actually animates
                QApplication.processEvents()

            # 6. Save the final image to disk
            progress.setLabelText("Compressing and saving PNG... (This might take a moment)")
            QApplication.processEvents()
            
            painter.end()
            high_res_pixmap.save(path, "PNG")
            
            # Complete the progress bar
            progress.setValue(total_steps)
            QMessageBox.information(self, "Success", f"Chart exported successfully!\nFinal Resolution: {high_res_pixmap.width()} x {high_res_pixmap.height()}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export high-quality PNG:\n{str(e)}")



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
                for p in div_data["planets"]:
                    if not p.get("lord_of"): continue
                    
                    for ruled_house in p["lord_of"]:
                        if ruled_house in AUSPICIOUS_HOUSES and p["house"] in AUSPICIOUS_HOUSES:
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
            
            tgt_sign = "Any Rashi"
            actual_body_name = "Ascendant" if body_name == "Ascendant" else body_name
            
            if actual_body_name in self.frozen_planets and self.frozen_planets[actual_body_name]["div"] == transit_div:
                tgt_sign = ZODIAC_NAMES[self.frozen_planets[actual_body_name]["sign_idx"]]

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
            columns_data = [b_name, ZODIAC_NAMES[s_idx], deg_str, house, retro]
            
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