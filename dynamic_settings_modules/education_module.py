# dynamic_settings_modules/education_mod.py

import sys
import copy
import json
import os
import datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, 
                             QLabel, QScrollArea, QGroupBox, QTextBrowser, QTabWidget,
                             QMenuBar, QFormLayout, QDoubleSpinBox, QDialogButtonBox, QApplication, QMessageBox, QCheckBox)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QUrl, QTimer

import main
import astro_engine
from chart_renderer import ChartAnalyzer, SIGN_LORDS, ChartRenderer

# Import the Live CSI Helper safely for end-of-analysis diagnostics ONLY
try:
    from dynamic_settings_modules.composite_strength_mod import CSIHelper
except ImportError as e:
    CSIHelper = None

PLUGIN_INDEX = 1


# ==========================================
# GLOBAL DECIDING WEIGHTS & CONSTANTS
# ==========================================

# 1. House & Lord Influences
W_INFLUENCE_OCC_CONJ = 0.4
W_INFLUENCE_ASPECT = 0.4
W_NAKSHATRA_5TH_LORD = 0.1

# 2. Mercury Repetition Rule
W_MERCURY_FACTOR = 0.2  

# 3. Rashi Technicalities
W_TECH_RASHI_4TH = 0.3
W_TECH_RASHI_5TH = 0.6

# 4. Planetary Category Weights
W_TECH_PLANET = 0.5
W_SEMI_TECH_PLANET = 0.5
W_NON_TECH_PLANET = 0.5

# 5. Mahadasha Timing Constants
AGE_OF_EDUCATION = 18.0   
W_MAHADASHA_PLANET = 3.0  

# 6. Chart Toggles (Analysis Selection - MAX 4 ALLOWED)
ANALYZE_D1 = True
ANALYZE_D9 = True
ANALYZE_D24 = True
ANALYZE_D60 = True
ANALYZE_MD = False
ANALYZE_KARAKAMSHA = False

# 7. Varga Multipliers
W_D1_MULTIPLIER = 1.0           
W_D9_MULTIPLIER = 1.0           
W_D24_MULTIPLIER = 1.0
W_D60_MULTIPLIER = 1.0
W_DASHA_LAGNA_MULTIPLIER = 1.0  
W_KARAKAMSHA_MULTIPLIER = 1.0

# 8. Special Rules
W_D24_4TH_HOUSE_WEIGHT = 0.6
W_D24_5TH_HOUSE_WEIGHT = 0.3
W_D1_5TH_LORD_BOOST = 2.0
W_SPECIAL_STATUS_BOOST = 2.0
W_SEMI_TECH_PENALTY = 0.5

# Map for Settings UI configuration
WEIGHTS_MAP = {
    "W_INFLUENCE_OCC_CONJ": ("5th House Occupants / Lord Conjunctions", 0.0, 10.0, 0.1, "Points given to planets sitting in the 5th House or conjunct the 5th House ruler."),
    "W_INFLUENCE_ASPECT": ("5th House / Lord Aspects", 0.0, 10.0, 0.1, "Points given to planets aspecting the 5th House or aspecting the 5th House ruler."),
    "W_NAKSHATRA_5TH_LORD": ("5th Lord's Nakshatra Weight", 0.0, 10.0, 0.1, "Influence level of the constellation (Nakshatra) where the 5th House ruler sits."),
    "W_MERCURY_FACTOR": ("Mercury Rule Weight (fraction of 5H)", 0.0, 2.0, 0.1, "Multiplier for evaluating the '5th House from Mercury' (the natural planet of education)."),
    "W_TECH_RASHI_4TH": ("Technical Rashi (4th House) Weight", 0.0, 10.0, 0.1, "Bonus points if the 4th House (Basic Education) falls in a Technical Zodiac Sign (e.g., Aries, Gemini)."),
    "W_TECH_RASHI_5TH": ("Technical Rashi (5th House) Weight", 0.0, 10.0, 0.1, "Bonus points if the 5th House (Higher Education) falls in a Technical Zodiac Sign."),
    "W_TECH_PLANET": ("Technical Planet Core Multiplier", 0.0, 10.0, 0.1, "Power multiplier for naturally Technical planets (like Mars, Saturn, Rahu)."),
    "W_SEMI_TECH_PLANET": ("Semi-Tech Planet Core Multiplier", 0.0, 10.0, 0.1, "Power multiplier for Semi-Technical planets (like Jupiter, Venus)."),
    "W_NON_TECH_PLANET": ("Non-Tech Planet Core Multiplier", 0.0, 10.0, 0.1, "Power multiplier for Non-Technical planets (like Moon, pure Mercury)."),
    "AGE_OF_EDUCATION": ("Age of Education (Dasha Lock)", 1.0, 100.0, 1.0, "The exact age to calculate which Mahadasha (Planetary Period) is running when college starts."),
    "W_MAHADASHA_PLANET": ("Mahadasha Planet Weight", 0.0, 10.0, 0.5, "How strongly the Mahadasha lord running at the 'Age of Education' steers the final career choice."),
    "W_D1_MULTIPLIER": ("D-1 Varga Multiplier", 0.0, 10.0, 0.1, "Importance of the main D-1 Birth Chart in the overall score."),
    "W_D9_MULTIPLIER": ("D-9 Varga Multiplier", 0.0, 10.0, 0.1, "Importance of the D-9 Navamsha Chart (Subconscious talents)."),
    "W_D24_MULTIPLIER": ("D-24 Varga Multiplier", 0.0, 10.0, 0.1, "Importance of the D-24 Siddhamsa Chart (The specific microscopic chart for education)."),
    "W_D60_MULTIPLIER": ("D-60 Varga Multiplier", 0.0, 10.0, 0.1, "Importance of the D-60 Shashtiamsa Chart. Forced to ALWAYS be >= any other chart weight."),
    "W_DASHA_LAGNA_MULTIPLIER": ("Dasha Lagna Varga Multiplier", 0.0, 10.0, 0.1, "Importance of reading the D-1 chart using the Mahadasha Lord as the new Ascendant."),
    "W_KARAKAMSHA_MULTIPLIER": ("Karakamsha Varga Multiplier", 0.0, 10.0, 0.1, "Importance of the Karakamsha chart (D1 using D9 Atma Karaka sign as Ascendant)."),
    "W_D24_4TH_HOUSE_WEIGHT": ("D-24 4th House Base Weight", 0.0, 5.0, 0.1, "Exact base weight given to 4th house properties specifically inside the D-24 chart."),
    "W_D24_5TH_HOUSE_WEIGHT": ("D-24 5th House Base Weight", 0.0, 5.0, 0.1, "Exact base weight given to 5th house properties specifically inside the D-24 chart."),
    "W_D1_5TH_LORD_BOOST": ("D-1 5th Lord Conflict Boost", 0.0, 10.0, 0.5, "Bonus score given to the D-1 5th Lord if it is tied among top scorers."),
    "W_SPECIAL_STATUS_BOOST": ("Special D-1 Condition Boost", 0.0, 10.0, 0.5, "Bonus score given to an exalted, debilitated, or exchanged planet to resolve ties when the 5th Lord is absent."),
    "W_SEMI_TECH_PENALTY": ("Semi-Tech Penalty (4+ Malefics)", 0.0, 1.0, 0.1, "Factor to multiply Semi-Technical score by when a Non-Tech Rashi is afflicted by 4 or more malefics.")
}

TOGGLE_KEYS = ["ANALYZE_D1", "ANALYZE_D9", "ANALYZE_D24", "ANALYZE_D60", "ANALYZE_MD", "ANALYZE_KARAKAMSHA"]

TOGGLE_LINKS = {
    "W_D1_MULTIPLIER": ("ANALYZE_D1", "Analyze D-1 Base Chart"),
    "W_D9_MULTIPLIER": ("ANALYZE_D9", "Analyze D-9 Navamsha"),
    "W_D24_MULTIPLIER": ("ANALYZE_D24", "Analyze D-24 Siddhamsa"),
    "W_D60_MULTIPLIER": ("ANALYZE_D60", "Analyze D-60 Shashtiamsa"),
    "W_DASHA_LAGNA_MULTIPLIER": ("ANALYZE_MD", "Analyze Mahadasha Chart"),
    "W_KARAKAMSHA_MULTIPLIER": ("ANALYZE_KARAKAMSHA", "Analyze Karakamsha Chart")
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "education_weights_config.json")

def load_weights():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                saved_weights = json.load(f)
            for key, val in saved_weights.items():
                if key in WEIGHTS_MAP:
                    globals()[key] = float(val)
                elif key in TOGGLE_KEYS:
                    globals()[key] = bool(val)
        except Exception as e:
            print(f"Error loading education weights: {e}")

# Load weights on module initialization
load_weights()

# 9. Basic Definitions
TECH_RASHIS = {1, 3, 5, 6, 9, 10, 11}
NON_TECH_RASHIS = {2, 4, 7, 8, 12}

DEVA_GRAHAS = ["Sun", "Moon", "Mars", "Jupiter"]
DANAVA_GRAHAS = ["Saturn", "Rahu", "Ketu", "Venus"]
MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
BENEFICS = {"Moon", "Mercury", "Venus", "Jupiter"}

PLUGIN_GROUP = "ANALYSIS"
PLUGIN_INDEX = 6

