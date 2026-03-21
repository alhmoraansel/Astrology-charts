
class ShadbalaCalculator:
    def __init__(self, base_chart, varga_charts, app):
        self.base_chart = base_chart or {}
        self.varga_charts = varga_charts or {}
        self.app = app
        self.planets_list = self.base_chart.get("planets", [])
        self.valid_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        
        self.lat = float(getattr(self.app, "current_lat", 28.6139))
        self.lon = float(getattr(self.app, "current_lon", 77.2090))
        
        self.dt = getattr(self.app, "current_datetime", datetime.datetime.now())
        provided_jd = self.base_chart.get("current_jd")
        
        # self.cur_jd is ALWAYS treated as the UTC Julian Day in this class
        if provided_jd is not None and float(provided_jd) > 0.0:
            self.cur_jd = float(provided_jd)
        else:
            if swe:
                h = self.dt.hour + self.dt.minute / 60.0 + self.dt.second / 3600.0
                local_jd_temp = swe.julday(self.dt.year, self.dt.month, self.dt.day, h)
                tz = self._get_tz_offset()
                self.cur_jd = local_jd_temp - (tz / 24.0)
            else:
                self.cur_jd = 2451545.0 + (self.dt - datetime.datetime(2000, 1, 1, 12)).total_seconds() / 86400.0

        if not (625000.5 <= self.cur_jd <= 2818000.5):
            raise ValueError(f"Invalid Julian Day: {self.cur_jd}. JD must be in valid Swiss Ephemeris range.")

        print(f"\n[DEBUG Shadbala] Init -> Lat: {self.lat}, Lon: {self.lon}")
        print(f"[DEBUG Shadbala] Init -> UTC JD: {self.cur_jd}")

    def _get_jhora_planet_id(self, p_name):
        planet_map = {
            "Sun": 0, "Moon": 1, "Mars": 2, "Mercury": 3,
            "Jupiter": 4, "Venus": 5, "Saturn": 6
        }
        return planet_map.get(p_name)

    def _get_tz_offset(self):
        tz_attr = getattr(self.app, "current_tz", 5.5)
        try:
            return float(tz_attr)
        except (ValueError, TypeError):
            if isinstance(tz_attr, str):
                try:
                    from zoneinfo import ZoneInfo
                    dt_aware = self.dt.replace(tzinfo=ZoneInfo(tz_attr))
                    return dt_aware.utcoffset().total_seconds() / 3600.0
                except Exception:
                    pass
        return 5.5

    def _run_shadbala_logic(self, local_jd, place):
        """
        Locally implemented shad_bala logic, bypassing the PyJHora wrapper 
        while directly utilizing its sub-components to prevent signature mismatches.
        """
        stb = strength._sthana_bala(local_jd, place)
        kb = strength._kaala_bala(local_jd, place)
        dgb = strength._dig_bala(local_jd, place)
        cb = strength._cheshta_bala_new(local_jd, place, use_epoch_table=True)
        nb = strength._naisargika_bala(local_jd, place)
        dkb = strength._drik_bala(local_jd, place)
        
        import numpy as np
        sb = [stb, kb, dgb, cb, nb, dkb]
        sbn = np.array(sb).tolist()
        sb_sum = np.around(np.sum(sbn,0),2).tolist()
        sb_rupa = [round(ss/60.0,2) for ss in sb_sum]
        
        return [stb, kb, dgb, cb, nb, dkb, sb_sum, sb_rupa, []]

    def calculate_all(self):
        """
        Delegates the planetary strength calculation (Shadbala).
        Handles UTC/Local Time conversions and intercepts Swisseph Moshier errors.
        """
        results = {}
        tz = self._get_tz_offset()
        
        if drik is None or strength is None or swe is None:
            print("[PyJHora Error] PyJHora modules are not properly loaded.")
            return self._get_fallback_results()
            
        place = drik.Place('Location', self.lat, self.lon, tz)
        
        # --- CRITICAL TIMEZONE FIX ---
        # PyJHora assumes the JD passed to it is the LOCAL Julian Day.
        # We must add the timezone back to our UTC JD so PyJHora computes the chart for the correct time.
        local_jd_for_pyjhora = self.cur_jd + (tz / 24.0)
        jd_utc_correct = self.cur_jd  # Our base JD is already UTC

        print(f"[DEBUG Shadbala] Local JD passed to PyJHora: {local_jd_for_pyjhora}")

        swisseph_module = sys.modules.get('swisseph')

        # --- EPHEMERIS PATH CONFIGURATION ---
        base_dir = os.path.dirname(os.path.abspath(__file__))
        ephe_dir = os.path.abspath(os.path.join(base_dir, "..", "ephe"))
        if not os.path.exists(ephe_dir):
            ephe_dir = "../ephe"
            
        try:
            if swe: swe.set_ephe_path(ephe_dir)
            if swisseph_module: swisseph_module.set_ephe_path(ephe_dir)
        except Exception:
            pass

        # --- PYJHORA MOSHIER BUG INTERCEPTOR ---
        original_calc_ut = swisseph_module.calc_ut
        original_houses_ex = swisseph_module.houses_ex
        original_get_ayanamsa = swisseph_module.get_ayanamsa
        swe_error = getattr(swe, 'Error', Exception)
        
        def safe_calc_ut(jd, planet, *args, **kwargs):
            try:
                target_jd = jd_utc_correct if not (625000.5 <= jd <= 2818000.5) else jd
                return original_calc_ut(target_jd, planet, *args, **kwargs)
            except (swe_error, BaseException):
                # If Planet 11 (True Node) crashes Moshier, dynamically fallback to Planet 10 (Mean Node)
                if planet == 11:
                    print("[DEBUG INTERCEPTOR] Moshier True Node Crash intercepted -> Using Mean Node (10).")
                    return original_calc_ut(target_jd, 10, *args, **kwargs)
                return ([0.0, 0.0, 0.0, 0.0, 0.0, 0.0], kwargs.get('flags', 0))

        def safe_houses_ex(jd, lat, lon, *args, **kwargs):
            if not (625000.5 <= jd <= 2818000.5):
                return original_houses_ex(jd_utc_correct, lat, lon, *args, **kwargs)
            return original_houses_ex(jd, lat, lon, *args, **kwargs)
            
        def safe_get_ayanamsa(jd, *args, **kwargs):
            if not (625000.5 <= jd <= 2818000.5):
                return original_get_ayanamsa(jd_utc_correct, *args, **kwargs)
            return original_get_ayanamsa(jd, *args, **kwargs)

        original_set_sid_mode = getattr(swisseph_module, 'set_sid_mode', None)

        def safe_set_sid_mode(sid_mode, t0=0.0, ayan_t0=0.0, *args, **kwargs):
            if sid_mode == swe.SIDM_USER and t0 < 625000.0:
                return original_set_sid_mode(swe.SIDM_LAHIRI, 0.0, 0.0, *args, **kwargs)
            return original_set_sid_mode(sid_mode, t0, ayan_t0, *args, **kwargs)

        swisseph_module.calc_ut = safe_calc_ut
        swisseph_module.houses_ex = safe_houses_ex
        swisseph_module.get_ayanamsa = safe_get_ayanamsa
        if original_set_sid_mode: swisseph_module.set_sid_mode = safe_set_sid_mode
            
        swe.calc_ut = safe_calc_ut
        swe.houses_ex = safe_houses_ex
        swe.get_ayanamsa = safe_get_ayanamsa
        if original_set_sid_mode: swe.set_sid_mode = safe_set_sid_mode
        # ----------------------
        
        try:
            print(f"[DEBUG Shadbala] Executing PyJHora calculations...")
            # Note: We pass local_jd_for_pyjhora because PyJHora assumes the argument is Local Time
            sb_data = self._run_shadbala_logic(local_jd_for_pyjhora, place)
            print("[DEBUG Shadbala] Calculation completed successfully.")
            
            stb_list = sb_data[0]   # Sthana Bala
            kb_list = sb_data[1]    # Kaala Bala
            dgb_list = sb_data[2]   # Dig Bala
            cb_list = sb_data[3]    # Cheshta Bala
            nb_list = sb_data[4]    # Naisargika Bala
            dkb_list = sb_data[5]   # Drik Bala
            total_list = sb_data[6] # Total
            
        except Exception as e:
            print(f"[DEBUG Shadbala] Calculation Failed. Traceback:")
            traceback.print_exc()
            stb_list = kb_list = dgb_list = cb_list = nb_list = dkb_list = total_list = [0.0] * 7
            
        finally:
            # Safely restore original functions
            swisseph_module.calc_ut = original_calc_ut
            swisseph_module.houses_ex = original_houses_ex
            swisseph_module.get_ayanamsa = original_get_ayanamsa
            if original_set_sid_mode: swisseph_module.set_sid_mode = original_set_sid_mode
                
            swe.calc_ut = original_calc_ut
            swe.houses_ex = original_houses_ex
            swe.get_ayanamsa = original_get_ayanamsa
            if original_set_sid_mode: swe.set_sid_mode = original_set_sid_mode
        
        for p_name in self.valid_planets:
            p_data = next((p for p in self.planets_list if p.get("name") == p_name), None)
            if not p_data: 
                continue
            
            p_id = self._get_jhora_planet_id(p_name)
            
            if p_id is not None:
                results[p_name] = {
                    "Sthana": round(stb_list[p_id], 2), 
                    "Dig": round(dgb_list[p_id], 2), 
                    "Kala": round(kb_list[p_id], 2),
                    "Cheshta": round(cb_list[p_id], 2), 
                    "Naisargika": round(nb_list[p_id], 2), 
                    "Drik": round(dkb_list[p_id], 2),
                    "Total": round(total_list[p_id], 2), 
                    "sign": int(p_data.get("sign_num", 1))
                }
            else:
                results[p_name] = self._get_zeroed_planet(p_data)
                
        return results

    def _get_fallback_results(self):
        results = {}
        for p_name in self.valid_planets:
            p_data = next((p for p in self.planets_list if p.get("name") == p_name), None)
            if p_data: 
                results[p_name] = self._get_zeroed_planet(p_data)
        return results
        
    def _get_zeroed_planet(self, p_data):
        return {
            "Sthana": 0.0, "Dig": 0.0, "Kala": 0.0,
            "Cheshta": 0.0, "Naisargika": 0.0, "Drik": 0.0,
            "Total": 0.0, "sign": int(p_data.get("sign_num", 1))
        }

