# dynamic_settings_modules/composite_strength_mod.py
import sys, math, json, os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QScrollArea, QGroupBox, QFrame, QCheckBox, QSizePolicy, QDoubleSpinBox, QGridLayout)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPolygonF, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer, QObject, pyqtSignal
import main

# Attempt to load SmoothScroller from the main application namespace safely
SmoothScroller = getattr(main, 'SmoothScroller', None)
info_print = getattr(main, 'info_print', print)
error_print = getattr(main, 'error_print', print)

import astro_engine

PLUGIN_GROUP = "STRENGTHS"
PLUGIN_INDEX = 40

# ==============================================================================
# GLOBAL WEIGHTS & PERSISTENCE
# ==============================================================================
MIN_CHART_SIZE = 400                   # Global variable for minimum chart size

DEFAULT_CSI_WEIGHTS = {
    # Planetary Base Weights
    "SHADBALA_NORM_WEIGHT": 0.50,      
    "ASHTAKAVARGA_SAV_WEIGHT": 0.25,   
    "AVASTHA_DIGNITY_WEIGHT": 0.25,    
    
    # Planetary Penalties and Modifiers
    "COMBUSTION_PENALTY": -0.25,       
    "RETROGRADE_MODIFIER": 0.15,       
    "ECLIPSE_NODE_PENALTY": -0.20,     
    
    # Special Override Rules
    "SPECIAL_RULE_EXCHANGE_BONUS": 0.15,         # Parivartana Yoga
    "SPECIAL_RULE_INDIRECT_EXCHANGE_BONUS": 0.00,# Parivartana Yoga (Indirect)
    "SPECIAL_RULE_VIPARITA_BONUS": 0.00,         # Viparita Raja Yoga (Set to 0 default)
    "SPECIAL_RULE_INDIRECT_VIPARITA_BONUS": 0.00,# Viparita Raja Yoga (Indirect)
    "SPECIAL_RULE_VIPARITA_CANCELLED_BONUS": 0.00, 
    "SPECIAL_RULE_LAGNA_TRIK_BHAVA_PENALTY": -0.40,
    
    # Exaltation & Debilitation Special Modifiers
    "SPECIAL_RULE_EXALTED_OCCUPANT_BONUS": 0.30, 
    "SPECIAL_RULE_EXALTED_LORD_BONUS": 0.00,     
    "SPECIAL_RULE_DEB_OCCUPANT_PENALTY": 0.00,   
    "SPECIAL_RULE_DEB_LORD_PENALTY": 0.00,       

    # Functional Mode Planetary Modifiers 
    "FUNC_LORD_FRIEND_MODIFIER": 0.15, 
    "FUNC_LORD_ENEMY_PENALTY": 0.00,  
    
    # Functional Mode HOUSE Modifiers
    "FUNC_HOUSE_LORD_BENEFIC_BONUS": 0.00,     
    "FUNC_HOUSE_LORD_MALEFIC_PENALTY": 0.00,  
    "FUNC_HOUSE_LORD_FRIEND_PLC_BONUS": 0.15,  
    "FUNC_HOUSE_LORD_ENEMY_PLC_PENALTY": 0.00,
    "FUNC_HOUSE_LORD_TRIK_BHAVA_PENALTY": -0.25, 
    
    # Scaling & Core Engine Base Weights
    "SHADBALA_SCALING_WEIGHT": 1.0,    
    "HOUSE_LORD_WEIGHT": 0.5,          
    "HOUSE_MALEFIC_PRESSURE_WEIGHT": 0.8, 
    "HOUSE_SAV_DIVISOR": 28.0          
}

CSI_WEIGHTS = DEFAULT_CSI_WEIGHTS.copy()
PREFS_FILE = "csi_weights_prefs.json"

def load_csi_weights():
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, 'r') as f:
                saved = json.load(f)
                CSI_WEIGHTS.update(saved)
        except Exception as e:
            error_print(f"Error loading CSI weights: {e}")

def save_csi_weights():
    try:
        with open(PREFS_FILE, 'w') as f:
            json.dump(CSI_WEIGHTS, f, indent=4)
    except Exception as e:
        error_print(f"Error saving CSI weights: {e}")

load_csi_weights()

WEIGHT_NAMES_MAPPING = {
    "SHADBALA_NORM_WEIGHT": "Shadbala Base Weight",
    "ASHTAKAVARGA_SAV_WEIGHT": "Ashtakavarga (SAV) Base Weight",
    "AVASTHA_DIGNITY_WEIGHT": "Avastha Dignity Base Weight",
    "HOUSE_LORD_WEIGHT": "House Lord Influence Weight",
    "HOUSE_MALEFIC_PRESSURE_WEIGHT": "Malefic Pressure Multiplier",
    "HOUSE_SAV_DIVISOR": "SAV Neutral Divisor (Avg 28)",
    "SHADBALA_SCALING_WEIGHT": "Shadbala Scaling Multiplier",
    "COMBUSTION_PENALTY": "Combustion Penalty",
    "RETROGRADE_MODIFIER": "Retrograde Modifier",
    "ECLIPSE_NODE_PENALTY": "Eclipse (Nodal Conjunction) Penalty",
    "SPECIAL_RULE_EXCHANGE_BONUS": "Parivartana (Exchange) Bonus",
    "SPECIAL_RULE_INDIRECT_EXCHANGE_BONUS": "Parivartana (Indirect) Bonus",
    "SPECIAL_RULE_VIPARITA_BONUS": "Viparita Raja Yoga Bonus",
    "SPECIAL_RULE_INDIRECT_VIPARITA_BONUS": "Viparita Yoga (Indirect) Bonus",
    "SPECIAL_RULE_VIPARITA_CANCELLED_BONUS": "Viparita Cancelled Penalty",
    "SPECIAL_RULE_LAGNA_TRIK_BHAVA_PENALTY": "Lagna Lord in Trik Penalty",
    "SPECIAL_RULE_EXALTED_OCCUPANT_BONUS": "Exalted Occupant Bonus",
    "SPECIAL_RULE_EXALTED_LORD_BONUS": "Exalted Lord (Indirect) Bonus",
    "SPECIAL_RULE_DEB_OCCUPANT_PENALTY": "Debilitated Occupant Penalty",
    "SPECIAL_RULE_DEB_LORD_PENALTY": "Debilitated Lord (Indirect) Penalty",
    "FUNC_LORD_FRIEND_MODIFIER": "Occupying Friend/Own House",
    "FUNC_LORD_ENEMY_PENALTY": "Occupying Enemy House",
    "FUNC_HOUSE_LORD_BENEFIC_BONUS": "House Lord is Func. Benefic",
    "FUNC_HOUSE_LORD_MALEFIC_PENALTY": "House Lord is Func. Malefic",
    "FUNC_HOUSE_LORD_FRIEND_PLC_BONUS": "House Lord in Friend/Own Sign",
    "FUNC_HOUSE_LORD_ENEMY_PLC_PENALTY": "House Lord in Enemy Sign",
    "FUNC_HOUSE_LORD_TRIK_BHAVA_PENALTY": "House Lord in Trik Bhava Penalty"
}

REQUIRED_SHADBALA = {
    "Sun": 390.0, "Moon": 360.0, "Mars": 300.0, 
    "Mercury": 420.0, "Jupiter": 390.0, "Venus": 330.0, "Saturn": 300.0
}

DEVA_GRAHAS = ["Sun", "Moon", "Mars", "Jupiter"]
DANAVA_GRAHAS = ["Saturn", "Rahu", "Ketu", "Venus"]

# ==============================================================================
# CUSTOM UI COMPONENTS FOR TOOLTIPS & TABLES

class CustomTooltipTable(QTableWidget):
    """A custom table that bypasses OS delays to show HTML tooltips instantly following the cursor."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.tooltip_label = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""
            QLabel { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; font-size: 13px; font-family: 'Segoe UI', Tahoma, sans-serif;}
        """)
        self.tooltip_label.hide()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        item = self.itemAt(pos)

        tt_text = ""
        if item and item.data(Qt.ItemDataRole.UserRole):
            tt_text = item.data(Qt.ItemDataRole.UserRole)

        if tt_text:
            if self.tooltip_label.text() != tt_text:
                self.tooltip_label.setText(tt_text)
                self.tooltip_label.adjustSize()

            global_pos = event.globalPosition().toPoint()
            new_x, new_y = global_pos.x() + 15, global_pos.y() + 15
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): new_x = global_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): new_y = global_pos.y() - self.tooltip_label.height() - 5
                if new_x < sg.left(): new_x = sg.left() + 5
                if new_y < sg.top(): new_y = sg.top() + 5

            self.tooltip_label.move(new_x, new_y)
            if not self.tooltip_label.isVisible(): self.tooltip_label.show()
            self.tooltip_label.raise_()
        else:
            self.tooltip_label.hide()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tooltip_label.hide()
        super().leaveEvent(event)

