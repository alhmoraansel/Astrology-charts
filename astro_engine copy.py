# astro_engine.py

import swisseph as swe, datetime, pytz, time, math, copy, os, sys, threading
import custom_vargas

swe_lock = threading.Lock()

# ==========================================
# GLOBAL ASTROLOGICAL RULES & CONSTANTS
# ==========================================

# Exaltation signs (1-indexed: 1=Aries, 2=Taurus, etc.)
EXALTATION_RULES = {
    "Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, 
    "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8
}

# Debilitation signs (1-indexed)
DEBILITATION_RULES = {
    "Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, 
    "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2
}

# Sign Rulerships (1=Aries -> Mars)
SIGN_RULERS = {
    1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 
    5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 
    9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"
}

# Mapping swisseph bodies to strings for fallback calculations
SWE_BODY_MAP_REV = {
    swe.SUN: "Sun", swe.MOON: "Moon", swe.MARS: "Mars",
    swe.MERCURY: "Mercury", swe.JUPITER: "Jupiter", swe.VENUS: "Venus",
    swe.SATURN: "Saturn", swe.TRUE_NODE: "Rahu", swe.MEAN_NODE: "Rahu"
}

def get_dignities(p_name, sign_num, deg_in_sign):
    """
    Calculates Exaltation, Own Sign, and Debilitation status for a given planet.
    Includes specific deep-degree exceptions for Moon and Mercury.
    """
    is_own = (SIGN_RULERS.get(sign_num) == p_name)
    is_debilitated = (sign_num == DEBILITATION_RULES.get(p_name))
    is_exalted = (sign_num == EXALTATION_RULES.get(p_name))
    
    # Specific degree-based exceptions in Vedic Astrology
    if p_name == "Moon" and sign_num == 2:
        is_exalted = (deg_in_sign <= 3.0)
        is_own = not is_exalted
    elif p_name == "Mercury" and sign_num == 6:
        is_exalted = (deg_in_sign <= 15.0)
        is_own = not is_exalted
        
    if p_name == "Moon" and sign_num == 8:
        is_debilitated = (deg_in_sign <= 3.0)
    elif p_name == "Mercury" and sign_num == 12:
        is_debilitated = (deg_in_sign <= 15.0)
        
    return is_exalted, is_own, is_debilitated


# ==========================================
# SWISSEPH SAFE WRAPPERS & FALLBACK MATH
# ==========================================
def get_resource_path(relative_path):
    """Safely gets the resource path for Raw Python, Nuitka, and PyInstaller."""
    try:
        # 1. PyInstaller --onefile / --onedir runtime temp directory
        if hasattr(sys, '_MEIPASS'):
            meipass_path = os.path.join(sys._MEIPASS, relative_path)
            if os.path.exists(meipass_path):
                return meipass_path

        # 2. Executable root (Nuitka --standalone or PyInstaller fallback)
        if getattr(sys, 'frozen', False) or '__compiled__' in globals():
            root_path = os.path.join(os.path.dirname(sys.executable), relative_path)
            if os.path.exists(root_path):
                return root_path

        # 3. Fallback for normal terminal execution (.py script)
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    except Exception as e:
        print(f"[DEBUG - ASTRO_ENGINE] Error resolving resource path for {relative_path}: {e}")
        return relative_path

# Cache the path string so we aren't resolving it thousands of times per second
GLOBAL_EPHE_PATH = get_resource_path('ephe')


def fallback_ayanamsa(jd):
    """Fallback Ayanamsa calculation if Swiss Ephemeris is missing."""
    T = (jd - 2451545.0) / 36525.0
    return (23.85 + 1.396 * T) % 360.0


def fallback_planet_calc(jd, body_name):
    """Hardcoded approximate planetary calculation for emergency fallbacks."""
    T = (jd - 2451545.0) / 36525.0
    elements = {
        "Sun": (280.46646, 36000.76983), "Moon": (218.3165, 481267.8813),
        "Mars": (355.4533, 19140.3026), "Mercury": (252.2503, 149472.6741),
        "Jupiter": (34.40438, 3034.9057), "Venus": (181.9791, 58517.8153),
        "Saturn": (50.07744, 1222.1136), "Rahu": (125.0445, -1934.13626)
    }
    
    if body_name in elements:
        L0, L1 = elements[body_name]
        return ((L0 + L1 * T) % 360.0, 0.0, 0.0, L1 / 36525.0)
    return (0.0, 0.0, 0.0, 0.0)


def fallback_ascendant(jd, lat, lon):
    """Mathematical fallback for calculating the Ascendant degree."""
    T = (jd - 2451545.0) / 36525.0
    GMST = 280.46061837 + 360.98564736629 * (jd - 2451545.0)
    LST = (GMST + lon) % 360.0
    eps = 23.43929 - 0.0130042 * T
    rad = math.pi / 180.0
    
    y = math.cos(LST * rad)
    x = -math.sin(LST * rad) * math.cos(eps * rad) - math.tan(lat * rad) * math.sin(eps * rad)
    asc = math.atan2(y, x) / rad
    
    return asc + 360.0 if asc < 0 else asc


