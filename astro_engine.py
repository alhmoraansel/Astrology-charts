# astro_engine.py
import swisseph as swe
import datetime
import pytz
import time
import math
import copy

# -------------------------
# Date utilities (astronomical year support)
# -------------------------
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

def format_astro_date(d):
    y = d['year']
    if y <= 0: return f"{1 - y} BCE {d['month']:02d}-{d['day']:02d} {d['hour']:02d}:{d['minute']:02d}:{int(d['second']):02d}"
    else: return f"{y} CE {d['month']:02d}-{d['day']:02d} {d['hour']:02d}:{d['minute']:02d}:{int(d['second']):02d}"

def dt_dict_to_utc_jd(dt_dict, tz_name):
    y, m, d = dt_dict['year'], dt_dict.get('month', 1), dt_dict.get('day', 1)
    h, mi, s = dt_dict.get('hour', 0), dt_dict.get('minute', 0), dt_dict.get('second', 0.0)
    local_tz = pytz.timezone(tz_name)
    offset_hours = 0.0
    try:
        if y > 0:
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
        if y > 0:
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


# ==========================================
# SINGLE-PROCESS HEURISTIC TRANSIT ENGINE
# ==========================================
def perform_transit_search(params, result_queue, stop_event):
    """Highly optimized background worker that returns UTC Julian Days uniformly"""
    try:
        swe.set_ephe_path('ephe')
        ayanamsa_modes = { "Lahiri": swe.SIDM_LAHIRI, "Raman": swe.SIDM_RAMAN, "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY }

        dt_param = params['dt']
        lat, lon, tz_name = params['lat'], params['lon'], params['tz_name']
        body_name, direction = params['body_name'], params['direction']
        target_sign_name, frozen_planets = params['target_sign_name'], params['frozen_planets']

        local_tz = pytz.timezone(tz_name)
        if isinstance(dt_param, dict) and 'year' in dt_param:
            jd_start = dt_dict_to_utc_jd(dt_param, tz_name)
        elif isinstance(dt_param, dict) and 'jd' in dt_param:
            jd_start = float(dt_param['jd'])
        else:
            dt_iso = dt_param if isinstance(dt_param, str) else params.get('dt')
            dt = datetime.datetime.fromisoformat(dt_iso)
            if dt.tzinfo is None: dt = local_tz.localize(dt)
            dt_utc = dt.astimezone(pytz.utc)
            decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
            jd_start = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)

        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        swe.set_sid_mode(ayanamsa_modes[params['ayanamsa']])
        body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}

        def get_sign(j, b_name):
            if b_name == "Ascendant":
                cusps, ascmc = swe.houses_ex(j, lat, lon, b'P', calc_flag)
                return int(ascmc[0] / 30.0)
            elif b_name == "Ketu":
                res, _ = swe.calc_ut(j, swe.TRUE_NODE, calc_flag)
                return int((res[0] + 180.0) % 360.0 / 30.0)
            else:
                res, _ = swe.calc_ut(j, body_map[b_name], calc_flag)
                return int(res[0] / 30.0)

        original_start_sign = get_sign(jd_start, body_name)
        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        target_sign = zodiac_names.index(target_sign_name) if target_sign_name and target_sign_name != "Any Rashi" else None

        constrained_planets = frozen_planets.copy()
        if target_sign is not None: constrained_planets[body_name] = target_sign

        must_leave_target = (target_sign is not None and original_start_sign == target_sign)

        def get_forward_dist(p, curr_s, target_s, d_dir):
            if p in ["Rahu", "Ketu"]: return (curr_s - target_s) * d_dir % 12
            else: return (target_s - curr_s) * d_dir % 12

        def calc_max_leap(jd_check, d_dir):
            max_leap = 0
            for p, target_s in constrained_planets.items():
                curr_s = get_sign(jd_check, p)
                if curr_s == target_s: continue
                dist = get_forward_dist(p, curr_s, target_s, d_dir)
                safe_days = {"Saturn": 750, "Rahu": 450, "Ketu": 450, "Jupiter": 300, "Mars": 35, "Sun": 27, "Venus": 20, "Mercury": 15, "Moon": 2, "Ascendant": 0.05}
                if 2 <= dist <= 11:
                    p_leap = (dist - 1.5) * safe_days.get(p, 0)
                    if p_leap > max_leap: max_leap = p_leap
            return max_leap

        step_map = {"Ascendant": 0.01, "Moon": 0.1, "Sun": 1.0, "Mercury": 1.0, "Venus": 1.0, "Mars": 2.0, "Jupiter": 5.0, "Saturn": 10.0, "Rahu": 10.0, "Ketu": 10.0}
        step = step_map.get(body_name, 10.0)
        inner_step = step
        for fp in frozen_planets.keys():
            if fp != body_name: inner_step = min(inner_step, step_map.get(fp, 10.0))

        jd = jd_start + (0.001 * direction)
        prev_sign = get_sign(jd - step * direction, body_name)
        loops = 0
        last_progress_time = time.time()

        while not stop_event.is_set():
            if jd < -1000000 or jd > 5000000:
                result_queue.put({"status": "error", "message": "Search reached extreme bounds (10,000+ years) without finding a match."})
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
                prev_sign = get_sign(jd - step * direction, body_name)
                continue

            current_sign = get_sign(jd, body_name)
            
            if must_leave_target and current_sign != target_sign:
                must_leave_target = False
                
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
                    mid_sign = get_sign(t_mid, body_name)
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
                        
                    m_sign = get_sign(jd_inner, body_name)
                    if target_sign is not None:
                        if m_sign != target_sign: break
                    else:
                        if m_sign != current_sign: break

                    f_ok = True
                    for fp_name, f_sign_idx in frozen_planets.items():
                        if fp_name != body_name and get_sign(jd_inner, fp_name) != f_sign_idx:
                            f_ok = False; break

                    if f_ok: found_jd, window_match = jd_inner, True; break
                    jd_inner += inner_step * direction

                if window_match:
                    t1_final, t2_final = found_jd - inner_step * direction, found_jd
                    for _ in range(20):
                        t_mid = (t1_final + t2_final) / 2.0
                        m_sign = get_sign(t_mid, body_name)
                        c_ok = False
                        if target_sign is not None:
                            if m_sign == target_sign: c_ok = True
                        else:
                            if m_sign == current_sign: c_ok = True

                        if c_ok:
                            for fp_name, f_sign_idx in frozen_planets.items():
                                if fp_name != body_name and get_sign(t_mid, fp_name) != f_sign_idx:
                                    c_ok = False; break
                        if c_ok: t2_final = t_mid
                        else: t1_final = t_mid

                    result_queue.put({"status": "success", "result_jd_utc": float(t2_final)})
                    return
                else:
                    jd, current_sign = jd_inner, get_sign(jd_inner, body_name)

            prev_sign = current_sign
            jd += step * direction

        result_queue.put({"status": "stopped"})
    except Exception as e:
        result_queue.put({"status": "error", "message": str(e)})