# ==============================================================================
# VISUALIZER COMPONENT: COMPOSITE DIAMOND CHART
# ==============================================================================
class CompositeChartWidget(QWidget):
    def __init__(self, csi_data, chart_data, parent=None):
        super().__init__(parent)
        self.csi_data = csi_data
        self.chart_data = chart_data
        
        self.setMinimumSize(MIN_CHART_SIZE, MIN_CHART_SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.house_polys = {}
        
        self.tooltip_label = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""
            QLabel { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px; padding: 12px; font-size: 13px; font-family: 'Segoe UI', Tahoma, sans-serif; }
        """)
        self.tooltip_label.hide()
        
    def _get_house_polygon(self, h_num, x, y, w, h):
        p_tl, p_tr = QPointF(x, y), QPointF(x + w, y)
        p_bl, p_br = QPointF(x, y + h), QPointF(x + w, y + h)
        p_tc, p_bc = QPointF(x + w / 2, y), QPointF(x + w / 2, y + h)
        p_lc, p_rc = QPointF(x, y + h / 2), QPointF(x + w, y + h / 2)
        p_cc = QPointF(x + w / 2, y + h / 2)

        p_i_tl = QPointF(x + w / 4, y + h / 4)
        p_i_tr = QPointF(x + 3 * w / 4, y + h / 4)
        p_i_bl = QPointF(x + w / 4, y + 3 * h / 4)
        p_i_br = QPointF(x + 3 * w / 4, y + 3 * h / 4)

        polygons = {
            1: [p_tc, p_i_tr, p_cc, p_i_tl],
            2: [p_tl, p_tc, p_i_tl],
            3: [p_tl, p_i_tl, p_lc],
            4: [p_lc, p_i_tl, p_cc, p_i_bl],
            5: [p_lc, p_i_bl, p_bl],
            6: [p_i_bl, p_bc, p_bl],
            7: [p_cc, p_i_br, p_bc, p_i_bl],
            8: [p_bc, p_i_br, p_br],
            9: [p_i_br, p_rc, p_br],
            10: [p_i_tr, p_rc, p_i_br, p_cc],
            11: [p_tr, p_rc, p_i_tr],
            12: [p_tc, p_tr, p_i_tr]
        }
        return QPolygonF(polygons[h_num])

    def _get_house_center(self, h_num, x, y, w, h):
        poly = self._get_house_polygon(h_num, x, y, w, h)
        cx = sum([pt.x() for pt in poly]) / poly.count()
        cy = sum([pt.y() for pt in poly]) / poly.count()
        return QPointF(cx, cy)
        
    def _get_inner_corner(self, h_num, x, y, w, h):
        p_cc = QPointF(x + w / 2, y + h / 2)
        p_i_tl = QPointF(x + w / 4, y + h / 4)
        p_i_tr = QPointF(x + 3 * w / 4, y + h / 4)
        p_i_bl = QPointF(x + w / 4, y + 3 * h / 4)
        p_i_br = QPointF(x + 3 * w / 4, y + 3 * h / 4)
        
        corners = {
            1: p_cc, 2: p_i_tl, 3: p_i_tl, 4: p_cc, 
            5: p_i_bl, 6: p_i_bl, 7: p_cc, 8: p_i_br, 
            9: p_i_br, 10: p_cc, 11: p_i_tr, 12: p_i_tr
        }
        return corners[h_num]

    def mouseMoveEvent(self, event):
        pos = event.pos()
        pos_f = QPointF(float(pos.x()), float(pos.y()))
        tt_text = ""
        
        for h_num, poly in self.house_polys.items():
            if poly.containsPoint(pos_f, Qt.FillRule.OddEvenFill):
                h_data = self.csi_data["houses"].get(h_num, {})
                
                lord = h_data.get("lord", "Unknown")
                lord_csi = h_data.get("lord_csi", 0.0)
                base_net_energy = h_data.get("base_net_energy", 0.0)
                net_energy = h_data.get("net_energy", 0.0)
                sav_points = h_data.get("sav", 0)
                vector = h_data.get("vector_status", "Neutral")
                func_mod_html = h_data.get("func_mod_html", "")
                
                benefic_support = h_data.get("benefic_support", 0.0)
                malefic_pressure = h_data.get("malefic_pressure", 0.0)
                
                w_sav_div = CSI_WEIGHTS["HOUSE_SAV_DIVISOR"]
                w_lord = CSI_WEIGHTS["HOUSE_LORD_WEIGHT"]
                w_mal = CSI_WEIGHTS["HOUSE_MALEFIC_PRESSURE_WEIGHT"]
                
                sav_comp = sav_points / w_sav_div
                lord_comp = lord_csi * w_lord
                mal_comp = malefic_pressure * w_mal
                
                occ_details_list = h_data.get("occupant_details", [])
                occ_html_lines = []
                for od in occ_details_list:
                    n_col = "#059669" if od["nature"] == "Benefic" else "#DC2626"
                    occ_html_lines.append(f"• <b>{od['name']}</b> ({od['csi']:.2f}): <span style='color:{n_col}; font-weight:bold;'>{od['nature']}</span> <span style='font-size:11px; color:#64748B;'>({od['reason']})</span>")
                
                occ_breakdown = f"<div style='margin-bottom:4px;'><b>Occupants:</b><br>{'<br>'.join(occ_html_lines)}</div>" if occ_html_lines else ""
                func_mods = f"<b><br>Functional Modifiers:</b><br>{func_mod_html}" if func_mod_html else ""
                
                color_hex = "#0284C7"
                if "Constructive" in vector: color_hex = "#059669"
                elif "Destructive" in vector: color_hex = "#DC2626"
                elif "Challenging" in vector: color_hex = "#D97706"
                
                tt_text = (
                    f"<div style='min-width: 320px;'>"
                    f"<h3 style='margin:0; color:{color_hex};'>House {h_num} Profile</h3><hr style='border-top: 1px solid #CBD5E1; margin: 4px 0;'>"
                    f"<b>Net Composite:</b> <span style='font-size:14px;'>{net_energy:.2f}</span> | "
                    f"<b>Nature:</b> <span style='color:{color_hex}; font-weight:bold;'>{vector}</span>"
                    f"{occ_breakdown}"
                    f"<hr style='border-top: 1px dashed #CBD5E1; margin: 4px 0;'>"
                    f"<b>Breakdown:</b><br>"
                    f"• SAV: {sav_points}/{w_sav_div} = <span style='color:#0284C7;'>{sav_comp:.2f}</span><br>"
                    f"• Lord ({lord[:2]}): {lord_csi:.2f}*{w_lord} = <span style='color:#0284C7;'>{lord_comp:.2f}</span><br>"
                    f"• Benefic/Malefic: <span style='color:#059669;'>+{benefic_support:.2f}</span> / <span style='color:#DC2626;'>-{mal_comp:.2f}</span><br>"
                    f"<b>Base Points:</b> {sav_comp:.2f} + {lord_comp:.2f} + {benefic_support:.2f} - {mal_comp:.2f} = <b>{base_net_energy:.2f}</b>"
                    f"{func_mods}"
                    f"<hr style='border-top: 1px dashed #CBD5E1; margin: 4px 0;'>"
                    f"<b>Final House CSI:</b> <span style='font-size:14px; font-weight:bold;'>{net_energy:.2f}</span>"
                    f"</div>"
                )
                break

        if tt_text:
            if self.tooltip_label.text() != tt_text:
                self.tooltip_label.setText(tt_text)
                self.tooltip_label.adjustSize()
            global_pos = event.globalPosition().toPoint()
            new_x, new_y = global_pos.x() + 15, global_pos.y() + 15
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): new_x = global_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): new_y = global_pos.y() - self.tooltip_label.height() - 5
                if new_x < sg.left(): new_x = sg.left() + 5
                if new_y < sg.top(): new_y = sg.top() + 5

            self.tooltip_label.move(new_x, new_y)
            self.tooltip_label.show()
            self.tooltip_label.raise_()
        else:
            self.tooltip_label.hide()
            
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tooltip_label.hide()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#F8FAFC"))

        size = min(rect.width(), rect.height()) - 60
        cx, cy = rect.width() / 2, rect.height() / 2
        x, y, w, h = cx - size / 2, cy - size / 2 + 10, size, size

        self.house_polys.clear()
        
        asc_sign_idx = self.chart_data["ascendant"]["sign_index"]
        bodies_by_house = {i: [] for i in range(1, 13)}
        
        bodies_by_house[1].append({"name": "Asc", "color": QColor("#000000"), "abbr": "Asc"})
        
        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"]: 
                h_num = ((p["sign_index"] - asc_sign_idx) % 12) + 1
                bodies_by_house[h_num].append({"name": p["name"], "color": QColor("#64748B"), "abbr": p["name"][:2]})
                continue
                
            h_num = ((p["sign_index"] - asc_sign_idx) % 12) + 1
            p_csi_data = self.csi_data["planets"].get(p["name"], {})
            vector = p_csi_data.get("vector", "Neutral")
            
            p_color = QColor("#000000")
            if "Constructive" in vector: p_color = QColor("#059669")
            elif "Destructive" in vector: p_color = QColor("#DC2626")
            
            bodies_by_house[h_num].append({"name": p["name"], "color": p_color, "abbr": p["name"][:2]})
        
        for h_num in range(1, 13):
            poly = self._get_house_polygon(h_num, x, y, w, h)
            self.house_polys[h_num] = poly
            
            h_data = self.csi_data["houses"].get(h_num, {})
            vector = h_data.get("vector_status", "Neutral")
            
            if "Highly Constructive" in vector: fill_c, border_c = QColor("#D1FAE5"), QColor("#059669")
            elif "Constructive" in vector: fill_c, border_c = QColor("#ECFDF5"), QColor("#10B981")
            elif "Highly Destructive" in vector: fill_c, border_c = QColor("#FEE2E2"), QColor("#DC2626")
            elif "Destructive" in vector: fill_c, border_c = QColor("#FEF2F2"), QColor("#EF4444")
            elif "Challenging" in vector: fill_c, border_c = QColor("#FEF3C7"), QColor("#D97706")
            else: fill_c, border_c = QColor("#F1F5F9"), QColor("#94A3B8")
            
            painter.setBrush(QBrush(fill_c))
            painter.setPen(QPen(border_c, max(2.0, w * 0.005), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.drawPolygon(poly)
            
            center = self._get_house_center(h_num, x, y, w, h)
            
            if len(bodies_by_house[h_num]) > 0:
                inner = self._get_inner_corner(h_num, x, y, w, h)
                text_x = center.x() + (inner.x() - center.x()) * 0.65
                text_y = center.y() + (inner.y() - center.y()) * 0.65
                text_pos = QPointF(text_x, text_y)
            else:
                text_pos = center
                
            painter.setPen(QColor(border_c.red(), border_c.green(), border_c.blue(), 150))
            painter.setFont(QFont("Segoe UI", int(w * 0.035), QFont.Weight.Bold))
            painter.drawText(QRectF(text_pos.x() - 15, text_pos.y() - 18, 30, 20), Qt.AlignmentFlag.AlignCenter, str(h_num))
            
            # Show rashi numbers in smaller font
            sign_num = ((asc_sign_idx + h_num - 1) % 12) + 1
            painter.setFont(QFont("Segoe UI", int(w * 0.02)))
            painter.drawText(QRectF(text_pos.x() - 15, text_pos.y() + 2, 30, 15), Qt.AlignmentFlag.AlignCenter, f"({sign_num})")

        for h_num, bodies in bodies_by_house.items():
            if not bodies: continue
            
            center = self._get_house_center(h_num, x, y, w, h)
            num_b = len(bodies)
            spacing = h * 0.04
            start_y = center.y() - ((num_b - 1) * spacing) / 2.0
            
            for idx, b in enumerate(bodies):
                py = start_y + (idx * spacing)
                painter.setPen(b["color"])
                painter.setFont(QFont("Segoe UI", int(w * 0.025), QFont.Weight.Bold))
                painter.drawText(QRectF(center.x() - 30, py - 10, 60, 20), Qt.AlignmentFlag.AlignCenter, b["abbr"])

# ==============================================================================
# ENGINE: CSI CALCULATOR
# ==============================================================================
class CSICalculator:
    def __init__(self, app, use_functional=True, scale_by_shadbala=True):
        self.app = app
        self.use_functional = use_functional
        self.scale_by_shadbala = scale_by_shadbala
        self.chart = getattr(app, 'current_base_chart', {})
        self.shadbala = getattr(app, '_shadbala_results', {})
        self.valid_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        self.natural_benefics = ["Jupiter", "Venus", "Moon", "Mercury"] 
        self.natural_malefics = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]

    def is_enemy(self, p1, p2):
        if p1 == p2: return False
        if "Mercury" in (p1, p2):
            other = p2 if p1 == "Mercury" else p1
            if other in ["Moon", "Mars"]: return True
            return False 
        if p1 in DEVA_GRAHAS and p2 in DEVA_GRAHAS: return False
        if p1 in DANAVA_GRAHAS and p2 in DANAVA_GRAHAS: return False
        return True 

    def get_planet_nature(self, p_name):
        if not self.use_functional:
            if p_name in self.natural_benefics:
                return "Benefic", "Natural Benefic"
            else:
                return "Malefic", "Natural Malefic"
            
        asc_sign_idx = self.chart["ascendant"]["sign_index"]
        asc_sign = asc_sign_idx + 1
        lagna_lord = astro_engine.SIGN_RULERS.get(asc_sign)
        
        occupied_house = 1
        for p in self.chart.get("planets", []):
            if p["name"] == p_name:
                occupied_house = ((p["sign_index"] - asc_sign_idx) % 12) + 1
                break
                
        is_upachaya_occupied = occupied_house in [6, 8, 12]

        if p_name in ["Rahu", "Ketu"]:
            if is_upachaya_occupied:
                return "Malefic", f"Node occupying Trik Bhava (H{occupied_house})"
            return "Malefic", "Nodes are natural Malefics"

        ruled_houses = []
        for sign, lord in astro_engine.SIGN_RULERS.items():
            if lord == p_name:
                h_num = ((sign - asc_sign) % 12) + 1
                ruled_houses.append(h_num)
                
        if 5 in ruled_houses or 9 in ruled_houses:
            trikon_house = 5 if 5 in ruled_houses else 9
            return "Benefic", f"Rules Trikon (H{trikon_house})"
            
        if 1 in ruled_houses:
            if is_upachaya_occupied:
                return "Malefic", f"Lagna Lord occupying Trik Bhava (H{occupied_house})"
            return "Benefic", "Lagna Lord is always Benefic"
            
        if is_upachaya_occupied:
            return "Malefic", f"Occupies Trik Bhava (H{occupied_house})"
            
        upachaya_ruled = [h for h in ruled_houses if h in [6, 8, 12]]
        if upachaya_ruled:
            return "Malefic", f"Rules Trik Bhava (H{upachaya_ruled[0]})"
            
        if self.is_enemy(p_name, lagna_lord):
            return "Malefic", f"Enemy of Lagna Lord ({lagna_lord})"
            
        return "Benefic", f"Friend of Lagna Lord ({lagna_lord})"

    def calculate_avastha_score(self, planet_data):
        if planet_data.get("exalted"): return 1.0
        if planet_data.get("own_sign"): return 0.8
        if planet_data.get("debilitated"): return 0.1
        
        p_name = planet_data["name"]
        if p_name in self.shadbala:
            sthana = self.shadbala[p_name]["Sthana_Details"]["Total"]
            if sthana >= 150: return 0.7
            elif sthana <= 75: return 0.3
        
        return 0.5

    def is_combust(self, p_lon, sun_lon, p_name):
        if p_name in ["Sun", "Rahu", "Ketu"]: return False
        dist = min((p_lon - sun_lon) % 360, (sun_lon - p_lon) % 360)
        limits = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11, "Venus": 10, "Saturn": 15}
        return dist <= limits.get(p_name, 15)

    def calculate_csi(self):
        if not self.chart or not self.shadbala: return None
        
        planets_data = self.chart.get("planets", [])
        sun_p = next((p for p in planets_data if p["name"] == "Sun"), None)
        sun_lon = sun_p["lon"] if sun_p else 0
        
        csi_results = {"planets": {}, "houses": {}}
        asc_sign_idx = self.chart["ascendant"]["sign_index"]
        
        lagna_lord_name = astro_engine.SIGN_RULERS.get(asc_sign_idx + 1)
        lagna_lord_p = next((pl for pl in planets_data if pl["name"] == lagna_lord_name), None)
        lagna_lord_h_num = ((lagna_lord_p["sign_index"] - asc_sign_idx) % 12) + 1 if lagna_lord_p else 1
        is_lagna_lord_in_dusthana = lagna_lord_h_num in [6, 8, 12]
        
        # 1. PLANETARY CSI CALCULATION
        for p in planets_data:
            p_name = p["name"]
            if p_name not in self.valid_planets: continue
            
            sb_data = self.shadbala.get(p_name)
            if not sb_data: continue
            
            norm_shadbala = min(2.0, sb_data["Total"] / REQUIRED_SHADBALA.get(p_name, 300))
            
            sign_idx = p["sign_index"]
            h_num = ((sign_idx - asc_sign_idx) % 12) + 1
            sav_points = sb_data["Ashtakavarga"]["SAV_Points"][sign_idx]
            norm_sav = min(1.5, sav_points / 28.0)
            avastha_score = self.calculate_avastha_score(p)
            
            base_csi = (
                (norm_shadbala * CSI_WEIGHTS["SHADBALA_NORM_WEIGHT"]) +
                (norm_sav * CSI_WEIGHTS["ASHTAKAVARGA_SAV_WEIGHT"]) +
                (avastha_score * CSI_WEIGHTS["AVASTHA_DIGNITY_WEIGHT"])
            )
            
            is_retro = p.get("retro", False)
            combust = self.is_combust(p["lon"], sun_lon, p_name)
            
            node_conjunct = False
            for op in planets_data:
                if op["name"] in ["Rahu", "Ketu"] and op["sign_index"] == sign_idx:
                    dist = min(abs(p["lon"] - op["lon"]), 360 - abs(p["lon"] - op["lon"]))
                    if dist <= 10.0: node_conjunct = True; break
            
            sb_mod = norm_shadbala * CSI_WEIGHTS["SHADBALA_SCALING_WEIGHT"] if self.scale_by_shadbala else 1.0
            sb_tag = f" <span style='font-size:10px;color:#64748B;'>[sb:{norm_shadbala:.1f}x]</span>" if self.scale_by_shadbala else ""

            modifier = 1.0
            base_mod_html = ""
            
            if combust: 
                v = CSI_WEIGHTS["COMBUSTION_PENALTY"] * sb_mod
                modifier += v
                if abs(v) > 0.001: base_mod_html += f"• Combustion Penalty: <span style='color:#DC2626;'>{v:.2f}</span>{sb_tag}<br>"
            if is_retro: 
                v = CSI_WEIGHTS["RETROGRADE_MODIFIER"] * sb_mod
                modifier += v
                if abs(v) > 0.001: base_mod_html += f"• Retrograde Modifier: <span style='color:#059669;'>+{v:.2f}</span>{sb_tag}<br>"
            if node_conjunct: 
                v = CSI_WEIGHTS["ECLIPSE_NODE_PENALTY"] * sb_mod
                modifier += v
                if abs(v) > 0.001: base_mod_html += f"• Nodal Eclipse Penalty: <span style='color:#DC2626;'>{v:.2f}</span>{sb_tag}<br>"
            
            lord_relation = None
            special_rule_html = ""
            mod_html_ext = ""
            
            if self.use_functional:
                sign_lord = astro_engine.SIGN_RULERS.get(sign_idx + 1)
                
                ruled_h = [((s - asc_sign_idx - 1) % 12) + 1 for s, l in astro_engine.SIGN_RULERS.items() if l == p_name]
                is_lagna_lord = 1 in ruled_h
                occupies_dusthana = h_num in [6, 8, 12]
                rules_dusthana = any(h in [6, 8, 12] for h in ruled_h)
                
                is_viparita = occupies_dusthana and rules_dusthana and not is_lagna_lord
                is_viparita_cancelled = False
                
                if is_viparita and is_lagna_lord_in_dusthana:
                    is_viparita = False
                    is_viparita_cancelled = True
                
                is_exchange = False
                if sign_lord != p_name and sign_lord in [pl["name"] for pl in planets_data]:
                    disp_p = next(pl for pl in planets_data if pl["name"] == sign_lord)
                    if astro_engine.SIGN_RULERS.get(disp_p["sign_index"] + 1) == p_name:
                        is_exchange = True

                if is_exchange:
                    lord_relation = "Rashi Exchange"
                    v = CSI_WEIGHTS["SPECIAL_RULE_EXCHANGE_BONUS"] * sb_mod
                    modifier += v
                    if abs(v) > 0.001: special_rule_html = f"<div style='background-color:#ECFDF5; padding:6px; border:1px solid #059669; border-radius:4px; margin-bottom:6px; color:#059669;'><b>✨ Rule Triggered: Parivartana Yoga (Exchange)</b><br>Awarded high bonus (+{v:.2f}){sb_tag}</div>"
                elif is_lagna_lord and occupies_dusthana:
                    lord_relation = "Lagna Lord in Trik Bhava"
                    v = CSI_WEIGHTS["SPECIAL_RULE_LAGNA_TRIK_BHAVA_PENALTY"] * sb_mod
                    modifier += v
                    if abs(v) > 0.001: special_rule_html = f"<div style='background-color:#FEF2F2; padding:6px; border:1px solid #DC2626; border-radius:4px; margin-bottom:6px; color:#DC2626;'><b>⚠️ Rule Triggered: Lagna Lord in Trik Bhava (H{h_num})</b><br>Deducted points ({v:.2f}){sb_tag}</div>"
                elif is_viparita:
                    lord_relation = "Viparita Raja Yoga"
                    v = CSI_WEIGHTS["SPECIAL_RULE_VIPARITA_BONUS"] * sb_mod
                    modifier += v
                    if abs(v) > 0.001: special_rule_html = f"<div style='background-color:#FEF3C7; padding:6px; border:1px solid #D97706; border-radius:4px; margin-bottom:6px; color:#D97706;'><b>✨ Rule Triggered: Viparita Raja Yoga (6/8/12 Lord in 6/8/12)</b><br>Awarded high bonus (+{v:.2f}){sb_tag}</div>"
                elif is_viparita_cancelled:
                    lord_relation = "Viparita Raja Yoga (Cancelled)"
                    v = CSI_WEIGHTS["SPECIAL_RULE_VIPARITA_CANCELLED_BONUS"] * sb_mod
                    modifier += v
                    if abs(v) > 0.001: special_rule_html = f"<div style='background-color:#F1F5F9; padding:6px; border:1px solid #CBD5E1; border-radius:4px; margin-bottom:6px; color:#475569;'><b>ℹ️ Rule Triggered: Viparita Yoga (Cancelled)</b><br>Lagna Lord is in Trik Bhava. Awarded points (+{v:.2f}){sb_tag}</div>"
                elif p_name == sign_lord:
                    lord_relation = "Own Sign"
                    v = CSI_WEIGHTS["FUNC_LORD_FRIEND_MODIFIER"] * sb_mod
                    modifier += v
                    if abs(v) > 0.001: mod_html_ext += f"• Own Sign Bonus: <span style='color:#059669;'>+{v:.2f}</span>{sb_tag}<br>"
                elif self.is_enemy(p_name, sign_lord):
                    lord_relation = "Enemy House"
                    v = CSI_WEIGHTS["FUNC_LORD_ENEMY_PENALTY"] * sb_mod
                    modifier += v
                    if abs(v) > 0.001: mod_html_ext += f"• Enemy House ({sign_lord[:2]}) Penalty: <span style='color:#DC2626;'>{v:.2f}</span>{sb_tag}<br>"
                else:
                    lord_relation = "Friend House"
                    v = CSI_WEIGHTS["FUNC_LORD_FRIEND_MODIFIER"] * sb_mod
                    modifier += v
                    if abs(v) > 0.001: mod_html_ext += f"• Friend House ({sign_lord[:2]}) Bonus: <span style='color:#059669;'>+{v:.2f}</span>{sb_tag}<br>"
            
            final_csi = base_csi * max(0.1, modifier)
            
            nature, reason = self.get_planet_nature(p_name)
            vector = "Neutral"
            is_benefic = (nature == "Benefic")
            
            if final_csi > 1.2:
                if is_benefic and not combust: vector = "Highly Constructive"
                elif not is_benefic and avastha_score > 0.6: vector = "Constructive (Protective)"
                elif not is_benefic and avastha_score <= 0.6: vector = "Highly Destructive"
            elif final_csi > 0.8:
                if is_benefic: vector = "Constructive"
                else: vector = "Challenging"
            else:
                if is_benefic: vector = "Passive/Weak"
                else: vector = "Destructive"
                
            if is_retro and "Constructive" in vector: vector += " (Retro)"

            csi_results["planets"][p_name] = {
                "csi": final_csi,
                "vector": vector,
                "norm_sb": norm_shadbala,
                "sav_points": sav_points,
                "norm_sav": norm_sav,
                "avastha": avastha_score,
                "combust": combust,
                "retro": is_retro,
                "node_conj": node_conjunct,
                "nature_applied": nature,
                "nature_reason": reason,
                "used_functional": self.use_functional,
                "lord_relation": lord_relation,
                "base_mod_html": base_mod_html,
                "mod_html_ext": mod_html_ext,
                "special_rule_html": special_rule_html,
                "total_modifier": modifier,
                "is_exalted": p.get("exalted", False),
                "is_debilitated": p.get("debilitated", False)
            }

        # 2. HOUSE CSI CALCULATION
        sav_array = list(self.shadbala.values())[0]["Ashtakavarga"]["SAV_Points"] if self.shadbala else [28]*12
        
        for h_num in range(1, 13):
            sign_idx = (asc_sign_idx + h_num - 1) % 12
            lord_name = astro_engine.SIGN_RULERS.get(sign_idx + 1)
            
            occupants = [p["name"] for p in planets_data if p["sign_index"] == sign_idx and p["name"] not in ["Rahu", "Ketu"]]
            lord_csi = csi_results["planets"].get(lord_name, {}).get("csi", 0.5)
            sav = sav_array[sign_idx]
            
            occ_energy, malefic_pressure, benefic_support = 0, 0, 0
            occ_details = []
            
            for o in occupants:
                o_csi = csi_results["planets"][o]["csi"]
                o_vec = csi_results["planets"][o]["vector"]
                o_nature = csi_results["planets"][o]["nature_applied"]
                o_reason = csi_results["planets"][o]["nature_reason"]
                occ_energy += o_csi
                
                if "Destructive" in o_vec or "Challenging" in o_vec: malefic_pressure += o_csi
                if "Constructive" in o_vec: benefic_support += o_csi
                occ_details.append({"name": o, "csi": o_csi, "nature": o_nature, "reason": o_reason})

            nodes = [p["name"] for p in planets_data if p["sign_index"] == sign_idx and p["name"] in ["Rahu", "Ketu"]]
            if nodes: 
                for node in nodes:
                    n_nature, n_reason = self.get_planet_nature(node)
                    val = 0.5 
                    if n_nature == "Malefic": malefic_pressure += val
                    else: benefic_support += val
                    occ_details.append({"name": node, "csi": val, "nature": n_nature, "reason": n_reason})
            
            w_sav_div = CSI_WEIGHTS["HOUSE_SAV_DIVISOR"]
            w_lord = CSI_WEIGHTS["HOUSE_LORD_WEIGHT"]
            w_mal = CSI_WEIGHTS["HOUSE_MALEFIC_PRESSURE_WEIGHT"]
            
            base_net_energy = (sav / w_sav_div) + (lord_csi * w_lord) + (benefic_support) - (malefic_pressure * w_mal)
            net_energy = base_net_energy
            
            func_mod_html = ""
            if self.use_functional:
                got_direct_exchange = False
                got_direct_viparita = False
                got_direct_cancelled = False
                occupant_mod_html = ""
                
                # Check for direct yoga bonuses from occupants first
                for occ in occupants + nodes:
                    if occ in csi_results["planets"]:
                        occ_data = csi_results["planets"][occ]
                        occ_relation = occ_data.get("lord_relation")
                        
                        occ_sb = occ_data.get("norm_sb", 1.0)
                        occ_sb_mod = occ_sb * CSI_WEIGHTS["SHADBALA_SCALING_WEIGHT"] if self.scale_by_shadbala else 1.0
                        sb_tag = f" <span style='font-size:10px;color:#64748B;'>[sb:{occ_sb:.1f}x]</span>" if self.scale_by_shadbala else ""

                        if occ_relation == "Rashi Exchange":
                            v = CSI_WEIGHTS["SPECIAL_RULE_EXCHANGE_BONUS"] * occ_sb_mod
                            net_energy += v
                            if abs(v) > 0.001: occupant_mod_html += f"<div style='color:#059669; margin-top:2px;'><b>✨ Occupant ({occ}) in Parivartana</b>: +{v:.2f}{sb_tag}</div>"
                            got_direct_exchange = True
                        elif occ_relation == "Viparita Raja Yoga":
                            v = CSI_WEIGHTS["SPECIAL_RULE_VIPARITA_BONUS"] * occ_sb_mod
                            net_energy += v
                            if abs(v) > 0.001: occupant_mod_html += f"<div style='color:#D97706; margin-top:2px;'><b>✨ Occupant ({occ}) forms Viparita</b>: +{v:.2f}{sb_tag}</div>"
                            got_direct_viparita = True
                        elif occ_relation == "Viparita Raja Yoga (Cancelled)":
                            v = CSI_WEIGHTS["SPECIAL_RULE_VIPARITA_CANCELLED_BONUS"] * occ_sb_mod
                            net_energy += v
                            if abs(v) > 0.001: occupant_mod_html += f"<div style='color:#64748B; margin-top:2px;'><b>ℹ️ Occupant ({occ}) Viparita Cancelled</b>: +{v:.2f}{sb_tag}</div>"
                            got_direct_cancelled = True

                        if occ_data.get("is_exalted"):
                            v = CSI_WEIGHTS["SPECIAL_RULE_EXALTED_OCCUPANT_BONUS"] * occ_sb_mod
                            net_energy += v
                            if abs(v) > 0.001: occupant_mod_html += f"<div style='color:#059669; margin-top:2px;'><b>✨ Occupant ({occ}) is Exalted</b>: +{v:.2f}{sb_tag}</div>"
                        elif occ_data.get("is_debilitated"):
                            v = CSI_WEIGHTS["SPECIAL_RULE_DEB_OCCUPANT_PENALTY"] * occ_sb_mod
                            net_energy += v
                            if abs(v) > 0.001: occupant_mod_html += f"<div style='color:#64748B; margin-top:2px;'><b>ℹ️ Occupant ({occ}) is Debilitated</b>: {v:.2f}{sb_tag}</div>"

                lord_mod_html = ""
                # Check modifiers from the House Lord's placement
                if lord_name in csi_results["planets"]:
                    l_data = csi_results["planets"][lord_name]
                    l_nature = l_data["nature_applied"]
                    l_relation = l_data["lord_relation"]
                    
                    l_sb = l_data.get("norm_sb", 1.0)
                    l_sb_mod = l_sb * CSI_WEIGHTS["SHADBALA_SCALING_WEIGHT"] if self.scale_by_shadbala else 1.0
                    sb_tag = f" <span style='font-size:10px;color:#64748B;'>[sb:{l_sb:.1f}x]</span>" if self.scale_by_shadbala else ""
                    
                    lord_h_num = 1
                    for p in planets_data:
                        if p["name"] == lord_name:
                            lord_h_num = ((p["sign_index"] - asc_sign_idx) % 12) + 1
                            break
                            
                    if l_nature == "Benefic":
                        v = CSI_WEIGHTS["FUNC_HOUSE_LORD_BENEFIC_BONUS"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"• Lord ({lord_name}) is Func. Benefic: <span style='color:#059669;'>+{v:.2f}</span>{sb_tag}<br>"
                    else:
                        v = CSI_WEIGHTS["FUNC_HOUSE_LORD_MALEFIC_PENALTY"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"• Lord ({lord_name}) is Func. Malefic: <span style='color:#DC2626;'>{v:.2f}</span>{sb_tag}<br>"
                        
                    if l_relation in ["Own Sign", "Friend House"]:
                        v = CSI_WEIGHTS["FUNC_HOUSE_LORD_FRIEND_PLC_BONUS"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"• Lord sits in {l_relation}: <span style='color:#059669;'>+{v:.2f}</span>{sb_tag}<br>"
                    elif l_relation == "Enemy House":
                        v = CSI_WEIGHTS["FUNC_HOUSE_LORD_ENEMY_PLC_PENALTY"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"• Lord sits in Enemy House: <span style='color:#DC2626;'>{v:.2f}</span>{sb_tag}<br>"
                        
                    if lord_h_num in [6, 8, 12] and l_relation not in ["Viparita Raja Yoga", "Viparita Raja Yoga (Cancelled)", "Lagna Lord in Trik Bhava", "Rashi Exchange"]:
                        v = CSI_WEIGHTS["FUNC_HOUSE_LORD_TRIK_BHAVA_PENALTY"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"• Lord in Trik Bhava (H{lord_h_num}): <span style='color:#DC2626;'>{v:.2f}</span>{sb_tag}<br>"

                    # Indirect Rule Assignments (Only apply if NOT already directly triggered by occupants)
                    if l_relation == "Rashi Exchange" and not got_direct_exchange:
                        v = CSI_WEIGHTS["SPECIAL_RULE_INDIRECT_EXCHANGE_BONUS"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"<div style='color:#059669; margin-top:2px;'><b>✨ Lord in Parivartana (Indirect)</b>: +{v:.2f}{sb_tag}</div>"
                    elif l_relation == "Viparita Raja Yoga" and not got_direct_viparita:
                        v = CSI_WEIGHTS["SPECIAL_RULE_INDIRECT_VIPARITA_BONUS"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"<div style='color:#D97706; margin-top:2px;'><b>✨ Lord forms Viparita (Indirect)</b>: +{v:.2f}{sb_tag}</div>"
                    elif l_relation == "Viparita Raja Yoga (Cancelled)" and not got_direct_cancelled:
                        v = CSI_WEIGHTS["SPECIAL_RULE_VIPARITA_CANCELLED_BONUS"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"<div style='color:#64748B; margin-top:2px;'><b>ℹ️ Lord's Viparita Cancelled</b>: +{v:.2f}{sb_tag}</div>"
                    elif l_relation == "Lagna Lord in Trik Bhava":
                        v = CSI_WEIGHTS["SPECIAL_RULE_LAGNA_TRIK_BHAVA_PENALTY"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"<div style='color:#DC2626; margin-top:2px;'><b>⚠️ Lagna Lord in Trik Bhava</b>: {v:.2f}{sb_tag}</div>"

                    # Exalted / Debilitated Logic (Indirect)
                    if l_data.get("is_exalted"):
                        v = CSI_WEIGHTS["SPECIAL_RULE_EXALTED_LORD_BONUS"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"<div style='color:#059669; margin-top:2px;'><b>✨ Lord ({lord_name}) is Exalted (Indirect)</b>: +{v:.2f}{sb_tag}</div>"
                    elif l_data.get("is_debilitated"):
                        v = CSI_WEIGHTS["SPECIAL_RULE_DEB_LORD_PENALTY"] * l_sb_mod
                        net_energy += v
                        if abs(v) > 0.001: lord_mod_html += f"<div style='color:#64748B; margin-top:2px;'><b>ℹ️ Lord ({lord_name}) is Debilitated (Indirect)</b>: {v:.2f}{sb_tag}</div>"


                func_mod_html = occupant_mod_html + lord_mod_html
            
            if net_energy > 2.0: h_vector = "Highly Constructive"
            elif net_energy > 1.2: h_vector = "Constructive"
            elif net_energy < 0.5 and malefic_pressure > benefic_support: h_vector = "Highly Destructive"
            elif net_energy < 0.8: h_vector = "Destructive"
            elif malefic_pressure > 0.8: h_vector = "Challenging"
            else: h_vector = "Passive"

            csi_results["houses"][h_num] = {
                "base_net_energy": base_net_energy,
                "net_energy": net_energy,
                "vector_status": h_vector,
                "sav": sav,
                "lord": lord_name,
                "lord_csi": lord_csi,
                "occupants": occupants + nodes,
                "occupant_details": occ_details,
                "benefic_support": benefic_support,
                "malefic_pressure": malefic_pressure,
                "occ_energy": occ_energy,
                "func_mod_html": func_mod_html
            }

        return csi_results

# ==============================================================================
# MAIN DIALOG: COMPOSITE STRENGTH DETAILS
# ==============================================================================
class CompositeStrengthDialog(QDialog):
    def __init__(self, csi_data, chart_data, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowFlags(Qt.WindowType.Window)
        self.setWindowTitle("Composite Strength Index (CSI) - AstroBasics Diamond Chart Pro : USE WITH CAUTION")
        self.resize(1100, 850)
        self.scrollers = []

        self.csi_data = csi_data
        self.chart_data = chart_data

        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 4px; }
            QTabBar::tab { background: #E2E8F0; padding: 10px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; color: #0284C7; border-bottom: 2px solid #0284C7; }
            QTableWidget { background: #FFFFFF; alternate-background-color: #F8FAFC; border: 1px solid #CBD5E1; }
            QHeaderView::section { background-color: #E2E8F0; font-weight: bold; padding: 6px; border: 1px solid #CBD5E1; }
            QScrollArea { background-color: transparent; }
        """)

        layout = QVBoxLayout(self)
        
        info_lbl = QLabel(
            "<b>Composite Strength Index (CSI)</b> merges Shadbala, Ashtakavarga, and Avasthas into a unified scalar. "
            "It applies penalties for combustion and nodal conjunctions, mapping everything to final Nature in which houses or planets express themselves."
            "<i>  Note:</i>  Since the author did not refer to classical texts while implementing this, care must be taken while using this Index."
        )
        info_lbl.setStyleSheet("color: #334155; font-size: 13px; margin-bottom: 8px;")
        info_lbl.setWordWrap(True)
        layout.addWidget(info_lbl)

        checkbox_style = """
            QCheckBox { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: 500; color: #334155; }
            QCheckBox:hover { background-color: #F1F5F9; border: 1px solid #CBD5E1; }
            QCheckBox:checked { background-color: #F0F9FF; border: 1px solid #0EA5E9; color: #0369A1; }
            QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #CBD5E1; background-color: white; }
            QCheckBox::indicator:checked { background-color: #0EA5E9; }
        """

        self.cb_functional = QCheckBox("Use Functional Benefic/Malefic", self)
        self.cb_functional.setStyleSheet(checkbox_style)
        self.cb_functional.setChecked(True)
        self.cb_functional.stateChanged.connect(self.recalculate_and_refresh)

        self.cb_shadbala = QCheckBox("Scale by Planet Shadbala", self) 
        self.cb_shadbala.setStyleSheet(checkbox_style)
        self.cb_shadbala.setChecked(True)
        self.cb_shadbala.stateChanged.connect(self.recalculate_and_refresh)
        
        cb_layout = QHBoxLayout()
        cb_layout.addWidget(self.cb_functional)
        cb_layout.addWidget(self.cb_shadbala)
        cb_layout.addStretch() 
        layout.addLayout(cb_layout)

        self.tabs = QTabWidget()
        self.tab_chart = QWidget()
        self.tab_table = QWidget()
        
        self.tab_chart_layout = QVBoxLayout(self.tab_chart)
        self.tab_table_layout = QVBoxLayout(self.tab_table)
        
        # Split second tab into table container and settings container
        self.table_container = QVBoxLayout()
        self.tab_table_layout.addLayout(self.table_container)
        self.build_settings_panel()
        
        self.tabs.addTab(self.tab_chart, "1. Houses Analysis")
        self.tabs.addTab(self.tab_table, "2. Planetary Analysis")
        layout.addWidget(self.tabs)
        
        self.recalculate_and_refresh()

    def apply_smooth_scroll(self, widget):
        if SmoothScroller:
            scroller = SmoothScroller(widget)
            self.scrollers.append(scroller)
            
    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                elif item.layout() is not None:
                    self._clear_layout(item.layout())

    def recalculate_and_refresh(self):
        use_func = self.cb_functional.isChecked()
        scale_sb = self.cb_shadbala.isChecked()
        calc = CSICalculator(self.app, use_functional=use_func, scale_by_shadbala=scale_sb)
        new_csi_data = calc.calculate_csi()
        if new_csi_data:
            self.csi_data = new_csi_data
            
            # --- CRITICAL FIX: Push the fresh calculation to the global app cache ---
            self.app._csi_results = new_csi_data
            
            self.chart_data = getattr(self.app, 'current_base_chart', self.chart_data)
            self.build_chart_tab()
            self.build_table_tab()

    def update_weight(self, key, value):
        if CSI_WEIGHTS[key] != value:
            CSI_WEIGHTS[key] = value
            save_csi_weights()
            self.recalculate_and_refresh()

    def reset_weights(self):
        global CSI_WEIGHTS
        CSI_WEIGHTS.update(DEFAULT_CSI_WEIGHTS)
        save_csi_weights()
        self.build_settings_panel()
        self.recalculate_and_refresh()

    def build_settings_panel(self):
        if hasattr(self, 'settings_group'):
            self.settings_group.deleteLater()
            
        self.settings_group = QGroupBox("Calculation weights and modifiers")
        self.settings_group.setStyleSheet("QGroupBox { font-weight: bold; border: 1px solid #CBD5E1; border-radius: 6px; margin-top: 10px; }")
        
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setMaximumHeight(250)
        settings_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.apply_smooth_scroll(settings_scroll)
        
        settings_widget = QWidget()
        settings_layout = QGridLayout(settings_widget)
        settings_layout.setHorizontalSpacing(15)
        
        row, col = 0, 0
        for key, name in WEIGHT_NAMES_MAPPING.items():
            lbl = QLabel(name)
            lbl.setStyleSheet("font-size: 11px; color: #334155;")
            spin = QDoubleSpinBox()
            spin.setRange(-100.0, 100.0)
            spin.setSingleStep(0.05)
            spin.setValue(CSI_WEIGHTS[key])
            spin.setStyleSheet("QDoubleSpinBox { padding: 2px; font-size: 11px; border: 1px solid #CBD5E1; border-radius: 3px; }")
            
            spin.editingFinished.connect(lambda k=key, s=spin: self.update_weight(k, s.value()))
            
            settings_layout.addWidget(lbl, row, col*2)
            settings_layout.addWidget(spin, row, col*2 + 1)
            
            col += 1
            if col > 3:  # Changed to 4 columns (0, 1, 2, 3)
                col = 0
                row += 1
                
        settings_scroll.setWidget(settings_widget)
        group_layout = QVBoxLayout(self.settings_group)
        group_layout.addWidget(settings_scroll)
        
        self.tab_table_layout.addWidget(self.settings_group)

    def build_chart_tab(self):
        self._clear_layout(self.tab_chart_layout)
        
        legend_html = (
            "<div style='background: #F1F5F9; padding: 8px; border-radius: 6px; border: 1px solid #CBD5E1; display: flex; gap: 15px; flex-wrap: wrap; margin-right: 320px;'>"
            "<b>House Energy Legends:</b> "
            "<span style='color: #059669;'>■ Highly Constructive</span> | "
            "<span style='color: #10B981;'>■ Constructive</span> | "
            "<span style='color: #94A3B8;'>■ Passive/Neutral</span> | "
            "<span style='color: #D97706;'>■ Challenging</span> | "
            "<span style='color: #EF4444;'>■ Destructive</span> | "
            "<span style='color: #DC2626;'>■ Highly Destructive</span>"
            "</div>"
        )
        self.tab_chart_layout.addWidget(QLabel(legend_html))
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.apply_smooth_scroll(scroll)
        
        chart_widget = CompositeChartWidget(self.csi_data, self.chart_data)
        scroll.setWidget(chart_widget)
        self.tab_chart_layout.addWidget(scroll)

    def build_table_tab(self):
        self._clear_layout(self.table_container)
        
        table = CustomTooltipTable()
        self.apply_smooth_scroll(table)
        
        cols = ["Planet", "Normalized Shadbala", "Host House SAV Points", "Avastha(Deb/Exh)", "Penalties", "Final Composite Strength", "Expression"]
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        planets_data = self.csi_data.get("planets", {})
        table.setRowCount(len(planets_data))
        
        for row, (p_name, data) in enumerate(planets_data.items()):
            table.setItem(row, 0, QTableWidgetItem(p_name))
            
            sb_item = QTableWidgetItem(f"{data['norm_sb']:.2f}x")
            sb_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 1, sb_item)
            
            sav_item = QTableWidgetItem(f"{data['norm_sav']:.2f}x")
            sav_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 2, sav_item)
            
            av_item = QTableWidgetItem(f"{data['avastha']:.2f}")
            av_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(row, 3, av_item)
            
            pens = []
            if data['combust'] and abs(CSI_WEIGHTS["COMBUSTION_PENALTY"]) > 0.001: pens.append("Combust")
            if data['retro'] and abs(CSI_WEIGHTS["RETROGRADE_MODIFIER"]) > 0.001: pens.append("Retro")
            if data['node_conj'] and abs(CSI_WEIGHTS["ECLIPSE_NODE_PENALTY"]) > 0.001: pens.append("Eclipse")
            pen_str = ", ".join(pens) if pens else "None"
            
            pen_item = QTableWidgetItem(pen_str)
            if pens: pen_item.setForeground(QColor("#DC2626"))
            table.setItem(row, 4, pen_item)
            
            csi_item = QTableWidgetItem(f"{data['csi']:.2f}")
            csi_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            csi_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            if data['csi'] >= 1.0: csi_item.setBackground(QColor("#D1FAE5"))
            elif data['csi'] < 0.6: csi_item.setBackground(QColor("#FEE2E2"))
            
            w_sb = CSI_WEIGHTS["SHADBALA_NORM_WEIGHT"]
            w_sav = CSI_WEIGHTS["ASHTAKAVARGA_SAV_WEIGHT"]
            w_av = CSI_WEIGHTS["AVASTHA_DIGNITY_WEIGHT"]
            
            c_sb = data['norm_sb'] * w_sb
            c_sav = data['norm_sav'] * w_sav
            c_av = data['avastha'] * w_av
            
            base_csi = c_sb + c_sav + c_av
            mod = data.get("total_modifier", 1.0)
            
            mod_html = data.get("base_mod_html", "") + data.get("mod_html_ext", "")
            special_rule_html = data.get("special_rule_html", "")
                
            tt_html = (
                f"<div style='min-width: 300px;'>"
                f"<h3 style='margin:0; color:#0284C7;'>{p_name} Composite Strength</h3><hr style='border-top: 1px solid #CBD5E1; margin: 4px 0;'>"
                f"<b>Nature:</b> <span style='color:#8B5CF6; font-weight:bold;'>{data.get('nature_applied', 'Unknown')}</span> "
                f"<span style='font-size:11px; color:#64748B;'>({data.get('nature_reason', '')})</span><br>"
                f"{special_rule_html}"
                f"<hr style='border-top: 1px dashed #CBD5E1; margin: 4px 0;'>"
                f"<b>Base Calculations:</b><br>"
                f"• Shadbala: {data['norm_sb']:.2f}*{w_sb} = <span style='color:#0284C7;'>{c_sb:.2f}</span><br>"
                f"• SAV: {data['norm_sav']:.2f}*{w_sav} = <span style='color:#0284C7;'>{c_sav:.2f}</span><br>"
                f"• Avastha: {data['avastha']:.2f}*{w_av} = <span style='color:#0284C7;'>{c_av:.2f}</span><br>"
                f"<b>Base Sum = {base_csi:.2f}</b>"
                f"<hr style='border-top: 1px dashed #CBD5E1; margin: 4px 0;'>"
                f"<b>Modifiers:</b><br>"
                f"{mod_html if mod_html else '• None<br>'}"
                f"<b>Total Multiplier = {max(0.1, mod):.2f}</b>"
                f"<hr style='border-top: 1px dashed #CBD5E1; margin: 4px 0;'>"
                f"<b>Final CSI:</b> {base_csi:.2f} * {max(0.1, mod):.2f} = <span style='font-size:14px; font-weight:bold;'>{data['csi']:.2f}</span>"
                f"</div>"
            )
            csi_item.setData(Qt.ItemDataRole.UserRole, tt_html)
            self.table_container.addWidget(table)
            table.setItem(row, 5, csi_item)
            
            vec_item = QTableWidgetItem(data['vector'])
            vec_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if "Constructive" in data['vector']: vec_item.setForeground(QColor("#059669"))
            elif "Destructive" in data['vector']: vec_item.setForeground(QColor("#DC2626"))
            elif "Challenging" in data['vector']: vec_item.setForeground(QColor("#D97706"))
            vec_item.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            table.setItem(row, 6, vec_item)

