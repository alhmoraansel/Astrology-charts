#dunamic_system_modules/vishmottari_mode.py

import datetime
import main  # NEW: Import main to access the main application namespace
from PyQt6.QtWidgets import (QPushButton, QMessageBox, QLabel, QVBoxLayout, QHBoxLayout,QDialog, QTreeWidget, QTreeWidgetItem, QHeaderView, QLineEdit,QApplication, QAbstractItemView, QDateEdit, QGroupBox)
from PyQt6.QtCore import Qt, QTimer, QDate
from PyQt6.QtGui import QColor, QBrush, QFont

import astro_engine

PLUGIN_GROUP = "DASHAS"
PLUGIN_INDEX = 7

# Attempt to load SmoothScroller from the main application namespace
SmoothScroller = getattr(main, 'SmoothScroller', None)
# --- VIMSHOTTARI CONSTANTS ---
DASHA_LORDS = ["Ketu", "Venus", "Sun", "Moon",
               "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
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
        # Tracks strictly the 5 active items for O(1) instantaneous updates
        self.active_path_items = []
        self._search_cache = []  # Pure data cache for lightning-fast search
        
        # NEW: Keep a reference to scrollers to prevent garbage collection
        self.scrollers = [] 

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

        info_lbl = QLabel(
            f"<b>Birth Date:</b> {self.birth_date.strftime('%d %b %Y, %H:%M')}")
        info_lbl.setStyleSheet("color: #34495e; font-size: 13px;")

        target_date_lbl = QLabel("<b>Target Date:</b>")
        target_date_lbl.setStyleSheet(
            "color: #34495e; font-size: 13px; margin-left: 15px;")

        # Interactive Date Picker for Target Date
        self.target_date_edit = QDateEdit()
        self.target_date_edit.setCalendarPopup(True)
        self.target_date_edit.setDisplayFormat("dd MMM yyyy")
        self.target_date_edit.setDate(
            QDate(self.current_date.year, self.current_date.month, self.current_date.day))
        self.target_date_edit.setStyleSheet("font-size: 13px; padding: 2px;")
        self.target_date_edit.dateChanged.connect(self.on_target_date_changed)

        btn_collapse = QPushButton("Collapse All")
        btn_collapse.clicked.connect(lambda: self.tree.collapseAll())

        header_layout.addWidget(info_lbl)
        header_layout.addWidget(target_date_lbl)
        header_layout.addWidget(self.target_date_edit)
        header_layout.addStretch()
        header_layout.addWidget(btn_collapse)

        layout.addLayout(header_layout)

        # --- Expandable Tree Widget ---
        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(
            ["Dasha Sequence", "Start Date", "End Date", "Age at Start"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.setSelectionBehavior(
            QTreeWidget.SelectionBehavior.SelectRows)

        # --- NEW: Qt Scrolling Optimizations ---
        self.tree.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tree.setUniformRowHeights(True)

        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(
            3, QHeaderView.ResizeMode.ResizeToContents)

        # Connect manual lazy loading (if user clicks before background loader reaches it)
        self.tree.itemExpanded.connect(self.on_item_expanded)

        layout.addWidget(self.tree)

        # --- NEW: Apply your custom Smooth Scroller ---
        self.apply_smooth_scroll(self.tree)

        # --- Footer ---
        footer = QHBoxLayout()
        legend = QLabel(
            "🟢 Highlighted row indicates the currently active Dasha.")
        legend.setStyleSheet("color: #27ae60; font-weight: bold;")

        self.load_status_lbl = QLabel("")
        self.load_status_lbl.setStyleSheet(
            "color: #7f8c8d; font-size: 12px; font-style: italic;")

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

    # --- NEW: Smooth Scroll Applier Method ---
    def apply_smooth_scroll(self, widget):
        if SmoothScroller:
            scroller = SmoothScroller(widget)
            self.scrollers.append(scroller)

    def on_target_date_changed(self, new_qdate):
        """Triggered when the user picks a new date. Instant O(1) highlighting update."""
        self.current_date = datetime.datetime(
            new_qdate.year(), new_qdate.month(), new_qdate.day())

        self.tree.setUpdatesEnabled(False)

        # 1. Instantly wipe highlighting ONLY from the previously active nodes (max 5 nodes)
        for item in self.active_path_items:
            self._unhighlight_item(item)

        self.active_path_items.clear()
        self.active_leaf_item = None
        self.tree.collapseAll()

        # 2. Lightning-fast drill down to find and highlight the new path
        for i in range(self.tree.topLevelItemCount()):
            root_item = self.tree.topLevelItem(i)
            data = root_item.data(0, Qt.ItemDataRole.UserRole)
            if data["start_dt"] <= self.current_date < data["end_dt"]:
                self._drill_down_and_highlight(root_item)
                break

        self.tree.setUpdatesEnabled(True)

        # Pin scroll to newly active Dasha
        if self.active_leaf_item:
            self.tree.scrollToItem(
                self.active_leaf_item, QAbstractItemView.ScrollHint.PositionAtCenter)

    def _unhighlight_item(self, item):
        """Resets an item to its default non-active state."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        for col in range(4):
            item.setBackground(col, QBrush())  # Reset background

        font = item.font(0)
        # Only top-level items are bold naturally
        font.setBold(data["depth"] == 1)

        for col in range(4):
            item.setFont(col, font)
            if col == 0:
                fg_color = PLANET_COLORS.get(data["lord_name"], "#000000")
                item.setForeground(col, QBrush(QColor(fg_color)))
            else:
                # Reset to default text color
                item.setForeground(col, QBrush())

    def _highlight_item(self, item, data):
        """Applies the active green highlight style to a given item."""
        bg_brush = QBrush(QColor("#e8f8f5"))
        for col in range(4):
            item.setBackground(col, bg_brush)

        if data["depth"] == 5:
            font = item.font(0)
            font.setBold(True)
            for col in range(4):
                item.setFont(col, font)
                item.setForeground(col, QBrush(QColor("#117a65")))
            self.active_leaf_item = item

    def _drill_down_and_highlight(self, item):
        """Traverses only the matching active time branch, loading it on the fly if needed."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        self._highlight_item(item, data)
        self.active_path_items.append(item)
        item.setExpanded(True)

        if data["depth"] == 5:
            return

        if item.data(0, Qt.ItemDataRole.UserRole + 1):  # Children haven't been loaded yet
            dummy = item.child(0)
            if dummy and dummy.text(0) == "Loading...":
                item.removeChild(dummy)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, False)

            # Auto-expand flag will naturally build the remainder of the active tree
            self._build_children(item, data["lord_idx"], data["current_start"],
                                 data["duration_years"], data["depth"], data["prefix"], auto_expand_active=True)
            data["loaded"] = True
            item.setData(0, Qt.ItemDataRole.UserRole, data)
        else:
            # Children are already loaded (via background index). Just find the active one.
            for i in range(item.childCount()):
                child = item.child(i)
                c_data = child.data(0, Qt.ItemDataRole.UserRole)
                if c_data and c_data["start_dt"] <= self.current_date < c_data["end_dt"]:
                    self._drill_down_and_highlight(child)
                    break

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

        self._build_children(item, data["lord_idx"], data["current_start"],
                             data["duration_years"], data["depth"], data["prefix"], auto_expand_active=False)

        data["loaded"] = True
        item.setData(0, Qt.ItemDataRole.UserRole, data)

    def _build_children(self, parent_item, lord_idx, current_start, duration_years, depth, prefix, auto_expand_active=False):
        """Dynamically generates 9 Antar/Pratyantar children for any given parent Dasha"""
        sub_start = current_start
        for i in range(9):
            sub_lord_idx = (lord_idx + i) % 9
            sub_lord = DASHA_LORDS[sub_lord_idx]

            sub_dur_years = duration_years * (DASHA_YEARS[sub_lord] / 120.0)
            sub_end = sub_start + \
                datetime.timedelta(days=sub_dur_years * 365.2425)

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

            start_str = self.format_dt(actual_start, depth + 1)
            end_str = self.format_dt(sub_end, depth + 1)

            item = QTreeWidgetItem(parent_item)
            item.setText(0, seq_name)
            item.setText(1, start_str)
            item.setText(2, end_str)
            item.setText(3, age_str)

            # Cache for lightning fast O(1) text search
            search_text = f"{seq_name} {start_str} {end_str} {age_str}".lower()
            self._search_cache.append((search_text, item))

            # Attach all required data immediately to allow rapid highlight refreshing
            data = {
                "lord_idx": sub_lord_idx,
                "current_start": sub_start,
                "duration_years": sub_dur_years,
                "depth": depth + 1,
                "prefix": seq_name,
                "loaded": depth + 1 == 5,
                "start_dt": actual_start,
                "end_dt": sub_end,
                "lord_name": sub_lord
            }
            item.setData(0, Qt.ItemDataRole.UserRole, data)

            item.setForeground(
                0, QBrush(QColor(PLANET_COLORS.get(sub_lord, "#000000"))))

            if is_active:
                self._highlight_item(item, data)
                self.active_path_items.append(item)

            # Determine if we should prepare lazy children
            if depth + 1 < 5:
                dummy = QTreeWidgetItem(item)
                dummy.setText(0, "Loading...")
                item.setData(0, Qt.ItemDataRole.UserRole + 1, True)

                # Eager load the active path straight down to the leaf node
                if auto_expand_active and is_active:
                    item.removeChild(dummy)
                    item.setData(0, Qt.ItemDataRole.UserRole + 1, False)
                    self._build_children(
                        item, sub_lord_idx, sub_start, sub_dur_years, depth + 1, seq_name, auto_expand_active=True)
                    data["loaded"] = True
                    item.setData(0, Qt.ItemDataRole.UserRole, data)
                    item.setExpanded(True)

            sub_start = sub_end

    def populate_tree(self):
        """Builds Top-Level Maha Dashas, eager-loads the active timeline, and queues the rest for background hydration."""
        self.tree.clear()
        self.is_fully_loaded = False
        self._load_queue = []
        self._search_cache.clear()
        self.active_leaf_item = None

        nak_len = 360.0 / 27.0
        nak_idx = int(self.moon_lon / nak_len)
        elapsed = self.moon_lon % nak_len
        fraction_left = (nak_len - elapsed) / nak_len

        start_lord_idx = nak_idx % 9
        start_lord = DASHA_LORDS[start_lord_idx]
        start_lord_years = DASHA_YEARS[start_lord]

        past_fraction = 1.0 - fraction_left
        md_start_dt = self.birth_date - \
            datetime.timedelta(
                days=(past_fraction * start_lord_years * 365.2425))

        cur_md_start = md_start_dt
        self.tree.setUpdatesEnabled(False)

        for i in range(9):
            md_lord_idx = (start_lord_idx + i) % 9
            md_lord = DASHA_LORDS[md_lord_idx]
            md_dur_years = DASHA_YEARS[md_lord]

            md_end = cur_md_start + \
                datetime.timedelta(days=md_dur_years * 365.2425)

            if md_end > self.birth_date:
                actual_start = max(self.birth_date, cur_md_start)
                age_years = (
                    actual_start - self.birth_date).total_seconds() / (365.2425 * 86400.0)
                y = int(age_years)
                m = int(round((age_years - y) * 12))
                if m == 12:
                    y += 1
                    m = 0

                age_str = f"{y}y {m}m"
                is_active = actual_start <= self.current_date < md_end

                start_str = self.format_dt(actual_start, 1)
                end_str = self.format_dt(md_end, 1)

                root = QTreeWidgetItem(self.tree)
                root.setText(0, md_lord)
                root.setText(1, start_str)
                root.setText(2, end_str)
                root.setText(3, age_str)

                search_text = f"{md_lord} {start_str} {end_str} {age_str}".lower()
                self._search_cache.append((search_text, root))

                font = root.font(0)
                font.setBold(True)
                for col in range(4):
                    root.setFont(col, font)
                root.setForeground(
                    0, QBrush(QColor(PLANET_COLORS.get(md_lord, "#000000"))))

                data = {
                    "lord_idx": md_lord_idx,
                    "current_start": cur_md_start,
                    "duration_years": md_dur_years,
                    "depth": 1,
                    "prefix": md_lord,
                    "loaded": False,
                    "start_dt": actual_start,
                    "end_dt": md_end,
                    "lord_name": md_lord
                }
                root.setData(0, Qt.ItemDataRole.UserRole, data)

                if is_active:
                    self._highlight_item(root, data)
                    self.active_path_items.append(root)

                dummy = QTreeWidgetItem(root)
                dummy.setText(0, "Loading...")
                root.setData(0, Qt.ItemDataRole.UserRole + 1, True)

                # Eagerly drill down the active path immediately
                if is_active:
                    root.removeChild(dummy)
                    root.setData(0, Qt.ItemDataRole.UserRole + 1, False)
                    self._build_children(
                        root, md_lord_idx, cur_md_start, md_dur_years, 1, md_lord, auto_expand_active=True)
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
            QTimer.singleShot(10, lambda: self.tree.scrollToItem(
                self.active_leaf_item, QAbstractItemView.ScrollHint.PositionAtCenter))

        # Initiate silent background loading
        self.load_status_lbl.setText("⏳ Indexing timeline...")
        self._bg_timer.start(15)  # Smooth 15ms background chunks

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

                self._build_children(item, data["lord_idx"], data["current_start"],
                                     data["duration_years"], data["depth"], data["prefix"], auto_expand_active=False)
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
        if self.is_fully_loaded:
            return
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

                self._build_children(item, data["lord_idx"], data["current_start"],
                                     data["duration_years"], data["depth"], data["prefix"], auto_expand_active=False)
                data["loaded"] = True
                item.setData(0, Qt.ItemDataRole.UserRole, data)

            if data and data["depth"] < 4:
                for i in range(item.childCount()):
                    self._load_queue.append(item.child(i))

        self.tree.setUpdatesEnabled(True)
        self.is_fully_loaded = True
        self.load_status_lbl.setText("✔️ Timeline fully indexed.")

    def _perform_search(self):
        text = self.search_input.text().strip().lower()
        if not text:
            self.tree.collapseAll()
            self._re_expand_active()
            if self.active_leaf_item:
                self.tree.scrollToItem(
                    self.active_leaf_item, QAbstractItemView.ScrollHint.PositionAtCenter)
            return

        if not self.is_fully_loaded:
            self.force_load_all()

        first_match = None
        self.tree.setUpdatesEnabled(False)
        self.tree.clearSelection()

        # Traverse the pure data cache instead of the UI Tree for instant results
        for search_string, item in self._search_cache:
            if text in search_string:
                if first_match is None:
                    first_match = item
                item.setSelected(True)

                # Expand parent folders so result becomes visible
                p = item.parent()
                while p:
                    p.setExpanded(True)
                    p = p.parent()

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
            except Exception:
                pass
            iterator += 1

def setup_ui(app, layout):
    group = QGroupBox("Vimshottari Timeline")
    v_layout = QVBoxLayout()
    v_layout.setContentsMargins(8, 8, 8, 8)
    
    status_label = QLabel("Dashas Explorer, Indexes the timeline on first launch.")
    status_label.setWordWrap(True)
    status_label.setStyleSheet("color: #555; font-size: 11px;")
    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(6)

    btn_show = QPushButton("Open Dasha Tree")

# --- Open Dasha Tree Button (Vimshottari Blue Theme) ---
    btn_show.setStyleSheet("""
    QPushButton {
        background-color: #2980b9; 
        color: white; 
        font-weight: bold; 
        padding: 6px 15px;
        border: 1px solid #1c5982;
        border-radius: 4px;
    }
    QPushButton:hover {
        background-color: #0d5c91;
        border-color: #2980b9;
    }
    QPushButton:pressed {
        background-color: #2471a3;
        border-style: inset;
    }
""")
    v_layout.addWidget(status_label)
    btn_layout.addWidget(btn_show)
    v_layout.addLayout(btn_layout)
    group.setLayout(v_layout)
    layout.addWidget(group)

    def open_dasha():
        if not hasattr(app, 'current_base_chart') or not app.current_base_chart:
            QMessageBox.warning(
                app, "No Chart Data", "Please wait for the base chart to calculate first!")
            return

        moon_p = next((p for p in app.current_base_chart.get(
            "planets", []) if p["name"] == "Moon"), None)
        if not moon_p:
            QMessageBox.warning(
                app, "Error", "Could not locate Moon in the current chart!")
            return

        birth_dt_dict = app.time_ctrl.current_time
        moon_lon = moon_p.get("lon", 0.0)

        # Create a signature to check if the chart properties have changed
        chart_sig = (moon_lon, tuple(birth_dt_dict.items()))

        # Cache the dialog per chart to prevent re-indexing the entire tree!
        if not hasattr(app, '_vimshottari_dlg_cache') or getattr(app, '_vimshottari_chart_sig', None) != chart_sig:
            current_dt = datetime.datetime.now()
            app._vimshottari_dlg_cache = VimshottariDialog(
                app, moon_lon, birth_dt_dict, current_dt)
            app._vimshottari_chart_sig = chart_sig

        app._vimshottari_dlg_cache.exec()

    btn_show.clicked.connect(open_dasha)
