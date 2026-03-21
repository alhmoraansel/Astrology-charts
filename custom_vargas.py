# custom_vargas.py

import json, os, sys, traceback
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget,QLineEdit, QSpinBox, QComboBox, QPushButton, QMessageBox, QFrame, QTabWidget, QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView,QCheckBox, QAbstractItemView, QApplication, QScrollArea)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

# ==========================================
# GLOBAL ERROR CATCHER FOR DEBUGGING
# ==========================================
def global_exception_handler(exc_type, exc_value, exc_traceback):
    """Intercepts unhandled PyQt crashes and shows the exact line number/error."""
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print(error_msg)  # Print to console as backup
    
    if QApplication.instance():
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Critical Crash Details")
        msg_box.setText("An unhandled exception occurred.\nClick 'Show Details...' to see exactly what went wrong.")
        msg_box.setDetailedText(error_msg)
        msg_box.setStyleSheet("QMessageBox { background-color: #F8F9FA; font-family: 'Segoe UI'; font-size: 11px; }")
        msg_box.exec()

# Attach the hook globally
sys.excepthook = global_exception_handler


CUSTOM_FILE = "custom_vargas.json"

# Definition of the classical Vargas to complete the standard 20 using the new advanced logic engine
STANDARD_EXTRA_VARGAS = {
    "D3": {"name": "D3 (Drekkana)", "divs": 3, "is_cyclical": False, "base_map": "sign", "start_from": "1st_5th_9th_mfd", "reverse_even": False, "progression": "trinal"},
    "D5": {"name": "D5 (Panchamsha)", "divs": 5, "is_cyclical": False, "base_map": "sign", "start_from": "base", "reverse_even": False},
    "D6": {"name": "D6 (Shashthamsha)", "divs": 6, "is_cyclical": False, "base_map": "sign", "start_from": "base", "reverse_even": False},
    "D8": {"name": "D8 (Ashtamsha)", "divs": 8, "is_cyclical": False, "base_map": "aries", "start_from": "1st_9th", "reverse_even": False},
    "D11": {"name": "D11 (Rudramsha)", "divs": 11, "is_cyclical": False, "base_map": "aries", "start_from": "1st_7th", "reverse_even": True},
    "D27": {"name": "D27 (Bhamsha)", "divs": 27, "is_cyclical": False, "base_map": "aries", "start_from": "1st_4th_7th_10th_feaw", "reverse_even": False},
    "D40": {"name": "D40 (Khavedamsha)", "divs": 40, "is_cyclical": False, "base_map": "aries", "start_from": "1st_7th", "reverse_even": False},
    "D45": {"name": "D45 (Akshavedamsha)", "divs": 45, "is_cyclical": False, "base_map": "sign", "start_from": "1st_9th", "reverse_even": False}
}

# Used to populate sub-divisional dropdowns
ALL_STANDARD_CHARTS = [
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", 
    "D11", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"
]