# ==============================================================================
# PLUGIN ENTRY POINT
# ==============================================================================
def setup_ui(app, layout):
    shared_group_id = "AdvancedAstroGroup"
    
    shared_group = None
    for i in range(layout.count()):
        w = layout.itemAt(i).widget()
        if w and w.objectName() == shared_group_id:
            shared_group = w
            break
            
    if not shared_group:
        shared_group = QGroupBox("Strength Analysis")
        shared_group.setObjectName(shared_group_id)
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(6, 6, 6, 6)
        group_layout.setSpacing(6)
        shared_group.setLayout(group_layout)
        layout.addWidget(shared_group)
        
    target_layout = shared_group.layout()

    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #dcdde1; margin-top: 4px; margin-bottom: 4px;")
    target_layout.addWidget(line)

    lbl_title = QLabel("Composite Strength Index")
    lbl_title.setStyleSheet("color: #0284C7; font-weight: bold; font-size: 15px; margin-top: 4px;")
    target_layout.addWidget(lbl_title)
    
    lbl_name = "csi_summary_lbl_active"
    btn_name = "csi_btn_details_active"
    
    summary_lbl = QLabel("<i>Awaiting dependencies (Shadbala/BPHS)...</i>")
    summary_lbl.setObjectName(lbl_name)
    summary_lbl.setStyleSheet("background-color: #fdfefe; border: 1px solid #dcdde1; border-radius: 4px; padding: 6px; font-family: monospace;")
    summary_lbl.setWordWrap(True)
    target_layout.addWidget(summary_lbl)

    btn_details = QPushButton("Composite Strength Index")
    btn_details.setObjectName(btn_name)
    btn_details.setStyleSheet("""
        QPushButton { background-color: #34495e; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }
        QPushButton:hover { background-color: #0284C7; }
        QPushButton:disabled { background-color: #bdc3c7; color: #7f8c8d; }
    """)
    btn_details.setEnabled(False)
    target_layout.addWidget(btn_details)

    app._csi_results = {}
    current_ui_id = id(summary_lbl)
    app._csi_active_ui_id = current_ui_id
    
    retry_timer = QTimer()
    retry_timer.setSingleShot(True)
    app._csi_retry_timer = retry_timer

    def run_computation():
        if getattr(app, '_csi_active_ui_id', None) != current_ui_id:
            return

        current_shared_group = app.findChild(QGroupBox, shared_group_id)
        if not current_shared_group:
            error_print("CSI: Layout not mounted yet. Retrying in 1s...")
            retry_timer.start(1000)
            return
        
        active_lbl = current_shared_group.findChild(QLabel, lbl_name)
        active_btn = current_shared_group.findChild(QPushButton, btn_name)
        
        if not active_lbl or not active_btn:
            error_print("CSI: labels missing. Retrying in 1s...")
            retry_timer.start(1000)
            return

        if not hasattr(app, 'current_base_chart') or not app.current_base_chart or not app.current_base_chart.get("planets"):
            active_lbl.setText("<i>Waiting for astrological engine...</i>")
            retry_timer.start(1000) 
            return
            
        if not hasattr(app, '_shadbala_results') or not app._shadbala_results:
            active_lbl.setText("<i>Waiting for Shadbala & Ashtakavarga metrics...</i>")
            retry_timer.start(1000) 
            return

        try:
            calculator = CSICalculator(app)
            results = calculator.calculate_csi()
            
            if not results:
                active_lbl.setText("<i>Calculation yielded empty data...</i>")
                retry_timer.start(1000)
                return

            # Push the very first calculation into the main app cache
            app._csi_results = results
            
            planets_list = list(results["planets"].items())
            if planets_list:
                strongest = max(planets_list, key=lambda x: x[1]['csi'])
                weakest = min(planets_list, key=lambda x: x[1]['csi'])
                
                summary_txt = (
                    f"<b>Best Support:</b> {strongest[0]} (CSI: {strongest[1]['csi']:.2f})<br>"
                    f"<b>Most Challenging:</b> {weakest[0]} (CSI: {weakest[1]['csi']:.2f})"
                )
                active_lbl.setText(summary_txt)
                active_btn.setEnabled(True)
            
            if hasattr(app, '_csi_dialog') and getattr(app._csi_dialog, 'isVisible', lambda: False)():
                pass
                
        except Exception as e:
            error_print(f"CSI Calculation Error: {e}")
            active_lbl.setText(f"<i>Error in CSI Calculation. Retrying...</i>")
            retry_timer.start(1500)

    retry_timer.timeout.connect(run_computation)

    def auto_trigger(*args, **kwargs):
        if getattr(app, '_csi_active_ui_id', None) == current_ui_id:
            retry_timer.start(0)

    if hasattr(app, 'calc_worker'):
        app.calc_worker.calc_finished.connect(auto_trigger)

    def show_details():
        if hasattr(app, '_csi_results') and app._csi_results:
            app._csi_dialog = CompositeStrengthDialog(app._csi_results, app.current_base_chart, app)
            app._csi_dialog.showMaximized()
            app._csi_dialog.raise_()

    btn_details.clicked.connect(show_details)
    auto_trigger()


