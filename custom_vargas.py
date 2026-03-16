import json
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QSpinBox, QComboBox, QPushButton, QMessageBox, QFrame)
from PyQt6.QtCore import Qt

CUSTOM_FILE = "custom_vargas.json"

# Definition of the 8 missing classical Vargas to complete the standard 20 (Shadvarga + etc)
STANDARD_EXTRA_VARGAS = {
    "D3": {"name": "D3 (Drekkana)", "divs": 3, "logic": "drekkana"},
    "D5": {"name": "D5 (Panchamsha)", "divs": 5, "logic": "cyclical"},
    "D6": {"name": "D6 (Shashthamsha)", "divs": 6, "logic": "cyclical"},
    "D8": {"name": "D8 (Ashtamsha)", "divs": 8, "logic": "odd_aries_even_sag"},
    "D11": {"name": "D11 (Rudramsha)", "divs": 11, "logic": "odd_aries_even_libra"},
    "D27": {"name": "D27 (Bhamsha)", "divs": 27, "logic": "element_based"},
    "D40": {"name": "D40 (Khavedamsha)", "divs": 40, "logic": "odd_aries_even_libra"},
    "D45": {"name": "D45 (Akshavedamsha)", "divs": 45, "logic": "modality_based"}
}

def load_custom_rules():
    """Loads user-created custom varga rules from the local JSON file."""
    rules = {}
    if os.path.exists(CUSTOM_FILE):
        try:
            with open(CUSTOM_FILE, "r") as f:
                rules = json.load(f)
        except Exception as e:
            print(f"Error loading custom vargas: {e}")
    return rules

def get_all_extra_vargas():
    """Returns a combined dictionary of standard extra vargas + user custom vargas."""
    res = {k: v["name"] for k, v in STANDARD_EXTRA_VARGAS.items()}
    for k, v in load_custom_rules().items():
        res[k] = v["name"]
    return res

def get_varga_rule(div_id):
    if div_id in STANDARD_EXTRA_VARGAS:
        return STANDARD_EXTRA_VARGAS[div_id]
    customs = load_custom_rules()
    return customs.get(div_id)

def calculate_new_sign(sign_idx, deg_in_sign, rule):
    """
    Applies classical Vedic astrological calculations to determine the 
    destination sign in a specific divisional chart based on its rule.
    """
    divs = rule["divs"]
    logic = rule["logic"]
    part_size = 30.0 / divs
    
    part_num = int(deg_in_sign // part_size)
    if part_num >= divs: part_num = divs - 1

    if logic == "drekkana":
        if part_num == 0: return sign_idx
        elif part_num == 1: return (sign_idx + 4) % 12
        else: return (sign_idx + 8) % 12
    elif logic == "cyclical":
        return (sign_idx + part_num) % 12
    elif logic == "same_sign":
        return (sign_idx + part_num) % 12
    elif logic == "continuous_aries":
        return part_num % 12
    elif logic == "element_based":
        # Fire=0,4,8 -> Aries(0); Earth=1,5,9 -> Cancer(3); Air=2,6,10 -> Libra(6); Water=3,7,11 -> Capricorn(9)
        start_sign = (sign_idx % 4) * 3
        return (start_sign + part_num) % 12
    elif logic == "modality_based":
        # Movable=0,3,6,9 -> Aries(0); Fixed=1,4,7,10 -> Leo(4); Dual=2,5,8,11 -> Sagittarius(8)
        start_sign = (sign_idx % 3) * 4
        return (start_sign + part_num) % 12
    elif logic == "odd_aries_even_libra":
        start_sign = 0 if sign_idx % 2 == 0 else 6
        return (start_sign + part_num) % 12
    elif logic == "odd_aries_even_sag":
        start_sign = 0 if sign_idx % 2 == 0 else 8
        return (start_sign + part_num) % 12
    else:
        return sign_idx

def compute_divisional_chart(base_chart, div_id):
    """Computes the complete structural chart for a custom/extra division."""
    rule = get_varga_rule(div_id)
    if not rule: 
        return base_chart

    divs = rule["divs"]
    part_size = 30.0 / divs

    asc = base_chart["ascendant"]
    new_asc_sign = calculate_new_sign(asc["sign_index"], asc["degree"] % 30, rule)
    new_asc_deg = ((asc["degree"] % 30) % part_size) * divs
    new_asc = {
        "sign_index": new_asc_sign,
        "sign_num": new_asc_sign + 1,
        "degree": new_asc_deg,
        "div_lon": new_asc_sign * 30.0 + new_asc_deg,
        "vargottama": (new_asc_sign == asc["sign_index"])
    }

    new_planets = []
    exaltation_rules = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
    debilitation_rules = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
    sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}
    planet_lordships = {"Sun": [5], "Moon": [4], "Mars": [1, 8], "Mercury": [3, 6], "Jupiter": [9, 12], "Venus": [2, 7], "Saturn": [10, 11], "Rahu": [], "Ketu": []}

    for p in base_chart["planets"]:
        p_deg = p["deg_in_sign"]
        new_sign_idx = calculate_new_sign(p["sign_index"], p_deg, rule)
        new_sign_num = new_sign_idx + 1
        new_deg_in_sign = (p_deg % part_size) * divs

        is_exalted = False
        is_own = (sign_rulers.get(new_sign_num) == p["name"])
        is_debilitated = (new_sign_num == debilitation_rules.get(p["name"]))

        if p["name"] == "Moon" and new_sign_num == 2:
            is_own = True; is_exalted = False
        elif p["name"] == "Mercury" and new_sign_num == 6:
            is_exalted = True; is_own = False
        else:
            is_exalted = (new_sign_num == exaltation_rules.get(p["name"]))

        if p["name"] == "Moon" and new_sign_num == 8: is_debilitated = False
        elif p["name"] == "Mercury" and new_sign_num == 12: is_debilitated = True

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
            "vargottama": (new_sign_idx == p["sign_index"]),
            "lord_of": planet_lordships.get(p["name"], [])
        })
        new_planets.append(new_p)

    return {
        "ascendant": new_asc,
        "planets": new_planets,
        "aspects": base_chart.get("aspects", [])
    }