# ==========================================
# EXACT CLASSICAL PROFESSIONS LIST
# ==========================================
RAW_PROFESSIONS = {
    "Technical": {
        "Sun": ["Higher Mathematics", "Physics", "Mula -Ayurvedic - Medicines"],
        "Moon": ["Chemistry", "Medicine", "Pharmacy", "Biochemistry", "Environmental Science"],
        "Mars": ["Science", "Engineering", "Mechanical Work"],
        "Mercury": ["Higher Accountancy"],
        "Jupiter": ["Jeev Vigyan (Biology) - Zoology in association with Ketu", "Biotechnology", "Management", "Law"],
        "Venus": ["Mula (Botany, Horticulture and Agriculture)", "Computer Graphics & Animation"],
        "Saturn": ["Engineering", "Geology"],
        "Rahu": ["Pilot", "Air Hostess", "Aerospace/Aeronautical Engineering/Environmental Science"],
        "Ketu": ["Meteorology", "Computer Language/ Programming", "Microbiology in association with Jupiter"]
    },
    "Semi-Technical": {
        "Sun": ["Statistics", "Mathematics", "Astronomy", "Actuary"],
        "Moon": ["Paramedics"],
        "Mars": ["Science", "Mechanic"],
        "Mercury": ["Semi-technical Accounts"],
        "Jupiter": ["Management", "Commerce", "Finance", "Banking", "Psychology", "Philosophy"],
        "Venus": ["Hotel Management", "Fashion Designing", "Architecture", "Tourism", "Photography"],
        "Saturn": ["Mechanical Work"],
        "Rahu": ["Avionics"],
        "Ketu": ["Languages"]
    },
    "Non-Technical": {
        "Sun": ["Political Science"],
        "Moon": ["Fine Arts", "Humanities", "Music", "Dance"],
        "Mars": ["Law", "Logic related", "Land"],
        "Mercury": ["Astrology", "Journalism", "Public Relation", "Accountancy"],
        "Jupiter": ["History", "Sanskrit", "Classical Literature"],
        "Venus": ["Fine Arts", "Humanities", "Music", "Dance", "Painting", "Sociology"],
        "Saturn": ["History", "Geography", "Law", "Prachin Vidya", "Archaeology"],
        "Rahu": ["Research work", "Psychology"],
        "Ketu": ["Languages"]
    }
}

# ==========================================
# HOUSE THEME ELIMINATION KEYWORDS
# ==========================================
THEME_KEYWORDS = {
    "Foundation (4H)": ["architecture", "land", "agriculture", "botany", "mula", "mechanical", "mechanic", "hotel", "geology", "designing", "property", "engineering", "science", "civil", "construction", "interior"],
    "Medical/Occult (6/8/12H)": ["medicine", "ayurvedic", "pharmacy", "biochemistry", "biology", "zoology", "paramedics", "psychology", "astrology", "prachin vidya", "archaeology", "research", "microbiology", "genetics", "speech", "nursing", "pathology", "surgery"],
    "Communication (3/7/9H)": ["journalism", "public relation", "tourism", "photography", "pilot", "aviation", "languages", "law", "air hostess", "aerospace", "telecommunication", "media", "animation"],
    "Finance (2/11H)": ["accountancy", "commerce", "finance", "banking", "actuary", "statistics", "economics", "management", "financial"],
    "Authority (10H)": ["political science", "management", "public relation", "engineering", "electrical", "defense", "law", "administration", "control", "production"],
    "General (1/5H)": ["mathematics", "physics", "chemistry", "fine arts", "humanities", "music", "dance", "literature", "history", "sanskrit", "sociology", "painting", "computer"]
}

# ==========================================
# PLANETARY ELIMINATION KEYWORDS
# ==========================================
PLANET_KEYWORDS = {
    "Sun": ["mathematics", "physics", "medicine", "ayurvedic", "statistics", "astronomy", "actuary", "political"],
    "Moon": ["chemistry", "medicine", "pharmacy", "biochemistry", "environmental", "paramedics", "arts", "humanities", "music", "dance"],
    "Mars": ["science", "engineering", "mechanic", "mechanical", "law", "logic", "land"],
    "Mercury": ["accountancy", "accounts", "astrology", "journalism", "relation", "communication"],
    "Jupiter": ["biology", "zoology", "biotechnology", "management", "law", "commerce", "finance", "banking", "psychology", "philosophy", "history", "sanskrit", "literature"],
    "Venus": ["botany", "horticulture", "agriculture", "graphics", "animation", "hotel", "fashion", "architecture", "tourism", "photography", "arts", "humanities", "music", "dance", "painting", "sociology"],
    "Saturn": ["engineering", "geology", "mechanical", "history", "geography", "law", "prachin vidya", "archaeology"],
    "Rahu": ["pilot", "hostess", "aerospace", "aeronautical", "environmental", "avionics", "research", "psychology"],
    "Ketu": ["meteorology", "computer", "programming", "microbiology", "languages"]
}

def apply_elimination_logic(prof_list, theme, dom_planet):
    """
    Applies a 2-step strict keyword funnel to eliminate professions.
    Step 1: Eliminates options that don't match the House theme.
    Step 2: Eliminates remaining options that don't match the Planet theme.
    Returns: (exact_degree_str, elim_by_house_list, elim_by_planet_list, original_list)
    """
    if not prof_list: 
        return "Undecided", [], [], []
    if len(prof_list) == 1: 
        return prof_list[0], [], [], prof_list

    theme_keywords = THEME_KEYWORDS.get(theme, [])
    planet_keywords = PLANET_KEYWORDS.get(dom_planet, [])
    
    # Step 1: Filter by House Theme
    passed_house = []
    elim_by_house = []
    if theme_keywords:
        for prof in prof_list:
            if any(kw in prof.lower() for kw in theme_keywords):
                passed_house.append(prof)
            else:
                elim_by_house.append(prof)
    else:
        passed_house = list(prof_list)
        
    # Fallback: If house filter was too strict and eliminated everything, revert it.
    if not passed_house:
        passed_house = list(prof_list)
        elim_by_house = []
        
    # Step 2: Filter by Planet Theme
    passed_planet = []
    elim_by_planet = []
    if planet_keywords:
        for prof in passed_house:
            if any(kw in prof.lower() for kw in planet_keywords):
                passed_planet.append(prof)
            else:
                elim_by_planet.append(prof)
    else:
        passed_planet = list(passed_house)
        
    # Fallback: If planet filter eliminated everything remaining, revert it.
    if not passed_planet:
        passed_planet = list(passed_house)
        elim_by_planet = []
        
    exact_degree = " / ".join(passed_planet) if passed_planet else " / ".join(prof_list)
    
    return exact_degree, elim_by_house, elim_by_planet, list(prof_list)