def safe_calc_ut(jd, body, flag):
    with swe_lock: 
        # CRITICAL FIX: Re-assert path inside the lock to defeat C-level Thread Local Storage dropping paths
        swe.set_ephe_path(GLOBAL_EPHE_PATH)
        try: 
            res = swe.calc_ut(jd, body, flag)
            
            # Silent Drop Detector: Swisseph didn't throw an error, but it used Moshier instead of Se1!
            if (flag & swe.FLG_SWIEPH) and not (res[1] & swe.FLG_SWIEPH):
                print(f"[WARNING - ASTRO_ENGINE] Swisseph SILENTLY fell back to Moshier for body {body}. Ephe files might be missing or unreadable.")
                
            return res
        except Exception as e:
            print(f"\n[CRITICAL ERROR - ASTRO_ENGINE] SWISSEPH PRECISION FAILURE for body {body}.")
            print(f"[CRITICAL ERROR - ASTRO_ENGINE] Error details: {e}")
            
            abs_ephe_dir = os.path.abspath(GLOBAL_EPHE_PATH)
            print(f"[CRITICAL ERROR - ASTRO_ENGINE] Looked for ephemeris folder at: {abs_ephe_dir}")
            
            if not os.path.exists(abs_ephe_dir):
                print(f"[CRITICAL ERROR - ASTRO_ENGINE] The 'ephe' folder DOES NOT EXIST at the specified path.")
            else:
                files_in_dir = os.listdir(abs_ephe_dir)
                se1_files = [f for f in files_in_dir if f.endswith('.se1')]
                print(f"[CRITICAL ERROR - ASTRO_ENGINE] Folder exists. Found {len(se1_files)} .se1 files: {se1_files}")
                print(f"[CRITICAL ERROR - ASTRO_ENGINE] Swisseph expected highly precise .se1 files (like sepl_18.se1, semo_18.se1) for JD {jd} which are MISSING.")

            print("[CRITICAL ERROR - ASTRO_ENGINE] Falling back to MOSEPH emulator. STRICT PRECISION WILL BE LOST!")
            
            eval_body = swe.MEAN_NODE if body == swe.TRUE_NODE else body
            if body == swe.TRUE_NODE:
                print(f"[CRITICAL ERROR - ASTRO_ENGINE] TRUE_NODE (Rahu) not supported by Moshier. Force-swapping to MEAN_NODE.")
            
            try: 
                fallback_flag = (flag & ~swe.FLG_SWIEPH) | swe.FLG_MOSEPH
                res = swe.calc_ut(jd, eval_body, fallback_flag)
                return res
            except Exception as e2:
                print(f"[CRITICAL ERROR - ASTRO_ENGINE] MOSEPH fallback completely failed: {e2}. Attempting pure Python math fallback...")
                
                body_name = SWE_BODY_MAP_REV.get(body)
                if body_name:
                    res = fallback_planet_calc(jd, body_name)
                    return (res, 0)
                return ((0.0, 0.0, 0.0, 0.0), 0)


def safe_houses_ex(jd, lat, lon, hsys, flag):
    """Safe wrapper for calculating astrological houses and ascendant."""
    with swe_lock: 
        # CRITICAL FIX: Re-assert path for Thread Local Storage
        swe.set_ephe_path(GLOBAL_EPHE_PATH)
        try: 
            return swe.houses_ex(jd, lat, lon, hsys, flag)
        except Exception as e:
            print(f"\n[CRITICAL ERROR - ASTRO_ENGINE] SWISSEPH HOUSES PRECISION FAILURE.")
            print(f"[CRITICAL ERROR - ASTRO_ENGINE] Error details: {e}")
            print(f"[CRITICAL ERROR - ASTRO_ENGINE] Falling back to MOSEPH house calculations. PRECISION WILL BE LOST!")
            try: 
                fallback_flag = (flag & ~swe.FLG_SWIEPH) | swe.FLG_MOSEPH
                return swe.houses_ex(jd, lat, lon, hsys, fallback_flag)
            except Exception as e2:
                print(f"[CRITICAL ERROR - ASTRO_ENGINE] MOSEPH house fallback failed: {e2}. Attempting pure python ascendant math...")
                pass
                
    # Manual fallback execution (outside the main try block)
    asc_lon = fallback_ascendant(jd, lat, lon)
    if flag & swe.FLG_SIDEREAL:
        asc_lon = (asc_lon - fallback_ayanamsa(jd)) % 360.0
    return (tuple([0.0]*13), (asc_lon, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))


def safe_rise_trans(jd, body, rsmi, geopos):
    """Safe wrapper for Sunrise/Sunset event calculations."""
    with swe_lock: 
        # CRITICAL FIX: Re-assert path for Thread Local Storage
        swe.set_ephe_path(GLOBAL_EPHE_PATH)
        try: 
            # PySwisseph signature drops 'starname' completely for planets
            return swe.rise_trans(jd, body, rsmi, geopos)
        except Exception as e: 
            print(f"\n[CRITICAL ERROR - ASTRO_ENGINE] SWISSEPH RISE/TRANS PRECISION FAILURE.")
            print(f"[CRITICAL ERROR - ASTRO_ENGINE] Error details: {e}")
            print(f"[CRITICAL ERROR - ASTRO_ENGINE] Falling back to MOSEPH rise_trans calculations. PRECISION WILL BE LOST!")
            try:
                eval_body = swe.MEAN_NODE if body == swe.TRUE_NODE else body
                # epheflag is the 7th argument natively, so we pass it safely as a kwarg
                return swe.rise_trans(jd, eval_body, rsmi, geopos, epheflag=swe.FLG_MOSEPH)
            except Exception as e2:
                print(f"[CRITICAL ERROR - ASTRO_ENGINE] MOSEPH rise_trans failed: {e2}. No fallback available, aborting calculation.")
                raise e2

# ==========================================
# TIME & DATE CONVERSION UTILITIES
# ==========================================
def ymdhms_to_jd(year, month, day, hour=0, minute=0, second=0.0, gregorian=True):
    """Converts a standard calendar date and time to a Julian Day number."""
    day_frac = (hour + minute / 60.0 + second / 3600.0) / 24.0
    D = day + day_frac
    Y = year
    M = month
    
    if M <= 2: 
        Y -= 1
        M += 12
        
    A = math.floor(Y / 100.0)
    B = 2 - A + math.floor(A / 4.0) if gregorian else 0
    
    return float(math.floor(365.25 * (Y + 4716)) + math.floor(30.6001 * (M + 1)) + D + B - 1524.5)

