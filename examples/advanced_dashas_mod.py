# dynamic_settings_modules/advanced_dashas_mod.py

import sys, os, math, datetime
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QDialog, QTreeWidget, QTreeWidgetItem, QLabel, 
                             QGroupBox, QTabWidget, QHeaderView, QMessageBox,
                             QComboBox, QDateEdit, QSpinBox, QTableWidget, 
                             QTableWidgetItem, QFrame, QGridLayout, QApplication,
                             QProgressBar, QTextBrowser, QDoubleSpinBox, QCheckBox)
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import Qt, QTimer, QDate, QThread, pyqtSignal
import swisseph as swe
import __main__

# Add parent dir to path to import the dictionary and engine
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import astro_engine
import advanced_dasha_results

info_print = getattr(__main__, 'info_print', print)
error_print = getattr(__main__, 'error_print', print)

# ==============================================================================
# ASTROLOGICAL CONSTANTS
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

SIGN_RULERS = {
    1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 
    5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 
    9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"
}

ZODIAC_NAMES = {
    1: "Aries", 2: "Taurus", 3: "Gemini", 4: "Cancer", 5: "Leo", 6: "Virgo", 
    7: "Libra", 8: "Scorpio", 9: "Sagittarius", 10: "Capricorn", 11: "Aquarius", 12: "Pisces"
}

EVENT_CATEGORIES = [
    "Marriage / Romance",
    "Childbirth",
    "Career Success / Wealth",
    "Sudden Career / Job", 
    "Accident / Injury / Distress"
]

# ==============================================================================
# ASTROLOGICAL RULE COMPONENTS (Dasha & BTR validations)
# ==============================================================================

def get_house_lord(house_sign):
    return SIGN_RULERS.get(house_sign)

def get_relative_house(base_sign, target_sign):
    return (target_sign - base_sign) % 12 + 1

def check_parashari_aspect(asp_planet, p_sign, target_sign):
    dist = get_relative_house(p_sign, target_sign)
    if dist == 7: return True
    if asp_planet == "Mars" and dist in [4, 8]: return True
    if asp_planet == "Jupiter" and dist in [5, 9]: return True
    if asp_planet == "Saturn" and dist in [3, 10]: return True
    return False

def check_jaimini_aspect(s1, s2):
    if s1 in [1, 4, 7, 10]:     
        return s2 in {1: [5,8,11], 4: [8,11,2], 7: [11,2,5], 10: [2,5,8]}[s1]
    elif s1 in [2, 5, 8, 11]:   
        return s2 in {2: [4,7,10], 5: [7,10,1], 8: [10,1,4], 11: [1,4,7]}[s1]
    elif s1 in [3, 6, 9, 12]:   
        return s2 in {3: [6,9,12], 6: [9,12,3], 9: [12,3,6], 12: [3,6,9]}[s1]
    return False

def check_connection(p1_name, p1_sign, p2_name, p2_sign):
    if p1_sign == p2_sign: return True, f"Conjunction in {ZODIAC_NAMES[p1_sign]}"
    if check_parashari_aspect(p1_name, p1_sign, p2_sign): return True, f"{p1_name} aspects {p2_name}"
    if check_parashari_aspect(p2_name, p2_sign, p1_sign): return True, f"{p2_name} aspects {p1_name}"
    if get_house_lord(p1_sign) == p2_name and get_house_lord(p2_sign) == p1_name:
        return True, f"Exchange (Parivartana) between {p1_name} and {p2_name}"
    return False, ""

def evaluate_sudden_career(dasha_lagna, planets_data):
    debug_logs = []
    house_8 = (dasha_lagna + 6) % 12 + 1
    house_10 = (dasha_lagna + 8) % 12 + 1
    lord_8 = get_house_lord(house_8)
    lord_10 = get_house_lord(house_10)
    l8_sign = planets_data[lord_8]['sign']
    l10_sign = planets_data[lord_10]['sign']
    
    if l8_sign == house_10:
        debug_logs.append(f"[Sudden Job] MATCH: 8th Lord {lord_8} occupies 10th House ({ZODIAC_NAMES[house_10]}) from Dasha Lagna.")
        return True, 4, debug_logs
    if check_parashari_aspect(lord_8, l8_sign, house_10):
        debug_logs.append(f"[Sudden Job] MATCH: 8th Lord {lord_8} aspects 10th House ({ZODIAC_NAMES[house_10]}).")
        return True, 3, debug_logs
    if l10_sign == house_8:
        debug_logs.append(f"[Sudden Job] MATCH: 10th Lord {lord_10} occupies 8th House ({ZODIAC_NAMES[house_8]}) from Dasha Lagna.")
        return True, 4, debug_logs
        
    connected, reason = check_connection(lord_8, l8_sign, lord_10, l10_sign)
    if connected:
        debug_logs.append(f"[Sudden Job] MATCH: 8th Lord {lord_8} & 10th Lord {lord_10} connected: {reason}.")
        return True, 4, debug_logs
    return False, 0, debug_logs