def load_custom_rules():
    """Loads user-created custom varga rules from the local JSON file securely."""
    rules = {}
    if os.path.exists(CUSTOM_FILE):
        try:
            with open(CUSTOM_FILE, "r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    rules = data
        except Exception as e:
            print(f"Error loading custom vargas: {e}")
    return rules

def get_all_extra_vargas():
    """Returns a combined dictionary of standard extra vargas + user custom vargas."""
    res = {k: v.get("name", k) for k, v in STANDARD_EXTRA_VARGAS.items()}
    for k, v in load_custom_rules().items():
        if isinstance(v, dict):
            res[k] = v.get("name", str(k))
    return res

def get_varga_rule(div_id):
    if div_id in STANDARD_EXTRA_VARGAS:
        return STANDARD_EXTRA_VARGAS[div_id]
    customs = load_custom_rules()
    return customs.get(div_id)

def calculate_new_sign(sign_idx, deg_in_sign, rule):
    """
    Applies rigorous classical Vedic astrological calculations. 
    Handles both explicit legacy logic and advanced Parametric JH math.
    """
    divs = max(1, int(rule.get("divs", 1))) # Prevent Division by Zero
    sign_idx = int(sign_idx) # Enforce integer logic for Modulo math
    
    part_size = 30.0 / divs
    part_num = int(deg_in_sign // part_size)
    if part_num >= divs: part_num = divs - 1

    # --- 1. LEGACY LOGIC ESCAPE HATCH ---
    # Guarantees old charts created with explicit logic never break
    logic = rule.get("logic", "")
    if logic:
        if logic == "parashari_trine":
            if part_num % 3 == 0: return sign_idx
            elif part_num % 3 == 1: return (sign_idx + 4) % 12
            else: return (sign_idx + 8) % 12
        elif logic == "cyclical_same":
            return (sign_idx + part_num) % 12
        elif logic == "parivritti_traya":
            return ((sign_idx * divs) + part_num) % 12
        elif logic == "navamsha_elements":
            element = sign_idx % 4
            start_sign = {0:0, 1:9, 2:6, 3:3}[element]
            return (start_sign + part_num) % 12
        elif logic == "dashamsha_odd_even":
            start_sign = sign_idx if sign_idx % 2 == 0 else (sign_idx + 8) % 12
            return (start_sign + part_num) % 12
        elif logic == "odd_aries_even_libra":
            start_sign = 0 if sign_idx % 2 == 0 else 6
            return (start_sign + part_num) % 12
        elif logic == "odd_aries_even_sag":
            start_sign = 0 if sign_idx % 2 == 0 else 8
            return (start_sign + part_num) % 12

    # --- 2. ADVANCED JH MATHEMATICS ---
    # 2a. Cyclical Option Override
    if rule.get("is_cyclical", False):
        total_parts_from_aries = (sign_idx * divs) + part_num
        return total_parts_from_aries % 12

    # 2b. Non-Cyclical Configuration
    base_map = rule.get("base_map", "sign")
    start_from = rule.get("start_from", "base")
    reverse_even = rule.get("reverse_even", False)
    
    base_sign = sign_idx if base_map == "sign" else 0
    is_odd_sign = (sign_idx % 2 == 0) # Aries(0) is Odd, Taurus(1) is Even
    
    mod = sign_idx % 3
    elem = sign_idx % 4

    # Determine Starting Sign
    if start_from == "base":
        start_sign = base_sign
    elif start_from == "1st_7th":
        start_sign = base_sign if is_odd_sign else (base_sign + 6) % 12
    elif start_from == "1st_9th":
        start_sign = base_sign if is_odd_sign else (base_sign + 8) % 12
    elif start_from == "1st_5th":
        start_sign = base_sign if is_odd_sign else (base_sign + 4) % 12
    elif start_from == "1st_11th":
        start_sign = base_sign if is_odd_sign else (base_sign + 10) % 12
    elif start_from == "1st_3rd":
        start_sign = base_sign if is_odd_sign else (base_sign + 2) % 12
    elif start_from == "1st_5th_9th_mfd":
        offset = 0 if mod == 0 else (4 if mod == 1 else 8)
        start_sign = (base_sign + offset) % 12
    elif start_from == "1st_9th_5th_mfd":
        offset = 0 if mod == 0 else (8 if mod == 1 else 4)
        start_sign = (base_sign + offset) % 12
    elif start_from == "1st_4th_7th_10th_feaw":
        offset = 0 if elem == 0 else (3 if elem == 1 else (6 if elem == 2 else 9))
        start_sign = (base_sign + offset) % 12
    elif start_from == "1st_10th_7th_4th_feaw":
        offset = 0 if elem == 0 else (9 if elem == 1 else (6 if elem == 2 else 3))
        start_sign = (base_sign + offset) % 12
    else:
        start_sign = base_sign

    # Even Sign Rule Reversal
    if reverse_even and not is_odd_sign:
        effective_part = divs - 1 - part_num
    else:
        effective_part = part_num

    # Progression
    if rule.get("progression") == "trinal":
        offset = (effective_part % 3) * 4
        return (start_sign + offset) % 12

    return (start_sign + effective_part) % 12


def compute_divisional_chart(base_chart, div_id):
    """Computes the complete structural chart for a custom/extra division securely."""
    rule = get_varga_rule(div_id)
    if not rule or not isinstance(base_chart, dict): 
        return base_chart
        
    if "ascendant" not in base_chart or "planets" not in base_chart:
        return base_chart

    # --- SUB-DIVISION RECURSIVE ROUTING ---
    if rule.get("is_subdiv"):
        # Anti-Recursion Safety Lock to prevent Infinite Exception Crashes
        b_varga = rule.get("base_varga", "D1")
        a_varga = rule.get("applied_varga", "D1")
        if b_varga == div_id or a_varga == div_id:
            print(f"Warning: Cyclic reference blocked in {div_id}. Returning base chart.")
            return base_chart
            
        try:
            import astro_engine
            engine = astro_engine.EphemerisEngine()
            # Inject customs so engine can recursively evaluate
            engine.set_custom_vargas(load_custom_rules())
            
            # Level 1 Generation
            chart_level_1 = engine.compute_divisional_chart(base_chart, b_varga)
            # Level 2 Generation
            chart_level_2 = engine.compute_divisional_chart(chart_level_1, a_varga)
            
            return chart_level_2
        except ImportError:
            print("astro_engine not found, falling back to base chart.")
            return base_chart

    # --- STANDARD VARGA COMPUTATION ---
    divs = max(1, int(rule.get("divs", 1)))
    part_size = 30.0 / divs

    asc = base_chart.get("ascendant", {})
    new_asc_sign = calculate_new_sign(asc.get("sign_index", 0), asc.get("degree", 0.0) % 30, rule)
    
    # Preserve precise degree fraction inside the new divisional sign
    new_asc_deg = ((asc.get("degree", 0.0) % 30) % part_size) * divs
    
    new_asc = {
        "sign_index": new_asc_sign,
        "sign_num": new_asc_sign + 1,
        "degree": new_asc_deg,
        "div_lon": new_asc_sign * 30.0 + new_asc_deg,
        "vargottama": (new_asc_sign == asc.get("sign_index", 0))
    }

    new_planets = []
    exaltation_rules = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
    debilitation_rules = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
    sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}
    planet_lordships = {"Sun": [5], "Moon": [4], "Mars": [1, 8], "Mercury": [3, 6], "Jupiter": [9, 12], "Venus": [2, 7], "Saturn": [10, 11], "Rahu": [], "Ketu": []}

    for p in base_chart.get("planets", []):
        p_name = p.get("name", "Unknown")
        p_deg = p.get("deg_in_sign", 15.0)
        new_sign_idx = calculate_new_sign(p.get("sign_index", 0), p_deg, rule)
        new_sign_num = new_sign_idx + 1
        new_deg_in_sign = (p_deg % part_size) * divs

        is_exalted = False
        is_own = (sign_rulers.get(new_sign_num) == p_name)
        is_debilitated = (new_sign_num == debilitation_rules.get(p_name))

        if p_name == "Moon" and new_sign_num == 2:
            is_own = True; is_exalted = False
        elif p_name == "Mercury" and new_sign_num == 6:
            is_exalted = True; is_own = False
        else:
            is_exalted = (new_sign_num == exaltation_rules.get(p_name))

        if p_name == "Moon" and new_sign_num == 8: is_debilitated = False
        elif p_name == "Mercury" and new_sign_num == 12: is_debilitated = True

        new_house = ((new_sign_idx - new_asc_sign) % 12) + 1

        new_p = dict(p)
        new_p.update({
            "sign_index": new_sign_idx,
            "sign_num": new_sign_num,
            "deg_in_sign": new_deg_in_sign,
            "div_lon": new_sign_idx * 30.0 + new_deg_in_sign,
            "house": new_house,
            "exalted": is_exalted,
            "debilitated": is_debilitated,
            "own_sign": is_own,
            "vargottama": (new_sign_idx == p.get("sign_index", -1)),
            "lord_of": planet_lordships.get(p_name, [])
        })
        new_planets.append(new_p)

    return {
        "ascendant": new_asc,
        "planets": new_planets,
        "aspects": base_chart.get("aspects", [])
    }


# ==========================================
# UI COMPONENTS
# ==========================================
class CustomVargaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Varga Construction (requires restart)")
        self.resize(550, 500)  # Reduced size to be more compact
        
        self.setStyleSheet("""
            QDialog { background-color: #F8F9FA; font-family: 'Segoe UI'; font-size: 11px; }
            QLineEdit, QSpinBox, QComboBox { padding: 4px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFF; color: #333; }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #3B82F6; }
            QComboBox QAbstractItemView { background-color: #FFF; color: #333; selection-background-color: #E2E8F0; selection-color: #000; }
            QTabWidget::pane { border: 1px solid #CBD5E1; border-radius: 4px; background: white; }
            QTabBar::tab { background: #E2E8F0; color: #475569; padding: 4px 8px; border-top-left-radius: 4px; border-top-right-radius: 4px; margin-right: 2px; }
            QTabBar::tab:selected { background: #FFF; color: #0F172A; font-weight: bold; border-bottom: 2px solid #3B82F6; }
            QPushButton { padding: 4px 8px; font-weight: bold; border-radius: 4px; }
            QPushButton#saveBtn { background-color: #10B981; color: white; border: none; }
            QPushButton#saveBtn:hover { background-color: #059669; }
            QPushButton#delBtn { background-color: #EF4444; color: white; border: none; }
            QPushButton#delBtn:hover { background-color: #DC2626; }
            QPushButton#closeBtn { background-color: #E2E8F0; color: #333; border: 1px solid #CBD5E1; }
            QPushButton#closeBtn:hover { background-color: #CBD5E1; }
            QTableWidget { background-color: #FFF; border: 1px solid #CBD5E1; border-radius: 4px; gridline-color: #F1F5F9; font-size: 11px; }
            QHeaderView::section { background-color: #F8F9FA; padding: 4px; border: none; border-bottom: 1px solid #CBD5E1; font-weight: bold; color: #475569; font-size: 11px; }
            QCheckBox { font-size: 11px; font-weight: bold; }
        """)
        
        try:
            main_layout = QVBoxLayout(self)
            self.tabs = QTabWidget()
            
            # Initialize all tabs
            self._init_legacy_tab()
            self._init_jh_tab()
            self._init_sub_varga_tab()
            self._init_manage_tab()
            
            main_layout.addWidget(self.tabs)
            
            # Default to Legacy Tab
            self.tabs.setCurrentIndex(0)

            # Bottom Bar
            btn_box = QHBoxLayout()
            cancel_btn = QPushButton("Close")
            cancel_btn.setObjectName("closeBtn")
            cancel_btn.clicked.connect(self.reject)
            btn_box.addStretch()
            btn_box.addWidget(cancel_btn)
            main_layout.addLayout(btn_box)
            
            self._refresh_table()
        except Exception as e:
            QMessageBox.critical(self, "UI Init Error", f"Failed to build UI: {str(e)}")

    def _init_legacy_tab(self):
        """Standard, easy-to-use legacy options."""
        self.tab_legacy = QWidget()
        main_tab_layout = QVBoxLayout(self.tab_legacy)
        main_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        
        header_lbl = QLabel("Create a simple, classical custom divisional chart using standard presets.")
        header_lbl.setStyleSheet("color: #64748B; margin-bottom: 8px;")
        layout.addWidget(header_lbl)
        
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        
        self.legacy_id_input = QLineEdit("D144")
        self.legacy_name_input = QLineEdit("My Standard Varga")
        self.legacy_divs_spin = QSpinBox()
        self.legacy_divs_spin.setRange(2, 1000)
        self.legacy_divs_spin.setValue(144)

        self.legacy_logic_cb = QComboBox()
        self.legacy_logic_mapping = {
            "Parivritti Traya (Continuous from Aries)": "parivritti_traya",
            "Parashari Trine (1st, 5th, 9th)": "parashari_trine",
            "Cyclical (Start from self)": "cyclical_same",
            "Tattva / Element Pattern (Standard D9)": "navamsha_elements",
            "Odd/Even 9th Modality (Standard D10)": "dashamsha_odd_even",
            "Odd->Aries, Even->Libra (Standard D40)": "odd_aries_even_libra",
            "Odd->Aries, Even->Sagittarius (Standard D60)": "odd_aries_even_sag"
        }
        for ui_text in self.legacy_logic_mapping.keys():
            self.legacy_logic_cb.addItem(ui_text)

        form_layout.addRow("<b>Varga Identifier:</b>", self.legacy_id_input)
        form_layout.addRow("<b>Display Name:</b>", self.legacy_name_input)
        form_layout.addRow("<b>Divisions (Parts):</b>", self.legacy_divs_spin)
        form_layout.addRow("<b>Algorithmic Logic:</b>", self.legacy_logic_cb)

        layout.addLayout(form_layout)
        layout.addStretch()

        save_btn = QPushButton("Save Legacy Chart")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_legacy_custom)
        layout.addWidget(save_btn)
        
        scroll.setWidget(content_widget)
        main_tab_layout.addWidget(scroll)
        self.tabs.addTab(self.tab_legacy, "Legacy Options")

    def _init_jh_tab(self):
        """Advanced JH-style parametric configuration."""
        self.tab_jh = QWidget()
        main_tab_layout = QVBoxLayout(self.tab_jh)
        main_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        create_layout = QVBoxLayout(content_widget)
        
        # Warning Label explicitly stating difference from JHora
        warn_lbl = QLabel("<b>⚠️ Note:</b> These advanced mathematical mappings attempt to replicate Jagannatha Hora (JHora) logic but may differ from JHora. Verify manually.")
        warn_lbl.setWordWrap(True)
        warn_lbl.setStyleSheet("color: #D97706; background-color: #FEF3C7; padding: 6px; border: 1px solid #F59E0B; border-radius: 4px; margin-bottom: 8px;")
        create_layout.addWidget(warn_lbl)

        # --- PRESETS ---
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("<b>Load Parametric Preset:</b>"))
        self.preset_cb = QComboBox()
        self.preset_cb.addItems([
            "-- Select a Custom Varga Preset --",
            "Parivritti Traya (Cyclical) D12",
            "Parashari Navamsha (D9)",
            "Parashari Dashamsha (D10)",
            "Parashari Shashtiamsha (D60)",
            "Iyer Ekadashamsha (D11)"
        ])
        self.preset_cb.currentIndexChanged.connect(self.apply_preset)
        preset_layout.addWidget(self.preset_cb)
        preset_layout.addStretch()
        create_layout.addLayout(preset_layout)

        line1 = QFrame(); line1.setFrameShape(QFrame.Shape.HLine); line1.setFrameShadow(QFrame.Shadow.Sunken)
        create_layout.addWidget(line1)
        
        # --- BASIC SETTINGS ---
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        
        self.id_input = QLineEdit("D144")
        self.name_input = QLineEdit("My Advanced Varga")
        self.divs_spin = QSpinBox()
        self.divs_spin.setRange(2, 1000)
        self.divs_spin.setValue(144)
        
        form_layout.addRow("<b>Varga Identifier:</b>", self.id_input)
        form_layout.addRow("<b>Display Name:</b>", self.name_input)
        form_layout.addRow("<b>Divisions (Parts):</b>", self.divs_spin)
        create_layout.addLayout(form_layout)
        create_layout.addSpacing(5)

        # --- CYCLICAL OPTION ---
        self.lbl_cyc_title = QLabel("<b>Cyclical Option:</b>")
        create_layout.addWidget(self.lbl_cyc_title)
        
        # Split Checkbox and WordWrapped Label
        self.chk_cyclical = QCheckBox("This is a cyclical (parivritti) chart")
        lbl_cyc_desc = QLabel("Keep going around the zodiac again and again and distribute the first N signs to Ar, next N signs to Ta and so on.")
        lbl_cyc_desc.setWordWrap(True)
        lbl_cyc_desc.setStyleSheet("color: #64748B; margin-left: 20px;")
        
        self.chk_cyclical.stateChanged.connect(self.toggle_cyclical_ui)
        create_layout.addWidget(self.chk_cyclical)
        create_layout.addWidget(lbl_cyc_desc)
        create_layout.addSpacing(5)

        # --- NON-CYCLICAL OPTIONS ---
        self.non_cyclical_widget = QWidget()
        nc_layout = QVBoxLayout(self.non_cyclical_widget)
        nc_layout.setContentsMargins(0,0,0,0)
        
        lbl_note = QLabel("<b>Non-Cyclical Options Note:</b><br><span style='color: #64748B;'>:: The following options are relevant only for non-cyclical charts ::</span>")
        nc_layout.addWidget(lbl_note)
        nc_layout.addSpacing(5)

        # Base Mapping
        lbl_base = QLabel("<b>Base Mapping Option:</b><br>The base for the mapping of N divisions in a sign:")
        lbl_base.setWordWrap(True)
        nc_layout.addWidget(lbl_base)
        self.base_map_cb = QComboBox()
        self.base_map_cb.addItems(["The sign in question", "Aries"])
        nc_layout.addWidget(self.base_map_cb)
        nc_layout.addSpacing(5)

        # Starting Point
        lbl_start = QLabel("<b>Starting Point Option:</b><br>Mapping of divisions starts from:")
        lbl_start.setWordWrap(True)
        nc_layout.addWidget(lbl_start)
        
        # Concise Texts to prevent width stretching
        self.start_from_cb = QComboBox()
        self.start_from_mapping = {
            "The base": "base",
            "1st / 7th from base (Odd / Even sign)": "1st_7th",
            "1st / 9th from base (Odd / Even sign)": "1st_9th",
            "1st / 5th from base (Odd / Even sign)": "1st_5th",
            "1st / 11th from base (Odd / Even sign)": "1st_11th",
            "1st / 3rd from base (Odd / Even sign)": "1st_3rd",
            "1st / 5th / 9th from base (Movable / Fixed / Dual)": "1st_5th_9th_mfd",
            "1st / 9th / 5th from base (Movable / Fixed / Dual)": "1st_9th_5th_mfd",
            "1st / 4th / 7th / 10th from base (Fire / Earth / Air / Water)": "1st_4th_7th_10th_feaw",
            "1st / 10th / 7th / 4th from base (Fire / Earth / Air / Water)": "1st_10th_7th_4th_feaw"
        }
        for k in self.start_from_mapping.keys(): self.start_from_cb.addItem(k)
        nc_layout.addWidget(self.start_from_cb)
        nc_layout.addSpacing(5)

        # Even Sign Rule
        lbl_even = QLabel("<b>Even Sign Rule:</b>")
        nc_layout.addWidget(lbl_even)
        
        # Split Checkbox and WordWrapped Label
        self.chk_even_reverse = QCheckBox("Count N divisions from the end of the sign if the sign is even.")
        lbl_even_desc = QLabel("This, for example, allows the 9 parts of Ar to go to Ar, Ta, ..., Sc, Sg and the 9 parts of Ta to go to Vi, Le, ..., Aq, Cp.")
        lbl_even_desc.setWordWrap(True)
        lbl_even_desc.setStyleSheet("color: #64748B; margin-left: 20px;")
        
        nc_layout.addWidget(self.chk_even_reverse)
        nc_layout.addWidget(lbl_even_desc)

        create_layout.addWidget(self.non_cyclical_widget)
        create_layout.addStretch()

        save_btn = QPushButton("Save Advanced Chart")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_jh_custom)
        create_layout.addWidget(save_btn)
        
        scroll.setWidget(content_widget)
        main_tab_layout.addWidget(scroll)
        self.tabs.addTab(self.tab_jh, "Advanced (JH) ⚠️")

    def _init_sub_varga_tab(self):
        self.tab_subdiv = QWidget()
        main_tab_layout = QVBoxLayout(self.tab_subdiv)
        main_tab_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content_widget = QWidget()
        subdiv_layout = QVBoxLayout(content_widget)
        
        header_lbl = QLabel("Construct a Sub-Divisional chart by recursively mapping one chart onto another (e.g. Sva-Navamsha).")
        header_lbl.setStyleSheet("color: #64748B; margin-bottom: 8px;")
        header_lbl.setWordWrap(True)
        subdiv_layout.addWidget(header_lbl)

        form_layout = QFormLayout()
        form_layout.setSpacing(8)

        self.sub_id_input = QLineEdit("D81")
        self.sub_name_input = QLineEdit("Navamsha of Navamsha")
        
        self.base_varga_cb = QComboBox()
        self.applied_varga_cb = QComboBox()
        
        form_layout.addRow("<b>Sub-Varga Identifier:</b>", self.sub_id_input)
        form_layout.addRow("<b>Display Name:</b>", self.sub_name_input)
        form_layout.addRow("<b>Base Chart:</b>", self.base_varga_cb)
        form_layout.addRow("<b>Applied Varga:</b>", self.applied_varga_cb)

        subdiv_layout.addLayout(form_layout)
        subdiv_layout.addStretch()

        save_btn = QPushButton("Save Sub-Division")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_subdiv_custom)
        subdiv_layout.addWidget(save_btn)
        
        scroll.setWidget(content_widget)
        main_tab_layout.addWidget(scroll)
        self.tabs.addTab(self.tab_subdiv, "Sub-Divisional")

    def _init_manage_tab(self):
        self.tab_manage = QWidget()
        manage_layout = QVBoxLayout(self.tab_manage)
        
        self.varga_table = QTableWidget()
        self.varga_table.setColumnCount(3)
        self.varga_table.setHorizontalHeaderLabels(["ID", "Name", "Details"])
        self.varga_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.varga_table.verticalHeader().setVisible(False)
        
        # Explicit QAbstractItemView properties for safe PyQt6 Enum typing
        self.varga_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.varga_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        manage_layout.addWidget(self.varga_table)
        
        del_btn = QPushButton("Remove Selected Chart")
        del_btn.setObjectName("delBtn")
        del_btn.clicked.connect(self.delete_custom)
        manage_layout.addWidget(del_btn)
        self.tabs.addTab(self.tab_manage, "Manage Library")

    def toggle_cyclical_ui(self):
        self.non_cyclical_widget.setDisabled(self.chk_cyclical.isChecked())
        if self.chk_cyclical.isChecked():
            self.non_cyclical_widget.setStyleSheet("color: #9CA3AF;")
        else:
            self.non_cyclical_widget.setStyleSheet("")

    def apply_preset(self):
        idx = self.preset_cb.currentIndex()
        if idx == 0: return
        
        if idx == 1: # Parivritti Traya (Cyclical) D12
            self.id_input.setText("D12")
            self.name_input.setText("Parivritti Dwadashamsha")
            self.divs_spin.setValue(12)
            self.chk_cyclical.setChecked(True)
        elif idx == 2: # Parashari Navamsha (D9)
            self.id_input.setText("D9")
            self.name_input.setText("Parashari Navamsha")
            self.divs_spin.setValue(9)
            self.chk_cyclical.setChecked(False)
            self.base_map_cb.setCurrentText("Aries")
            self.start_from_cb.setCurrentText("1st / 4th / 7th / 10th from base (Fire / Earth / Air / Water)")
            self.chk_even_reverse.setChecked(False)
        elif idx == 3: # Parashari Dashamsha (D10)
            self.id_input.setText("D10")
            self.name_input.setText("Parashari Dashamsha")
            self.divs_spin.setValue(10)
            self.chk_cyclical.setChecked(False)
            self.base_map_cb.setCurrentText("The sign in question")
            self.start_from_cb.setCurrentText("1st / 9th from base (Odd / Even sign)")
            self.chk_even_reverse.setChecked(False)
        elif idx == 4: # Parashari Shashtiamsha (D60)
            self.id_input.setText("D60")
            self.name_input.setText("Parashari Shashtiamsha")
            self.divs_spin.setValue(60)
            self.chk_cyclical.setChecked(False)
            self.base_map_cb.setCurrentText("The sign in question")
            self.start_from_cb.setCurrentText("The base")
            self.chk_even_reverse.setChecked(False)
        elif idx == 5: # Iyer Ekadashamsha (D11)
            self.id_input.setText("D11")
            self.name_input.setText("Iyer Rudramsha")
            self.divs_spin.setValue(11)
            self.chk_cyclical.setChecked(False)
            self.base_map_cb.setCurrentText("Aries")
            self.start_from_cb.setCurrentText("1st / 7th from base (Odd / Even sign)")
            self.chk_even_reverse.setChecked(True)

    def _refresh_dropdowns(self):
        """Refreshes the base and applied Varga dropdowns with all available options."""
        try:
            self.base_varga_cb.clear()
            self.applied_varga_cb.clear()
            
            all_options = ALL_STANDARD_CHARTS.copy()
            custom_rules = load_custom_rules()
            for k in custom_rules.keys():
                if k not in all_options:
                    all_options.append(k)
                    
            all_options.sort(key=lambda x: int(x[1:]) if x[1:].isdigit() else 999)
            
            self.base_varga_cb.addItems(all_options)
            self.applied_varga_cb.addItems(all_options)
            
            d9_idx = self.base_varga_cb.findText("D9")
            if d9_idx >= 0:
                self.base_varga_cb.setCurrentIndex(d9_idx)
                self.applied_varga_cb.setCurrentIndex(d9_idx)
        except Exception as e:
            print(f"Error in refresh dropdowns: {e}")

    def _refresh_table(self):
        try:
            self._refresh_dropdowns()
            rules = load_custom_rules()
            self.varga_table.setRowCount(len(rules))
            for row, (v_id, data) in enumerate(rules.items()):
                self.varga_table.setItem(row, 0, QTableWidgetItem(str(v_id)))
                self.varga_table.setItem(row, 1, QTableWidgetItem(str(data.get("name", v_id))))
                
                # Dynamic details rendering based on rule type
                if "logic" in data and data["logic"]:
                    logic_key = data["logic"]
                    friendly_start = next((k for k, v in self.legacy_logic_mapping.items() if v == logic_key), logic_key)
                    details = f"Legacy: {friendly_start.split('(')[0].strip()}"
                elif data.get("is_subdiv"):
                    details = f"Sub-Div: {data.get('applied_varga', 'D1')} applied on {data.get('base_varga', 'D1')}"
                elif data.get("is_cyclical"):
                    details = f"JH: Cyclical (Parivritti)"
                else:
                    start_key = data.get("start_from", "base")
                    base_str = "Sign" if data.get("base_map", "sign") == "sign" else "Aries"
                    friendly_start = next((k for k, v in self.start_from_mapping.items() if v == start_key), str(start_key))
                    rev_str = " | Even Rev" if data.get("reverse_even") else ""
                    details = f"JH: Base={base_str} | Start={friendly_start.split('(')[0].strip()}{rev_str}"
                        
                self.varga_table.setItem(row, 2, QTableWidgetItem(details))
        except Exception as e:
            print(f"Error in refresh table: {e}")

    def save_legacy_custom(self):
        try:
            v_id = self.legacy_id_input.text().strip().upper()
            if not v_id:
                QMessageBox.warning(self, "Invalid ID", "Varga ID cannot be empty.")
                return
                
            if not v_id.startswith("D"): v_id = "D" + v_id
            
            rules = load_custom_rules()
            rules[v_id] = {
                "name": f"{v_id} ({self.legacy_name_input.text().strip()})",
                "divs": self.legacy_divs_spin.value(),
                "logic": self.legacy_logic_mapping.get(self.legacy_logic_cb.currentText(), "cyclical_same")
            }
            
            self._commit_save(rules, v_id)
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", str(e))

    def save_jh_custom(self):
        try:
            v_id = self.id_input.text().strip().upper()
            if not v_id:
                QMessageBox.warning(self, "Invalid ID", "Varga ID cannot be empty.")
                return
                
            if not v_id.startswith("D"): v_id = "D" + v_id
            
            rules = load_custom_rules()
            rules[v_id] = {
                "name": f"{v_id} ({self.name_input.text().strip()})",
                "divs": self.divs_spin.value(),
                "is_cyclical": self.chk_cyclical.isChecked(),
                "base_map": "sign" if self.base_map_cb.currentIndex() == 0 else "aries",
                "start_from": self.start_from_mapping.get(self.start_from_cb.currentText(), "base"),
                "reverse_even": self.chk_even_reverse.isChecked(),
                "progression": "continuous",
                "logic": "" # Empty logic ensures JH engine handles it
            }
            
            self._commit_save(rules, v_id)
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", str(e))

    def save_subdiv_custom(self):
        try:
            v_id = self.sub_id_input.text().strip().upper()
            if not v_id:
                QMessageBox.warning(self, "Invalid ID", "Sub-Varga ID cannot be empty.")
                return
                
            if not v_id.startswith("D"): v_id = "D" + v_id
            
            # Explicit protection against Sub-Divisional Cycle Recursion Error
            if self.base_varga_cb.currentText() == v_id or self.applied_varga_cb.currentText() == v_id:
                QMessageBox.warning(self, "Cyclic Reference", "A Sub-Divisional chart cannot map onto itself.")
                return
            
            rules = load_custom_rules()
            rules[v_id] = {
                "name": f"{v_id} ({self.sub_name_input.text().strip()})",
                "is_subdiv": True,
                "base_varga": self.base_varga_cb.currentText(),
                "applied_varga": self.applied_varga_cb.currentText()
            }
            
            self._commit_save(rules, v_id)
        except Exception as e:
            QMessageBox.critical(self, "Validation Error", str(e))

    def _commit_save(self, rules, v_id):
        try:
            with open(CUSTOM_FILE, "w") as f:
                json.dump(rules, f, indent=4)
            self._refresh_table()
            QMessageBox.information(self, "Success", f"Chart {v_id} constructed successfully.\nPlease restart the application to inject it into the main UI.")
            self.tabs.setCurrentIndex(3) # Switch to manage tab
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save rules:\n{str(e)}")

    def delete_custom(self):
        try:
            selected = self.varga_table.selectedItems()
            if not selected:
                QMessageBox.warning(self, "Selection Required", "Please select a custom chart to remove.")
                return
                
            v_id = self.varga_table.item(selected[0].row(), 0).text()
            
            rules = load_custom_rules()
            if v_id in rules:
                del rules[v_id]
                with open(CUSTOM_FILE, "w") as f:
                    json.dump(rules, f, indent=4)
                self._refresh_table()
                QMessageBox.information(self, "Deleted", f"Successfully removed {v_id}.\nPlease restart the application to clean up the UI.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete rule:\n{str(e)}")