# dynamic_settings_modules/shadbala_mod.py

import math, datetime, traceback
from PyQt6.QtWidgets import (QPushButton, QMessageBox, QLabel, QVBoxLayout, QHBoxLayout, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QWidget, QTabWidget, QTextEdit, QStyledItemDelegate,QGroupBox)
from PyQt6.QtGui import QCursor, QFont, QColor, QPen, QBrush, QPainter
from PyQt6.QtCore import Qt, QTimer, QPoint, QRectF, QPointF
import __main__

# Attempt to load SmoothScroller from the main application namespace
SmoothScroller = getattr(__main__, 'SmoothScroller', None)

import astro_engine as astro_engine

# ==============================================================================
# CLASSICAL CONSTANTS & CONFIGURATION TABLES
# ==============================================================================

DEBILITATION_DEGREES = {
    "Sun": 190.0, "Moon": 213.0, "Mars": 118.0, 
    "Mercury": 345.0, "Jupiter": 275.0, "Venus": 177.0, "Saturn": 20.0
}

NATURAL_FRIENDS = {
    "Sun": ["Moon", "Mars", "Jupiter"], "Moon": ["Sun", "Mercury"],
    "Mars": ["Sun", "Moon", "Jupiter"], "Mercury": ["Sun", "Venus"],
    "Jupiter": ["Sun", "Moon", "Mars"], "Venus": ["Mercury", "Saturn"],
    "Saturn": ["Mercury", "Venus"]
}

NATURAL_ENEMIES = {
    "Sun": ["Venus", "Saturn"], "Moon": [], "Mars": ["Mercury"],
    "Mercury": ["Moon"], "Jupiter": ["Mercury", "Venus"],
    "Venus": ["Sun", "Moon"], "Saturn": ["Sun", "Moon", "Mars"]
}

REQUIRED_SHADBALA = {
    "Sun": 390.0, "Moon": 360.0, "Mars": 300.0, 
    "Mercury": 420.0, "Jupiter": 390.0, "Venus": 330.0, "Saturn": 300.0
}

NAISARGIKA_BALA = {
    "Sun": 60.0, "Moon": 51.43, "Venus": 42.85, 
    "Jupiter": 34.28, "Mercury": 25.71, "Mars": 17.14, "Saturn": 8.57
}

# Bhinna Ashtakavarga mappings strictly mapped as per the provided BPHS text rules
BAV_BinduMatrix = {
    "Sun": {
        "Sun": [1, 2, 4, 7, 8, 9, 10, 11],
        "Moon": [3, 6, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [5, 6, 9, 11],
        "Venus": [6, 7, 12],
        "Saturn": [1, 2, 4, 7, 8, 9, 10, 11],
        "Ascendant": [3, 4, 6, 10, 11, 12]
    },
    "Moon": {
        "Sun": [3, 6, 7, 8, 10, 11],
        "Moon": [1, 3, 6, 7, 9, 10, 11],
        "Mars": [2, 3, 5, 6, 10, 11],
        "Mercury": [1, 3, 4, 5, 7, 8, 10, 11],
        "Jupiter": [1, 2, 4, 7, 8, 10, 11],
        "Venus": [3, 4, 5, 7, 9, 10, 11],
        "Saturn": [3, 5, 6, 11],
        "Ascendant": [3, 6, 10, 11]
    },
    "Mars": {
        "Sun": [3, 5, 6, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [3, 5, 6, 11],
        "Jupiter": [6, 10, 11, 12],
        "Venus": [6, 8, 11, 12],
        "Saturn": [1, 4, 7, 8, 9, 10, 11],
        "Ascendant": [1, 3, 6, 10, 11]
    },
    "Mercury": {
        "Sun": [6, 9, 11, 12],
        "Moon": [2, 4, 6, 8, 10, 11],
        "Mars": [1, 2, 4, 7, 8, 9, 10, 11],
        "Mercury": [1, 3, 5, 6, 9, 10, 11, 12],
        "Jupiter": [6, 8, 11, 12],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 11],
        "Saturn": [1, 2, 4, 5, 7, 8, 9, 10, 11],
        "Ascendant": [1, 2, 4, 6, 8, 10, 11]
    },
    "Jupiter": {
        "Sun": [1, 2, 3, 4, 7, 8, 9, 10, 11],
        "Moon": [2, 5, 7, 9, 11],
        "Mars": [1, 2, 4, 7, 8, 10, 11],
        "Mercury": [1, 2, 4, 5, 6, 9, 10, 11],
        "Jupiter": [2, 3, 7, 8, 10, 11],
        "Venus": [2, 5, 6, 9, 10, 11],
        "Saturn": [3, 5, 6, 12],
        "Ascendant": [1, 2, 4, 5, 6, 7, 9, 10, 11]
    },
    "Venus": {
        "Sun": [8, 11, 12],
        "Moon": [1, 2, 3, 4, 5, 8, 9, 11, 12],
        "Mars": [3, 4, 6, 9, 11, 12],
        "Mercury": [3, 5, 6, 9, 11],
        "Jupiter": [5, 8, 9, 10, 11],
        "Venus": [1, 2, 3, 4, 5, 8, 9, 10, 11],
        "Saturn": [3, 4, 5, 8, 9, 10, 11],
        "Ascendant": [1, 2, 3, 4, 5, 8, 9, 11]
    },
    "Saturn": {
        "Sun": [1, 2, 4, 7, 8, 10, 11],
        "Moon": [3, 6, 11],
        "Mars": [3, 5, 6, 10, 11, 12],
        "Mercury": [6, 8, 9, 10, 11, 12],
        "Jupiter": [5, 6, 11, 12],
        "Venus": [6, 11, 12],
        "Saturn": [3, 5, 6, 11],
        "Ascendant": [1, 3, 4, 6, 10, 11]
    },
    "Ascendant": {
        "Sun": [3, 4, 6, 10, 11, 12],
        "Moon": [3, 6, 10, 11, 12],
        "Mars": [1, 3, 6, 10, 11],
        "Mercury": [1, 2, 4, 6, 8, 10, 11],
        "Jupiter": [1, 2, 4, 5, 6, 7, 9, 10, 11],
        "Venus": [1, 2, 3, 4, 5, 8, 9],
        "Saturn": [1, 3, 4, 6, 10, 11],
        "Ascendant": [3, 6, 10, 11]
    }
}

# ==============================================================================
# CUSTOM UI COMPONENTS FOR INSTANT TOOLTIPS
# ==============================================================================

class HoverProgressBar(QProgressBar):
    def __init__(self, tooltip_html, parent=None):
        super().__init__(parent)
        self.tooltip_html = tooltip_html
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

class CustomTooltipTable(QTableWidget):
    """A custom table that bypasses OS delays to show HTML tooltips instantly following the cursor."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.tooltip_label = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
        """)
        self.tooltip_label.hide()
        
    def mouseMoveEvent(self, event):
        pos = event.pos()
        item = self.itemAt(pos)
        index = self.indexAt(pos)
        widget = self.cellWidget(index.row(), index.column())
        
        tt_text = ""
        if widget and hasattr(widget, 'tooltip_html') and widget.tooltip_html:
            tt_text = widget.tooltip_html
        elif item and item.data(Qt.ItemDataRole.UserRole):
            tt_text = item.data(Qt.ItemDataRole.UserRole)
            
        if tt_text:
            if self.tooltip_label.text() != tt_text:
                self.tooltip_label.setText(tt_text)
                self.tooltip_label.adjustSize()
                
            global_pos = event.globalPosition().toPoint()
            new_x, new_y = global_pos.x() + 15, global_pos.y() + 15
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): 
                    new_x = global_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): 
                    new_y = global_pos.y() - self.tooltip_label.height() - 5
            
            self.tooltip_label.move(new_x, new_y)
            if not self.tooltip_label.isVisible():
                self.tooltip_label.show()
            self.tooltip_label.raise_()
        else:
            self.tooltip_label.hide()
            
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tooltip_label.hide()
        super().leaveEvent(event)

class WeakRowDelegate(QStyledItemDelegate):
    """Custom delegate to draw a continuous red border around entire rows marked as weak."""
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        is_weak = index.data(Qt.ItemDataRole.UserRole + 1)
        if is_weak:
            painter.save()
            pen = QPen(QColor("#DC2626"), 2)
            painter.setPen(pen)
            
            rect = option.rect
            painter.drawLine(rect.topLeft(), rect.topRight())
            bottom_left = QPoint(rect.left(), rect.bottom() - 1)
            bottom_right = QPoint(rect.right(), rect.bottom() - 1)
            painter.drawLine(bottom_left, bottom_right)
            
            if index.column() == 0:
                painter.drawLine(rect.topLeft(), rect.bottomLeft())
            if index.column() == 12: 
                right_top = QPoint(rect.right() - 1, rect.top())
                right_bottom = QPoint(rect.right() - 1, rect.bottom())
                painter.drawLine(right_top, right_bottom)
            painter.restore()