def evaluate_injury_accident(dasha_lagna, planets_data):
    debug_logs = []
    house_8 = (dasha_lagna + 6) % 12 + 1
    lord_8 = get_house_lord(house_8)
    mars_sign = planets_data["Mars"]['sign']
    l8_sign = planets_data[lord_8]['sign']
    
    if mars_sign == house_8:
        debug_logs.append(f"[Accident] MATCH: Mars occupies 8th House ({ZODIAC_NAMES[house_8]}) from Dasha Lagna.")
        return True, 5, debug_logs
    if check_parashari_aspect("Mars", mars_sign, house_8):
        debug_logs.append(f"[Accident] MATCH: Mars aspects 8th House ({ZODIAC_NAMES[house_8]}) from Dasha Lagna.")
        return True, 3, debug_logs
        
    connected, reason = check_connection("Mars", mars_sign, lord_8, l8_sign)
    if connected:
        debug_logs.append(f"[Accident] MATCH: Mars connects to 8th Lord ({lord_8}) via {reason}.")
        return True, 4, debug_logs
    return False, 0, debug_logs

# --- BIRTH TIME RECTIFICATION (BTR) CORE RULES ---

def get_d9_sign(lon):
    base = int(lon / 30) + 1
    nav = int((lon % 30) / (30/9))
    if base in [1, 4, 7, 10]: start = base
    elif base in [2, 5, 8, 11]: start = (base + 8) % 12 + 1
    else: start = (base + 4) % 12 + 1
    return (start - 1 + nav) % 12 + 1

def check_btr_kunda(asc_lon, moon_lon):
    """BTR Kunda Rule: Ascendant * 81 must fall into a Nakshatra matching the Moon's ruling planet."""
    kunda_lon = (asc_lon * 81.0) % 360.0
    kunda_nak = int(kunda_lon / (360.0/27.0))
    moon_nak = int(moon_lon / (360.0/27.0))
    
    if (kunda_nak % 9) == (moon_nak % 9):
        return True, f"[BTR Kunda] PASSED: Asc*81 -> Nakshatra #{kunda_nak}, ruled by same planet as Moon's Nakshatra #{moon_nak}."
    return False, ""

def check_btr_navamsha_moon(asc_lon, moon_lon):
    """BTR Navamsha Rule: D9 Ascendant must align with D9 Moon (1st, 5th, 7th, or 9th house)."""
    d9_asc = get_d9_sign(asc_lon)
    d9_moon = get_d9_sign(moon_lon)
    
    dist = get_relative_house(d9_asc, d9_moon)
    if dist in [1, 5, 7, 9]:
        return True, f"[BTR Navamsha] PASSED: D9 Moon ({ZODIAC_NAMES[d9_moon]}) is in House {dist} from D9 Ascendant ({ZODIAC_NAMES[d9_asc]})."
    return False, ""

