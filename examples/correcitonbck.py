# dynamic_settings_modules/advanced_dashas_mod.py

import sys, os, math, datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QDialog, QTreeWidget, QTreeWidgetItem, QLabel, 
                             QGroupBox, QTabWidget, QHeaderView, QMessageBox,
                             QComboBox, QDateEdit, QSpinBox, QTableWidget, 
                             QTableWidgetItem, QFrame, QGridLayout, QHeaderView, QApplication)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QTimer, QDate
import swisseph as swe
import __main__

# Add parent dir to path to import the dictionary and engine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import astro_engine
import advanced_dasha_results

info_print = getattr(__main__, 'info_print', print)
error_print = getattr(__main__, 'error_print', print)

# ==============================================================================
# ASTROLOGICAL CONSTANTS & KEYWORD DICTIONARY FOR REVERSE SEARCH
# ==============================================================================

VIM_DASHA_LORDS = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
VIM_DASHA_YEARS = {"Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7, "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17}

YOGINI_DEITIES = {
    1: ("Mangal", 1), 2: ("Pingal", 2), 3: ("Dhanya", 3), 4: ("Bhramari", 4),
    5: ("Bhadrika", 5), 6: ("Ulka", 6), 7: ("Siddha", 7), 8: ("Sankat", 8)
}

SWE_PLANET_MAP = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, 
    "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, 
    "Rahu": swe.MEAN_NODE, "Ketu": swe.MEAN_NODE
}

# Used to map events to Classical Dasha effects and to validate via Dasha-Lagna
EVENT_CATEGORIES = {
    "Marriage / Romance": {
        "kws": ["marriage", "wife", "husband", "conjugal", "women", "romance", "bed", "sweet"],
        "support_houses": [1, 2, 4, 5, 7, 9, 10, 11] # Favorable relative placements
    },
    "Childbirth": {
        "kws": ["son", "daughter", "child", "grandchildren", "birth", "family"],
        "support_houses": [1, 2, 5, 9, 11]
    },
    "Career Success / Wealth": {
        "kws": ["king", "wealth", "business", "commander", "glory", "property", "gains", "profits", "sovereignty", "headship", "recognition"],
        "support_houses": [1, 2, 9, 10, 11]
    },
    "Accident / Injury / Distress": {
        "kws": ["wound", "fire", "weapon", "accident", "distress", "danger", "thieves", "imprisonment", "jail", "snakes", "poison"],
        "support_houses": [3, 6, 8, 12] # In this case, negative houses SUPPORT the occurrence of the negative event
    },
    "Illness / Disease": {
        "kws": ["fever", "disease", "dysentery", "urinary", "health", "rheumatism", "leprosy", "blood", "stomach", "pain", "ailment"],
        "support_houses": [6, 8, 12]
    }
}

# ==============================================================================
# PURE MATHEMATICAL CORE
# ==============================================================================

def calculate_vimshottari_engine(moon_lon, start_datetime):
    nak_len = 13.33333333
    moon_nak = moon_lon / nak_len
    nak_idx = int(moon_nak)
    fraction_elapsed = moon_nak - nak_idx
    fraction_left = 1.0 - fraction_elapsed
    
    start_lord_idx = nak_idx % 9
    first_lord = VIM_DASHA_LORDS[start_lord_idx]
    first_lord_total = VIM_DASHA_YEARS[first_lord]
    first_lord_rem = first_lord_total * fraction_left

    timeline = []
    current_dt = start_datetime
    
    for i in range(9):
        lord_idx = (start_lord_idx + i) % 9
        lord = VIM_DASHA_LORDS[lord_idx]
        lord_years = VIM_DASHA_YEARS[lord] if i > 0 else first_lord_rem
        end_dt = current_dt + datetime.timedelta(days=lord_years * 365.2425)
        
        antardashas = []
        sub_current_dt = current_dt
        for j in range(9):
            sub_lord_idx = (lord_idx + j) % 9
            sub_lord = VIM_DASHA_LORDS[sub_lord_idx]
            sub_years = (VIM_DASHA_YEARS[lord] * VIM_DASHA_YEARS[sub_lord]) / 120.0
            sub_end_dt = sub_current_dt + datetime.timedelta(days=sub_years * 365.2425)
            
            effects = advanced_dasha_results.VIM_ANTAR_EFFECTS.get(lord, {}).get(sub_lord, {})
            antardashas.append({
                "sub_lord": sub_lord,
                "start": sub_current_dt,
                "end": sub_end_dt,
                "effect": effects.get("effect", ""),
                "weak": effects.get("weak", ""),
                "remedy": effects.get("remedy", "")
            })
            sub_current_dt = sub_end_dt

        timeline.append({
            "lord": lord,
            "start": current_dt,
            "end": end_dt,
            "general_fav": advanced_dasha_results.MAHADASHA_GENERAL.get(lord, {}).get("favorable", ""),
            "general_unfav": advanced_dasha_results.MAHADASHA_GENERAL.get(lord, {}).get("unfavorable", ""),
            "antardashas": antardashas
        })
        current_dt = end_dt

    return timeline

