# dynamic_settings_modules/a_transit_mod.py

import datetime, math, copy

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,QPushButton, QLabel, QCheckBox, QComboBox, QGroupBox, QDateTimeEdit)
from PyQt6.QtCore import Qt, QDateTime, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QBrush

import astro_engine, chart_renderer

PLUGIN_GROUP = "BASIC TOOLS"
PLUGIN_INDEX = 1


class TransitPluginUI(QWidget):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app = app_ref
        
        # Attach directly to the ChartRenderer class to survive hot-reloads
        # and avoid module-scope closure bugs caused by __pycache__ creation.
        chart_renderer.ChartRenderer._transit_plugin_instance = self

        # Plugin State
        self.is_enabled = False
        self.transit_dt = datetime.datetime.now()
        self.transit_data = None
        self.selected_planets = {"Jupiter", "Saturn", "Rahu", "Ketu"} # Default slow movers
        
        self.init_ui()
        self.patch_chart_renderer()
        
        # Removed the QTimer and initial calculation. 
        # We will use "Lazy Evaluation" instead to calculate only when the app is fully ready.

    def init_ui(self):
        # The main layout for the widget itself
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(2)
        
        # 1. Create the requested GroupBox and its Layout
        group = QGroupBox("Gochar / Transit")
        v_layout = QVBoxLayout()
        v_layout.setContentsMargins(8, 8, 8, 8)
        
        status_label = QLabel("Displays transits of planets (Rashi/Sign they currently are in)")
        status_label.setWordWrap(True)
        status_label.setStyleSheet("color: #555; font-size: 11px;")
        v_layout.addWidget(status_label)

        # 2. Main Toggle
        self.chk_enable = QCheckBox("Enable Gochar (Transit) Overlay")
        self.chk_enable.setStyleSheet("font-weight: bold; color: #005FFF; font-size: 15px;")
        self.chk_enable.stateChanged.connect(self.on_enable_toggle)
        v_layout.addWidget(self.chk_enable)

        # 3. Controls Container (hidden by default)
        self.controls_widget = QWidget()
        ctrl_layout = QVBoxLayout(self.controls_widget)
        ctrl_layout.setContentsMargins(0, 0, 0, 0)
        ctrl_layout.setSpacing(2)
        
        # --- Time Navigation ---
        time_group = QGroupBox("Transit Time")
        time_layout = QVBoxLayout()
        time_layout.setContentsMargins(2, 6, 2, 2)
        time_layout.setSpacing(2)
        
        # Datetime display
        dt_layout = QHBoxLayout()
        dt_layout.setSpacing(2)
        self.dt_edit = QDateTimeEdit(self.transit_dt)
        self.dt_edit.setDisplayFormat("dd MMM yy, HH:mm")
        self.dt_edit.dateTimeChanged.connect(self.on_datetime_edited)
        
        btn_now = QPushButton("Now")
        btn_now.clicked.connect(self.set_time_to_now)
        
        dt_layout.addWidget(QLabel("Date:"))
        dt_layout.addWidget(self.dt_edit)
        dt_layout.addWidget(btn_now)
        time_layout.addLayout(dt_layout)
        
        # Step Controls
        step_layout = QHBoxLayout()
        step_layout.setSpacing(2)
        steps = [("-1M", -30), ("-1W", -7), ("+1W", 7), ("+1M", 30)]
        for label, days in steps:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, d=days: self.step_time(d))
            step_layout.addWidget(btn)
        time_layout.addLayout(step_layout)
        
        # Next/Prev Rashi Entry
        rashi_layout = QHBoxLayout()
        rashi_layout.setSpacing(2)
        rashi_layout.addWidget(QLabel("Jump:"))
        self.cb_jump_planet = QComboBox()
        self.cb_jump_planet.addItems(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"])
        
        btn_prev_sign = QPushButton("<")
        btn_next_sign = QPushButton(">")
        btn_prev_sign.clicked.connect(lambda: self.jump_rashi(-1))
        btn_next_sign.clicked.connect(lambda: self.jump_rashi(1))
        
        rashi_layout.addWidget(self.cb_jump_planet)
        rashi_layout.addWidget(btn_prev_sign)
        rashi_layout.addWidget(btn_next_sign)
        time_layout.addLayout(rashi_layout)
        
        time_group.setLayout(time_layout)
        ctrl_layout.addWidget(time_group)
        
        # --- Planet Selection ---
        planet_group = QGroupBox("Active Planets")
        planet_layout = QVBoxLayout()
        planet_layout.setContentsMargins(2, 6, 2, 2)
        planet_layout.setSpacing(2)
        
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(2)
        planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        self.planet_checkboxes = {}
        
        for i, p in enumerate(planets):
            cb = QCheckBox(p)
            cb.setChecked(p in self.selected_planets)
            cb.stateChanged.connect(self.update_selected_planets)
            self.planet_checkboxes[p] = cb
            grid.addWidget(cb, i // 3, i % 3)
            
        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(2)
        btn_all = QPushButton("All")
        btn_slow = QPushButton("Slow")
        btn_none = QPushButton("None")
        
        btn_all.clicked.connect(lambda: self.quick_select(["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]))
        btn_slow.clicked.connect(lambda: self.quick_select(["Jupiter", "Saturn", "Rahu", "Ketu"]))
        btn_none.clicked.connect(lambda: self.quick_select([]))
        
        quick_layout.addWidget(btn_all)
        quick_layout.addWidget(btn_slow)
        quick_layout.addWidget(btn_none)
        
        planet_layout.addLayout(grid)
        planet_layout.addLayout(quick_layout)
        planet_group.setLayout(planet_layout)
        ctrl_layout.addWidget(planet_group)
        
        # Add the nested controls to the GroupBox layout
        self.controls_widget.setVisible(False)
        v_layout.addWidget(self.controls_widget)

        # 4. Finalize GroupBox and add to Main Layout
        group.setLayout(v_layout)
        main_layout.addWidget(group)

    def on_enable_toggle(self, state):
        self.is_enabled = (state == Qt.CheckState.Checked.value)
        self.controls_widget.setVisible(self.is_enabled)
        
        # Lazy initialization: Calculate exactly when enabled if we don't have data yet
        if self.is_enabled and not self.transit_data:
            self.calculate_transit()
            
        self.trigger_redraw()

    def set_time_to_now(self):
        self.transit_dt = datetime.datetime.now()
        self.update_dt_edit()
        self.calculate_transit()

    def step_time(self, days):
        self.transit_dt += datetime.timedelta(days=days)
        self.update_dt_edit()
        self.calculate_transit()

    def on_datetime_edited(self, qdt):
        self.transit_dt = qdt.toPyDateTime()
        self.calculate_transit()

    def update_dt_edit(self):
        self.dt_edit.blockSignals(True)
        self.dt_edit.setDateTime(QDateTime(self.transit_dt))
        self.dt_edit.blockSignals(False)

    def quick_select(self, planet_list):
        for p, cb in self.planet_checkboxes.items():
            cb.blockSignals(True)
            cb.setChecked(p in planet_list)
            cb.blockSignals(False)
        self.update_selected_planets()

    def update_selected_planets(self):
        self.selected_planets = {p for p, cb in self.planet_checkboxes.items() if cb.isChecked()}
        self.trigger_redraw()

    def jump_rashi(self, direction):
        planet = self.cb_jump_planet.currentText()
        jd_utc = self.get_transit_jd()
        
        engine = self.app.ephemeris
        prev_jd, next_jd = engine.find_adjacent_planet_transits(jd_utc, planet, "D1")
        
        target_jd = next_jd if direction == 1 else prev_jd
        if target_jd:
            # Shift slightly into the sign to ensure it registers correctly
            offset = 0.05 if direction == 1 else -0.05
            self.transit_dt = astro_engine.utc_jd_to_dt_dict(target_jd + offset, self.app.current_tz)
            
            # Convert dictionary back to datetime object
            self.transit_dt = datetime.datetime(
                self.transit_dt['year'], self.transit_dt['month'], self.transit_dt['day'],
                self.transit_dt['hour'], self.transit_dt['minute'], int(self.transit_dt['second'])
            )
            self.update_dt_edit()
            self.calculate_transit()

    def get_transit_jd(self):
        dt_dict = {
            'year': self.transit_dt.year, 'month': self.transit_dt.month, 'day': self.transit_dt.day,
            'hour': self.transit_dt.hour, 'minute': self.transit_dt.minute, 'second': self.transit_dt.second
        }
        return astro_engine.dt_dict_to_utc_jd(dt_dict, getattr(self.app, 'current_tz', 0.0))

    def calculate_transit(self):
        dt_dict = {
            'year': self.transit_dt.year, 'month': self.transit_dt.month, 'day': self.transit_dt.day,
            'hour': self.transit_dt.hour, 'minute': self.transit_dt.minute, 'second': self.transit_dt.second
        }
        
        # Safely fetch location variables. If main app hasn't fully loaded them yet, abort cleanly.
        lat = getattr(self.app, 'current_lat', None)
        lon = getattr(self.app, 'current_lon', None)
        tz = getattr(self.app, 'current_tz', None)
        
        if lat is None or lon is None or tz is None:
            return # App is not fully initialized yet; defer calculation.
            
        try:
            # Calculate full transit chart
            self.transit_data = self.app.ephemeris.calculate_chart(
                dt_dict, lat, lon, tz
            )
        except Exception as e:
            print(f"Gochar calculation deferred: {e}")
            
        self.trigger_redraw()

    def trigger_redraw(self):
        if hasattr(self.app, 'charts_container'):
            self.app.charts_container.update()

    def patch_chart_renderer(self):
        # Monkey patch the main ChartRenderer to draw overlays after standard rendering
        if not hasattr(chart_renderer.ChartRenderer, "_original_paintEvent_gochar"):
            chart_renderer.ChartRenderer._original_paintEvent_gochar = chart_renderer.ChartRenderer.paintEvent

            def hooked_paintEvent(renderer_self, event):
                # 1. Run standard natal chart paint event
                renderer_self._original_paintEvent_gochar(event)
                
                # 2. Draw Gochar Overlay using the class-level reference
                plugin = getattr(chart_renderer.ChartRenderer, "_transit_plugin_instance", None)
                if plugin and plugin.is_enabled:
                    plugin.draw_transits(renderer_self)

            chart_renderer.ChartRenderer.paintEvent = hooked_paintEvent

    def draw_transits(self, renderer):
        # If enabled but missing data (e.g., app just finished loading), lazy load it now
        if not self.transit_data and self.is_enabled:
            self.calculate_transit()
            
        if not self.transit_data or not getattr(renderer, 'chart_data', None):
            return
            
        layout = getattr(renderer, "current_layout", None)
        if not layout or "houses" not in layout:
            return
            
        # Determine current divisional chart type
        div_type = "D1"
        for k, v in self.app.div_titles.items():
            if v == renderer.title:
                div_type = k
                break
                
        # IMPORTANT: ONLY display transits on the D1 chart to prevent clutter/confusion
        if div_type != "D1":
            return
                
        # Standard Chart Metrics
        size = min(renderer.width(), renderer.height()) - 50
        cx, cy = renderer.width() / 2, renderer.height() / 2 + 10
        x = cx - size / 2
        y = cy - size / 2
        
        # Get Natal Ascendant mapping
        base_asc_sign = renderer.chart_data["ascendant"]["sign_index"]
        if getattr(renderer, 'rotated_asc_sign_idx', None) is not None:
            base_asc_sign = renderer.rotated_asc_sign_idx
            
        # Group transit planets by visual house in the current chart
        transit_by_vh = {i: [] for i in range(1, 13)}
        
        for p in self.transit_data["planets"]:
            if p["name"] not in self.selected_planets:
                continue
                
            # Convert transit absolute longitude to current D-chart sign
            sign_idx, _ = self.app.ephemeris.get_div_sign_and_lon(p["lon"], div_type)
            visual_h = ((sign_idx - base_asc_sign) % 12) + 1
            transit_by_vh[visual_h].append(p)

        # Initialize Painter for Overlay
        painter = QPainter(renderer)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Adjust font scaling based on chart size
        font_scale = max(0.6, min(1.2, size / 400.0))
        font_size = int(10 * font_scale)
        icon_font = QFont("Arial", font_size, QFont.Weight.Bold)
        
        colors = chart_renderer.BRIGHT_COLORS
        
        # Explicit outer-edge coordinate placement for Diamond Charts.
        # Format: house: (rx, ry, 'H'/'V' orientation, wrap_dx, wrap_dy)
        # rx, ry define relative positions along the outer diamond boundaries (0.0 to 1.0)
        # wrap_dx, wrap_dy push rows inwards to neatly stack planets during stelliums
        diamond_coords = {
            1:  (0.50, 0.08, 'H', 0, 1),
            2:  (0.12, 0.06, 'H', 0, 1),   # Outer top-left corner (upper)
            3:  (0.06, 0.12, 'V', 1, 0),   # Outer top-left corner (lower)
            4:  (0.08, 0.50, 'V', 1, 0),
            5:  (0.06, 0.88, 'V', 1, 0),   # Outer bottom-left corner (upper)
            6:  (0.12, 0.94, 'H', 0, -1),  # Outer bottom-left corner (lower)
            7:  (0.50, 0.92, 'H', 0, -1),
            8:  (0.88, 0.94, 'H', 0, -1),  # Outer bottom-right corner (lower)
            9:  (0.94, 0.88, 'V', -1, 0),  # Outer bottom-right corner (upper)
            10: (0.92, 0.50, 'V', -1, 0),
            11: (0.94, 0.12, 'V', -1, 0),  # Outer top-right corner (lower)
            12: (0.88, 0.06, 'H', 0, 1)    # Outer top-right corner (upper)
        }

        for vh, planets in transit_by_vh.items():
            if not planets:
                continue

            # Determine Anchor Point and Layout Strategy
            if getattr(renderer, "use_circular", False):
                h_info = layout["houses"].get(vh)
                if not h_info: continue
                hx, hy = h_info["x"], h_info["y"]
                dx, dy = hx - cx, hy - cy
                dist = max(1, math.hypot(dx, dy))
                push_factor = size * 0.42 # Push beyond outer ring
                base_px = cx + (dx / dist) * push_factor
                base_py = cy + (dy / dist) * push_factor
                orientation, wrap_dx, wrap_dy = 'H', 0, 1
            else:
                rx, ry, orientation, wrap_dx, wrap_dy = diamond_coords.get(vh, (0.5, 0.5, 'H', 0, 1))
                base_px = x + (rx * size)
                base_py = y + (ry * size)
            
            # Draw clustered planets perfectly centered at the edge anchor
            badge_size = 20 * font_scale
            spacing = badge_size + 2
            items_per_line = 3 # Triggers wrapping if more than 3 planets share a sign
            
            for i, p in enumerate(planets):
                line_idx = i % items_per_line
                wrap_idx = i // items_per_line
                
                items_in_current_line = min(items_per_line, len(planets) - wrap_idx * items_per_line)
                total_length = (items_in_current_line - 1) * spacing
                
                # Apply precise offset based on layout orientation
                if orientation == 'H':
                    start_x = base_px - (total_length / 2)
                    px = start_x + (line_idx * spacing)
                    py = base_py + (wrap_idx * spacing * wrap_dy)
                else:
                    start_y = base_py - (total_length / 2)
                    px = base_px + (wrap_idx * spacing * wrap_dx)
                    py = start_y + (line_idx * spacing)
                
                color = colors.get(p["name"], QColor("#000000"))
                bg_color = QColor(color)
                bg_color.setAlpha(40) # Soft glow background to separate from natal chart lines
                
                # 1. Draw glowing secondary layer (Dashed Orbit Effect)
                pen = QPen(color, max(1.5, size * 0.003))
                pen.setStyle(Qt.PenStyle.DashLine)
                painter.setPen(pen)
                painter.setBrush(QBrush(bg_color))
                
                painter.drawEllipse(int(px - badge_size/2), int(py - badge_size/2), 
                                    int(badge_size), int(badge_size))
                
                # 2. Draw Planet Text/Symbol
                painter.setPen(color.darker(120))
                painter.setFont(icon_font)
                
                sym = p["sym"]
                if getattr(renderer, "use_symbols", False):
                    sym = chart_renderer.UNICODE_SYMS.get(p["name"], p["sym"])
                    
                text_rect = painter.fontMetrics().boundingRect(sym)
                painter.drawText(int(px - text_rect.width()/2), 
                                 int(py + text_rect.height()/3), sym)
                
                # 3. Draw mini-status indicator (Retrograde Indicator Offset)
                if p.get("retro") and p["name"] not in ["Rahu", "Ketu"]:
                    painter.setPen(QColor("#D35400"))
                    retro_font = QFont("Arial", max(6, int(font_size * 0.7)), QFont.Weight.Bold)
                    painter.setFont(retro_font)
                    painter.drawText(int(px + badge_size/3), int(py - badge_size/3), "R")

        painter.end()


def setup_ui(app, layout):
    """
    Standard entry point for AstroBasics dynamic modules.
    Instantiates the plugin and attaches it to the sidebar layout.
    """
    plugin = TransitPluginUI(app)
    layout.addWidget(plugin)