# ==========================================
# USER WEIGHTS SETTINGS DIALOG
# ==========================================
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Configure Algorithm Weights & Details")
        
        self.resize(850, 650)
        self.setStyleSheet("QDialog { background-color: #F8FAFC; }")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        header_lbl = QLabel("⚙️ Algorithm Configuration Engine")
        header_lbl.setStyleSheet("font-size: 20px; font-weight: bold; color: #0F172A; margin-bottom: 2px;")
        layout.addWidget(header_lbl)
        
        info_label = QLabel("Adjust core calculation variables used across the multi-step triangulation process. Select charts to analyze and tune their independent weights.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-size: 13px; color: #475569; margin-bottom: 10px;")
        layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #E2E8F0; border-radius: 6px; background-color: white; }")
        
        import main
        SmoothScroller = getattr(main, 'SmoothScroller', None)
        if SmoothScroller:
            self.scroller = SmoothScroller(scroll)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(12, 12, 12, 12)
        
        CATEGORIES = {
            "House & Lord Influences": ["W_INFLUENCE_OCC_CONJ", "W_INFLUENCE_ASPECT", "W_NAKSHATRA_5TH_LORD", "W_MERCURY_FACTOR"],
            "Rashi Technicalities": ["W_TECH_RASHI_4TH", "W_TECH_RASHI_5TH"],
            "Planet Nature Multipliers": ["W_TECH_PLANET", "W_SEMI_TECH_PLANET", "W_NON_TECH_PLANET"],
            "Dasha & Timing": ["AGE_OF_EDUCATION", "W_MAHADASHA_PLANET"],
            "Selected Charts & Varga Weights": ["W_D1_MULTIPLIER", "W_D9_MULTIPLIER", "W_D24_MULTIPLIER", "W_D60_MULTIPLIER", "W_DASHA_LAGNA_MULTIPLIER", "W_KARAKAMSHA_MULTIPLIER", "W_D24_4TH_HOUSE_WEIGHT", "W_D24_5TH_HOUSE_WEIGHT"],
            "Special Overrides": ["W_D1_5TH_LORD_BOOST", "W_SPECIAL_STATUS_BOOST", "W_SEMI_TECH_PENALTY"]
        }
        
        self.spin_boxes = {}
        self.checkboxes = {}
        
        for cat_name, keys in CATEGORIES.items():
            cat_widget = QWidget()
            cat_layout = QVBoxLayout(cat_widget)
            cat_layout.setContentsMargins(0, 0, 0, 0)
            cat_layout.setSpacing(6)
            
            cat_label = QLabel(cat_name)
            cat_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #4F46E5; border-bottom: 2px solid #E2E8F0; padding-bottom: 2px;")
            cat_layout.addWidget(cat_label)
            
            for key in keys:
                if key in WEIGHTS_MAP:
                    name, min_val, max_val, step, desc = WEIGHTS_MAP[key]
                    
                    item_widget = QWidget()
                    item_layout = QVBoxLayout(item_widget)
                    item_layout.setContentsMargins(8, 0, 0, 0)
                    item_layout.setSpacing(0)
                    
                    row_layout = QHBoxLayout()
                    
                    spin = QDoubleSpinBox()
                    spin.setRange(min_val, max_val)
                    spin.setSingleStep(step)
                    spin.setDecimals(1)
                    spin.setValue(float(globals().get(key, 0.0)))
                    spin.setFixedWidth(100)
                    spin.setStyleSheet("padding: 2px; border: 1px solid #CBD5E1; border-radius: 4px; background: #FFFFFF; color: #0F172A; font-weight: bold;")
                    
                    # If this weight corresponds to a chart that can be toggled on/off
                    if key in TOGGLE_LINKS:
                        toggle_key, toggle_label = TOGGLE_LINKS[key]
                        chk = QCheckBox(toggle_label)
                        chk.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 13px;")
                        chk.setChecked(bool(globals().get(toggle_key, True)))
                        
                        # Grey out spinbox when unchecked
                        spin.setEnabled(chk.isChecked())
                        chk.toggled.connect(spin.setEnabled)
                        
                        self.checkboxes[toggle_key] = chk
                        row_layout.addWidget(chk)
                    else:
                        name_lbl = QLabel(name)
                        name_lbl.setStyleSheet("font-weight: bold; color: #1E293B; font-size: 13px;")
                        row_layout.addWidget(name_lbl)
                        
                    row_layout.addStretch()
                    row_layout.addWidget(spin)
                    
                    desc_lbl = QLabel(desc)
                    desc_lbl.setWordWrap(True)
                    desc_lbl.setStyleSheet("color: #64748B; font-size: 11px; margin-bottom: 4px;")
                    
                    item_layout.addLayout(row_layout)
                    item_layout.addWidget(desc_lbl)
                    
                    cat_layout.addWidget(item_widget)
                    self.spin_boxes[key] = spin
                    
            content_layout.addWidget(cat_widget)
            
        # Hook up the D-60 multiplier strict validation rule
        for k in ["W_D1_MULTIPLIER", "W_D9_MULTIPLIER", "W_D24_MULTIPLIER", "W_DASHA_LAGNA_MULTIPLIER", "W_KARAKAMSHA_MULTIPLIER"]:
            if k in self.spin_boxes:
                self.spin_boxes[k].valueChanged.connect(self.enforce_d60_rule)
                
        self.enforce_d60_rule()
        
        # Hook up the 4-Chart max validation rule
        for chk in self.checkboxes.values():
            chk.toggled.connect(self.enforce_max_charts)
        self.enforce_max_charts()
            
        # Add "FULL STEPS" inside the scroll container
        algo_group = QGroupBox("How This Algorithm Works")
        algo_group.setStyleSheet("""
            QGroupBox { 
                background-color: #F0FDF4; 
                border: 1px solid #10B981; 
                border-radius: 6px; 
                margin-top: 10px; 
                padding-top: 20px; 
                font-weight: bold; 
                color: #047857; 
                font-size: 13px;
            } 
            QGroupBox::title { left: 10px; top: 6px; }
        """)
        algo_layout = QVBoxLayout(algo_group)
        algo_layout.setSpacing(6)
        
        steps = [
            "<b>1. Look at Selected Charts:</b> Analyze up to 4 charts across D-1, Navamsha (D-9), Siddhamsa (D-24), Shashtiamsa (D-60), Age 18 Dasha Chart, and Karakamsha.",
            "<b>2. Score the Planets & Signs:</b> In all these charts, look at the 5th house (Intellect), its ruler, and Mercury. That gives 'Technical', 'Semi-Technical', or 'Non-Technical' points based on which planets and zodiac signs are involved.",
            "<b>3. Pick the Winning Category:</b> Total all the points across all active charts. The category (Tech, Semi-Tech, or Non-Tech) with the highest score wins.",
            "<b>4. Find the Boss Planet:</b> See which individual planet scored the most points overall. This planet will dictate the specific subject area.",
            "<b>5. Narrow it down by Theme:</b> Finally, look at which area of life (Houses) the Boss Planet affects the most (e.g., Medical, Communication). Use this to filter the Boss Planet's subject list down to the exact degree!"
        ]
        
        for step in steps:
            lbl = QLabel(step)
            lbl.setWordWrap(True)
            lbl.setStyleSheet("color: #1E293B; font-size: 12px; font-weight: normal; line-height: 1.3;")
            algo_layout.addWidget(lbl)
            
        content_layout.addWidget(algo_group)
            
        scroll.setWidget(content)
        layout.addWidget(scroll, stretch=1)
        
        # Fixed Buttons at the bottom
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.setStyleSheet("""
            QPushButton { padding: 6px 20px; font-weight: bold; border-radius: 4px; font-size: 13px; } 
            QPushButton[text='Save'] { background-color: #10B981; color: white; border: 1px solid #059669; }
            QPushButton[text='Cancel'] { background-color: #EF4444; color: white; border: 1px solid #DC2626; }
        """)
        btns.accepted.connect(self.save_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def enforce_d60_rule(self, *_args):
        """Forces the D-60 spinbox to have a minimum value equal to the highest other chart multiplier."""
        if "W_D60_MULTIPLIER" in self.spin_boxes:
            max_other = max(
                self.spin_boxes.get("W_D1_MULTIPLIER", QDoubleSpinBox()).value(),
                self.spin_boxes.get("W_D9_MULTIPLIER", QDoubleSpinBox()).value(),
                self.spin_boxes.get("W_D24_MULTIPLIER", QDoubleSpinBox()).value(),
                self.spin_boxes.get("W_DASHA_LAGNA_MULTIPLIER", QDoubleSpinBox()).value(),
                self.spin_boxes.get("W_KARAKAMSHA_MULTIPLIER", QDoubleSpinBox()).value()
            )
            self.spin_boxes["W_D60_MULTIPLIER"].setMinimum(max_other)

    def enforce_max_charts(self, *_args):
        """Disables unchecked checkboxes if 4 charts are already selected to enforce the limit."""
        checked_count = sum(1 for chk in self.checkboxes.values() if chk.isChecked())
        for toggle_key, chk in self.checkboxes.items():
            if not chk.isChecked():
                chk.setEnabled(checked_count < 4)
        
    def save_and_accept(self):
        saved_weights = {}
        for key, spin in self.spin_boxes.items():
            val = spin.value()
            globals()[key] = val
            saved_weights[key] = val
            
        for key, chk in self.checkboxes.items():
            val = chk.isChecked()
            globals()[key] = val
            saved_weights[key] = val
            
        # CRITICAL: Double-enforce the D60 rule globally directly into standard memory
        globals()["W_D60_MULTIPLIER"] = max(
            globals()["W_D60_MULTIPLIER"],
            globals()["W_D1_MULTIPLIER"],
            globals()["W_D9_MULTIPLIER"],
            globals()["W_D24_MULTIPLIER"],
            globals()["W_DASHA_LAGNA_MULTIPLIER"],
            globals()["W_KARAKAMSHA_MULTIPLIER"]
        )
        saved_weights["W_D60_MULTIPLIER"] = globals()["W_D60_MULTIPLIER"]
            
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(saved_weights, f, indent=4)
            QMessageBox.information(self, "Settings Saved", "Algorithm weights and chart selections have been successfully saved and applied.")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Error saving education weights securely:\n{e}")
            
        self.accept()

# ==========================================
# EDUCATION CALCULATOR ENGINE
# ==========================================
class EducationCalculator:
    def __init__(self, chart_data, d9_data=None, d24_data=None, d60_data=None):
        self.chart_data = chart_data
        self.d9_data = d9_data
        self.d24_data = d24_data
        self.d60_data = d60_data
        self.analyzer_d1 = ChartAnalyzer(chart_data)
        
        self.log = []
        self.scores = {"Technical": 0.0, "Non-Technical": 0.0, "Semi-Technical": 0.0}
        self.dominant_planet_scores = {p: 0 for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]}

    def _is_enemy(self, p1, p2):
        if p1 == p2: return False
        if "Mercury" in (p1, p2):
            other = p2 if p1 == "Mercury" else p1
            if other in ["Moon", "Mars"]: return True
            return False 
        if p1 in DEVA_GRAHAS and p2 in DEVA_GRAHAS: return False
        if p1 in DANAVA_GRAHAS and p2 in DANAVA_GRAHAS: return False
        return True 

    def get_functional_nature(self, p_name, chart, asc_override_idx=None):
        asc_sign_idx = asc_override_idx if asc_override_idx is not None else chart["ascendant"]["sign_index"]
        asc_sign = asc_sign_idx + 1
        lagna_lord = SIGN_LORDS.get(asc_sign)

        occupied_house = 1
        for p in chart.get("planets", []):
            if p["name"] == p_name:
                occupied_house = ((p["sign_index"] - asc_sign_idx) % 12) + 1
                break

        is_upachaya_occupied = occupied_house in [6, 8, 12]

        if p_name in ["Rahu", "Ketu"]:
            if is_upachaya_occupied: return "Malefic", f"Node in Trik Bhava (H{occupied_house})"
            return "Malefic", "Nodes are natural Malefics"

        ruled_houses = []
        for sign, lord in SIGN_LORDS.items():
            if lord == p_name:
                h_num = ((sign - asc_sign) % 12) + 1
                ruled_houses.append(h_num)

        if 5 in ruled_houses or 9 in ruled_houses:
            return "Benefic", "Rules Trikon"

        if 1 in ruled_houses:
            if is_upachaya_occupied: return "Malefic", f"Lagna Lord in Trik (H{occupied_house})"
            return "Benefic", "Lagna Lord"

        if is_upachaya_occupied:
            return "Malefic", f"Occupies Trik (H{occupied_house})"

        upachaya_ruled = [h for h in ruled_houses if h in [6, 8, 12]]
        if upachaya_ruled:
            return "Malefic", "Rules Trik Bhava"

        if self._is_enemy(p_name, lagna_lord):
            return "Malefic", f"Enemy of Lagna Lord ({lagna_lord})"

        return "Benefic", f"Friend of Lagna Lord ({lagna_lord})"

    def _is_afflicted_in_chart(self, p_name, analyzer, asc_override_idx=None):
        p_data = analyzer.get_planet(p_name)
        if not p_data: return False

        conjunct = analyzer.get_conjunct_planets(p_name)
        aspects = analyzer.get_aspecting_planets(p_data["house"])

        for cp in conjunct + aspects:
            func_nature, _ = self.get_functional_nature(cp, analyzer.chart_data, asc_override_idx)
            if func_nature == "Malefic" or cp in MALEFICS:
                return True
        return False

    def _classify_planet(self, p_name, analyzer, asc_override_idx=None):
        p_data = analyzer.get_planet(p_name)
        if not p_data: return "Non-Technical", 0.0, "Planet Not Found"

        sign_num = p_data["sign_index"] + 1
        in_tech_rashi = sign_num in TECH_RASHIS
        rashi_str = "Technical Rashi" if in_tech_rashi else "Non-Technical Rashi"

        func_nature, _ = self.get_functional_nature(p_name, analyzer.chart_data, asc_override_idx)
        is_func_malefic = (func_nature == "Malefic")

        is_inherent_malefic = (p_name in MALEFICS) or p_data.get("debilitated") or p_data.get("retro", False) or is_func_malefic
        afflicted = self._is_afflicted_in_chart(p_name, analyzer, asc_override_idx)
        
        is_acting_malefic = is_inherent_malefic or afflicted
        
        w_tech = globals().get("W_TECH_PLANET", 0.5)
        w_semi = globals().get("W_SEMI_TECH_PLANET", 0.5)
        w_non = globals().get("W_NON_TECH_PLANET", 0.5)

        if is_acting_malefic:
            base_reason = "Malefic/Afflicted"
            if in_tech_rashi: 
                return "Technical", w_tech, f"{base_reason} in {rashi_str}"
            else: 
                return "Semi-Technical", w_semi, f"{base_reason} in {rashi_str}"
        else:
            base_reason = "Unafflicted Benefic"
            if in_tech_rashi: 
                return "Semi-Technical", w_semi, f"{base_reason} in {rashi_str}"
            else: 
                return "Non-Technical", w_non, f"{base_reason} in {rashi_str}"

    def _get_atma_karaka(self, chart_data):
        max_deg = -1
        ak = None
        for p in chart_data.get("planets", []):
            if p["name"] in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]:
                lon = p.get("lon", 0.0)
                deg = lon % 30.0
                if deg > max_deg:
                    max_deg = deg
                    ak = p["name"]
        return ak

    def _process_influences(self, analyzer, target_name, occupant_list, aspect_list, wt_occ, wt_asp, mult, desc_occ, desc_asp, asc_override_idx=None, target_sign=None):
        is_non_tech = target_sign in NON_TECH_RASHIS if target_sign else False
        semi_tech_penalty = 1.0
        
        if is_non_tech:
            malefic_count = 0
            for p in occupant_list + aspect_list:
                p_name = p if isinstance(p, str) else (p.get("name") or p.get("aspecting_planet"))
                if p_name:
                    func_nature, _ = self.get_functional_nature(p_name, analyzer.chart_data, asc_override_idx)
                    if p_name in MALEFICS or func_nature == "Malefic":
                        malefic_count += 1
            
            if malefic_count >= 4:
                semi_tech_penalty = globals().get("W_SEMI_TECH_PENALTY", 0.5)
                self.log.append(f"<li style='color:#DC2626; font-size:11px;'><i>Rule Triggered: {target_name} is in a Non-Tech Rashi with {malefic_count} Malefic influences. Semi-Tech points from these influences will be multiplied by {semi_tech_penalty}.</i></li>")

        for p in occupant_list:
            p_name = p if isinstance(p, str) else p.get("name")
            if not p_name: continue
            
            cat, p_wt, reason = self._classify_planet(p_name, analyzer, asc_override_idx)
            final_wt = wt_occ * p_wt * mult
            math_str = f"{desc_occ} * Planet Wt ({p_wt:.2f}) * Chart Mult ({mult:.2f})"
            
            if cat == "Semi-Technical" and semi_tech_penalty != 1.0:
                final_wt *= semi_tech_penalty
                math_str += f" * Penalty ({semi_tech_penalty})"
                
            self.scores[cat] += final_wt
            self.dominant_planet_scores[p_name] += final_wt
            
            self.log.append(f"<li><b>{p_name}</b> occupies/conjuncts {target_name} &rarr; <b style='color:#0284C7;'>{cat}</b> (+{final_wt:.2f}) <br>"
                            f"<span style='color:#64748B; font-size: 11px;'><i>Reason: {reason}. Math: {math_str} = {final_wt:.2f}</i></span></li>")
            
        for p in aspect_list:
            p_name = p if isinstance(p, str) else p.get("aspecting_planet")
            if not p_name: continue
            
            cat, p_wt, reason = self._classify_planet(p_name, analyzer, asc_override_idx)
            final_wt = wt_asp * p_wt * mult
            math_str = f"{desc_asp} * Planet Wt ({p_wt:.2f}) * Chart Mult ({mult:.2f})"
            
            if cat == "Semi-Technical" and semi_tech_penalty != 1.0:
                final_wt *= semi_tech_penalty
                math_str += f" * Penalty ({semi_tech_penalty})"
                
            self.scores[cat] += final_wt
            self.dominant_planet_scores[p_name] += final_wt
            
            self.log.append(f"<li><b>{p_name}</b> aspects {target_name} &rarr; <b style='color:#0284C7;'>{cat}</b> (+{final_wt:.2f}) <br>"
                            f"<span style='color:#64748B; font-size: 11px;'><i>Reason: {reason}. Math: {math_str} = {final_wt:.2f}</i></span></li>")

    def _eval_varga_chart(self, chart, name, mult, asc_override_idx=None):
        if not chart: return
        self.log.append(f"<div style='margin-bottom: 15px; border-left: 3px solid #0284C7; padding-left: 10px;'>")
        self.log.append(f"<h3 style='color:#0284C7; margin-bottom: 4px;'>--- {name.upper()} ANALYSIS ---</h3><ul>")
        
        is_d24 = "D-24" in name
        
        # Explicitly read exact user-configured global variables to guarantee pure base substitution 
        w_4h_rashi = globals().get("W_D24_4TH_HOUSE_WEIGHT", 0.6) if is_d24 else globals().get("W_TECH_RASHI_4TH", 0.3)
        w_5h_rashi = globals().get("W_D24_5TH_HOUSE_WEIGHT", 0.3) if is_d24 else globals().get("W_TECH_RASHI_5TH", 0.6)
        
        if is_d24:
            w_occ_conj = globals().get("W_D24_4TH_HOUSE_WEIGHT", 0.6)
            w_aspect = globals().get("W_D24_4TH_HOUSE_WEIGHT", 0.6)
        else:
            w_occ_conj = globals().get("W_INFLUENCE_OCC_CONJ", 0.4)
            w_aspect = globals().get("W_INFLUENCE_ASPECT", 0.4)
            
        w_nak_5l = globals().get("W_NAKSHATRA_5TH_LORD", 0.1)
        w_merc_factor = globals().get("W_MERCURY_FACTOR", 0.2)

        analyzer = ChartAnalyzer(chart)
        original_asc_idx = chart["ascendant"]["sign_index"]
        
        asc_idx = asc_override_idx if asc_override_idx is not None else original_asc_idx
        
        h4_sign_idx = (asc_idx + 3) % 12
        h5_sign_idx = (asc_idx + 4) % 12
        
        h4_sign = h4_sign_idx + 1
        h5_sign = h5_sign_idx + 1
        
        self.log.append("<b>1. CHECKING RASHI:</b><br>")
        if h4_sign in TECH_RASHIS:
            self.scores["Technical"] += w_4h_rashi * mult
            self.log.append(f"<li>4th House Sign ({h4_sign}) is Technical &rarr; <b style='color:#0284C7;'>Technical</b> (+{w_4h_rashi * mult:.2f}) <br><span style='color:#64748B; font-size: 11px;'><i>Math: 4H Rashi Base ({w_4h_rashi:.2f}) * Chart Mult ({mult:.2f})</i></span></li>")
        else:
            self.scores["Non-Technical"] += w_4h_rashi * mult
            self.log.append(f"<li>4th House Sign ({h4_sign}) is Non-Technical &rarr; <b style='color:#0284C7;'>Non-Technical</b> (+{w_4h_rashi * mult:.2f}) <br><span style='color:#64748B; font-size: 11px;'><i>Math: 4H Rashi Base ({w_4h_rashi:.2f}) * Chart Mult ({mult:.2f})</i></span></li>")
            
        if h5_sign in TECH_RASHIS:
            self.scores["Technical"] += w_5h_rashi * mult
            self.log.append(f"<li>5th House Sign ({h5_sign}) is Technical &rarr; <b style='color:#0284C7;'>Technical</b> (+{w_5h_rashi * mult:.2f}) <br><span style='color:#64748B; font-size: 11px;'><i>Math: 5H Rashi Base ({w_5h_rashi:.2f}) * Chart Mult ({mult:.2f})</i></span></li>")
        else:
            self.scores["Non-Technical"] += w_5h_rashi * mult
            self.log.append(f"<li>5th House Sign ({h5_sign}) is Non-Technical &rarr; <b style='color:#0284C7;'>Non-Technical</b> (+{w_5h_rashi * mult:.2f}) <br><span style='color:#64748B; font-size: 11px;'><i>Math: 5H Rashi Base ({w_5h_rashi:.2f}) * Chart Mult ({mult:.2f})</i></span></li>")

        target_h_idx = h4_sign_idx if is_d24 else h5_sign_idx
        target_h_sign = h4_sign if is_d24 else h5_sign
        target_h_name = "4th House" if is_d24 else "5th House"
        target_l_name = "4th Lord" if is_d24 else "5th Lord"
        
        target_original_house_num = ((target_h_idx - original_asc_idx) % 12) + 1

        self.log.append(f"<br><b>2. CHECKING {target_h_name.upper()} INFLUENCE:</b><br>")
        t_occ = analyzer.get_occupants(target_original_house_num)
        t_asp = analyzer.get_aspecting_planets(target_original_house_num)
        
        if not t_occ and not t_asp:
            self.log.append(f"<li>No planets occupying or aspecting {target_h_name.lower()}.</li>")
        else:
            desc_occ = f"{'4H' if is_d24 else '5H'} Occ Base ({w_occ_conj:.2f})"
            desc_asp = f"{'4H' if is_d24 else '5H'} Asp Base ({w_aspect:.2f})"
            self._process_influences(analyzer, target_h_name, t_occ, t_asp, w_occ_conj, w_aspect, mult, desc_occ, desc_asp, asc_override_idx, target_sign=target_h_sign)

        self.log.append(f"<br><b>3. CHECKING {target_l_name.upper()} INFLUENCE:</b><br>")
        lord_name = SIGN_LORDS.get(target_h_sign)
        if lord_name:
            lord_p = analyzer.get_planet(lord_name)
            if lord_p:
                lord_orig_h = lord_p["house"]
                lord_sign = lord_p["sign_index"] + 1
                
                l_conj = analyzer.get_conjunct_planets(lord_name)
                l_asp = analyzer.get_aspecting_planets(lord_orig_h)
                if lord_name in l_asp: l_asp.remove(lord_name)
                
                if not l_conj and not l_asp:
                    self.log.append(f"<li>No planets conjunct or aspecting {target_l_name} ({lord_name}).</li>")
                else:
                    desc_conj = f"{'4L' if is_d24 else '5L'} Conj Base ({w_occ_conj:.2f})"
                    desc_lasp = f"{'4L' if is_d24 else '5L'} Asp Base ({w_aspect:.2f})"
                    self._process_influences(analyzer, f"{target_l_name} ({lord_name})", l_conj, l_asp, w_occ_conj, w_aspect, mult, desc_conj, desc_lasp, asc_override_idx, target_sign=lord_sign)
                    
                nak_lord = lord_p.get("nakshatra_lord")
                if nak_lord:
                    cat, n_wt, reason = self._classify_planet(nak_lord, analyzer, asc_override_idx)
                    final_n_wt = w_nak_5l * n_wt * mult
                    self.scores[cat] += final_n_wt
                    self.dominant_planet_scores[nak_lord] += final_n_wt
                    self.log.append(f"<li>Nakshatra Lord of {target_l_name} is <b>{nak_lord}</b> &rarr; <b style='color:#0284C7;'>{cat}</b> (+{final_n_wt:.2f}) <br>"
                                    f"<span style='color:#64748B; font-size: 11px;'><i>Reason: {reason}. Math: Nak Base Wt ({w_nak_5l:.2f}) * Planet Wt ({n_wt:.2f}) * Chart Mult ({mult:.2f}) = {final_n_wt:.2f}</i></span></li>")
        else:
            self.log.append(f"<li>Could not determine {target_l_name.lower()}.</li>")

        self.log.append(f"<br><b>4. REPEATING PROCESS FROM MERCURY (Fractional Factor - w={w_merc_factor:.2f}):</b><br>")
        merc = analyzer.get_planet("Mercury")
        if merc:
            w_merc_5h_rashi = globals().get("W_TECH_RASHI_5TH", 0.6)
            w_merc_occ = globals().get("W_INFLUENCE_OCC_CONJ", 0.4)
            w_merc_asp = globals().get("W_INFLUENCE_ASPECT", 0.4)
            
            merc_sign_idx = merc["sign_index"]
            merc_h5_sign_idx = (merc_sign_idx + 4) % 12
            merc_h5_sign = merc_h5_sign_idx + 1
            
            if merc_h5_sign in TECH_RASHIS:
                self.scores["Technical"] += w_merc_5h_rashi * w_merc_factor * mult
                self.log.append(f"<li>5th House from Mercury Sign ({merc_h5_sign}) is Technical &rarr; <b style='color:#0284C7;'>Technical</b> (+{w_merc_5h_rashi * w_merc_factor * mult:.2f}) <br><span style='color:#64748B; font-size: 11px;'><i>Math: 5H Rashi Base ({w_merc_5h_rashi:.2f}) * Merc Factor ({w_merc_factor:.2f}) * Chart Mult ({mult:.2f})</i></span></li>")
            else:
                self.scores["Non-Technical"] += w_merc_5h_rashi * w_merc_factor * mult
                self.log.append(f"<li>5th House from Mercury Sign ({merc_h5_sign}) is Non-Technical &rarr; <b style='color:#0284C7;'>Non-Technical</b> (+{w_merc_5h_rashi * w_merc_factor * mult:.2f}) <br><span style='color:#64748B; font-size: 11px;'><i>Math: 5H Rashi Base ({w_merc_5h_rashi:.2f}) * Merc Factor ({w_merc_factor:.2f}) * Chart Mult ({mult:.2f})</i></span></li>")

            merc_h5_original_house_num = ((merc_h5_sign_idx - original_asc_idx) % 12) + 1
            m_h5_occ = analyzer.get_occupants(merc_h5_original_house_num)
            m_h5_asp = analyzer.get_aspecting_planets(merc_h5_original_house_num)
            self._process_influences(analyzer, "5th House from Mercury", m_h5_occ, m_h5_asp, w_merc_occ * w_merc_factor, w_merc_asp * w_merc_factor, mult, f"Merc 5H Occ Wt (Base {w_merc_occ:.2f} * Factor {w_merc_factor:.2f})", f"Merc 5H Asp Wt (Base {w_merc_asp:.2f} * Factor {w_merc_factor:.2f})", asc_override_idx, target_sign=merc_h5_sign)
            
            m_l5_name = SIGN_LORDS.get(merc_h5_sign)
            if m_l5_name:
                m_l5_p = analyzer.get_planet(m_l5_name)
                if m_l5_p:
                    m_l5_original_house_num = m_l5_p["house"]
                    m_l5_sign = m_l5_p["sign_index"] + 1
                    
                    m_l5_conj = analyzer.get_conjunct_planets(m_l5_name)
                    m_l5_asp = analyzer.get_aspecting_planets(m_l5_original_house_num)
                    if m_l5_name in m_l5_asp: m_l5_asp.remove(m_l5_name)
                    
                    self._process_influences(analyzer, f"5th Lord from Mercury ({m_l5_name})", m_l5_conj, m_l5_asp, w_merc_occ * w_merc_factor, w_merc_asp * w_merc_factor, mult, f"Merc 5L Conj Wt (Base {w_merc_occ:.2f} * Factor {w_merc_factor:.2f})", f"Merc 5L Asp Wt (Base {w_merc_asp:.2f} * Factor {w_merc_factor:.2f})", asc_override_idx, target_sign=m_l5_sign)
                    
                    m_nak_lord = m_l5_p.get("nakshatra_lord")
                    if m_nak_lord:
                        cat, n_wt, reason = self._classify_planet(m_nak_lord, analyzer, asc_override_idx)
                        final_n_wt = w_nak_5l * w_merc_factor * n_wt * mult
                        self.scores[cat] += final_n_wt
                        self.dominant_planet_scores[m_nak_lord] += final_n_wt
                        self.log.append(f"<li>Nakshatra Lord of Merc's 5L is <b>{m_nak_lord}</b> &rarr; <b style='color:#0284C7;'>{cat}</b> (+{final_n_wt:.2f}) <br>"
                                        f"<span style='color:#64748B; font-size: 11px;'><i>Reason: {reason}. Math: Merc Nak Wt ({w_nak_5l * w_merc_factor:.2f}) * Planet Wt ({n_wt:.2f}) * Chart Mult ({mult:.2f}) = {final_n_wt:.2f}</i></span></li>")
        else:
            self.log.append("<li>Mercury data missing.</li>")
        self.log.append("</ul></div>")

    def _find_house_theme(self, dom_planet):
        h_scores = {h: 0 for h in range(1, 13)}
        
        l5 = self.analyzer_d1.get_lord_of_house(5)
        if l5: h_scores[l5.get("house", 1)] += 2
        
        dom_p = self.analyzer_d1.get_planet(dom_planet)
        if dom_p:
            h_scores[dom_p.get("house", 1)] += 3
            for ruled in dom_p.get("lord_of", []): h_scores[ruled] += 2
            
        for cp in self.analyzer_d1.get_conjunct_planets(dom_planet):
            cp_p = self.analyzer_d1.get_planet(cp)
            for ruled in cp_p.get("lord_of", []): h_scores[ruled] += 1

        best_h = max(h_scores, key=h_scores.get)

        if best_h in [4]: theme, theme_reason = "Foundation (4H)", f"Points heavily directed at 4th House"
        elif best_h in [6, 8, 12]: theme, theme_reason = "Medical/Occult (6/8/12H)", f"Points heavily directed at Dusthanas (6/8/12)"
        elif best_h in [3, 7, 9]: theme, theme_reason = "Communication (3/7/9H)", f"Points heavily directed at 3/7/9 Houses"
        elif best_h in [2, 11]: theme, theme_reason = "Finance (2/11H)", f"Points heavily directed at Wealth Houses (2/11)"
        elif best_h in [10]: theme, theme_reason = "Authority (10H)", f"Points heavily directed at 10th House"
        else: theme, theme_reason = "General (1/5H)", f"Points directed at 1/5 Axis"

        return theme, theme_reason, h_scores

    def run_analysis(self, app_instance=None):
        self.log.append("<h2>Four-Step Triangulation Process</h2>")
        self.log.append("<p style='font-size:12px; color:#64748B;'>Applying logic rules dynamically to active charts.</p>")
        
        # Enforce D60 rule globally at runtime from user variables
        w_d1 = globals().get("W_D1_MULTIPLIER", 1.0)
        w_d9 = globals().get("W_D9_MULTIPLIER", 1.0)
        w_d24 = globals().get("W_D24_MULTIPLIER", 1.0)
        w_d60 = globals().get("W_D60_MULTIPLIER", 1.0)
        w_md = globals().get("W_DASHA_LAGNA_MULTIPLIER", 1.0)
        w_karakamsha = globals().get("W_KARAKAMSHA_MULTIPLIER", 1.0)
        
        actual_d60_mult = max(w_d60, w_d1, w_d9, w_d24, w_md, w_karakamsha)
        age_edu = globals().get("AGE_OF_EDUCATION", 18.0)
        
        # Step 1, 2, 3: Core Varga Evaluations based on selected charts
        if globals().get("ANALYZE_D1", True):
            self._eval_varga_chart(self.chart_data, "D-1 Base Chart", w_d1, asc_override_idx=None)
        if globals().get("ANALYZE_D9", True):
            self._eval_varga_chart(self.d9_data, "D-9 Navamsha", w_d9, asc_override_idx=None)
        if globals().get("ANALYZE_D24", True):
            self._eval_varga_chart(self.d24_data, "D-24 Siddhamsa", w_d24, asc_override_idx=None)
        if globals().get("ANALYZE_D60", True):
            self._eval_varga_chart(self.d60_data, "D-60 Shashtiamsa", actual_d60_mult, asc_override_idx=None)
            
        # Karakamsha Evaluation
        if globals().get("ANALYZE_KARAKAMSHA", False):
            ak_name = self._get_atma_karaka(self.chart_data)
            self.log.append(f"<div style='margin-bottom: 15px; border-left: 3px solid #D97706; padding-left: 10px;'>")
            self.log.append(f"<h3 style='color:#D97706; margin-bottom: 4px;'>--- KARAKAMSHA ANALYSIS ---</h3><ul>")
            if ak_name:
                ak_d9_sign_idx = None
                for p in self.d9_data.get("planets", []):
                    if p["name"] == ak_name:
                        ak_d9_sign_idx = p["sign_index"]
                        break
                if ak_d9_sign_idx is not None:
                    self.log.append(f"<li>Atma Karaka is <b>{ak_name}</b>. It occupies sign {ak_d9_sign_idx + 1} in D-9. Using as new D-1 Ascendant.</li></ul></div>")
                    self._eval_varga_chart(self.chart_data, f"Karakamsha (Lagna={ak_d9_sign_idx + 1})", w_karakamsha, asc_override_idx=ak_d9_sign_idx)
                else:
                    self.log.append(f"<li>Could not locate Atma Karaka ({ak_name}) in D-9. Skipping Karakamsha.</li></ul></div>")
            else:
                self.log.append("<li>Could not identify Atma Karaka. Skipping Karakamsha.</li></ul></div>")
        
        # Mahadasha Evaluation
        if globals().get("ANALYZE_MD", False):
            jd_utc = self.chart_data.get("current_jd")
            moon_p = self.analyzer_d1.get_planet("Moon")
            
            self.log.append(f"<div style='margin-bottom: 15px; border-left: 3px solid #8B5CF6; padding-left: 10px;'>")
            self.log.append(f"<h3 style='color:#8B5CF6; margin-bottom: 4px;'>--- D-1 DASHA LAGNA (AGE {age_edu}) ANALYSIS ---</h3><ul>")
            if jd_utc and moon_p:
                target_jd = jd_utc + (age_edu * 365.2421904)
                engine = astro_engine.EphemerisEngine()
                dasha_data = engine.calculate_vimshottari_dasha(jd_utc, moon_p["lon"], target_jd)
                dasha_seq = dasha_data.get("current_sequence", [])
                
                if dasha_seq and len(dasha_seq) > 0:
                    md_lord = dasha_seq[0]
                    md_p = self.analyzer_d1.get_planet(md_lord)
                    if md_p:
                        md_sign_idx = md_p["sign_index"]
                        self.log.append(f"<li>Dasha Lord at Age {age_edu} is {md_lord}. Processing chart with {md_lord}'s sign as Lagna.</li></ul></div>")
                        self._eval_varga_chart(self.chart_data, f"D-1 Dasha Lagna ({md_lord})", w_md, asc_override_idx=md_sign_idx)
                    else:
                        self.log.append(f"<li>Could not find {md_lord} in chart. Skipping Dasha Lagna.</li></ul></div>")
                else:
                    self.log.append("<li>Could not compute Dasha timing. Skipping Dasha Lagna.</li></ul></div>")
            else:
                self.log.append("<li>Missing JD or Moon data for Dasha. Skipping Dasha Lagna.</li></ul></div>")

        # Aggregating Results
        self.log.append(f"<div style='margin-bottom: 15px; border-left: 3px solid #10B981; padding-left: 10px;'>")
        self.log.append(f"<h3 style='color:#10B981; margin-bottom: 4px;'>--- AGGREGATING FINAL RESULTS ---</h3><ul>")

        winner_cat = max(self.scores, key=self.scores.get)
        self.log.append(f"<li><b>1. Dominant Category Selected:</b> {winner_cat} (Score: {self.scores[winner_cat]:.2f})</li>")
        
        # CHANGED: Threshold is now >= 1.0
        high_scorers = [p for p, s in self.dominant_planet_scores.items() if s >= 1.0]
        l5 = self.analyzer_d1.get_lord_of_house(5)
        d1_5th_lord_name = l5.get("name") if l5 else None
        
        w_5l_boost = globals().get("W_D1_5TH_LORD_BOOST", 2.0)
        w_special_boost = globals().get("W_SPECIAL_STATUS_BOOST", 2.0)

        if len(high_scorers) >= 2:
            self.log.append(f"<li><b>Boss Selection Conflict:</b> Multiple planets scored &ge; 1.0: {', '.join(high_scorers)}</li>")
            if d1_5th_lord_name in high_scorers:
                self.dominant_planet_scores[d1_5th_lord_name] += w_5l_boost
                self.log.append(f"<li>&rarr; <b>D-1 5th Lord Rule:</b> {d1_5th_lord_name} receives 5th Lord Boost (+{w_5l_boost:.2f}). New score: {self.dominant_planet_scores[d1_5th_lord_name]:.2f}</li>")
                dom_planet = max(self.dominant_planet_scores, key=self.dominant_planet_scores.get)
            else:
                self.log.append(f"<li>&rarr; D-1 5th Lord ({d1_5th_lord_name}) not among top contenders. Applying Special D-1 conditions.</li>")
                
                # Find D1 Rashi Exchanges
                rashi_exchanges = set()
                for p1_name, p1_data in self.analyzer_d1.planets.items():
                    if p1_name in ["Rahu", "Ketu"]: continue
                    p1_sign_lord = SIGN_LORDS.get(p1_data["sign_num"])
                    if p1_sign_lord and p1_sign_lord != p1_name and p1_sign_lord not in ["Rahu", "Ketu"]:
                        p2_data = self.analyzer_d1.get_planet(p1_sign_lord)
                        if p2_data:
                            p2_sign_lord = SIGN_LORDS.get(p2_data["sign_num"])
                            if p2_sign_lord == p1_name:
                                rashi_exchanges.add(p1_name)
                                rashi_exchanges.add(p1_sign_lord)
                
                for p in high_scorers:
                    p_data = self.analyzer_d1.get_planet(p)
                    is_special = False
                    reasons = []
                    if p_data.get("exalted"):
                        is_special = True; reasons.append("Exalted")
                    if p_data.get("debilitated"):
                        is_special = True; reasons.append("Debilitated")
                    if p in rashi_exchanges:
                        is_special = True; reasons.append("Rashi Exchange")
                        
                    if is_special:
                        self.dominant_planet_scores[p] += w_special_boost
                        self.log.append(f"<li>&rarr; <b>{p}</b> receives Special Condition Boost (+{w_special_boost:.2f}) for: {', '.join(reasons)}. New score: {self.dominant_planet_scores[p]:.2f}</li>")
                
                dom_planet = max(self.dominant_planet_scores, key=self.dominant_planet_scores.get)
        else:
            dom_planet = max(self.dominant_planet_scores, key=self.dominant_planet_scores.get)

        self.log.append(f"<li><b>2. Planetary Influence Selected:</b> {dom_planet} (Score: {self.dominant_planet_scores[dom_planet]:.2f})</li>")
        
        prof_list = RAW_PROFESSIONS.get(winner_cat, {}).get(dom_planet, ["General Studies"])
        
        theme, theme_reason, h_scores = self._find_house_theme(dom_planet)
        self.log.append(f"<li><b>4. House Result:</b> {theme} - {theme_reason}</li>")
        
        exact_degree, elim_house, elim_planet, original_list = apply_elimination_logic(prof_list, theme, dom_planet)
        
        orig_str = " / ".join(original_list) if original_list else "None"
        elim_house_str = " / ".join(elim_house) if elim_house else "None"
        elim_planet_str = " / ".join(elim_planet) if elim_planet else "None"
        
        self.log.append(f"<li><b>5. Final Elimination Funnel:</b><br>"
                        f"&nbsp;&nbsp;&nbsp;&bull; <b>Classical Results:</b> {orig_str}<br>"
                        f"&nbsp;&nbsp;&nbsp;&bull; <b>Eliminated by House ({theme}):</b> <span style='color:#DC2626;'>{elim_house_str}</span><br>"
                        f"&nbsp;&nbsp;&nbsp;&bull; <b>Eliminated by Planet ({dom_planet}):</b> <span style='color:#DC2626;'>{elim_planet_str}</span><br>"
                        f"&nbsp;&nbsp;&nbsp;&bull; <b>Final Surviving Degrees:</b> <b style='color:#047857;'>{exact_degree}</b></li>")
        
        nak_lord = self.analyzer_d1.get_nakshatra_lord(dom_planet)
        if not nak_lord: nak_lord = "Ketu"
        self.log.append(f"<li><b>6. Final Nakshatra Influence:</b> Star of {nak_lord}</li></ul></div>")

        logic_str = (
            f"<b>1. Dominant Category Selected:</b> {winner_cat} (Score: {self.scores[winner_cat]:.2f})<br>"
            f"<b>2. Planetary Influence Selected:</b> {dom_planet} (Score: {self.dominant_planet_scores[dom_planet]:.2f})<br>"
            f"<b>3. Classical Results (Initial Options):</b> {orig_str}<br>"
            f"<b>4. House Theme:</b> {theme} - {theme_reason}<br>"
            f"<b>5. Elimination Process:</b><br>"
            f"&nbsp;&nbsp;&nbsp;<span style='color:#DC2626;'>&bull; Eliminated by House Theme: {elim_house_str}</span><br>"
            f"&nbsp;&nbsp;&nbsp;<span style='color:#DC2626;'>&bull; Eliminated by Planet Theme: {elim_planet_str}</span><br>"
            f"<b>6. Final Nakshatra Influence:</b> Star of {nak_lord}"
        )

        self.log.append("<hr><h3>Real-World Diagnostics (CSI Verification)</h3><ul>")
        if CSIHelper and app_instance:
            helper = CSIHelper.get_instance(app_instance)
            csi_4, csi_5, csi_9 = float(helper.csi_house_4()), float(helper.csi_house_5()), float(helper.csi_house_9())
        else:
            csi_4 = csi_5 = csi_9 = 1.0

        self.log.append(f"<li><b>4th House (Formal Education):</b> CSI {csi_4:.2f}</li>")
        self.log.append(f"<li><b>5th House (Raw Intellect):</b> CSI {csi_5:.2f}</li>")
        self.log.append(f"<li><b>9th House (Post-Graduate):</b> CSI {csi_9:.2f}</li></ul>")

        # Insert Complete Score Breakdown Table directly into the Algorithmic Trail
        table_html = "<div style='background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 10px; margin-top: 15px;'>"
        table_html += "<h3 style='margin-top: 0; margin-bottom: 10px; color: #1E293B; text-align: center; border-bottom: 1px solid #E2E8F0; padding-bottom: 6px;'>COMPLETE SCORE BREAKDOWN</h3>"

        table_html += "<table width='100%' cellpadding='4' cellspacing='0' style='border:none;'>"
        table_html += "<tr><td valign='top' width='33%' style='padding-right: 5px;'>"

        # Category Table
        table_html += "<table width='100%' style='border-collapse: collapse; font-size: 12px;'>"
        table_html += "<tr style='background-color:#E2E8F0;'><th style='border:1px solid #CBD5E1; padding:4px; text-align:left;'>Stream Category</th><th style='border:1px solid #CBD5E1; padding:4px; text-align:right;'>Score</th></tr>"
        for cat, score in sorted(self.scores.items(), key=lambda x: x[1], reverse=True):
            table_html += f"<tr><td style='border:1px solid #CBD5E1; padding:4px; color:#334155;'>{cat}</td><td style='border:1px solid #CBD5E1; padding:4px; text-align:right; font-weight:bold; color:#0F172A;'>{score:.2f}</td></tr>"
        table_html += "</table>"

        table_html += "</td><td valign='top' width='33%' style='padding-left: 5px; padding-right: 5px;'>"

        # Planet Table
        table_html += "<table width='100%' style='border-collapse: collapse; font-size: 12px;'>"
        table_html += "<tr style='background-color:#E2E8F0;'><th style='border:1px solid #CBD5E1; padding:4px; text-align:left;'>Planet</th><th style='border:1px solid #CBD5E1; padding:4px; text-align:right;'>Score</th></tr>"
        for p, score in sorted(self.dominant_planet_scores.items(), key=lambda x: x[1], reverse=True):
            table_html += f"<tr><td style='border:1px solid #CBD5E1; padding:4px; color:#334155;'>{p}</td><td style='border:1px solid #CBD5E1; padding:4px; text-align:right; font-weight:bold; color:#0F172A;'>{score:.2f}</td></tr>"
        table_html += "</table>"

        table_html += "</td><td valign='top' width='33%' style='padding-left: 5px;'>"

        # House Table
        table_html += "<table width='100%' style='border-collapse: collapse; font-size: 12px;'>"
        table_html += "<tr style='background-color:#E2E8F0;'><th style='border:1px solid #CBD5E1; padding:4px; text-align:left;'>House Theme</th><th style='border:1px solid #CBD5E1; padding:4px; text-align:right;'>Score</th></tr>"
        for h, score in sorted(h_scores.items(), key=lambda x: x[1], reverse=True):
            table_html += f"<tr><td style='border:1px solid #CBD5E1; padding:4px; color:#334155;'>House {h}</td><td style='border:1px solid #CBD5E1; padding:4px; text-align:right; font-weight:bold; color:#0F172A;'>{score:.2f}</td></tr>"
        table_html += "</table>"

        table_html += "</td></tr></table></div>"

        self.log.append(table_html)

        return {
            "exact_degree": exact_degree,
            "winner_cat": winner_cat,
            "theme": theme,
            "dom_planet": dom_planet,
            "nak_lord": nak_lord,
            "logic_str": logic_str,
            "elim_house_str": elim_house_str,
            "elim_planet_str": elim_planet_str,
            "original_str": orig_str,
            "log": "".join(self.log),
            "scores": self.scores,
            "planet_scores": self.dominant_planet_scores,
            "h_scores": h_scores,
            "csi_4": csi_4,
            "csi_5": csi_5,
            "csi_9": csi_9
        }

