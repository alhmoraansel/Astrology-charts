#chart_renderer.py

import math, time, animation

from PyQt6.QtWidgets import QWidget, QLabel, QSizePolicy
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygonF, QPixmap,QRadialGradient, QPainterPath, QLinearGradient
from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF

import astro_engine

# ==========================================
# GLOBAL SETTINGS FOR CHART RENDERING
# ==========================================
GLOBAL_FONT_SCALE_MULTIPLIER = 1.0
GLOBAL_UI_FONT_FAMILY = "Segoe UI"
GLOBAL_CHART_FONT_FAMILY = "Arial"
GLOBAL_RASHI_FONT_FAMILY = "Arial"
GLOBAL_EMOJI_FONT_FAMILY = "Segoe UI Emoji"
GLOBAL_TOOLTIP_ASTERISK_SIZE = 18  # Global size for tooltips
GLOBAL_CANVAS_ASTERISK_SCALE = 2.2 # Global multiplier for canvas drawing
GLOBAL_DEGREE_FONT_MULTIPLIER = 1.1 # Global multiplier for degree font size
DEGREE_AFTER_SYMBOLS = True # Draw degrees after retrograde/combust/exalted symbols
DEGREE_FONT_BOLD = True # Draw degrees in bold font
USE_BETTER_LAYOUT = True # Shift crowded planets to prevent overlap or clipping
GLOBAL_KARAKAMSHA_THICKNESS = 5.5  # Controls the thickness of the D1 Karakamsha highlight boundary
GLOBAL_SHOW_KARAKAMSHA_HIGHLIGHT = True  # Extracted boolean to control visibility




# ==========================================
# ASTROLOGICAL REFERENCE DICTIONARIES
# ==========================================
ZODIAC_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
ZODIAC_ELEMENTS = ["🔥 Fire", "🌍 Earth", "💭 Air", "💧 Water"] * 3
ZODIAC_NATURES = ["Movable", "Fixed", "Dual"] * 4
ZODIAC_EMOJIS = {1: '🔥', 2: '🌍', 3: '💭', 4: '💧', 5: '🔥', 6: '🌍', 7: '💭', 8: '💧', 9: '🔥', 10: '🌍', 11: '💭', 12: '💧'}

SIGN_LORDS = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}

PLANET_FRIENDS = {
    "Sun": ["Moon", "Mars", "Jupiter"], "Moon": ["Sun", "Mercury"], 
    "Mars": ["Sun", "Moon", "Jupiter"], "Mercury": ["Sun", "Venus"], 
    "Jupiter": ["Sun", "Moon", "Mars"], "Venus": ["Mercury", "Saturn"], 
    "Saturn": ["Mercury", "Venus"], "Rahu": ["Mercury", "Venus", "Saturn"], 
    "Ketu": ["Mercury", "Venus", "Saturn"]
}

PLANET_ENEMIES = {
    "Sun": ["Venus", "Saturn"], "Moon": [], "Mars": ["Mercury"], 
    "Mercury": ["Moon"], "Jupiter": ["Mercury", "Venus"], 
    "Venus": ["Sun", "Moon"], "Saturn": ["Sun", "Moon", "Mars"], 
    "Rahu": ["Sun", "Moon", "Mars"], "Ketu": ["Sun", "Moon", "Mars"]
}

NATURAL_BENEFICS = {"Moon", "Mercury", "Jupiter", "Venus"}
NATURAL_MALEFICS = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}