# ==============================================================================
# GLOBAL HELPER API FOR OTHER PLUGINS
# ==============================================================================
class LiveCSIValue:
    """
    A dynamic wrapper that behaves exactly like a float.
    It fetches the latest CSI value on-demand every time it is used, printed, or calculated.
    """
    def __init__(self, helper, type_key, identifier):
        self.helper = helper
        self.type_key = type_key       # 'house' or 'planet'
        self.identifier = identifier   # e.g., 4 or 'Sun'
        
    @property
    def value(self):
        # Always fetches the live value from the helper (returns 0.0 if not loaded)
        if self.type_key == 'house':
            return self.helper._get_h(self.identifier)
        return self.helper._get_p(self.identifier)
        
    # --- Standard Type Conversions ---
    def __float__(self): return float(self.value)
    def __int__(self): return int(self.value)
    def __str__(self): return f"{self.value:.2f}"
    def __format__(self, format_spec): return format(self.value, format_spec)
    def __round__(self, ndigits=None): return round(self.value, ndigits)
    def __bool__(self): return bool(self.value)
    
    # --- Math Operator Overloads ---
    def _val(self, other):
        return other.value if isinstance(other, LiveCSIValue) else float(other)
        
    def __add__(self, other): return self.value + self._val(other)
    def __radd__(self, other): return self._val(other) + self.value
    def __sub__(self, other): return self.value - self._val(other)
    def __rsub__(self, other): return self._val(other) - self.value
    def __mul__(self, other): return self.value * self._val(other)
    def __rmul__(self, other): return self._val(other) * self.value
    def __truediv__(self, other): return self.value / self._val(other)
    def __rtruediv__(self, other): return self._val(other) / self.value
    
    # --- Comparisons ---
    def __lt__(self, other): return self.value < self._val(other)
    def __le__(self, other): return self.value <= self._val(other)
    def __eq__(self, other): return self.value == self._val(other)
    def __ge__(self, other): return self.value >= self._val(other)
    def __gt__(self, other): return self.value > self._val(other)


