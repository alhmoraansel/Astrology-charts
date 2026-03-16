import swisseph as swe
import datetime
import pytz
import time
import math
import copy

# -------------------------
# SWISSEPH SAFE WRAPPERS (Unrestricted Time Support)
# -------------------------
def fallback_ayanamsa(jd):
    T = (jd - 2451545.0) / 36525.0
    return (23.85 + 1.396 * T) % 360.0

def fallback_planet_calc(jd, body_name):
    T = (jd - 2451545.0) / 36525.0
    elements = {
        "Sun": (280.46646, 36000.76983),
        "Moon": (218.3165, 481267.8813),
        "Mars": (355.4533, 19140.3026),
        "Mercury": (252.2503, 149472.6741),
        "Jupiter": (34.40438, 3034.9057),
        "Venus": (181.9791, 58517.8153),
        "Saturn": (50.07744, 1222.1136),
        "Rahu": (125.0445, -1934.13626)
    }
    if body_name in elements:
        L0, L1 = elements[body_name]
        lon_deg = (L0 + L1 * T) % 360.0
        return (lon_deg, 0.0, 0.0, L1/36525.0)
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
    if asc < 0: asc += 360.0
    return asc

def safe_calc_ut(jd, body, flag):
    try:
        return swe.calc_ut(jd, body, flag)
    except Exception:
        try:
            return swe.calc_ut(jd, body, (flag & ~swe.FLG_SWIEPH) | swe.FLG_MOSEPH)
        except Exception:
            body_lookup = {swe.SUN: "Sun", swe.MOON: "Moon", swe.MARS: "Mars", swe.MERCURY: "Mercury", swe.JUPITER: "Jupiter", swe.VENUS: "Venus", swe.SATURN: "Saturn", swe.TRUE_NODE: "Rahu"}
            body_name = body_lookup.get(body, "")
            res = fallback_planet_calc(jd, body_name)
            if flag & swe.FLG_SIDEREAL:
                aya = fallback_ayanamsa(jd)
                res = ((res[0] - aya) % 360.0, res[1], res[2], res[3])
            return res, None

def safe_houses_ex(jd, lat, lon, hsys, flag):
    try:
        return swe.houses_ex(jd, lat, lon, hsys, flag)
    except Exception:
        try:
            return swe.houses_ex(jd, lat, lon, hsys, (flag & ~swe.FLG_SWIEPH) | swe.FLG_MOSEPH)
        except Exception:
            asc_trop = fallback_ascendant(jd, lat, lon)
            if flag & swe.FLG_SIDEREAL:
                aya = fallback_ayanamsa(jd)
                asc_sid = (asc_trop - aya) % 360.0
            else:
                asc_sid = asc_trop
            return (tuple([0.0]*13), (asc_sid, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0))

def safe_rise_trans(jd, body, starname, epheflag, rsmi, geopos, atpress, attemp):
    try:
        return swe.rise_trans(jd, body, starname, epheflag, rsmi, geopos, atpress, attemp)
    except Exception:
        return swe.rise_trans(jd, body, starname, (epheflag & ~swe.FLG_SWIEPH) | swe.FLG_MOSEPH, rsmi, geopos, atpress, attemp)

def parse_user_year(year_input):
    if isinstance(year_input, int): return year_input
    s = str(year_input).strip()
    if s.lower().endswith(("bce", "bc")): return -(int(s.split()[0]) - 1)
    if s.startswith("-"): return int(s)
    return int(s)

def ymdhms_to_jd(year, month, day, hour=0, minute=0, second=0.0, gregorian=True):
    day_frac = (hour + minute / 60.0 + second / 3600.0) / 24.0
    D = day + day_frac
    Y = year
    M = month
    if M <= 2:
        Y -= 1
        M += 12
    A = math.floor(Y / 100.0)
    B = 2 - A + math.floor(A / 4.0) if gregorian else 0
    jd = math.floor(365.25 * (Y + 4716)) + math.floor(30.6001 * (M + 1)) + D + B - 1524.5
    return float(jd)