def calculate_yogini_engine(moon_lon, start_datetime):
    nak_len = 13.33333333
    nak_num = int(moon_lon / nak_len) + 1
    rem = (nak_num + 3) % 8
    start_deity_idx = rem if rem != 0 else 8
    
    timeline = []
    current_dt = start_datetime
    
    for cycle in range(2):
        for i in range(8):
            deity_idx = start_deity_idx + i
            if deity_idx > 8: deity_idx -= 8
            
            deity_name, deity_years = YOGINI_DEITIES[deity_idx]
            end_dt = current_dt + datetime.timedelta(days=deity_years * 365.2425)
            timeline.append({
                "deity": deity_name,
                "years": deity_years,
                "start": current_dt,
                "end": end_dt
            })
            current_dt = end_dt
    return timeline

# ==============================================================================
# REVERSE DASHA SEARCH LOGIC
# ==============================================================================

def get_sidereal_sign(jd, planet_name):
    """Calculates the sidereal sign (1-12) of a planet for Dasha-Lagna validation"""
    if planet_name == "Ketu":
        lon = (swe.calc_ut(jd, swe.MEAN_NODE)[0][0] + 180) % 360
    else:
        lon = swe.calc_ut(jd, SWE_PLANET_MAP[planet_name])[0][0]
    
    aya = swe.get_ayanamsa_ut(jd)
    sid_lon = (lon - aya) % 360
    return int(sid_lon / 30) + 1

class ReverseDashaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reverse Dasha Search (Birth Date Finder)")
        self.resize(1000, 700)
        self.setStyleSheet("background-color: #F8FAFC; color: #0F172A;")
        
        layout = QVBoxLayout(self)
        
        # --- Input Section ---
        input_group = QGroupBox("Target Events & Approximate Age")
        input_layout = QGridLayout(input_group)
        
        input_layout.addWidget(QLabel("Approximate Age in Current Year:"), 0, 0)
        self.age_spin = QSpinBox()
        self.age_spin.setRange(1, 120)
        self.age_spin.setValue(30)
        input_layout.addWidget(self.age_spin, 0, 1)

        self.events_ui = []
        for i in range(3):
            cat_combo = QComboBox()
            cat_combo.addItems(EVENT_CATEGORIES.keys())
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate.currentDate().addYears(-(i*2))) # Just some defaults
            
            input_layout.addWidget(QLabel(f"Event {i+1} Category:"), i+1, 0)
            input_layout.addWidget(cat_combo, i+1, 1)
            input_layout.addWidget(QLabel("Date of Occurrence:"), i+1, 2)
            input_layout.addWidget(date_edit, i+1, 3)
            
            self.events_ui.append((cat_combo, date_edit))
            
        layout.addWidget(input_group)
        
        # --- Controls ---
        self.btn_search = QPushButton("Scan Timeline for Possible Birth Dates")
        self.btn_search.setStyleSheet("QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 10px; }")
        self.btn_search.clicked.connect(self.run_search)
        layout.addWidget(self.btn_search)
        
        self.lbl_status = QLabel("Ready to search. This will scan 365 possible days...")
        layout.addWidget(self.lbl_status)
        
        # --- Results Table ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Possible Birth Date", "Event 1 Match", "Event 2 Match", "Event 3 Match", "Confidence Score"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.setAlternatingRowColors(True)
        layout.addWidget(self.results_table)

    def run_search(self):
        self.btn_search.setEnabled(False)
        self.lbl_status.setText("Scanning all possibilities... Please wait.")
        QApplication.processEvents() # Force UI update before heavy loop
        
        target_year = datetime.datetime.now().year - self.age_spin.value()
        start_date = datetime.datetime(target_year, 1, 1, 12, 0)
        end_date = datetime.datetime(target_year, 12, 31, 12, 0)
        
        events_data = []
        for combo, dedit in self.events_ui:
            events_data.append({
                "cat": combo.currentText(),
                "date": dedit.date().toPyDate()
            })
            
        swe.set_ephe_path('') 
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        
        results = []
        curr_date = start_date
        
        # Scan every day of the target year
        while curr_date <= end_date:
            jd = swe.julday(curr_date.year, curr_date.month, curr_date.day, 12.0)
            moon_lon = swe.calc_ut(jd, swe.MOON)[0][0]
            aya = swe.get_ayanamsa_ut(jd)
            moon_sid_lon = (moon_lon - aya) % 360
            
            timeline = calculate_vimshottari_engine(moon_sid_lon, curr_date)
            
            total_score = 0
            day_matches = []
            
            for ev in events_data:
                ev_date = ev["date"]
                ev_cat = ev["cat"]
                rules = EVENT_CATEGORIES[ev_cat]
                
                active_md = None
                active_ad = None
                
                for md in timeline:
                    if md['start'].date() <= ev_date <= md['end'].date():
                        active_md = md
                        for ad in md['antardashas']:
                            if ad['start'].date() <= ev_date <= ad['end'].date():
                                active_ad = ad
                                break
                        break
                
                if active_md and active_ad:
                    md_lord = active_md['lord']
                    ad_lord = active_ad['sub_lord']
                    
                    # 1. Classical Text Keyword Match
                    text_to_search = (active_ad['effect'] + " " + active_ad['weak']).lower()
                    matched_kws = [kw for kw in rules["kws"] if kw.lower() in text_to_search]
                    
                    # 2. Dasha Lagna Validation (Set MD as Lagna, check AD house)
                    md_sign = get_sidereal_sign(jd, md_lord)
                    ad_sign = get_sidereal_sign(jd, ad_lord)
                    relative_house = (ad_sign - md_sign) % 12 + 1
                    
                    event_score = 0
                    if matched_kws:
                        event_score += 2
                    if relative_house in rules["support_houses"]:
                        event_score += 3 # High weight for astronomical validation
                        
                    total_score += event_score
                    
                    match_str = f"MD:{md_lord} AD:{ad_lord} | Score: {event_score}"
                    day_matches.append(match_str)
                else:
                    day_matches.append("Out of bounds")

            # Only add if it's a strongly plausible date
            if total_score >= 8: 
                results.append((curr_date, day_matches, total_score))
                
            curr_date += datetime.timedelta(days=1)
            
        # Sort by confidence score
        results.sort(key=lambda x: x[2], reverse=True)
        
        self.results_table.setRowCount(0)
        for row_idx, (c_date, matches, score) in enumerate(results):
            self.results_table.insertRow(row_idx)
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(c_date.strftime("%Y-%b-%d")))
            self.results_table.setItem(row_idx, 1, QTableWidgetItem(matches[0]))
            self.results_table.setItem(row_idx, 2, QTableWidgetItem(matches[1]))
            self.results_table.setItem(row_idx, 3, QTableWidgetItem(matches[2]))
            
            score_item = QTableWidgetItem(str(score))
            score_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            if score >= 12:
                score_item.setForeground(QColor("#16A34A")) # High confidence Green
            self.results_table.setItem(row_idx, 4, score_item)
            
        self.lbl_status.setText(f"Search complete. Found {len(results)} possible dates based on classical texts and Dasha Lagna.")
        self.btn_search.setEnabled(True)

# ==============================================================================
# UI PRESENTATION LAYER (Viewer & Setup)
# ==============================================================================

