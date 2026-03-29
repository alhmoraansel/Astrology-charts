# dynamic_settings_modules/education_mod.py

import sys
import copy
import json
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, 
                             QLabel, QScrollArea, QGroupBox, QTextBrowser, QTabWidget,
                             QMenuBar, QFormLayout, QDoubleSpinBox, QDialogButtonBox, QApplication, QMessageBox)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QUrl

import main
import astro_engine
from chart_renderer import ChartAnalyzer, SIGN_LORDS, ChartRenderer

# Import the Live CSI Helper safely for end-of-analysis diagnostics ONLY
try:
    from dynamic_settings_modules.composite_strength_module import CSIHelper
except ImportError as e:
    CSIHelper = None

PLUGIN_INDEX = 1


# ==========================================
# GLOBAL DECIDING WEIGHTS & CONSTANTS
# ==========================================

# 1. House & Lord Influences
W_INFLUENCE_5TH_HOUSE = 0.4
W_INFLUENCE_5TH_LORD = 0.4
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

# 6. Varga Multipliers
W_D1_MULTIPLIER = 1.0           
W_D9_MULTIPLIER = 1.0           
W_D24_MULTIPLIER = 1.0          
W_DASHA_LAGNA_MULTIPLIER = 1.0  

# 7. Advanced Yogas
W_BUDHADITYA_TECH_BONUS = 0.3
W_BUDHADITYA_SEMI_BONUS = 0.4
W_SARASWATI_NON_TECH_BONUS = 0.8
W_SARASWATI_SEMI_BONUS = 0.5