def filter_by_d24_mk(planets_data, asc_lon):
    """D24 Jaimini Filter: MK must connect with 5H/5L."""
    seven_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
    sorted_p = sorted(seven_planets, key=lambda p: planets_data[p]['lon'] % 30.0, reverse=True)
    mk_name = sorted_p[3]
    
    def get_d24_sign(lon):
        base_sign = int(lon / 30) + 1
        div_idx = int((lon % 30) / 1.25)
        if base_sign % 2 != 0: return (4 + div_idx) % 12 + 1 
        else: return (3 + div_idx) % 12 + 1 
        
    d24_asc = get_d24_sign(asc_lon)
    mk_d24_sign = get_d24_sign(planets_data[mk_name]['lon'])
    
    fifth_house_sign = (d24_asc + 3) % 12 + 1
    fifth_lord = get_house_lord(fifth_house_sign)
    fifth_lord_d24_sign = get_d24_sign(planets_data[fifth_lord]['lon'])
    
    log_prefix = f"[D24 Edu Filter] MK ({mk_name}) in {ZODIAC_NAMES[mk_d24_sign]}. 5th Lord ({fifth_lord}) in {ZODIAC_NAMES[fifth_lord_d24_sign]}."
    
    if mk_d24_sign == fifth_house_sign: return True, f"{log_prefix} -> PASSED: MK occupies 5th House."
    if mk_d24_sign == fifth_lord_d24_sign: return True, f"{log_prefix} -> PASSED: MK conjuncts 5th Lord."

    if check_jaimini_aspect(mk_d24_sign, fifth_house_sign): return True, f"{log_prefix} -> PASSED: MK Jaimini-aspects 5th House."
    if check_jaimini_aspect(mk_d24_sign, fifth_lord_d24_sign): return True, f"{log_prefix} -> PASSED: MK Jaimini-aspects 5th Lord."
    if check_parashari_aspect(mk_name, mk_d24_sign, fifth_house_sign): return True, f"{log_prefix} -> PASSED: MK Parashari-aspects 5th House."
    if check_parashari_aspect(mk_name, mk_d24_sign, fifth_lord_d24_sign): return True, f"{log_prefix} -> PASSED: MK Parashari-aspects 5th Lord."

    if get_house_lord(mk_d24_sign) == fifth_lord and get_house_lord(fifth_lord_d24_sign) == mk_name:
        if mk_d24_sign == fifth_house_sign or fifth_lord_d24_sign == fifth_house_sign:
            return True, f"{log_prefix} -> PASSED: Valid MK/5th Lord Exchange involving 5H."
            
    return False, f"{log_prefix} -> FAILED: No connection."


# ==============================================================================
# PURE MATHEMATICAL CORE (Dashas)
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
# WORKER THREAD FOR REVERSE DASHA & BTR SEARCH
# ==============================================================================