class CustomVargaDialog(QDialog):
    """UI Interface for users to manage (create/remove) custom divisional charts"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Custom Divisional Charts")
        self.resize(400, 420)
        
        # Fixed stylesheet to prevent invisible text on hover inside dropdown items
        self.setStyleSheet("""
            QDialog { background-color: #FAFAFA; font-family: 'Segoe UI'; font-size: 13px; }
            QLineEdit, QSpinBox, QComboBox { padding: 5px; border: 1px solid #CCC; border-radius: 4px; background: #FFF; color: #000; }
            QComboBox QAbstractItemView {
                background-color: #FFF;
                color: #000;
                selection-background-color: #E0E0E0;
                selection-color: #000;
            }
            QPushButton { padding: 6px; font-weight: bold; border-radius: 4px; }
            QPushButton#saveBtn { background-color: #27ae60; color: white; border: none; }
            QPushButton#saveBtn:hover { background-color: #219653; }
            QPushButton#delBtn { background-color: #e74c3c; color: white; border: none; }
            QPushButton#delBtn:hover { background-color: #c0392b; }
        """)
        
        layout = QVBoxLayout(self)

        # ---- CREATE SECTION ----
        layout.addWidget(QLabel("<h3 style='color:#2980b9;'>Create New Varga</h3>"))
        
        self.id_input = QLineEdit("D144")
        self.name_input = QLineEdit("My Custom Varga")
        self.divs_spin = QSpinBox()
        self.divs_spin.setRange(2, 500)
        self.divs_spin.setValue(144)

        self.logic_cb = QComboBox()
        self.logic_cb.addItems([
            "continuous_aries", "same_sign", "cyclical", "element_based",
            "modality_based", "odd_aries_even_libra", "odd_aries_even_sag", "drekkana"
        ])
        
        friendly_names = {
            "continuous_aries": "Continuous counting from Aries",
            "same_sign": "Start from the Planet's own sign",
            "cyclical": "Cyclic multiplication",
            "element_based": "Elements (Fire->Aries, Earth->Cancer, etc)",
            "modality_based": "Modality (Movable->Aries, Fixed->Leo, etc)",
            "odd_aries_even_libra": "Odd signs->Aries, Even signs->Libra",
            "odd_aries_even_sag": "Odd signs->Aries, Even signs->Sagittarius",
            "drekkana": "Parashari Drekkana Rules"
        }
        for i in range(self.logic_cb.count()):
            self.logic_cb.setItemData(i, friendly_names.get(self.logic_cb.itemText(i), ""), Qt.ItemDataRole.ToolTipRole)

        layout.addWidget(QLabel("<b>Varga ID</b> (e.g., D144):"))
        layout.addWidget(self.id_input)
        layout.addWidget(QLabel("<b>Display Name</b>:"))
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("<b>Number of Divisions</b> (Parts per Sign):"))
        layout.addWidget(self.divs_spin)
        layout.addWidget(QLabel("<b>Starting Sign Logic</b>:"))
        layout.addWidget(self.logic_cb)

        save_btn = QPushButton("Save & Apply")
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.save_custom)
        layout.addWidget(save_btn)

        # Visual Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addSpacing(15)
        layout.addWidget(line)
        layout.addSpacing(5)

        # ---- DELETE SECTION ----
        layout.addWidget(QLabel("<h3 style='color:#c0392b;'>Remove Existing Varga</h3>"))
        self.del_cb = QComboBox()
        
        # Populate with existing custom rules
        custom_rules = load_custom_rules()
        for k, v in custom_rules.items():
            self.del_cb.addItem(v["name"], k)
            
        layout.addWidget(self.del_cb)

        del_btn = QPushButton("Remove Selected")
        del_btn.setObjectName("delBtn")
        del_btn.clicked.connect(self.delete_custom)
        if not custom_rules:
            del_btn.setEnabled(False)
            self.del_cb.setEnabled(False)
            
        layout.addWidget(del_btn)

        layout.addStretch()
        btn_box = QHBoxLayout()
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addStretch()
        btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box)

    def save_custom(self):
        v_id = self.id_input.text().strip().upper()
        if not v_id:
            QMessageBox.warning(self, "Invalid ID", "Varga ID cannot be empty.")
            return
            
        if not v_id.startswith("D"): v_id = "D" + v_id
        
        rules = load_custom_rules()
        rules[v_id] = {
            "name": f"{v_id} ({self.name_input.text().strip()})",
            "divs": self.divs_spin.value(),
            "logic": self.logic_cb.currentText()
        }
        
        try:
            with open(CUSTOM_FILE, "w") as f:
                json.dump(rules, f, indent=4)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save rules:\n{str(e)}")

    def delete_custom(self):
        v_id = self.del_cb.currentData()
        if not v_id: return
        
        rules = load_custom_rules()
        if v_id in rules:
            del rules[v_id]
            try:
                with open(CUSTOM_FILE, "w") as f:
                    json.dump(rules, f, indent=4)
                QMessageBox.information(self, "Deleted", f"Successfully removed {v_id}.\nPlease restart the application for changes to take effect.")
                self.accept()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete rule:\n{str(e)}")