# rectification_engine.py

import os, sys, pytz
import swisseph as swe
from astro_engine import (
    swe_lock,
    EphemerisEngine,
    dt_dict_to_utc_jd,
    utc_jd_to_dt_dict,
    safe_calc_ut,
    safe_houses_ex
)
from dynamic_settings_modules.zzlogger_mod import error_print

# ==========================================
# RESOURCE / PATH RESOLVER FOR PYINSTALLER
# ==========================================
def get_standalone_resource_path(relative_path):
    try:
        if hasattr(sys, '_MEIPASS'):
            res_path = os.path.join(sys._MEIPASS, relative_path)
            if os.path.exists(res_path): return res_path
        if getattr(sys, 'frozen', False) or '__compiled__' in globals():
            res_path = os.path.join(os.path.dirname(sys.executable), relative_path)
            if os.path.exists(res_path): return res_path
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)
    except Exception as e:
        print(f"[DEBUG - RECTIFICATION] Fallback error resolving resource path: {e}")
        return relative_path

# ==========================================
# DIVISIONAL D-CHART RECTIFIER
# ==========================================
class DivisionalRectifier:
    """Strictly isolated engine just for handling complex Varga chart reverse-searches."""
    def __init__(self, params, result_queue, stop_event, mode_str):
        self.params = params
        self.result_queue = result_queue
        self.stop_event = stop_event
        self.mode_str = mode_str
        
        self.engine = EphemerisEngine()
        self.engine.set_ayanamsa(params['ayanamsa'])
        self.engine.set_custom_vargas(params.get('custom_vargas', {}))
        
        try:
            if params['ayanamsa'] in self.engine.ayanamsa_modes:
                with swe_lock:
                    swe.set_sid_mode(self.engine.ayanamsa_modes[params['ayanamsa']])
            else:
                raise ValueError(f"Ayanamsa '{params['ayanamsa']}' is not mapped.")
        except Exception as e:
            self.result_queue.put({"status": "error", "message": f"Ayanamsa setup failed: {str(e)}"})
            return

        self.calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        self.body_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN, "Rahu": swe.TRUE_NODE, "Ketu": swe.TRUE_NODE}
        self.div_type = params['div_type']
        self.div_factor = params['custom_vargas'][self.div_type].get("parts", 1) if self.div_type in params.get('custom_vargas', {}) else int(self.div_type[1:])
        self.window_deg = 30.0 / self.div_factor
        self.max_speeds = {"Saturn": 0.25, "Jupiter": 0.35, "Rahu": 0.2, "Ketu": 0.2, "Mars": 1.2, "Sun": 1.2, "Venus": 1.8, "Mercury": 3.5, "Moon": 16.5, "Ascendant": 500.0}

    def get_sign_idx(self, jd, name):
        if name == "Ascendant":
            asc_res = safe_houses_ex(jd, self.params['lat'], self.params['lon'], b'P', self.calc_flag)
            return self.engine.get_div_sign_and_lon(asc_res[1][0], self.div_type)[0]
        elif name == "Ketu":
            res = safe_calc_ut(jd, swe.TRUE_NODE, self.calc_flag)
            return self.engine.get_div_sign_and_lon((res[0][0] + 180.0) % 360.0, self.div_type)[0]
        else:
            res = safe_calc_ut(jd, self.body_map[name], self.calc_flag)
            return self.engine.get_div_sign_and_lon(res[0][0], self.div_type)[0]

    def search(self):
        #print(f"\n[DEBUG - DIV RECT] >>> EXHAUSTIVE DIVISIONAL TRACING ENABLED FOR {self.div_type} <<<")
        print(f"[DEBUG - DIV RECT] Division Factor: {self.div_factor} | Window Deg: {self.window_deg}")
        
        checks = []
        for p in ["Saturn", "Rahu", "Ketu", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon", "Ascendant"]:
            if p == "Ascendant" and self.params['target_asc'] is not None: checks.append((p, self.params['target_asc']))
            elif p in self.params['target_planets']: checks.append((p, self.params['target_planets'][p]))
                
        origin_jd = dt_dict_to_utc_jd({'year': self.params['base_year'], 'month': 1, 'day': 1}, self.params['tz'])
        
        # Exact Boundary Mathematics Dump for diagnostic tracking
        print(f"\n[DEBUG - DIV RECT] --- ORIGIN BOUNDARY CHECK (Jan 1, {self.params['base_year']}) ---")
        for p_name, t_sign in checks:
            test_val = self.get_sign_idx(origin_jd, p_name)
            print(f"  -> {p_name} sits at Sign Index: {test_val} (Target is {t_sign})")
        print(f"----------------------------------------------------\n")

        search_range = self.params.get('search_range', 1000)
        start_range = self.params.get('start_range', 0)
        
        for i in range(start_range, search_range + 1):
            offsets = [i, -i] if i != 0 else [0]
            year_matches = []
            
            for offset in offsets:
                year = self.params['base_year'] + offset
                if offset % 10 == 0 and offset >= 0: 
                    self.result_queue.put({"status": "progress", "msg": f"Cascading Search: Shell +/- {i} Years (Processing {year})..."})
                
                start_win = dt_dict_to_utc_jd({'year': year, 'month': 1, 'day': 1}, self.params['tz'])
                end_win = dt_dict_to_utc_jd({'year': year+1, 'month': 1, 'day': 1}, self.params['tz'])
                windows = [(start_win, end_win)]

                trace_eliminations = (i == 0) # Only intensely log the base year to avoid log-spam

                if trace_eliminations:
                    print(f"\n[DEBUG - DIV RECT] --- TRACING WINDOW ELIMINATIONS FOR BASE YEAR {year} ---")

                for p_name, t_sign in checks:
                    if not windows: 
                        if trace_eliminations: print(f"  [!] YEAR COMPLETELY ELIMINATED BY: {p_name}")
                        break 
                        
                    calc_step = (self.window_deg / 500.0) * 0.25 if p_name == "Ascendant" else (self.window_deg / self.max_speeds.get(p_name, 1.0)) * 0.25
                    safe_step = max(calc_step, 5.0 / 86400.0 if p_name == "Ascendant" else 60.0 / 86400.0) 
                        
                    new_windows = []
                    for w_start, w_end in windows:
                        t = w_start
                        in_match = False
                        m_start = None
                        
                        while True:
                            if self.stop_event.is_set(): return
                                
                            check_t = min(t, w_end)
                            is_match = (self.get_sign_idx(check_t, p_name) == t_sign)
                            
                            if is_match and not in_match: 
                                t0, t1 = max(w_start, check_t - safe_step), check_t
                                if self.get_sign_idx(t0, p_name) == t_sign: m_start = t0
                                else:
                                    for _ in range(15):
                                        tm = (t0 + t1) / 2.0
                                        if self.get_sign_idx(tm, p_name) == t_sign: t1 = tm
                                        else: t0 = tm
                                    m_start = t1
                                in_match = True
                                
                            elif not is_match and in_match: 
                                t0, t1 = check_t - safe_step, check_t
                                for _ in range(15):
                                    tm = (t0 + t1) / 2.0
                                    if self.get_sign_idx(tm, p_name) == t_sign: t0 = tm
                                    else: t1 = tm
                                new_windows.append((m_start, t0))
                                in_match = False
                                
                            if t >= w_end:
                                if in_match: new_windows.append((m_start, w_end))
                                break
                                
                            prev_t = t
                            t += safe_step
                            if t == prev_t: t += 0.0001
                            
                    merged_windows = []
                    for w in new_windows:
                        if not merged_windows: merged_windows.append(w)
                        else:
                            last = merged_windows[-1]
                            if w[0] <= last[1] + (10.0 / 86400.0): merged_windows[-1] = (last[0], max(last[1], w[1]))
                            else: merged_windows.append(w)
                    
                    if trace_eliminations:
                        print(f"  -> Applied {p_name} (Sign {t_sign}): Left with {len(merged_windows)} windows.")
                    windows = merged_windows

                if windows:
                    for w in windows:
                        year_matches.append({
                            "start": utc_jd_to_dt_dict(w[0], self.params['tz']), 
                            "end": utc_jd_to_dt_dict(w[1], self.params['tz']), 
                            "start_jd": w[0], "end_jd": w[1], "mid_jd": (w[0] + w[1]) / 2.0
                        })

            if year_matches:
                year_matches.sort(key=lambda x: abs(x["mid_jd"] - origin_jd))
                print(f"[DEBUG - DIV RECT] MATCH FOUND at depth +/- {i} years!")
                self.result_queue.put({"status": "success", "year": f"+/- {i}", "blocks": year_matches})
                return
                
        self.result_queue.put({"status": "phase1_failed", "message": f"Mathematical cascade scan finished +/- {search_range} years. No matches found.", "last_range": search_range})


# ==========================================
# NATAL D1 RECTIFIER
# ==========================================
class NatalRectifier(DivisionalRectifier):
    """Reuses the framework but strictly isolated for Natal (D1) logic context tagging."""
    def search(self):
        print(f"\n[DEBUG - NATAL RECT] Processing D1 Search Logic...")
        super().search()


# ==========================================
# RECTIFICATION ENGINE MAIN WRAPPER
# ==========================================
def perform_rectification_search(params, result_queue, stop_event):
    is_compiled = getattr(sys, 'frozen', False) or '__compiled__' in globals()
    mode_str = "EXPORTED APP" if is_compiled else "DEBUG MODE"
    
    print(f"\n{'='*60}")
    print(f"[DEBUG - RECTIFICATION ENGINE] Booting Lock-Pick Sequence")
    print(f"[DEBUG - RECTIFICATION ENGINE] EXECUTION ENVIRONMENT: >>> {mode_str} <<<")
    print(f"[DEBUG - RECTIFICATION ENGINE] Full UI Params: {params}")
    print(f"{'='*60}")
    
    try:
        import pytz
        pytz.timezone(params['tz'])
        print(f"[DEBUG - RECTIFICATION] PYTZ Audit: Database contains '{params['tz']}' successfully.")
    except Exception as e:
        error_print(f"[CRITICAL ERROR] PYTZ Audit FAILED for '{params['tz']}': {e}")
        error_print(f"[CRITICAL ERROR] The exported app is MISSING TIMEZONE DATA! Timezones defaulting strictly to UTC!")

    with swe_lock:
        ephe_path = get_standalone_resource_path('ephe')
        swe.set_ephe_path(ephe_path)
        print(f"[DEBUG - RECTIFICATION] Swisseph Path Injected: {ephe_path}")
        try:
            files = os.listdir(ephe_path)
            se1_files = [f for f in files if f.endswith('.se1')]
            print(f"[DEBUG - RECTIFICATION] Ephe Folder Audit: Found {len(se1_files)} .se1 precision files.")
            if len(se1_files) == 0:
                print(f"[CRITICAL WARNING] Directory exists but is EMPTY of .se1 files! Moshier Fallback guaranteed!")
        except Exception as e:
            print(f"[CRITICAL WARNING] Ephe directory is completely inaccessible or missing! Error: {e}")

    # Branch routing based on Div Type
    if params['div_type'] == "D1":
        rectifier = NatalRectifier(params, result_queue, stop_event, mode_str)
    else:
        rectifier = DivisionalRectifier(params, result_queue, stop_event, mode_str)
        
    rectifier.search()