def jd_to_ymdhms(jd, gregorian=True):
    Z = math.floor(jd + 0.5)
    F = (jd + 0.5) - Z
    if gregorian:
        alpha = math.floor((Z - 1867216.25) / 36524.25)
        A = Z + 1 + alpha - math.floor(alpha / 4.0)
    else: A = Z
    B = A + 1524
    C = math.floor((B - 122.1) / 365.25)
    D = math.floor(365.25 * C)
    E = math.floor((B - D) / 30.6001)
    day_decimal = B - D - math.floor(30.6001 * E) + F
    day = int(math.floor(day_decimal))
    frac_day = day_decimal - day
    month = int(E - 1) if E < 14 else int(E - 13)
    year = int(C - 4716) if month > 2 else int(C - 4715)
    total_seconds = frac_day * 86400.0
    hour = int(total_seconds // 3600)
    minute = int((total_seconds % 3600) // 60)
    second = total_seconds - hour * 3600 - minute * 60
    return {'year': year, 'month': month, 'day': day, 'hour': hour, 'minute': minute, 'second': second}

def dt_dict_to_utc_jd(dt_dict, tz_name):
    y, m, d = dt_dict['year'], dt_dict.get('month', 1), dt_dict.get('day', 1)
    h, mi, s = dt_dict.get('hour', 0), dt_dict.get('minute', 0), dt_dict.get('second', 0.0)
    local_tz = pytz.timezone(tz_name)
    offset_hours = 0.0
    try:
        if 1 <= y <= 9999:
            temp_dt = datetime.datetime(y, m, d, h, mi, int(s))
            localized = local_tz.localize(temp_dt)
            offset_hours = localized.utcoffset().total_seconds() / 3600.0
        else:
            temp_dt = datetime.datetime(2000, 1, 1)
            localized = local_tz.localize(temp_dt)
            offset_hours = localized.utcoffset().total_seconds() / 3600.0
    except: pass
    local_jd = ymdhms_to_jd(y, m, d, h, mi, s)
    return local_jd - (offset_hours / 24.0)

def utc_jd_to_dt_dict(jd_utc, tz_name):
    local_tz = pytz.timezone(tz_name)
    d_temp = jd_to_ymdhms(jd_utc)
    y = d_temp['year']
    offset_hours = 0.0
    try:
        if 1 <= y <= 9999:
            utc_dt = datetime.datetime(y, d_temp['month'], d_temp['day'], d_temp['hour'], d_temp['minute'], int(d_temp['second']))
            utc_dt = pytz.utc.localize(utc_dt)
            local_dt = utc_dt.astimezone(local_tz)
            offset_hours = local_dt.utcoffset().total_seconds() / 3600.0
        else:
            temp_dt = datetime.datetime(2000, 1, 1)
            localized = local_tz.localize(temp_dt)
            offset_hours = localized.utcoffset().total_seconds() / 3600.0
    except: pass
    local_jd = jd_utc + (offset_hours / 24.0)
    return jd_to_ymdhms(local_jd)

def get_nakshatra(lon_deg):
    nak_idx = int(lon_deg / (360.0 / 27.0))
    naks = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashirsha", "Ardra", "Punarvasu", "Pushya", "Ashlesha",
            "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
            "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
    lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
    pada = int((lon_deg % (360.0 / 27.0)) / (360.0 / 108.0)) + 1
    return naks[nak_idx], lords[nak_idx % 9], pada

# ==========================================
# ADVANCED METADATA COMPUTATION (NATURE, VITALITY, PRESSURE & REGIME)
# ==========================================
def assign_functional_nature(planets):
    for p in planets:
        if p["name"] in ["Rahu", "Ketu"]:
            p["func_color"] = "#7f8c8d"
            p["func_label"] = "Neutral (Node)"
            continue
            
        lordships = p.get("lord_of", [])
        is_yogakaraka = any(h in [4,7,10] for h in lordships) and any(h in [1,5,9] for h in lordships)
        
        if is_yogakaraka:
            color, label = "#FFD700", "Yoga Karaka (Gold)"
        elif any(h in [1,5,9] for h in lordships):
            color, label = "#27ae60", "Functional Benefic (Trine)"
        elif any(h in [3,11] for h in lordships):
            if any(h in [6,8,12] for h in lordships):
                color, label = "#c0392b", "Functional Malefic"
            else:
                color, label = "#f1c40f", "Mixed/Opportunistic"
        elif any(h in [6,8,12] for h in lordships):
            color, label = "#c0392b", "Functional Malefic"
        elif any(h in [4,7,10] for h in lordships):
            color, label = "#2980b9", "Situational/Neutral (Kendra)"
        else:
            color, label = "#7f8c8d", "Neutral"
            
        p["func_color"] = color
        p["func_label"] = label

def compute_house_metadata(chart_data):
    sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}
    chart_data["houses_info"] = {}
    
    aspect_counts = {h: 0 for h in range(1, 13)}
    disp_map = {}
    p_house = {}
    
    for p in chart_data["planets"]:
        if p["name"] not in ["Rahu", "Ketu"]:
            ruler = sign_rulers.get(p["sign_num"])
            if ruler: disp_map[p["name"]] = ruler
        p_house[p["name"]] = p["house"]
        
    if "aspects" in chart_data:
        for asp in chart_data["aspects"]:
            aspect_counts[asp["target_house"]] += 1

    regime_terminals = set()
    for p_name in disp_map:
        visited = []
        curr = p_name
        while curr not in visited:
            visited.append(curr)
            curr = disp_map.get(curr)
            if not curr: break
        if curr:
            loop_start = visited.index(curr)
            for terminal_p in visited[loop_start:]:
                if terminal_p in p_house:
                    regime_terminals.add(p_house[terminal_p])

    projection_hubs = set()
    for h_num in range(1, 13):
        targets = set()
        if "aspects" in chart_data:
            for asp in chart_data["aspects"]:
                if asp["source_house"] == h_num:
                    targets.add(asp["target_house"])
        if len(targets) >= 3:
            projection_hubs.add(h_num)

    convergence_hubs = set()
    for h_num in range(1, 13):
        influences = set()
        for p in chart_data["planets"]:
            if p["house"] == h_num: influences.add(p["name"])
        if "aspects" in chart_data:
            for asp in chart_data["aspects"]:
                if asp["target_house"] == h_num: influences.add(asp["aspecting_planet"])
        if len(influences) >= 4:
            convergence_hubs.add(h_num)
            
    for h_num in range(1, 13):
        asc_sign_idx = chart_data["ascendant"]["sign_index"]
        sign_num = (asc_sign_idx + h_num - 1) % 12 + 1
        lord_name = sign_rulers.get(sign_num)
        
        v_color, v_width, v_vitality = "#BDC3C7", 1.0, "Background Scenery (Neutral)"
        if lord_name:
            lord_p = next((p for p in chart_data["planets"] if p["name"] == lord_name), None)
            if lord_p:
                is_ex = lord_p.get("exalted", False)
                is_ow = lord_p.get("own_sign", False)
                is_deb = lord_p.get("debilitated", False)
                is_combust = lord_p.get("combust", False)
                l_h = lord_p.get("house", 1)
                
                in_dusthana = l_h in [6, 8, 12]
                in_kendra_trikona = l_h in [1, 4, 5, 7, 9, 10]
                
                if (is_ex or is_ow) and not in_dusthana and not is_combust:
                    v_color, v_width, v_vitality = "#27ae60", 3.5, "Life Engine (Powerful Lord)"
                elif (is_ex or is_ow) and in_dusthana:
                    v_color, v_width, v_vitality = "#e67e22", 3.5, "Plot Twist (Strong Lord in Dusthana)"
                elif is_deb and in_kendra_trikona:
                    v_color, v_width, v_vitality = "#e67e22", 3.5, "Plot Twist (Debilitated Lord in Kendra/Trine)"
                elif (is_deb and not in_kendra_trikona) or is_combust:
                    v_color, v_width, v_vitality = "#c0392b", 3.5, "Friction Zone (Compromised Lord)"
                    
        p_count = aspect_counts[h_num]
        if p_count >= 4:
            p_color, p_width, p_label = "#c0392b", 3.5, f"Overloaded ({p_count} influences)"
        elif p_count == 3:
            p_color, p_width, p_label = "#f1c40f", 3.0, f"Strong ({p_count} influences)"
        elif p_count == 2:
            p_color, p_width, p_label = "#2980b9", 2.5, f"Moderately Active ({p_count} influences)"
        else:
            p_color, p_width, p_label = "#BDC3C7", 1.0, f"Quiet ({p_count} influences)"

        r_colors = []
        r_labels = []
        if h_num in regime_terminals:
            r_colors.append("#DC143C") 
            r_labels.append("<b style='color:#DC143C;'>Dispositor Terminal (Crimson)</b>")
        if h_num in projection_hubs:
            r_colors.append("#005FFF") 
            r_labels.append("<b style='color:#005FFF;'>Aspect Projection Hub (Blue)</b>")
        if h_num in convergence_hubs:
            r_colors.append("#FFD700") 
            r_labels.append("<b style='color:#f39c12;'>Theme Convergence (Gold)</b>")

        chart_data["houses_info"][h_num] = {
            "vitality_color": v_color, "vitality_width": v_width, "vitality_label": v_vitality,
            "pressure_color": p_color, "pressure_width": p_width, "pressure_label": p_label,
            "pressure_count": p_count,
            "regime_colors": r_colors, "regime_labels": r_labels
        }


# ==========================================
# SINGLE-PROCESS HEURISTIC TRANSIT ENGINE
# ==========================================
def perform_transit_search(params, result_queue, stop_event):
    try:
        swe.set_ephe_path('ephe')
        ayanamsa_modes = { "Lahiri": swe.SIDM_LAHIRI, "Raman": swe.SIDM_RAMAN, "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY }

        dt_param = params['dt']
        tz_name = params['tz_name']
        body_name, direction = params['body_name'], params['direction']
        target_sign_name, frozen_planets = params['target_sign_name'], params['frozen_planets']
        div_type = params.get('div_type', 'D1')
        custom_vargas = params.get('custom_vargas', {})
        
        engine = EphemerisEngine()
        engine.set_custom_vargas(custom_vargas)

        if isinstance(dt_param, dict) and 'year' in dt_param:
            jd_start = dt_dict_to_utc_jd(dt_param, tz_name)
        elif isinstance(dt_param, dict) and 'jd' in dt_param:
            jd_start = float(dt_param['jd'])
        else:
            try:
                local_tz = pytz.timezone(tz_name)
                dt_iso = dt_param if isinstance(dt_param, str) else params.get('dt')
                dt = datetime.datetime.fromisoformat(dt_iso)
                if dt.tzinfo is None: dt = local_tz.localize(dt)
                dt_utc = dt.astimezone(pytz.utc)
                decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
                jd_start = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)
            except Exception:
                jd_start = dt_dict_to_utc_jd({'year': 2000, 'month': 1, 'day': 1}, tz_name)

        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        swe.set_sid_mode(ayanamsa_modes[params['ayanamsa']])
        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}

        def get_sign(j, b_name, target_div="D1"):
            if b_name == "Ascendant":
                cusps, ascmc = safe_houses_ex(j, params['lat'], params['lon'], b'P', calc_flag)
                sign_idx, _ = engine.get_div_sign_and_lon(ascmc[0], target_div)
                return sign_idx
            elif b_name == "Ketu":
                res, _ = safe_calc_ut(j, swe.TRUE_NODE, calc_flag)
                p_lon = (res[0] + 180.0) % 360.0
                sign_idx, _ = engine.get_div_sign_and_lon(p_lon, target_div)
                return sign_idx
            else:
                res, _ = safe_calc_ut(j, body_map[b_name], calc_flag)
                p_lon = res[0]
                sign_idx, _ = engine.get_div_sign_and_lon(p_lon, target_div)
                return sign_idx

        original_start_sign = get_sign(jd_start, body_name, div_type)
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        target_sign = zodiac_names.index(target_sign_name) if target_sign_name and target_sign_name != "Any Rashi" else None

        constrained_planets = {}
        for fp, f_info in frozen_planets.items():
            constrained_planets[fp] = {"target": f_info["sign_idx"], "div": f_info["div"]}
        if target_sign is not None:
            constrained_planets[body_name] = {"target": target_sign, "div": div_type}
            
        must_leave_target = (target_sign is not None and original_start_sign == target_sign)

        def get_forward_dist(p, curr_s, target_s, d_dir):
            if p in ["Rahu", "Ketu"]: return (curr_s - target_s) * d_dir % 12
            else: return (target_s - curr_s) * d_dir % 12

        div_factor = custom_vargas[div_type].get("parts", 1) if div_type in custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1)

        def calc_max_leap(jd_check, d_dir):
            max_leap = 0
            for p, p_info in constrained_planets.items():
                curr_s = get_sign(jd_check, p, p_info["div"])
                if curr_s == p_info["target"]: continue
                dist = get_forward_dist(p, curr_s, p_info["target"], d_dir)
                
                safe_days_val = {"Saturn": 750, "Rahu": 450, "Ketu": 450, "Jupiter": 300, "Mars": 35, "Sun": 27, "Venus": 20, "Mercury": 15, "Moon": 2, "Ascendant": 0.05}.get(p, 0)
                
                p_div = p_info["div"]
                d_factor = custom_vargas[p_div].get("parts", 1) if p_div in custom_vargas else (int(p_div[1:]) if p_div != "D1" else 1)
                
                if 2 <= dist <= 11:
                    p_leap = ((dist - 1.5) * safe_days_val) / d_factor
                    if p_leap > max_leap: max_leap = p_leap
            return max_leap

        step_map = {"Ascendant": 0.01, "Moon": 0.1, "Sun": 1.0, "Mercury": 1.0, "Venus": 1.0, "Mars": 2.0, "Jupiter": 5.0, "Saturn": 10.0, "Rahu": 10.0, "Ketu": 10.0}
        step = step_map.get(body_name, 10.0) / div_factor
        inner_step = step
        for fp, f_info in frozen_planets.items():
            if fp != body_name: 
                f_div = f_info["div"]
                f_div_factor = custom_vargas[f_div].get("parts", 1) if f_div in custom_vargas else (int(f_div[1:]) if f_div != "D1" else 1)
                inner_step = min(inner_step, step_map.get(fp, 10.0) / f_div_factor)

        jd = jd_start + (0.001 * direction / div_factor)
        prev_sign = get_sign(jd - step * direction, body_name, div_type)
        loops = 0
        last_progress_time = time.time()

        while not stop_event.is_set():
            if jd < -50000000 or jd > 50000000:
                result_queue.put({"status": "error", "message": "Search reached bounds."})
                return

            loops += 1
            if loops % 50 == 0:
                now = time.time()
                if now - last_progress_time > 0.3:
                    year, month, day, _ = swe.revjul(jd, 1)
                    if year <= 0: result_queue.put({"status": "progress", "date": f"{int(1-year)} BCE-{int(month):02d}-{int(day):02d}"})
                    else: result_queue.put({"status": "progress", "date": f"{int(year)}-{int(month):02d}-{int(day):02d}"})
                    last_progress_time = now

            leap_days = calc_max_leap(jd, direction)
            if leap_days > 15:
                jd += leap_days * direction
                prev_sign = get_sign(jd - step * direction, body_name, div_type)
                continue

            current_sign = get_sign(jd, body_name, div_type)
            if must_leave_target and current_sign != target_sign: must_leave_target = False
            transitioned_in = False
            
            if not must_leave_target:
                if target_sign is not None:
                    if current_sign == target_sign and prev_sign != target_sign: transitioned_in = True
                else:
                    if current_sign != prev_sign and current_sign != original_start_sign: transitioned_in = True

            if transitioned_in:
                t1, t2 = jd - step * direction, jd
                for _ in range(20):
                    t_mid = (t1 + t2) / 2.0
                    mid_sign = get_sign(t_mid, body_name, div_type)
                    v_targ = False
                    if target_sign is not None:
                        if mid_sign == target_sign: v_targ = True
                    else:
                        if mid_sign != prev_sign and mid_sign != original_start_sign: v_targ = True
                    if v_targ: t2 = t_mid
                    else: t1 = t_mid

                jd_inner, window_match = t2, False
                for _ in range(150000):
                    if stop_event.is_set():
                        result_queue.put({"status": "stopped"})
                        return
                    m_sign = get_sign(jd_inner, body_name, div_type)
                    if target_sign is not None:
                        if m_sign != target_sign: break
                    else:
                        if m_sign != current_sign: break
                    f_ok = True
                    for fp_name, f_info in frozen_planets.items():
                        if fp_name != body_name and get_sign(jd_inner, fp_name, f_info["div"]) != f_info["sign_idx"]:
                            f_ok = False; break
                    if f_ok: found_jd, window_match = jd_inner, True; break
                    jd_inner += inner_step * direction

                if window_match:
                    t1_final, t2_final = found_jd - inner_step * direction, found_jd
                    for _ in range(20):
                        t_mid = (t1_final + t2_final) / 2.0
                        m_sign = get_sign(t_mid, body_name, div_type)
                        c_ok = False
                        if target_sign is not None:
                            if m_sign == target_sign: c_ok = True
                        else:
                            if m_sign == current_sign: c_ok = True
                        if c_ok:
                            for fp_name, f_info in frozen_planets.items():
                                if fp_name != body_name and get_sign(t_mid, fp_name, f_info["div"]) != f_info["sign_idx"]:
                                    c_ok = False; break
                        if c_ok: t2_final = t_mid
                        else: t1_final = t_mid
                    result_queue.put({"status": "success", "result_jd_utc": float(t2_final)})
                    return
                else:
                    jd, current_sign = jd_inner, get_sign(jd_inner, body_name, div_type)

            prev_sign = current_sign
            jd += step * direction
        result_queue.put({"status": "stopped"})
    except Exception as e:
        result_queue.put({"status": "error", "message": str(e)})