class SearchWorker(QThread):
    progress = pyqtSignal(int)
    log_msg = pyqtSignal(str)
    search_finished = pyqtSignal(list)

    def __init__(self, target_year, events_data, lat, lon, apply_d24_filter):
        super().__init__()
        self.target_year = target_year
        self.events_data = events_data
        self.lat = lat
        self.lon = lon
        self.apply_d24_filter = apply_d24_filter

    def fetch_planets(self, jd):
        planets_data = {}
        for p_name, swe_id in SWE_PLANET_MAP.items():
            if p_name == "Ketu":
                lon_val = (swe.calc_ut(jd, swe.MEAN_NODE)[0][0] + 180) % 360
            else:
                lon_val = swe.calc_ut(jd, swe_id)[0][0]
            aya = swe.get_ayanamsa_ut(jd)
            sid_lon = (lon_val - aya) % 360
            planets_data[p_name] = {'lon': sid_lon, 'sign': int(sid_lon / 30) + 1}
        return planets_data

    def get_ascendant(self, jd):
        cusps, ascmc = swe.houses(jd, self.lat, self.lon, b'P')
        aya = swe.get_ayanamsa_ut(jd)
        return (ascmc[0] - aya) % 360

    def run(self):
        swe.set_ephe_path('') 
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        
        self.log_msg.emit(">>> PHASE 1: Macro Day-Level Scan (Finding Plausible Days based on Dashas)...")
        start_date = datetime.datetime(self.target_year, 1, 1, 12, 0)
        
        plausible_days = []
        
        # PHASE 1: Scan 365 Days at noon to find periods where Dasha aligns with events
        for day_idx in range(365):
            curr_date = start_date + datetime.timedelta(days=day_idx)
            jd = swe.julday(curr_date.year, curr_date.month, curr_date.day, 12.0)
            
            planets_data = self.fetch_planets(jd)
            moon_sid_lon = planets_data["Moon"]['lon']
            timeline = calculate_vimshottari_engine(moon_sid_lon, curr_date)
            
            total_score = 0
            day_matches = []
            
            for ev in self.events_data:
                ev_date = ev["date"]
                ev_cat = ev["cat"]
                active_md, active_ad = None, None
                
                for md in timeline:
                    if md['start'].date() <= ev_date <= md['end'].date():
                        active_md = md
                        for ad in md['antardashas']:
                            if ad['start'].date() <= ev_date <= ad['end'].date():
                                active_ad = ad
                                break
                        break
                
                if active_md and active_ad:
                    md_lord, ad_lord = active_md['lord'], active_ad['sub_lord']
                    dasha_lagna = planets_data[md_lord]['sign']
                    event_score = 0
                    log_str = ""

                    if ev_cat == "Accident / Injury / Distress":
                        is_match, score, logs = evaluate_injury_accident(dasha_lagna, planets_data)
                        event_score += score
                        if logs: log_str = logs[0]
                    elif ev_cat == "Sudden Career / Job":
                        is_match, score, logs = evaluate_sudden_career(dasha_lagna, planets_data)
                        event_score += score
                        if logs: log_str = logs[0]
                    else:
                        kws = {
                            "Marriage / Romance": ["marriage", "wife", "husband", "conjugal", "women", "romance", "bed", "sweet"],
                            "Childbirth": ["son", "daughter", "child", "grandchildren", "birth", "family"],
                            "Career Success / Wealth": ["king", "wealth", "business", "commander", "glory", "property", "gains", "profits", "sovereignty"]
                        }.get(ev_cat, [])
                        
                        text_to_search = (active_ad['effect'] + " " + active_ad['weak']).lower()
                        matched_kws = [kw for kw in kws if kw.lower() in text_to_search]
                        
                        if matched_kws:
                            event_score += 2
                            log_str = f"[{ev_cat}] Keyword match in {ad_lord} AD: {', '.join(matched_kws)}."
                            
                    total_score += event_score
                    if log_str: day_matches.append(log_str)
            
            if total_score >= 6:
                plausible_days.append((curr_date, day_matches, total_score))
            
            if day_idx % 36 == 0: self.progress.emit(int((day_idx / 365) * 50))

        self.log_msg.emit(f">>> PHASE 1 COMPLETE. Found {len(plausible_days)} plausible days.")
        if not plausible_days:
            self.search_finished.emit([])
            return

        self.log_msg.emit(">>> PHASE 2: Micro Minute-Level Scan (Applying Strict BTR Rules)...")
        
        final_results = []
        total_days = len(plausible_days)
        
        # PHASE 2: Scan every 3 minutes inside the plausible days
        for idx, (base_date, base_matches, base_score) in enumerate(plausible_days):
            day_start = datetime.datetime(base_date.year, base_date.month, base_date.day, 0, 0)
            
            current_window = None
            
            for m in range(0, 1440, 3): # 3-minute steps (approx 0.75 degrees Asc shift)
                curr_time = day_start + datetime.timedelta(minutes=m)
                jd = swe.julday(curr_time.year, curr_time.month, curr_time.day, curr_time.hour + (curr_time.minute/60.0))
                
                asc_lon = self.get_ascendant(jd)
                planets_data = self.fetch_planets(jd)
                moon_lon = planets_data["Moon"]['lon']
                
                # --- APPLY BTR RULES ---
                btr_logs = []
                
                # Rule 1: Kunda Match (Mandatory)
                pass_kunda, kunda_log = check_btr_kunda(asc_lon, moon_lon)
                if not pass_kunda:
                    if current_window: 
                        final_results.append((current_window, base_matches, base_score))
                        current_window = None
                    continue
                btr_logs.append(kunda_log)
                
                # Rule 2: Navamsha Moon Connection (Mandatory)
                pass_nav, nav_log = check_btr_navamsha_moon(asc_lon, moon_lon)
                if not pass_nav:
                    if current_window: 
                        final_results.append((current_window, base_matches, base_score))
                        current_window = None
                    continue
                btr_logs.append(nav_log)
                
                # Rule 3: Jaimini D24 (Conditional)
                if self.apply_d24_filter:
                    pass_d24, d24_log = filter_by_d24_mk(planets_data, asc_lon)
                    if not pass_d24:
                        if current_window: 
                            final_results.append((current_window, base_matches, base_score))
                            current_window = None
                        continue
                    btr_logs.append(d24_log)
                
                # If we get here, all BTR checks passed for this minute! Group contiguous hits.
                if current_window is None:
                    current_window = {"start": curr_time, "end": curr_time, "logs": btr_logs}
                else:
                    current_window["end"] = curr_time
                    
            if current_window:
                final_results.append((current_window, base_matches, base_score))
                
            self.progress.emit(50 + int(((idx+1) / total_days) * 50))
            
        final_results.sort(key=lambda x: x[2], reverse=True)
        self.search_finished.emit(final_results)


