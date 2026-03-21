#astro_engine.py

import swisseph as swe,datetime,pytz,time,math,copy

# -------------------------
# GLOBAL ASTROLOGICAL RULES
# -------------------------
EXALTATION_RULES = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
DEBILITATION_RULES = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
SIGN_RULERS = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}

def get_dignities(p_name, sign_num, deg_in_sign):
    """Calculates Exaltation, Own Sign, and Debilitation logically to prevent redundancy."""
    is_own = (SIGN_RULERS.get(sign_num) == p_name)
    is_debilitated = (sign_num == DEBILITATION_RULES.get(p_name))
    
    if p_name == "Moon" and sign_num == 2:
        is_exalted = (deg_in_sign <= 3.0); is_own = not is_exalted
    elif p_name == "Mercury" and sign_num == 6:
        is_exalted = (deg_in_sign <= 15.0); is_own = not is_exalted
    else:
        is_exalted = (sign_num == EXALTATION_RULES.get(p_name))
        
    if p_name == "Moon" and sign_num == 8:
        is_debilitated = (deg_in_sign <= 3.0)
    elif p_name == "Mercury" and sign_num == 12:
        is_debilitated = (deg_in_sign <= 15.0)
        
    return is_exalted, is_own, is_debilitated

# -------------------------
# SWISSEPH SAFE WRAPPERS
# -------------------------
def fallback_ayanamsa(jd):
    T = (jd - 2451545.0) / 36525.0
    return (23.85 + 1.396 * T) % 360.0

def fallback_planet_calc(jd, body_name):
    T = (jd - 2451545.0) / 36525.0
    elements = {
        "Sun": (280.46646, 36000.76983), "Moon": (218.3165, 481267.8813),
        "Mars": (355.4533, 19140.3026), "Mercury": (252.2503, 149472.6741),
        "Jupiter": (34.40438, 3034.9057), "Venus": (181.9791, 58517.8153),
        "Saturn": (50.07744, 1222.1136), "Rahu": (125.0445, -1934.13626)
    }
    if body_name in elements:
        L0, L1 = elements[body_name]
        return ((L0 + L1 * T) % 360.0, 0.0, 0.0, L1/36525.0)
    return (0.0, 0.0, 0.0, 0.0)

def fallback_ascendant(jd, lat, lon):
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
    try: return swe.calc_ut(jd, body, flag)
    except Exception:
        try: return swe.calc_ut(jd, body, (flag & ~swe.FLG_SWIEPH) | swe.FLG_MOSEPH)
        except Exception:
            body_lookup = {swe.SUN: "Sun", swe.MOON: "Moon", swe.MARS: "Mars", swe.MERCURY: "Mercury", swe.JUPITER: "Jupiter", swe.VENUS: "Venus", swe.SATURN: "Saturn", swe.TRUE_NODE: "Rahu"}
            res = fallback_planet_calc(jd, body_lookup.get(body, ""))
            if flag & swe.FLG_SIDEREAL: res = ((res[0] - fallback_ayanamsa(jd)) % 360.0, res[1], res[2], res[3])
            return res, None