# ==========================================
# CASCADING REVERSE RECTIFICATION ENGINE
# ==========================================
def perform_rectification_search(params, result_queue, stop_event):
    try:
        swe.set_ephe_path('ephe')
        div_type = params['div_type']
        target_asc = params['target_asc'] 
        target_planets = params['target_planets'] 
        search_mode = params.get('search_mode', 'speed')
        custom_vargas = params.get('custom_vargas', {})
        
        engine = EphemerisEngine()
        engine.set_ayanamsa(params['ayanamsa'])
        engine.set_custom_vargas(custom_vargas)
        
        ayanamsa_modes = {"Lahiri": swe.SIDM_LAHIRI, "Raman": swe.SIDM_RAMAN, "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY}
        if params['ayanamsa'] in ayanamsa_modes:
            swe.set_sid_mode(ayanamsa_modes[params['ayanamsa']])
            
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}

        div_factor = custom_vargas[div_type].get("parts", 1) if div_type in custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1)
        window_deg = 30.0 / div_factor

        max_speeds = {
            "Saturn": 0.25, "Jupiter": 0.35, "Rahu": 0.2, "Ketu": 0.2, 
            "Mars": 1.2, "Sun": 1.2, "Venus": 1.8, "Mercury": 3.5,
            "Moon": 16.5, "Ascendant": 500.0
        }

        def get_sign_idx(jd, name):
            if name == "Ascendant":
                cusps, ascmc = safe_houses_ex(jd, params['lat'], params['lon'], b'P', calc_flag)
                asc_sign, _ = engine.get_div_sign_and_lon(ascmc[0], div_type)
                return asc_sign
            elif name == "Ketu":
                res, _ = safe_calc_ut(jd, swe.TRUE_NODE, calc_flag)
                p_lon = (res[0] + 180.0) % 360.0
                sign_idx, _ = engine.get_div_sign_and_lon(p_lon, div_type)
                return sign_idx
            else:
                res, _ = safe_calc_ut(jd, body_map[name], calc_flag)
                p_lon = res[0]
                sign_idx, _ = engine.get_div_sign_and_lon(p_lon, div_type)
                return sign_idx

        priorities = ["Saturn", "Jupiter", "Rahu", "Ketu", "Mars", "Sun", "Venus", "Mercury", "Moon", "Ascendant"]
        checks = []
        for p in priorities:
            if p == "Ascendant" and target_asc is not None:
                checks.append(("Ascendant", target_asc))
            elif p in target_planets:
                checks.append((p, target_planets[p]))

        base_year = params['base_year']
        origin_jd = dt_dict_to_utc_jd({'year': base_year, 'month': 1, 'day': 1}, params['tz'])
        
        offsets = [0]
        for i in range(1, 1001):
            offsets.extend([i, -i])

        if search_mode == 'speed':
            for offset in offsets:
                year = base_year + offset
                if offset % 10 == 0:
                    result_queue.put({"status": "progress", "msg": f"Cascade Scan: Year {year} (Range +/- 1000)..."})
                
                jd_start = dt_dict_to_utc_jd({'year': year, 'month': 1, 'day': 1}, params['tz'])
                jd_end = dt_dict_to_utc_jd({'year': year+1, 'month': 1, 'day': 1}, params['tz'])
                
                windows = [(jd_start, jd_end)]

                for p_name, t_sign in checks:
                    if not windows: break 
                    
                    safe_step = max((window_deg / max_speeds.get(p_name, 1.0)) * 0.45, 1.0 / 1440.0)
                    if p_name == "Ascendant": safe_step = 0.5 / 1440.0 
                    
                    new_windows = []
                    for w_start, w_end in windows:
                        t = w_start
                        in_match = False
                        m_start = None

                        while t <= w_end + safe_step:
                            if stop_event.is_set(): return
                            
                            check_t = min(t, w_end)
                            is_match = (get_sign_idx(check_t, p_name) == t_sign)
                            
                            if is_match and not in_match:
                                m_start = check_t
                                in_match = True
                            elif not is_match and in_match:
                                new_windows.append((m_start, check_t))
                                in_match = False
                                
                            if t >= w_end: break
                            t += safe_step
                            
                        if in_match:
                            new_windows.append((m_start, w_end))
                            
                    windows = new_windows

                if windows:
                    formatted_blocks = []
                    for w_start, w_end in windows:
                        mid_jd = (w_start + w_end) / 2.0
                        formatted_blocks.append({
                            "start": utc_jd_to_dt_dict(w_start, params['tz']), 
                            "end": utc_jd_to_dt_dict(w_end, params['tz']), 
                            "mid_jd": mid_jd
                        })
                    result_queue.put({"status": "success", "year": year, "blocks": formatted_blocks})
                    return
            
            result_queue.put({"status": "phase1_failed", "message": "Mathematical cascade scan finished +/- 1000 years. No matches found."})
            return

        elif search_mode == 'brute':
            result_queue.put({"status": "progress", "msg": "Phase 2: Deep 1-Minute Brute-Force radiating outward..."})
            
            max_steps = int(1000 * 365.25 * 1440)
            
            for step in range(max_steps):
                if stop_event.is_set(): return
                    
                if step % 100000 == 0:
                    years_out = step / (365.25 * 1440)
                    result_queue.put({"status": "progress", "msg": f"Brute-Force: Scanned +/- {years_out:.2f} years radiating from origin..."})
                    
                for sign_dir in (1, -1) if step > 0 else (1,):
                    jd = origin_jd + (step * sign_dir / 1440.0)
                    
                    match = True
                    for p_name, t_sign in checks:
                        if get_sign_idx(jd, p_name) != t_sign:
                            match = False
                            break
                            
                    if match:
                        target_dt = utc_jd_to_dt_dict(jd, params['tz'])
                        result_queue.put({"status": "success", "year": target_dt['year'], "blocks": [{"start": target_dt, "end": target_dt, "mid_jd": jd}]})
                        return
                        
            result_queue.put({"status": "not_found", "message": "No matches found within +/- 1000 years."})
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        result_queue.put({"status": "error", "message": str(e)})


