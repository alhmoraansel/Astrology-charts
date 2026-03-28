#dynamic_settings_modules/research_plugin.py

import sys, os, json, importlib, copy
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,QSplitter, QScrollArea, QGridLayout, QLineEdit, QFileDialog,QMainWindow, QMenu, QMessageBox, QGroupBox, QComboBox)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QAction

PLUGIN_GROUP = "RESEARCH"
PLUGIN_INDEX = 30

# =========================================================================
# GLOBAL SETTINGS & EXPLICIT PLUGIN REGISTRY
# =========================================================================

# Adjust this value to change the minimum vertical size of the charts in Research Mode
MIN_CHART_HEIGHT = 300

# Only the plugins explicitly stated here will load in the Research Mode dropdowns.
# Add your modules below to make them available.
try:
    from dynamic_settings_modules import shadbal_mod, vishmottari_mod
    AVAILABLE_RESEARCH_PLUGINS = [shadbal_mod, vishmottari_mod]
except ImportError:
    AVAILABLE_RESEARCH_PLUGINS = []

# =========================================================================

# Attempt to import main application space to reuse the ChartRenderer and globals
try:
    import main
    ChartRenderer = main.ChartRenderer
    SmoothScroller = main.SmoothScroller
except ImportError:
    ChartRenderer = None
    SmoothScroller = None


class MockTimeCtrl(QObject):
    """Mock TimeController to satisfy plugins requesting app.time_ctrl.current_time"""
    time_changed = pyqtSignal(dict)

    def __init__(self, dt_dict):
        super().__init__()
        self.current_time = dt_dict or {}
        self.is_playing = False


class MockCalcWorker(QObject):
    """Mock worker to simulate calculation finishes for plugins that bind to app.calc_worker"""
    calc_finished = pyqtSignal(dict, dict, bool, str, str)

    def __init__(self):
        super().__init__()


class ProxyApp(QWidget):
    """
    A proxy object that impersonates the main AstroApp. 
    It intercepts data requests so plugins operate on the specific panel's chart data, 
    but passes unhandled requests (like UI configs or methods) back to the main app.
    Inherits QWidget so plugins can use it safely as a Parent for QDialogs/QMessageBoxes.
    """

    def __init__(self, main_app, panel):
        super().__init__(panel)
        self.hide()  # Stops the proxy widget from eating mouse clicks!
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._main_app = main_app
        self._panel = panel
        self.calc_worker = MockCalcWorker()

    @property
    def current_base_chart(self):
        return self._panel.chart_data

    @property
    def current_lat(self):
        return self._panel.chart_params.get('lat', self._main_app.current_lat) if self._panel.chart_params else self._main_app.current_lat

    @property
    def current_lon(self):
        return self._panel.chart_params.get('lon', self._main_app.current_lon) if self._panel.chart_params else self._main_app.current_lon

    @property
    def current_tz(self):
        return self._panel.chart_params.get('tz', self._main_app.current_tz) if self._panel.chart_params else self._main_app.current_tz

    @property
    def time_ctrl(self):
        dt = self._panel.chart_params.get(
            'datetime_dict') if self._panel.chart_params else self._main_app.time_ctrl.current_time
        return MockTimeCtrl(dt)

    def recalculate(self):
        # Research mode charts are static snapshots; block main app recalculation loops.
        pass

    def __getattr__(self, item):
        return getattr(self._main_app, item)