class AshtakavargaBarChart(QWidget):
    """Visualizes Bindu distribution (SAV) and overlays planetary transit strength."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sav_points = []
        self.planet_houses = {}
        self.bar_rects = {}
        self.setMinimumHeight(240)
        self.setMouseTracking(True)
        self.tooltip_label = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""
            QLabel {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 10px;
                font-size: 13px;
                font-family: 'Segoe UI', Tahoma, sans-serif;
            }
        """)
        self.tooltip_label.hide()

    def update_data(self, sav_points, planet_houses):
        self.sav_points = sav_points
        self.planet_houses = planet_houses
        self.update()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        pos_f = QPointF(float(pos.x()), float(pos.y()))
        tt_text = ""
        sign_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        for i, rect in self.bar_rects.items():
            if rect.contains(pos_f):
                val = self.sav_points[i]
                planets = self.planet_houses.get(i, [])
                planet_str = ", ".join(planets) if planets else "None"
                
                if val >= 28:
                    status = "Highly Auspicious 🟢"
                    color = "#10B981"
                elif val >= 25:
                    status = "Average / Neutral"
                    color = "#F59E0B"
                else:
                    status = "Inauspicious ⚠️"
                    color = "#EF4444"
                
                tt_text = (
                    f"<div style='min-width: 200px;'>"
                    f"<h3 style='margin:0; color:{color};'>{sign_names[i]} SAV</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                    f"<b>Total Points:</b> <span style='font-size: 14px; font-weight: bold;'>{val}</span><br>"
                    f"<b>Status:</b> {status}<br><br>"
                    f"<b>Transiting Planets Here:</b><br>{planet_str}"
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
                if new_x + self.tooltip_label.width() > sg.right(): 
                    new_x = global_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): 
                    new_y = global_pos.y() - self.tooltip_label.height() - 5
            
            self.tooltip_label.move(new_x, new_y)
            if not self.tooltip_label.isVisible():
                self.tooltip_label.show()
            self.tooltip_label.raise_()
        else:
            self.tooltip_label.hide()
            super().mouseMoveEvent(event)
        
    def leaveEvent(self, event):
        self.tooltip_label.hide()
        super().leaveEvent(event)

    def paintEvent(self, event):
        if not self.sav_points: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect()
        painter.fillRect(rect, QColor("#F8FAFC"))
        
        w, h = rect.width(), rect.height()
        ml, mr, mt, mb = 40, 20, 30, 30
        pw, ph = w - ml - mr, h - mt - mb
        
        max_val = max(50, max(self.sav_points) + 5)
        
        painter.setPen(QPen(QColor("#CBD5E1"), 1))
        painter.drawLine(ml, mt, ml, mt + ph)
        painter.drawLine(ml, mt + ph, ml + pw, mt + ph)
        
        painter.setFont(QFont("Segoe UI", 8))
        painter.setPen(QColor("#64748B"))
        for y_val in [0, 10, 20, 28, 30, 40, 50]:
            if y_val > max_val: continue
            y_pos = mt + ph - (y_val / max_val) * ph
            painter.drawText(ml - 25, int(y_pos + 4), str(y_val))
            if y_val != 28:
                painter.setPen(QPen(QColor("#E2E8F0"), 1, Qt.PenStyle.DashLine))
                painter.drawLine(ml, int(y_pos), ml + pw, int(y_pos))
                painter.setPen(QColor("#64748B"))
            
        y_28 = mt + ph - (28 / max_val) * ph
        painter.setPen(QPen(QColor("#10B981"), 2, Qt.PenStyle.DashLine))
        painter.drawLine(ml, int(y_28), ml + pw, int(y_28))
        
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.drawText(ml + pw - 90, int(y_28 - 5), "28 (Auspicious)")
        
        bar_w = (pw / 12) * 0.6
        spacing = pw / 12
        
        self.bar_rects.clear()
        sign_names = ["Ar", "Ta", "Ge", "Cn", "Le", "Vi", "Li", "Sc", "Sg", "Cp", "Aq", "Pi"]
        
        for i in range(12):
            val = self.sav_points[i]
            x = ml + i * spacing + (spacing - bar_w) / 2
            bar_h = (val / max_val) * ph
            y = mt + ph - bar_h
            
            self.bar_rects[i] = QRectF(x, mt, bar_w, ph + 25)
            
            if val >= 28: color = "#10B981"
            elif val >= 25: color = "#F59E0B"
            else: color = "#EF4444"
            
            painter.setBrush(QBrush(QColor(color)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_h), 4, 4)
            
            painter.setPen(QColor("#1E293B"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(QRectF(x, y - 20, bar_w, 20), Qt.AlignmentFlag.AlignCenter, str(val))
            
            painter.setPen(QColor("#475569"))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(QRectF(x, mt + ph + 5, bar_w, 20), Qt.AlignmentFlag.AlignCenter, sign_names[i])
            
            planets = self.planet_houses.get(i, [])
            for p_idx, p_name in enumerate(planets):
                p_abbr = p_name[:2]
                py = mt + ph - 24 - (p_idx * 20)
                
                badge_rect = QRectF(x + 2, py, bar_w - 4, 18)
                painter.setBrush(QBrush(QColor("#FFFFFF")))
                painter.setPen(QPen(QColor("#475569"), 1))
                painter.drawRoundedRect(badge_rect, 4, 4)
                
                painter.setPen(QColor("#0F172A"))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, p_abbr)

# ==============================================================================
# CALCULATION ENGINE
# ==============================================================================
def get_jm_sputadrishti(degree, aspectingplanet):
    if degree <= 30: return 0.0
    elif degree <= 60: return (degree - 30.0) * 2.0 if aspectingplanet == "Saturn" else (degree - 30.0) / 2.0
    elif degree <= 90: return 45.0 + (90.0 - degree) / 2.0 if aspectingplanet == "Saturn" else degree - 45.0
    elif degree <= 120: return 45.0 + (degree - 90.0) / 2.0 if aspectingplanet in ["Mars", "Jupiter"] else 30.0 + (120.0 - degree) / 2.0
    elif degree <= 150: return (150.0 - degree) * 2.0 if aspectingplanet in ["Mars", "Jupiter"] else 150.0 - degree
    elif degree <= 180: return abs(150.0 - degree) * 2.0
    elif degree <= 210: return 60.0 if aspectingplanet == "Mars" else (300.0 - degree) / 2.0
    elif degree <= 240:
        if aspectingplanet == "Mars": return 270.0 - degree
        elif aspectingplanet == "Jupiter": return 45.0 + (degree - 210.0) / 2.0
        else: return (300.0 - degree) / 2.0
    elif degree <= 270:
        if aspectingplanet == "Saturn": return degree - 210.0
        elif aspectingplanet == "Jupiter": return 15.0 + 2.0 * (270.0 - degree) / 3.0
        else: return (300.0 - degree) / 2.0
    elif degree <= 300: return (300.0 - degree) * 2.0 if aspectingplanet == "Saturn" else (300.0 - degree) / 2.0
    return 0.0

class ShadbalaCalculator:
    def __init__(self, base_chart, varga_charts, app):
        self.base_chart = base_chart or {}
        self.varga_charts = varga_charts or {}
        self.app = app
        self.planets_list = self.base_chart.get("planets", [])
        self.valid_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
      
        self.asc_lon = 0.0
        self.cur_jd = float(self.base_chart.get("current_jd", 0.0))
        self._check_swisseph()

    def _check_swisseph(self):
        self.has_swe = False
        try:
            import swisseph as swe
            self.swe = swe
            self.has_swe = True
        except ImportError:
            self.swe = None

    def _setup_ascendant(self):
        asc = self.base_chart.get("ascendant", {})
        self.asc_lon = float(asc.get("degree", asc.get("lon", 0.0)))
        if self.asc_lon == 0.0 and self.has_swe:
            try:
                import swisseph as swe
                lat = float(getattr(self.app, "current_lat", 28.6139))
                lon = float(getattr(self.app, "current_lon", 77.2090))
                ayanamsa = float(swe.get_ayanamsa_ut(self.cur_jd))
                _, ascmc = swe.houses(self.cur_jd, lat, lon, b'S')
                self.asc_lon = (ascmc[0] - ayanamsa) % 360.0
            except Exception:
                pass

    def calc_ashtakavarga(self):
        p_signs = {}
        asc_sign = int(self.asc_lon / 30.0) + 1
        p_signs["Ascendant"] = asc_sign

        valid_grahas_for_occupation = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
        planet_signs_set = set()
        planet_signs_map = {i: [] for i in range(12)}

        for p in self.planets_list:
            p_name = p.get("name")
            p_lon = float(p.get("lon", 0.0))
            if p_name in self.valid_planets:
                p_signs[p_name] = int(p_lon / 30.0) + 1
            if p_name in valid_grahas_for_occupation:
                sign_idx = int(p_lon / 30.0)
                planet_signs_set.add(sign_idx)
                planet_signs_map[sign_idx].append(p_name)

        bav_entities = self.valid_planets + ["Ascendant"]
        bav_points = {p: [0]*12 for p in bav_entities}
        sav_points = [0]*12
        self.bav_traces = {p: {h: [] for h in range(12)} for p in bav_entities}

        for planet in BAV_BinduMatrix:
            for refPlanet in BAV_BinduMatrix[planet]:
                ref_sign = p_signs.get(refPlanet)
                if not ref_sign: continue
                for nth in BAV_BinduMatrix[planet][refPlanet]:
                    target_sign_idx = (ref_sign + nth - 2) % 12
                    if planet in bav_points:
                        bav_points[planet][target_sign_idx] += 1
                        self.bav_traces[planet][target_sign_idx].append(f"<span style='color:#059669'>+1</span> from <b>{refPlanet}</b> <i>(in its {nth}th house)</i>")

        for i in range(12):
            sav_points[i] = sum(bav_points[p][i] for p in self.valid_planets)

        self.bav_points = bav_points
        self.sav_points = sav_points

        # --- Shodhana Calculations (Trikon, Ekadhipatya, Pinda) ---
        self.trikon_points = {p: [0]*12 for p in bav_entities}
        self.ekadhipatya_points = {p: [0]*12 for p in bav_entities}
        self.shodhya_pindas = {p: 0 for p in bav_entities}

        rashi_mult = [7, 10, 8, 4, 10, 6, 7, 8, 9, 5, 11, 12]
        grah_mult = {"Sun": 5, "Moon": 5, "Mars": 8, "Mercury": 5, "Jupiter": 10, "Venus": 7, "Saturn": 5}
        eka_pairs = [(0, 7), (1, 6), (2, 5), (8, 11), (9, 10)]

        for p in bav_entities:
            # 1. Trikon Shodhana
            trikon = list(bav_points[p])
            for t in [(0, 4, 8), (1, 5, 9), (2, 6, 10), (3, 7, 11)]:
                v1, v2, v3 = trikon[t[0]], trikon[t[1]], trikon[t[2]]
                min_v = min(v1, v2, v3)
                if min_v > 0:
                    trikon[t[0]] -= min_v
                    trikon[t[1]] -= min_v
                    trikon[t[2]] -= min_v
            self.trikon_points[p] = trikon

            # 2. Ekadhipatya Shodhana
            eka = list(trikon)
            for s1, s2 in eka_pairs:
                v1, v2 = eka[s1], eka[s2]
                if v1 == 0 or v2 == 0: continue
                
                p1 = s1 in planet_signs_set
                p2 = s2 in planet_signs_set
                
                if p1 and p2:
                    continue # Both have planets
                elif not p1 and not p2: # Both empty
                    if v1 == v2:
                        eka[s1] = eka[s2] = 0
                    else:
                        min_v = min(v1, v2)
                        eka[s1] = eka[s2] = min_v
                else: # One has planet, one empty
                    idx_p = s1 if p1 else s2
                    idx_e = s2 if p1 else s1
                    vp, ve = eka[idx_p], eka[idx_e]
                    
                    if vp > ve:
                        eka[idx_e] = 0
                    elif vp < ve:
                        eka[idx_e] = ve - vp
                    else:
                        eka[idx_e] = 0
            self.ekadhipatya_points[p] = eka

            # 3. Pinda Sadhana
            pinda = 0
            for i in range(12):
                val = eka[i]
                if val > 0:
                    pinda += val * rashi_mult[i]
                    for g in planet_signs_map[i]:
                        if g in grah_mult:
                            pinda += val * grah_mult[g]
            self.shodhya_pindas[p] = pinda

    def get_jm_dignity(self, p_name, varga_name):
        varga_chart = self.varga_charts.get(varga_name, {})
        pv = next((x for x in varga_chart.get("planets", []) if x.get("name") == p_name), None)
        if not pv: return 10.0

        varga_lon = float(pv.get("lon", 0.0))
        varga_sign = int(pv.get("sign_num", int(varga_lon / 30.0) + 1))
        varga_deg = float(pv.get("deg_in_sign", varga_lon % 30.0))

        status = "NONE"
        if varga_name == "D1":
            if p_name == "Sun" and varga_sign == 5: status = "MOOL" if varga_deg <= 20.0 else "OWN"
            elif p_name == "Moon" and varga_sign == 2: status = "EXALT" if varga_deg <= 3.0 else "MOOL"
            elif p_name == "Moon" and varga_sign == 4: status = "OWN"
            elif p_name == "Mars" and varga_sign == 1: status = "MOOL" if varga_deg <= 12.0 else "OWN"
            elif p_name == "Mars" and varga_sign == 8: status = "OWN"
            elif p_name == "Mercury" and varga_sign == 6:
                if varga_deg <= 15.0: status = "EXALT"
                elif varga_deg <= 20.0: status = "MOOL"
                else: status = "OWN"
            elif p_name == "Mercury" and varga_sign == 3: status = "OWN"
            elif p_name == "Jupiter" and varga_sign == 9: status = "MOOL" if varga_deg <= 10.0 else "OWN"
            elif p_name == "Jupiter" and varga_sign == 12: status = "OWN"
            elif p_name == "Venus" and varga_sign == 7: status = "MOOL" if varga_deg <= 15.0 else "OWN"
            elif p_name == "Venus" and varga_sign == 2: status = "OWN"
            elif p_name == "Saturn" and varga_sign == 11: status = "MOOL" if varga_deg <= 20.0 else "OWN"
            elif p_name == "Saturn" and varga_sign == 10: status = "OWN"
        else:
            if p_name == "Sun" and varga_sign == 5: status = "MOOL"
            elif p_name == "Moon" and varga_sign == 2: status = "MOOL"
            elif p_name == "Moon" and varga_sign == 4: status = "OWN"
            elif p_name == "Mars" and varga_sign == 1: status = "MOOL"
            elif p_name == "Mars" and varga_sign == 8: status = "OWN"
            elif p_name == "Mercury" and varga_sign == 6: status = "MOOL"
            elif p_name == "Mercury" and varga_sign == 3: status = "OWN"
            elif p_name == "Jupiter" and varga_sign == 9: status = "MOOL"
            elif p_name == "Jupiter" and varga_sign == 12: status = "OWN"
            elif p_name == "Venus" and varga_sign == 7: status = "MOOL"
            elif p_name == "Venus" and varga_sign == 2: status = "OWN"
            elif p_name == "Saturn" and varga_sign == 11: status = "MOOL"
            elif p_name == "Saturn" and varga_sign == 10: status = "OWN"

        if status in ["EXALT", "MOOL"]: return 45.0
        if status == "OWN": return 30.0

        dispositor = astro_engine.SIGN_RULERS.get(varga_sign)

        nat_friends = NATURAL_FRIENDS.get(p_name, [])
        nat_enemies = NATURAL_ENEMIES.get(p_name, [])
        n_val = 1 if dispositor in nat_friends else (-1 if dispositor in nat_enemies else 0)

        base_p = next((x for x in self.planets_list if x.get("name") == p_name), None)
        base_disp = next((x for x in self.planets_list if x.get("name") == dispositor), None)
        t_val = 0
        if base_p and base_disp:
            p_d1_sign = int(base_p.get("sign_num", int(float(base_p.get("lon", 0.0)) / 30.0) + 1))
            disp_d1_sign = int(base_disp.get("sign_num", int(float(base_disp.get("lon", 0.0)) / 30.0) + 1))
            diff = (disp_d1_sign - p_d1_sign) % 12 + 1
            if diff in [2, 3, 4, 10, 11, 12]: t_val = 1
            else: t_val = -1

        final_val = n_val + t_val
        if final_val == 2: return 20.0     
        elif final_val == 1: return 15.0   
        elif final_val == 0: return 10.0   
        elif final_val == -1: return 4.0   
        elif final_val == -2: return 2.0   
        return 10.0

    def calc_sthana_bala(self, p_name, p_data, p_lon):
        deb_deg = DEBILITATION_DEGREES.get(p_name, 0.0)
        dist = min(abs(p_lon - deb_deg), 360.0 - abs(p_lon - deb_deg))
        uchcha_bala = dist / 3.0

        sapta_bala = sum(self.get_jm_dignity(p_name, v) for v in ["D1", "D2", "D3", "D7", "D9", "D12", "D30"])

        d1_sign = int(p_data.get("sign_num", int(p_lon / 30.0) + 1))
        d9_chart = self.varga_charts.get("D9", {})
        p_d9 = next((x for x in d9_chart.get("planets", []) if x.get("name") == p_name), None)
        d9_sign = int(p_d9.get("sign_num", int(float(p_d9.get("lon", 0.0)) / 30.0) + 1)) if p_d9 else d1_sign

        ojha_bala = 0.0
        if p_name in ["Sun", "Mars", "Mercury", "Jupiter", "Saturn"]:
            if d1_sign % 2 != 0: ojha_bala += 15.0
            if d9_sign % 2 != 0: ojha_bala += 15.0
        else: 
            if d1_sign % 2 == 0: ojha_bala += 15.0
            if d9_sign % 2 == 0: ojha_bala += 15.0

        asc_sign = int(self.base_chart.get("ascendant", {}).get("sign_num", int(self.asc_lon / 30.0) + 1))
        hno = (d1_sign - asc_sign) % 12 + 1
        
        if hno in [1, 4, 7, 10]: kendradi_bala = 60.0
        elif hno in [2, 5, 8, 11]: kendradi_bala = 30.0
        else: kendradi_bala = 15.0

        deg = float(p_data.get("deg_in_sign", p_lon % 30.0))
        drekkana_bala = 0.0
        if deg <= 10.0 and p_name in ["Sun", "Jupiter", "Mars"]: drekkana_bala = 15.0
        elif 10.0 < deg <= 20.0 and p_name in ["Moon", "Venus"]: drekkana_bala = 15.0
        elif deg > 20.0 and p_name in ["Mercury", "Saturn"]: drekkana_bala = 15.0

        return {
            "Total": uchcha_bala + sapta_bala + ojha_bala + kendradi_bala + drekkana_bala,
            "Uchcha": uchcha_bala, "Saptavargaja": sapta_bala, "Ojhayugma": ojha_bala, 
            "Kendradi": kendradi_bala, "Drekkana": drekkana_bala, "dist": dist
        }

    def calc_dig_bala(self, p_name, p_lon):
        asc_sign = int(self.asc_lon / 30.0) + 1
        def get_house_sign_1_idx(h): return (asc_sign + h - 2) % 12 + 1

        zero_h = {"Sun": 4, "Moon": 10, "Mars": 4, "Mercury": 7, "Jupiter": 7, "Venus": 10, "Saturn": 1}
        z_sign = get_house_sign_1_idx(zero_h[p_name])
        zero_lon = (z_sign - 1) * 30.0 + 15.0

        dist = min(abs(p_lon - zero_lon), 360.0 - abs(p_lon - zero_lon))
        return {"Total": dist / 3.0, "zero_h": zero_h[p_name], "zero_lon": zero_lon, "dist": dist}

    def get_csp_varsha_lord(self):
        """Calculates Varsha Lord based on Chaitra Shukla Pratipada (Luni-Solar Year)."""
        import swisseph as swe
        import math
        
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

        for i in range(380):
            jd_eval = self.cur_jd - i
            sun_pos, _ = swe.calc_ut(jd_eval, swe.SUN, flags)
            moon_pos, _ = swe.calc_ut(jd_eval, swe.MOON, flags)
            
            # Sun in Sidereal Pisces (330 to 360 degrees)
            if 330.0 <= sun_pos[0] < 360.0:
                tithi_deg = (360.0 + moon_pos[0] - sun_pos[0]) % 360.0
                # Shukla Pratipada (First 12 degrees after New Moon)
                if 0.0 <= tithi_deg < 12.0:
                    weekday_idx = int(math.floor(jd_eval + 1.5 + float(getattr(self.app, "current_lon", 77.2090))/360.0)) % 7
                    daylord_map = {0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 4: "Jupiter", 5: "Venus", 6: "Saturn"}
                    return daylord_map[weekday_idx]
        return "Sun" 

    def get_panchang_maasa_lord(self):
        """Calculates Maasa Lord based on the current lunar month's Shukla Pratipada."""
        import swisseph as swe
        import math
        
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

        for i in range(35):
            jd_eval = self.cur_jd - i
            sun_pos, _ = swe.calc_ut(jd_eval, swe.SUN, flags)
            moon_pos, _ = swe.calc_ut(jd_eval, swe.MOON, flags)
            
            tithi_deg = (360.0 + moon_pos[0] - sun_pos[0]) % 360.0
            # Shukla Pratipada of the current lunar month
            if 0.0 <= tithi_deg < 12.0:
                weekday_idx = int(math.floor(jd_eval + 1.5 + float(getattr(self.app, "current_lon", 77.2090))/360.0)) % 7
                daylord_map = {0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 4: "Jupiter", 5: "Venus", 6: "Saturn"}
                return daylord_map[weekday_idx]
        return "Sun"

    def calc_kala_bala(self, p_name, p_lon):
        import math
        
        # ---------------------------------------------------------
        # 1. Nathonnata Bal 
        # ---------------------------------------------------------
        lon_deg = float(getattr(self.app, "current_lon", 77.2090))
        lmt_hours = (self.cur_jd + 0.5 + lon_deg / 360.0) % 1.0 * 24.0
        
        unnata_hours = lmt_hours if lmt_hours <= 12.0 else 24.0 - lmt_hours
        unnata_ghatis = unnata_hours * 2.5
        nata_ghatis = 30.0 - unnata_ghatis

        if p_name in ["Moon", "Mars", "Saturn"]: 
            natonnata = nata_ghatis * 2.0
        elif p_name in ["Sun", "Jupiter", "Venus"]: 
            natonnata = 60.0 - (nata_ghatis * 2.0)
        else: 
            natonnata = 60.0

        # ---------------------------------------------------------
        # 2. Paksha Bal 
        # ---------------------------------------------------------
        moon_lon = getattr(self, "moon_lon", (self.sun_lon + (self.paksha_val * 3.0)) % 360.0)
        moon_sun_diff = (360.0 + moon_lon - self.sun_lon) % 360.0
        
        if moon_sun_diff > 180.0:
            moon_sun_diff = 360.0 - moon_sun_diff
            
        benefic_paksha = moon_sun_diff / 3.0
        malefic_paksha = 60.0 - benefic_paksha
        
        if p_name in ["Moon", "Mercury", "Jupiter", "Venus"]:
            paksha = benefic_paksha
        else:
            paksha = malefic_paksha

        # ---------------------------------------------------------
        # 3. Tribhaga Bal 
        # ---------------------------------------------------------
        sun2lagna_dist = (360.0 + self.asc_lon - self.sun_lon) % 360.0
        tribhaga = 0.0
        if p_name == "Jupiter": tribhaga = 60.0
        elif sun2lagna_dist <= 60.0 and p_name == "Mercury": tribhaga = 60.0
        elif 60.0 < sun2lagna_dist <= 120.0 and p_name == "Sun": tribhaga = 60.0
        elif 120.0 < sun2lagna_dist <= 180.0 and p_name == "Saturn": tribhaga = 60.0
        elif 180.0 < sun2lagna_dist <= 240.0 and p_name == "Moon": tribhaga = 60.0
        elif 240.0 < sun2lagna_dist <= 300.0 and p_name == "Venus": tribhaga = 60.0
        elif 300.0 < sun2lagna_dist <= 360.0 and p_name == "Mars": tribhaga = 60.0

        # ---------------------------------------------------------
        # 4. Varsha-Maas-Dina-Hora (VMDH) Bal - PANCHANG METHOD
        # ---------------------------------------------------------
        # Call the new helper methods for Year and Month lords
        varsha_lord = self.get_csp_varsha_lord()
        maasa_lord = self.get_panchang_maasa_lord()
        
        # Calculate current Gregorian weekday based on local time
        local_jd = self.cur_jd + (lon_deg / 360.0)
        gregorian_weekday_idx = int(math.floor(local_jd + 1.5)) % 7
        
        # In Panchang, the day does not change until Sunrise.
        # If sun2lagna_dist is roughly between 270 (midnight) and 359 (just before sunrise),
        # we are technically still on the previous Panchang day.
        if 270.0 <= sun2lagna_dist < 360.0:
            gregorian_weekday_idx = (gregorian_weekday_idx - 1) % 7

        daylord_map = {
            0: "Sun", 1: "Moon", 2: "Mars", 3: "Mercury", 
            4: "Jupiter", 5: "Venus", 6: "Saturn"
        }
        dina_lord = daylord_map[gregorian_weekday_idx]

        # Hora Ruler (skips by 6 weekdays / jumps +5 index spaces)
        hora_num = int(sun2lagna_dist // 15.0)
        weekday_names = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        dina_idx = weekday_names.index(dina_lord)
        
        hora_lord_idx = (dina_idx + (hora_num * 5)) % 7
        hora_lord = weekday_names[hora_lord_idx]

        vmdh_bala = 0.0
        if p_name == varsha_lord: vmdh_bala += 15.0
        if p_name == maasa_lord: vmdh_bala += 30.0
        if p_name == dina_lord: vmdh_bala += 45.0
        if p_name == hora_lord: vmdh_bala += 60.0

        # ---------------------------------------------------------
        # 5. Ayana Bal
        # ---------------------------------------------------------
        ayana_bala = self.ayana_balas.get(p_name, 0.0)

        return {
            "Total": natonnata + ayana_bala + paksha + tribhaga + vmdh_bala,
            "Natonnata": natonnata, "Ayana": ayana_bala, "Paksha": paksha, "Tribhaga": tribhaga, "VMDH": vmdh_bala,
            "Lords": f"Y({varsha_lord}), M({maasa_lord}), D({dina_lord}), H({hora_lord})"
        }

    def calc_cheshta_bala(self, p_name, p_data, p_lon):
        if p_name == "Sun": return {"Total": self.ayana_balas.get("Sun", 0.0), "Type": "Ayana Default", "Retro": None, "Gap": 0.0}
        if p_name == "Moon": return {"Total": self.paksha_val, "Type": "Paksha Default", "Retro": None, "Gap": 0.0}

        gap = min(abs(p_lon - self.sun_lon), 360.0 - abs(p_lon - self.sun_lon))
        gap_signs = int(gap // 30.0)
        gap_degrees = gap % 30.0

        is_retro = p_data.get("retro", False)
        if "is_retro" in p_data: is_retro = p_data["is_retro"]
        elif "speed" in p_data: is_retro = p_data.get("speed", 1.0) < 0.0

        if p_name in ["Mars", "Jupiter", "Saturn"]:
            kurma_pts = {"Jupiter": [7, 5, 3, 1, 2, 2, 0], "Saturn": [6, 5, 3, 1, 2, 3, 0], "Mars": [7, 6, 4, 2, 0, 1, 0]}
            pts = kurma_pts[p_name]
            sign_part = sum(pts[0:gap_signs]) * 3.0
            deg_part = (0.1 * gap_degrees) * pts[gap_signs]
            return {"Total": sign_part + deg_part, "Type": "Kurma Method", "Gap": gap, "Retro": is_retro}

        elif p_name in ["Venus", "Mercury"]:
            if p_name == "Venus":
                tot = (60.0 - (gap / 10.0)) if is_retro else (gap if gap <= 40.0 else 2.0 * gap - 41.0)
            else:
                tot = (60.0 - (gap / 2.0)) if is_retro else (2.0 * gap)
            return {"Total": max(0.0, tot), "Type": "Inner Planet Motional", "Retro": is_retro, "Gap": gap}
        return {"Total": 0.0, "Type": "Unknown", "Retro": None, "Gap": 0.0}

    def calc_jm_drik_bala(self, p_name, p_lon):
        benefics, malefics = ["Jupiter", "Venus"], ["Sun", "Mars", "Saturn"]
        if getattr(self, "is_waxing", True): benefics.append("Moon")
        else: malefics.append("Moon")

        if getattr(self, "is_merc_benefic", True): benefics.append("Mercury")
        else: malefics.append("Mercury")

        benefic_sputa, malefic_sputa = 0.0, 0.0
        breakdown = []

        for q in self.planets_list:
            q_name = q.get("name")
            if not q_name or q_name == p_name or q_name not in benefics + malefics: continue

            q_lon = float(q.get("lon", 0.0))
            degree = (p_lon - q_lon) % 360.0
            sputa = get_jm_sputadrishti(degree, q_name)
            
            if sputa > 0:
                if q_name in benefics:
                    benefic_sputa += sputa
                    breakdown.append(f"<span style='color:#059669'>+{sputa:.1f} (Benefic {q_name})</span>")
                if q_name in malefics:
                    malefic_sputa += sputa
                    breakdown.append(f"<span style='color:#DC2626'>-{sputa:.1f} (Malefic {q_name})</span>")

        return {"Total": (benefic_sputa - malefic_sputa) / 4.0, "Trace": breakdown}

    def calculate_all(self):
        self._setup_ascendant()

        self.sun_p = next((x for x in self.planets_list if x["name"] == "Sun"), {"lon": 0})
        self.moon_p = next((x for x in self.planets_list if x["name"] == "Moon"), {"lon": 0})
        self.sun_lon = float(self.sun_p.get("lon", 0.0))
        self.moon_lon = float(self.moon_p.get("lon", 0.0))

        sun_moon_gap = min(abs(self.moon_lon - self.sun_lon), 360.0 - abs(self.moon_lon - self.sun_lon))
        self.paksha_val = sun_moon_gap / 3.0
        self.phase_angle = (self.moon_lon - self.sun_lon) % 360.0
        self.is_waxing = self.phase_angle < 180.0
        
        merc_p = next((p for p in self.planets_list if p.get("name") == "Mercury"), None)
        self.is_merc_benefic = True
        if merc_p:
            merc_lon = float(merc_p.get("lon", 0.0))
            b_count, m_count = 0, 0
            for q in self.planets_list:
                q_n = q.get("name")
                if not q_n or q_n in ["Mercury", "Rahu", "Ketu"]: continue
                q_lon = float(q.get("lon", 0.0))
                conj_diff = min(abs(merc_lon - q_lon), 360.0 - abs(merc_lon - q_lon))
                if conj_diff <= 15.0:
                    if q_n in ["Sun", "Mars", "Saturn"]: m_count += 1
                    elif q_n in ["Jupiter", "Venus", "Moon"]: b_count += 1
            self.is_merc_benefic = (b_count >= m_count)

        self.ayana_balas = {}
        for p_name in self.valid_planets:
            p_data = next((p for p in self.planets_list if p.get("name") == p_name), None)
            if not p_data: continue
            p_lon = float(p_data.get("lon", 0.0))
            signno = int(p_lon / 30.0) + 1
            kranti = "North" if signno in [1, 2, 3, 4, 5, 6] else "South"
            sin_val = abs(math.sin(math.radians(p_lon)))
            if p_name in ["Moon", "Saturn"]: ay = 30.0 * (1.0 - sin_val) if kranti == "North" else 30.0 * (1.0 + sin_val)
            elif p_name in ["Sun", "Mars", "Jupiter", "Venus"]: ay = 30.0 * (1.0 - sin_val) if kranti == "South" else 30.0 * (1.0 + sin_val)
            else: ay = 30.0 * (1.0 + sin_val)
            self.ayana_balas[p_name] = ay

        # Calculate Ashtakavarga metrics & Shodhanas
        self.calc_ashtakavarga()

        pre_yuddha_results = {}
        for p_name in self.valid_planets:
            p_data = next((p for p in self.planets_list if p.get("name") == p_name), None)
            if not p_data: continue

            p_lon = float(p_data.get("lon", 0.0))

            sd = self.calc_sthana_bala(p_name, p_data, p_lon)
            dd = self.calc_dig_bala(p_name, p_lon)
            kd = self.calc_kala_bala(p_name, p_lon)
            cd = self.calc_cheshta_bala(p_name, p_data, p_lon)
            naisargika = NAISARGIKA_BALA.get(p_name, 0.0)
            drd = self.calc_jm_drik_bala(p_name, p_lon)

            total = sd["Total"] + dd["Total"] + kd["Total"] + cd["Total"] + naisargika + drd["Total"]
            pre_yuddha_results[p_name] = {
                "Sthana": sd, "Dig": dd, "Kala": kd, "Cheshta": cd, 
                "Naisargika": naisargika, "Drik": drd, "Total": total, 
                "sign": int(p_data.get("sign_num", int(p_lon / 30.0) + 1)), "lon": p_lon
            }

        # Jyotishmitra Yuddha Bala Adjustments
        yuddha_adjustments = {p: 0.0 for p in self.valid_planets}
        for i in range(len(self.valid_planets)):
            for j in range(i + 1, len(self.valid_planets)):
                p1 = self.valid_planets[i]
                p2 = self.valid_planets[j]
                if p1 not in pre_yuddha_results or p2 not in pre_yuddha_results: continue

                lon1 = pre_yuddha_results[p1]["lon"]
                lon2 = pre_yuddha_results[p2]["lon"]
                dist = min(abs(lon1 - lon2), 360.0 - abs(lon1 - lon2))

                if dist < 1.0:
                    gap = abs(pre_yuddha_results[p1]["Total"] - pre_yuddha_results[p2]["Total"])
                    if pre_yuddha_results[p1]["Total"] >= pre_yuddha_results[p2]["Total"]:
                        yuddha_adjustments[p1] += gap
                        yuddha_adjustments[p2] -= gap
                    else:
                        yuddha_adjustments[p2] += gap
                        yuddha_adjustments[p1] -= gap

        final_results = {}
        for p, res in pre_yuddha_results.items():
            res["Kala"]["Total"] += yuddha_adjustments[p]
            res["Kala"]["Yuddha"] = yuddha_adjustments[p]
            res["Total"] += yuddha_adjustments[p]

            final_results[p] = {
                "Sthana_Details": res["Sthana"], 
                "Dig_Details": res["Dig"], 
                "Kala_Details": res["Kala"],
                "Cheshta_Details": res["Cheshta"], 
                "Naisargika": res["Naisargika"], 
                "Drik_Details": res["Drik"],
                "Sthana": round(res["Sthana"]["Total"], 2),
                "Dig": round(res["Dig"]["Total"], 2),
                "Kala": round(res["Kala"]["Total"], 2),
                "Cheshta": round(res["Cheshta"]["Total"], 2),
                "Drik": round(res["Drik"]["Total"], 2),
                "Total": round(res["Total"], 2), 
                "Uchcha": round(res["Sthana"]["Uchcha"], 2),
                "sign": res["sign"],
                "Ashtakavarga": {
                    "BAV_Points": self.bav_points,
                    "SAV_Points": self.sav_points,
                    "Traces": self.bav_traces,
                    "Trikon": self.trikon_points,
                    "Ekadhipatya": self.ekadhipatya_points,
                    "Shodhya_Pinda": self.shodhya_pindas,
                    "asc_sign": int(self.asc_lon / 30.0) + 1
                }
            }

        return final_results

# ==============================================================================
# USER INTERFACE & DIALOGS
# ==============================================================================

class ShadbalaDetailsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window) 
        self.setWindowTitle("Shadbala and Ashtakavarga Analysis")
        self.resize(1200, 750)
        self.scrollers = []  
        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 4px; }
            QTabBar::tab { background: #E2E8F0; padding: 10px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; color: #0284C7; border-bottom: 2px solid #0284C7; }
            QTableWidget { font-size: 13px; background-color: white; border: 1px solid #CBD5E1; }
            QHeaderView::section { font-weight: bold; background-color: #E2E8F0; padding: 6px; border: 1px solid #CBD5E1; }
        """)
        
        main_layout = QVBoxLayout(self)
        info_lbl = QLabel(
            "Using same algorithm as laid in Jyotishmitra Open source Library.<br>"
            "<b>Whatever Yogas, or effects have been stated with respect to a Bhava, will come to pass through the strongest Grah </b>"
            "<br><span style='color: #059669;'><b>Hover your cursor over progress bars for breakdown of every calculation.</b></span>"
        )
        info_lbl.setStyleSheet("color: #334155; font-size: 13px; margin-bottom: 8px;")
        main_layout.addWidget(info_lbl)

        self.tabs = QTabWidget()
        self.shadbala_tab = QWidget()
        self.ashtakavarga_tab = QWidget()
        
        self.tabs.addTab(self.shadbala_tab, "1. Shadbala Breakdown")
        self.tabs.addTab(self.ashtakavarga_tab, "2. Ashtakavarga analysis")
        main_layout.addWidget(self.tabs)
        
        # --- Shadbala Tab ---
        sb_layout = QVBoxLayout(self.shadbala_tab)
        self.sb_table = CustomTooltipTable()
        self.apply_smooth_scroll(self.sb_table)
        
        cols = ["Planet", "Sthana", "Dig", "Kala", "Cheshta", "Naisargika", "Drik (Net)", "TOTAL SCORE", "Threshold", "Status"]
        self.sb_table.setColumnCount(len(cols))
        self.sb_table.setHorizontalHeaderLabels(cols)
        self.sb_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sb_table.verticalHeader().setVisible(False)
        sb_layout.addWidget(self.sb_table)
        
        # --- Ashtakavarga Tab ---
        av_layout = QVBoxLayout(self.ashtakavarga_tab)
        
        av_split = QHBoxLayout()
        
        # Left side: Table
        table_container = QVBoxLayout()
        t_lbl = QLabel("<b>Bhinna Ashtakavarga (BAV) and Sarva Ashtakvarga (SAV) Mappings</b>")
        t_lbl.setStyleSheet("color: #0284C7; font-size: 14px;")
        table_container.addWidget(t_lbl)
        
        self.av_table = CustomTooltipTable()
        self.apply_smooth_scroll(self.av_table)
        self.av_table.setColumnCount(13)
        # Note: BAV distributions deposit into Absolute Signs mapping (0=Aries, 1=Taurus...) not relative Ascendant houses!
        self.av_table.setHorizontalHeaderLabels(["Planet", "Ar (1)", "Ta (2)", "Ge (3)", "Cn (4)", "Le (5)", "Vi (6)", "Li (7)", "Sc (8)", "Sg (9)", "Cp (10)", "Aq (11)", "Pi (12)"])
        self.av_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.av_table.verticalHeader().setVisible(False)
        
        self.av_table.setItemDelegate(WeakRowDelegate(self.av_table))
        table_container.addWidget(self.av_table)
        
        av_split.addLayout(table_container, stretch=6)
        
        # Right side: Chart
        chart_container = QVBoxLayout()
        chart_lbl = QLabel("<b>Bindu Distribution</b>")
        chart_lbl.setMaximumHeight(20)
        chart_lbl.setStyleSheet("color: #0284C7; font-size: 14px;")
        chart_container.addWidget(chart_lbl)
        
        self.av_chart = AshtakavargaBarChart()
        chart_container.addWidget(self.av_chart)
        
        av_split.addLayout(chart_container, stretch=4)
        
        av_layout.addLayout(av_split)
        
        evidence_panel = QTextEdit()
        evidence_panel.setReadOnly(True)
        evidence_panel.setHtml("""
            <h3 style='color:#0284C7; margin-bottom: 2px;'>Ashtakavarga System</h3>
            <p style='font-size: 13px; color: #334155; margin-top: 2px;'>
            <b>Bhinna Ashtakavarga :</b> Individual points deposited in specific Signs.<br>
            <b>Sarva Ashtakvarga :</b> The net cumulative strength. > 28 is highly auspicious.<br>
            <b>Shodhya Pinda:</b> Trikon & Ekadhipatya Shodhana + Pinda Sadhana multipliers are also calculated.<br>
            <b>Transit Strength Overlay:</b>Planets transiting green bars (>= 28) yield highly favorable results.
            </p>
        """)
        evidence_panel.setMaximumHeight(105)
        av_layout.addWidget(evidence_panel)

        btn_close = QPushButton("Close Detailed Analysis")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("padding: 8px; font-weight: bold; background-color: #334155; color: white; border-radius: 4px;")
        main_layout.addWidget(btn_close)

    def apply_smooth_scroll(self, widget):
        """Attaches the main app's SmoothScroller to our widgets safely"""
        if SmoothScroller:
            scroller = SmoothScroller(widget)
            self.scrollers.append(scroller)

    def _create_bar(self, val, max_val, color_thresholds, tooltip=""):
        bar = HoverProgressBar(tooltip)
        bar.setMaximum(int(max_val))
        bar.setValue(min(int(max_val), int(abs(val))))
        bar.setFormat(f"{val:.1f}")
        bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        color = color_thresholds[-1][1] 
        for threshold, c in color_thresholds:
            if val >= threshold: 
                color = c; break 
            
        bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }} QProgressBar {{ border: 1px solid #bdc3c7; border-radius: 2px; text-align: center; font-weight: bold; color: black; }}")
        return bar

    def refresh_data(self, shadbala_data):
        if not shadbala_data: return
        self.sb_table.setRowCount(0); self.sb_table.setRowCount(len(shadbala_data))
        sorted_data = sorted(shadbala_data.items(), key=lambda x: x[1]['Total'] / REQUIRED_SHADBALA.get(x[0], 300), reverse=True)
        
        for row, (p_name, scores) in enumerate(sorted_data):
            lord = astro_engine.SIGN_RULERS.get(scores.get('sign', 1), '')
            p_item = QTableWidgetItem(f"{p_name}\n({lord})")
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sb_table.setItem(row, 0, p_item)
            
            sd = scores['Sthana_Details']
            sthana_tt = (
                f"<div style='min-width: 250px;'>"
                f"<h3 style='margin:0; color:#0284C7;'>Sthana Bala (Positional)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                f"<b>Uchcha:</b> <span style='color:#D97706;'>{sd['Uchcha']:.2f}</span> <i>(Dist: {sd.get('dist',0):.1f}°)</i><br>"
                f"<b>Saptavargaja:</b> <span style='color:#D97706;'>{sd['Saptavargaja']:.2f}</span> <i>(Roots in D1-D30)</i><br>"
                f"<b>Ojhayugma:</b> <span style='color:#D97706;'>{sd['Ojhayugma']:.2f}</span> <i>(Odd/Even in D1 & D9)</i><br>"
                f"<b>Kendradi:</b> <span style='color:#D97706;'>{sd['Kendradi']:.2f}</span> <i>(60 Kendra, 30 Pana, 15 Apok)</i><br>"
                f"<b>Drekkana:</b> <span style='color:#D97706;'>{sd['Drekkana']:.2f}</span>"
                f"</div>"
            )
            self.sb_table.setCellWidget(row, 1, self._create_bar(scores["Sthana"], 300, [(150, "#10B981"), (100, "#F59E0B"), (0, "#EF4444")], sthana_tt))
            
            dd = scores['Dig_Details']
            dig_tt = (
                f"<div style='min-width: 200px;'>"
                f"<h3 style='margin:0; color:#0284C7;'>Dig Bala (Directional)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                f"<b>Zero Point:</b> House {dd.get('zero_h',0)} ({dd.get('zero_lon',0):.1f}°)<br>"
                f"<b>Distance:</b> {dd.get('dist',0):.1f}°"
                f"</div>"
            )
            self.sb_table.setCellWidget(row, 2, self._create_bar(scores["Dig"], 60, [(30, "#10B981"), (15, "#F59E0B"), (0, "#EF4444")], dig_tt))
            
            kd = scores['Kala_Details']
            kala_tt = (
                f"<div style='min-width: 250px;'>"
                f"<h3 style='margin:0; color:#0284C7;'>Kala Bala (Temporal)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                f"<b>Natonnata:</b> <span style='color:#D97706;'>{kd.get('Natonnata', 0):.2f}</span><br>"
                f"<b>Ayana:</b> <span style='color:#D97706;'>{kd.get('Ayana', 0):.2f}</span><br>"
                f"<b>Paksha:</b> <span style='color:#D97706;'>{kd.get('Paksha', 0):.2f}</span><br>"
                f"<b>Tribhaga:</b> <span style='color:#D97706;'>{kd.get('Tribhaga', 0):.2f}</span><br>"
                f"<b>VMDH:</b> <span style='color:#D97706;'>{kd.get('VMDH', 0):.2f}</span> <i>(Lords: {kd.get('Lords')})</i><br>"
                f"<b>Yuddha Adj:</b> <span style='color:#D97706;'>{kd.get('Yuddha', 0.0):.2f}</span>"
                f"</div>"
            )
            self.sb_table.setCellWidget(row, 3, self._create_bar(scores["Kala"], 300, [(150, "#10B981"), (75, "#F59E0B"), (0, "#EF4444")], kala_tt))
            
            cd = scores['Cheshta_Details']
            retro_status = "<span style='color:#DC2626;'>Yes</span>" if cd.get('Retro') else "<span style='color:#059669;'>No</span>" if cd.get('Retro') is False else "<span style='color:#64748B;'>N/A</span>"
            cheshta_tt = (
                f"<div style='min-width: 250px;'>"
                f"<h3 style='margin:0; color:#0284C7;'>Cheshta Bala (Motional)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                f"<b>Type:</b> <span style='color:#D97706;'>{cd.get('Type', '')}</span><br>"
                f"<b>Retrograde:</b> {retro_status}<br>"
                f"<b>Gap to Sun:</b> {cd.get('Gap', 0):.1f}°"
                f"</div>"
            )
            self.sb_table.setCellWidget(row, 4, self._create_bar(scores["Cheshta"], 60, [(30, "#10B981"), (15, "#F59E0B"), (0, "#EF4444")], cheshta_tt))
            
            nais_tt = f"<div style='min-width: 250px;'><h3 style='margin:0; color:#0284C7;'>Naisargika Bala</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>Natural strength of the planets (Fixed).</div>"
            self.sb_table.setCellWidget(row, 5, self._create_bar(scores["Naisargika"], 60, [(0, "#3B82F6")], nais_tt))
            
            d_trace = "<br>".join(scores["Drik_Details"].get("Trace", ["None"]))
            drik_tt = f"<div style='min-width: 200px;'><h3 style='margin:0; color:#0284C7;'>Drik Bala Aspects</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>{d_trace}</div>"
            
            drik_item = QTableWidgetItem(f"{scores['Drik']:+.1f}")
            drik_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            drik_item.setData(Qt.ItemDataRole.UserRole, drik_tt)
            d_color = QColor("#10B981") if scores['Drik'] >= 0 else QColor("#EF4444")
            drik_item.setForeground(d_color)
            drik_item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            self.sb_table.setItem(row, 6, drik_item)
            
            req_thresh = REQUIRED_SHADBALA.get(p_name, 300)
            tot_tt = f"<div style='min-width: 200px;'><h3 style='margin:0; color:#0284C7;'>Total Shadbala</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>Sum of all 6 components.<br>Required: {req_thresh}</div>"
            self.sb_table.setCellWidget(row, 7, self._create_bar(scores["Total"], max(600, scores["Total"]), [(req_thresh, "#10B981"), (0, "#EF4444")], tot_tt))
            
            thresh_item = QTableWidgetItem(f"{req_thresh:.0f}"); thresh_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sb_table.setItem(row, 8, thresh_item)
            
            is_strong = scores["Total"] >= req_thresh
            status_lbl = QLabel("STRONG 🟢" if is_strong else "WEAK ⚠️")
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_lbl.setStyleSheet(f"font-weight: bold; color: {'#10B981' if is_strong else '#EF4444'};")
            self.sb_table.setCellWidget(row, 9, status_lbl)
            self.sb_table.setRowHeight(row, 45)

        # --- Populating Ashtakavarga Tab ---
        sample_p = list(shadbala_data.keys())[0]
        av_data = shadbala_data[sample_p]["Ashtakavarga"]
        bav_points, sav_points, traces = av_data["BAV_Points"], av_data["SAV_Points"], av_data["Traces"]
        
        bav_entities = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Ascendant"]
        self.av_table.setRowCount(len(bav_entities) + 1)
        
        def get_tinted_color(base_hex, is_weak):
            """Washes the base color with a faint red tint if the planet is weak."""
            if not is_weak: return QColor(base_hex)
            base = QColor(base_hex)
            tint = QColor("#FECACA") # Tailwind Red-200
            return QColor(
                int(base.red() * 0.7 + tint.red() * 0.3),
                int(base.green() * 0.7 + tint.green() * 0.3),
                int(base.blue() * 0.7 + tint.blue() * 0.3)
            )
        
        sign_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        for r, p_name in enumerate(bav_entities):
            hdr_text = f"{p_name}" if p_name != "Ascendant" else "Asc"
            hdr = QTableWidgetItem(hdr_text)
            
            is_weak_planet = False
            
            # Saptbal/Shadbala Color Hint & Tooltip + Shodhya Pinda Display
            if p_name in shadbala_data:
                sb_total = shadbala_data[p_name]["Total"]
                req = REQUIRED_SHADBALA.get(p_name, 300)
                is_strong = sb_total >= req
                is_weak_planet = not is_strong
                
                bg_color = QColor("#D1FAE5") if is_strong else QColor("#FEE2E2") 
                text_color = QColor("#065F46") if is_strong else QColor("#991B1B")
                
                hdr.setBackground(bg_color)
                hdr.setForeground(text_color)
                hdr.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                
                pinda_val = av_data.get("Shodhya_Pinda", {}).get(p_name, 0)
                tt = (
                    f"<div style='min-width: 200px;'>"
                    f"<h3 style='margin:0; color:{'#059669' if is_strong else '#DC2626'};'>{p_name} Strength (ShadBal)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                    f"<b>Shadbala Score:</b> {sb_total:.1f} Virupas<br>"
                    f"<b>Required Score:</b> {req} Virupas<br>"
                    f"<b>Status:</b> {'Strong 🟢' if is_strong else 'Weak ⚠️'}<br><br>"
                    f"<b>Shodhya Pinda:</b> <span style='font-size: 14px; font-weight: bold;'>{pinda_val}</span>"
                    f"</div>"
                )
                hdr.setData(Qt.ItemDataRole.UserRole, tt)
            else:
                hdr.setBackground(QColor("#E2E8F0"))
                hdr.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                pinda_val = av_data.get("Shodhya_Pinda", {}).get("Ascendant", 0)
                tt = f"<div style='min-width: 150px;'><h3 style='margin:0; color:#0284C7;'>Ascendant</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>Lagna Bindus<br><br><b>Shodhya Pinda:</b> <span style='font-size: 14px; font-weight: bold;'>{pinda_val}</span></div>"
                hdr.setData(Qt.ItemDataRole.UserRole, tt)
                
            hdr.setData(Qt.ItemDataRole.UserRole + 1, is_weak_planet)
            self.av_table.setItem(r, 0, hdr)
            
            for c in range(12):
                pts = bav_points.get(p_name, [0]*12)[c]
                trace_list = traces.get(p_name, {}).get(c, [])
                trace_html = "<br>".join([f"• {t}" for t in trace_list]) if trace_list else "No bindus."
                
                tt = (
                    f"<div style='min-width: 250px;'>"
                    f"<h3 style='margin:0; color:#0284C7;'>{p_name} Bindus in {sign_names[c]}</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                    f"<b>Breakdown:</b><br>{trace_html}"
                    f"</div>"
                )
                
                item = QTableWidgetItem(str(pts))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setData(Qt.ItemDataRole.UserRole, tt)
                item.setData(Qt.ItemDataRole.UserRole + 1, is_weak_planet)
                
                base_hex = "#FFFFFF"
                if pts >= 5: 
                    base_hex = "#D1FAE5" 
                elif pts == 0: 
                    base_hex = "#FCA5A5" 
                
                item.setBackground(get_tinted_color(base_hex, is_weak_planet))
                    
                self.av_table.setItem(r, c+1, item)

        sav_hdr = QTableWidgetItem("Total")
        sav_hdr.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)); sav_hdr.setBackground(QColor("#475569")); sav_hdr.setForeground(Qt.GlobalColor.white)
        self.av_table.setItem(len(bav_entities), 0, sav_hdr)
        
        for c in range(12):
            s_pts = sav_points[c]
            item = QTableWidgetItem(str(s_pts))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter); item.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            tt = (
                f"<div style='min-width: 250px;'><h3 style='margin:0; color:#D97706;'>Sarvashtakavarga ({sign_names[c]})</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                f"<b>Total:</b> <span style='color:#059669; font-weight:bold;'>{s_pts}</span> points<br>"
                f"<i>(Note: Sums of only the 7 primary planets (and not asc).</i>"
                f"</div>"
            )
            item.setData(Qt.ItemDataRole.UserRole, tt)
            if s_pts >= 30: item.setBackground(QColor("#BAE6FD"))
            elif s_pts < 25: item.setBackground(QColor("#F1F5F9"))
            self.av_table.setItem(len(bav_entities), c+1, item)
            
        asc_sign = av_data.get("asc_sign", 1)
        planet_houses = {i: [] for i in range(12)}
        valid_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        
        for p_name in valid_planets:
            if p_name in shadbala_data:
                p_sign = shadbala_data[p_name]["sign"]
                h_idx = (p_sign - 1) % 12  # Mapped absolutely to sign index 0-11
                planet_houses[h_idx].append(p_name)
                
        self.av_chart.update_data(sav_points, planet_houses)


# ==============================================================================
# MAIN INTEGRATION HOOK
# ==============================================================================
import __main__
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import QTimer

info_print = getattr(__main__, 'info_print', print)
error_print = getattr(__main__, 'error_print', print)


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
        group_layout.setContentsMargins(6, 6, 6,6)
        group_layout.setSpacing(1)
        shared_group.setLayout(group_layout)
        layout.addWidget(shared_group)
        
    target_layout = shared_group.layout()
    
    status_label = QLabel("Shadbala, Ashtakvarga, Ishta/Kasht bala, Bhava/Upa pads, and argala analysis.")
    status_label.setWordWrap(True)
    status_label.setStyleSheet("color: #555; font-size: 11px;")
    status_label.setContentsMargins(2, 2, 2, 2) 
    target_layout.addWidget(status_label)

    lbl_title = QLabel("Shadbala Analysis")
    lbl_title.setStyleSheet("color: #8e44ad; font-weight: bold; font-size: 15px; margin-top: 8px;")
    target_layout.addWidget(lbl_title)
    
    lbl_name = "shadbala_leaderboard_lbl_active"
    btn_name = "shadbala_btn_details_active"
    
    leaderboard_lbl = QLabel("<i>Calculating initial rankings...</i>")
    leaderboard_lbl.setObjectName(lbl_name)
    leaderboard_lbl.setStyleSheet("background-color: #fdfefe; border: 1px solid #dcdde1; border-radius: 4px; padding: 6px; font-family: monospace;")
    leaderboard_lbl.setWordWrap(True)
    target_layout.addWidget(leaderboard_lbl)
    
    btn_details = QPushButton("Shadbala and Ashtakavarga")
    btn_details.setObjectName(btn_name)
    btn_details.setStyleSheet("""
        QPushButton { background-color: #34495e; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }
        QPushButton:hover { background-color: #0d5c91; }
        QPushButton:disabled { background-color: #bdc3c7; color: #7f8c8d; }
    """)
    btn_details.setEnabled(False)
    target_layout.addWidget(btn_details)
    
    app._shadbala_results = {}
    
    current_ui_id = id(leaderboard_lbl)
    app._shadbala_active_ui_id = current_ui_id
    
    retry_timer = QTimer()
    retry_timer.setSingleShot(True)
    app._shadbala_retry_timer = retry_timer 
    
    def run_computation():
        
        if getattr(app, '_shadbala_active_ui_id', None) != current_ui_id:
            return

        current_shared_group = app.findChild(QGroupBox, shared_group_id)
        if not current_shared_group:
            error_print("Shadbala: Layout not mounted yet. Retrying in 1s...")
            retry_timer.start(1000)
            return
            
        active_lbl = current_shared_group.findChild(QLabel, lbl_name)
        active_btn = current_shared_group.findChild(QPushButton, btn_name)
        
        if not active_lbl or not active_btn:
            error_print("Shadbala: Labels missing from tree. Retrying in 1s...")
            retry_timer.start(1000)
            return

        if not hasattr(app, 'current_base_chart') or not app.current_base_chart or not app.current_base_chart.get("planets"):
            active_lbl.setText("<i>Waiting for astrological engine to spin up...</i>")
            retry_timer.start(1000)
            return
        required_vargas = ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]
        varga_charts = {"D1": app.current_base_chart}
        
        for v in required_vargas[1:]:
            v_chart = app.ephemeris.compute_divisional_chart(app.current_base_chart, v)
            varga_charts[v] = v_chart if v_chart else {"planets": []}

        calculator = ShadbalaCalculator(app.current_base_chart, varga_charts, app)
        results = calculator.calculate_all()
        
        if not results:
            active_lbl.setText("<i>Calculation yielded empty data, recalculating...</i>")
            error_print("Shadbala: Calculation yielded empty data. Retrying in 1s...")
            retry_timer.start(1000)
            return
        app._shadbala_results = results
        
        sorted_planets = sorted(results.items(), key=lambda x: x[1]['Total'] / REQUIRED_SHADBALA.get(x[0], 300), reverse=True)
        leader_txt = "<b>Shadbala Rankings:</b><br>"
        for i, (p, data) in enumerate(sorted_planets, start=1):
            req = REQUIRED_SHADBALA.get(p, 300)
            icon = "🟢" if data['Total'] >= req else "⚠️"
            leader_txt += f"{i}. <b>{p}</b> - {data['Total']:.1f} / {req:.0f} req. {icon}<br>"
            
        active_lbl.setText(leader_txt)
        active_btn.setEnabled(True)
        
        if hasattr(app, '_shadbala_dialog') and getattr(app._shadbala_dialog, 'isVisible', lambda: False)():
            app._shadbala_dialog.refresh_data(results)

    retry_timer.timeout.connect(run_computation)

    def auto_trigger(*args, **kwargs):
        if getattr(app, '_shadbala_active_ui_id', None) == current_ui_id:
            retry_timer.start(0)

    if hasattr(app, 'calc_worker'):
        app.calc_worker.calc_finished.connect(auto_trigger)

    def show_details():
        if hasattr(app, '_shadbala_results') and app._shadbala_results:
            if not hasattr(app, '_shadbala_dialog'):
                app._shadbala_dialog = ShadbalaDetailsDialog(app)
            app._shadbala_dialog.refresh_data(app._shadbala_results)
            app._shadbala_dialog.showMaximized() 
            app._shadbala_dialog.raise_()

    btn_details.clicked.connect(show_details)
    
    auto_trigger()