class AdvancedDashaDialog(QDialog):
    def __init__(self, vim_data, yog_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Classical Dasha Analysis (Deep Effects)")
        self.resize(900, 600)
        self.setStyleSheet("background-color: #F8FAFC; color: #0F172A;")
        
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.setStyleSheet("QTabBar::tab { padding: 10px; font-weight: bold; }")
        
        vim_tab = QWidget()
        vim_layout = QVBoxLayout(vim_tab)
        self.vim_tree = QTreeWidget()
        self.vim_tree.setHeaderLabels(["Timeline / Lord", "Start Date", "End Date", "Classical Effects / Remedies"])
        self.vim_tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.vim_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.vim_tree.setAlternatingRowColors(True)
        
        for maha in vim_data:
            m_item = QTreeWidgetItem(self.vim_tree, [
                f"{maha['lord']} Mahadasha", 
                maha['start'].strftime("%d-%b-%Y"), 
                maha['end'].strftime("%d-%b-%Y"),
                f"Fav: {maha['general_fav'][:60]}..."
            ])
            m_item.setBackground(0, QColor("#E2E8F0"))
            font = m_item.font(0)
            font.setBold(True)
            m_item.setFont(0, font)
            
            for ant in maha['antardashas']:
                a_item = QTreeWidgetItem(m_item, [
                    f"  ↳ {ant['sub_lord']} Antar", 
                    ant['start'].strftime("%d-%b-%Y"), 
                    ant['end'].strftime("%d-%b-%Y"),
                    f"Result: {ant['effect']}"
                ])
                if ant['remedy']:
                    r_item = QTreeWidgetItem(a_item, ["", "", "", f"Remedy: {ant['remedy']}"])
                    r_item.setForeground(3, QColor("#16A34A"))
                if ant['weak']:
                    w_item = QTreeWidgetItem(a_item, ["", "", "", f"If Weak: {ant['weak']}"])
                    w_item.setForeground(3, QColor("#DC2626"))

        vim_layout.addWidget(self.vim_tree)
        tabs.addTab(vim_tab, "Deep Vimshottari")
        
        yog_tab = QWidget()
        yog_layout = QVBoxLayout(yog_tab)
        self.yog_tree = QTreeWidget()
        self.yog_tree.setHeaderLabels(["Deity (Yogini)", "Duration", "Start Date", "End Date"])
        self.yog_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        for y in yog_data:
            QTreeWidgetItem(self.yog_tree, [
                y['deity'], f"{y['years']} Years",
                y['start'].strftime("%d-%b-%Y"), y['end'].strftime("%d-%b-%Y")
            ])
            
        yog_layout.addWidget(self.yog_tree)
        tabs.addTab(yog_tab, "Yogini Dasha")

        layout.addWidget(tabs)

# ==============================================================================
# UI INJECTION (Follows requested setup_ui pattern)
# ==============================================================================

def setup_ui(app, layout):
    """
    Sets up the UI exactly as requested, injecting the Advanced Reverse Dasha Search
    under the specified shared group format.
    """
    shared_group_id = "AdvancedAstroGroup"
    
    shared_group = None
    for i in range(layout.count()):
        w = layout.itemAt(i).widget()
        if w and w.objectName() == shared_group_id:
            shared_group = w
            break
            
    if not shared_group:
        shared_group = QGroupBox("Advanced Analysis")
        shared_group.setObjectName(shared_group_id)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(6, 6, 6, 6)
        group_layout.setSpacing(6)
        shared_group.setLayout(group_layout)
        layout.addWidget(shared_group)
        
    target_layout = shared_group.layout()

    # --- 1. Separator Line ---
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #dcdde1; margin-top: 4px; margin-bottom: 4px;")
    target_layout.addWidget(line)

    # --- 2. Title Label ---
    lbl_title = QLabel("Reverse Dasha Search")
    lbl_title.setStyleSheet("color: #0284C7; font-weight: bold; font-size: 15px; margin-top: 4px;")
    target_layout.addWidget(lbl_title)
    
    lbl_name = "reverse_dasha_lbl_active"
    btn_name = "reverse_dasha_btn_active"
    
    # --- 3. Summary Box ---
    summary_lbl = QLabel("<i>Enter 3 life events to reverse-calculate precise dates. Validates via Dasha Lagna rules.</i>")
    summary_lbl.setObjectName(lbl_name)
    summary_lbl.setStyleSheet("background-color: #fdfefe; border: 1px solid #dcdde1; border-radius: 4px; padding: 6px; font-family: monospace;")
    summary_lbl.setWordWrap(True)
    target_layout.addWidget(summary_lbl)

    # --- 4. Launch Button ---
    btn_details = QPushButton("Find Birth Date from Events")
    btn_details.setObjectName(btn_name)
    btn_details.setStyleSheet("""
        QPushButton { background-color: #34495e; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }
        QPushButton:hover { background-color: #0284C7; }
    """)
    target_layout.addWidget(btn_details)

    def show_reverse_search_details():
        if not hasattr(app, '_reverse_dasha_dialog'):
            app._reverse_dasha_dialog = ReverseDashaDialog(app)
        app._reverse_dasha_dialog.show()
        app._reverse_dasha_dialog.raise_()

    btn_details.clicked.connect(show_reverse_search_details)

def init_ui(layout):
    """
    Standard entry point for dynamic modules. Calls the precise setup_ui 
    and adds the standard chart viewer below it.
    """
    app = QApplication.instance()
    
    # 1. First inject the Reverse Search UI block
    setup_ui(app, layout)
    
    # 2. Proceed with standard Dasha Viewer initialization below it
    current_ui_id = id(layout)
    if hasattr(app, '_adv_dasha_active_ui_id') and app._adv_dasha_active_ui_id == current_ui_id:
        return
    app._adv_dasha_active_ui_id = current_ui_id

    group = QGroupBox("Current Chart Dashas")
    v_layout = QVBoxLayout()
    
    status_label = QLabel("<i>Awaiting chart calculation...</i>")
    status_label.setWordWrap(True)
    
    btn_show = QPushButton("View Comprehensive Dashas")
    btn_show.setEnabled(False)
    btn_show.setMinimumHeight(35)
    btn_show.setStyleSheet("QPushButton { font-weight: bold; }")
    
    v_layout.addWidget(status_label)
    v_layout.addWidget(btn_show)
    group.setLayout(v_layout)
    layout.addWidget(group)

    retry_timer = QTimer()
    retry_timer.setSingleShot(True)

    def run_computation():
        if not hasattr(app, 'current_base_chart') or not app.current_base_chart:
            retry_timer.start(1000)
            return
            
        try:
            moon_p = next((p for p in app.current_base_chart.get("planets", []) if p["name"] == "Moon"), None)
            if not moon_p:
                status_label.setText("Error: Moon not found in chart.")
                return
                
            moon_lon = moon_p["lon"]
            dt_dict = app.time_ctrl.current_time
            start_dt = datetime.datetime(
                dt_dict['year'], dt_dict['month'], dt_dict['day'],
                dt_dict['hour'], dt_dict['minute']
            )
            
            app._adv_vim_data = calculate_vimshottari_engine(moon_lon, start_dt)
            app._adv_yog_data = calculate_yogini_engine(moon_lon, start_dt)
            
            curr_maha = app._adv_vim_data[0]['lord']
            curr_yog = app._adv_yog_data[0]['deity']
            status_label.setText(f"<b>Active:</b> {curr_maha} (Vim), {curr_yog} (Yogini)")
            btn_show.setEnabled(True)
            
            if hasattr(app, '_adv_dasha_dialog') and app._adv_dasha_dialog.isVisible():
                app._adv_dasha_dialog.close()
                show_details()
                
        except Exception as e:
            error_print(f"Advanced Dasha Calculation Error: {e}")
            status_label.setText("<i>Calculation Error. Retrying...</i>")
            retry_timer.start(1500)

    retry_timer.timeout.connect(run_computation)

    def auto_trigger(*args, **kwargs):
        if getattr(app, '_adv_dasha_active_ui_id', None) == current_ui_id:
            retry_timer.start(0)

    if hasattr(app, 'calc_worker'):
        app.calc_worker.calc_finished.connect(auto_trigger)

    def show_details():
        if hasattr(app, '_adv_vim_data') and hasattr(app, '_adv_yog_data'):
            app._adv_dasha_dialog = AdvancedDashaDialog(app._adv_vim_data, app._adv_yog_data, app)
            app._adv_dasha_dialog.exec()
            
    btn_show.clicked.connect(show_details)
    retry_timer.start(500)