DIV_THEME_MAP = {
    "D2": 2, "D3": 3, "D4": 4, "D5": 5, "D6": 6, 
    "D7": 5, "D8": 8, "D9": 7, "D10": 10, "D11": 11, 
    "D12": 9, "D16": 4, "D20": 9, "D24": 4, "D27": 3, 
    "D30": 6, "D40": 4, "D45": 9, "D60": 1
}
NATURE_COLORS = {'Movable': '#e67e22', 'Fixed': '#2980b9', 'Dual': '#8e44ad'}
PLANET_LANE_ORDER = {"Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3, "Jupiter": 4, "Venus": 5, "Saturn": 6, "Rahu": 7, "Ketu": 8, "Ascendant": 9}

UNICODE_SYMS = {"Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿", "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", "Rahu": "☊", "Ketu": "☋"}

BRIGHT_COLORS = {
    "Sun": QColor("#FF8C00"), "Moon": QColor("#00BCD4"), "Mars": QColor("#FF0000"), 
    "Mercury": QColor("#00C853"), "Jupiter": QColor("#FFD700"), "Venus": QColor("#FF1493"), 
    "Saturn": QColor("#0000CD"), "Rahu": QColor("#708090"), "Ketu": QColor("#8B4513"), 
    "Ascendant": QColor("#C0392B")
}

DARK_COLORS = {
    "Sun": QColor("#CC5500"), "Moon": QColor("#007A8C"), "Mars": QColor("#AA0000"), 
    "Mercury": QColor("#008033"), "Jupiter": QColor("#A68A00"), "Venus": QColor("#B30066"), 
    "Saturn": QColor("#000080"), "Rahu": QColor("#444444"), "Ketu": QColor("#5C3A21"), 
    "Ascendant": QColor("#8B0000")
}

KENDRA_HOUSES = {4, 7, 10}
TRINE_HOUSES = {1, 5, 9}
DUSTHANA_HOUSES = {6, 8, 12}
UPACHAYA_MALEFIC_HOUSES = {3, 11}

def get_ordinal(n):
    if 11 <= (n % 100) <= 13: return str(n) + 'th'
    return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


# ==========================================
# CHART ANALYZER (Plugin API Helper)
# ==========================================

class ChartAnalyzer:
    """
    Helper API to access planetary statuses safely and cleanly.
    Intended for use in Dynamic Plugins to easily query chart information.
    Supports dynamic accessors like: analyzer.is_saturn_debilitated(), analyzer.is_moon_exalted()
    """
    def __init__(self, chart_data):
        self.chart_data = chart_data
        self.planets = {p["name"]: p for p in chart_data.get("planets", [])}
        self.ascendant = chart_data.get("ascendant", {})

    def __getattr__(self, name):
        # Magic method allowing properties like `is_saturn_debilitated()` dynamically
        if name.startswith("is_"):
            parts = name[3:].split("_")
            if len(parts) >= 2:
                planet_name = parts[0].capitalize()
                status = "_".join(parts[1:])
                
                if planet_name in self.planets:
                    if status == "debilitated": return self.is_debilitated(planet_name)
                    if status == "exalted": return self.is_exalted(planet_name)
                    if status == "retrograde": return self.is_retrograde(planet_name)
                    if status == "combust": return self.is_combust(planet_name)
                    if status == "vargottama": return self.is_vargottama(planet_name)
                    if status == "own_sign": return self.is_own_sign(planet_name)
                    
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    # ==========================================
    # Core Accessors
    # ==========================================
    def get_planet(self, name): return self.planets.get(name, {})
    def get_all_planets(self): return list(self.planets.values())
    
    # ==========================================
    # Status Checks
    # ==========================================
    def is_exalted(self, name): return self.get_planet(name).get("exalted", False)
    def is_debilitated(self, name): return self.get_planet(name).get("debilitated", False)
    def is_own_sign(self, name): return self.get_planet(name).get("own_sign", False)
    def is_retrograde(self, name): return self.get_planet(name).get("retro", False)
    def is_combust(self, name): return self.get_planet(name).get("combust", False)
    def is_vargottama(self, name): return self.get_planet(name).get("vargottama", False)
    
    def is_benefic(self, name): return name in NATURAL_BENEFICS
    def is_malefic(self, name): return name in NATURAL_MALEFICS
    
    # ==========================================
    # Aggregates & Counts
    # ==========================================
    def num_deb_planets(self): return sum(1 for p in self.planets.values() if p.get("debilitated"))
    def num_exalted_planets(self): return sum(1 for p in self.planets.values() if p.get("exalted"))
    def num_retro_planets(self): return sum(1 for p in self.planets.values() if p.get("retro") and p["name"] not in ["Rahu", "Ketu"])
    
    # ==========================================
    # Structural Accessors
    # ==========================================
    def get_house_of(self, name): return self.get_planet(name).get("house", -1)
    def get_sign_of(self, name): return self.get_planet(name).get("sign_num", -1)
    
    def get_lord_of_house(self, house_num):
        asc_sign_idx = self.ascendant.get("sign_index", 0)
        sign_num = (asc_sign_idx + house_num - 1) % 12 + 1
        ruler_name = SIGN_LORDS.get(sign_num)
        return self.get_planet(ruler_name) if ruler_name else {}

    def get_occupants(self, house_num): 
        return [p for p in self.planets.values() if p.get("house") == house_num]
        
    def get_aspecting_planets(self, house_num): 
        return [asp["aspecting_planet"] for asp in self.chart_data.get("aspects", []) if asp["target_house"] == house_num]

    def get_dispositor(self, name):
        """Returns the planet object ruling the sign the given planet is placed in."""
        sign_num = self.get_sign_of(name)
        ruler = SIGN_LORDS.get(sign_num)
        return self.get_planet(ruler) if ruler else {}
        
    def get_conjunct_planets(self, name):
        """Returns a list of planet names that share the same sign as the given planet."""
        sign_num = self.get_sign_of(name)
        return [p["name"] for p in self.planets.values() if p.get("sign_num") == sign_num and p["name"] != name]
        
    def get_atmakaraka(self):
        """Returns the name of the Atmakaraka (highest degree planet)."""
        for p in self.planets.values():
            if p.get("is_ak"): return p["name"]
        return None
        
    def get_kendra_planets(self): return [p["name"] for p in self.planets.values() if p.get("house") in KENDRA_HOUSES]
    def get_trine_planets(self): return [p["name"] for p in self.planets.values() if p.get("house") in TRINE_HOUSES]
    def get_dusthana_planets(self): return [p["name"] for p in self.planets.values() if p.get("house") in DUSTHANA_HOUSES]
    def get_upachaya_planets(self): return [p["name"] for p in self.planets.values() if p.get("house") in UPACHAYA_MALEFIC_HOUSES]

    # ==========================================
    # Standard Planet Nakshatra Accessors
    # ==========================================
    def get_nakshatra(self, name): 
        """Returns the nakshatra name of the given planet (e.g. 'Pushya')."""
        return self.get_planet(name).get("nakshatra")

    def get_nakshatra_lord(self, name): 
        """Returns the planet name ruling the nakshatra the given planet is placed in."""
        return self.get_planet(name).get("nakshatra_lord")

    def get_nakshatra_pada(self, name): 
        """Returns the nakshatra pada (1-4) of the given planet."""
        return self.get_planet(name).get("nakshatra_pada")

    # ==========================================
    # House Lord Nakshatra Accessors
    # ==========================================
    def get_house_lord_nakshatra(self, house_num):
        """Returns the nakshatra name of the planet ruling the given house."""
        lord = self.get_lord_of_house(house_num)
        return lord.get("nakshatra") if lord else None

    def get_house_lord_nakshatra_lord(self, house_num):
        """Returns the planet name ruling the nakshatra of the given house lord."""
        lord = self.get_lord_of_house(house_num)
        return lord.get("nakshatra_lord") if lord else None

    def get_house_lord_nakshatra_pada(self, house_num):
        """Returns the nakshatra pada (1-4) of the given house lord."""
        lord = self.get_lord_of_house(house_num)
        return lord.get("nakshatra_pada") if lord else None

    # ==========================================
    # Ascendant Nakshatra Accessors
    # ==========================================
    def get_ascendant_nakshatra(self):
        """Returns the nakshatra of the Ascendant degree."""
        return self.ascendant.get("nakshatra")

    def get_ascendant_nakshatra_lord(self):
        """Returns the planet name ruling the Ascendant's nakshatra."""
        return self.ascendant.get("nakshatra_lord")

    def get_ascendant_nakshatra_pada(self):
        """Returns the pada of the Ascendant's nakshatra."""
        return self.ascendant.get("nakshatra_pada")

    # ==========================================
    # Advanced Nakshatra Astrology Helpers
    # ==========================================
    def get_planets_in_nakshatra(self, nakshatra_name):
        """Returns a list of planet names currently placed in the specified nakshatra."""
        return [p["name"] for p in self.planets.values() if p.get("nakshatra") == nakshatra_name]

    def get_planets_in_nakshatra_ruled_by(self, lord_name):
        """Returns a list of planet names placed in ANY nakshatra ruled by the given planet."""
        return [p["name"] for p in self.planets.values() if p.get("nakshatra_lord") == lord_name]

    def get_nakshatra_dispositor(self, planet_name):
        """Returns the planet object of the given planet's Nakshatra Lord (Stellar Dispositor)."""
        nak_lord_name = self.get_nakshatra_lord(planet_name)
        return self.get_planet(nak_lord_name) if nak_lord_name else {}
        
    def is_in_own_nakshatra(self, planet_name):
        """Checks if a planet is placed in its own nakshatra (e.g., Moon in Rohini)."""
        return self.get_nakshatra_lord(planet_name) == planet_name
        
    def get_nakshatra_exchanges(self):
        """
        Finds pairs of planets that have exchanged nakshatras (Nakshatra Parivartana Yoga).
        Returns a list of tuples, e.g., [("Sun", "Moon")] if Sun is in Moon's star and Moon is in Sun's star.
        """
        exchanges = []
        p_names = list(self.planets.keys())
        for i, p1 in enumerate(p_names):
            for p2 in p_names[i+1:]:
                if self.get_nakshatra_lord(p1) == p2 and self.get_nakshatra_lord(p2) == p1:
                    exchanges.append((p1, p2))
        return exchanges


# ==========================================
# CORE RENDERER CLASS
# ==========================================
class ChartRenderer(QWidget):
    def toggle_karakamsha(self, is_checked: bool):
        """Connect your UI checkbox to this method to toggle the sacred stroke."""
        self.show_karakamsha = is_checked
        self.update()
    SHOW_TOOLTIPS = True

    def __init__(self):
        super().__init__()
        self.show_karakamsha = GLOBAL_SHOW_KARAKAMSHA_HIGHLIGHT
        
        # --- Widget Configuration ---
        self.setMinimumSize(100, 100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        
        # --- State Initialization ---
        self.title = ""
        self.d1_data = None
        self.outline_mode = "Vitality (Lords)"
        self.rotated_asc_sign_idx = None
        self.hitboxes = []
        self.house_polys = {}
        self.chart_data = None
        self.houses_info = {}
        
        # --- Display Flags ---
        self.use_symbols = False
        self.show_rahu_ketu = True
        self.highlight_asc_moon = True
        self.show_aspects = False
        self.show_arrows = True
        self.use_tint = True
        self.use_circular = False
        self.visible_aspect_planets = set()
        
        # --- Tooltip Configuration ---
        self.tooltip_label = QLabel(self)
        self.tooltip_label.setWindowFlags(
            Qt.WindowType.ToolTip | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        font_size = int(13 * GLOBAL_FONT_SCALE_MULTIPLIER)
        self.tooltip_label.setStyleSheet(
            f"QLabel {{ background-color: #FDFDFD; color: #222222; border: 1px solid #BBBBBB; padding: 6px; font-size: {font_size}px; }}"
        )
        self.tooltip_label.hide()
        
        # --- Animation State ---
        self.anim_timer = QTimer(self)
        # --- Ambient Animation Timer (for breathing effects) ---
        self.ambient_timer = QTimer(self)
        self.ambient_timer.timeout.connect(self.update)
        # 30-40ms is about 25-30 FPS, perfect for a smooth, slow breath without draining CPU
        self.ambient_timer.start(65)
        self.anim_timer.timeout.connect(self._on_anim_tick)
        self.anim_duration = 600.0
        self.anim_start_time = 0
        self.source_layout = None
        self.target_layout = None
        self.current_layout = None
        self.data_changed_flag = False

    def set_tooltips_status(self, status):
        """Toggles the global display of tooltips."""
        self.SHOW_TOOLTIPS = status
        if not self.SHOW_TOOLTIPS and hasattr(self, 'tooltip_label') and self.tooltip_label.isVisible():
            self.tooltip_label.hide()

    def _compute_house_metadata(self):
        """Computes presentation layer metadata (Regime, Pressure, Vitality) entirely internally."""
        self.houses_info = {}
        if not self.chart_data: return
        
        aspect_counts = {h: 0 for h in range(1, 13)}
        for asp in self.chart_data.get("aspects", []):
            aspect_counts[asp["target_house"]] += 1

        disp_map = {}
        p_house = {}
        for p in self.chart_data["planets"]:
            if p["name"] not in ["Rahu", "Ketu"]:
                ruler = SIGN_LORDS.get(p["sign_num"])
                if ruler: disp_map[p["name"]] = ruler
            p_house[p["name"]] = p["house"]

        regime_terminals = set()
        for p_name in disp_map:
            visited = []
            curr = p_name
            while curr not in visited and curr:
                visited.append(curr)
                curr = disp_map.get(curr)
            if curr:
                idx = visited.index(curr)
                for tp in visited[idx:]:
                    if tp in p_house: regime_terminals.add(p_house[tp])

        projection_hubs = set()
        convergence_hubs = set()
        for h_num in range(1, 13):
            outward = {asp["target_house"] for asp in self.chart_data.get("aspects", []) if asp["source_house"] == h_num}
            if len(outward) >= 3: projection_hubs.add(h_num)
            
            influences = {p["name"] for p in self.chart_data["planets"] if p["house"] == h_num}
            influences.update({asp["aspecting_planet"] for asp in self.chart_data.get("aspects", []) if asp["target_house"] == h_num})
            if len(influences) >= 4: convergence_hubs.add(h_num)

        asc_sign_idx = self.chart_data["ascendant"]["sign_index"]
        for h_num in range(1, 13):
            sign_num = (asc_sign_idx + h_num - 1) % 12 + 1
            
            # 1. Analyze aspects on this house to determine Font colors
            h_ben_aspects = 0
            h_mal_aspects = 0
            for asp in self.chart_data.get("aspects", []):
                if asp["target_house"] == h_num and asp["aspecting_planet"] != "Ketu":
                    asp_p = asp["aspecting_planet"]
                    asp_p_sign = next((p["sign_index"] for p in self.chart_data["planets"] if p["name"] == asp_p), -1)
                    is_ben, _ = self._get_nature_and_color(asp_p, asp_p_sign)
                    if is_ben: h_ben_aspects += 1
                    else: h_mal_aspects += 1
                    
            malefic_dominant = h_mal_aspects > h_ben_aspects
            
            # 2. Vitality (Lords) evaluation
            v_color, v_width, v_vitality = "#BDC3C7", 1.0, "Background Scenery (Neutral)"
            lord_p = next((p for p in self.chart_data["planets"] if p["name"] == SIGN_LORDS.get(sign_num)), None)
            if lord_p:
                is_strong = lord_p.get("exalted", False) or lord_p.get("own_sign", False)
                in_dusthana = lord_p.get("house", 1) in [6, 8, 12]
                in_kendra_trikona = lord_p.get("house", 1) in [1, 4, 5, 7, 9, 10]
                if is_strong and not in_dusthana and not lord_p.get("combust", False):
                    v_color, v_width, v_vitality = "#27ae60", 3.5, "Life Engine (Powerful Lord)"
                elif is_strong and in_dusthana:
                    v_color, v_width, v_vitality = "#e67e22", 3.5, "Plot Twist (Strong Lord in Dusthana)"
                elif lord_p.get("debilitated", False) and in_kendra_trikona:
                    v_color, v_width, v_vitality = "#e67e22", 3.5, "Plot Twist (Debilitated Lord in Kendra/Trine)"
                elif (lord_p.get("debilitated", False) and not in_kendra_trikona) or lord_p.get("combust", False):
                    v_color, v_width, v_vitality = "#c0392b", 3.5, "Friction Zone (Compromised Lord)"
                    
            # 3. Pressure (Aspects) evaluation
            p_count = aspect_counts[h_num]
            if p_count >= 4:
                p_color = "#c0392b" if malefic_dominant else "#b8860b"
                p_width, p_label = 3.5, f"Overloaded ({p_count} influences)"
            elif p_count == 3:
                p_color = "#c0392b" if malefic_dominant else "#f1c40f"
                p_width, p_label = 3.0, f"Strong ({p_count} influences)"
            elif p_count == 2:
                p_color, p_width, p_label = "#2980b9", 2.5, f"Moderately Active ({p_count} influences)"
            else:
                p_color, p_width, p_label = "#BDC3C7", 1.0, f"Quiet ({p_count} influences)"

            # 4. Regime Forces formatting
            r_colors, r_labels_html = [], []
            if h_num in regime_terminals:
                r_colors.append("#DC143C")
                r_labels_html.append("<span style='color:#DC143C'>Energy Disposition Terminal</span>")
            if h_num in projection_hubs:
                r_colors.append("#005FFF")
                r_labels_html.append("<span style='color:#005FFF'>Aspect Projection Hub</span>")
            if h_num in convergence_hubs:
                r_col = "#c0392b" if malefic_dominant else "#b8860b"
                r_colors.append(r_col)
                r_labels_html.append(f"<span style='color:{r_col}'><b>Theme Convergence</b></span>")

            # Export ready-to-inject data mappings
            self.houses_info[h_num] = {
                "vitality_color": v_color, "vitality_width": v_width, "vitality_label": v_vitality,
                "pressure_color": p_color, "pressure_width": p_width, "pressure_label": p_label,
                "pressure_count": p_count, "regime_colors": r_colors, "regime_labels_html": r_labels_html
            }

    def _get_dynamic_functional_nature(self, p_name, base_lords, base_asc_idx, current_asc_idx):
        """Calculates the functional benefic/malefic nature of a planet."""
        if p_name in ["Rahu", "Ketu"]: 
            return "#7f8c8d", "Neutral", "Node"
            
        if not base_lords: 
            return "#7f8c8d", "Neutral", "None"
            
        visual_lords = [((base_asc_idx + l - 1 - current_asc_idx) % 12) + 1 for l in base_lords]
        lords_str = "&".join([str(l) for l in sorted(visual_lords)])
        
        has_kendra = any(h in KENDRA_HOUSES for h in visual_lords)
        has_trine = any(h in TRINE_HOUSES for h in visual_lords)
        has_malefic = any(h in DUSTHANA_HOUSES for h in visual_lords)
        has_upachaya = any(h in UPACHAYA_MALEFIC_HOUSES for h in visual_lords)
        
        if has_kendra and has_trine:
            return "#FFD700", "Yogakaraka", f"L{lords_str}"
        elif has_trine:
            return "#27ae60", "Functional Benefic (trine)", f"L{lords_str}"
        elif has_upachaya:
            if has_malefic:
                return "#c0392b", "Functional Malefic (upachaya)", f"L{lords_str}"
            else:
                return "#f1c40f", "Mixed", f"L{lords_str}"
        elif has_malefic:
            return "#c0392b", "Malefic", f"L{lords_str}"
        elif has_kendra:
            return "#000000", "Neutral (kendra)", f"L{lords_str}"
            
        return "#7f8c8d", "Neutral", f"L{lords_str}"

    def _get_nature_and_color(self, p_name, sign_idx):
        """Returns (is_benefic, hex_color) adjusting Mercury's natural status dynamically."""
        if p_name in NATURAL_MALEFICS:
            return False, '#c0392b' # Malefic -> Red
        elif p_name == "Mercury":
            is_malefic = any(p["name"] in NATURAL_MALEFICS for p in self.chart_data["planets"] if p["sign_index"] == sign_idx and p["name"] != "Mercury")
            if is_malefic:
                return False, '#c0392b' # Malefic -> Red
            return True, '#27ae60' # Benefic -> Green
        elif p_name in NATURAL_BENEFICS:
            return True, '#27ae60' # Benefic -> Green
        return True, '#000000'

    def _get_house_polygon(self, h_num, x, y, w, h):
        """Generates the QPolygonF for the Vedic Diamond Chart houses."""
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
    
    def update_chart(self, data, d1_data=None):
        """Triggered from outside to inject new chart data."""
        self.chart_data = data
        self.d1_data = d1_data
        self._compute_house_metadata()
        self.rotated_asc_sign_idx = None
        self.data_changed_flag = True

        current_time = time.time() * 1000
        time_since_last = current_time - getattr(self, 'last_update_time', current_time)
        self.last_update_time = current_time
        
        if 0 < time_since_last < 1000:
            self.instant_snap = False
            self.anim_duration = time_since_last
            self.use_linear_easing = True
        else:
            self.instant_snap = False
            self.anim_duration = 600.0
            self.use_linear_easing = False
            
        self.update()  
    
    def _on_anim_tick(self):
        elapsed = (time.time() * 1000) - self.anim_start_time
        if self.anim_duration <= 0:
            self.anim_duration = 1.0 
            
        t = elapsed / self.anim_duration
        
        if t >= 1.0:
            t = 1.0 
            if self.anim_timer.isActive():
                self.anim_timer.stop() 
            self.current_layout = self.target_layout 
        else:
            self.current_layout = self._lerp_layout(self.source_layout, self.target_layout, t)
            
        self.update()
    
    def _lerp_layout(self, src, tgt, t):
        if getattr(self, 'use_linear_easing', False):
            e = t 
        else:
            e = 1 - (1 - t)**2
            
        def lerp(a, b):
            return a + (b - a) * e
        
        cur = {"zodiacs": {}, "houses": {}, "planets": {}, "tints": []}

        for cat in ["zodiacs", "houses", "planets"]:
            for k, t_v in tgt[cat].items():
                s_v = src[cat].get(k, t_v)
                cur[cat][k] = t_v.copy() 
                cur[cat][k]["x"] = lerp(s_v["x"], t_v["x"])
                cur[cat][k]["y"] = lerp(s_v["y"], t_v["y"])
                if cat == "planets":
                    cur[cat][k]["scale"] = lerp(s_v.get("scale", 1.0), t_v.get("scale", 1.0))

        tgt_tints = list(tgt.get("tints", []))
        for s_tint in src.get("tints", []):
            c = QColor(s_tint["color"])
            match = -1
            for i, t_t in enumerate(tgt_tints):
                if s_tint["h2"] == t_t["h2"] and c.rgb() == t_t["color"].rgb():
                    match = i
                    break
            
            if match != -1:
                c.setAlpha(int(lerp(c.alpha(), tgt_tints[match]["color"].alpha())))
                tgt_tints.pop(match)
            else:
                c.setAlpha(int(c.alpha() * (1.0 - e)))
            
            cur["tints"].append({"h2": s_tint["h2"], "color": c})
            
        for t_tint in tgt_tints:
            c = QColor(t_tint["color"])
            c.setAlpha(int(c.alpha() * e))
            cur["tints"].append({"h2": t_tint["h2"], "color": c})
            
        return cur

    def _compute_layout(self, x, y, w, h):
        layout = {"zodiacs": {}, "planets": {}, "houses": {}, "tints": []}
        if not self.chart_data: return layout
        
        base_asc_sign_idx = self.chart_data["ascendant"]["sign_index"]
        
        if getattr(self, 'rotated_asc_sign_idx', None) is not None:
            asc_sign_idx = self.rotated_asc_sign_idx
            asc_deg_effective = asc_sign_idx * 30.0 + 15.0
        else:
            asc_sign_idx = base_asc_sign_idx
            asc_deg_effective = self.chart_data["ascendant"].get("div_lon", self.chart_data["ascendant"]["degree"])
            
        all_bodies = []
        is_divisional = self.title and not (self.title == "D1" or self.title.startswith("D1 "))
        
        if self.highlight_asc_moon: 
            is_vargottama = self.chart_data["ascendant"].get("vargottama", False)
            asc_str = "Asc★" if is_vargottama and is_divisional else "Asc"
            all_bodies.append({
                "name": "Ascendant", 
                "str": asc_str, 
                "color_dark": DARK_COLORS.get("Ascendant", QColor("#000000")), 
                "lon": asc_deg_effective, 
                "retro": False, "exalted": False, "debilitated": False, "combust": False, 
                "obliterated": False,
                "raw": {
                    "name": "Ascendant", 
                    "sign_index": base_asc_sign_idx, 
                    "deg_in_sign": self.chart_data["ascendant"]["degree"] % 30, 
                    "retro": False, "combust": False, "obliterated": False, "house": 1, 
                    "vargottama": is_vargottama
                }
            })
            
        sun_p = next((p for p in self.chart_data["planets"] if p["name"] == "Sun"), None)
        sun_raw_lon = sun_p["lon"] if sun_p else None

        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"] and not self.show_rahu_ketu: 
                continue
                
            p_str = UNICODE_SYMS[p["name"]] if self.use_symbols else p["sym"]
            if p.get("vargottama", False) and is_divisional:
                p_str += "★"
                
            raw_copy = dict(p)
            
            # --- Dynamic Combust & Obliterated Logic based on True Longitude ---
            if sun_raw_lon is not None and p["name"] not in ["Sun", "Rahu", "Ketu"]:
                p_raw_lon = p["lon"]
                diff = min((p_raw_lon - sun_raw_lon) % 360, (sun_raw_lon - p_raw_lon) % 360)
                is_retro = p.get("retro", False)
                
                is_combust = False
                is_obliterated = False
                
                if diff <= 1.0:
                    is_obliterated = True
                    is_combust = True
                else:
                    name = p["name"]
                    if name == "Moon" and diff <= 12.0: is_combust = True
                    elif name == "Mars" and diff <= 17.0: is_combust = True
                    elif name == "Mercury" and ((is_retro and diff <= 12.0) or (not is_retro and diff <= 14.0)): is_combust = True
                    elif name == "Jupiter" and diff <= 11.0: is_combust = True
                    elif name == "Venus" and ((is_retro and diff <= 8.0) or (not is_retro and diff <= 10.0)): is_combust = True
                    elif name == "Saturn" and diff <= 15.0: is_combust = True
                
                raw_copy["combust"] = is_combust
                raw_copy["obliterated"] = is_obliterated

            all_bodies.append({
                "name": p["name"], 
                "str": p_str, 
                "color_dark": DARK_COLORS.get(p["name"], QColor("#000000")), 
                "lon": p.get("div_lon", p["lon"]), 
                "retro": p["retro"], 
                "exalted": p.get("exalted", False), 
                "debilitated": p.get("debilitated", False), 
                "combust": raw_copy.get("combust", False), 
                "obliterated": raw_copy.get("obliterated", False),
                "raw": raw_copy
            })

        bodies_by_house = {i: [] for i in range(1, 13)}
        for b in all_bodies: 
            visual_h_num = ((b["raw"]["sign_index"] - asc_sign_idx) % 12) + 1
            bodies_by_house[visual_h_num].append(b)

        for visual_h_num in range(1, 13):
            sign_idx = (asc_sign_idx + visual_h_num - 1) % 12
            sign_num = sign_idx + 1
            sign_lon = sign_idx * 30.0 + 15.0
            original_h_num = ((sign_idx - base_asc_sign_idx) % 12) + 1
            
            if getattr(self, "use_circular", False): 
                zx, zy = animation.get_circular_coords(sign_lon, asc_deg_effective, -3, w, h)
                hx, hy = animation.get_circular_coords(sign_lon, asc_deg_effective, -4, w, h)
            else: 
                has_bodies = len(bodies_by_house[visual_h_num]) > 0
                zx, zy = animation.get_diamond_zodiac_coords(visual_h_num, w, h, has_bodies)
                hx, hy = animation.get_diamond_house_center(visual_h_num, w, h)
                
            info = getattr(self, "houses_info", {}).get(original_h_num, {})
            
            if self.outline_mode == "Pressure (Aspects)":
                o_col = info.get("pressure_color", "#BDC3C7")
                o_wid = info.get("pressure_width", 1.0)
                r_cols = []
            elif self.outline_mode == "Regime (Forces)":
                o_col = "#BDC3C7"
                o_wid = 1.0
                r_cols = info.get("regime_colors", [])
            elif self.outline_mode == "Vitality (Lords)":
                o_col = info.get("vitality_color", "#BDC3C7")
                o_wid = info.get("vitality_width", 1.0)
                r_cols = []
            else:
                o_col = "#BDC3C7"
                o_wid = 1.0
                r_cols = []
                
            layout["houses"][visual_h_num] = {
                "x": hx + x, 
                "y": hy + y, 
                "outline_color": o_col, 
                "outline_width": o_wid, 
                "regime_colors": r_cols, 
                "original_h_num": original_h_num
            }
            
            elem_emoji = ZODIAC_EMOJIS[sign_num]
            layout["zodiacs"][sign_num] = {"x": zx + x, "y": zy + y, "val": f"{sign_num}{elem_emoji}"}

        for visual_h_num, bodies in bodies_by_house.items():
            num_b = len(bodies)
            if num_b <= 2:
                scale, spacing = 1.0, 0.08 * h
            elif num_b <= 4:
                scale, spacing = 0.85, 0.06 * h
            elif num_b <= 6:
                scale, spacing = 0.70, 0.045 * h
            else:
                scale, spacing = 0.55, 0.03 * h
                
            for idx, b in enumerate(bodies):
                if getattr(self, "use_circular", False): 
                    px, py = animation.get_circular_coords(b["lon"], asc_deg_effective, PLANET_LANE_ORDER.get(b["name"], 4.5), w, h)
                else: 
                    px, _ = animation.get_diamond_planet_coords(visual_h_num, idx, num_b, w, h)
                    py = animation.get_diamond_house_center(visual_h_num, w, h)[1] - ((num_b - 1) * spacing) / 2.0 + (idx * spacing)
                    
                    # --- NEW LAYOUT ADJUSTMENT: Prevent clipping and overlaps ---
                    if USE_BETTER_LAYOUT and num_b >= 1:
                        if visual_h_num in [3, 5]:
                            px -= w * 0.025
                        elif visual_h_num in [2, 6]:
                            px -= w * 0.035
                        elif visual_h_num in [8, 12]:
                            px -= w * 0.035
                        elif visual_h_num in [9, 11]:
                            px -= w * 0.035
                    
                layout["planets"][b["name"]] = {
                    "x": px + x, "y": py + y, "str": b["str"], 
                    "color_dark": b["color_dark"], "retro": b["retro"], 
                    "exalted": b["exalted"], "debilitated": b["debilitated"], 
                    "combust": b["combust"], "raw": b["raw"], "scale": scale
                }

        if self.show_aspects and self.use_tint and self.chart_data and self.chart_data.get("aspects"):
            for aspect in self.chart_data["aspects"]:
                is_node = aspect["aspecting_planet"] in ["Rahu", "Ketu"]
                if aspect["aspecting_planet"] in self.visible_aspect_planets and (not is_node or self.show_rahu_ketu):
                    c = QColor(BRIGHT_COLORS.get(aspect["aspecting_planet"], QColor(200, 200, 200)))
                    c.setAlpha(25)
                    target_visual_house = ((((base_asc_sign_idx + aspect["target_house"] - 1) % 12) - asc_sign_idx) % 12) + 1
                    layout["tints"].append({"h2": target_visual_house, "color": c})
                    
        return layout


    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            size = int(min(self.width(), self.height()) - 50)
            cx, cy = int(self.width() / 2), int(self.height() / 2)
            x, y, w, h = int(cx - size / 2), int(cy - size / 2 + 10), size, size
            
            layout_just_changed = False
            
            if getattr(self, '_last_layout_params', None) != (x, y, w, h) or self.data_changed_flag or getattr(self, 'target_layout', None) is None:
                new_target_layout = self._compute_layout(x, y, w, h)
                self._last_layout_params = (x, y, w, h)
                layout_just_changed = True
            else:
                new_target_layout = self.target_layout

            if self.data_changed_flag:
                self.data_changed_flag = False
                self.bg_cache = None 
                self._fg_cache = None # OPTIMIZATION: Invalidate foreground cache
                
                if getattr(self, 'instant_snap', False) or self.current_layout is None:
                    self.source_layout = self.target_layout = self.current_layout = new_target_layout
                    if self.anim_timer.isActive():
                        self.anim_timer.stop()
                else:
                    self.source_layout, self.target_layout = self.current_layout, new_target_layout
                    self.anim_start_time = time.time() * 1000
                    self.anim_timer.start(16)
            else:
                self.target_layout = new_target_layout
                if not self.anim_timer.isActive():
                    self.source_layout = self.current_layout = new_target_layout

            if not self.current_layout or not self.chart_data:
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Chart Data")
                return

            dpr = self.devicePixelRatioF()
            pixel_w = int(self.width() * dpr)
            pixel_h = int(self.height() * dpr)

            # ==========================================
            # 1. BACKGROUND CACHE (Static)
            # ==========================================
            if getattr(self, '_last_bg_size', None) != self.size() or not getattr(self, 'bg_cache', None):
                self._last_bg_size = self.size()
                self._fg_cache = None # Invalidate FG if BG resizes
                
                self.bg_cache = QPixmap(pixel_w, pixel_h)
                self.bg_cache.setDevicePixelRatio(dpr)
                self.bg_cache.fill(Qt.GlobalColor.white)
                
                bg_p = QPainter(self.bg_cache)
                try:
                    bg_p.setRenderHint(QPainter.RenderHint.Antialiasing)
                    
                    if self.title:
                        bg_p.setPen(QColor("#BBBBBB"))
                        calc_size = int(min(15, max(10, int(size * 0.035))) * GLOBAL_FONT_SCALE_MULTIPLIER)
                        bg_p.setFont(QFont(GLOBAL_UI_FONT_FAMILY, calc_size, QFont.Weight.Bold))
                        bg_p.drawText(QRectF(0, 0, self.width(), y - 10), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, self.title)

                    self.house_polys.clear()
                    for h_num in range(1, 13):
                        self.house_polys[h_num] = self._get_house_polygon(h_num, x, y, w, h)

                    if getattr(self, "use_circular", False):
                        outer_r, inner_r = (w - 40) / 2, w * 0.15
                        bg_p.setPen(QPen(QColor("#DAA520"), 2))
                        bg_p.drawEllipse(QPointF(cx, cy), outer_r + 4, outer_r + 4)
                        
                        bg_p.setPen(QPen(QColor("#8B4513"), 1.5))
                        bg_p.drawEllipse(QPointF(cx, cy), outer_r + 8, outer_r + 8)
                        
                        bg_p.setPen(QPen(QColor("#222222"), max(1.0, w * 0.005)))
                        bg_p.drawEllipse(QRectF(x + 20, y + 20, w - 40, h - 40))
                        bg_p.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))
                        
                        for i in range(12):
                            angle = math.radians(i * 30 + 15)
                            bg_p.drawLine(
                                int(cx + inner_r * math.cos(angle)), int(cy - inner_r * math.sin(angle)), 
                                int(cx + outer_r * math.cos(angle)), int(cy - outer_r * math.sin(angle))
                            )
                    else:
                        bg_p.setPen(QPen(QColor("#DAA520"), 2))
                        bg_p.drawRect(int(x - 4), int(y - 4), int(w + 8), int(h + 8))
                        
                        bg_p.setPen(QPen(QColor("#8B4513"), 1.5))
                        bg_p.drawRect(int(x - 8), int(y - 8), int(w + 16), int(h + 16))
                        
                        bg_p.setPen(Qt.PenStyle.NoPen)
                        bg_p.setBrush(QBrush(QColor("#8B4513")))
                        for px in [x - 8, x + w + 8]:
                            for py in [y - 8, y + h + 8]: 
                                bg_p.drawRect(int(px - 2), int(py - 2), 4, 4)
                                
                        bg_p.setBrush(Qt.BrushStyle.NoBrush)
                        bg_p.setPen(QPen(QColor("#222222"), max(1.0, w * 0.005)))
                        bg_p.drawRect(int(x), int(y), int(w), int(h))
                        
                        lines = [
                            (x, y, x + w, y + h), 
                            (x + w, y, x, y + h), 
                            (x + w/2, y, x + w, y + h/2), 
                            (x + w, y + h/2, x + w/2, y + h), 
                            (x + w/2, y + h, x, y + h/2), 
                            (x, y + h/2, x + w/2, y)
                        ]
                        for L in lines:
                            bg_p.drawLine(int(L[0]), int(L[1]), int(L[2]), int(L[3]))
                finally:
                    bg_p.end()

            # Instantly blit the base
            painter.drawPixmap(0, 0, self.bg_cache)

            # ==========================================
            # 2. KARAKAMSHA HIGHLIGHT (Dynamic Layer)
            # ==========================================
            is_d1_chart = self.title and (self.title == "D1" or self.title.startswith("D1 "))
            
            if getattr(self, "show_karakamsha", True) and is_d1_chart and getattr(self, "chart_data", None) and not getattr(self, "use_circular", False):
                ak_planet = next((p for p in self.chart_data.get("planets", []) if p.get("is_ak")), None)
                
                if ak_planet and "deg_in_sign" in ak_planet and "sign_index" in ak_planet:
                    ak_d9_sign = int(ak_planet["sign_index"] * 9 + ak_planet["deg_in_sign"] / (30.0 / 9.0)) % 12
                    asc_idx = self.rotated_asc_sign_idx if getattr(self, 'rotated_asc_sign_idx', None) is not None else self.chart_data["ascendant"]["sign_index"]
                    k_house = ((ak_d9_sign - asc_idx) % 12) + 1
                    
                    h_data = self.target_layout["houses"].get(k_house)
                    
                    if h_data and k_house in self.house_polys:
                        poly = self.house_polys[k_house]
                        
                        house_tints = [t["color"] for t in self.target_layout.get("tints", []) if t["h2"] == k_house]
                        if not house_tints:
                            glow_color = QColor(255, 215, 0) 
                        else:
                            bg_r, bg_g, bg_b = 255.0, 255.0, 255.0 
                            for tc in house_tints:
                                alpha = tc.alphaF()
                                bg_r = (tc.red() * alpha) + (bg_r * (1.0 - alpha))
                                bg_g = (tc.green() * alpha) + (bg_g * (1.0 - alpha))
                                bg_b = (tc.blue() * alpha) + (bg_b * (1.0 - alpha))
                            
                            bg_color = QColor(int(bg_r), int(bg_g), int(bg_b))
                            bg_h, bg_s, _, _ = bg_color.getHsv()
                            comp_h = 180 if (bg_h == -1 or bg_s < 15) else (bg_h + 180) % 360
                            glow_color = QColor.fromHsv(comp_h, 120, 255) 
                            
                        cache_key = (k_house, self.width(), self.height(), x, y, w, h, glow_color.rgb(), getattr(self, "outline_mode", ""), dpr)
                        if getattr(self, '_k_cache_key', None) != cache_key:
                            self._k_cache_key = cache_key
                            self._k_seeds = [(abs(math.sin(i * 37.1)), abs(math.cos(i * 91.3))) for i in range(24)]
                            self._k_glow_pix = QPixmap(pixel_w, pixel_h)
                            self._k_glow_pix.setDevicePixelRatio(dpr)
                            self._k_glow_pix.fill(Qt.GlobalColor.transparent)
                            
                            p_cache = QPainter(self._k_glow_pix)
                            p_cache.setRenderHint(QPainter.RenderHint.Antialiasing)
                            
                            p_cache.save()
                            clip_path = QPainterPath()
                            clip_path.addPolygon(poly)
                            p_cache.setClipPath(clip_path)
                            
                            radial_grad = QRadialGradient(QPointF(h_data["x"], h_data["y"]), w * 0.18)
                            radial_grad.setColorAt(0.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 180))
                            radial_grad.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
                            p_cache.setPen(Qt.PenStyle.NoPen)
                            p_cache.setBrush(QBrush(radial_grad))
                            p_cache.drawPolygon(poly)
                            p_cache.restore()
                            
                            def get_inset_poly(offset):
                                pts = []
                                for pt in poly:
                                    dx = h_data["x"] - pt.x()
                                    dy = h_data["y"] - pt.y()
                                    dist = max(1, math.hypot(dx, dy))
                                    pts.append(QPointF(pt.x() + (dx / dist) * offset, pt.y() + (dy / dist) * offset))
                                return QPolygonF(pts)

                            dynamic_inset = (max(1.0, w * 0.005) / 2.0)
                            if self.outline_mode == "Regime (Forces)" and h_data.get("regime_colors", []):
                                dynamic_inset += 4.25 + ((len(h_data["regime_colors"]) - 1) * 3.5) + 3.0
                            elif self.outline_mode != "Regime (Forces)" and h_data.get("outline_width", 1.0) > 1.05:
                                dynamic_inset += 4.25 + 3.0
                            else:
                                dynamic_inset += 5.0

                            inset_poly = get_inset_poly(dynamic_inset)
                            p_cache.setBrush(Qt.BrushStyle.NoBrush)
                            
                            glow_widths = [15.0, 10.0, 5.0, 2.0] 
                            for width_mult in glow_widths:
                                blur_thickness = max(width_mult, w * (width_mult / 1000.0))
                                p_cache.setPen(QPen(QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 100), blur_thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                                p_cache.drawPolygon(inset_poly)
                                
                            p_cache.setPen(QPen(QColor(255, 255, 255, 255), max(1.5, w * 0.0025), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.MiterJoin))
                            p_cache.drawPolygon(inset_poly)
                            p_cache.end()
                            
                        # OPTIMIZATION: Stripped math/object creation out of the stardust loop
                        current_time = time.time()
                        breath = (math.sin(current_time * 2.0) + 1.0) / 2.0
                        
                        painter.save()
                        pulse_opacity = 0.5 + (breath * 0.5) 
                        painter.setOpacity(pulse_opacity)
                        painter.drawPixmap(0, 0, self._k_glow_pix)
                        painter.restore()
                        
                        painter.save()
                        clip_path = QPainterPath()
                        clip_path.addPolygon(poly)
                        painter.setClipPath(clip_path)
                        painter.setPen(Qt.PenStyle.NoPen)
                        
                        rect = poly.boundingRect()
                        r_bottom, r_left = rect.bottom(), rect.left()
                        r_width, r_height = rect.width(), rect.height()
                        
                        # Cache particle color object once to avoid recreation
                        particle_color = QColor(255, 255, 255)
                        base_p_size = w * 0.0035
                        min_p_size = max(2.0, base_p_size)
                        sway_mult = w * 0.012

                        for i in range(24):
                            seed1, seed2 = self._k_seeds[i]
                            y_offset = ((current_time * (14 + seed1 * 20)) + (i * 45.2)) % r_height
                            x = r_left + (seed1 * r_width) + (math.sin(current_time * (0.8 + seed2 * 1.5) + i) * sway_mult)
                            
                            p_opacity = int(130 + (((math.sin(current_time * 4 + i) + 1) / 2.0) * 125))
                            particle_color.setAlpha(p_opacity)
                            
                            painter.setBrush(particle_color)
                            p_size = min_p_size + (seed2 * base_p_size)
                            painter.drawEllipse(QPointF(x, r_bottom - y_offset), p_size, p_size)

                        painter.restore() 

            # ==========================================
            # 3. FOREGROUND CACHE (Static Text & Layouts)
            # ==========================================
            is_animating = self.anim_timer.isActive()
            
            # OPTIMIZATION: Generate FG cache only if layout stopped moving or data changed
            if layout_just_changed or is_animating or not getattr(self, '_fg_cache', None):
                
                # If we are animating, draw straight to the main painter (it's moving).
                # If static, draw to the cache once.
                if not is_animating:
                    self._fg_cache = QPixmap(pixel_w, pixel_h)
                    self._fg_cache.setDevicePixelRatio(dpr)
                    self._fg_cache.fill(Qt.GlobalColor.transparent)
                    active_painter = QPainter(self._fg_cache)
                    active_painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                    self.hitboxes.clear() # Only clear hitboxes when making a new static layout
                else:
                    active_painter = painter
                
                # --- Begin Heavy FG Drawing ---
                for tint in self.current_layout["tints"]:
                    if not getattr(self, "use_circular", False) and tint["h2"] in self.house_polys:
                        active_painter.setBrush(QBrush(tint["color"]))
                        active_painter.setPen(Qt.PenStyle.NoPen)
                        active_painter.drawPolygon(self.house_polys[tint["h2"]])
                
                active_painter.setBrush(Qt.BrushStyle.NoBrush)
                if not getattr(self, "use_circular", False):
                    for h_num in range(1, 13):
                        h_data = self.current_layout["houses"].get(h_num)
                        if not h_data: continue
                            
                        if self.outline_mode == "Regime (Forces)" and h_data.get("regime_colors", []):
                            for i, col_hex in enumerate(h_data["regime_colors"]):
                                c = QColor(col_hex)
                                c.setAlpha(230)
                                inset_dist = (max(1.0, w * 0.005) / 2.0) + 4.25 + (i * 3.5)
                                
                                pts = []
                                for pt in self.house_polys[h_num]:
                                    dx = h_data["x"] - pt.x()
                                    dy = h_data["y"] - pt.y()
                                    dist = max(1, math.hypot(dx, dy))
                                    pts.append(QPointF(pt.x() + (dx / dist) * inset_dist, pt.y() + (dy / dist) * inset_dist))
                                    
                                active_painter.setPen(QPen(c, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                                active_painter.drawPolygon(QPolygonF(pts))
                                
                        elif self.outline_mode != "Regime (Forces)" and h_data.get("outline_width", 1.0) > 1.05:
                            c = QColor(h_data["outline_color"])
                            c.setAlpha(220)
                            inset_dist = (max(1.0, w * 0.005) / 2.0) + 4.25
                            
                            pts = []
                            for pt in self.house_polys[h_num]:
                                dx = h_data["x"] - pt.x()
                                dy = h_data["y"] - pt.y()
                                dist = max(1, math.hypot(dx, dy))
                                pts.append(QPointF(pt.x() + (dx / dist) * inset_dist, pt.y() + (dy / dist) * inset_dist))
                                
                            active_painter.setPen(QPen(c, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
                            active_painter.drawPolygon(QPolygonF(pts))

                z_font = QFont(GLOBAL_RASHI_FONT_FAMILY, int(max(7, min(14, max(9, w * 0.035)) * 0.5) * GLOBAL_FONT_SCALE_MULTIPLIER))
                active_painter.setFont(z_font)
                active_painter.setPen(QColor("#000000"))
                
                for z in self.current_layout["zodiacs"].values():
                    active_painter.drawText(QRectF(z["x"] - 15, z["y"] - 15, 30, 30), Qt.AlignmentFlag.AlignCenter, z["val"])

                p_base_font_size = min(14, max(9, int(w * 0.035))) * GLOBAL_FONT_SCALE_MULTIPLIER * 1.15
                marker_base_fs = max(4, min(9, max(6, int(w * 0.022))))
                
                # Pre-instantiate objects outside loop
                ak_brush = QBrush(QColor(255, 215, 0, 90))
                color_exalted = QColor("#27ae60")
                color_debilitated = QColor("#c0392b")
                
                for b in self.current_layout["planets"].values():
                    scale = b.get("scale", 1.0)
                    
                    if b["raw"].get("is_ak"):
                        active_painter.setPen(Qt.PenStyle.NoPen)
                        active_painter.setBrush(ak_brush)
                        active_painter.drawEllipse(QPointF(b["x"], b["y"] - 4 * scale), 22 * scale, 22 * scale)
                        
                    active_painter.setPen(b["color_dark"])
                    p_font = QFont(GLOBAL_CHART_FONT_FAMILY, int(p_base_font_size * scale), QFont.Weight.Bold)
                    active_painter.setFont(p_font)
                    p_rect = QRectF(b["x"] - 40 * scale, b["y"] - 10 * scale, 80 * scale, 20 * scale)
                    active_painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, b["str"])
                    
                    if not is_animating:
                        self.hitboxes.append((p_rect, b["raw"]))
                        
                    # OPTIMIZATION: Only calculate horizontalAdvance once per planet
                    font_adv = active_painter.fontMetrics().horizontalAdvance(b["str"])
                    marker_x = b["x"] + font_adv / 2.0 + 2 * scale
                    marker_y, marker_h = b["y"] - 10 * scale, 20 * scale
                    marker_fs = max(4, int(marker_base_fs * scale))
                    
                    draw_deg_block = False
                    deg_str = ""
                    deg_color = None
                    deg_fs = 5
                    
                    if is_d1_chart and "deg_in_sign" in b["raw"]:
                        draw_deg_block = True
                        deg_val = b["raw"]["deg_in_sign"]
                        deg_str = f"{int(deg_val)}°"
                        deg_fs = max(5, int(marker_fs * GLOBAL_DEGREE_FONT_MULTIPLIER)) 
                        
                        if deg_val < 6.0 or deg_val >= 24.0: deg_color = QColor("#777777")
                        elif deg_val < 12.0 or deg_val < 24.0: deg_color = QColor("#27ae60")
                        else: deg_color = QColor("#DAA520")
                        
                    if draw_deg_block and not DEGREE_AFTER_SYMBOLS:
                        deg_weight = QFont.Weight.Bold if DEGREE_FONT_BOLD else QFont.Weight.Normal
                        active_painter.setFont(QFont(GLOBAL_CHART_FONT_FAMILY, deg_fs, deg_weight))
                        active_painter.setPen(deg_color) 
                        active_painter.drawText(QRectF(marker_x, marker_y, 30 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, deg_str)
                        marker_x += active_painter.fontMetrics().horizontalAdvance(deg_str) + 2
                        
                    active_painter.setPen(b["color_dark"])
                    
                    if b["retro"]:
                        active_painter.setFont(QFont(GLOBAL_CHART_FONT_FAMILY, max(4, marker_fs - 1), QFont.Weight.Bold))
                        active_painter.drawText(QRectF(marker_x, marker_y - 5 * scale, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "R")
                        marker_x += active_painter.fontMetrics().horizontalAdvance("R") + 1
                        
                    if b.get("exalted"):
                        active_painter.setPen(color_exalted)
                        active_painter.setFont(QFont(GLOBAL_CHART_FONT_FAMILY, marker_fs, QFont.Weight.Bold))
                        active_painter.drawText(QRectF(marker_x, marker_y, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "▲")
                        marker_x += active_painter.fontMetrics().horizontalAdvance("▲") + 2
                    elif b.get("debilitated"):
                        active_painter.setPen(color_debilitated)
                        active_painter.setFont(QFont(GLOBAL_CHART_FONT_FAMILY, marker_fs, QFont.Weight.Bold))
                        active_painter.drawText(QRectF(marker_x, marker_y, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "▼")
                        marker_x += active_painter.fontMetrics().horizontalAdvance("▼") + 2
                        
                    if b.get("obliterated") or b.get("combust"):
                        active_painter.setFont(QFont(GLOBAL_EMOJI_FONT_FAMILY, marker_fs))
                        char = "☀" if b.get("obliterated") else "🔥"
                        active_painter.drawText(QRectF(marker_x, marker_y, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, char)
                        marker_x += active_painter.fontMetrics().horizontalAdvance(char) + 2

                    if b["raw"]["name"] != "Ascendant":
                        asc_sign_idx = self.rotated_asc_sign_idx if getattr(self, 'rotated_asc_sign_idx', None) is not None else self.chart_data["ascendant"]["sign_index"]
                        func_color, _, _ = self._get_dynamic_functional_nature(b["raw"]["name"], b["raw"].get("lord_of", []), self.chart_data["ascendant"]["sign_index"], asc_sign_idx)
                        if func_color and func_color != "#7f8c8d":
                            active_painter.setPen(QColor(func_color))
                            active_painter.setFont(QFont(GLOBAL_CHART_FONT_FAMILY, int(marker_fs * GLOBAL_CANVAS_ASTERISK_SCALE), QFont.Weight.Bold))
                            active_painter.drawText(QRectF(marker_x, marker_y + 2 * scale, 20 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, "*")
                            marker_x += active_painter.fontMetrics().horizontalAdvance("*") + 1
                            
                    if draw_deg_block and DEGREE_AFTER_SYMBOLS:
                        deg_weight = QFont.Weight.Bold if DEGREE_FONT_BOLD else QFont.Weight.Normal
                        active_painter.setFont(QFont(GLOBAL_CHART_FONT_FAMILY, deg_fs, deg_weight))
                        active_painter.setPen(deg_color) 
                        active_painter.drawText(QRectF(marker_x, marker_y, 30 * scale, marker_h), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, deg_str)
                        marker_x += active_painter.fontMetrics().horizontalAdvance(deg_str) + 2

                if self.show_aspects and self.show_arrows and self.chart_data and self.chart_data.get("aspects"):
                    asc_sign_idx = self.rotated_asc_sign_idx if getattr(self, 'rotated_asc_sign_idx', None) is not None else self.chart_data["ascendant"]["sign_index"]
                    
                    for i, aspect in enumerate(self.chart_data["aspects"]):
                        is_node = aspect["aspecting_planet"] in ["Rahu", "Ketu"]
                        if aspect["aspecting_planet"] in self.visible_aspect_planets and (not is_node or self.show_rahu_ketu):
                            target_h_visual = ((((self.chart_data["ascendant"]["sign_index"] + aspect["target_house"] - 1) % 12) - asc_sign_idx) % 12) + 1
                            p_v = self.current_layout["planets"].get(aspect["aspecting_planet"])
                            h_v = self.current_layout["houses"].get(target_h_visual)
                            
                            if p_v and h_v:
                                c = QColor(BRIGHT_COLORS.get(aspect["aspecting_planet"], QColor(100, 100, 100)))
                                c.setAlpha(150)
                                offset_x = (i % 3 - 1) * 4
                                offset_y = ((i + 1) % 3 - 1) * 4
                                x1, y1 = p_v["x"] + offset_x, p_v["y"] + offset_y
                                x2, y2 = h_v["x"] + offset_x, h_v["y"] + offset_y
                                
                                dist = math.hypot(x2 - x1, y2 - y1)
                                if dist >= 70:
                                    sx = x1 + ((x2 - x1) / dist) * 35
                                    sy = y1 + ((y2 - y1) / dist) * 35
                                    ex = x2 - ((x2 - x1) / dist) * 35
                                    ey = y2 - ((y2 - y1) / dist) * 35
                                    
                                    active_painter.setPen(QPen(c, max(1.5, w * 0.005), Qt.PenStyle.SolidLine))
                                    active_painter.drawLine(int(sx), int(sy), int(ex), int(ey))
                                    
                                    angle = math.atan2(ey - sy, ex - sx)
                                    active_painter.setBrush(QBrush(c))
                                    active_painter.setPen(Qt.PenStyle.NoPen)
                                    
                                    arrow_pts = [
                                        QPointF(ex, ey), 
                                        QPointF(ex - 9 * math.cos(angle - math.pi / 6), ey - 9 * math.sin(angle - math.pi / 6)), 
                                        QPointF(ex - 9 * math.cos(angle + math.pi / 6), ey - 9 * math.sin(angle + math.pi / 6))
                                    ]
                                    active_painter.drawPolygon(QPolygonF(arrow_pts))
                
                # --- End Heavy Drawing ---
                if not is_animating:
                    active_painter.end()

            # Blit the cached foreground text instantly if we are idling
            if not is_animating and getattr(self, '_fg_cache', None):
                painter.drawPixmap(0, 0, self._fg_cache)

        finally:
            painter.end()



    def mouseDoubleClickEvent(self, event):
        if not self.chart_data: return
        
        for h_num, poly in self.house_polys.items():
            if poly.containsPoint(event.position(), Qt.FillRule.OddEvenFill):
                curr_asc = self.rotated_asc_sign_idx if getattr(self, 'rotated_asc_sign_idx', None) is not None else self.chart_data["ascendant"]["sign_index"]
                target_asc = (curr_asc + h_num - 1) % 12
                
                if target_asc == curr_asc and curr_asc != self.chart_data["ascendant"]["sign_index"]:
                    self.rotated_asc_sign_idx = None
                else:
                    self.rotated_asc_sign_idx = target_asc
                
                self.instant_snap = False
                self.anim_duration = 350.0
                self.use_linear_easing = False
                self.data_changed_flag = True
                
                self.update()
                self.tooltip_label.hide()
                break
    
    def mouseMoveEvent(self, event): 
        self._update_tooltip(event.position())

    def _update_tooltip(self, pos):
        if not self.SHOW_TOOLTIPS:
            self.tooltip_label.hide()
            return
            
        if not self.chart_data or not self.current_layout: 
            self.tooltip_label.hide()
            return
            
        tooltip_html = ""
        pos_point = QPointF(pos.x(), pos.y())

        fs_11 = int(11 * GLOBAL_FONT_SCALE_MULTIPLIER)
        fs_12 = int(12 * GLOBAL_FONT_SCALE_MULTIPLIER)
        fs_14 = int(14 * GLOBAL_FONT_SCALE_MULTIPLIER)
        fs_ast = int(GLOBAL_TOOLTIP_ASTERISK_SIZE * GLOBAL_FONT_SCALE_MULTIPLIER)
        
        base_asc_sign_idx = self.chart_data["ascendant"]["sign_index"]
        asc_sign_idx = getattr(self, 'rotated_asc_sign_idx', None) if getattr(self, 'rotated_asc_sign_idx', None) is not None else base_asc_sign_idx

        context_prefix = ""
        is_d_chart = self.title and not (self.title == "D1" or self.title.startswith("D1 "))
        
        if is_d_chart:
            chart_prefix = self.title.split()[0]
            
            if getattr(self, 'd1_data', None) and chart_prefix in DIV_THEME_MAP:
                d1_h = DIV_THEME_MAP[chart_prefix]
                
                d1_lord_name = SIGN_LORDS.get((self.d1_data["ascendant"]["sign_index"] + d1_h - 1) % 12 + 1)
                div_lord_p = next((p for p in self.chart_data["planets"] if p["name"] == d1_lord_name), None)
                
                if div_lord_p:
                    dig_flags = []
                    if div_lord_p.get("exalted"): dig_flags.append("Exalted")
                    if div_lord_p.get("debilitated"): dig_flags.append("Debilitated")
                    if div_lord_p.get("own_sign"): dig_flags.append("Own Sign")
                    
                    dig_str = f" ({', '.join(dig_flags)})" if dig_flags else ""
                    context_prefix += (
                        f"<div style='background-color:#FFF8DC; padding:5px; border:1px solid #EEDD82; "
                        f"border-radius:3px; margin-bottom:8px; font-size:{fs_12}px; color:#555;'>"
                        f"<b>Theme Lord: D1 {get_ordinal(d1_h)} Lord ({d1_lord_name}) is in {get_ordinal(div_lord_p['house'])} House here{dig_str}</b>"
                        f"</div>"
                    )

        for rect, p_raw in self.hitboxes:
            if rect.contains(pos_point):
                name = p_raw["name"]
                house = ((p_raw["sign_index"] - asc_sign_idx) % 12) + 1 if "house" in p_raw else "-"
                
                inline_statuses = []
                if p_raw.get("exalted"): inline_statuses.append("Exalted")
                if p_raw.get("debilitated"): inline_statuses.append("Debilitated")
                if p_raw.get("own_sign"): inline_statuses.append("Own Sign")
                
                if p_raw.get("obliterated"): inline_statuses.append("Obliterated")
                elif p_raw.get("combust"): inline_statuses.append("Combust")
                
                if p_raw.get("vargottama") and is_d_chart:
                    inline_statuses.append("Vargottama")
                
                is_retro = (p_raw.get("retro") or name in ["Rahu", "Ketu"]) and name != "Ascendant"
                
                html = context_prefix
                if p_raw.get("is_ak"):
                    html += f"<span style='color: #B8860B;'><b>* Brightest Star / Atmakaraka</b></span><br>"
                    
                visual_lords = sorted([((base_asc_sign_idx + l - 1 - asc_sign_idx) % 12) + 1 for l in p_raw.get("lord_of", [])])
                lord_texts = []
                for l in visual_lords:
                    if l in {1, 2, 4, 5, 7, 9, 10, 11}:
                        lord_texts.append(f"<span style='color: #27ae60;'><b>{get_ordinal(l)}</b></span>")
                    else:
                        lord_texts.append(f"<span style='color: #c0392b;'><b>{get_ordinal(l)}</b></span>")
                
                if name == "Ascendant": 
                    p_color = "#000000"
                else: 
                    _, p_color = self._get_nature_and_color(name, p_raw['sign_index'])
                
                func_color, func_label, func_reason = self._get_dynamic_functional_nature(name, p_raw.get("lord_of", []), base_asc_sign_idx, asc_sign_idx)
                
                retro_html = "<sup style='color:#d35400;'><b>R</b></sup>" if is_retro else ""
                status_str = f" <span style='font-size:{fs_12}px; color:#555;'>({', '.join(inline_statuses)})</span>" if inline_statuses else ""
                asterisk_html = f" <span style='color: {func_color}; font-size: {fs_ast}px;'>*</span>" if name != 'Ascendant' else ""
                
                html += f"<b style='color: {p_color}; font-size: {fs_14}px;'>{name}</b>{retro_html}{status_str}{asterisk_html}"
                if name != 'Ascendant':
                    html += f"<span style='font-size:{fs_11}px; color:#555;'>({func_label} - {func_reason})</span>"
                html += "<hr style='margin: 4px 0;'/>"
                
                html += f"Sign: {ZODIAC_NAMES[p_raw['sign_index']]} ({ZODIAC_ELEMENTS[p_raw['sign_index']]})<br>"
                if house != "-": 
                    html += f"House: {house}<br>"
                if visual_lords: 
                    html += f"Lord of: <b>{' & '.join(lord_texts)} House</b><br>"
                if p_raw.get("nakshatra"): 
                    html += f"Nakshatra: <b>{p_raw['nakshatra']}</b> (Lord: <b style='color: #8e44ad;'>{p_raw['nakshatra_lord']}</b>)<br>"
                
                if name != "Ascendant":
                    sc, bd = 0, []
                    if p_raw.get("exalted"): sc += 2; bd.append("Exalted (+2)")
                    if p_raw.get("own_sign"): sc += 2; bd.append("Own Sign (+2)")
                    if p_raw.get("debilitated"): sc -= 2; bd.append("Debilitated (-2)")
                    
                    if p_raw.get("obliterated"): sc -= 2; bd.append("Obliterated (-2)")
                    elif p_raw.get("combust"): sc -= 1; bd.append("Combust (-1)")
                    
                    if house != "-":
                        if house in [1, 4, 5, 7, 9, 10]: sc += 1; bd.append("Kendra/Trine (+1)")
                        if house in [6, 8, 12]: sc -= 1; bd.append("Dusthana (-1)")
                        
                        conjunct = [p for p in self.chart_data["planets"] if p["sign_index"] == p_raw["sign_index"] and p["name"] != name]
                        for cp in conjunct:
                            is_ben, _ = self._get_nature_and_color(cp["name"], cp["sign_index"])
                            if is_ben: pass
                            else: pass
                            
                        if any(o["name"] in ["Rahu", "Ketu"] for o in conjunct): 
                            sc -= 2; bd.append("<span style='color:#c0392b'>Nodes Conj (-2)</span>")
                        
                        for asp in self.chart_data.get("aspects", []):
                            if asp["target_house"] == ((p_raw["sign_index"] - base_asc_sign_idx) % 12) + 1 and asp["aspecting_planet"] != "Ketu":
                                asp_p = asp["aspecting_planet"]
                                asp_p_sign = next((p["sign_index"] for p in self.chart_data["planets"] if p["name"] == asp_p), -1)
                                is_ben, a_col = self._get_nature_and_color(asp_p, asp_p_sign)
                                
                                if is_ben: 
                                    sc += 1
                                    bd.append(f"<span style='color:{a_col}'>Asp: {asp_p[:2]} (+1)</span>")
                                else: 
                                    sc -= 1
                                    bd.append(f"<span style='color:{a_col}'>Asp: {asp_p[:2]} (-1)</span>")

                    if not any(p_raw.get(k) for k in ["exalted", "debilitated", "own_sign"]):
                        l_cur = SIGN_LORDS.get(p_raw["sign_index"] + 1)
                        if l_cur:
                            if l_cur in PLANET_FRIENDS.get(name, []): sc += 1; bd.append("Friendly Sign (+1)")
                            elif l_cur in PLANET_ENEMIES.get(name, []): sc -= 1; bd.append("Enemy Sign (-1)")

                    if sc >= 4:
                        st_t, bg_c, br_c, fg_c = "VERY STRONG", "#d5f5e3", "#abebc6", "#27ae60"
                    elif sc >= 2:
                        st_t, bg_c, br_c, fg_c = "STRONG", "#d5f5e3", "#abebc6", "#27ae60"
                    elif sc >= 0:
                        st_t, bg_c, br_c, fg_c = "AVERAGE", "#f2f3f4", "#bdc3c7", "#7f8c8d"
                    else:
                        st_t, bg_c, br_c, fg_c = "AFFLICTED", "#fadbd8", "#e6b0aa", "#c0392b"
                        
                    html += f"<div style='margin-top: 8px; margin-bottom: 4px; text-align: center; background-color: {bg_c}; color: {fg_c}; padding: 6px; border-radius: 4px; border: 1px solid {br_c};'><b style='font-size:{fs_12}px;'>{st_t}</b> <span style='font-size:{fs_11}px;'>(Score: {sc})</span><br><span style='font-size:{fs_11}px; font-weight:normal; color:#555;'>{', '.join(bd) or 'Neutral'}</span></div>"
                    
                deg, minute = int(p_raw['deg_in_sign']), int((p_raw['deg_in_sign'] - int(p_raw['deg_in_sign'])) * 60)
                tooltip_html = html + f"Base Longitude: {deg}°{minute:02d}'"
                break
                
        if not tooltip_html:
            hovered_visual_house = None
            for h, poly in self.house_polys.items():
                if poly.containsPoint(pos_point, Qt.FillRule.OddEvenFill):
                    hovered_visual_house = h
                    break
                    
            if hovered_visual_house and hovered_visual_house in self.current_layout.get("houses", {}):
                sign_idx = (asc_sign_idx + hovered_visual_house - 1) % 12
                original_h_num = self.current_layout["houses"][hovered_visual_house]["original_h_num"]
                s_name, s_elem, s_nat = ZODIAC_NAMES[sign_idx], ZODIAC_ELEMENTS[sign_idx], ZODIAC_NATURES[sign_idx]
                
                occ_colored = []
                for p in self.chart_data["planets"]:
                    if p["sign_index"] == sign_idx:
                        pn = p["name"]
                        _, c_col = self._get_nature_and_color(pn, sign_idx)
                        occ_colored.append(f"<b style='color: {c_col};'>{pn}</b>")
                
                rotated_from_house = ((asc_sign_idx - base_asc_sign_idx) % 12) + 1
                from_str = f" (from {get_ordinal(rotated_from_house)})" if rotated_from_house != 1 else ""
                base_str = f" | Base: {get_ordinal(original_h_num)}" if hovered_visual_house != original_h_num else ""
                
                if is_d_chart:
                    tooltip_html = context_prefix + f"<b style='color: #2980b9; font-size: {fs_14}px;'>{get_ordinal(hovered_visual_house)} House{from_str}</b><hr style='margin: 4px 0;'/>"
                else:
                    tooltip_html = context_prefix + f"<b style='color: #2980b9; font-size: {fs_14}px;'>{get_ordinal(hovered_visual_house)} House{from_str}{base_str}</b><hr style='margin: 4px 0;'/>"
                
                nat_color = NATURE_COLORS.get(s_nat, '#000000')
                tooltip_html += f"Sign: <b>{sign_idx + 1} - {s_name}</b><br>"
                tooltip_html += f"Nature: <b style='color: {nat_color};'>{s_nat}</b><br>"
                tooltip_html += f"Element: <b>{s_elem}</b><br>"
                
                h_info = getattr(self, "houses_info", {}).get(original_h_num, {})
                
                v_lbl = h_info.get("vitality_label", "Background Scenery (Neutral)")
                if v_lbl != "Background Scenery (Neutral)": 
                    tooltip_html += f"Vitality (Lords): <b style='color: {h_info.get('vitality_color', '#555')};'>{v_lbl}</b><br>"

                p_lbl = h_info.get("pressure_label", "Quiet (0 influences)")
                if p_lbl != "Quiet (0 influences)": 
                    tooltip_html += f"Pressure (Aspects): <b style='color: {h_info.get('pressure_color', '#555')};'>{p_lbl}</b><br>"
                    
                r_lbls_html = h_info.get("regime_labels_html", [])
                if r_lbls_html: 
                    tooltip_html += f"Regime Forces: {'<br>&nbsp;&nbsp;&nbsp;&bull; '.join([''] + r_lbls_html)}<br>"
                
                lord_name = SIGN_LORDS.get(sign_idx + 1)
                if lord_name:
                    lord_p = next((p for p in self.chart_data["planets"] if p["name"] == lord_name), None)
                    if lord_p:
                        l_status = []
                        if lord_p.get("retro"): l_status.append("Retrograde")
                        if lord_p.get("combust"): l_status.append("Combust")
                        if lord_p.get("exalted"): l_status.append("Exalted")
                        if lord_p.get("debilitated"): l_status.append("Own Sign") 
                        
                        if lord_name in NATURAL_BENEFICS: l_col = '#27ae60'
                        elif lord_name in NATURAL_MALEFICS: l_col = '#c0392b'
                        else: l_col = '#000000'
                        
                        house_idx = get_ordinal(((lord_p['sign_index'] - asc_sign_idx) % 12) + 1)
                        stat_str = f" <span style='font-size:{fs_12}px; color:#555;'>({', '.join(l_status)})</span>" if l_status else ""
                        tooltip_html += f"House Lord: <b style='color: {l_col};'>{lord_name}</b> went to <b>{house_idx} House</b>{stat_str}<br>"

                if occ_colored: 
                    tooltip_html += f"Occupants: {', '.join(occ_colored)}<br>"

                aspecting_strs = []
                for asp in self.chart_data.get("aspects", []):
                    if asp["target_house"] == original_h_num:
                        asp_p = next((p for p in self.chart_data["planets"] if p["name"] == asp["aspecting_planet"]), None)
                        if asp_p:
                            asp_name = asp["aspecting_planet"]
                            _, a_col = self._get_nature_and_color(asp_name, asp_p['sign_index'])
                            
                            elem_str = ZODIAC_ELEMENTS[asp_p['sign_index']].split()[1] + ' sign'
                            
                            lord_nums = [get_ordinal(l) for l in sorted([((base_asc_sign_idx + l - 1 - asc_sign_idx) % 12) + 1 for l in asp_p.get('lord_of', [])])]
                            lord_str = [f"{' & '.join(lord_nums)} lord"] if lord_nums else []
                            
                            stat_flags = []
                            if asp_p.get('retro'): stat_flags.append('Retro')
                            if asp_p.get('exalted'): stat_flags.append('Exalted')
                            if asp_p.get('debilitated'): stat_flags.append('Debilitated')
                            
                            meta_parts = [elem_str] + lord_str + stat_flags
                            meta_str = f" <span style='font-size:{fs_11}px; color:#555;'>({', '.join(meta_parts)})</span>"
                            aspecting_strs.append(f"<b style='color: {a_col};'>{asp_name}</b>{meta_str}")
                
                if aspecting_strs:
                    tooltip_html += f"Aspected by: {'<br>&nbsp;&nbsp;&nbsp;&bull; '.join([''] + aspecting_strs)}"

        if tooltip_html:
            self.tooltip_label.setText(tooltip_html)
            self.tooltip_label.adjustSize()
            
            global_pos = self.mapToGlobal(pos_point.toPoint())
            new_x, new_y = global_pos.x() + 15, global_pos.y() + 15
            
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): 
                    new_x = global_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): 
                    new_y = global_pos.y() - self.tooltip_label.height() - 5
                    
            self.tooltip_label.move(new_x, new_y)
            self.tooltip_label.show()
            self.tooltip_label.raise_()
        else: 
            self.tooltip_label.hide()

    def leaveEvent(self, event):
        if hasattr(self, 'tooltip_label') and self.tooltip_label.isVisible(): 
            self.tooltip_label.hide()
        super().leaveEvent(event)
        
    def hideEvent(self, event):
        if hasattr(self, 'tooltip_label') and self.tooltip_label.isVisible(): 
            self.tooltip_label.hide()
        super().hideEvent(event)