# ==========================================
# EPHEMERIS CHART CALCULATOR ENGINE
# ==========================================
class EphemerisEngine:
    def __init__(self):
        swe.set_ephe_path('ephe')
        self.ayanamsa_modes = {"Lahiri": swe.SIDM_LAHIRI, "Raman": swe.SIDM_RAMAN, "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY}
        self.current_ayanamsa = "Lahiri"
        self.custom_vargas = {}

    def set_ayanamsa(self, name):
        if name in self.ayanamsa_modes: self.current_ayanamsa = name
        
    def set_custom_vargas(self, vargas):
        self.custom_vargas = vargas

    def get_div_sign_and_lon(self, lon_deg, div_type):
        total_mas = int(round(lon_deg * 3600000.0))
        sign_index = (total_mas // 108000000) % 12
        mas_in_sign = total_mas % 108000000
        deg_in_sign = mas_in_sign / 3600000.0
        
        # Priority mapping: Apply custom user vargas first
        if div_type in self.custom_vargas:
            rule = self.custom_vargas[div_type]
            parts = rule.get("parts", 1)
            starts = rule.get("starts", [0]*12)
            segment = int(deg_in_sign / (30.0 / parts))
            if segment >= parts: segment = parts - 1 # Precision safeguard
            div_sign_index = (starts[sign_index] + segment) % 12
            deg_in_div_sign = (deg_in_sign % (30.0 / parts)) * parts
            return div_sign_index, div_sign_index * 30.0 + deg_in_div_sign
            
        if div_type == "D1": 
            return sign_index, lon_deg
        elif div_type == "D2":
            is_even = (sign_index % 2 != 0)
            if not is_even: div_sign_index = 4 if deg_in_sign < 15.0 else 3
            else: div_sign_index = 3 if deg_in_sign < 15.0 else 4
            deg_in_div_sign = (deg_in_sign % 15.0) * 2.0
        elif div_type == "D3":
            segment = int(deg_in_sign / 10.0)
            div_sign_index = (sign_index + segment * 4) % 12
            deg_in_div_sign = (deg_in_sign % 10.0) * 3.0
        elif div_type == "D4":
            segment = int(deg_in_sign / 7.5)
            deg_in_div_sign = (deg_in_sign % 7.5) * 4.0
            div_sign_index = (sign_index + (segment * 3)) % 12
        elif div_type == "D5":
            segment = int(deg_in_sign / 6.0)
            div_sign_index = (sign_index + segment) % 12
            deg_in_div_sign = (deg_in_sign % 6.0) * 5.0
        elif div_type == "D6":
            segment = int(deg_in_sign / 5.0)
            div_sign_index = (sign_index + segment) % 12
            deg_in_div_sign = (deg_in_sign % 5.0) * 6.0
        elif div_type == "D7":
            segment = int(deg_in_sign / (30.0 / 7.0))
            deg_in_div_sign = (deg_in_sign % (30.0 / 7.0)) * 7.0
            is_even = (sign_index % 2 != 0)
            start_sign = (sign_index + 6) % 12 if is_even else sign_index
            div_sign_index = (start_sign + segment) % 12
        elif div_type == "D8":
            segment = int(deg_in_sign / 3.75)
            div_sign_index = (sign_index + segment) % 12
            deg_in_div_sign = (deg_in_sign % 3.75) * 8.0
        elif div_type == "D9":
            segment = mas_in_sign // 12000000
            deg_in_div_sign = ((mas_in_sign % 12000000) / 12000000.0) * 30.0
            element = sign_index % 4
            start_sign = [0, 9, 6, 3][element]
            div_sign_index = (start_sign + segment) % 12
        elif div_type == "D10":
            segment = mas_in_sign // 10800000
            deg_in_div_sign = ((mas_in_sign % 10800000) / 10800000.0) * 30.0
            is_odd = (sign_index % 2 == 0)
            start_sign = sign_index if is_odd else (sign_index + 8)
            div_sign_index = (start_sign + segment) % 12
        elif div_type == "D11":
            segment = int(deg_in_sign / (30.0/11.0))
            div_sign_index = (sign_index + segment) % 12
            deg_in_div_sign = (deg_in_sign % (30.0/11.0)) * 11.0
        elif div_type == "D12":
            segment = int(deg_in_sign / 2.5)
            deg_in_div_sign = (deg_in_sign % 2.5) * 12.0
            div_sign_index = (sign_index + segment) % 12
        elif div_type == "D16":
            segment = int(deg_in_sign / 1.875)
            deg_in_div_sign = (deg_in_sign % 1.875) * 16.0
            modality = sign_index % 3
            start_sign = [0, 4, 8][modality]
            div_sign_index = (start_sign + segment) % 12
        elif div_type == "D20":
            segment = mas_in_sign // 5400000
            deg_in_div_sign = ((mas_in_sign % 5400000) / 5400000.0) * 30.0
            modality = sign_index % 3
            start_sign = [0, 8, 4][modality]
            div_sign_index = (start_sign + segment) % 12
        elif div_type == "D24":
            segment = int(deg_in_sign / 1.25)
            deg_in_div_sign = (deg_in_sign % 1.25) * 24.0
            is_even = (sign_index % 2 != 0)
            start_sign = 3 if is_even else 4 
            div_sign_index = (start_sign + segment) % 12
        elif div_type == "D27":
            segment = int(deg_in_sign / (30.0/27.0))
            element = sign_index % 4
            start_signs = [0, 3, 6, 9]
            div_sign_index = (start_signs[element] + segment) % 12
            deg_in_div_sign = (deg_in_sign % (30.0/27.0)) * 27.0
        elif div_type == "D30":
            is_odd = (sign_index % 2 == 0)
            if is_odd:
                if mas_in_sign < 18000000:       div_sign_index = 0;  deg_in_div_sign = (mas_in_sign / 18000000.0) * 30.0
                elif mas_in_sign < 36000000:     div_sign_index = 10; deg_in_div_sign = ((mas_in_sign - 18000000) / 18000000.0) * 30.0
                elif mas_in_sign < 64800000:     div_sign_index = 8;  deg_in_div_sign = ((mas_in_sign - 36000000) / 28800000.0) * 30.0
                elif mas_in_sign < 90000000:     div_sign_index = 2;  deg_in_div_sign = ((mas_in_sign - 64800000) / 25200000.0) * 30.0
                else:                            div_sign_index = 6;  deg_in_div_sign = ((mas_in_sign - 90000000) / 18000000.0) * 30.0
            else:
                if mas_in_sign < 18000000:       div_sign_index = 1;  deg_in_div_sign = (mas_in_sign / 18000000.0) * 30.0
                elif mas_in_sign < 43200000:     div_sign_index = 5;  deg_in_div_sign = ((mas_in_sign - 18000000) / 25200000.0) * 30.0
                elif mas_in_sign < 72000000:     div_sign_index = 11; deg_in_div_sign = ((mas_in_sign - 43200000) / 28800000.0) * 30.0
                elif mas_in_sign < 90000000:     div_sign_index = 9;  deg_in_div_sign = ((mas_in_sign - 72000000) / 18000000.0) * 30.0
                else:                            div_sign_index = 7;  deg_in_div_sign = ((mas_in_sign - 90000000) / 18000000.0) * 30.0
        elif div_type == "D40":
            segment = int(deg_in_sign / 0.75)
            is_odd = (sign_index % 2 == 0)
            start_sign = 0 if is_odd else 6
            div_sign_index = (start_sign + segment) % 12
            deg_in_div_sign = (deg_in_sign % 0.75) * 40.0
        elif div_type == "D45":
            segment = int(deg_in_sign / (30.0/45.0))
            modality = sign_index % 3
            start_signs = [0, 4, 8]
            div_sign_index = (start_signs[modality] + segment) % 12
            deg_in_div_sign = (deg_in_sign % (30.0/45.0)) * 45.0
        elif div_type == "D60":
            segment = mas_in_sign // 1800000
            deg_in_div_sign = ((mas_in_sign % 1800000) / 1800000.0) * 30.0
            div_sign_index = (sign_index + segment) % 12
        else:
            div_sign_index = sign_index
            deg_in_div_sign = deg_in_sign

        return div_sign_index, div_sign_index * 30.0 + deg_in_div_sign

    def calculate_vedic_aspects(self, planets):
        aspects = []
        aspect_rules = {"Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7], "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10], "Rahu": [5, 7, 9], "Ketu": [5, 7, 9]}
        for p in planets:
            for aspect_count in aspect_rules.get(p["name"], []):
                aspects.append({
                    "aspecting_planet": p["name"], 
                    "source_house": p["house"], 
                    "target_house": (p["house"] + aspect_count - 2) % 12 + 1, 
                    "aspect_count": aspect_count
                })
        return aspects

    def build_divisional_chart_from_raw(self, base_asc_lon, base_planets, div_type, d1_asc_sign_idx=None):
        chart = {"ascendant": {}, "planets": []}
        
        asc_sign_idx, asc_div_lon = self.get_div_sign_and_lon(base_asc_lon, div_type)
        chart["ascendant"] = {
            "sign_index": asc_sign_idx, "sign_num": asc_sign_idx + 1,
            "degree": asc_div_lon % 30.0, "div_lon": asc_div_lon,
            "vargottama": (d1_asc_sign_idx == asc_sign_idx) if d1_asc_sign_idx is not None else False
        }
        
        exaltation_rules = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
        debilitation_rules = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
        sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}

        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            sign_in_house = (asc_sign_idx + h - 1) % 12 + 1
            ruler = sign_rulers.get(sign_in_house)
            if ruler: planet_lordships[ruler].append(h)

        for p_raw in base_planets:
            p_sign_idx, p_div_lon = self.get_div_sign_and_lon(p_raw["lon"], div_type)
            p_sign_num = p_sign_idx + 1
            deg_in_div = p_div_lon % 30.0
            
            is_exalted, is_own, is_debilitated = False, (sign_rulers.get(p_sign_num) == p_raw["name"]), (p_sign_num == debilitation_rules.get(p_raw["name"]))
            
            if p_raw["name"] == "Moon" and p_sign_num == 2:
                if deg_in_div <= 3.0: is_exalted, is_own = True, False
                else: is_exalted, is_own = False, True
            elif p_raw["name"] == "Mercury" and p_sign_num == 6:
                if deg_in_div <= 15.0: is_exalted, is_own = True, False
                else: is_exalted, is_own = False, True
            else:
                is_exalted = (p_sign_num == exaltation_rules.get(p_raw["name"]))
                
            if p_raw["name"] == "Moon" and p_sign_num == 8: is_debilitated = (deg_in_div <= 3.0)
            elif p_raw["name"] == "Mercury" and p_sign_num == 12: is_debilitated = (deg_in_div <= 15.0)

            chart["planets"].append({
                "name": p_raw["name"], "sym": p_raw["sym"], "lon": p_div_lon, "sign_index": p_sign_idx,
                "sign_num": p_sign_num, "deg_in_sign": deg_in_div, "house": (p_sign_idx - asc_sign_idx) % 12 + 1,
                "retro": p_raw["retro"], "exalted": is_exalted, "debilitated": is_debilitated,
                "own_sign": is_own, "lord_of": planet_lordships.get(p_raw["name"], []),
                "is_ak": p_raw.get("is_ak", False), "nakshatra": p_raw.get("nakshatra", ""), "nakshatra_lord": p_raw.get("nakshatra_lord", ""),
                "combust": False, "vargottama": (int(p_raw["lon"]/30.0) == p_sign_idx) if div_type != "D1" else False
            })

        chart["aspects"] = self.calculate_vedic_aspects(chart["planets"])
        assign_functional_nature(chart["planets"])
        compute_house_metadata(chart)
        
        return chart

    def process_imported_json(self, json_data):
        try:
            d1_node = json_data["divisional_charts"]["D1"]
            asc_sign_idx = d1_node["ascendant"]["sign_index"]
            asc_deg = d1_node["ascendant"]["degree_in_sign"]
            asc_lon = asc_sign_idx * 30.0 + asc_deg
            
            planets_raw = []
            for p in d1_node["planets"]:
                p_lon = p["sign_index"] * 30.0 + p.get("degree_in_sign", 0.0)
                sym = p["name"][:2] if p["name"] not in ["Rahu", "Ketu"] else ("Ra" if p["name"]=="Rahu" else "Ke")
                planets_raw.append({
                    "name": p["name"],
                    "sym": sym,
                    "lon": p_lon,
                    "retro": p.get("is_retrograde", False),
                    "is_ak": p.get("is_brightest_ak", False),
                    "nakshatra": p.get("nakshatra", ""),
                    "nakshatra_lord": p.get("nakshatra_lord", "")
                })
                
            base_chart = self.build_divisional_chart_from_raw(asc_lon, planets_raw, "D1")
            
            all_charts = {"D1": base_chart}
            # Includes standard 20 + dynamically appended custom vargas
            divs = ["D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"] + list(self.custom_vargas.keys())
            for div in divs:
                all_charts[div] = self.build_divisional_chart_from_raw(asc_lon, planets_raw, div, base_chart["ascendant"]["sign_index"])
                
            return all_charts
        except Exception as e:
            print(f"Error processing JSON: {e}")
            return None

    def get_ascendant_sign(self, jd_utc, lat, lon, div_type="D1"):
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        cusps, ascmc = safe_houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        asc_deg = ascmc[0]
        sign_idx, _ = self.get_div_sign_and_lon(asc_deg, div_type)
        return sign_idx

    def find_adjacent_ascendant_transits(self, jd_utc, lat, lon, div_type="D1"):
        orig_sign = self.get_ascendant_sign(jd_utc, lat, lon, div_type)
        div_factor = self.custom_vargas[div_type].get("parts", 1) if div_type in self.custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1)
        step = 0.01 / div_factor
        
        jd_next = jd_utc
        for _ in range(300):
            jd_next += step
            if self.get_ascendant_sign(jd_next, lat, lon, div_type) != orig_sign: break
        t1, t2 = jd_next - step, jd_next
        for _ in range(15):
            tm = (t1 + t2) / 2.0
            if self.get_ascendant_sign(tm, lat, lon, div_type) != orig_sign: t2 = tm
            else: t1 = tm
        jd_next_exact = t2
        
        jd_prev = jd_utc
        for _ in range(300):
            jd_prev -= step
            if self.get_ascendant_sign(jd_prev, lat, lon, div_type) != orig_sign: break
        t1, t2 = jd_prev, jd_prev + step
        for _ in range(15):
            tm = (t1 + t2) / 2.0
            if self.get_ascendant_sign(tm, lat, lon, div_type) != orig_sign: t1 = tm
            else: t2 = tm
        jd_prev_exact = t1
        return jd_prev_exact, jd_next_exact

    def find_adjacent_planet_transits(self, jd_utc, planet_name, div_type="D1"):
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        
        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}
        
        if planet_name not in body_map: return jd_utc, jd_utc
        
        def get_sign(j):
            res, _ = safe_calc_ut(j, body_map[planet_name], calc_flag)
            lon = res[0] if planet_name != "Ketu" else (res[0] + 180.0) % 360.0
            sign_idx, _ = self.get_div_sign_and_lon(lon, div_type)
            return sign_idx

        orig_sign = get_sign(jd_utc)
        div_factor = self.custom_vargas[div_type].get("parts", 1) if div_type in self.custom_vargas else (int(div_type[1:]) if div_type != "D1" else 1)
        
        base_steps = {
            "Moon": 0.05, "Sun": 0.5, "Mercury": 0.5, "Venus": 0.5,
            "Mars": 1.0, "Jupiter": 2.0, "Saturn": 5.0, "Rahu": 5.0, "Ketu": 5.0
        }
        step = base_steps.get(planet_name, 1.0) / div_factor
        
        jd_next = jd_utc
        for _ in range(4000):
            jd_next += step
            if get_sign(jd_next) != orig_sign: break
        t1, t2 = jd_next - step, jd_next
        for _ in range(12):
            tm = (t1 + t2) / 2.0
            if get_sign(tm) != orig_sign: t2 = tm
            else: t1 = tm
        exact_next = t2
        
        jd_prev = jd_utc
        for _ in range(4000):
            jd_prev -= step
            if get_sign(jd_prev) != orig_sign: break
        t1, t2 = jd_prev, jd_prev + step
        for _ in range(12):
            tm = (t1 + t2) / 2.0
            if get_sign(tm) != orig_sign: t1 = tm
            else: t2 = tm
        exact_prev = t1
        
        return exact_prev, exact_next

    def calculate_vimshottari_dasha(self, birth_jd, moon_lon, target_jd, forecast_start_jd=None, forecast_end_jd=None):
        lords = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
        years = [7, 20, 6, 10, 7, 18, 16, 19, 17]
        
        total_mas = int(round(moon_lon * 3600000.0))
        nak_len = 48000000 
        nak_idx = total_mas // nak_len
        lord_idx = nak_idx % 9
        passed_frac = (total_mas % nak_len) / float(nak_len)
        passed_years = passed_frac * years[lord_idx]
        
        dasha_start_jd = birth_jd - (passed_years * 365.2421904)

        def get_node(t_jd):
            elapsed_years = (t_jd - dasha_start_jd) / 365.2421904
            elapsed_years %= 120.0
            
            y_acc = 0.0
            for i in range(9):
                l1 = (lord_idx + i) % 9
                d1 = years[l1]
                if i == 8 or elapsed_years < y_acc + d1:
                    rem1 = elapsed_years - y_acc
                    s1 = dasha_start_jd + y_acc * 365.2421904
                    break
                y_acc += d1
                
            y_acc2 = 0.0
            for i in range(9):
                l2 = (l1 + i) % 9
                d2 = d1 * years[l2] / 120.0
                if i == 8 or rem1 < y_acc2 + d2:
                    rem2 = rem1 - y_acc2
                    s2 = s1 + y_acc2 * 365.2421904
                    break
                y_acc2 += d2
                
            y_acc3 = 0.0
            for i in range(9):
                l3 = (l2 + i) % 9
                d3 = d2 * years[l3] / 120.0
                if i == 8 or rem2 < y_acc3 + d3:
                    rem3 = rem2 - y_acc3
                    s3 = s2 + y_acc3 * 365.2421904
                    break
                y_acc3 += d3
                
            y_acc4 = 0.0
            for i in range(9):
                l4 = (l3 + i) % 9
                d4 = d3 * years[l4] / 120.0
                if i == 8 or rem3 < y_acc4 + d4:
                    rem4 = rem3 - y_acc4
                    s4 = s3 + y_acc4 * 365.2421904
                    break
                y_acc4 += d4
                
            y_acc5 = 0.0
            for i in range(9):
                l5 = (l4 + i) % 9
                d5 = d4 * years[l5] / 120.0
                if i == 8 or rem4 < y_acc5 + d5:
                    s5 = s4 + y_acc5 * 365.2421904
                    e5 = s4 + (y_acc5 + d5) * 365.2421904
                    break
                y_acc5 += d5
                
            return [lords[l1], lords[l2], lords[l3], lords[l4], lords[l5]], s5, e5

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
        nak_idx = total_mas // nak_len
        lord_idx = nak_idx % 9
        passed_frac = (total_mas % nak_len) / float(nak_len)
        passed_years = passed_frac * years[lord_idx]
        
        dasha_start_jd = birth_jd - (passed_years * 365.2421904)
        
        export_list = []
        
        y_acc = 0.0
        for i in range(9):
            l1 = (lord_idx + i) % 9
            d1 = years[l1]
            md_start_jd = dasha_start_jd + y_acc * 365.2421904
            
            y_acc2 = 0.0
            for j in range(9):
                l2 = (l1 + j) % 9
                d2 = d1 * years[l2] / 120.0
                ad_start_jd = md_start_jd + y_acc2 * 365.2421904
                
                y_acc3 = 0.0
                for k in range(9):
                    l3 = (l2 + k) % 9
                    d3 = d2 * years[l3] / 120.0
                    pd_start_jd = ad_start_jd + y_acc3 * 365.2421904
                    pd_end_jd = pd_start_jd + d3 * 365.2421904
                    y_acc3 += d3
                    
                    if pd_end_jd <= birth_jd:
                        continue
                        
                    age_start = max(0.0, (pd_start_jd - birth_jd) / 365.2421904)
                    age_end = (pd_end_jd - birth_jd) / 365.2421904
                    
                    if age_start > 120.0:
                        break
                        
                    export_list.append(f"age {age_start:.2f}-{age_end:.2f} years dasha influence {lords[l1].lower()} {lords[l2].lower()} {lords[l3].lower()}")
                
                y_acc2 += d2
            y_acc += d1
            
        return export_list

    def get_panchang(self, jd_utc, lat, lon):
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

        moon_res, _ = safe_calc_ut(jd_utc, swe.MOON, calc_flag)
        sun_res, _ = safe_calc_ut(jd_utc, swe.SUN, calc_flag)

        moon_lon = moon_res[0]
        sun_lon = sun_res[0]

        nak_name, nak_lord, nak_pada = get_nakshatra(moon_lon)

        diff = (moon_lon - sun_lon) % 360.0
        tithi_idx = int(diff / 12.0)
        paksha = "Shukla" if diff < 180 else "Krishna"
        tithi_num = (tithi_idx % 15) + 1
        
        tithi_names = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi", "Purnima", "Amavasya"]
        if tithi_num == 15:
            tithi_name = "Purnima" if paksha == "Shukla" else "Amavasya"
        else:
            tithi_name = tithi_names[tithi_num - 1]

        sunrise_jd, sunset_jd = None, None
        try:
            geopos = (lon, lat, 0.0)
            res_rise = safe_rise_trans(jd_utc - 0.5, swe.SUN, b'', swe.FLG_SWIEPH, 1+256, geopos, 1013.25, 15.0)
            res_set = safe_rise_trans(res_rise[1][0] if hasattr(res_rise[1], '__getitem__') else res_rise[0], swe.SUN, b'', swe.FLG_SWIEPH, 2+256, geopos, 1013.25, 15.0)
            
            sunrise_jd = res_rise[1][0] if len(res_rise) > 1 and type(res_rise[1]) is tuple else res_rise[0]
            sunset_jd = res_set[1][0] if len(res_set) > 1 and type(res_set[1]) is tuple else res_set[0]
        except Exception:
            pass

        return {
            "nakshatra": nak_name,
            "nakshatra_lord": nak_lord,
            "nakshatra_pada": nak_pada,
            "tithi": tithi_name,
            "paksha": paksha,
            "sunrise_jd": sunrise_jd,
            "sunset_jd": sunset_jd,
            "moon_lon": moon_lon,
            "sun_lon": sun_lon
        }

    def calculate_chart(self, dt, lat: float, lon: float, tz_name: str, real_now_jd: float = None, transit_div: str = "D1", transit_planet: str = "Sun"):
        if isinstance(dt, dict) and 'year' in dt: jd_utc = dt_dict_to_utc_jd(dt, tz_name)
        elif isinstance(dt, dict) and 'jd' in dt: jd_utc = float(dt['jd'])
        else:
            try:
                local_tz = pytz.timezone(tz_name)
                if dt.tzinfo is None: dt = local_tz.localize(dt)
                dt_utc = dt.astimezone(pytz.utc)
                decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
                jd_utc = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)
            except Exception:
                jd_utc = dt_dict_to_utc_jd({'year': 2000, 'month': 1, 'day': 1}, tz_name)

        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        
        cusps, ascmc = safe_houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        asc_deg, asc_sign_index = ascmc[0], int(ascmc[0] / 30)
        
        asc_nak_name, asc_nak_lord, asc_nak_pada = get_nakshatra(asc_deg)
        chart_data = {
            "ascendant": {
                "degree": asc_deg, "sign_index": asc_sign_index, "sign_num": asc_sign_index + 1,
                "nakshatra": asc_nak_name, "nakshatra_lord": asc_nak_lord, "nakshatra_pada": asc_nak_pada
            }, 
            "planets": []
        }
        
        jd_prev_asc, jd_next_asc = self.find_adjacent_ascendant_transits(jd_utc, lat, lon, transit_div)
        jd_prev_p, jd_next_p = self.find_adjacent_planet_transits(jd_utc, transit_planet, transit_div)
        
        chart_data["prev_asc_jd"] = jd_prev_asc
        chart_data["next_asc_jd"] = jd_next_asc
        chart_data["prev_p_jd"] = jd_prev_p
        chart_data["next_p_jd"] = jd_next_p
        chart_data["current_jd"] = jd_utc

        exaltation_rules = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
        debilitation_rules = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
        sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}

        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            sign_in_house = (asc_sign_index + h - 1) % 12 + 1
            ruler = sign_rulers.get(sign_in_house)
            if ruler: planet_lordships[ruler].append(h)

        bodies = [("Sun", "Su", swe.SUN), ("Moon", "Mo", swe.MOON), ("Mars", "Ma", swe.MARS), ("Mercury", "Me", swe.MERCURY), ("Jupiter", "Ju", swe.JUPITER), ("Venus", "Ve", swe.VENUS), ("Saturn", "Sa", swe.SATURN), ("Rahu", "Ra", swe.TRUE_NODE)]

        for name, sym, body_id in bodies:
            res, _ = safe_calc_ut(jd_utc, body_id, calc_flag)
            lon_deg = res[0]
            speed = res[3]
            deg_in_sign = lon_deg % 30.0
            p_sign_idx = int(lon_deg / 30)
            p_sign_num = p_sign_idx + 1
            is_retro = speed < 0 if name not in ["Sun", "Moon", "Rahu", "Ketu"] else False
            if name == "Rahu": is_retro = True

            nak_name, nak_lord, nak_pada = get_nakshatra(lon_deg)

            is_exalted = False
            is_own = (sign_rulers.get(p_sign_num) == name)
            is_debilitated = (p_sign_num == debilitation_rules.get(name))
            
            if name == "Moon" and p_sign_num == 2:
                if deg_in_sign <= 3.0: is_exalted = True; is_own = False
                else: is_exalted = False; is_own = True
            elif name == "Mercury" and p_sign_num == 6:
                if deg_in_sign <= 15.0: is_exalted = True; is_own = False
                else: is_exalted = False; is_own = True
            else:
                is_exalted = (p_sign_num == exaltation_rules.get(name))
                
            if name == "Moon" and p_sign_num == 8:
                is_debilitated = (deg_in_sign <= 3.0)
            elif name == "Mercury" and p_sign_num == 12:
                is_debilitated = (deg_in_sign <= 15.0)

            chart_data["planets"].append({
                "name": name, "sym": sym, "lon": lon_deg, "sign_index": p_sign_idx, "sign_num": p_sign_num,
                "deg_in_sign": deg_in_sign, "house": (p_sign_idx - asc_sign_index) % 12 + 1, "retro": is_retro,
                "exalted": is_exalted, "debilitated": is_debilitated, 
                "own_sign": is_own, "lord_of": planet_lordships.get(name, []),
                "nakshatra": nak_name, "nakshatra_lord": nak_lord, "nakshatra_pada": nak_pada
            })

        rahu = next(p for p in chart_data["planets"] if p["name"] == "Rahu")
        ketu_lon = (rahu["lon"] + 180.0) % 360.0
        ketu_sign_idx = int(ketu_lon / 30)
        
        ketu_nak_name, ketu_nak_lord, ketu_nak_pada = get_nakshatra(ketu_lon)

        chart_data["planets"].append({
            "name": "Ketu", "sym": "Ke", "lon": ketu_lon, "sign_index": ketu_sign_idx, "sign_num": ketu_sign_idx + 1,
            "deg_in_sign": ketu_lon % 30, "house": (ketu_sign_idx - asc_sign_index) % 12 + 1, "retro": True,
            "exalted": (ketu_sign_idx + 1 == exaltation_rules.get("Ketu")), "debilitated": (ketu_sign_idx + 1 == debilitation_rules.get("Ketu")),
            "own_sign": False, "lord_of": [],
            "nakshatra": ketu_nak_name, "nakshatra_lord": ketu_nak_lord, "nakshatra_pada": ketu_nak_pada
        })

        sun_p = next((p for p in chart_data["planets"] if p["name"] == "Sun"), None)
        if sun_p:
            sun_lon = sun_p["lon"]
            combust_rules = {
                "Moon": {"dir": 12, "retro": 12}, "Mars": {"dir": 17, "retro": 17}, "Mercury": {"dir": 14, "retro": 12},
                "Jupiter": {"dir": 11, "retro": 11}, "Venus": {"dir": 10, "retro": 8}, "Saturn": {"dir": 15, "retro": 15}
            }
            
            for p in chart_data["planets"]:
                if p["name"] in combust_rules:
                    diff = abs(sun_lon - p["lon"])
                    if diff > 180.0: diff = 360.0 - diff
                    limit = combust_rules[p["name"]]["retro"] if p.get("retro") else combust_rules[p["name"]]["dir"]
                    p["combust"] = (diff <= limit)
                else:
                    p["combust"] = False
        else:
            for p in chart_data["planets"]: p["combust"] = False

        valid_ak_planets = [p for p in chart_data["planets"] if p["name"] not in ["Rahu", "Ketu"]]
        if valid_ak_planets:
            ak_planet = max(valid_ak_planets, key=lambda x: x["deg_in_sign"])
            for p in chart_data["planets"]:
                p["is_ak"] = (p["name"] == ak_planet["name"])

        moon_p = next((p for p in chart_data["planets"] if p["name"] == "Moon"), None)
        if moon_p:
            dasha_target = real_now_jd if real_now_jd else jd_utc
            dasha_info = self.calculate_vimshottari_dasha(jd_utc, moon_p["lon"], dasha_target)
            chart_data["dasha_sequence"] = dasha_info["current_sequence"] or []

        chart_data["aspects"] = self.calculate_vedic_aspects(chart_data["planets"])
        
        panchang = self.get_panchang(jd_utc, lat, lon)
        if panchang["sunrise_jd"]:
            sr_dt = utc_jd_to_dt_dict(panchang["sunrise_jd"], tz_name)
            panchang["sunrise_str"] = f"{sr_dt['hour']:02d}:{sr_dt['minute']:02d}"
        else: panchang["sunrise_str"] = "N/A"
        
        if panchang["sunset_jd"]:
            ss_dt = utc_jd_to_dt_dict(panchang["sunset_jd"], tz_name)
            panchang["sunset_str"] = f"{ss_dt['hour']:02d}:{ss_dt['minute']:02d}"
        else: panchang["sunset_str"] = "N/A"
        
        chart_data["panchang"] = panchang

        assign_functional_nature(chart_data["planets"])
        compute_house_metadata(chart_data)

        return chart_data

    def compute_divisional_chart(self, base_chart, div_type):
        chart = copy.deepcopy(base_chart)

        asc_d1_sign = chart["ascendant"]["sign_index"]
        asc_lon = (asc_d1_sign * 30.0) + (chart["ascendant"]["degree"] % 30.0)
        new_asc_sign_index, new_asc_div_lon = self.get_div_sign_and_lon(asc_lon, div_type)
        
        chart["ascendant"]["sign_index"] = new_asc_sign_index
        chart["ascendant"]["sign_num"] = new_asc_sign_index + 1
        chart["ascendant"]["div_lon"] = new_asc_div_lon
        chart["ascendant"]["vargottama"] = (asc_d1_sign == new_asc_sign_index) and (div_type != "D1")
        
        exaltation_rules = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
        debilitation_rules = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
        sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}

        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            sign_in_house = (new_asc_sign_index + h - 1) % 12 + 1
            ruler = sign_rulers.get(sign_in_house)
            if ruler: planet_lordships[ruler].append(h)

        for p in chart["planets"]:
            p_d1_sign = p["sign_index"]
            new_sign_idx, new_div_lon = self.get_div_sign_and_lon(p["lon"], div_type)
            new_sign_num = new_sign_idx + 1
            deg_in_div = new_div_lon % 30.0
            
            p["sign_index"] = new_sign_idx
            p["sign_num"] = new_sign_num
            p["div_lon"] = new_div_lon
            p["deg_in_sign"] = deg_in_div
            p["house"] = (new_sign_idx - new_asc_sign_index) % 12 + 1
            
            is_exalted = False
            is_own = (sign_rulers.get(new_sign_num) == p["name"])
            is_debilitated = (new_sign_num == debilitation_rules.get(p["name"]))
            
            if p["name"] == "Moon" and new_sign_num == 2:
                if deg_in_div <= 3.0: is_exalted = True; is_own = False
                else: is_exalted = False; is_own = True
            elif p["name"] == "Mercury" and new_sign_num == 6:
                if deg_in_div <= 15.0: is_exalted = True; is_own = False
                else: is_exalted = False; is_own = True
            else:
                is_exalted = (new_sign_num == exaltation_rules.get(p["name"]))
                
            if p["name"] == "Moon" and new_sign_num == 8:
                is_debilitated = (deg_in_div <= 3.0)
            elif p["name"] == "Mercury" and new_sign_num == 12:
                is_debilitated = (deg_in_div <= 15.0)

            p["exalted"] = is_exalted
            p["debilitated"] = is_debilitated
            p["own_sign"] = is_own
            p["lord_of"] = planet_lordships.get(p["name"], [])
            p["vargottama"] = (p_d1_sign == p["sign_index"]) and (div_type != "D1")
            
            if div_type != "D1": p["combust"] = False
            
        chart["aspects"] = self.calculate_vedic_aspects(chart["planets"])
        
        assign_functional_nature(chart["planets"])
        compute_house_metadata(chart)
        
        return chart