# ==============================================================================
# REVERSE DASHA UI DIALOG
# ==============================================================================

class ReverseDashaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reverse Dasha & BTR Search (Super Accurate Time Finder)")
        self.resize(1200, 800)
        self.setStyleSheet("background-color: #F8FAFC; color: #0F172A;")
        
        layout = QVBoxLayout(self)
        
        # --- Top Input Section ---
        input_group = QGroupBox("Target Events & Geography")
        input_layout = QGridLayout(input_group)
        
        input_layout.addWidget(QLabel("Target Age (in Current Year):"), 0, 0)
        self.age_spin = QSpinBox()
        self.age_spin.setRange(1, 120)
        self.age_spin.setValue(30)
        input_layout.addWidget(self.age_spin, 0, 1)

        input_layout.addWidget(QLabel("Birth Lat:"), 0, 2)
        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90, 90)
        self.lat_spin.setValue(28.6139) # Delhi default
        input_layout.addWidget(self.lat_spin, 0, 3)
        
        input_layout.addWidget(QLabel("Birth Lon:"), 0, 4)
        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180, 180)
        self.lon_spin.setValue(77.2090)
        input_layout.addWidget(self.lon_spin, 0, 5)

        self.events_ui = []
        for i in range(3):
            cat_combo = QComboBox()
            cat_combo.addItems(EVENT_CATEGORIES)
            date_edit = QDateEdit()
            date_edit.setCalendarPopup(True)
            date_edit.setDate(QDate.currentDate().addYears(-(i*2)))
            
            input_layout.addWidget(QLabel(f"Event {i+1} Category:"), i+1, 0)
            input_layout.addWidget(cat_combo, i+1, 1, 1, 2)
            input_layout.addWidget(QLabel("Date of Occurrence:"), i+1, 3)
            input_layout.addWidget(date_edit, i+1, 4, 1, 2)
            
            self.events_ui.append((cat_combo, date_edit))
            
        layout.addWidget(input_group)
        
        # --- Strict Filters ---
        self.d24_filter_cb = QCheckBox("Apply Strict D24 MK-5H Filter (Removes charts failing Jaimini Education Rule)")
        self.d24_filter_cb.setChecked(True)
        self.d24_filter_cb.setStyleSheet("font-weight: bold; color: #B91C1C;")
        layout.addWidget(self.d24_filter_cb)
        
        # --- Progress & Controls ---
        ctrl_layout = QHBoxLayout()
        self.btn_search = QPushButton("Start 2-Phase BTR Deep Scan")
        self.btn_search.setStyleSheet("QPushButton { background-color: #0284C7; color: white; font-weight: bold; padding: 10px; border-radius: 4px;}")
        self.btn_search.clicked.connect(self.start_scan)
        ctrl_layout.addWidget(self.btn_search)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        ctrl_layout.addWidget(self.progress_bar)
        layout.addLayout(ctrl_layout)
        
        # --- Split View (Results vs Debug Log) ---
        split_layout = QHBoxLayout()
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Precise Time Window", "Events Verified (Dashas)", "BTR Rules Passed", "Score"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.itemSelectionChanged.connect(self.display_selection_debug)
        split_layout.addWidget(self.results_table, 2)
        
        debug_group = QGroupBox("Engine Debug / Mathematical Proofs")
        debug_vbox = QVBoxLayout(debug_group)
        self.debug_console = QTextBrowser()
        self.debug_console.setStyleSheet("background-color: #1E293B; color: #38BDF8; font-family: monospace; font-size: 11px;")
        debug_vbox.addWidget(self.debug_console)
        split_layout.addWidget(debug_group, 1)
        
        layout.addLayout(split_layout)
        
        self.worker = None
        self.current_results = []

    def start_scan(self):
        self.btn_search.setEnabled(False)
        self.progress_bar.setValue(0)
        self.debug_console.clear()
        self.debug_console.append(">>> Initializing 2-Phase Swiss Ephemeris deep scan...\n")
        
        target_year = datetime.datetime.now().year - self.age_spin.value()
        events_data = [{"cat": combo.currentText(), "date": dedit.date().toPyDate()} for combo, dedit in self.events_ui]
            
        self.worker = SearchWorker(
            target_year, 
            events_data, 
            self.lat_spin.value(), 
            self.lon_spin.value(),
            self.d24_filter_cb.isChecked()
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log_msg.connect(self.debug_console.append)
        self.worker.search_finished.connect(self.on_search_finished)
        self.worker.start()

    def on_search_finished(self, results):
        self.progress_bar.setValue(100)
        self.btn_search.setEnabled(True)
        self.current_results = results
        
        self.results_table.setRowCount(0)
        for row_idx, (window, dasha_matches, score) in enumerate(results):
            self.results_table.insertRow(row_idx)
            
            # Format time window beautifully
            t_start = window['start'].strftime("%Y-%b-%d  %H:%M")
            t_end = window['end'].strftime("%H:%M")
            time_str = f"{t_start} to {t_end}"
            
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(time_str))
            
            events_txt = "\n".join(dasha_matches)
            btr_txt = f"{len(window['logs'])} Classical BTR Checks Passed"
            
            self.results_table.setItem(row_idx, 1, QTableWidgetItem(events_txt))
            self.results_table.setItem(row_idx, 2, QTableWidgetItem(btr_txt))
            
            score_item = QTableWidgetItem(str(score))
            score_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            if score >= 12: score_item.setForeground(QColor("#16A34A"))
            self.results_table.setItem(row_idx, 3, score_item)
            
            self.results_table.resizeRowToContents(row_idx)
            
        self.debug_console.append(f"\n>>> Scan Complete. Filtered down to {len(results)} highly verified minute-level time windows.")

    def display_selection_debug(self):
        selected = self.results_table.selectedItems()
        if not selected: return
        row = selected[0].row()
        
        window, dasha_matches, score = self.current_results[row]
        self.debug_console.clear()
        
        t_start = window['start'].strftime("%Y-%b-%d  %H:%M")
        t_end = window['end'].strftime("%H:%M")
        
        self.debug_console.append(f"<b>--- MATHEMATICAL TRACE FOR WINDOW: {t_start} to {t_end} ---</b><br>")
        self.debug_console.append(f"<b>Dasha/Event Confidence Score: {score}</b><br>")
        
        self.debug_console.append("<br><b>1. Dasha-Lagna Validations:</b>")
        for log in dasha_matches:
            self.debug_console.append(f" > {log}")
            
        self.debug_console.append("<br><b>2. Birth Time Rectification (BTR) Validations:</b>")
        for log in window['logs']:
            self.debug_console.append(f" > {log}")


