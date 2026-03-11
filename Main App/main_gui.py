import sys
import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QSplitter, QLabel, QLineEdit, 
                             QPushButton, QComboBox, QDateEdit, QTimeEdit, 
                             QSlider, QTableWidget, QTableWidgetItem, QCheckBox,
                             QHeaderView, QMessageBox, QGroupBox, QFileDialog)
from PyQt6.QtCore import Qt, QDate, QTime

from location_service import LocationWorker
from ephemeris_engine import EphemerisEngine
from chart_renderer import ChartRenderer
from time_controller import TimeController

class AstroApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vedic Astrology Diamond Chart Pro")
        self.resize(1100, 750)

        # Core Engines
        self.ephemeris = EphemerisEngine()
        self.time_ctrl = TimeController()
        
        # State variables
        self.current_lat = 28.6139
        self.current_lon = 77.2090
        self.current_tz = "Asia/Kolkata"
        self.is_updating_ui = False # Guard to prevent signal loops

        self._init_ui()
        self._connect_signals()
        
        # Initialize default chart
        self.time_ctrl.set_time(datetime.datetime.now())

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Panel (Controls)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMaximumWidth(350)

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
        self.chk_theme = QCheckBox("Dark Mode")
        
        self.btn_export = QPushButton("Export PNG...")

        set_layout.addWidget(QLabel("Ayanamsa:"))
        set_layout.addWidget(self.cb_ayanamsa)
        set_layout.addWidget(self.chk_symbols)
        set_layout.addWidget(self.chk_rahu)
        set_layout.addWidget(self.chk_theme)
        set_layout.addWidget(self.btn_export)
        set_group.setLayout(set_layout)

        # Add to left layout
        left_layout.addWidget(loc_group)
        left_layout.addWidget(dt_group)
        left_layout.addWidget(nav_group)
        left_layout.addWidget(set_group)
        left_layout.addStretch()

        # Right Panel (Splitter for Chart and Table)
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Chart
        self.chart = ChartRenderer()
        right_splitter.addWidget(self.chart)
        
        # Info Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Planet", "Sign", "Degree", "House", "Retrograde"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        right_splitter.addWidget(self.table)
        right_splitter.setSizes([500, 200])

        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_splitter)

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
        self.chk_theme.stateChanged.connect(self.toggle_theme)
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
        self.ephemeris.set_ayanamsa(self.cb_ayanamsa.currentText())
        self.chart.use_symbols = self.chk_symbols.isChecked()
        self.chart.show_rahu_ketu = self.chk_rahu.isChecked()
        self.recalculate()

    def toggle_theme(self):
        is_dark = self.chk_theme.isChecked()
        self.chart.set_theme(is_dark)
        
        if is_dark:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #121212; color: #EEEEEE; }
                QLineEdit, QComboBox, QDateEdit, QTimeEdit { background-color: #2D2D2D; color: #EEE; border: 1px solid #555; }
                QPushButton { background-color: #333; color: white; border: 1px solid #555; padding: 5px; }
                QTableWidget { background-color: #1E1E1E; color: white; gridline-color: #444; }
                QHeaderView::section { background-color: #2D2D2D; color: white; }
                QGroupBox { border: 1px solid #555; margin-top: 1ex; }
                QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }
            """)
        else:
            self.setStyleSheet("") # Reset to default
            
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

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AstroApp()
    window.show()
    sys.exit(app.exec())