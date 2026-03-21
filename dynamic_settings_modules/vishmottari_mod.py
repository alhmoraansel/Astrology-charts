# dynamic_settings_modules/vimshottari_mod.py
import datetime
from PyQt6.QtWidgets import (QPushButton, QMessageBox, QLabel, QVBoxLayout, QHBoxLayout, 
                             QDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit, QApplication, QAbstractItemView)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QBrush, QFont

import astro_engine

# --- VIMSHOTTARI CONSTANTS ---
DASHA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, 
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17
}

PLANET_COLORS = {
    "Sun": "#d35400", "Moon": "#2980b9", "Mars": "#c0392b", 
    "Mercury": "#27ae60", "Jupiter": "#f39c12", "Venus": "#8e44ad", 
    "Saturn": "#2c3e50", "Rahu": "#7f8c8d", "Ketu": "#8d6e63"
}

class VimshottariDialog(QDialog):
    def __init__(self, parent, moon_lon, birth_dt_dict, current_dt):
        super().__init__(parent)
        self.setWindowTitle("Vimshottari Dasha Explorer (Hierarchical)")
        self.resize(1000, 650)
        self.setStyleSheet("""
            QTreeWidget { font-size: 14px; alternate-background-color: #f9f9f9; border: 1px solid #ddd; }
            QTreeWidget::item { padding: 4px; }
            QTreeWidget::item:selected { background-color: #e0f7fa; color: black; }
            QHeaderView::section { font-weight: bold; background-color: #ecf0f1; padding: 6px; border: none; border-right: 1px solid #ddd; border-bottom: 1px solid #ddd; }
        """)
        
        self.moon_lon = moon_lon
        self.is_fully_loaded = False
        self._load_queue = []
        self.active_leaf_item = None
        
        # Safely parse birth date
        y = max(1, birth_dt_dict.get("year", 2000))
        m = max(1, min(12, birth_dt_dict.get("month", 1)))
        d = max(1, min(31, birth_dt_dict.get("day", 1)))
        hr = max(0, min(23, birth_dt_dict.get("hour", 0)))
        mn = max(0, min(59, birth_dt_dict.get("minute", 0)))
        sc = max(0, min(59, int(birth_dt_dict.get("second", 0))))
        self.birth_date = datetime.datetime(y, m, d, hr, mn, sc)
        
        self.current_date = current_dt
        
        layout = QVBoxLayout(self)
        
        # --- Info & Search Header ---
        header_layout = QHBoxLayout()
        
        info_lbl = QLabel(f"<b>Birth Date:</b> {self.birth_date.strftime('%d %b %Y, %H:%M')}  |  <b>Target Date (Today):</b> {self.current_date.strftime('%d %b %Y')}")
        info_lbl.setStyleSheet("color: #34495e; font-size: 13px;")
        

        
        btn_collapse = QPushButton("Collapse All")
        btn_collapse.clicked.connect(lambda: self.tree.collapseAll())
        
        header_layout.addWidget(info_lbl)
        header_layout.addStretch()
        header_layout.addWidget(btn_collapse)
        
        layout.addLayout(header_layout)
        
        # --- Expandable Tree Widget ---
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["Dasha Sequence", "Start Date", "End Date", "Age at Start"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setSelectionBehavior(QTreeWidget.SelectionBehavior.SelectRows)
        
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        # Connect manual lazy loading (if user clicks before background loader reaches it)
        self.tree.itemExpanded.connect(self.on_item_expanded)
        
        layout.addWidget(self.tree)
        
        # --- Footer ---
        footer = QHBoxLayout()
        legend = QLabel("🟢 Highlighted row indicates the currently active Dasha.")
        legend.setStyleSheet("color: #27ae60; font-weight: bold;")
        
        self.load_status_lbl = QLabel("")
        self.load_status_lbl.setStyleSheet("color: #7f8c8d; font-size: 12px; font-style: italic;")
        
        btn_close = QPushButton("Close")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        
        footer.addWidget(legend)
        footer.addWidget(self.load_status_lbl)
        footer.addStretch()
        footer.addWidget(btn_close)
        layout.addLayout(footer)
        
        # Background Loading Timer
        self._bg_timer = QTimer(self)
        self._bg_timer.timeout.connect(self._bg_load_chunk)
        
        # Initialize the interface
        self.populate_tree()

    def format_dt(self, dt, depth):
        """Format datetime: Display exact time for level 4 (Sookshma) and 5 (Prana)"""
        if depth >= 4:
            return dt.strftime("%d %b %Y, %H:%M")
        return dt.strftime("%d %b %Y")

    def on_item_expanded(self, item):
        """Manual lazy loading handler if the user expands a folder manually before background loading finishes."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("loaded"):
            return
            
        if item.data(0, Qt.ItemDataRole.UserRole + 1):
            dummy = item.child(0)
            if dummy and dummy.text(0) == "Loading...":
                item.removeChild(dummy)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
            
        self._build_children(item, data["lord_idx"], data["current_start"], data["duration_years"], data["depth"], data["prefix"], auto_expand_active=False)
        
        data["loaded"] = True
        item.setData(0, Qt.ItemDataRole.UserRole, data)

    def _build_children(self, parent_item, lord_idx, current_start, duration_years, depth, prefix, auto_expand_active=False):
        """Dynamically generates 9 Antar/Pratyantar children for any given parent Dasha"""
        sub_start = current_start
        for i in range(9):
            sub_lord_idx = (lord_idx + i) % 9
            sub_lord = DASHA_LORDS[sub_lord_idx]
            
            sub_dur_years = duration_years * (DASHA_YEARS[sub_lord] / 120.0)
            sub_end = sub_start + datetime.timedelta(days=sub_dur_years * 365.2425)
            
            # Skip if branch ended before birth
            if sub_end <= self.birth_date:
                sub_start = sub_end
                continue
    

            from dateutil.relativedelta import relativedelta

            # This calculates the exact calendar difference
            actual_start = max(self.birth_date, sub_start)
            diff = relativedelta(actual_start, self.birth_date)

            y = diff.years
            m = diff.months

            
            age_str = f"{y}y {m}m"
            seq_name = prefix + ("-" if prefix else "") + sub_lord
            is_active = actual_start <= self.current_date < sub_end
            
            item = QTreeWidgetItem(parent_item)
            item.setText(0, seq_name)
            item.setText(1, self.format_dt(actual_start, depth + 1))
            item.setText(2, self.format_dt(sub_end, depth + 1))
            item.setText(3, age_str)
            
            item.setForeground(0, QBrush(QColor(PLANET_COLORS.get(sub_lord, "#000000"))))
            
            if is_active:
                bg_brush = QBrush(QColor("#e8f8f5"))
                for col in range(4): item.setBackground(col, bg_brush)
                if depth + 1 == 5:
                    font = item.font(0); font.setBold(True)
                    for col in range(4): 
                        item.setFont(col, font)
                        item.setForeground(col, QBrush(QColor("#117a65")))
                    self.active_leaf_item = item # Capture for auto-scroll!
                        
            # Determine if we should prepare lazy children
            if depth + 1 < 5:
                data = {
                    "lord_idx": sub_lord_idx,
                    "current_start": sub_start,
                    "duration_years": sub_dur_years,
                    "depth": depth + 1,
                    "prefix": seq_name,
                    "loaded": False
                }
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                
                dummy = QTreeWidgetItem(item)
                dummy.setText(0, "Loading...")
                item.setData(0, Qt.ItemDataRole.UserRole + 1, True)
                
                # Eager load the active path straight down to the leaf node
                if auto_expand_active and is_active:
                    item.removeChild(dummy)
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
                    self._build_children(item, sub_lord_idx, sub_start, sub_dur_years, depth + 1, seq_name, auto_expand_active=True)
                    data["loaded"] = True
                    item.setData(0, Qt.ItemDataRole.UserRole, data)
                    item.setExpanded(True)
                    
            sub_start = sub_end

    def populate_tree(self):
        """Builds Top-Level Maha Dashas, eager-loads the active timeline, and queues the rest for background hydration."""
        self.tree.clear()
        self.is_fully_loaded = False
        self._load_queue = []
        self.active_leaf_item = None
        
        nak_len = 360.0 / 27.0
        nak_idx = int(self.moon_lon / nak_len)
        elapsed = self.moon_lon % nak_len
        fraction_left = (nak_len - elapsed) / nak_len

        start_lord_idx = nak_idx % 9
        start_lord = DASHA_LORDS[start_lord_idx]
        start_lord_years = DASHA_YEARS[start_lord]

        past_fraction = 1.0 - fraction_left
        md_start_dt = self.birth_date - datetime.timedelta(days=(past_fraction * start_lord_years * 365.2425))

        cur_md_start = md_start_dt
        self.tree.setUpdatesEnabled(False)
        
        for i in range(9):
            md_lord_idx = (start_lord_idx + i) % 9
            md_lord = DASHA_LORDS[md_lord_idx]
            md_dur_years = DASHA_YEARS[md_lord]
            
            md_end = cur_md_start + datetime.timedelta(days=md_dur_years * 365.2425)
            
            if md_end > self.birth_date:
                actual_start = max(self.birth_date, cur_md_start)
                age_years = (actual_start - self.birth_date).total_seconds() / (365.2425 * 86400.0)
                y = int(age_years); m = int(round((age_years - y) * 12))
                if m == 12: y += 1; m = 0
                
                age_str = f"{y}y {m}m"
                is_active = actual_start <= self.current_date < md_end
                
                root = QTreeWidgetItem(self.tree)
                root.setText(0, md_lord)
                root.setText(1, self.format_dt(actual_start, 1))
                root.setText(2, self.format_dt(md_end, 1))
                root.setText(3, age_str)
                
                font = root.font(0); font.setBold(True)
                for col in range(4): root.setFont(col, font)
                root.setForeground(0, QBrush(QColor(PLANET_COLORS.get(md_lord, "#000000"))))
                
                if is_active:
                    for col in range(4): root.setBackground(col, QBrush(QColor("#e8f8f5")))

                data = {
                    "lord_idx": md_lord_idx,
                    "current_start": cur_md_start,
                    "duration_years": md_dur_years,
                    "depth": 1,
                    "prefix": md_lord,
                    "loaded": False
                }
                root.setData(0, Qt.ItemDataRole.UserRole, data)
                
                dummy = QTreeWidgetItem(root)
                dummy.setText(0, "Loading...")
                root.setData(0, Qt.ItemDataRole.UserRole + 1, True)
                
                # Eagerly drill down the active path immediately
                if is_active:
                    root.removeChild(dummy)
                    root.setData(0, Qt.ItemDataRole.UserRole + 1, False)
                    self._build_children(root, md_lord_idx, cur_md_start, md_dur_years, 1, md_lord, auto_expand_active=True)
                    data["loaded"] = True
                    root.setData(0, Qt.ItemDataRole.UserRole, data)
                    root.setExpanded(True)
                
                self._load_queue.append(root)
                    
            cur_md_start = md_end
            if (cur_md_start - self.birth_date).days / 365.2425 > 120.0:
                break
                
        self.tree.setUpdatesEnabled(True)
        
        # Pin scroll to the currently active Prana Dasha instantly
        if self.active_leaf_item:
            QTimer.singleShot(10, lambda: self.tree.scrollToItem(self.active_leaf_item, QAbstractItemView.ScrollHint.PositionAtCenter))
            
        # Initiate silent background loading
        self.load_status_lbl.setText("⏳ Indexing timeline...")
        self._bg_timer.start(15) # Smooth 15ms background chunks

    def _bg_load_chunk(self):
        """Silently populates collapsed folders in the background without affecting scroll position."""
        chunks_processed = 0
        self.tree.setUpdatesEnabled(False)
        
        while self._load_queue and chunks_processed < 100:
            item = self._load_queue.pop(0)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            # Load children if it hasn't been loaded
            if data and not data.get("loaded"):
                if item.data(0, Qt.ItemDataRole.UserRole + 1):
                    dummy = item.child(0)
                    if dummy and dummy.text(0) == "Loading...":
                        item.removeChild(dummy)
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
                    
                self._build_children(item, data["lord_idx"], data["current_start"], data["duration_years"], data["depth"], data["prefix"], auto_expand_active=False)
                data["loaded"] = True
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                
            # Queue the children for their own expansion (if not leaf)
            if data and data["depth"] < 4:
                for i in range(item.childCount()):
                    self._load_queue.append(item.child(i))
                    
            chunks_processed += 1
            
        self.tree.setUpdatesEnabled(True)
        
        if not self._load_queue:
            self._bg_timer.stop()
            self.is_fully_loaded = True
            self.load_status_lbl.setText("✔️ Timeline Fully indexed.")

    def force_load_all(self):
        """Forces immediate completion of the loading queue if the user performs an early search."""
        if self.is_fully_loaded: return
        self._bg_timer.stop()
        self.load_status_lbl.setText("⏳ Force indexing for search...")
        QApplication.processEvents()
        
        self.tree.setUpdatesEnabled(False)
        while self._load_queue:
            item = self._load_queue.pop(0)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            
            if data and not data.get("loaded"):
                if item.data(0, Qt.ItemDataRole.UserRole + 1):
                    dummy = item.child(0)
                    if dummy and dummy.text(0) == "Loading...":
                        item.removeChild(dummy)
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
                    
                self._build_children(item, data["lord_idx"], data["current_start"], data["duration_years"], data["depth"], data["prefix"], auto_expand_active=False)
                data["loaded"] = True
                item.setData(0, Qt.ItemDataRole.UserRole, data)
                
            if data and data["depth"] < 4:
                for i in range(item.childCount()):
                    self._load_queue.append(item.child(i))
                    
        self.tree.setUpdatesEnabled(True)
        self.is_fully_loaded = True
        self.load_status_lbl.setText("✔️ Timeline fully indexed.")

    def _perform_search(self):
        pass
        text = ""
        if not text:
            self.tree.collapseAll()
            self._re_expand_active()
            if self.active_leaf_item:
                self.tree.scrollToItem(self.active_leaf_item, QAbstractItemView.ScrollHint.PositionAtCenter)
            return
            
        if not self.is_fully_loaded:
            self.force_load_all() 
            
        import PyQt6.QtWidgets as QtWidgets
        iterator = QtWidgets.QTreeWidgetItemIterator(self.tree)
        
        first_match = None
        self.tree.setUpdatesEnabled(False)
        self.tree.clearSelection()
        
        while iterator.value():
            item = iterator.value()
            match = False
            for col in range(4):
                if text in item.text(col).lower():
                    match = True
                    break
                    
            if match:
                if first_match is None:
                    first_match = item
                item.setSelected(True)
                
                # Expand parent folders so result becomes visible
                p = item.parent()
                while p:
                    p.setExpanded(True)
                    p = p.parent()
                    
            iterator += 1
            
        self.tree.setUpdatesEnabled(True)
        if first_match:
            self.tree.scrollToItem(first_match)

    def _re_expand_active(self):
        import PyQt6.QtWidgets as QtWidgets
        iterator = QtWidgets.QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            try:
                bg = item.background(0)
                if bg.color() == QColor("#e8f8f5"):
                    item.setExpanded(True)
            except Exception: pass
            iterator += 1


def setup_ui(app, layout):
    lbl_title = QLabel("Vimshottari Timeline ")
    lbl_title.setStyleSheet("color: #2980b9; font-weight: bold; font-size: 15px; margin-top: 8px;")
    layout.addWidget(lbl_title)
    
    btn_show = QPushButton("Open Dasha Tree")
    btn_show.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold; padding: 6px;")
    layout.addWidget(btn_show)
    
    def open_dasha():
        if not hasattr(app, 'current_base_chart') or not app.current_base_chart:
            QMessageBox.warning(app, "No Chart Data", "Please wait for the base chart to calculate first!")
            return
            
        moon_p = next((p for p in app.current_base_chart.get("planets", []) if p["name"] == "Moon"), None)
        if not moon_p:
            QMessageBox.warning(app, "Error", "Could not locate Moon in the current chart!")
            return
            
        birth_dt_dict = app.time_ctrl.current_time
        current_dt = datetime.datetime.now()
        
        dlg = VimshottariDialog(app, moon_p.get("lon", 0.0), birth_dt_dict, current_dt)
        dlg.exec()

    btn_show.clicked.connect(open_dasha)