# ==========================================
# EPHEMERIS CHART CALCULATOR ENGINE
# ==========================================
class EphemerisEngine:
    def __init__(self):
        swe.set_ephe_path('ephe')
        self.ayanamsa_modes = {"Lahiri": swe.SIDM_LAHIRI, "Raman": swe.SIDM_RAMAN, "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY}
        self.current_ayanamsa = "Lahiri"

    def set_ayanamsa(self, name):
        if name in self.ayanamsa_modes: self.current_ayanamsa = name

    def get_ascendant_sign(self, jd_utc, lat, lon):
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        return int(ascmc[0] / 30)

    def find_adjacent_ascendant_transits(self, jd_utc, lat, lon):
        orig_sign = self.get_ascendant_sign(jd_utc, lat, lon)
        
        jd_next = jd_utc
        for _ in range(300):
            jd_next += 0.01
            if self.get_ascendant_sign(jd_next, lat, lon) != orig_sign: break
        
        t1, t2 = jd_next - 0.01, jd_next
        for _ in range(12):
            tm = (t1 + t2) / 2.0
            if self.get_ascendant_sign(tm, lat, lon) != orig_sign: t2 = tm
            else: t1 = tm
        jd_next_exact = t2
        
        jd_prev = jd_utc
        for _ in range(300):
            jd_prev -= 0.01
            if self.get_ascendant_sign(jd_prev, lat, lon) != orig_sign: break
                
        t1, t2 = jd_prev, jd_prev + 0.01
        for _ in range(12):
            tm = (t1 + t2) / 2.0
            if self.get_ascendant_sign(tm, lat, lon) != orig_sign: t1 = tm
            else: t2 = tm
        jd_prev_exact = t1
        
        return jd_prev_exact, jd_next_exact

    def calculate_chart(self, dt, lat: float, lon: float, tz_name: str):
        if isinstance(dt, dict) and 'year' in dt: jd_utc = dt_dict_to_utc_jd(dt, tz_name)
        elif isinstance(dt, dict) and 'jd' in dt: jd_utc = float(dt['jd'])
        else:
            local_tz = pytz.timezone(tz_name)
            if dt.tzinfo is None: dt = local_tz.localize(dt)
            dt_utc = dt.astimezone(pytz.utc)
            decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
            jd_utc = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)

        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        
        cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        asc_deg, asc_sign_index = ascmc[0], int(ascmc[0] / 30)
        
        chart_data = {"ascendant": {"degree": asc_deg, "sign_index": asc_sign_index, "sign_num": asc_sign_index + 1}, "planets": []}
        
        jd_prev_asc, jd_next_asc = self.find_adjacent_ascendant_transits(jd_utc, lat, lon)
        chart_data["prev_asc_jd"] = jd_prev_asc
        chart_data["next_asc_jd"] = jd_next_asc
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
            res, _ = swe.calc_ut(jd_utc, body_id, calc_flag)
            lon_deg = res[0]
            speed = res[3]
            p_sign_idx = int(lon_deg / 30)
            p_sign_num = p_sign_idx + 1
            
            is_retro = speed < 0 if name not in ["Sun", "Moon", "Rahu", "Ketu"] else False
            if name == "Rahu": is_retro = True

            chart_data["planets"].append({
                "name": name, "sym": sym, "lon": lon_deg, "sign_index": p_sign_idx, "sign_num": p_sign_num,
                "deg_in_sign": lon_deg % 30, "house": (p_sign_idx - asc_sign_index) % 12 + 1, "retro": is_retro,
                "exalted": (p_sign_num == exaltation_rules.get(name)), "debilitated": (p_sign_num == debilitation_rules.get(name)), 
                "own_sign": (sign_rulers.get(p_sign_num) == name), "lord_of": planet_lordships.get(name, [])
            })

        rahu = next(p for p in chart_data["planets"] if p["name"] == "Rahu")
        ketu_lon = (rahu["lon"] + 180.0) % 360.0
        ketu_sign_idx = int(ketu_lon / 30)
        
        chart_data["planets"].append({
            "name": "Ketu", "sym": "Ke", "lon": ketu_lon, "sign_index": ketu_sign_idx, "sign_num": ketu_sign_idx + 1,
            "deg_in_sign": ketu_lon % 30, "house": (ketu_sign_idx - asc_sign_index) % 12 + 1, "retro": True,
            "exalted": (ketu_sign_idx + 1 == exaltation_rules.get("Ketu")), "debilitated": (ketu_sign_idx + 1 == debilitation_rules.get("Ketu")),
            "own_sign": False, "lord_of": []
        })

        sun_p = next((p for p in chart_data["planets"] if p["name"] == "Sun"), None)
        sun_lon = sun_p["lon"] if sun_p else 0.0
        combust_rules = {"Moon": {"dir": 12, "retro": 12}, "Mercury": {"dir": 14, "retro": 12}, "Venus": {"dir": 10, "retro": 8},
                         "Mars": {"dir": 17, "retro": 17}, "Jupiter": {"dir": 11, "retro": 11}, "Saturn": {"dir": 15, "retro": 15}}
        
        for p in chart_data["planets"]:
            if p["name"] in combust_rules:
                dist = min(abs(p["lon"] - sun_lon), 360.0 - abs(p["lon"] - sun_lon))
                p["combust"] = (dist <= (combust_rules[p["name"]]["retro"] if p["retro"] else combust_rules[p["name"]]["dir"]))
            else: p["combust"] = False

        chart_data["aspects"] = self.calculate_vedic_aspects(chart_data["planets"])
        return chart_data

    def compute_divisional_chart(self, base_chart, div_type):
        """Generates dynamic divisional charts scaled using strict integer milliarcseconds to eliminate floating-point boundary errors."""
        chart = copy.deepcopy(base_chart)

        def get_div_sign_and_lon(lon_deg, div_type):
            # Convert longitude to absolute milli-arcseconds (mas) mathematically bypassing 1e-9 float issues entirely
            # 1 degree = 60 mins = 3600 secs = 3,600,000 mas. 
            # 1 Sign (30 degrees) = 108,000,000 mas.
            total_mas = int(round(lon_deg * 3600000.0))
            sign_index = (total_mas // 108000000) % 12
            mas_in_sign = total_mas % 108000000
            deg_in_sign = mas_in_sign / 3600000.0
            
            if div_type == "D1":
                return sign_index, lon_deg
                
            elif div_type == "D9":
                # Navamsha: 1 segment = 3°20' = 12,000,000 mas
                segment = mas_in_sign // 12000000
                rem_mas = mas_in_sign % 12000000
                deg_in_div_sign = (rem_mas / 12000000.0) * 30.0
                
                # Fire(0,4,8)->Aries(0), Earth(1,5,9)->Cap(9), Air(2,6,10)->Libra(6), Water(3,7,11)->Cancer(3)
                element = sign_index % 4
                start_sign = [0, 9, 6, 3][element]
                div_sign_index = (start_sign + segment) % 12
                
            elif div_type == "D10":
                # Dashamsha: 1 segment = 3°00' = 10,800,000 mas
                segment = mas_in_sign // 10800000
                rem_mas = mas_in_sign % 10800000
                deg_in_div_sign = (rem_mas / 10800000.0) * 30.0
                
                # Odd -> Starts at sign itself. Even -> Starts 9th from sign (sign_index + 8)
                is_odd = (sign_index % 2 == 0)
                start_sign = sign_index if is_odd else (sign_index + 8)
                div_sign_index = (start_sign + segment) % 12
                
            elif div_type == "D20":
                # Vimshamsha: 1 segment = 1°30' = 5,400,000 mas
                segment = mas_in_sign // 5400000
                rem_mas = mas_in_sign % 5400000
                deg_in_div_sign = (rem_mas / 5400000.0) * 30.0
                
                # Movable(0,3,6,9)->Aries(0), Fixed(1,4,7,10)->Sag(8), Dual(2,5,8,11)->Leo(4)
                modality = sign_index % 3
                start_sign = [0, 8, 4][modality]
                div_sign_index = (start_sign + segment) % 12
                
            elif div_type == "D30":
                # Trimshamsha relies on thresholds
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
                    
            elif div_type == "D60":
                # Shashtiamsha: 1 segment = 0°30' = 1,800,000 mas
                segment = mas_in_sign // 1800000
                rem_mas = mas_in_sign % 1800000
                deg_in_div_sign = (rem_mas / 1800000.0) * 30.0
                
                # Standard Parashari D60 spans completely continuously from the base sign 
                div_sign_index = (sign_index + segment) % 12
                
            else:
                div_sign_index = sign_index
                deg_in_div_sign = deg_in_sign

            return div_sign_index, div_sign_index * 30.0 + deg_in_div_sign

        # Re-derive the Ascendant
        asc_d1_sign = chart["ascendant"]["sign_index"]
        asc_lon = (asc_d1_sign * 30.0) + (chart["ascendant"]["degree"] % 30.0)
        new_asc_sign_index, new_asc_div_lon = get_div_sign_and_lon(asc_lon, div_type)
        
        chart["ascendant"]["sign_index"] = new_asc_sign_index
        chart["ascendant"]["sign_num"] = new_asc_sign_index + 1
        
        # Storing divisional longitude cleanly enables Circular Charts to draw the planets proportionally
        chart["ascendant"]["div_lon"] = new_asc_div_lon
        
        # Set Vargottama directly if it matches D1 sign
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
            new_sign_idx, new_div_lon = get_div_sign_and_lon(p["lon"], div_type)
            
            p["sign_index"] = new_sign_idx
            p["sign_num"] = new_sign_idx + 1
            p["div_lon"] = new_div_lon
            p["house"] = (new_sign_idx - new_asc_sign_index) % 12 + 1
            
            p["exalted"] = (p["sign_num"] == exaltation_rules.get(p["name"]))
            p["debilitated"] = (p["sign_num"] == debilitation_rules.get(p["name"]))
            p["own_sign"] = (sign_rulers.get(p["sign_num"]) == p["name"])
            p["lord_of"] = planet_lordships.get(p["name"], [])
            
            # Flag Vargottama onto individual planets
            p["vargottama"] = (p_d1_sign == p["sign_index"]) and (div_type != "D1")
            
        chart["aspects"] = self.calculate_vedic_aspects(chart["planets"])
        return chart

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