# Map for Settings UI configuration
WEIGHTS_MAP = {
    "W_INFLUENCE_5TH_HOUSE": ("5th House Occupants/Aspects Weight", 0.0, 10.0, 0.1),
    "W_INFLUENCE_5TH_LORD": ("5th Lord Conjuncts/Aspects Weight", 0.0, 10.0, 0.1),
    "W_NAKSHATRA_5TH_LORD": ("5th Lord's Nakshatra Weight", 0.0, 10.0, 0.1),
    "W_MERCURY_FACTOR": ("Mercury Rule Weight (fraction of 5H)", 0.0, 2.0, 0.1),
    "W_TECH_RASHI_4TH": ("Technical Rashi (4th House) Weight", 0.0, 10.0, 0.1),
    "W_TECH_RASHI_5TH": ("Technical Rashi (5th House) Weight", 0.0, 10.0, 0.1),
    "W_TECH_PLANET": ("Technical Planet Core Multiplier", 0.0, 10.0, 0.1),
    "W_SEMI_TECH_PLANET": ("Semi-Tech Planet Core Multiplier", 0.0, 10.0, 0.1),
    "W_NON_TECH_PLANET": ("Non-Tech Planet Core Multiplier", 0.0, 10.0, 0.1),
    "AGE_OF_EDUCATION": ("Age of Education (Dasha Lock)", 1.0, 100.0, 1.0),
    "W_MAHADASHA_PLANET": ("Mahadasha Planet Weight", 0.0, 10.0, 0.5),
    "W_D1_MULTIPLIER": ("D-1 Varga Multiplier", 0.0, 5.0, 0.1),
    "W_D9_MULTIPLIER": ("D-9 Varga Multiplier", 0.0, 5.0, 0.1),
    "W_D24_MULTIPLIER": ("D-24 Varga Multiplier", 0.0, 5.0, 0.1),
    "W_DASHA_LAGNA_MULTIPLIER": ("Dasha Lagna Varga Multiplier", 0.0, 5.0, 0.1),
    "W_BUDHADITYA_TECH_BONUS": ("Budhaditya Yoga (Tech Bonus)", 0.0, 10.0, 0.1),
    "W_BUDHADITYA_SEMI_BONUS": ("Budhaditya Yoga (Semi-Tech Bonus)", 0.0, 10.0, 0.1),
    "W_SARASWATI_NON_TECH_BONUS": ("Saraswati Yoga (Non-Tech Bonus)", 0.0, 10.0, 0.1),
    "W_SARASWATI_SEMI_BONUS": ("Saraswati Yoga (Semi-Tech Bonus)", 0.0, 10.0, 0.1)
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
        except Exception as e:
            print(f"Error loading education weights: {e}")

# Load weights on module initialization
load_weights()

# 8. Basic Definitions
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
# USER WEIGHTS SETTINGS DIALOG
# ==========================================
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Algorithm Weights")
        self.resize(450, 700)
        
        # Removed heavy global stylesheet to optimize performance on older systems
        
        layout = QVBoxLayout(self)
        
        info_label = QLabel("Adjust core calculation variables. Changes apply dynamically upon saving.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Smooth Scroll for Settings
        import main
        SmoothScroller = getattr(main, 'SmoothScroller', None)
        if SmoothScroller:
            self.scroller = SmoothScroller(scroll)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        CATEGORIES = {
            "House & Lord Influences": ["W_INFLUENCE_5TH_HOUSE", "W_INFLUENCE_5TH_LORD", "W_NAKSHATRA_5TH_LORD", "W_MERCURY_FACTOR"],
            "Rashi Technicalities": ["W_TECH_RASHI_4TH", "W_TECH_RASHI_5TH"],
            "Planet Nature Multipliers": ["W_TECH_PLANET", "W_SEMI_TECH_PLANET", "W_NON_TECH_PLANET"],
            "Dasha & Timing": ["AGE_OF_EDUCATION", "W_MAHADASHA_PLANET"],
            "Varga Chart Weights": ["W_D1_MULTIPLIER", "W_D9_MULTIPLIER", "W_D24_MULTIPLIER", "W_DASHA_LAGNA_MULTIPLIER"],
            "Classical Yogas": ["W_BUDHADITYA_TECH_BONUS", "W_BUDHADITYA_SEMI_BONUS", "W_SARASWATI_NON_TECH_BONUS", "W_SARASWATI_SEMI_BONUS"]
        }
        
        self.spin_boxes = {}
        for cat_name, keys in CATEGORIES.items():
            # Using primitive QLabel instead of heavy QGroupBoxes for better system performance
            cat_label = QLabel(cat_name)
            cat_label.setStyleSheet("font-weight: bold; text-decoration: underline; margin-top: 10px;")
            content_layout.addWidget(cat_label)
            
            form = QFormLayout()
            form.setVerticalSpacing(8)
            for key in keys:
                if key in WEIGHTS_MAP:
                    name, min_val, max_val, step = WEIGHTS_MAP[key]
                    spin = QDoubleSpinBox() # Primitive native field
                    spin.setRange(min_val, max_val)
                    spin.setSingleStep(step)
                    spin.setDecimals(1)
                    spin.setValue(float(globals().get(key, 0.0)))
                    form.addRow(name, spin)
                    self.spin_boxes[key] = spin
            content_layout.addLayout(form)
            
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.save_and_accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
    def save_and_accept(self):
        saved_weights = {}
        for key, spin in self.spin_boxes.items():
            val = spin.value()
            globals()[key] = val
            saved_weights[key] = val
            
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(saved_weights, f, indent=4)
            QMessageBox.information(self, "Settings Saved", "Algorithm weights have been successfully saved to disk and applied globally.")
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", f"Error saving education weights securely:\n{e}")
            
        self.accept()


# ==========================================
# EDUCATION CALCULATOR ENGINE
# ==========================================
class EducationCalculator:
    def __init__(self, chart_data, d9_data=None, d24_data=None):
        self.chart_data = chart_data
        self.d9_data = d9_data
        self.d24_data = d24_data
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

        if is_acting_malefic:
            base_reason = "Malefic/Afflicted"
            if in_tech_rashi: 
                return "Technical", W_TECH_PLANET, f"{base_reason} in {rashi_str}"
            else: 
                return "Semi-Technical", W_SEMI_TECH_PLANET, f"{base_reason} in {rashi_str}"
        else:
            base_reason = "Unafflicted Benefic"
            if in_tech_rashi: 
                return "Semi-Technical", W_SEMI_TECH_PLANET, f"{base_reason} in {rashi_str}"
            else: 
                return "Non-Technical", W_NON_TECH_PLANET, f"{base_reason} in {rashi_str}"

    def _process_influences(self, analyzer, target_name, occupant_list, aspect_list, base_weight, mult, target_desc, asc_override_idx=None):
        for p in occupant_list:
            p_name = p if isinstance(p, str) else p.get("name")
            if not p_name: continue
            
            cat, p_wt, reason = self._classify_planet(p_name, analyzer, asc_override_idx)
            final_wt = base_weight * p_wt * mult
            self.scores[cat] += final_wt
            self.dominant_planet_scores[p_name] += final_wt
            
            self.log.append(f"<li><b>{p_name}</b> occupies/conjuncts {target_name} &rarr; <b style='color:#0284C7;'>{cat}</b> (+{final_wt:.2f}) <br>"
                            f"<span style='color:#64748B; font-size: 11px;'><i>Reason: {reason}. Math: {target_desc} (w={base_weight:.2f}) * Planet Wt (w={p_wt:.2f}) * Chart Mult (w={mult:.2f}) = {final_wt:.2f}</i></span></li>")
            
        for p in aspect_list:
            p_name = p if isinstance(p, str) else p.get("aspecting_planet")
            if not p_name: continue
            
            cat, p_wt, reason = self._classify_planet(p_name, analyzer, asc_override_idx)
            final_wt = base_weight * p_wt * mult
            self.scores[cat] += final_wt
            self.dominant_planet_scores[p_name] += final_wt
            
            self.log.append(f"<li><b>{p_name}</b> aspects {target_name} &rarr; <b style='color:#0284C7;'>{cat}</b> (+{final_wt:.2f}) <br>"
                            f"<span style='color:#64748B; font-size: 11px;'><i>Reason: {reason}. Math: {target_desc} (w={base_weight:.2f}) * Planet Wt (w={p_wt:.2f}) * Chart Mult (w={mult:.2f}) = {final_wt:.2f}</i></span></li>")

    def _eval_varga_chart(self, chart, name, mult, asc_override_idx=None):
        if not chart: return
        self.log.append(f"<div style='margin-bottom: 15px; border-left: 3px solid #0284C7; padding-left: 10px;'>")
        self.log.append(f"<h3 style='color:#0284C7; margin-bottom: 4px;'>--- {name.upper()} ANALYSIS ---</h3><ul>")
        
        analyzer = ChartAnalyzer(chart)
        original_asc_idx = chart["ascendant"]["sign_index"]
        
        asc_idx = asc_override_idx if asc_override_idx is not None else original_asc_idx
        
        h4_sign_idx = (asc_idx + 3) % 12
        h5_sign_idx = (asc_idx + 4) % 12
        
        h4_sign = h4_sign_idx + 1
        h5_sign = h5_sign_idx + 1
        
        self.log.append("<b>1. CHECKING RASHI:</b><br>")
        if h4_sign in TECH_RASHIS:
            self.scores["Technical"] += W_TECH_RASHI_4TH * mult
            self.log.append(f"<li>4th House Sign ({h4_sign}) is Technical &rarr; <b style='color:#0284C7;'>Technical</b> (+{W_TECH_RASHI_4TH * mult:.2f})</li>")
        else:
            self.scores["Non-Technical"] += W_TECH_RASHI_4TH * mult
            self.log.append(f"<li>4th House Sign ({h4_sign}) is Non-Technical &rarr; <b style='color:#0284C7;'>Non-Technical</b> (+{W_TECH_RASHI_4TH * mult:.2f})</li>")
            
        if h5_sign in TECH_RASHIS:
            self.scores["Technical"] += W_TECH_RASHI_5TH * mult
            self.log.append(f"<li>5th House Sign ({h5_sign}) is Technical &rarr; <b style='color:#0284C7;'>Technical</b> (+{W_TECH_RASHI_5TH * mult:.2f})</li>")
        else:
            self.scores["Non-Technical"] += W_TECH_RASHI_5TH * mult
            self.log.append(f"<li>5th House Sign ({h5_sign}) is Non-Technical &rarr; <b style='color:#0284C7;'>Non-Technical</b> (+{W_TECH_RASHI_5TH * mult:.2f})</li>")

        self.log.append("<br><b>2. CHECKING 5TH HOUSE INFLUENCE:</b><br>")
        h5_original_house_num = ((h5_sign_idx - original_asc_idx) % 12) + 1
        h5_occ = analyzer.get_occupants(h5_original_house_num)
        h5_asp = analyzer.get_aspecting_planets(h5_original_house_num)
        
        if not h5_occ and not h5_asp:
            self.log.append("<li>No planets occupying or aspecting 5th house.</li>")
        else:
            self._process_influences(analyzer, "5th House", h5_occ, h5_asp, W_INFLUENCE_5TH_HOUSE, mult, f"w={W_INFLUENCE_5TH_HOUSE:.2f}", asc_override_idx)

        self.log.append("<br><b>3. CHECKING 5TH LORD INFLUENCE:</b><br>")
        l5_name = SIGN_LORDS.get(h5_sign)
        if l5_name:
            l5_p = analyzer.get_planet(l5_name)
            if l5_p:
                l5_original_house_num = l5_p["house"]
                
                l5_conj = analyzer.get_conjunct_planets(l5_name)
                l5_asp = analyzer.get_aspecting_planets(l5_original_house_num)
                if l5_name in l5_asp: l5_asp.remove(l5_name)
                
                if not l5_conj and not l5_asp:
                    self.log.append(f"<li>No planets conjunct or aspecting 5th Lord ({l5_name}).</li>")
                else:
                    self._process_influences(analyzer, f"5th Lord ({l5_name})", l5_conj, l5_asp, W_INFLUENCE_5TH_LORD, mult, f"w={W_INFLUENCE_5TH_LORD:.2f}", asc_override_idx)
                    
                nak_lord = l5_p.get("nakshatra_lord")
                if nak_lord:
                    cat, n_wt, reason = self._classify_planet(nak_lord, analyzer, asc_override_idx)
                    final_n_wt = W_NAKSHATRA_5TH_LORD * n_wt * mult
                    self.scores[cat] += final_n_wt
                    self.dominant_planet_scores[nak_lord] += final_n_wt
                    self.log.append(f"<li>Nakshatra Lord of 5th Lord is <b>{nak_lord}</b> &rarr; <b style='color:#0284C7;'>{cat}</b> (+{final_n_wt:.2f}) <br>"
                                    f"<span style='color:#64748B; font-size: 11px;'><i>Reason: {reason}. Math: Nak Wt (w={W_NAKSHATRA_5TH_LORD:.2f}) * Planet Wt (w={n_wt:.2f}) * Chart Mult (w={mult:.2f}) = {final_n_wt:.2f}</i></span></li>")
        else:
            self.log.append("<li>Could not determine 5th lord.</li>")

        self.log.append(f"<br><b>4. REPEATING PROCESS FROM MERCURY (1/5th Weight - w={W_MERCURY_FACTOR}):</b><br>")
        merc = analyzer.get_planet("Mercury")
        if merc:
            merc_sign_idx = merc["sign_index"]
            merc_h5_sign_idx = (merc_sign_idx + 4) % 12
            merc_h5_sign = merc_h5_sign_idx + 1
            
            if merc_h5_sign in TECH_RASHIS:
                self.scores["Technical"] += W_TECH_RASHI_5TH * W_MERCURY_FACTOR * mult
                self.log.append(f"<li>5th House from Mercury Sign ({merc_h5_sign}) is Technical &rarr; <b style='color:#0284C7;'>Technical</b> (+{W_TECH_RASHI_5TH * W_MERCURY_FACTOR * mult:.2f})</li>")
            else:
                self.scores["Non-Technical"] += W_TECH_RASHI_5TH * W_MERCURY_FACTOR * mult
                self.log.append(f"<li>5th House from Mercury Sign ({merc_h5_sign}) is Non-Technical &rarr; <b style='color:#0284C7;'>Non-Technical</b> (+{W_TECH_RASHI_5TH * W_MERCURY_FACTOR * mult:.2f})</li>")

            merc_h5_original_house_num = ((merc_h5_sign_idx - original_asc_idx) % 12) + 1
            m_h5_occ = analyzer.get_occupants(merc_h5_original_house_num)
            m_h5_asp = analyzer.get_aspecting_planets(merc_h5_original_house_num)
            self._process_influences(analyzer, "5th House from Mercury", m_h5_occ, m_h5_asp, W_INFLUENCE_5TH_HOUSE * W_MERCURY_FACTOR, mult, "w=0.08", asc_override_idx)
            
            m_l5_name = SIGN_LORDS.get(merc_h5_sign)
            if m_l5_name:
                m_l5_p = analyzer.get_planet(m_l5_name)
                if m_l5_p:
                    m_l5_original_house_num = m_l5_p["house"]
                    m_l5_conj = analyzer.get_conjunct_planets(m_l5_name)
                    m_l5_asp = analyzer.get_aspecting_planets(m_l5_original_house_num)
                    if m_l5_name in m_l5_asp: m_l5_asp.remove(m_l5_name)
                    
                    self._process_influences(analyzer, f"5th Lord from Mercury ({m_l5_name})", m_l5_conj, m_l5_asp, W_INFLUENCE_5TH_LORD * W_MERCURY_FACTOR, mult, "w=0.08", asc_override_idx)
                    
                    m_nak_lord = m_l5_p.get("nakshatra_lord")
                    if m_nak_lord:
                        cat, n_wt, reason = self._classify_planet(m_nak_lord, analyzer, asc_override_idx)
                        final_n_wt = W_NAKSHATRA_5TH_LORD * W_MERCURY_FACTOR * n_wt * mult
                        self.scores[cat] += final_n_wt
                        self.dominant_planet_scores[m_nak_lord] += final_n_wt
                        self.log.append(f"<li>Nakshatra Lord of Merc's 5L is <b>{m_nak_lord}</b> &rarr; <b style='color:#0284C7;'>{cat}</b> (+{final_n_wt:.2f}) <br>"
                                        f"<span style='color:#64748B; font-size: 11px;'><i>Reason: {reason}. Math: Nak Wt (w=0.02) * Planet Wt (w={n_wt:.2f}) * Chart Mult (w={mult:.2f}) = {final_n_wt:.2f}</i></span></li>")
        else:
            self.log.append("<li>Mercury data missing.</li>")
        self.log.append("</ul></div>")

    def _eval_knowledge_yogas(self):
        self.log.append(f"<div style='margin-bottom: 15px; border-left: 3px solid #D97706; padding-left: 10px;'>")
        self.log.append(f"<h3 style='color:#D97706; margin-bottom: 4px;'>--- KNOWLEDGE YOGAS ---</h3><ul>")
        
        sun_h = self.analyzer_d1.get_house_of("Sun")
        mer_h = self.analyzer_d1.get_house_of("Mercury")
        ven_h = self.analyzer_d1.get_house_of("Venus")
        jup_h = self.analyzer_d1.get_house_of("Jupiter")
        
        yogas_found = False

        if sun_h and mer_h and sun_h == mer_h:
            yogas_found = True
            self.scores["Technical"] += W_BUDHADITYA_TECH_BONUS
            self.scores["Semi-Technical"] += W_BUDHADITYA_SEMI_BONUS
            self.dominant_planet_scores["Sun"] += W_BUDHADITYA_TECH_BONUS
            self.dominant_planet_scores["Mercury"] += W_BUDHADITYA_SEMI_BONUS
            self.log.append(f"<li><b>Budhaditya Yoga</b> detected in D1. Tech (+{W_BUDHADITYA_TECH_BONUS}), Semi-Tech (+{W_BUDHADITYA_SEMI_BONUS}).</li>")

        kendra_trikona = [1, 4, 5, 7, 9, 10]
        if mer_h in kendra_trikona and ven_h in kendra_trikona and jup_h in kendra_trikona:
            yogas_found = True
            self.scores["Non-Technical"] += W_SARASWATI_NON_TECH_BONUS
            self.scores["Semi-Technical"] += W_SARASWATI_SEMI_BONUS
            self.dominant_planet_scores["Jupiter"] += W_SARASWATI_NON_TECH_BONUS
            self.dominant_planet_scores["Venus"] += W_SARASWATI_SEMI_BONUS
            self.dominant_planet_scores["Mercury"] += W_SARASWATI_SEMI_BONUS
            self.log.append(f"<li><b>Saraswati Yoga</b> detected in D1. Non-Tech (+{W_SARASWATI_NON_TECH_BONUS}), Semi-Tech (+{W_SARASWATI_SEMI_BONUS}).</li>")

        if not yogas_found:
            self.log.append("<li>No major classical knowledge Yogas detected in D-1.</li>")
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

        if best_h in [4]: return "Foundation (4H)", f"Points heavily directed at 4th House"
        if best_h in [6, 8, 12]: return "Medical/Occult (6/8/12H)", f"Points heavily directed at Dusthanas (6/8/12)"
        if best_h in [3, 7, 9]: return "Communication (3/7/9H)", f"Points heavily directed at 3/7/9 Houses"
        if best_h in [2, 11]: return "Finance (2/11H)", f"Points heavily directed at Wealth Houses (2/11)"
        if best_h in [10]: return "Authority (10H)", f"Points heavily directed at 10th House"
        
        return "General (1/5H)", f"Points directed at 1/5 Axis"

    def _filter_exact_profession(self, prof_list, theme):
        if not prof_list: return "Undecided"
        if len(prof_list) == 1: return prof_list[0]

        theme_keywords = {
            "Foundation (4H)": ["architecture", "land", "agriculture", "botany", "mula", "mechanical", "mechanic", "hotel", "geology", "designing", "property", "engineering", "science", "civil", "construction", "interior"],
            "Medical/Occult (6/8/12H)": ["medicine", "ayurvedic", "pharmacy", "biochemistry", "biology", "zoology", "paramedics", "psychology", "astrology", "prachin vidya", "archaeology", "research", "microbiology", "genetics", "speech", "nursing", "pathology", "surgery"],
            "Communication (3/7/9H)": ["journalism", "public relation", "tourism", "photography", "pilot", "aviation", "languages", "law", "air hostess", "aerospace", "telecommunication", "media", "animation"],
            "Finance (2/11H)": ["accountancy", "commerce", "finance", "banking", "actuary", "statistics", "economics", "management", "financial"],
            "Authority (10H)": ["political science", "management", "public relation", "engineering", "electrical", "defense", "law", "administration", "control", "production"],
            "General (1/5H)": ["mathematics", "physics", "chemistry", "fine arts", "humanities", "music", "dance", "literature", "history", "sanskrit", "sociology", "painting", "computer"]
        }
        
        keywords = theme_keywords.get(theme, [])
        
        valid_matches = []
        for prof in prof_list:
            prof_lower = prof.lower()
            for kw in keywords:
                if kw in prof_lower:
                    if prof not in valid_matches:
                        valid_matches.append(prof)

        if len(valid_matches) > 0:
            return " / ".join(valid_matches)
        
        return " / ".join(prof_list)

    def run_analysis(self, app_instance=None):
        self.log.append("<h2>Four-Step Triangulation Process</h2>")
        self.log.append("<p style='font-size:12px; color:#64748B;'>Applying identical logic rules across D1, D9, D24, and D-1 (Age 18 Dasha Lagna).</p>")
        
        # Step 1, 2, 3: Core Varga Evaluations 
        self._eval_varga_chart(self.chart_data, "Step 1: D-1 Base Chart", W_D1_MULTIPLIER, asc_override_idx=None)
        self._eval_varga_chart(self.d9_data, "Step 2: D-9 Navamsha", W_D9_MULTIPLIER, asc_override_idx=None)
        self._eval_varga_chart(self.d24_data, "Step 3: D-24 Siddhamsa", W_D24_MULTIPLIER, asc_override_idx=None)
        
        # Step 4: Mahadasha Evaluation
        jd_utc = self.chart_data.get("current_jd")
        moon_p = self.analyzer_d1.get_planet("Moon")
        
        self.log.append(f"<div style='margin-bottom: 15px; border-left: 3px solid #8B5CF6; padding-left: 10px;'>")
        self.log.append(f"<h3 style='color:#8B5CF6; margin-bottom: 4px;'>--- STEP 4: D-1 DASHA LAGNA (AGE {AGE_OF_EDUCATION}) ANALYSIS ---</h3><ul>")
        if jd_utc and moon_p:
            target_jd = jd_utc + (AGE_OF_EDUCATION * 365.2421904)
            engine = astro_engine.EphemerisEngine()
            dasha_data = engine.calculate_vimshottari_dasha(jd_utc, moon_p["lon"], target_jd)
            dasha_seq = dasha_data.get("current_sequence", [])
            
            if dasha_seq and len(dasha_seq) > 0:
                md_lord = dasha_seq[0]
                md_p = self.analyzer_d1.get_planet(md_lord)
                if md_p:
                    md_sign_idx = md_p["sign_index"]
                    self.log.append(f"<li>Dasha Lord at Age {AGE_OF_EDUCATION} is {md_lord}. Processing chart with {md_lord}'s sign as Lagna.</li></ul></div>")
                    self._eval_varga_chart(self.chart_data, f"Step 4: D-1 Dasha Lagna ({md_lord})", W_DASHA_LAGNA_MULTIPLIER, asc_override_idx=md_sign_idx)
                else:
                    self.log.append(f"<li>Could not find {md_lord} in chart. Skipping Step 4.</li></ul></div>")
            else:
                self.log.append("<li>Could not compute Dasha timing. Skipping Step 4.</li></ul></div>")
        else:
            self.log.append("<li>Missing JD or Moon data for Dasha. Skipping Step 4.</li></ul></div>")

        # Step 5: Aggregating Results
        self.log.append(f"<div style='margin-bottom: 15px; border-left: 3px solid #10B981; padding-left: 10px;'>")
        self.log.append(f"<h3 style='color:#10B981; margin-bottom: 4px;'>--- STEP 5: AGGREGATING FINAL RESULTS ---</h3><ul>")

        winner_cat = max(self.scores, key=self.scores.get)
        self.log.append(f"<li><b>1. Dominant Category Selected:</b> {winner_cat} (Score: {self.scores[winner_cat]:.2f})</li>")
        
        dom_planet = max(self.dominant_planet_scores, key=self.dominant_planet_scores.get)
        self.log.append(f"<li><b>2. Planetary Influence Selected:</b> {dom_planet} (Score: {self.dominant_planet_scores[dom_planet]:.2f})</li>")
        
        prof_list = RAW_PROFESSIONS.get(winner_cat, {}).get(dom_planet, ["General Studies"])
        self.log.append(f"<li><b>3. Available Options for {dom_planet} ({winner_cat}):</b> [{', '.join(prof_list)}]</li>")
        
        theme, theme_reason = self._find_house_theme(dom_planet)
        self.log.append(f"<li><b>4. House Result:</b> {theme} - {theme_reason}</li>")
        
        exact_degree = self._filter_exact_profession(prof_list, theme)
        eliminated = [p for p in prof_list if p not in exact_degree.split(" / ")]
        elim_str = " / ".join(eliminated) if eliminated else "None"
        self.log.append(f"<li><b>5. House Theme Filtering:</b> {theme} narrowed the selection down to <b>{exact_degree}</b>. (Eliminated options: {elim_str})</li>")
        
        nak_lord = self.analyzer_d1.get_nakshatra_lord(dom_planet)
        if not nak_lord: nak_lord = "Ketu"
        self.log.append(f"<li><b>6. Final Nakshatra Influence:</b> Star of {nak_lord}</li></ul></div>")

        logic_str = (
            f"<b>1. Dominant Category Selected:</b> {winner_cat} (Score: {self.scores[winner_cat]:.2f})<br>"
            f"<b>2. Planetary Influence Selected:</b> {dom_planet} (Score: {self.dominant_planet_scores[dom_planet]:.2f})<br>"
            f"<b>3. Available Options for {dom_planet} ({winner_cat}):</b> [{', '.join(prof_list)}]<br>"
            f"<b>4. House Result:</b> {theme} - {theme_reason}<br>"
            f"<b>5. House Theme Filtering:</b> {theme} narrowed the selection down to <b>{exact_degree}</b>. (Eliminated options: {elim_str})<br>"
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

        return {
            "exact_degree": exact_degree,
            "winner_cat": winner_cat,
            "theme": theme,
            "dom_planet": dom_planet,
            "nak_lord": nak_lord,
            "logic_str": logic_str,
            "eliminated_str": elim_str,
            "log": "".join(self.log),
            "scores": self.scores,
            "csi_4": csi_4,
            "csi_5": csi_5,
            "csi_9": csi_9
        }

# ==========================================
# EDUCATION UI DIALOG
# ==========================================
class EducationAnalysisDialog(QDialog):
    def __init__(self, app_instance, chart_data, parent=None):
        super().__init__(parent)
        self.app = app_instance
        self.chart_data = chart_data
        self.time_logs = {} # Cache to store offset specific logs
        
        engine = astro_engine.EphemerisEngine()
        self.d9_data = engine.compute_divisional_chart(self.chart_data, "D9")
        self.d24_data = engine.compute_divisional_chart(self.chart_data, "D24")

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

        # Main Layout restructuring to support top Menu Bar
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Menu Bar for Settings
        self.menu_bar = QMenuBar()
        self.menu_bar.setStyleSheet("background-color: #E2E8F0; padding: 4px;")
        settings_action = self.menu_bar.addAction("⚙️ Configure Algorithm Weights")
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
        summary_layout.addStretch() # Pushes the label to the top safely
        self.summary_group.setLayout(summary_layout)
        self.left_layout.addWidget(self.summary_group)
        self.left_layout.addStretch() # Pushes the group box to the top
        
        # Changed panel ratio: Left gets 1 part, right gets 2 parts
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
        
        # Algorithmic Trail UI Init
        self.log_tab = QWidget()
        log_tab_layout = QVBoxLayout(self.log_tab)
        self.log_browser = QTextBrowser()
        
        SmoothScroller = getattr(main, 'SmoothScroller', None)
        if SmoothScroller:
            self.scroller = SmoothScroller(self.log_browser)
            
        log_tab_layout.addWidget(self.log_browser)
        
        # Build Standard Tabs
        self.right_panel.addTab(self.d1_chart_ui, "D-1 Base Chart")
        self.right_panel.addTab(self.d9_chart_ui, "D-9 Navamsha")
        self.right_panel.addTab(self.d24_chart_ui, "D-24 Siddhamsa")
        self.right_panel.addTab(self.log_tab, "Algorithmic Trail")
        
        # --- Time Sensitivity Tab ---
        self.time_mod_tab = QWidget()
        time_mod_layout = QVBoxLayout(self.time_mod_tab)
        
        time_top_bar = QHBoxLayout()
        self.btn_run_time_mod = QPushButton("Run Sensitivity Analysis (±60 mins)")
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
        
        self.right_panel.addTab(self.time_mod_tab, "Time Sensitivity (±60m)")
        # ----------------------------
        
        self.content_layout.addWidget(self.right_panel, stretch=2)
        self.refresh_analysis()

    def open_settings(self):
        dlg = SettingsDialog(self)
        if dlg.exec():
            self.refresh_analysis()

    def on_time_link_clicked(self, url):
        """Swaps the Algorithmic Trail to the requested specific time offset."""
        offset_str = url.toString()
        if offset_str in self.time_logs:
            self.log_browser.setHtml(self.time_logs[offset_str])
            # Auto-switch to the Algorithmic Trail tab for instant viewing
            idx = self.right_panel.indexOf(self.log_tab)
            if idx != -1:
                self.right_panel.setCurrentIndex(idx)

    def refresh_analysis(self):
        calc = EducationCalculator(self.chart_data, self.d9_data, self.d24_data)
        res = calc.run_analysis(self.app)
        
        # Cache the current exact log for the link handler
        self.time_logs["0"] = res["log"]
        
        rec_str = "<div style='color: #0F172A; margin-bottom: 12px; padding: 12px; background-color: #F0FDF4; border: 1px solid #10B981; border-radius: 6px;'>"
        rec_str += f"<h3 style='margin-top:0; margin-bottom: 6px; color:#047857;'>Educational Degree Prediction</h3>"
        rec_str += f"<div style='font-size: 22px; font-weight: bold; color: #4F46E5; margin-bottom: 12px;'>► {res['exact_degree']}</div>"
        rec_str += f"<div style='font-size: 13px; color: #475569; line-height: 1.5;'>{res['logic_str']}</div>"
        rec_str += "</div>"

        rec_str += "<div style='background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 4px; padding: 10px; margin-top: 10px;'>"
        rec_str += "<h4 style='margin-top: 0; margin-bottom: 6px; color: #334155;'>Computed Stream Category Scores</h4>"
        rec_str += "<ul style='margin-bottom: 0; padding-left: 20px; font-size: 13px; color: #475569;'>"
        rec_str += f"<li><b>Technical:</b> {res['scores']['Technical']:.2f}</li>"
        rec_str += f"<li><b>Semi-Technical:</b> {res['scores']['Semi-Technical']:.2f}</li>"
        rec_str += f"<li><b>Non-Technical:</b> {res['scores']['Non-Technical']:.2f}</li>"
        rec_str += "</ul></div>"
        
        self.lbl_recommendations.setText(rec_str)
        self.log_browser.setHtml(res["log"])

    def _approximate_chart_for_offset(self, base_chart, offset_mins):
        """Robust fallback to synthesize chart shift when main engine recalc is inaccessible."""
        new_chart = copy.deepcopy(base_chart)
        new_chart["current_jd"] = base_chart["current_jd"] + (offset_mins / 1440.0)
        
        # Approximate Ascendant shift (approx 1 degree per 4 minutes)
        deg_shift = offset_mins / 4.0
        
        # Safely handle missing 'lon' key for ascendant
        asc_lon = new_chart.get("ascendant", {}).get("lon")
        if asc_lon is None:
            # Try to calculate base ascendant longitude using astro_engine mathematically
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
                    
                # Fallback: estimate longitude from sign_index (middle of the sign)
                asc_sign_idx = new_chart.get("ascendant", {}).get("sign_index", 0)
                asc_lon = (asc_sign_idx * 30.0) + 15.0
            
        new_asc_lon = (asc_lon + deg_shift) % 360.0
        new_chart["ascendant"]["lon"] = new_asc_lon
        new_asc_sign = int(new_asc_lon // 30)
        new_chart["ascendant"]["sign_index"] = new_asc_sign
        
        # Approximate Moon shift (approx 0.5 degrees per hour)
        for p in new_chart.get("planets", []):
            if p["name"] == "Moon":
                # Safely handle missing 'lon' key for Moon
                p_lon = p.get("lon")
                if p_lon is None:
                    try:
                        res = astro_engine.fallback_planet_calc(base_chart["current_jd"], "Moon")
                        p_lon = res[0]
                    except Exception:
                        p_lon = (p.get("sign_index", 0) * 30.0) + 15.0
                p["lon"] = (p_lon + (offset_mins * 0.008333)) % 360.0
                p["sign_index"] = int(p["lon"] // 30)
            
            # Reposition functional houses mathematically
            p["house"] = ((p["sign_index"] - new_asc_sign) % 12) + 1
            
        return new_chart

    def run_time_sensitivity(self):
        self._shown_lon_error = False
        self.btn_run_time_mod.setText("Calculating (Please wait...)")
        self.btn_run_time_mod.setEnabled(False)
        QApplication.processEvents()
        
        html = "<h3 style='color: #0F172A; margin-bottom: 16px; margin-top: 5px;'>Time Fluctuation Analysis</h3>"
        html += "<table width='100%' style='border-collapse: separate; border-spacing: 0 10px;'>"
        
        offsets = list(range(-60, 65, 5))
        engine = astro_engine.EphemerisEngine()
        lat = self.chart_data.get("lat", 0.0)
        lon = self.chart_data.get("lon", 0.0)
        tz = self.chart_data.get("tz", 5.5)
        
        for offset in offsets:
            shifted_d1 = None
            used_approx = False
            
            if offset == 0:
                shifted_d1 = self.chart_data
                shifted_d9 = self.d9_data
                shifted_d24 = self.d24_data
            else:
                new_jd = self.chart_data["current_jd"] + (offset / 1440.0)
                
                try:
                    if hasattr(self.app, 'calculate_chart_for_jd'):
                        shifted_d1 = self.app.calculate_chart_for_jd(new_jd)
                    elif hasattr(self.app, 'engine') and hasattr(self.app.engine, 'calculate_chart_data'):
                        shifted_d1 = self.app.engine.calculate_chart_data(new_jd, lat, lon, tz)
                except Exception:
                    pass
                
                if not shifted_d1:
                    shifted_d1 = self._approximate_chart_for_offset(self.chart_data, offset)
                    used_approx = True
                    
                if shifted_d1:
                    shifted_d9 = engine.compute_divisional_chart(shifted_d1, "D9")
                    shifted_d24 = engine.compute_divisional_chart(shifted_d1, "D24")
                
            if shifted_d1:
                calc = EducationCalculator(shifted_d1, shifted_d9, shifted_d24)
                res = calc.run_analysis(self.app)
                
                # Caching this offset's detailed trail for clickable links
                self.time_logs[str(offset)] = res["log"]
                
                output_html = f"<div style='font-size: 18px; font-weight: bold; color: #4F46E5; margin-bottom: 8px;'>► {res['exact_degree']}</div>"
                if res.get('eliminated_str') and res['eliminated_str'] != "None":
                    output_html += f"<div style='font-size: 12px; color: #DC2626; margin-bottom: 8px;'><b>Eliminated Options:</b> {res['eliminated_str']}</div>"
                output_html += f"<div style='font-size: 13px; color: #334155; line-height: 1.5;'>{res['logic_str']}</div>"
                
                # Interactive Link addition
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
        
        self.btn_run_time_mod.setText("Run Sensitivity Analysis (±60 mins)")
        self.btn_run_time_mod.setEnabled(True)


# ==========================================
# PLUGIN ENTRY POINT
# ==========================================
def setup_ui(app, layout):
    shared_group_id = "AdvancedAstroGroup"
    shared_group = None
    for i in range(layout.count()):
        w = layout.itemAt(i).widget()
        if w and w.objectName() == shared_group_id:
            shared_group = w
            break
    
    if not shared_group:
        from PyQt6.QtWidgets import QGroupBox
        shared_group = QGroupBox("Advanced Analysis")
        shared_group.setObjectName(shared_group_id)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(6, 6, 6, 6)
        group_layout.setSpacing(6)
        shared_group.setLayout(group_layout)
        layout.addWidget(shared_group)
        
    target_layout = shared_group.layout()

    btn_edu = QPushButton("Educational Degree")
    btn_edu.setStyleSheet("""
        QPushButton { background-color: #4F46E5; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; margin-top: 4px;}
        QPushButton:hover { background-color: #4338CA; }
        QPushButton:disabled { background-color: #C7D2FE; color: #3730A3; }
    """)
    target_layout.addWidget(btn_edu)

    def launch_education_dialog():
        if not hasattr(app, 'current_base_chart') or not app.current_base_chart: return
        app._edu_dialog = EducationAnalysisDialog(app, app.current_base_chart, app)
        app._edu_dialog.showMaximized()

    btn_edu.clicked.connect(launch_education_dialog)