def safe_houses_ex(jd, lat, lon, hsys, flag):
    try: return swe.houses_ex(jd, lat, lon, hsys, flag)
    except Exception:
        try: return swe.houses_ex(jd, lat, lon, hsys, (flag & ~swe.FLG_SWIEPH) | swe.FLG_MOSEPH)
        except Exception:
            asc_sid = (fallback_ascendant(jd, lat, lon) - fallback_ayanamsa(jd)) % 360.0 if flag & swe.FLG_SIDEREAL else fallback_ascendant(jd, lat, lon)
            return (tuple([0.0]*13), (asc_sid, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

def safe_rise_trans(jd, body, starname, epheflag, rsmi, geopos, atpress, attemp):
    try: return swe.rise_trans(jd, body, starname, epheflag, rsmi, geopos, atpress, attemp)
    except Exception: return swe.rise_trans(jd, body, starname, (epheflag & ~swe.FLG_SWIEPH) | swe.FLG_MOSEPH, rsmi, geopos, atpress, attemp)

def ymdhms_to_jd(year, month, day, hour=0, minute=0, second=0.0, gregorian=True):
    day_frac = (hour + minute / 60.0 + second / 3600.0) / 24.0
    D, Y, M = day + day_frac, year, month
    if M <= 2: Y -= 1; M += 12
    A = math.floor(Y / 100.0)
    B = 2 - A + math.floor(A / 4.0) if gregorian else 0
    return float(math.floor(365.25 * (Y + 4716)) + math.floor(30.6001 * (M + 1)) + D + B - 1524.5)

def jd_to_ymdhms(jd, gregorian=True):
    Z, F = math.floor(jd + 0.5), (jd + 0.5) - math.floor(jd + 0.5)
    if gregorian:
        alpha = math.floor((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - math.floor(alpha / 4.0)
    else: A = Z
    B = A + 1524
    C = math.floor((B - 122.1) / 365.25)
    D = math.floor(365.25 * C)
    E = math.floor((B - D) / 30.6001)
    day_decimal = B - D - math.floor(30.6001 * E) + F
    day, total_seconds = int(math.floor(day_decimal)), (day_decimal - int(math.floor(day_decimal))) * 86400.0
    month = int(E - 1) if E < 14 else int(E - 13)
    year = int(C - 4716) if month > 2 else int(C - 4715)
    hour = int(total_seconds // 3600)
    minute = int((total_seconds % 3600) // 60)
    return {'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute, 'second': total_seconds - hour * 3600 - minute * 60}

def dt_dict_to_utc_jd(dt_dict, tz_name):
    y, m, d = dt_dict['year'], dt_dict.get('month', 1), dt_dict.get('day', 1)
    h, mi, s = dt_dict.get('hour', 0), dt_dict.get('minute', 0), dt_dict.get('second', 0.0)
    offset_hours = 0.0
    try:
        if 1 <= y <= 9999: offset_hours = pytz.timezone(tz_name).localize(datetime.datetime(y, m, d, h, mi, int(s))).utcoffset().total_seconds() / 3600.0
        else: offset_hours = pytz.timezone(tz_name).localize(datetime.datetime(2000, 1, 1)).utcoffset().total_seconds() / 3600.0
    except: pass
    return ymdhms_to_jd(y, m, d, h, mi, s) - (offset_hours / 24.0)

def utc_jd_to_dt_dict(jd_utc, tz_name):
    local_tz = pytz.timezone(tz_name)
    d_temp = jd_to_ymdhms(jd_utc)
    y, offset_hours = d_temp['year'], 0.0
    try:
        if 1 <= y <= 9999: offset_hours = pytz.utc.localize(datetime.datetime(y, d_temp['month'], d_temp['day'], d_temp['hour'], d_temp['minute'], int(d_temp['second']))).astimezone(local_tz).utcoffset().total_seconds() / 3600.0
        else: offset_hours = local_tz.localize(datetime.datetime(2000, 1, 1)).utcoffset().total_seconds() / 3600.0
    except: pass
    return jd_to_ymdhms(jd_utc + (offset_hours / 24.0))

def get_nakshatra(lon_deg):
    naks = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    return naks[int(lon_deg / (360.0 / 27.0))], lords[int(lon_deg / (360.0 / 27.0)) % 9], int((lon_deg % (360.0 / 27.0)) / (360.0 / 108.0)) + 1

# ==========================================
# ADVANCED METADATA COMPUTATION
# ==========================================
def assign_functional_nature(planets):
    for p in planets:
        if p["name"] in ["Rahu", "Ketu"]:
            p["func_color"], p["func_label"] = "#7f8c8d", "Neutral (Node)"
            continue
        lordships = p.get("lord_of", [])
        if any(h in [4,7,10] for h in lordships) and any(h in [1,5,9] for h in lordships): color, label = "#FFD700", "Yoga Karaka (Gold)"
        elif any(h in [1,5,9] for h in lordships): color, label = "#27ae60", "Functional Benefic (Trine)"
        elif any(h in [3,11] for h in lordships): color, label = "#c0392b" if any(h in [6,8,12] for h in lordships) else "#f1c40f", "Functional Malefic" if any(h in [6,8,12] for h in lordships) else "Mixed/Opportunistic"
        elif any(h in [6,8,12] for h in lordships): color, label = "#c0392b", "Functional Malefic"
        elif any(h in [4,7,10] for h in lordships): color, label = "#2980b9", "Situational/Neutral (Kendra)"
        else: color, label = "#7f8c8d", "Neutral"
        p["func_color"], p["func_label"] = color, label

def assign_afflictions(chart_data):
    """Calculates Afflictions (by malefics) and Protections (by benefics) via conjunctions and aspects."""
    malefics = {"Sun", "Mars", "Saturn", "Rahu", "Ketu"}
    benefics = {"Moon", "Mercury", "Jupiter", "Venus"}
    aspects = chart_data.get("aspects", [])
    
    for p in chart_data["planets"]:
        # Afflictions
        conj_m = [other["name"] for other in chart_data["planets"] if other["sign_index"] == p["sign_index"] and other["name"] != p["name"] and other["name"] in malefics]
        asp_m = [asp["aspecting_planet"] for asp in aspects if asp["target_house"] == p["house"] and asp["aspecting_planet"] in malefics and asp["aspecting_planet"] != p["name"]]
        afflictors = list(set(conj_m + asp_m))
        p["afflicted"] = bool(afflictors)
        p["afflicting_bodies"] = afflictors
        
        # Protections (Blessings)
        conj_b = [other["name"] for other in chart_data["planets"] if other["sign_index"] == p["sign_index"] and other["name"] != p["name"] and other["name"] in benefics]
        asp_b = [asp["aspecting_planet"] for asp in aspects if asp["target_house"] == p["house"] and asp["aspecting_planet"] in benefics and asp["aspecting_planet"] != p["name"]]
        protectors = list(set(conj_b + asp_b))
        p["protected"] = bool(protectors)
        p["protecting_bodies"] = protectors

def compute_house_metadata(chart_data):
    chart_data["houses_info"] = {}
    aspect_counts = {h: 0 for h in range(1, 13)}
    disp_map, p_house = {}, {}
    
    for p in chart_data["planets"]:
        if p["name"] not in ["Rahu", "Ketu"]:
            if ruler := SIGN_RULERS.get(p["sign_num"]): disp_map[p["name"]] = ruler
        p_house[p["name"]] = p["house"]
        
    for asp in chart_data.get("aspects", []): aspect_counts[asp["target_house"]] += 1

    regime_terminals, projection_hubs, convergence_hubs = set(), set(), set()
    for p_name in disp_map:
        visited, curr = [], p_name
        while curr not in visited and curr: visited.append(curr); curr = disp_map.get(curr)
        if curr: regime_terminals.update({p_house[p] for p in visited[visited.index(curr):] if p in p_house})

    for h_num in range(1, 13):
        if len({asp["target_house"] for asp in chart_data.get("aspects", []) if asp["source_house"] == h_num}) >= 3: projection_hubs.add(h_num)
        influences = {p["name"] for p in chart_data["planets"] if p["house"] == h_num} | {asp["aspecting_planet"] for asp in chart_data.get("aspects", []) if asp["target_house"] == h_num}
        if len(influences) >= 4: convergence_hubs.add(h_num)
            
    for h_num in range(1, 13):
        sign_num = (chart_data["ascendant"]["sign_index"] + h_num - 1) % 12 + 1
        v_color, v_width, v_vitality = "#BDC3C7", 1.0, "Background Scenery (Neutral)"
        if lord_p := next((p for p in chart_data["planets"] if p["name"] == SIGN_RULERS.get(sign_num)), None):
            is_strong = lord_p.get("exalted", False) or lord_p.get("own_sign", False)
            in_dusthana, in_kendra_trikona = lord_p.get("house", 1) in [6, 8, 12], lord_p.get("house", 1) in [1, 4, 5, 7, 9, 10]
            if is_strong and not in_dusthana and not lord_p.get("combust", False): v_color, v_width, v_vitality = "#27ae60", 3.5, "Life Engine (Powerful Lord)"
            elif is_strong and in_dusthana: v_color, v_width, v_vitality = "#e67e22", 3.5, "Plot Twist (Strong Lord in Dusthana)"
            elif lord_p.get("debilitated", False) and in_kendra_trikona: v_color, v_width, v_vitality = "#e67e22", 3.5, "Plot Twist (Debilitated Lord in Kendra/Trine)"
            elif (lord_p.get("debilitated", False) and not in_kendra_trikona) or lord_p.get("combust", False): v_color, v_width, v_vitality = "#c0392b", 3.5, "Friction Zone (Compromised Lord)"
                    
        p_count = aspect_counts[h_num]
        p_color, p_width, p_label = ("#c0392b", 3.5, f"Overloaded ({p_count} influences)") if p_count >= 4 else ("#f1c40f", 3.0, f"Strong ({p_count} influences)") if p_count == 3 else ("#2980b9", 2.5, f"Moderately Active ({p_count} influences)") if p_count == 2 else ("#BDC3C7", 1.0, f"Quiet ({p_count} influences)")
        
        r_colors, r_labels = [], []
        if h_num in regime_terminals: r_colors.append("#DC143C"); r_labels.append("<b style='color:#DC143C;'>Dispositor Terminal (Crimson)</b>")
        if h_num in projection_hubs: r_colors.append("#005FFF"); r_labels.append("<b style='color:#005FFF;'>Aspect Projection Hub (Blue)</b>")
        if h_num in convergence_hubs: r_colors.append("#FFD700"); r_labels.append("<b style='color:#f39c12;'>Theme Convergence (Gold)</b>")

        chart_data["houses_info"][h_num] = {"vitality_color": v_color, "vitality_width": v_width, "vitality_label": v_vitality, "pressure_color": p_color, "pressure_width": p_width, "pressure_label": p_label, "pressure_count": p_count, "regime_colors": r_colors, "regime_labels": r_labels}


# ==========================================
# RECTIFICATION ENGINES
# ==========================================
def perform_rectification_search(params, result_queue, stop_event):
    try:
        swe.set_ephe_path('ephe')
        div_type, target_asc, target_planets = params['div_type'], params['target_asc'], params['target_planets']
        
        engine = EphemerisEngine()
        engine.set_ayanamsa(params['ayanamsa']); engine.set_custom_vargas(params.get('custom_vargas', {}))
        
        ayanamsa_modes = {"Lahiri": swe.SIDM_LAHIRI, "Raman": swe.SIDM_RAMAN, "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY}
        if params['ayanamsa'] in ayanamsa_modes: swe.set_sid_mode(ayanamsa_modes[params['ayanamsa']])
            
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}

        div_factor = params.get('custom_vargas', {}).get(div_type, {}).get("parts", 1) if div_type in params.get('custom_vargas', {}) else (int(div_type[1:]) if div_type != "D1" else 1)
        window_deg = 30.0 / div_factor
        max_speeds = {"Saturn": 0.25, "Jupiter": 0.35, "Rahu": 0.2, "Ketu": 0.2, "Mars": 1.2, "Sun": 1.2, "Venus": 1.8, "Mercury": 3.5, "Moon": 16.5, "Ascendant": 500.0}

        def get_sign_idx(jd, name):
            if name == "Ascendant":
                return engine.get_div_sign_and_lon(safe_houses_ex(jd, params['lat'], params['lon'], b'P', calc_flag)[1][0], div_type)[0]
            elif name == "Ketu":
                return engine.get_div_sign_and_lon((safe_calc_ut(jd, swe.TRUE_NODE, calc_flag)[0][0] + 180.0) % 360.0, div_type)[0]
            else:
                return engine.get_div_sign_and_lon(safe_calc_ut(jd, body_map[name], calc_flag)[0][0], div_type)[0]

        checks = [(p, target_asc if p == "Ascendant" else target_planets[p]) for p in ["Saturn", "Jupiter", "Rahu", "Ketu", "Mars", "Sun", "Venus", "Mercury", "Moon", "Ascendant"] if (p == "Ascendant" and target_asc is not None) or p in target_planets]
        origin_jd = dt_dict_to_utc_jd({'year': params['base_year'], 'month': 1, 'day': 1}, params['tz'])
        
        if params.get('search_mode', 'speed') == 'speed':
            search_range = params.get('search_range', 1000)
            start_range = params.get('start_range', 1)
            offsets = [0] if start_range == 1 else []
            offsets += [val for i in range(start_range, search_range + 1) for val in (i, -i)]
            
            for offset in offsets:
                year = params['base_year'] + offset
                if offset % 10 == 0: result_queue.put({"status": "progress", "msg": f"Cascade Scan: Year {year} (Range +/- {search_range})..."})
                
                windows = [(dt_dict_to_utc_jd({'year': year, 'month': 1, 'day': 1}, params['tz']), dt_dict_to_utc_jd({'year': year+1, 'month': 1, 'day': 1}, params['tz']))]

                for p_name, t_sign in checks:
                    if not windows: break 
                    safe_step = 0.5 / 1440.0 if p_name == "Ascendant" else max((window_deg / max_speeds.get(p_name, 1.0)) * 0.45, 1.0 / 1440.0)
                    new_windows = []
                    for w_start, w_end in windows:
                        t, in_match, m_start = w_start, False, None
                        while t <= w_end + safe_step:
                            if stop_event.is_set(): return
                            check_t = min(t, w_end)
                            is_match = (get_sign_idx(check_t, p_name) == t_sign)
                            if is_match and not in_match: m_start, in_match = check_t, True
                            elif not is_match and in_match: new_windows.append((m_start, check_t)); in_match = False
                            if t >= w_end: break
                            t += safe_step
                        if in_match: new_windows.append((m_start, w_end))
                    windows = new_windows

                if windows:
                    result_queue.put({"status": "success", "year": year, "blocks": [{"start": utc_jd_to_dt_dict(w[0], params['tz']), "end": utc_jd_to_dt_dict(w[1], params['tz']), "mid_jd": (w[0] + w[1]) / 2.0} for w in windows]})
                    return
            result_queue.put({"status": "phase1_failed", "message": f"Mathematical cascade scan finished +/- {search_range} years. No matches found.", "last_range": search_range})
            return

        elif params.get('search_mode') == 'brute':
            result_queue.put({"status": "progress", "msg": "Phase 2: Deep 1-Minute Brute-Force radiating outward..."})
            for step in range(int(1000 * 365.25 * 1440)):
                if stop_event.is_set(): return
                if step % 100000 == 0: result_queue.put({"status": "progress", "msg": f"Brute-Force: Scanned +/- {step / (365.25 * 1440):.2f} years radiating from origin..."})
                for sign_dir in (1, -1) if step > 0 else (1,):
                    jd = origin_jd + (step * sign_dir / 1440.0)
                    if all(get_sign_idx(jd, p_name) == t_sign for p_name, t_sign in checks):
                        target_dt = utc_jd_to_dt_dict(jd, params['tz'])
                        result_queue.put({"status": "success", "year": target_dt['year'], "blocks": [{"start": target_dt, "end": target_dt, "mid_jd": jd}]})
                        return
            result_queue.put({"status": "not_found", "message": "No matches found within +/- 1000 years."})
    except Exception as e: result_queue.put({"status": "error", "message": str(e)})

# ==========================================
# EPHEMERIS CHART CALCULATOR ENGINE
# ==========================================
class EphemerisEngine:
    def __init__(self):
        swe.set_ephe_path('ephe')
        self.ayanamsa_modes = {"Lahiri": swe.SIDM_LAHIRI, "Raman": swe.SIDM_RAMAN, "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY}
        self.current_ayanamsa = "Lahiri"
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
        total_mas = int(round(lon_deg * 3600000.0))
        sign_index = (total_mas // 108000000) % 12
        mas_in_sign = total_mas % 108000000
        deg_in_sign = mas_in_sign / 3600000.0
        
        if div_type in self.custom_vargas:
            rule = self.custom_vargas[div_type]
            
            # 1. Use the dynamic logic format from custom_vargas.py
            if "logic" in rule and "divs" in rule:
                import custom_vargas
                parts = rule["divs"]
                new_sign_idx = custom_vargas.calculate_new_sign(sign_index, deg_in_sign, rule)
                deg_remainder = (deg_in_sign % (30.0 / parts)) * parts
                return new_sign_idx, new_sign_idx * 30.0 + deg_remainder
                
            # 2. Fallback for the old legacy format
            parts = rule.get("parts", 1)
            starts = rule.get("starts", [0]*12)
            segment = min(int(deg_in_sign / (30.0 / parts)), parts - 1)
            return (starts[sign_index] + segment) % 12, ((starts[sign_index] + segment) % 12) * 30.0 + (deg_in_sign % (30.0 / parts)) * parts
        if div_type == "D1": return sign_index, lon_deg
        elif div_type == "D2": return (4 if deg_in_sign < 15.0 else 3) if (sign_index % 2 == 0) else (3 if deg_in_sign < 15.0 else 4), ((4 if deg_in_sign < 15.0 else 3) if (sign_index % 2 == 0) else (3 if deg_in_sign < 15.0 else 4)) * 30.0 + (deg_in_sign % 15.0) * 2.0
        elif div_type == "D3": return (sign_index + int(deg_in_sign / 10.0) * 4) % 12, ((sign_index + int(deg_in_sign / 10.0) * 4) % 12) * 30.0 + (deg_in_sign % 10.0) * 3.0
        elif div_type == "D4": return (sign_index + int(deg_in_sign / 7.5) * 3) % 12, ((sign_index + int(deg_in_sign / 7.5) * 3) % 12) * 30.0 + (deg_in_sign % 7.5) * 4.0
        elif div_type == "D5": return (sign_index + int(deg_in_sign / 6.0)) % 12, ((sign_index + int(deg_in_sign / 6.0)) % 12) * 30.0 + (deg_in_sign % 6.0) * 5.0
        elif div_type == "D6": return (sign_index + int(deg_in_sign / 5.0)) % 12, ((sign_index + int(deg_in_sign / 5.0)) % 12) * 30.0 + (deg_in_sign % 5.0) * 6.0
        elif div_type == "D7": return (((sign_index + 6) % 12 if sign_index % 2 != 0 else sign_index) + int(deg_in_sign / (30.0 / 7.0))) % 12, (((sign_index + 6) % 12 if sign_index % 2 != 0 else sign_index) + int(deg_in_sign / (30.0 / 7.0))) % 12 * 30.0 + (deg_in_sign % (30.0 / 7.0)) * 7.0
        elif div_type == "D8": return (sign_index + int(deg_in_sign / 3.75)) % 12, ((sign_index + int(deg_in_sign / 3.75)) % 12) * 30.0 + (deg_in_sign % 3.75) * 8.0
        elif div_type == "D9": return ([0, 9, 6, 3][sign_index % 4] + mas_in_sign // 12000000) % 12, (([0, 9, 6, 3][sign_index % 4] + mas_in_sign // 12000000) % 12) * 30.0 + ((mas_in_sign % 12000000) / 12000000.0) * 30.0
        elif div_type == "D10": return ((sign_index if sign_index % 2 == 0 else sign_index + 8) + mas_in_sign // 10800000) % 12, (((sign_index if sign_index % 2 == 0 else sign_index + 8) + mas_in_sign // 10800000) % 12) * 30.0 + ((mas_in_sign % 10800000) / 10800000.0) * 30.0
        elif div_type == "D11": return (sign_index + int(deg_in_sign / (30.0/11.0))) % 12, ((sign_index + int(deg_in_sign / (30.0/11.0))) % 12) * 30.0 + (deg_in_sign % (30.0/11.0)) * 11.0
        elif div_type == "D12": return (sign_index + int(deg_in_sign / 2.5)) % 12, ((sign_index + int(deg_in_sign / 2.5)) % 12) * 30.0 + (deg_in_sign % 2.5) * 12.0
        elif div_type == "D16": return ([0, 4, 8][sign_index % 3] + int(deg_in_sign / 1.875)) % 12, (([0, 4, 8][sign_index % 3] + int(deg_in_sign / 1.875)) % 12) * 30.0 + (deg_in_sign % 1.875) * 16.0
        elif div_type == "D20": return ([0, 8, 4][sign_index % 3] + mas_in_sign // 5400000) % 12, (([0, 8, 4][sign_index % 3] + mas_in_sign // 5400000) % 12) * 30.0 + ((mas_in_sign % 5400000) / 5400000.0) * 30.0
        elif div_type == "D24": return ((3 if sign_index % 2 != 0 else 4) + int(deg_in_sign / 1.25)) % 12, (((3 if sign_index % 2 != 0 else 4) + int(deg_in_sign / 1.25)) % 12) * 30.0 + (deg_in_sign % 1.25) * 24.0
        elif div_type == "D27": return ([0, 3, 6, 9][sign_index % 4] + int(deg_in_sign / (30.0/27.0))) % 12, (([0, 3, 6, 9][sign_index % 4] + int(deg_in_sign / (30.0/27.0))) % 12) * 30.0 + (deg_in_sign % (30.0/27.0)) * 27.0
        elif div_type == "D30":
            if sign_index % 2 == 0:
                if mas_in_sign < 18000000: return 0, (mas_in_sign / 18000000.0) * 30.0
                elif mas_in_sign < 36000000: return 10, 300.0 + ((mas_in_sign - 18000000) / 18000000.0) * 30.0
                elif mas_in_sign < 64800000: return 8, 240.0 + ((mas_in_sign - 36000000) / 28800000.0) * 30.0
                elif mas_in_sign < 90000000: return 2, 60.0 + ((mas_in_sign - 64800000) / 25200000.0) * 30.0
                else: return 6, 180.0 + ((mas_in_sign - 90000000) / 18000000.0) * 30.0
            else:
                if mas_in_sign < 18000000: return 1, 30.0 + (mas_in_sign / 18000000.0) * 30.0
                elif mas_in_sign < 43200000: return 5, 150.0 + ((mas_in_sign - 18000000) / 25200000.0) * 30.0
                elif mas_in_sign < 72000000: return 11, 330.0 + ((mas_in_sign - 43200000) / 28800000.0) * 30.0
                elif mas_in_sign < 90000000: return 9, 270.0 + ((mas_in_sign - 72000000) / 18000000.0) * 30.0
                else: return 7, 210.0 + ((mas_in_sign - 90000000) / 18000000.0) * 30.0
        elif div_type == "D40": return ((0 if sign_index % 2 == 0 else 6) + int(deg_in_sign / 0.75)) % 12, (((0 if sign_index % 2 == 0 else 6) + int(deg_in_sign / 0.75)) % 12) * 30.0 + (deg_in_sign % 0.75) * 40.0
        elif div_type == "D45": return ([0, 4, 8][sign_index % 3] + int(deg_in_sign / (30.0/45.0))) % 12, (([0, 4, 8][sign_index % 3] + int(deg_in_sign / (30.0/45.0))) % 12) * 30.0 + (deg_in_sign % (30.0/45.0)) * 45.0
        elif div_type == "D60": return (sign_index + mas_in_sign // 1800000) % 12, ((sign_index + mas_in_sign // 1800000) % 12) * 30.0 + ((mas_in_sign % 1800000) / 1800000.0) * 30.0
        return sign_index, sign_index * 30.0 + deg_in_sign

    def calculate_vedic_aspects(self, planets):
        aspects = []
        aspect_rules = {"Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7], "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10], "Rahu": [7], "Ketu": []}
        for p in planets:
            for count in aspect_rules.get(p["name"], []):
                aspects.append({"aspecting_planet": p["name"], "source_house": p["house"], "target_house": (p["house"] + count - 2) % 12 + 1, "aspect_count": count})
        return aspects

    def build_divisional_chart_from_raw(self, base_asc_lon, base_planets, div_type, d1_asc_sign_idx=None):
        asc_sign_idx, asc_div_lon = self.get_div_sign_and_lon(base_asc_lon, div_type)
        chart = {"ascendant": {"sign_index": asc_sign_idx, "sign_num": asc_sign_idx + 1, "degree": asc_div_lon % 30.0, "div_lon": asc_div_lon, "vargottama": (d1_asc_sign_idx == asc_sign_idx) if d1_asc_sign_idx is not None else False}, "planets": []}
        
        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            if ruler := SIGN_RULERS.get((asc_sign_idx + h - 1) % 12 + 1): planet_lordships[ruler].append(h)

        for p_raw in base_planets:
            p_sign_idx, p_div_lon = self.get_div_sign_and_lon(p_raw["lon"], div_type)
            is_ex, is_ow, is_deb = get_dignities(p_raw["name"], p_sign_idx + 1, p_div_lon % 30.0)
            
            chart["planets"].append({
                "name": p_raw["name"], "sym": p_raw["sym"], "lon": p_div_lon, "sign_index": p_sign_idx, "sign_num": p_sign_idx + 1,
                "deg_in_sign": p_div_lon % 30.0, "house": (p_sign_idx - asc_sign_idx) % 12 + 1, "retro": p_raw["retro"], 
                "exalted": is_ex, "debilitated": is_deb, "own_sign": is_ow, "lord_of": planet_lordships.get(p_raw["name"], []),
                "is_ak": p_raw.get("is_ak", False), "nakshatra": p_raw.get("nakshatra", ""), "nakshatra_lord": p_raw.get("nakshatra_lord", ""),
                "combust": False, "vargottama": (int(p_raw["lon"]/30.0) == p_sign_idx) if div_type != "D1" else False
            })

        chart["aspects"] = self.calculate_vedic_aspects(chart["planets"])
        assign_functional_nature(chart["planets"])
        assign_afflictions(chart)
        compute_house_metadata(chart)
        return chart

    def process_imported_json(self, json_data):
        try:
            d1_node = json_data["divisional_charts"]["D1"]
            asc_lon = d1_node["ascendant"]["sign_index"] * 30.0 + d1_node["ascendant"]["degree_in_sign"]
            
            planets_raw = [{"name": p["name"], "sym": p["name"][:2] if p["name"] not in ["Rahu", "Ketu"] else ("Ra" if p["name"]=="Rahu" else "Ke"), "lon": p["sign_index"] * 30.0 + p.get("degree_in_sign", 0.0), "retro": p.get("is_retrograde", False), "is_ak": p.get("is_brightest_ak", False), "nakshatra": p.get("nakshatra", ""), "nakshatra_lord": p.get("nakshatra_lord", "")} for p in d1_node["planets"]]
                
            base_chart = self.build_divisional_chart_from_raw(asc_lon, planets_raw, "D1")
            all_charts = {"D1": base_chart}
            for div in ["D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"] + list(self.custom_vargas.keys()):
                all_charts[div] = self.build_divisional_chart_from_raw(asc_lon, planets_raw, div, base_chart["ascendant"]["sign_index"])
            return all_charts
        except Exception as e: print(f"Error processing JSON: {e}"); return None

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
        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}

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
        target_sign = zodiac_names.index(target_sign_name) if target_sign_name and target_sign_name != "Any Rashi" else None

        constrained_planets = {fp: {"target": f_info["sign_idx"], "div": f_info["div"]} for fp, f_info in frozen_planets.items()}
        if target_sign is not None: constrained_planets[body_name] = {"target": target_sign, "div": div_type}
        must_leave_target = (target_sign is not None and original_start_sign == target_sign)

        def calc_max_leap(jd_check, d_dir):
            max_leap = 0
            for p, p_info in constrained_planets.items():
                curr_s = get_sign(jd_check, p, p_info["div"])
                if curr_s == p_info["target"]: continue
                dist = ((curr_s - p_info["target"]) if p in ["Rahu", "Ketu"] else (p_info["target"] - curr_s)) * d_dir % 12
                safe_days_val = {"Saturn": 750, "Rahu": 450, "Ketu": 450, "Jupiter": 300, "Mars": 35, "Sun": 27, "Venus": 20, "Mercury": 15, "Moon": 2, "Ascendant": 0.05}.get(p, 0)
                d_factor = self.custom_vargas[p_info["div"]].get("parts", 1) if p_info["div"] in self.custom_vargas else (int(p_info["div"][1:]) if p_info["div"] != "D1" else 1)
                if 2 <= dist <= 11 and ((dist - 1.5) * safe_days_val) / d_factor > max_leap: max_leap = ((dist - 1.5) * safe_days_val) / d_factor
            return max_leap

        step_map = {"Ascendant": 0.01, "Moon": 0.1, "Sun": 1.0, "Mercury": 1.0, "Venus": 1.0, "Mars": 2.0, "Jupiter": 5.0, "Saturn": 10.0, "Rahu": 10.0, "Ketu": 10.0}
        div_factor = self.custom_vargas[div_type].get("parts", 1) if div_type in self.custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1)
        step = step_map.get(body_name, 10.0) / div_factor
        inner_step = step
        
        for fp, f_info in frozen_planets.items():
            if fp != body_name: 
                f_div_factor = self.custom_vargas[f_info["div"]].get("parts", 1) if f_info["div"] in self.custom_vargas else (int(f_info["div"][1:]) if f_info["div"] != "D1" else 1)
                inner_step = min(inner_step, step_map.get(fp, 10.0) / f_div_factor)

        jd, prev_sign = jd_start + (0.001 * direction / div_factor), get_sign(jd_start - step * direction, body_name, div_type)
        
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
            
            transitioned_in = not must_leave_target and ((current_sign == target_sign and prev_sign != target_sign) if target_sign is not None else (current_sign != prev_sign and current_sign != original_start_sign))

            if transitioned_in:
                t1, t2 = jd - step * direction, jd
                for _ in range(20):
                    t_mid = (t1 + t2) / 2.0
                    m_sign = get_sign(t_mid, body_name, div_type)
                    if (m_sign == target_sign) if target_sign is not None else (m_sign != prev_sign and m_sign != original_start_sign): t2 = t_mid
                    else: t1 = t_mid

                jd_inner, window_match = t2, False
                for _ in range(15000): 
                    if stop_event and stop_event.is_set(): return None
                    if (get_sign(jd_inner, body_name, div_type) != target_sign) if target_sign is not None else (get_sign(jd_inner, body_name, div_type) != current_sign): break
                    if all(get_sign(jd_inner, fp_name, f_info["div"]) == f_info["sign_idx"] for fp_name, f_info in frozen_planets.items() if fp_name != body_name):
                        found_jd, window_match = jd_inner, True; break
                    jd_inner += inner_step * direction

                if window_match:
                    t1_final, t2_final = found_jd - inner_step * direction, found_jd
                    for _ in range(20):
                        t_mid = (t1_final + t2_final) / 2.0
                        if ((get_sign(t_mid, body_name, div_type) == target_sign) if target_sign is not None else (get_sign(t_mid, body_name, div_type) == current_sign)) and all(get_sign(t_mid, fp_name, f_info["div"]) == f_info["sign_idx"] for fp_name, f_info in frozen_planets.items() if fp_name != body_name):
                            t2_final = t_mid
                        else: t1_final = t_mid
                    return float(t2_final)
                else: 
                    jd, current_sign = jd_inner, get_sign(jd_inner, body_name, div_type)
            prev_sign = current_sign
            jd += step * direction

    def get_ascendant_sign(self, jd_utc, lat, lon, div_type="D1"):
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        return self.get_div_sign_and_lon(safe_houses_ex(jd_utc, lat, lon, b'P', swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[1][0], div_type)[0]

    def find_adjacent_ascendant_transits(self, jd_utc, lat, lon, div_type="D1"):
        orig_sign = self.get_ascendant_sign(jd_utc, lat, lon, div_type)
        cache_key = ('asc', lat, lon, div_type, self.current_ayanamsa)
        
        if hasattr(self, 'transit_cache') and cache_key in self.transit_cache:
            c = self.transit_cache[cache_key]
            if c['prev'] < jd_utc < c['next'] and c['orig_sign'] == orig_sign:
                return c['prev'], c['next']
                
        step = 0.01 / (self.custom_vargas[div_type].get("parts", 1) if div_type in self.custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1))
        jd_next = next((jd_utc + step * i for i in range(1, 301) if self.get_ascendant_sign(jd_utc + step * i, lat, lon, div_type) != orig_sign), jd_utc + step * 300)
        t1, t2 = jd_next - step, jd_next
        for _ in range(15):
            tm = (t1 + t2) / 2.0
            if self.get_ascendant_sign(tm, lat, lon, div_type) == orig_sign: t1 = tm
            else: t2 = tm
        jd_next_exact = t2
        
        jd_prev = next((jd_utc - step * i for i in range(1, 301) if self.get_ascendant_sign(jd_utc - step * i, lat, lon, div_type) != orig_sign), jd_utc - step * 300)
        t1_prev, t2 = jd_prev, jd_prev + step
        for _ in range(15):
            tm = (t1_prev + t2) / 2.0
            if self.get_ascendant_sign(tm, lat, lon, div_type) == orig_sign: t2 = tm
            else: t1_prev = tm
            
        if not hasattr(self, 'transit_cache'): self.transit_cache = {}
        self.transit_cache[cache_key] = {'prev': t1_prev, 'next': jd_next_exact, 'orig_sign': orig_sign}
        return t1_prev, jd_next_exact

    def find_adjacent_planet_transits(self, jd_utc, planet_name, div_type="D1"):
        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}
        if planet_name not in body_map: return jd_utc, jd_utc
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        
        def get_s(j): return self.get_div_sign_and_lon(safe_calc_ut(j, body_map[planet_name], swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0] if planet_name != "Ketu" else (safe_calc_ut(j, swe.TRUE_NODE, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0] + 180.0) % 360.0, div_type)[0]
        
        orig_sign = get_s(jd_utc)
        cache_key = ('planet', planet_name, div_type, self.current_ayanamsa)
        
        if hasattr(self, 'transit_cache') and cache_key in self.transit_cache:
            c = self.transit_cache[cache_key]
            if c['prev'] < jd_utc < c['next'] and c['orig_sign'] == orig_sign:
                return c['prev'], c['next']
                
        step = {"Moon": 0.05, "Sun": 0.5, "Mercury": 0.5, "Venus": 0.5, "Mars": 1.0, "Jupiter": 2.0, "Saturn": 5.0, "Rahu": 5.0, "Ketu": 5.0}.get(planet_name, 1.0) / (self.custom_vargas[div_type].get("parts", 1) if div_type in self.custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1))
        
        jd_next = next((jd_utc + step * i for i in range(1, 4001) if get_s(jd_utc + step * i) != orig_sign), jd_utc + step * 4000)
        t1, t2 = jd_next - step, jd_next
        for _ in range(12):
            tm = (t1 + t2) / 2.0
            if get_s(tm) == orig_sign: t1 = tm
            else: t2 = tm
        exact_next = t2
        
        jd_prev = next((jd_utc - step * i for i in range(1, 4001) if get_s(jd_utc - step * i) != orig_sign), jd_utc - step * 4000)
        t1_prev, t2 = jd_prev, jd_prev + step
        for _ in range(12):
            tm = (t1_prev + t2) / 2.0
            if get_s(tm) == orig_sign: t2 = tm
            else: t1_prev = tm
            
        if not hasattr(self, 'transit_cache'): self.transit_cache = {}
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
                        seq.append(lords[l_idx]); c_start += y_acc * 365.2421904; rem -= y_acc; c_lord, c_dur = l_idx, d; break
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
            l1 = (lord_idx + i) % 9; d1 = years[l1]; y_acc2 = 0.0
            for j in range(9):
                l2 = (l1 + j) % 9; d2 = d1 * years[l2] / 120.0; y_acc3 = 0.0
                for k in range(9):
                    l3 = (l2 + k) % 9; d3 = d2 * years[l3] / 120.0
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

        moon_lon = safe_calc_ut(jd_utc, swe.MOON, calc_flag)[0][0]
        sun_lon = safe_calc_ut(jd_utc, swe.SUN, calc_flag)[0][0]

        nak_name, nak_lord, nak_pada = get_nakshatra(moon_lon)
        diff = (moon_lon - sun_lon) % 360.0
        paksha = "Shukla" if diff < 180 else "Krishna"
        tithi_num = (int(diff / 12.0) % 15) + 1
        tithi_name = "Purnima" if tithi_num == 15 and paksha == "Shukla" else "Amavasya" if tithi_num == 15 else ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"][tithi_num - 1]

        sunrise_jd, sunset_jd = None, None
        try:
            res_rise = safe_rise_trans(jd_utc - 0.5, swe.SUN, b'', swe.FLG_SWIEPH, 1+256, (lon, lat, 0.0), 1013.25, 15.0)
            sunrise_jd = res_rise[1][0] if len(res_rise) > 1 and type(res_rise[1]) is tuple else res_rise[0]
            res_set = safe_rise_trans(sunrise_jd, swe.SUN, b'', swe.FLG_SWIEPH, 2+256, (lon, lat, 0.0), 1013.25, 15.0)
            sunset_jd = res_set[1][0] if len(res_set) > 1 and type(res_set[1]) is tuple else res_set[0]
        except Exception: pass

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
        
        asc_deg, asc_sign_index = safe_houses_ex(jd_utc, lat, lon, b'P', calc_flag)[1][0], int(safe_houses_ex(jd_utc, lat, lon, b'P', calc_flag)[1][0] / 30)
        asc_nak_name, asc_nak_lord, asc_nak_pada = get_nakshatra(asc_deg)
        chart_data = {"ascendant": {"degree": asc_deg, "sign_index": asc_sign_index, "sign_num": asc_sign_index + 1, "nakshatra": asc_nak_name, "nakshatra_lord": asc_nak_lord, "nakshatra_pada": asc_nak_pada}, "planets": []}
        
        chart_data["prev_asc_jd"], chart_data["next_asc_jd"] = self.find_adjacent_ascendant_transits(jd_utc, lat, lon, transit_div)
        chart_data["prev_p_jd"], chart_data["next_p_jd"] = self.find_adjacent_planet_transits(jd_utc, transit_planet, transit_div)
        chart_data["current_jd"] = jd_utc

        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            if ruler := SIGN_RULERS.get((asc_sign_index + h - 1) % 12 + 1): planet_lordships[ruler].append(h)

        for name, sym, body_id in [("Sun", "Su", swe.SUN), ("Moon", "Mo", swe.MOON), ("Mars", "Ma", swe.MARS), ("Mercury", "Me", swe.MERCURY), ("Jupiter", "Ju", swe.JUPITER), ("Venus", "Ve", swe.VENUS), ("Saturn", "Sa", swe.SATURN), ("Rahu", "Ra", swe.TRUE_NODE)]:
            res, _ = safe_calc_ut(jd_utc, body_id, calc_flag)
            lon_deg, speed = res[0], res[3]
            p_sign_idx = int(lon_deg / 30)
            nak_name, nak_lord, nak_pada = get_nakshatra(lon_deg)
            is_ex, is_ow, is_deb = get_dignities(name, p_sign_idx + 1, lon_deg % 30.0)

            chart_data["planets"].append({
                "name": name, "sym": sym, "lon": lon_deg, "sign_index": p_sign_idx, "sign_num": p_sign_idx + 1,
                "deg_in_sign": lon_deg % 30.0, "house": (p_sign_idx - asc_sign_index) % 12 + 1, 
                "retro": True if name == "Rahu" else (speed < 0 if name not in ["Sun", "Moon", "Ketu"] else False),
                "exalted": is_ex, "debilitated": is_deb, "own_sign": is_ow, "lord_of": planet_lordships.get(name, []),
                "nakshatra": nak_name, "nakshatra_lord": nak_lord, "nakshatra_pada": nak_pada
            })

        ketu_lon = (next(p["lon"] for p in chart_data["planets"] if p["name"] == "Rahu") + 180.0) % 360.0
        ketu_sign_idx = int(ketu_lon / 30)
        ketu_nak_name, ketu_nak_lord, ketu_nak_pada = get_nakshatra(ketu_lon)
        is_ex, is_ow, is_deb = get_dignities("Ketu", ketu_sign_idx + 1, ketu_lon % 30)
        
        chart_data["planets"].append({
            "name": "Ketu", "sym": "Ke", "lon": ketu_lon, "sign_index": ketu_sign_idx, "sign_num": ketu_sign_idx + 1,
            "deg_in_sign": ketu_lon % 30, "house": (ketu_sign_idx - asc_sign_index) % 12 + 1, "retro": True,
            "exalted": is_ex, "debilitated": is_deb, "own_sign": is_ow, "lord_of": [],
            "nakshatra": ketu_nak_name, "nakshatra_lord": ketu_nak_lord, "nakshatra_pada": ketu_nak_pada
        })

        sun_lon = next((p["lon"] for p in chart_data["planets"] if p["name"] == "Sun"), None)
        combust_rules = {"Moon": {"dir": 12, "retro": 12}, "Mars": {"dir": 17, "retro": 17}, "Mercury": {"dir": 14, "retro": 12}, "Jupiter": {"dir": 11, "retro": 11}, "Venus": {"dir": 10, "retro": 8}, "Saturn": {"dir": 15, "retro": 15}}
        for p in chart_data["planets"]:
            p["combust"] = (abs(sun_lon - p["lon"]) if abs(sun_lon - p["lon"]) <= 180.0 else 360.0 - abs(sun_lon - p["lon"])) <= combust_rules[p["name"]]["retro" if p.get("retro") else "dir"] if sun_lon is not None and p["name"] in combust_rules else False

        valid_ak = [p for p in chart_data["planets"] if p["name"] not in ["Rahu", "Ketu"]]
        if valid_ak:
            ak_name = max(valid_ak, key=lambda x: x["deg_in_sign"])["name"]
            for p in chart_data["planets"]: p["is_ak"] = (p["name"] == ak_name)

        if moon_p := next((p for p in chart_data["planets"] if p["name"] == "Moon"), None):
            chart_data["dasha_sequence"] = self.calculate_vimshottari_dasha(jd_utc, moon_p["lon"], real_now_jd if real_now_jd else jd_utc)["current_sequence"] or []

        chart_data["aspects"] = self.calculate_vedic_aspects(chart_data["planets"])
        
        panchang = self.get_panchang(jd_utc, lat, lon)
        panchang["sunrise_str"] = f"{utc_jd_to_dt_dict(panchang['sunrise_jd'], tz_name)['hour']:02d}:{utc_jd_to_dt_dict(panchang['sunrise_jd'], tz_name)['minute']:02d}" if panchang["sunrise_jd"] else "N/A"
        panchang["sunset_str"] = f"{utc_jd_to_dt_dict(panchang['sunset_jd'], tz_name)['hour']:02d}:{utc_jd_to_dt_dict(panchang['sunset_jd'], tz_name)['minute']:02d}" if panchang["sunset_jd"] else "N/A"
        chart_data["panchang"] = panchang

        assign_functional_nature(chart_data["planets"])
        assign_afflictions(chart_data)
        compute_house_metadata(chart_data)
        return chart_data

    def compute_divisional_chart(self, base_chart, div_type):
        chart = copy.deepcopy(base_chart)

        asc_d1_sign = chart["ascendant"]["sign_index"]
        new_asc_sign_index, new_asc_div_lon = self.get_div_sign_and_lon((asc_d1_sign * 30.0) + (chart["ascendant"]["degree"] % 30.0), div_type)
        
        chart["ascendant"]["sign_index"] = new_asc_sign_index
        chart["ascendant"]["sign_num"] = new_asc_sign_index + 1
        chart["ascendant"]["div_lon"] = new_asc_div_lon
        chart["ascendant"]["vargottama"] = (asc_d1_sign == new_asc_sign_index) and (div_type != "D1")
        
        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            if ruler := SIGN_RULERS.get((new_asc_sign_index + h - 1) % 12 + 1): planet_lordships[ruler].append(h)

        for p in chart["planets"]:
            p_d1_sign = p["sign_index"]
            new_sign_idx, new_div_lon = self.get_div_sign_and_lon(p["lon"], div_type)
            is_ex, is_ow, is_deb = get_dignities(p["name"], new_sign_idx + 1, new_div_lon % 30.0)
            
            p.update({"sign_index": new_sign_idx, "sign_num": new_sign_idx + 1, "div_lon": new_div_lon, "deg_in_sign": new_div_lon % 30.0, "house": (new_sign_idx - new_asc_sign_index) % 12 + 1, "exalted": is_ex, "debilitated": is_deb, "own_sign": is_ow, "lord_of": planet_lordships.get(p["name"], []), "vargottama": (p_d1_sign == new_sign_idx) and (div_type != "D1")})
            if div_type != "D1": p["combust"] = False
            
        chart["aspects"] = self.calculate_vedic_aspects(chart["planets"])
        assign_functional_nature(chart["planets"])
        assign_afflictions(chart)
        compute_house_metadata(chart)
        return chart