class CSIHelper(QObject):
    """
    Singleton Helper to access CSI values across plugins.
    Emits csi_updated when the base plugin loads or when user weights change.
    """
    csi_updated = pyqtSignal()
    
    _instance = None
    
    @classmethod
    def get_instance(cls, app):
        """Safely fetch the singleton instance of the CSI Helper."""
        if cls._instance is None:
            cls._instance = cls(app)
        return cls._instance
        
    def __init__(self, app):
        super().__init__()
        self.app = app
        self._last_results_id = None
        
        # Setup a lightweight polling timer to detect when the main plugin 
        # generates a new CSI dictionary (either on load or weight change).
        self.watcher_timer = QTimer(self)
        self.watcher_timer.timeout.connect(self._check_for_updates)
        self.watcher_timer.start(500)  # Check every 500ms

    def _check_for_updates(self):
        """Monitors app._csi_results memory ID to detect fresh calculations."""
        current_results = getattr(self.app, '_csi_results', None)
        if current_results is not None:
            current_id = id(current_results)
            if current_id != self._last_results_id:
                self._last_results_id = current_id
                # Notify the rest of the application that data has changed!
                self.csi_updated.emit()

    def _get_h(self, h_num):
        """Internal fetcher for house. Returns 0.0 if not ready."""
        res = getattr(self.app, '_csi_results', None)
        if res and "houses" in res and h_num in res["houses"]:
            return float(res["houses"][h_num].get("net_energy", 0.0))
        return 0.0

    def _get_p(self, p_name):
        """Internal fetcher for planets. Returns 0.0 if not ready."""
        res = getattr(self.app, '_csi_results', None)
        if res and "planets" in res and p_name in res["planets"]:
            return float(res["planets"][p_name].get("csi", 0.0))
        return 0.0

    # ==========================================
    # PUBLIC API: HOUSE CSI METHODS
    # ==========================================
    def csi_house_1(self): return LiveCSIValue(self, 'house', 1)
    def csi_house_2(self): return LiveCSIValue(self, 'house', 2)
    def csi_house_3(self): return LiveCSIValue(self, 'house', 3)
    def csi_house_4(self): return LiveCSIValue(self, 'house', 4)
    def csi_house_5(self): return LiveCSIValue(self, 'house', 5)
    def csi_house_6(self): return LiveCSIValue(self, 'house', 6)
    def csi_house_7(self): return LiveCSIValue(self, 'house', 7)
    def csi_house_8(self): return LiveCSIValue(self, 'house', 8)
    def csi_house_9(self): return LiveCSIValue(self, 'house', 9)
    def csi_house_10(self): return LiveCSIValue(self, 'house', 10)
    def csi_house_11(self): return LiveCSIValue(self, 'house', 11)
    def csi_house_12(self): return LiveCSIValue(self, 'house', 12)

    # ==========================================
    # PUBLIC API: PLANETARY CSI METHODS
    # ==========================================
    def csi_sun(self): return LiveCSIValue(self, 'planet', "Sun")
    def csi_moon(self): return LiveCSIValue(self, 'planet', "Moon")
    def csi_mars(self): return LiveCSIValue(self, 'planet', "Mars")
    def csi_mercury(self): return LiveCSIValue(self, 'planet', "Mercury")
    def csi_jupiter(self): return LiveCSIValue(self, 'planet', "Jupiter")
    def csi_venus(self): return LiveCSIValue(self, 'planet', "Venus")
    def csi_saturn(self): return LiveCSIValue(self, 'planet', "Saturn")
    def csi_rahu(self): return LiveCSIValue(self, 'planet', "Rahu")
    def csi_ketu(self): return LiveCSIValue(self, 'planet', "Ketu")