# ==============================================================================
# UI VIEWER DIALOG (Standard Chart Dashas)
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
# UI INJECTION (Shared Setup Implementation)
# ==============================================================================

def setup_ui(app, layout):
    """Injects Reverse Dasha Search button into the unified Analysis group."""
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

    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #dcdde1; margin-top: 4px; margin-bottom: 4px;")
    target_layout.addWidget(line)

    lbl_title = QLabel("BTR & Reverse Dasha Search")
    lbl_title.setStyleSheet("color: #0284C7; font-weight: bold; font-size: 15px; margin-top: 4px;")
    target_layout.addWidget(lbl_title)
    
    lbl_name = "reverse_dasha_lbl_active"
    btn_name = "reverse_dasha_btn_active"
    
    summary_lbl = QLabel("<i>Calculates exact birth-time to the minute using Classical Kunda (*81) rules, D9 Navamsha connections, and Jaimini D24 MK tracking.</i>")
    summary_lbl.setObjectName(lbl_name)
    summary_lbl.setStyleSheet("background-color: #fdfefe; border: 1px solid #dcdde1; border-radius: 4px; padding: 6px; font-family: monospace;")
    summary_lbl.setWordWrap(True)
    target_layout.addWidget(summary_lbl)

    btn_details = QPushButton("Run Precise BTR Tool")
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
    """Standard entry point."""
    app = QApplication.instance()
    setup_ui(app, layout)
    
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