def jd_to_ymdhms(jd, gregorian=True):
    """Converts a Julian Day number back into a calendar date/time dictionary."""
    Z = math.floor(jd + 0.5)
    F = (jd + 0.5) - Z
    
    if gregorian:
        alpha = math.floor((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - math.floor(alpha / 4.0)
    else: 
        A = Z
        
    B = A + 1524
    C = math.floor((B - 122.1) / 365.25)
    D = math.floor(365.25 * C)
    E = math.floor((B - D) / 30.6001)
    
    day_decimal = B - D - math.floor(30.6001 * E) + F
    day = int(math.floor(day_decimal))
    total_seconds = (day_decimal - day) * 86400.0
    
    month = int(E - 1) if E < 14 else int(E - 13)
    year = int(C - 4716) if month > 2 else int(C - 4715)
    
    hour = int(total_seconds // 3600)
    minute = int((total_seconds % 3600) // 60)
    second = total_seconds - (hour * 3600) - (minute * 60)
    
    return {'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute, 'second': second}

def dt_dict_to_utc_jd(dt_dict, tz_name):
    """Converts a localized datetime dictionary into a UTC Julian Day."""
    y = dt_dict['year']
    m = dt_dict.get('month', 1)
    d = dt_dict.get('day', 1)
    h = dt_dict.get('hour', 0)
    mi = dt_dict.get('minute', 0)
    s = dt_dict.get('second', 0.0)
    
    offset_hours = 0.0
    try:
        if 1 <= y <= 9999: 
            dt_obj = datetime.datetime(y, m, d, h, mi, int(s))
            localized_dt = pytz.timezone(tz_name).localize(dt_obj)
            offset_hours = localized_dt.utcoffset().total_seconds() / 3600.0
        else: 
            fallback_dt = datetime.datetime(2000, 1, 1)
            localized_dt = pytz.timezone(tz_name).localize(fallback_dt)
            offset_hours = localized_dt.utcoffset().total_seconds() / 3600.0
    except Exception: 
        pass
        
    return ymdhms_to_jd(y, m, d, h, mi, s) - (offset_hours / 24.0)

def utc_jd_to_dt_dict(jd_utc, tz_name):
    """Converts a UTC Julian Day back into a localized datetime dictionary."""
    local_tz = pytz.timezone(tz_name)
    d_temp = jd_to_ymdhms(jd_utc)
    y = d_temp['year']
    
    offset_hours = 0.0
    try:
        if 1 <= y <= 9999: 
            dt_utc = datetime.datetime(y, d_temp['month'], d_temp['day'], d_temp['hour'], d_temp['minute'], int(d_temp['second']))
            localized_dt = pytz.utc.localize(dt_utc).astimezone(local_tz)
            offset_hours = localized_dt.utcoffset().total_seconds() / 3600.0
        else: 
            fallback_dt = datetime.datetime(2000, 1, 1)
            offset_hours = local_tz.localize(fallback_dt).utcoffset().total_seconds() / 3600.0
    except Exception: 
        pass
        
    return jd_to_ymdhms(jd_utc + (offset_hours / 24.0))

def get_nakshatra(lon_deg):
    """Determines the Nakshatra, its Lord, and the Pada based on degrees."""
    naks = [
        "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra", 
        "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", 
        "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", 
        "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", 
        "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
    ]
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    
    nak_length = 360.0 / 27.0
    pada_length = 360.0 / 108.0
    
    nak_index = int(lon_deg / nak_length)
    nak_name = naks[nak_index]
    nak_lord = lords[nak_index % 9]
    nak_pada = int((lon_deg % nak_length) / pada_length) + 1
    
    return nak_name, nak_lord, nak_pada


# ==========================================
# EPHEMERIS CHART CALCULATOR ENGINE (FORWARD ONLY)
# ==========================================
class EphemerisEngine:
    def __init__(self):
        try:
            swe.set_ephe_path(GLOBAL_EPHE_PATH)
            print("[DEBUG - ASTRO_ENGINE] Ephemeris path successfully mapped.")
        except Exception as e:
            print(f"[DEBUG - ASTRO_ENGINE] Failed to set ephemeris path: {e}")

        # Safely wrap internal swisseph constants in getattr to completely prevent
        # AttributeError crashes on module instantiation regardless of swisseph version.
        self.ayanamsa_modes = {
            "Lahiri": getattr(swe, 'SIDM_LAHIRI', 1), 
            "True Lahiri (Chitrapaksha)": getattr(swe, 'SIDM_TRUE_CITRA', 27),
            "Raman": getattr(swe, 'SIDM_RAMAN', 3), 
            "Fagan/Bradley": getattr(swe, 'SIDM_FAGAN_BRADLEY', 0),
            "Krishnamurti (KP)": getattr(swe, 'SIDM_KRISHNAMURTI', 5),
            "True Revati": getattr(swe, 'SIDM_TRUE_REVATI', 28),
            "True Pushya": getattr(swe, 'SIDM_TRUE_PUSHYA', 29),
            "Suryasiddhanta": getattr(swe, 'SIDM_SURYASIDDHANTA', 0),
            "Yukteshwar": getattr(swe, 'SIDM_YUKTESHWAR', 7),
            "Usha/Shashi": getattr(swe, 'SIDM_USHASHASHI', getattr(swe, 'SIDM_USHA_SHASHI', 21)),
            "Bhasin": getattr(swe, 'SIDM_JN_BHASIN', getattr(swe, 'SIDM_BHASIN', 20))
        }
        self.current_ayanamsa = "True Lahiri (Chitrapaksha)"
        self.custom_vargas = {}
        self.transit_cache = {}

    def set_ayanamsa(self, name):
        if name in self.ayanamsa_modes and name != self.current_ayanamsa:
            self.current_ayanamsa = name
            self.transit_cache.clear()

    def set_custom_vargas(self, vargas):
        self.custom_vargas = vargas
        self.transit_cache.clear()

    def get_div_sign_and_lon(self, lon_deg, div_type):
        """
        Converts a D1 Longitude into a target Varga (Divisional) sign index and longitude.
        Strictly follows BPHS and pure float math boundaries.
        """
        lon_deg = lon_deg % 360.0
        
        sign_index = int(lon_deg / 30.0)
        deg_in_sign = lon_deg % 30.0
        
        if div_type in self.custom_vargas:
            rule = self.custom_vargas[div_type]
            if "logic" in rule and "divs" in rule:
                parts = rule["divs"]
                new_sign_idx = custom_vargas.calculate_new_sign(sign_index, deg_in_sign, rule)
                segment_length = 30.0 / parts
                part_num = int(deg_in_sign / segment_length)
                deg_rem = (deg_in_sign - (part_num * segment_length)) * parts
                return new_sign_idx, (new_sign_idx * 30.0) + deg_rem
                
            parts = rule.get("parts", 1)
            starts = rule.get("starts", [0]*12)
            segment_length = 30.0 / parts
            part_num = int(deg_in_sign / segment_length)
            new_sign_idx = (starts[sign_index] + part_num) % 12
            deg_rem = (deg_in_sign - (part_num * segment_length)) * parts
            return new_sign_idx, (new_sign_idx * 30.0) + deg_rem
            
        if div_type == "D1": 
            return sign_index, lon_deg
            
        if div_type == "D30":
            deg = deg_in_sign
            if sign_index % 2 == 0: 
                if deg < 5.0: new_sign, rem_deg = 0, (deg / 5.0) * 30.0
                elif deg < 10.0: new_sign, rem_deg = 10, ((deg - 5.0) / 5.0) * 30.0
                elif deg < 18.0: new_sign, rem_deg = 8, ((deg - 10.0) / 8.0) * 30.0
                elif deg < 25.0: new_sign, rem_deg = 2, ((deg - 18.0) / 7.0) * 30.0
                else: new_sign, rem_deg = 6, ((deg - 25.0) / 5.0) * 30.0
            else: 
                if deg < 5.0: new_sign, rem_deg = 1, (deg / 5.0) * 30.0
                elif deg < 12.0: new_sign, rem_deg = 5, ((deg - 5.0) / 7.0) * 30.0
                elif deg < 18.0: new_sign, rem_deg = 11, ((deg - 12.0) / 6.0) * 30.0
                elif deg < 25.0: new_sign, rem_deg = 9, ((deg - 18.0) / 7.0) * 30.0
                else: new_sign, rem_deg = 7, ((deg - 25.0) / 5.0) * 30.0
                    
            return new_sign, (new_sign * 30.0) + rem_deg

        div_map = {
            "D2": 2, "D3": 3, "D4": 4, "D5": 5, "D6": 6, "D7": 7,
            "D8": 8, "D9": 9, "D10": 10, "D11": 11, "D12": 12,
            "D16": 16, "D20": 20, "D24": 24, "D27": 27, "D40": 40,
            "D45": 45, "D60": 60
        }
        
        if div_type not in div_map:
            return sign_index, (sign_index * 30.0) + deg_in_sign

        divs = div_map[div_type]
        segment_length = 30.0 / divs
        
        part = int(deg_in_sign / segment_length)
        if part >= divs: part = divs - 1
        
        deg_rem = ((deg_in_sign - (part * segment_length)) / segment_length) * 30.0
        if deg_rem < 0: deg_rem = 0.0

        if div_type == "D2":
            if sign_index % 2 == 0: new_sign_idx = 4 if part == 0 else 3
            else: new_sign_idx = 3 if part == 0 else 4
        elif div_type == "D3": new_sign_idx = (sign_index + part * 4) % 12
        elif div_type == "D4": new_sign_idx = (sign_index + part * 3) % 12
        elif div_type == "D5":
            if sign_index % 2 == 0: new_sign_idx = [0, 10, 8, 2, 6][part]
            else: new_sign_idx = [1, 5, 11, 9, 7][part]
        elif div_type == "D6":
            start_sign = 0 if sign_index % 2 == 0 else 6 
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D7":
            start_sign = sign_index if sign_index % 2 == 0 else (sign_index + 6) % 12
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D8":
            start_sign = [0, 8, 4][sign_index % 3] 
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D9":
            start_sign = [0, 9, 6, 3][sign_index % 4]
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D10":
            start_sign = sign_index if sign_index % 2 == 0 else (sign_index + 8) % 12
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D11":
            start_sign = (12 - sign_index) % 12 
            new_sign_idx = (start_sign + part) % 12 
        elif div_type == "D12": new_sign_idx = (sign_index + part) % 12
        elif div_type == "D16":
            start_sign = [0, 4, 8][sign_index % 3]
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D20":
            start_sign = [0, 8, 4][sign_index % 3]
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D24":
            start_sign = 4 if sign_index % 2 == 0 else 3
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D27":
            start_sign = [0, 3, 6, 9][sign_index % 4]
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D40":
            start_sign = 0 if sign_index % 2 == 0 else 6
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D45":
            start_sign = [0, 4, 8][sign_index % 3]
            new_sign_idx = (start_sign + part) % 12
        elif div_type == "D60": new_sign_idx = (sign_index + part) % 12

        return new_sign_idx, (new_sign_idx * 30.0) + deg_rem

    def calculate_vedic_aspects(self, planets):
        aspects = []
        aspect_rules = {
            "Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7], 
            "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10], 
            "Rahu": [7], "Ketu": []
        }
        for p in planets:
            for count in aspect_rules.get(p["name"], []):
                target_house = (p["house"] + count - 2) % 12 + 1
                aspects.append({
                    "aspecting_planet": p["name"], "source_house": p["house"], 
                    "target_house": target_house, "aspect_count": count
                })
        return aspects

    def build_divisional_chart_from_raw(self, base_asc_lon, base_planets, div_type, d1_asc_sign_idx=None):
        asc_sign_idx, asc_div_lon = self.get_div_sign_and_lon(base_asc_lon, div_type)
        is_vargottama = (d1_asc_sign_idx == asc_sign_idx) if d1_asc_sign_idx is not None else False
            
        chart = {
            "ascendant": {
                "sign_index": asc_sign_idx, "sign_num": asc_sign_idx + 1, 
                "degree": asc_div_lon % 30.0, "div_lon": asc_div_lon, "vargottama": is_vargottama
            }, 
            "planets": []
        }
        
        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            ruler = SIGN_RULERS.get((asc_sign_idx + h - 1) % 12 + 1)
            if ruler: planet_lordships[ruler].append(h)

        for p_raw in base_planets:
            p_sign_idx, p_div_lon = self.get_div_sign_and_lon(p_raw["lon"], div_type)
            is_ex, is_ow, is_deb = get_dignities(p_raw["name"], p_sign_idx + 1, p_div_lon % 30.0)
            p_is_varg = (int(p_raw["lon"]/30.0) == p_sign_idx) if div_type != "D1" else False
                
            chart["planets"].append({
                "name": p_raw["name"], "sym": p_raw["sym"], "lon": p_div_lon, 
                "sign_index": p_sign_idx, "sign_num": p_sign_idx + 1,
                "deg_in_sign": p_div_lon % 30.0, "house": (p_sign_idx - asc_sign_idx) % 12 + 1, 
                "retro": p_raw["retro"], "exalted": is_ex, "debilitated": is_deb, 
                "own_sign": is_ow, "lord_of": planet_lordships.get(p_raw["name"], []),
                "is_ak": p_raw.get("is_ak", False), "nakshatra": p_raw.get("nakshatra", ""), 
                "nakshatra_lord": p_raw.get("nakshatra_lord", ""),
                "combust": False, "vargottama": p_is_varg
            })

        chart["aspects"] = self.calculate_vedic_aspects(chart["planets"])
        return chart

    def process_imported_json(self, json_data):
        try:
            d1_node = json_data["divisional_charts"]["D1"]
            asc_lon = (d1_node["ascendant"]["sign_index"] * 30.0) + d1_node["ascendant"]["degree_in_sign"]
            
            planets_raw = []
            for p in d1_node["planets"]:
                sym = p["name"][:2] if p["name"] not in ["Rahu", "Ketu"] else ("Ra" if p["name"]=="Rahu" else "Ke")
                planets_raw.append({
                    "name": p["name"], "sym": sym, 
                    "lon": p["sign_index"] * 30.0 + p.get("degree_in_sign", 0.0), 
                    "retro": p.get("is_retrograde", False), "is_ak": p.get("is_brightest_ak", False), 
                    "nakshatra": p.get("nakshatra", ""), "nakshatra_lord": p.get("nakshatra_lord", "")
                })
                
            base_chart = self.build_divisional_chart_from_raw(asc_lon, planets_raw, "D1")
            all_charts = {"D1": base_chart}
            
            standard_vargas = ["D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"]
            vargas_to_build = standard_vargas + list(self.custom_vargas.keys())
            
            for div in vargas_to_build:
                all_charts[div] = self.build_divisional_chart_from_raw(asc_lon, planets_raw, div, base_chart["ascendant"]["sign_index"])
            return all_charts
        except Exception as e: 
            print(f"[DEBUG - ASTRO_ENGINE] Error processing JSON: {e}")
            return None

    def search_transit_core(self, jd_start, lat, lon, body_name, direction, div_type, frozen_planets, target_sign_name="Any Rashi", stop_event=None):
        if not frozen_planets and target_sign_name == "Any Rashi":
            if body_name == "Ascendant":
                pr, nx = self.find_adjacent_ascendant_transits(jd_start, lat, lon, div_type)
                return nx if direction == 1 else pr
            else:
                pr, nx = self.find_adjacent_planet_transits(jd_start, body_name, div_type)
                return nx if direction == 1 else pr

        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        
        body_map = {
            "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, 
            "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, 
            "Venus": swe.VENUS, "Saturn": swe.SATURN, 
            "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE
        }

        def get_sign(j, b_name, target_div="D1"):
            if b_name == "Ascendant":
                _, ascmc = safe_houses_ex(j, lat, lon, b'P', calc_flag)
                return self.get_div_sign_and_lon(ascmc[0], target_div)[0]
            elif b_name == "Ketu":
                res, _ = safe_calc_ut(j, swe.TRUE_NODE, calc_flag)
                return self.get_div_sign_and_lon((res[0] + 180.0) % 360.0, target_div)[0]
            else:
                res, _ = safe_calc_ut(j, body_map[b_name], calc_flag)
                return self.get_div_sign_and_lon(res[0], target_div)[0]

        original_start_sign = get_sign(jd_start, body_name, div_type)
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        
        target_sign = None
        if target_sign_name and target_sign_name != "Any Rashi":
            target_sign = zodiac_names.index(target_sign_name)

        constrained_planets = {fp: {"target": f_info["sign_idx"], "div": f_info["div"]} for fp, f_info in frozen_planets.items()}
        if target_sign is not None: 
            constrained_planets[body_name] = {"target": target_sign, "div": div_type}
            
        must_leave_target = (target_sign is not None and original_start_sign == target_sign)

        def calc_max_leap(jd_check, d_dir):
            max_leap = 0
            for p, p_info in constrained_planets.items():
                curr_s = get_sign(jd_check, p, p_info["div"])
                if curr_s == p_info["target"]: continue
                dist = (curr_s - p_info["target"]) * d_dir % 12 if p in ["Rahu", "Ketu"] else (p_info["target"] - curr_s) * d_dir % 12
                safe_days_val = {"Saturn": 750, "Rahu": 450, "Ketu": 450, "Jupiter": 300, "Mars": 35, "Sun": 27, "Venus": 20, "Mercury": 15, "Moon": 2, "Ascendant": 0.05}.get(p, 0)
                div_factor = self.custom_vargas[p_info["div"]].get("parts", 1) if p_info["div"] in self.custom_vargas else (int(p_info["div"][1:]) if p_info["div"] != "D1" else 1)
                if 2 <= dist <= 11:
                    leap_calc = ((dist - 1.5) * safe_days_val) / div_factor
                    if leap_calc > max_leap: max_leap = leap_calc
            return max_leap

        step_map = {"Ascendant": 0.01, "Moon": 0.1, "Sun": 1.0, "Mercury": 1.0, "Venus": 1.0, "Mars": 2.0, "Jupiter": 5.0, "Saturn": 10.0, "Rahu": 10.0, "Ketu": 10.0}
        div_factor = self.custom_vargas[div_type].get("parts", 1) if div_type in self.custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1)
        step = step_map.get(body_name, 10.0) / div_factor
        inner_step = step
        
        for fp, f_info in frozen_planets.items():
            if fp != body_name: 
                f_div_factor = self.custom_vargas[f_info["div"]].get("parts", 1) if f_info["div"] in self.custom_vargas else (int(f_info["div"][1:]) if f_info["div"] != "D1" else 1)
                inner_step = min(inner_step, step_map.get(fp, 10.0) / f_div_factor)

        jd = jd_start + (0.001 * direction / div_factor)
        prev_sign = get_sign(jd_start - step * direction, body_name, div_type)
        
        while True:
            if stop_event and stop_event.is_set(): return None
            if jd < -50000000 or jd > 50000000: return None

            leap_days = calc_max_leap(jd, direction)
            if leap_days > 15: 
                jd += leap_days * direction
                prev_sign = get_sign(jd - step * direction, body_name, div_type)
                continue

            current_sign = get_sign(jd, body_name, div_type)
            if must_leave_target and current_sign != target_sign: must_leave_target = False
            
            transitioned_in = False
            if not must_leave_target:
                transitioned_in = (current_sign == target_sign and prev_sign != target_sign) if target_sign is not None else (current_sign != prev_sign and current_sign != original_start_sign)

            if transitioned_in:
                t1, t2 = jd - step * direction, jd
                for _ in range(20):
                    t_mid = (t1 + t2) / 2.0
                    m_sign = get_sign(t_mid, body_name, div_type)
                    is_mid_match = (m_sign == target_sign) if target_sign is not None else (m_sign != prev_sign and m_sign != original_start_sign)
                    if is_mid_match: t2 = t_mid
                    else: t1 = t_mid

                jd_inner, window_match = t2, False
                for _ in range(15000): 
                    if stop_event and stop_event.is_set(): return None
                    if target_sign is not None:
                        if get_sign(jd_inner, body_name, div_type) != target_sign: break
                    else:
                        if get_sign(jd_inner, body_name, div_type) != current_sign: break
                        
                    all_frozen_match = True
                    for fp_name, f_info in frozen_planets.items():
                        if fp_name != body_name and get_sign(jd_inner, fp_name, f_info["div"]) != f_info["sign_idx"]:
                            all_frozen_match = False
                            break
                    if all_frozen_match:
                        found_jd, window_match = jd_inner, True
                        break
                    jd_inner += inner_step * direction

                if window_match:
                    t1_final, t2_final = found_jd - inner_step * direction, found_jd
                    for _ in range(20):
                        t_mid = (t1_final + t2_final) / 2.0
                        target_match = (get_sign(t_mid, body_name, div_type) == target_sign) if target_sign is not None else (get_sign(t_mid, body_name, div_type) == current_sign)
                        frozen_match = True
                        for fp_name, f_info in frozen_planets.items():
                            if fp_name != body_name and get_sign(t_mid, fp_name, f_info["div"]) != f_info["sign_idx"]:
                                frozen_match = False
                                break
                        if target_match and frozen_match: t2_final = t_mid
                        else: t1_final = t_mid
                    return float(t2_final)
                else: 
                    jd = jd_inner
                    current_sign = get_sign(jd_inner, body_name, div_type)
                    
            prev_sign = current_sign
            jd += step * direction

    def get_ascendant_sign(self, jd_utc, lat, lon, div_type="D1"):
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        houses_res = safe_houses_ex(jd_utc, lat, lon, b'P', swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        return self.get_div_sign_and_lon(houses_res[1][0], div_type)[0]

    def find_adjacent_ascendant_transits(self, jd_utc, lat, lon, div_type="D1"):
        orig_sign = self.get_ascendant_sign(jd_utc, lat, lon, div_type)
        cache_key = ('asc', lat, lon, div_type, self.current_ayanamsa)
        
        if cache_key in self.transit_cache:
            c = self.transit_cache[cache_key]
            if c['prev'] < jd_utc < c['next'] and c['orig_sign'] == orig_sign:
                return c['prev'], c['next']
                
        div_factor = self.custom_vargas[div_type].get("parts", 1) if div_type in self.custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1)
        step = 0.01 / div_factor
        
        jd_next = jd_utc + step * 300
        for i in range(1, 301):
            if self.get_ascendant_sign(jd_utc + step * i, lat, lon, div_type) != orig_sign:
                jd_next = jd_utc + step * i
                break
                
        t1, t2 = jd_next - step, jd_next
        for _ in range(15):
            tm = (t1 + t2) / 2.0
            if self.get_ascendant_sign(tm, lat, lon, div_type) == orig_sign: t1 = tm
            else: t2 = tm
        jd_next_exact = t2
        
        jd_prev = jd_utc - step * 300
        for i in range(1, 301):
            if self.get_ascendant_sign(jd_utc - step * i, lat, lon, div_type) != orig_sign:
                jd_prev = jd_utc - step * i
                break
                
        t1_prev, t2 = jd_prev, jd_prev + step
        for _ in range(15):
            tm = (t1_prev + t2) / 2.0
            if self.get_ascendant_sign(tm, lat, lon, div_type) == orig_sign: t2 = tm
            else: t1_prev = tm
            
        self.transit_cache[cache_key] = {'prev': t1_prev, 'next': jd_next_exact, 'orig_sign': orig_sign}
        return t1_prev, jd_next_exact

    def find_adjacent_planet_transits(self, jd_utc, planet_name, div_type="D1"):
        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}
        if planet_name not in body_map: return jd_utc, jd_utc
            
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        
        def get_s(j): 
            if planet_name != "Ketu":
                res = safe_calc_ut(j, body_map[planet_name], swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
                return self.get_div_sign_and_lon(res[0][0], div_type)[0]
            else:
                res = safe_calc_ut(j, swe.TRUE_NODE, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
                return self.get_div_sign_and_lon((res[0][0] + 180.0) % 360.0, div_type)[0]
        
        orig_sign = get_s(jd_utc)
        cache_key = ('planet', planet_name, div_type, self.current_ayanamsa)
        
        if cache_key in self.transit_cache:
            c = self.transit_cache[cache_key]
            if c['prev'] < jd_utc < c['next'] and c['orig_sign'] == orig_sign:
                return c['prev'], c['next']
                
        base_step = {"Moon": 0.05, "Sun": 0.5, "Mercury": 0.5, "Venus": 0.5, "Mars": 1.0, "Jupiter": 2.0, "Saturn": 5.0, "Rahu": 5.0, "Ketu": 5.0}.get(planet_name, 1.0)
        div_factor = self.custom_vargas[div_type].get("parts", 1) if div_type in self.custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1)
        step = base_step / div_factor
        
        jd_next = jd_utc + step * 4000
        for i in range(1, 4001):
            if get_s(jd_utc + step * i) != orig_sign:
                jd_next = jd_utc + step * i
                break
                
        t1, t2 = jd_next - step, jd_next
        for _ in range(12):
            tm = (t1 + t2) / 2.0
            if get_s(tm) == orig_sign: t1 = tm
            else: t2 = tm
        exact_next = t2
        
        jd_prev = jd_utc - step * 4000
        for i in range(1, 4001):
            if get_s(jd_utc - step * i) != orig_sign:
                jd_prev = jd_utc - step * i
                break
                
        t1_prev, t2 = jd_prev, jd_prev + step
        for _ in range(12):
            tm = (t1_prev + t2) / 2.0
            if get_s(tm) == orig_sign: t2 = tm
            else: t1_prev = tm
            
        self.transit_cache[cache_key] = {'prev': t1_prev, 'next': exact_next, 'orig_sign': orig_sign}
        return t1_prev, exact_next

    def calculate_vimshottari_dasha(self, birth_jd, moon_lon, target_jd, forecast_start_jd=None, forecast_end_jd=None):
        lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
        years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
        total_mas = int(round(moon_lon * 3600000.0))
        nak_len = 48000000 
        lord_idx = (total_mas // nak_len) % 9
        
        passed_years = ((total_mas % nak_len) / float(nak_len)) * years[lord_idx]
        dasha_start_jd = birth_jd - (passed_years * 365.2421904)

        def get_node(t_jd):
            elapsed_years = (t_jd - dasha_start_jd) / 365.2421904
            rem = elapsed_years % 120.0
            c_start = dasha_start_jd + (elapsed_years - rem) * 365.2421904
            
            seq, c_lord, c_dur = [], lord_idx, 120.0
            for _ in range(5):
                y_acc = 0.0
                for i in range(9):
                    l_idx = (c_lord + i) % 9
                    d = c_dur * years[l_idx] / 120.0
                    if i == 8 or rem < y_acc + d:
                        seq.append(lords[l_idx])
                        c_start += y_acc * 365.2421904
                        rem -= y_acc
                        c_lord = l_idx
                        c_dur = d
                        break
                    y_acc += d
            return seq, c_start, c_start + c_dur * 365.2421904

        current_seq, _, _ = get_node(target_jd)
        pran_list = []
        if forecast_start_jd and forecast_end_jd:
            jd_iter = forecast_start_jd
            while jd_iter < forecast_end_jd:
                seq, s_jd, e_jd = get_node(jd_iter)
                if not seq: break
                pran_list.append({"sequence": seq, "start_jd": s_jd, "end_jd": e_jd})
                jd_iter = e_jd + 0.00069 
        return {"current_sequence": current_seq, "pran_forecast": pran_list}

    def get_dasha_export_list(self, birth_jd, moon_lon):
        lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
        years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
        total_mas = int(round(moon_lon * 3600000.0))
        nak_len = 48000000 
        lord_idx = (total_mas // nak_len) % 9
        passed_years = ((total_mas % nak_len) / float(nak_len)) * years[lord_idx]
        dasha_start_jd = birth_jd - (passed_years * 365.2421904)
        
        export_list = []
        y_acc1 = 0.0
        for i in range(9):
            l1 = (lord_idx + i) % 9
            d1 = years[l1]
            y_acc2 = 0.0
            for j in range(9):
                l2 = (l1 + j) % 9
                d2 = d1 * years[l2] / 120.0
                y_acc3 = 0.0
                for k in range(9):
                    l3 = (l2 + k) % 9
                    d3 = d2 * years[l3] / 120.0
                    pd_start = dasha_start_jd + (y_acc1 + y_acc2 + y_acc3) * 365.2421904
                    pd_end = pd_start + d3 * 365.2421904
                    y_acc3 += d3
                    
                    if pd_end <= birth_jd: continue
                    age_start = max(0.0, (pd_start - birth_jd) / 365.2421904)
                    age_end = (pd_end - birth_jd) / 365.2421904
                    if age_start > 120.0: return export_list
                    export_list.append(f"age {age_start:.2f}-{age_end:.2f} years dasha influence {lords[l1].lower()} {lords[l2].lower()} {lords[l3].lower()}")
                y_acc2 += d2
            y_acc1 += d1
        return export_list

    def get_panchang(self, jd_utc, lat, lon):
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

        moon_res = safe_calc_ut(jd_utc, swe.MOON, calc_flag)
        sun_res = safe_calc_ut(jd_utc, swe.SUN, calc_flag)
        moon_lon, sun_lon = moon_res[0][0], sun_res[0][0]

        nak_name, nak_lord, nak_pada = get_nakshatra(moon_lon)
        diff = (moon_lon - sun_lon) % 360.0
        paksha = "Shukla" if diff < 180 else "Krishna"
        
        tithi_num = (int(diff / 12.0) % 15) + 1
        tithi_names = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]
        tithi_name = "Purnima" if paksha == "Shukla" else "Amavasya" if tithi_num == 15 else tithi_names[tithi_num - 1]

        sunrise_jd, sunset_jd = None, None
        try:
            # FIX: Removed the empty string. Passed exactly 4 arguments: jd, body, rsmi, geopos.
            res_rise = safe_rise_trans(jd_utc - 0.5, swe.SUN, 1+256, (lon, lat, 0.0))
            sunrise_jd = res_rise[1][0] if len(res_rise) > 1 and type(res_rise[1]) is tuple else res_rise[0]
            
            # FIX: Removed the empty string. Passed exactly 4 arguments: jd, body, rsmi, geopos.
            res_set = safe_rise_trans(sunrise_jd, swe.SUN, 2+256, (lon, lat, 0.0))
            sunset_jd = res_set[1][0] if len(res_set) > 1 and type(res_set[1]) is tuple else res_set[0]
        except Exception as e: 
            print(f"[DEBUG - ASTRO_ENGINE] Panchang rise/set logic issue: {e}")

        return {"nakshatra": nak_name, "nakshatra_lord": nak_lord, "nakshatra_pada": nak_pada, "tithi": tithi_name, "paksha": paksha, "sunrise_jd": sunrise_jd, "sunset_jd": sunset_jd, "moon_lon": moon_lon, "sun_lon": sun_lon}

    def calculate_chart(self, dt, lat: float, lon: float, tz_name: str, real_now_jd: float = None, transit_div: str = "D1", transit_planet: str = "Sun"):
        if isinstance(dt, dict) and 'year' in dt: jd_utc = dt_dict_to_utc_jd(dt, tz_name)
        elif isinstance(dt, dict) and 'jd' in dt: jd_utc = float(dt['jd'])
        else:
            try:
                local_tz = pytz.timezone(tz_name)
                dt_utc = (local_tz.localize(dt) if dt.tzinfo is None else dt).astimezone(pytz.utc)
                jd_utc = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0)
            except Exception: jd_utc = dt_dict_to_utc_jd({'year': 2000, 'month': 1, 'day': 1}, tz_name)

        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        
        houses_res = safe_houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        asc_deg = houses_res[1][0]
        asc_sign_index = int(asc_deg / 30)
        asc_nak_name, asc_nak_lord, asc_nak_pada = get_nakshatra(asc_deg)
        
        chart_data = {
            "ascendant": {"degree": asc_deg, "sign_index": asc_sign_index, "sign_num": asc_sign_index + 1, "nakshatra": asc_nak_name, "nakshatra_lord": asc_nak_lord, "nakshatra_pada": asc_nak_pada}, 
            "planets": []
        }
        
        chart_data["prev_asc_jd"], chart_data["next_asc_jd"] = self.find_adjacent_ascendant_transits(jd_utc, lat, lon, transit_div)
        chart_data["prev_p_jd"], chart_data["next_p_jd"] = self.find_adjacent_planet_transits(jd_utc, transit_planet, transit_div)
        chart_data["current_jd"] = jd_utc

        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            ruler = SIGN_RULERS.get((asc_sign_index + h - 1) % 12 + 1)
            if ruler: planet_lordships[ruler].append(h)

        body_list = [("Sun", "Su", swe.SUN), ("Moon", "Mo", swe.MOON), ("Mars", "Ma", swe.MARS), ("Mercury", "Me", swe.MERCURY), ("Jupiter", "Ju", swe.JUPITER), ("Venus", "Ve", swe.VENUS), ("Saturn", "Sa", swe.SATURN), ("Rahu", "Ra", swe.TRUE_NODE)]
        
        for name, sym, body_id in body_list:
            res, _ = safe_calc_ut(jd_utc, body_id, calc_flag)
            lon_deg, speed = res[0], res[3]
            p_sign_idx = int(lon_deg / 30)
            nak_name, nak_lord, nak_pada = get_nakshatra(lon_deg)
            is_ex, is_ow, is_deb = get_dignities(name, p_sign_idx + 1, lon_deg % 30.0)
            
            is_retro = True if name == "Rahu" else (speed < 0 if name not in ["Sun", "Moon", "Ketu"] else False)
            chart_data["planets"].append({
                "name": name, "sym": sym, "lon": lon_deg, "sign_index": p_sign_idx, "sign_num": p_sign_idx + 1, "deg_in_sign": lon_deg % 30.0, 
                "house": (p_sign_idx - asc_sign_index) % 12 + 1, "retro": is_retro, "exalted": is_ex, "debilitated": is_deb, "own_sign": is_ow, 
                "lord_of": planet_lordships.get(name, []), "nakshatra": nak_name, "nakshatra_lord": nak_lord, "nakshatra_pada": nak_pada
            })

        rahu_lon = next((p["lon"] for p in chart_data["planets"] if p["name"] == "Rahu"), 0.0)
        ketu_lon = (rahu_lon + 180.0) % 360.0
        ketu_sign_idx = int(ketu_lon / 30)
        ketu_nak_name, ketu_nak_lord, ketu_nak_pada = get_nakshatra(ketu_lon)
        is_ex, is_ow, is_deb = get_dignities("Ketu", ketu_sign_idx + 1, ketu_lon % 30)
        
        chart_data["planets"].append({
            "name": "Ketu", "sym": "Ke", "lon": ketu_lon, "sign_index": ketu_sign_idx, "sign_num": ketu_sign_idx + 1, "deg_in_sign": ketu_lon % 30, 
            "house": (ketu_sign_idx - asc_sign_index) % 12 + 1, "retro": True, "exalted": is_ex, "debilitated": is_deb, "own_sign": is_ow, "lord_of": [],
            "nakshatra": ketu_nak_name, "nakshatra_lord": ketu_nak_lord, "nakshatra_pada": ketu_nak_pada
        })

        sun_lon = next((p["lon"] for p in chart_data["planets"] if p["name"] == "Sun"), None)
        combust_rules = {"Moon": {"dir": 12, "retro": 12}, "Mars": {"dir": 17, "retro": 17}, "Mercury": {"dir": 14, "retro": 12}, "Jupiter": {"dir": 11, "retro": 11}, "Venus": {"dir": 10, "retro": 8}, "Saturn": {"dir": 15, "retro": 15}}
        
        for p in chart_data["planets"]:
            p["combust"] = False
            if sun_lon is not None and p["name"] in combust_rules:
                dist = abs(sun_lon - p["lon"])
                if dist > 180.0: dist = 360.0 - dist
                if dist <= combust_rules[p["name"]]["retro" if p.get("retro") else "dir"]:
                    p["combust"] = True

        valid_ak = [p for p in chart_data["planets"] if p["name"] not in ["Rahu", "Ketu"]]
        if valid_ak:
            ak_name = max(valid_ak, key=lambda x: x["deg_in_sign"])["name"]
            for p in chart_data["planets"]: p["is_ak"] = (p["name"] == ak_name)

        moon_p = next((p for p in chart_data["planets"] if p["name"] == "Moon"), None)
        if moon_p:
            dasha_calc = self.calculate_vimshottari_dasha(jd_utc, moon_p["lon"], real_now_jd if real_now_jd else jd_utc)
            chart_data["dasha_sequence"] = dasha_calc["current_sequence"] or []

        chart_data["aspects"] = self.calculate_vedic_aspects(chart_data["planets"])
        
        panchang = self.get_panchang(jd_utc, lat, lon)
        if panchang["sunrise_jd"]:
            dt_dict = utc_jd_to_dt_dict(panchang['sunrise_jd'], tz_name)
            panchang["sunrise_str"] = f"{dt_dict['hour']:02d}:{dt_dict['minute']:02d}"
        else: panchang["sunrise_str"] = "N/A"
            
        if panchang["sunset_jd"]:
            dt_dict = utc_jd_to_dt_dict(panchang['sunset_jd'], tz_name)
            panchang["sunset_str"] = f"{dt_dict['hour']:02d}:{dt_dict['minute']:02d}"
        else: panchang["sunset_str"] = "N/A"
            
        chart_data["panchang"] = panchang
        return chart_data

    def compute_divisional_chart(self, base_chart, div_type):
        chart = copy.deepcopy(base_chart)
        asc_d1_sign = chart["ascendant"]["sign_index"]
        d1_lon = (asc_d1_sign * 30.0) + (chart["ascendant"]["degree"] % 30.0)
        new_asc_sign_index, new_asc_div_lon = self.get_div_sign_and_lon(d1_lon, div_type)
        
        chart["ascendant"].update({"sign_index": new_asc_sign_index, "sign_num": new_asc_sign_index + 1, "degree": new_asc_div_lon, "div_lon": new_asc_div_lon, "vargottama": (asc_d1_sign == new_asc_sign_index) and (div_type != "D1")})
        
        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            ruler = SIGN_RULERS.get((new_asc_sign_index + h - 1) % 12 + 1)
            if ruler: planet_lordships[ruler].append(h)

        for p in chart["planets"]:
            p_d1_sign = p["sign_index"]
            new_sign_idx, new_div_lon = self.get_div_sign_and_lon(p["lon"], div_type)
            is_ex, is_ow, is_deb = get_dignities(p["name"], new_sign_idx + 1, new_div_lon % 30.0)
            
            p.update({"sign_index": new_sign_idx, "sign_num": new_sign_idx + 1, "lon": new_div_lon, "div_lon": new_div_lon, "deg_in_sign": new_div_lon % 30.0, "house": (new_sign_idx - new_asc_sign_index) % 12 + 1, "exalted": is_ex, "debilitated": is_deb, "own_sign": is_ow, "lord_of": planet_lordships.get(p["name"], []), "vargottama": (p_d1_sign == new_sign_idx) and (div_type != "D1")})
            if div_type != "D1": p["combust"] = False
            
        chart["aspects"] = self.calculate_vedic_aspects(chart["planets"])
        return chart