class ResearchPanel(QWidget):
    """A single chart panel inside the Research Mode window."""

    def __init__(self, app_instance, title="Chart Panel", parent_window=None):
        super().__init__()
        self.app = app_instance
        self.parent_window = parent_window
        self.chart_data = None
        self.chart_params = None
        self.renderers = {}
        self.active_charts_order = ["D1"]

        # --- UI Setup ---
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        self.layout.setSpacing(4)

        # Top Control Bar (Combined and Compact)
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(4)

        btn_style = "padding: 3px 8px; font-size: 11px; border: 1px solid #ccc; border-radius: 3px;"

        self.btn_load_main = QPushButton("Load Main")
        self.btn_load_main.setStyleSheet(btn_style)
        self.btn_load_file = QPushButton("Load File")
        self.btn_load_file.setStyleSheet(btn_style)

        # Vargas Selector using a Menu
        self.btn_vargas = QPushButton("Vargas ▾")
        self.btn_vargas.setStyleSheet(btn_style)
        self.vargas_menu = QMenu(self)
        self.varga_actions = {}

        for d_id in self.app.div_titles.keys():
            action = self.vargas_menu.addAction(d_id)
            action.setCheckable(True)
            if d_id == "D1":
                action.setChecked(True)
            action.triggered.connect(
                lambda checked, did=d_id: self.on_varga_toggled(checked, did))
            self.varga_actions[d_id] = action

        self.btn_vargas.setMenu(self.vargas_menu)

        # Drop-down for Explicit Plugins
        self.plugin_combo = QComboBox()
        self.plugin_combo.setStyleSheet(
            btn_style + " background-color: #f39c12; color: white; font-weight: bold; border: none;")
        self.plugin_combo.addItem("⚙ Extensions...")
        self.plugin_combo.setEnabled(False)  # Disabled until a chart is loaded

        for mod in AVAILABLE_RESEARCH_PLUGINS:
            # Try to grab a nice display name, fallback to module name
            name = getattr(mod, "PLUGIN_NAME", mod.__name__.split('.')[-1])
            self.plugin_combo.addItem(name, mod)

        self.plugin_combo.currentIndexChanged.connect(self.on_plugin_selected)

        # Compact Tags directly in the same row
        lbl_tags = QLabel("Tags:")
        lbl_tags.setStyleSheet("font-size: 11px; margin-left: 10px;")
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("e.g. Twin 1...")
        self.tags_input.setStyleSheet("padding: 2px; font-size: 11px;")
        self.tags_input.setMaximumWidth(150)
        self.tags_input.textChanged.connect(self._on_modified)

        top_bar.addWidget(self.btn_load_main)
        top_bar.addWidget(self.btn_load_file)
        top_bar.addWidget(self.btn_vargas)
        top_bar.addWidget(self.plugin_combo)
        top_bar.addWidget(lbl_tags)
        top_bar.addWidget(self.tags_input)
        top_bar.addStretch()

        self.layout.addLayout(top_bar)

        # Plugin Target Container (Hidden by default, expands when extension is picked)
        self.plugin_container = QGroupBox("Extension Settings")
        self.plugin_container.setStyleSheet(
            "QGroupBox { background-color: #F8F9F9; border: 1px solid #D1D5DB; border-radius: 4px; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 7px; padding: 0 3px 0 3px; font-weight: bold; color: #555; }")
        self.plugin_container_layout = QVBoxLayout(self.plugin_container)
        self.plugin_container_layout.setContentsMargins(4, 16, 4, 4)
        self.plugin_container.setVisible(False)
        self.layout.addWidget(self.plugin_container)

        # Charts Area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(
            "QScrollArea { border: 1px solid #D1D5DB; border-radius: 4px; background-color: #FAFAFA; }")

        if SmoothScroller:
            self.smooth_scroller = SmoothScroller(self.scroll_area)

        self.charts_container = QWidget()
        self.grid_layout = QGridLayout(self.charts_container)
        self.scroll_area.setWidget(self.charts_container)

        self.layout.addWidget(self.scroll_area)

        # --- Connections & Initialization ---
        self.btn_load_main.clicked.connect(self.load_main_chart)
        self.btn_load_file.clicked.connect(self.load_file_chart)
        self.proxy_app = ProxyApp(self.app, self)

    def _on_modified(self, *args):
        if self.parent_window:
            self.parent_window.mark_modified()

    def on_varga_toggled(self, checked, d_id):
        if checked and d_id not in self.active_charts_order:
            self.active_charts_order.append(d_id)
        elif not checked and d_id in self.active_charts_order:
            self.active_charts_order.remove(d_id)
        self._on_modified()
        self.update_renderers()

    def show_chart_context_menu(self, pos, old_div):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #FAFAFA; border: 1px solid #D1D5DB; border-radius: 4px; } "
                           "QMenu::item { padding: 6px 24px 6px 24px; color: #1A1A1A; } "
                           "QMenu::item:selected { background-color: #0078D4; color: white; }")

        title_action = menu.addAction(f"--- Swap {old_div} With ---")
        title_action.setEnabled(False)
        menu.addSeparator()

        for d_id, d_name in self.app.div_titles.items():
            if d_id != old_div:
                action = menu.addAction(f"{d_name}")
                action.triggered.connect(
                    lambda checked, new_d=d_id: self.swap_charts(old_div, new_d))

        if old_div in self.renderers:
            renderer = self.renderers[old_div]
            menu.exec(renderer.mapToGlobal(pos))

    def swap_charts(self, old_div, new_div):
        if old_div in self.active_charts_order:
            idx = self.active_charts_order.index(old_div)
            if new_div in self.active_charts_order:
                # Both exist, just swap their visual order
                idx2 = self.active_charts_order.index(new_div)
                self.active_charts_order[idx], self.active_charts_order[
                    idx2] = self.active_charts_order[idx2], self.active_charts_order[idx]
            else:
                self.active_charts_order[idx] = new_div

            # Silently sync the dropdown checks so UI reflects the true state
            for d_id, action in self.varga_actions.items():
                action.blockSignals(True)
                action.setChecked(d_id in self.active_charts_order)
                action.blockSignals(False)

            self._on_modified()
            self.update_renderers()

    def on_plugin_selected(self, index):
        """Clears the current extension and loads the selected one."""
        self.clear_layout(self.plugin_container_layout)

        mod = self.plugin_combo.itemData(index)
        if mod and self.chart_data:
            self.plugin_container.setVisible(True)
            self.plugin_container.setTitle(self.plugin_combo.itemText(index))
            try:
                mod.setup_ui(self.proxy_app, self.plugin_container_layout)
            except Exception as e:
                lbl = QLabel(f"Error loading extension: {str(e)}")
                lbl.setStyleSheet("color: #c0392b; font-weight: bold;")
                self.plugin_container_layout.addWidget(lbl)
        else:
            self.plugin_container.setVisible(False)

        self._on_modified()

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clear_layout(item.layout())

    def refresh_active_plugin(self):
        """Re-triggers the UI generation for the active plugin with new chart data."""
        if self.plugin_combo.currentIndex() > 0:
            self.on_plugin_selected(self.plugin_combo.currentIndex())

        # Emit mock signal to trigger live-updates for compatible plugins (like Shadbala)
        if self.chart_data:
            self.proxy_app.calc_worker.calc_finished.emit(
                self.chart_data, {}, False, "", "")

    def load_main_chart(self):
        try:
            if not getattr(self.app, 'current_base_chart', None):
                QMessageBox.warning(
                    self, "Warning", "No chart currently loaded in the main application.")
                return

            try:
                # Deepcopy guarantees the Research chart remains completely frozen.
                self.chart_data = copy.deepcopy(self.app.current_base_chart)
            except Exception as e:
                import json
                # Fallback hack if deepcopy hits a weird uncopyable object
                self.chart_data = json.loads(
                    json.dumps(self.app.current_base_chart))

            self.chart_params = {
                "lat": getattr(self.app, 'current_lat', 28.6139),
                "lon": getattr(self.app, 'current_lon', 77.2090),
                "tz": getattr(self.app, 'current_tz', 'UTC'),
                "datetime_dict": copy.deepcopy(getattr(self.app.time_ctrl, 'current_time', {}))
            }

            # Mirror the exact vargas currently active in the main app
            if hasattr(self.app, 'active_charts_order'):
                self.active_charts_order = copy.deepcopy(
                    self.app.active_charts_order)
                for d_id, action in self.varga_actions.items():
                    action.blockSignals(True)
                    action.setChecked(d_id in self.active_charts_order)
                    action.blockSignals(False)

            self.tags_input.blockSignals(True)
            self.tags_input.setText("Imported from Main App")
            self.tags_input.blockSignals(False)

            self._on_modified()
            self.update_renderers()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self, "Error", f"Failed to load main chart:\n{str(e)}")

    def load_file_chart(self):
        try:
            import save_prefs
            import datetime
        except ImportError:
            QMessageBox.critical(
                self, "Error", "Dependencies missing (save_prefs/datetime).")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Load Chart", "saves", "JSON Files (*.json)")
        if not path:
            return

        try:
            file_data = save_prefs.load_chart_from_file(path)
            if file_data:
                dt_dict = file_data.get("datetime_dict")
                lat = 28.6139
                lon = 77.2090
                tz = "UTC"

                # Format 1: Detailed Analysis Export (Uses 'metadata' block)
                if not dt_dict and "metadata" in file_data:
                    dt_dict = file_data["metadata"].get("datetime")
                    lat = float(file_data["metadata"].get("latitude", lat))
                    lon = float(file_data["metadata"].get("longitude", lon))

                    # 'tz' is omitted in detailed exports to save space, reconstruct it:
                    try:
                        from timezonefinder import TimezoneFinder
                        tf = TimezoneFinder()
                        tz = tf.timezone_at(lng=lon, lat=lat) or "UTC"
                    except Exception as tz_err:
                        tz = "UTC"

                # Format 2: Standard Quick Save
                else:
                    lat = float(file_data.get('lat', lat))
                    lon = float(file_data.get('lon', lon))
                    tz = file_data.get('tz', 'UTC')

                if dt_dict:
                    # Sanitize dates stringified during deep JSON nesting exports
                    if isinstance(dt_dict, str):
                        try:
                            parsed = datetime.datetime.fromisoformat(dt_dict)
                            dt_dict = {
                                'year': parsed.year, 'month': parsed.month, 'day': parsed.day,
                                'hour': parsed.hour, 'minute': parsed.minute, 'second': parsed.second
                            }
                        except Exception as parse_err:
                            pass

                    self.chart_params = {
                        "lat": lat, "lon": lon, "tz": tz, "datetime_dict": dt_dict}
                    self.chart_data = self.app.ephemeris.calculate_chart(
                        dt_dict, lat, lon, tz)

                    self.tags_input.blockSignals(True)
                    self.tags_input.setText(os.path.basename(path))
                    self.tags_input.blockSignals(False)

                    self._on_modified()
                    self.update_renderers()
                else:
                    QMessageBox.warning(
                        self, "Error", "Invalid chart file format. Missing datetime.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self, "Error", f"Failed to load chart:\n{str(e)}")

    def update_renderers(self):
        if not getattr(self, 'chart_data', None) or ChartRenderer is None:
            return

        self.plugin_combo.setEnabled(True)

# Clear existing layout
        for i in reversed(range(self.grid_layout.count())):
            item = self.grid_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                self.grid_layout.removeWidget(widget)
                widget.hide()

        active_divs = self.active_charts_order.copy()
        if not active_divs:
            # Fallback if somehow emptied
            active_divs = ["D1"]
            self.active_charts_order = ["D1"]
            if "D1" in self.varga_actions:
                self.varga_actions["D1"].blockSignals(True)
                self.varga_actions["D1"].setChecked(True)
                self.varga_actions["D1"].blockSignals(False)

        mode_str = self.parent_window.current_layout_mode if self.parent_window else "1 Left, 2 Right (Stacked)"
        viewport_h = max(100, self.scroll_area.viewport().height())

        # Incorporate global MIN_CHART_HEIGHT variable
        min_h = max(MIN_CHART_HEIGHT, (viewport_h // 2 if mode_str ==
                    "1 Left, 2 Right (Stacked)" else viewport_h // 3) - 15)

        for i, div in enumerate(active_divs):
            if div not in self.renderers:
                r = ChartRenderer()
                r.title = self.app.div_titles.get(div, div)

                # Context Menu Setup
                r.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                r.customContextMenuRequested.connect(
                    lambda pos, d=div: self.show_chart_context_menu(pos, d))

                self.renderers[div] = r
            else:
                r = self.renderers[div]

            # Sync visual preferences safely
            r.outline_mode = self.app.cb_outline_mode.currentText() if hasattr(self.app, 'cb_outline_mode') else "Vitality (Lords)"
            r.use_symbols = self.app.chk_symbols.isChecked() if hasattr(self.app, 'chk_symbols') else False
            r.show_rahu_ketu = self.app.chk_rahu.isChecked() if hasattr(self.app,'chk_rahu') else True

            if self.parent_window:
                r.show_aspects = self.parent_window.show_aspects
                r.visible_aspect_planets = set(self.parent_window.visible_aspect_planets)
            else:
                r.show_aspects = self.app.chk_aspects.isChecked() if hasattr(self.app, 'chk_aspects') else False
                r.visible_aspect_planets = {p for p, cb in self.app.aspect_cb.items() if cb.isChecked()} if hasattr(self.app, 'aspect_cb') else {"Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"}

            r.show_arrows = self.app.chk_arrows.isChecked() if hasattr(self.app, 'chk_arrows') else True
            r.use_tint = self.app.chk_tint.isChecked() if hasattr(self.app, 'chk_tint') else True
            r.use_circular = self.app.chk_circular.isChecked() if hasattr(self.app, 'chk_circular') else False

            # Sync double-click rotation state directly from the main app
            if hasattr(self.app, 'renderers') and div in self.app.renderers:
                main_r = self.app.renderers[div]
                if hasattr(main_r, 'rotated_asc_sign_idx'):
                    r.rotated_asc_sign_idx = main_r.rotated_asc_sign_idx

            # --- MODULAR TOOLTIP SYNC ---
            # Utilize the main.py ChartRenderer tooltip setting natively
            show_tt = self.parent_window.show_tooltips if self.parent_window else True
            if hasattr(r, 'set_tooltips_status'):
                r.set_tooltips_status(show_tt)
            else:
                r.SHOW_TOOLTIPS = show_tt

            r.setMinimumHeight(min_h)

            if mode_str == "1 Left, 2 Right (Stacked)":
                if i == 0:
                    self.grid_layout.addWidget(r, 0, 0, 2, 1)
                elif i == 1:
                    self.grid_layout.addWidget(r, 0, 1, 1, 1)
                elif i == 2:
                    self.grid_layout.addWidget(r, 1, 1, 1, 1)
                else:
                    self.grid_layout.addWidget(
                        r, 2 + (i - 3) // 2, (i - 3) % 2, 1, 1)
            elif mode_str == "2 Columns":
                self.grid_layout.addWidget(r, i // 2, i % 2)
            else:
                self.grid_layout.addWidget(r, i // 3, i % 3)

            div_data = self.app.ephemeris.compute_divisional_chart(
                self.chart_data, div) if div != "D1" else self.chart_data
            d1_data = self.chart_data if div != "D1" else None
            r.update_chart(div_data, d1_data)
            r.show() 

        self.refresh_active_plugin()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not hasattr(self, 'scroll_area'):
            return
        viewport_h = max(100, self.scroll_area.viewport().height())
        mode_str = self.parent_window.current_layout_mode if self.parent_window else "1 Left, 2 Right (Stacked)"
        min_h = max(MIN_CHART_HEIGHT, (viewport_h // 2 if mode_str ==
                    "1 Left, 2 Right (Stacked)" else viewport_h // 3) - 15)
        for r in self.renderers.values():
            r.setMinimumHeight(min_h)

    def get_save_data(self):
        return {
            "chart_params": self.chart_params,
            "tags": self.tags_input.text(),
            "active_charts_order": self.active_charts_order
        }

    def load_from_data(self, data):
        if not data:
            return
        self.chart_params = data.get("chart_params")
        self.tags_input.setText(data.get("tags", ""))

        self.active_charts_order = data.get(
            "active_charts_order", data.get("active_vargas", ["D1"]))

        for d_id, action in self.varga_actions.items():
            action.blockSignals(True)
            action.setChecked(d_id in self.active_charts_order)
            action.blockSignals(False)

        if self.chart_params:
            try:
                self.chart_data = self.app.ephemeris.calculate_chart(
                    self.chart_params['datetime_dict'],
                    self.chart_params['lat'],
                    self.chart_params['lon'],
                    self.chart_params['tz']
                )
                self.update_renderers()
            except Exception as e:
                print(f"Research Mode: Error recalculating saved chart: {e}")


class ResearchModeWindow(QMainWindow):
    """Main standalone window for side-by-side Research Mode."""

    def __init__(self, app_instance):
        super().__init__()
        self.app = app_instance
        self.setWindowTitle("Research & Comparison Mode - Diamond Chart Pro")
        self.resize(1200, 800)

        self.current_layout_mode = self.app.cb_layout_mode.currentText() if hasattr(
            self.app, "cb_layout_mode") else "1 Left, 2 Right (Stacked)"

        self.show_tooltips = True  # Default state

        # Inherit default aspect settings safely from the main app
        self.show_aspects = self.app.chk_aspects.isChecked(
        ) if hasattr(self.app, 'chk_aspects') else False
        if hasattr(self.app, 'aspect_cb'):
            self.visible_aspect_planets = [
                p for p, cb in self.app.aspect_cb.items() if cb.isChecked()]
        else:
            self.visible_aspect_planets = [
                "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

        self.is_modified = False

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Move Save/Load to the native Window MenuBar to save vertical space
        menu_bar = self.menuBar()
        session_menu = menu_bar.addMenu("Research Session")

        save_act = QAction("💾 Save Session", self)
        save_act.triggered.connect(self.save_research)
        session_menu.addAction(save_act)

        load_act = QAction("📂 Load Session", self)
        load_act.triggered.connect(self.load_research)
        session_menu.addAction(load_act)

        layout_menu = menu_bar.addMenu("Layout")
        self.layout_actions = []
        for l_mode in ["3 Columns", "2 Columns", "1 Left, 2 Right (Stacked)"]:
            act = QAction(l_mode, self)
            act.setCheckable(True)
            if l_mode == self.current_layout_mode:
                act.setChecked(True)
            act.triggered.connect(
                lambda checked, lm=l_mode: self.change_layout(lm))
            layout_menu.addAction(act)
            self.layout_actions.append(act)

        settings_menu = menu_bar.addMenu("Settings")
        self.tooltips_act = QAction("Show Tooltips", self)
        self.tooltips_act.setCheckable(True)
        self.tooltips_act.setChecked(self.show_tooltips)
        self.tooltips_act.triggered.connect(self.toggle_tooltips)
        settings_menu.addAction(self.tooltips_act)

        # Aspects settings inside the Settings menu ONLY
        self.aspects_act = QAction("Show Aspects", self)
        self.aspects_act.setCheckable(True)
        self.aspects_act.setChecked(self.show_aspects)
        self.aspects_act.triggered.connect(self.toggle_aspects)
        settings_menu.addAction(self.aspects_act)

        self.aspect_planets_menu = settings_menu.addMenu("Aspecting Planets")
        self.aspect_planets_menu.setEnabled(self.show_aspects)
        self.aspect_planet_actions = {}

        aspect_planets = [
            ("Sun", "#FF8C00"), ("Moon", "#00BCD4"), ("Mars", "#FF0000"),
            ("Mercury", "#00C853"), ("Jupiter", "#FFD700"), ("Venus", "#FF1493"),
            ("Saturn", "#0000CD"), ("Rahu", "#708090"), ("Ketu", "#8B4513")
        ]

        for p, color in aspect_planets:
            act = QAction(p, self)
            act.setCheckable(True)
            act.setChecked(p in self.visible_aspect_planets)
            act.triggered.connect(self.toggle_aspect_planet)
            self.aspect_planets_menu.addAction(act)
            self.aspect_planet_actions[p] = act

        # Splitter Context
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_panel = ResearchPanel(
            self.app, "Panel 1", parent_window=self)
        self.right_panel = ResearchPanel(
            self.app, "Panel 2", parent_window=self)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([600, 600])

        main_layout.addWidget(self.splitter)

    def mark_modified(self):
        if not self.is_modified:
            self.is_modified = True
            self.setWindowTitle(
                "Research & Comparison Mode - Diamond Chart Pro *")

    def reset_modified(self):
        self.is_modified = False
        self.setWindowTitle("Research & Comparison Mode - Diamond Chart Pro")

    def change_layout(self, new_layout):
        self.current_layout_mode = new_layout
        for act in self.layout_actions:
            act.setChecked(act.text() == new_layout)
        self.mark_modified()
        self.left_panel.update_renderers()
        self.right_panel.update_renderers()

    def toggle_tooltips(self):
        """Toggles tooltips explicitly for all charts rendered in Research Mode."""
        self.show_tooltips = self.tooltips_act.isChecked()
        self.mark_modified()
        self.left_panel.update_renderers()
        self.right_panel.update_renderers()

    def toggle_aspects(self):
        """Toggles aspects explicitly for Research Mode."""
        self.show_aspects = self.aspects_act.isChecked()
        self.aspect_planets_menu.setEnabled(self.show_aspects)
        self.mark_modified()
        self.left_panel.update_renderers()
        self.right_panel.update_renderers()

    def toggle_aspect_planet(self):
        """Updates the list of visible aspecting planets in Research Mode."""
        self.visible_aspect_planets = [
            p for p, act in self.aspect_planet_actions.items() if act.isChecked()
        ]
        self.mark_modified()
        self.left_panel.update_renderers()
        self.right_panel.update_renderers()

    def save_research(self):
        os.makedirs(os.path.join("saves", "research"), exist_ok=True)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Research Session",
            os.path.join("saves", "research"),
            "Research JSON (*.json)"
        )
        if not path:
            return False

        data = {
            "version": "1.0",
            "type": "research_session",
            "layout_mode": self.current_layout_mode,
            "show_tooltips": self.show_tooltips,
            "show_aspects": self.show_aspects,
            "visible_aspect_planets": self.visible_aspect_planets,
            "left": self.left_panel.get_save_data(),
            "right": self.right_panel.get_save_data()
        }
        try:
            with open(path, 'w') as f:
                json.dump(data, f, indent=4)
            self.reset_modified()
            QMessageBox.information(
                self, "Success", "Research session saved successfully!")
            return True
        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to save research session:\n{str(e)}")
            return False

    def load_research(self):
        if self.is_modified:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                'Changes made save?',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            if reply == QMessageBox.StandardButton.Save:
                if not self.save_research():
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                return

        os.makedirs(os.path.join("saves", "research"), exist_ok=True)
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Research Session",
            os.path.join("saves", "research"),
            "Research JSON (*.json)"
        )
        if not path:
            return

        try:
            with open(path, 'r') as f:
                data = json.load(f)

            if data.get("type") != "research_session":
                QMessageBox.warning(
                    self, "Warning", "This file doesn't appear to be a valid Research Session.")
                return

            # Restore the layout mode first
            saved_layout = data.get("layout_mode")
            if saved_layout:
                self.change_layout(saved_layout)

            # Restore Tooltips setting
            saved_tooltips = data.get("show_tooltips", True)
            self.show_tooltips = saved_tooltips
            self.tooltips_act.setChecked(saved_tooltips)

            # Restore Aspects setting
            self.show_aspects = data.get("show_aspects", False)
            self.aspects_act.blockSignals(True)
            self.aspects_act.setChecked(self.show_aspects)
            self.aspects_act.blockSignals(False)
            self.aspect_planets_menu.setEnabled(self.show_aspects)

            planets_default = [ "Mars", "Jupiter", "Saturn",]
            self.visible_aspect_planets = data.get("visible_aspect_planets", planets_default)
            for p, act in self.aspect_planet_actions.items():
                act.blockSignals(True)
                act.setChecked(p in self.visible_aspect_planets)
                act.blockSignals(False)

            # Then load the data into the panels
            self.left_panel.load_from_data(data.get("left", {}))
            self.right_panel.load_from_data(data.get("right", {}))

            # Re-render UI after loads
            self.left_panel.update_renderers()
            self.right_panel.update_renderers()

            self.reset_modified()

        except Exception as e:
            QMessageBox.critical(
                self, "Error", f"Failed to load research session:\n{str(e)}")

    def closeEvent(self, event):
        if self.is_modified:
            reply = QMessageBox.question(
                self, 'Unsaved Changes',
                'Changes made save?',
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )

            if reply == QMessageBox.StandardButton.Save:
                if self.save_research():
                    event.accept()
                else:
                    event.ignore()
            elif reply == QMessageBox.StandardButton.Discard:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def setup_ui(app, layout):
    """
    Entry point for Diamond Chart Pro plugin system.
    This creates the launch button inside the extensions panel.
    """
    group = QGroupBox("Research Mode")
    v_layout = QVBoxLayout()
    v_layout.setContentsMargins(8, 8, 8, 8)
    
    status_label = QLabel("Launch research mode in which you can view multiple charts (and divisions) at once for comparision.")
    status_label.setWordWrap(True)
    status_label.setStyleSheet("color: #555; font-size: 11px;")
    
    btn_launch_research = QPushButton("Launch Research Mode")
    # Updated style sheet with hover and pressed effects
    btn_launch_research.setStyleSheet("""
        QPushButton {
            font-weight: bold;
            color: #3f275e;
            border: 1px solid #c0a3d5;
            background-color: #f3e5f5;
            padding: 5px 10px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #e1bee7;
            border-color: #8e44ad;
            color: #2c1a44;
        }
        QPushButton:pressed {
            background-color: #ce93d8;
            border-style: inset;
        }""")
    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(6)
    btn_layout.addWidget(btn_launch_research)
    
    v_layout.addWidget(status_label)
    v_layout.addLayout(btn_layout)
    group.setLayout(v_layout)
    layout.addWidget(group)

    # We attach the window reference to the app so it isn't garbage collected
    def on_launch():
        if not hasattr(app, "research_mode_window") or not app.research_mode_window.isVisible():
            app.research_mode_window = ResearchModeWindow(app)
            app.research_mode_window.showMaximized()
        else:
            app.research_mode_window.showMaximized()
            app.research_mode_window.raise_()
            app.research_mode_window.activateWindow()

    btn_launch_research.clicked.connect(on_launch)