# ==========================================
# EDUCATION UI DIALOG
# ==========================================
class EducationAnalysisDialog(QDialog):
    def __init__(self, app_instance, chart_data, parent=None):
        super().__init__(parent, Qt.WindowType.Window)
        
        self.app = app_instance
        self.chart_data = chart_data
        self.time_logs = {} 
        
        self.last_jd = self.chart_data.get('current_jd')
        
        self.monitor_timer = QTimer(self)
        self.monitor_timer.timeout.connect(self.check_for_app_updates)
        self.monitor_timer.start(1000)
        
        engine = astro_engine.EphemerisEngine()
        self.d9_data = engine.compute_divisional_chart(self.chart_data, "D9")
        self.d24_data = engine.compute_divisional_chart(self.chart_data, "D24")
        self.d60_data = engine.compute_divisional_chart(self.chart_data, "D60")

        self.setWindowTitle("Educational Degree Mapping")
        self.resize(1300, 850) 
        
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QGroupBox { background-color: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 6px; margin-top: 12px; font-size: 14px; font-weight: bold; color: #0F172A; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px 0 5px; }
            QTextBrowser { background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 4px; padding: 10px; font-family: 'Segoe UI', sans-serif; font-size: 13px; color: #334155; }
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 4px; }
            QTabBar::tab { background: #E2E8F0; padding: 10px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; color: #0284C7; border-bottom: 2px solid #0284C7; }
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.menu_bar = QMenuBar()
        self.menu_bar.setStyleSheet("background-color: #E2E8F0; padding: 4px;")
        settings_action = self.menu_bar.addAction("⚙️ Configure Algorithm Weights & Chart Toggles")
        settings_action.triggered.connect(self.open_settings)
        self.main_layout.addWidget(self.menu_bar)

        self.content_layout = QHBoxLayout()
        self.main_layout.addLayout(self.content_layout, stretch=1)
        
        self.left_panel = QWidget()
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(6, 6, 6, 6)
        
        self.summary_group = QGroupBox("Final Output")
        summary_layout = QVBoxLayout()
        
        self.lbl_recommendations = QLabel("Calculating...")
        self.lbl_recommendations.setWordWrap(True)
        self.lbl_recommendations.setStyleSheet("font-size: 14px; padding: 10px; background-color: #FFFFFF; border-radius: 4px; border: 1px solid #E2E8F0;")
        
        summary_layout.addWidget(self.lbl_recommendations)
        summary_layout.addStretch() 
        self.summary_group.setLayout(summary_layout)
        self.left_layout.addWidget(self.summary_group)
        self.left_layout.addStretch() 
        
        self.content_layout.addWidget(self.left_panel, stretch=1)
        
        self.right_panel = QTabWidget()
        
        # Chart UI Init
        self.d1_chart_ui = ChartRenderer()
        self.d1_chart_ui.title = "D-1 Rashi"
        self.d1_chart_ui.update_chart(self.chart_data)
        
        self.d9_chart_ui = ChartRenderer()
        self.d9_chart_ui.title = "D-9 Navamsha"
        self.d9_chart_ui.update_chart(self.d9_data, d1_data=self.chart_data)
        
        self.d24_chart_ui = ChartRenderer()
        self.d24_chart_ui.title = "D-24 Siddhamsa"
        self.d24_chart_ui.update_chart(self.d24_data, d1_data=self.chart_data)
        
        self.d60_chart_ui = ChartRenderer()
        self.d60_chart_ui.title = "D-60 Shashtiamsa"
        self.d60_chart_ui.update_chart(self.d60_data, d1_data=self.chart_data)
        
        self.log_tab = QWidget()
        log_tab_layout = QVBoxLayout(self.log_tab)
        self.log_browser = QTextBrowser()
        
        import main
        SmoothScroller = getattr(main, 'SmoothScroller', None)
        if SmoothScroller:
            self.scroller = SmoothScroller(self.log_browser)
            
        log_tab_layout.addWidget(self.log_browser)
        
        self.right_panel.addTab(self.d1_chart_ui, "D-1 Base Chart")
        self.right_panel.addTab(self.d9_chart_ui, "D-9 Navamsha")
        self.right_panel.addTab(self.d24_chart_ui, "D-24 Siddhamsa")
        self.right_panel.addTab(self.d60_chart_ui, "D-60 Shashtiamsa")
        self.right_panel.addTab(self.log_tab, "Algorithmic Trail")
        
        self.time_mod_tab = QWidget()
        time_mod_layout = QVBoxLayout(self.time_mod_tab)
        
        time_top_bar = QHBoxLayout()
        self.btn_run_time_mod = QPushButton("Run Sensitivity Analysis (±20 mins)")
        self.btn_run_time_mod.setStyleSheet("background-color: #8B5CF6; color: white; font-weight: bold; padding: 8px 16px; border-radius: 4px;")
        self.btn_run_time_mod.clicked.connect(self.run_time_sensitivity)
        
        time_info_lbl = QLabel("Checks how Birth Time fluctuations affect the Educational Stream.")
        time_info_lbl.setStyleSheet("color: #64748B; font-style: italic;")
        
        time_top_bar.addWidget(self.btn_run_time_mod)
        time_top_bar.addWidget(time_info_lbl)
        time_top_bar.addStretch()
        
        self.time_mod_results = QTextBrowser()
        self.time_mod_results.setStyleSheet("""
            QTextBrowser {
                background-color: #F8FAFC; 
                font-size: 13px; 
                color: #334155; 
                border: 1px solid #CBD5E1; 
                border-radius: 6px; 
                padding: 6px;
            }
            QScrollBar:vertical {
                border: none;
                background: #F1F5F9;
                width: 10px;
                border-radius: 5px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #CBD5E1;
                min-height: 30px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94A3B8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.time_mod_results.setOpenLinks(False)
        self.time_mod_results.anchorClicked.connect(self.on_time_link_clicked)
        
        if SmoothScroller:
            self.time_scroller = SmoothScroller(self.time_mod_results)
            
        time_mod_layout.addLayout(time_top_bar)
        time_mod_layout.addWidget(self.time_mod_results)
        
        self.right_panel.addTab(self.time_mod_tab, "Time Sensitivity (±20m)")
        
        self.content_layout.addWidget(self.right_panel, stretch=2)
        self.refresh_analysis()

    def check_for_app_updates(self):
        if not self.isVisible():
            return
        if hasattr(self.app, 'current_base_chart') and self.app.current_base_chart:
            current_jd = self.app.current_base_chart.get('current_jd')
            if current_jd and current_jd != self.last_jd:
                self.last_jd = current_jd
                self.update_data(self.app.current_base_chart)

    def update_data(self, new_chart_data):
        self.chart_data = new_chart_data
        engine = astro_engine.EphemerisEngine()
        self.d9_data = engine.compute_divisional_chart(self.chart_data, "D9")
        self.d24_data = engine.compute_divisional_chart(self.chart_data, "D24")
        self.d60_data = engine.compute_divisional_chart(self.chart_data, "D60")
        
        self.d1_chart_ui.update_chart(self.chart_data)
        self.d9_chart_ui.update_chart(self.d9_data, d1_data=self.chart_data)
        self.d24_chart_ui.update_chart(self.d24_data, d1_data=self.chart_data)
        self.d60_chart_ui.update_chart(self.d60_data, d1_data=self.chart_data)
        
        self.refresh_analysis()

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.refresh_analysis()

    def on_time_link_clicked(self, url):
        offset_str = url.toString()
        if offset_str in self.time_logs:
            self.log_browser.setHtml(self.time_logs[offset_str])
            idx = self.right_panel.indexOf(self.log_tab)
            if idx != -1:
                self.right_panel.setCurrentIndex(idx)

    def refresh_analysis(self):
        calc = EducationCalculator(self.chart_data, self.d9_data, self.d24_data, self.d60_data)
        res = calc.run_analysis(self.app)
        
        self.time_logs["0"] = res["log"]
        
        rec_str = "<div style='color: #0F172A; margin-bottom: 12px; padding: 12px; background-color: #F0FDF4; border: 1px solid #10B981; border-radius: 6px;'>"
        rec_str += f"<h3 style='margin-top:0; margin-bottom: 6px; color:#047857;'>Educational Degree Prediction</h3>"
        rec_str += f"<div style='font-size: 22px; font-weight: bold; color: #4F46E5; margin-bottom: 12px;'>► {res['exact_degree']}</div>"
        
        rec_str += f"<div style='font-size: 13px; color: #475569; margin-bottom: 8px; border-top: 1px solid #A7F3D0; padding-top: 8px;'>"
        rec_str += f"<b>📚 Classical Results:</b> {res['original_str']}<br>"
        rec_str += f"<b>🏠 Eliminated by House Theme:</b> <span style='color: #DC2626;'>{res['elim_house_str']}</span><br>"
        rec_str += f"<b>🪐 Eliminated by Planet Theme:</b> <span style='color: #DC2626;'>{res['elim_planet_str']}</span>"
        rec_str += f"</div>"
        
        rec_str += f"<div style='font-size: 13px; color: #475569; line-height: 1.5;'>{res['logic_str']}</div>"
        rec_str += "</div>"
        
        self.lbl_recommendations.setText(rec_str)
        self.log_browser.setHtml(res["log"])

    def _approximate_chart_for_offset(self, base_chart, offset_mins):
        new_chart = copy.deepcopy(base_chart)
        new_chart["current_jd"] = base_chart["current_jd"] + (offset_mins / 1440.0)
        
        deg_shift = offset_mins / 4.0
        
        asc_lon = new_chart.get("ascendant", {}).get("lon")
        if asc_lon is None:
            try:
                geo_lat = base_chart.get("lat", 0.0)
                geo_lon = base_chart.get("lon", 0.0)
                asc_lon = astro_engine.fallback_ascendant(base_chart["current_jd"], geo_lat, geo_lon)
            except Exception:
                pass
                
            if asc_lon is None:
                if not getattr(self, '_shown_lon_error', False):
                    QMessageBox.critical(self, "Critical Error", "CRITICAL ERROR: Exact Longitude ('lon') is missing from the chart data!\n\nProceeding with a mathematical approximation (15° default). Accuracy will be reduced.")
                    self._shown_lon_error = True
                    
                asc_sign_idx = new_chart.get("ascendant", {}).get("sign_index", 0)
                asc_lon = (asc_sign_idx * 30.0) + 15.0
            
        new_asc_lon = (asc_lon + deg_shift) % 360.0
        new_chart["ascendant"]["lon"] = new_asc_lon
        new_asc_sign = int(new_asc_lon // 30)
        new_chart["ascendant"]["sign_index"] = new_asc_sign
        
        for p in new_chart.get("planets", []):
            if p["name"] == "Moon":
                p_lon = p.get("lon")
                if p_lon is None:
                    try:
                        res = astro_engine.fallback_planet_calc(base_chart["current_jd"], "Moon")
                        p_lon = res[0]
                    except Exception:
                        p_lon = (p.get("sign_index", 0) * 30.0) + 15.0
                p["lon"] = (p_lon + (offset_mins * 0.008333)) % 360.0
                p["sign_index"] = int(p["lon"] // 30)
            
            p["house"] = ((p["sign_index"] - new_asc_sign) % 12) + 1
            
        return new_chart

    def run_time_sensitivity(self):
        self._shown_lon_error = False
        self.btn_run_time_mod.setText("Calculating (Please wait...)")
        self.btn_run_time_mod.setEnabled(False)
        QApplication.processEvents()
        
        html = "<h3 style='color: #0F172A; margin-bottom: 16px; margin-top: 5px;'>Time Fluctuation Analysis</h3>"
        html += "<table width='100%' style='border-collapse: separate; border-spacing: 0 10px;'>"
        
        offsets = list(range(-20, 25, 5))
        
        lat = getattr(self.app, 'current_lat', self.chart_data.get('lat', 0.0))
        lon = getattr(self.app, 'current_lon', self.chart_data.get('lon', 0.0))
        tz = getattr(self.app, 'current_tz', self.chart_data.get('tz', 'UTC'))
        
        if hasattr(self.app, 'time_ctrl') and hasattr(self.app.time_ctrl, 'current_time'):
            base_dt_dict = self.app.time_ctrl.current_time.copy()
        else:
            base_dt_dict = {
                'year': int(self.chart_data.get('year', 2000)),
                'month': int(self.chart_data.get('month', 1)),
                'day': int(self.chart_data.get('day', 1)),
                'hour': int(self.chart_data.get('hour', 12)),
                'minute': int(self.chart_data.get('minute', 0)),
                'second': int(self.chart_data.get('second', 0))
            }
            
        try:
            base_dt = datetime.datetime(
                base_dt_dict['year'], base_dt_dict['month'], base_dt_dict['day'], 
                base_dt_dict['hour'], base_dt_dict['minute'], int(base_dt_dict.get('second', 0))
            )
        except Exception:
            base_dt = None
            
        fresh_eng = astro_engine.EphemerisEngine()
        if hasattr(self.app, 'cb_ayanamsa'):
            fresh_eng.set_ayanamsa(self.app.cb_ayanamsa.currentText())
        if hasattr(self.app, 'chk_true_pos'):
            fresh_eng.set_true_positions(self.app.chk_true_pos.isChecked())
        if hasattr(self.app, 'ephemeris') and hasattr(self.app.ephemeris, 'custom_vargas'):
            fresh_eng.set_custom_vargas(self.app.ephemeris.custom_vargas)
        
        for offset in offsets:
            shifted_d1 = None
            
            if offset == 0:
                shifted_d1 = self.chart_data
                shifted_d9 = self.d9_data
                shifted_d24 = self.d24_data
                shifted_d60 = self.d60_data
            else:
                if base_dt:
                    new_dt = base_dt + datetime.timedelta(minutes=offset)
                    new_time_dict = {
                        'year': new_dt.year, 'month': new_dt.month, 'day': new_dt.day,
                        'hour': new_dt.hour, 'minute': new_dt.minute, 'second': new_dt.second
                    }
                    
                    try:
                        shifted_d1 = fresh_eng.calculate_chart(new_time_dict, lat, lon, tz)
                    except Exception as e:
                        print(f"Sensitivity calc exactly failed: {e}")
                
                if not shifted_d1:
                    shifted_d1 = self._approximate_chart_for_offset(self.chart_data, offset)
                    
                if shifted_d1:
                    if base_dt:
                        shifted_d1['year'] = new_dt.year
                        shifted_d1['month'] = new_dt.month
                        shifted_d1['day'] = new_dt.day
                        shifted_d1['hour'] = new_dt.hour
                        shifted_d1['minute'] = new_dt.minute
                        
                    shifted_d1['lat'] = lat
                    shifted_d1['lon'] = lon
                    shifted_d1['tz'] = tz
                        
                    shifted_d9 = fresh_eng.compute_divisional_chart(shifted_d1, "D9")
                    shifted_d24 = fresh_eng.compute_divisional_chart(shifted_d1, "D24")
                    shifted_d60 = fresh_eng.compute_divisional_chart(shifted_d1, "D60")
                
            if shifted_d1:
                calc = EducationCalculator(shifted_d1, shifted_d9, shifted_d24, shifted_d60)
                res = calc.run_analysis(self.app)
                
                self.time_logs[str(offset)] = res["log"]
                
                output_html = f"<div style='font-size: 18px; font-weight: bold; color: #4F46E5; margin-bottom: 8px;'>► {res['exact_degree']}</div>"
                output_html += f"<div style='font-size: 13px; color: #334155; line-height: 1.5;'>{res['logic_str']}</div>"
                
                link_html = f"<div style='margin-top: 10px;'><a href='{offset}' style='color: #0284C7; font-weight: bold; text-decoration: none;'>🔍 View Detailed Algorithmic Trail</a></div>"
                output_html += link_html
                
                time_lbl = "0 min<br><span style='font-size:11px; font-weight:normal; color:#64748B;'>(Current)</span>" if offset == 0 else f"{offset:+} mins"
                row_bg = "#F0FDF4" if offset == 0 else "#FFFFFF"
                border_col = "#10B981" if offset == 0 else "#CBD5E1"
                
                html += f"<tr>"
                html += f"<td width='15%' style='background-color: {row_bg}; border: 1px solid {border_col}; border-right: none; border-top-left-radius: 6px; border-bottom-left-radius: 6px; text-align: center; font-size: 15px; font-weight: bold; color: #0F172A; padding: 10px;'>{time_lbl}</td>"
                html += f"<td width='85%' style='background-color: {row_bg}; border: 1px solid {border_col}; border-left: none; border-top-right-radius: 6px; border-bottom-right-radius: 6px; padding: 12px 16px;'>{output_html}</td>"
                html += f"</tr>"
            
            QApplication.processEvents()
        
        html += "</table>"
        self.time_mod_results.setHtml(html)
        
        self.btn_run_time_mod.setText("Run Sensitivity Analysis (±20 mins)")
        self.btn_run_time_mod.setEnabled(True)


# ==========================================
# PLUGIN ENTRY POINT
# ==========================================
def setup_ui(app, layout):
    from PyQt6.QtWidgets import QGroupBox, QVBoxLayout
    
    plugin_group = QGroupBox("Analysis Engine")
    group_layout = QVBoxLayout()
    group_layout.setContentsMargins(6, 6, 6, 6)
    group_layout.setSpacing(6)
    plugin_group.setLayout(group_layout)
    
    layout.addWidget(plugin_group)

    btn_edu = QPushButton("Educational Degree")
    btn_edu.setStyleSheet("""
        QPushButton {
            font-weight: bold;
            color: #1e3a5f;
            border: 1px solid #93c5fd;
            background-color: #e0f2fe;
            padding: 5px 10px;
            border-radius: 4px;
        }

        QPushButton:hover {
            background-color: #bae6fd;
            border-color: #3b82f6;
            color: #172554;
        }

        QPushButton:pressed {
            background-color: #7dd3fc;
            border-style: inset;
        }

        QPushButton:disabled {
            background-color: #e5e7eb;
            color: #9ca3af;
            border: 1px solid #d1d5db;
        }
    """)
    
    group_layout.addWidget(btn_edu)

    def launch_education_dialog():
        if not hasattr(app, 'current_base_chart') or not app.current_base_chart: return
        
        if not hasattr(app, '_edu_dialog') or app._edu_dialog is None:
            app._edu_dialog = EducationAnalysisDialog(app, app.current_base_chart, app)
            app._edu_dialog.showMaximized()
        else:
            app._edu_dialog.update_data(app.current_base_chart)
            app._edu_dialog.show()
            app._edu_dialog.raise_()
            app._edu_dialog.activateWindow()

    btn_edu.clicked.connect(launch_education_dialog)