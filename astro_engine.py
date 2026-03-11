import swisseph as swe
import datetime
import pytz
import time

# ==========================================
# SINGLE-PROCESS HEURISTIC TRANSIT ENGINE
# ==========================================

def perform_transit_search(params, result_queue, stop_event):
    """
    Highly optimized background worker that calculates orbital distances 
    to skip 'dead' years instantly without needing nested multiprocessing.
    """
    try:
        swe.set_ephe_path('ephe')
        ayanamsa_modes = {
            "Lahiri": swe.SIDM_LAHIRI,
            "Raman": swe.SIDM_RAMAN,
            "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY
        }

        dt_iso = params['dt']
        lat = params['lat']
        lon = params['lon']
        tz_name = params['tz_name']
        body_name = params['body_name']
        direction = params['direction']
        target_sign_name = params['target_sign_name']
        frozen_planets = params['frozen_planets']
        current_ayanamsa = params['ayanamsa']

        dt = datetime.datetime.fromisoformat(dt_iso)
        local_tz = pytz.timezone(tz_name)
        if dt.tzinfo is None: dt = local_tz.localize(dt)
        dt_utc = dt.astimezone(pytz.utc)

        decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        jd_start = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)

        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        swe_mode = ayanamsa_modes[current_ayanamsa]
        swe.set_sid_mode(swe_mode)

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

        zodiac_names = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", 
                        "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        target_sign = None
        if target_sign_name and target_sign_name != "Any Rashi":
            if target_sign_name in zodiac_names:
                target_sign = zodiac_names.index(target_sign_name)

        # Merge constraints to heavily optimize jumping
        constrained_planets = frozen_planets.copy()
        if target_sign is not None:
            constrained_planets[body_name] = target_sign

        def get_forward_dist(p, curr_s, target_s, d_dir):
            if p in ["Rahu", "Ketu"]:
                return (curr_s - target_s) * d_dir % 12
            else:
                return (target_s - curr_s) * d_dir % 12

        def calc_max_leap(jd_check, d_dir):
            """Calculates the absolute maximum safe jump based on the slowest planet's distance to target."""
            max_leap = 0
            for p, target_s in constrained_planets.items():
                curr_s = get_sign(jd_check, p)
                if curr_s == target_s:
                    continue
                dist = get_forward_dist(p, curr_s, target_s, d_dir)
                
                # Minimum days guaranteed per sign (safely truncated to avoid retrograde overshoots)
                safe_days = {
                    "Saturn": 750, "Rahu": 450, "Ketu": 450, "Jupiter": 300,
                    "Mars": 35, "Sun": 27, "Venus": 20, "Mercury": 15, "Moon": 2, "Ascendant": 0.05
                }
                
                # Buffer of 1.5 signs to ensure we NEVER leap over the target entry boundary
                if 2 <= dist <= 11:
                    p_leap = (dist - 1.5) * safe_days.get(p, 0)
                    if p_leap > max_leap:
                        max_leap = p_leap
            return max_leap

        step_map = {
            "Ascendant": 0.01, "Moon": 0.1, "Sun": 1.0, "Mercury": 1.0, "Venus": 1.0,
            "Mars": 2.0, "Jupiter": 5.0, "Saturn": 10.0, "Rahu": 10.0, "Ketu": 10.0
        }

        step = step_map.get(body_name, 10.0)
        inner_step = step
        for fp in frozen_planets.keys():
            if fp != body_name:
                inner_step = min(inner_step, step_map.get(fp, 10.0))

        jd = jd_start + (0.001 * direction)
        prev_sign = get_sign(jd - step * direction, body_name)
        
        loops = 0
        last_progress_time = time.time()

        while not stop_event.is_set():
            if jd < 0 or jd > 5000000:
                result_queue.put({"status": "error", "message": "Search reached extreme astronomical bounds (10,000+ years) without finding a match."})
                return

            loops += 1
            # Update UI gently to prevent locking the queue
            if loops % 50 == 0:
                now = time.time()
                if now - last_progress_time > 0.3:  # Push UI update ~3 times a second
                    year, month, day, _ = swe.revjul(jd, 1)
                    result_queue.put({"status": "progress", "date": f"{int(year)}-{int(month):02d}-{int(day):02d}"})
                    last_progress_time = now

            # -- ORBITAL HEURISTIC LEAP --
            leap_days = calc_max_leap(jd, direction)
            if leap_days > 15:
                jd += leap_days * direction
                prev_sign = get_sign(jd - step * direction, body_name)
                continue # Skip step and re-evaluate from the future/past instantly

            current_sign = get_sign(jd, body_name)

            transitioned_in = False
            if target_sign is not None:
                if current_sign == target_sign and prev_sign != target_sign:
                    transitioned_in = True
            else:
                if current_sign != prev_sign and current_sign != original_start_sign:
                    transitioned_in = True

            if transitioned_in:
                t1 = jd - step * direction
                t2 = jd
                # Binary search exact entry boundary
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

                jd_inner = t2
                window_match = False

                # Scan the valid window bounds fully to intersect with frozen planets
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
                            f_ok = False
                            break

                    if f_ok:
                        found_jd = jd_inner
                        window_match = True
                        break

                    jd_inner += inner_step * direction

                if window_match:
                    # Precise compound intersection pin-pointer
                    t1_final = found_jd - inner_step * direction
                    t2_final = found_jd
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
                                    c_ok = False
                                    break

                        if c_ok: t2_final = t_mid
                        else: t1_final = t_mid

                    year, month, day, hour = swe.revjul(t2_final, 1)
                    h = int(hour); m = int((hour - h) * 60); s = int((((hour - h) * 60) - m) * 60)
                    try:
                        dt_utc_transit = datetime.datetime(year, month, day, h, m, s, tzinfo=pytz.utc)
                        final_dt = dt_utc_transit.astimezone(local_tz).replace(tzinfo=None)
                        result_queue.put({"status": "success", "result": final_dt.isoformat()})
                    except ValueError:
                        result_queue.put({"status": "error", "message": f"Found match out of bounds (Year {year})."})
                    return
                else:
                    # Target left the sign before the freeze constraint was met. Skip past window safely.
                    jd = jd_inner
                    current_sign = get_sign(jd, body_name)

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
        self.ayanamsa_modes = {
            "Lahiri": swe.SIDM_LAHIRI,
            "Raman": swe.SIDM_RAMAN,
            "Fagan/Bradley": swe.SIDM_FAGAN_BRADLEY
        }
        self.current_ayanamsa = "Lahiri"

    def set_ayanamsa(self, name):
        if name in self.ayanamsa_modes:
            self.current_ayanamsa = name

    def calculate_chart(self, dt: datetime.datetime, lat: float, lon: float, tz_name: str):
        local_tz = pytz.timezone(tz_name)
        if dt.tzinfo is None: dt = local_tz.localize(dt)
        dt_utc = dt.astimezone(pytz.utc)
        
        decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        jd_utc = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)

        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        
        cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        asc_deg = ascmc[0]
        asc_sign_index = int(asc_deg / 30)
        
        chart_data = {
            "ascendant": {"degree": asc_deg, "sign_index": asc_sign_index, "sign_num": asc_sign_index + 1},
            "planets": []
        }

        exaltation_rules = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
        debilitation_rules = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
        sign_rulers = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}

        planet_lordships = {p: [] for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]}
        for h in range(1, 13):
            sign_in_house = (asc_sign_index + h - 1) % 12 + 1
            ruler = sign_rulers.get(sign_in_house)
            if ruler: planet_lordships[ruler].append(h)

        bodies = [
            ("Sun", "Su", swe.SUN), ("Moon", "Mo", swe.MOON), ("Mars", "Ma", swe.MARS), ("Mercury", "Me", swe.MERCURY),
            ("Jupiter", "Ju", swe.JUPITER), ("Venus", "Ve", swe.VENUS), ("Saturn", "Sa", swe.SATURN), ("Rahu", "Ra", swe.TRUE_NODE)
        ]

        for name, sym, body_id in bodies:
            res, _ = swe.calc_ut(jd_utc, body_id, calc_flag)
            lon_deg = res[0]
            speed = res[3]
            
            p_sign_idx = int(lon_deg / 30)
            p_sign_num = p_sign_idx + 1
            deg_in_sign = lon_deg % 30
            is_retro = speed < 0 if name not in ["Sun", "Moon", "Rahu", "Ketu"] else False
            if name == "Rahu": is_retro = True

            house_num = (p_sign_idx - asc_sign_index) % 12 + 1
            
            exalted = (p_sign_num == exaltation_rules.get(name))
            debilitated = (p_sign_num == debilitation_rules.get(name))
            own_sign = (sign_rulers.get(p_sign_num) == name)

            chart_data["planets"].append({
                "name": name, "sym": sym, "lon": lon_deg, "sign_index": p_sign_idx, "sign_num": p_sign_num,
                "deg_in_sign": deg_in_sign, "house": house_num, "retro": is_retro,
                "exalted": exalted, "debilitated": debilitated, "own_sign": own_sign, "lord_of": planet_lordships.get(name, [])
            })

        rahu = next(p for p in chart_data["planets"] if p["name"] == "Rahu")
        ketu_lon = (rahu["lon"] + 180.0) % 360.0
        ketu_sign_idx = int(ketu_lon / 30)
        ketu_sign_num = ketu_sign_idx + 1
        ketu_deg_in_sign = ketu_lon % 30
        ketu_house = (ketu_sign_idx - asc_sign_index) % 12 + 1
        
        chart_data["planets"].append({
            "name": "Ketu", "sym": "Ke", "lon": ketu_lon, "sign_index": ketu_sign_idx, "sign_num": ketu_sign_num,
            "deg_in_sign": ketu_deg_in_sign, "house": ketu_house, "retro": True,
            "exalted": (ketu_sign_num == exaltation_rules.get("Ketu")), "debilitated": (ketu_sign_num == debilitation_rules.get("Ketu")),
            "own_sign": False, "lord_of": []
        })

        sun_p = next((p for p in chart_data["planets"] if p["name"] == "Sun"), None)
        sun_lon = sun_p["lon"] if sun_p else 0.0
        combust_rules = {"Moon": {"dir": 12, "retro": 12}, "Mercury": {"dir": 14, "retro": 12}, "Venus": {"dir": 10, "retro": 8},
                         "Mars": {"dir": 17, "retro": 17}, "Jupiter": {"dir": 11, "retro": 11}, "Saturn": {"dir": 15, "retro": 15}}
        
        for p in chart_data["planets"]:
            if p["name"] in combust_rules:
                dist = abs(p["lon"] - sun_lon)
                dist = min(dist, 360.0 - dist)
                limit = combust_rules[p["name"]]["retro"] if p["retro"] else combust_rules[p["name"]]["dir"]
                p["combust"] = (dist <= limit)
            else: p["combust"] = False

        chart_data["aspects"] = self.calculate_vedic_aspects(chart_data["planets"])
        return chart_data

    def calculate_vedic_aspects(self, planets):
        aspects = []
        aspect_rules = {"Sun": [7], "Moon": [7], "Mercury": [7], "Venus": [7], "Mars": [4, 7, 8], "Jupiter": [5, 7, 9], "Saturn": [3, 7, 10], "Rahu": [5, 7, 9], "Ketu": [5, 7, 9]}
        planet_colors = {"Sun": "orange", "Moon": "blue", "Mars": "red", "Mercury": "green", "Jupiter": "yellow", "Venus": "pink", "Saturn": "purple", "Rahu": "gray", "Ketu": "gray"}

        for p in planets:
            p_name = p["name"]
            p_house = p["house"]
            rules = aspect_rules.get(p_name, [])
            for aspect_count in rules:
                target_house = (p_house + aspect_count - 2) % 12 + 1
                aspects.append({"aspecting_planet": p_name, "source_house": p_house, "target_house": target_house, "aspect_count": aspect_count, "color": planet_colors.get(p_name, "white")})
        return aspects