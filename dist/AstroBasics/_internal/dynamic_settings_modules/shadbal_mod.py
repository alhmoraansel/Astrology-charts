# dynamic_settings_modules/shadbala_mod.py
import math
import datetime
import traceback
from PyQt6.QtWidgets import (QPushButton, QMessageBox, QLabel, QVBoxLayout, QHBoxLayout, 
                             QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QWidget)
from PyQt6.QtCore import Qt, QTimer

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

# ==============================================================================
# ASPECT CALCULATION (DRIK BALA - JYOTISHMITRA SPUTA DRISHTI)
# ==============================================================================
def get_jm_sputadrishti(degree, aspectingplanet):
    if degree <= 30: return 0.0
    elif degree <= 60:
        if aspectingplanet == "Saturn": return (degree - 30.0) * 2.0
        else: return (degree - 30.0) / 2.0
    elif degree <= 90:
        if aspectingplanet == "Saturn": return 45.0 + (90.0 - degree) / 2.0
        else: return degree - 45.0
    elif degree <= 120:
        if aspectingplanet in ["Mars", "Jupiter"]: return 45.0 + (degree - 90.0) / 2.0
        else: return 30.0 + (120.0 - degree) / 2.0
    elif degree <= 150:
        if aspectingplanet in ["Mars", "Jupiter"]: return (150.0 - degree) * 2.0
        else: return 150.0 - degree
    elif degree <= 180:
        return abs(150.0 - degree) * 2.0
    elif degree <= 210:
        if aspectingplanet == "Mars": return 60.0
        else: return (300.0 - degree) / 2.0
    elif degree <= 240:
        if aspectingplanet == "Mars": return 270.0 - degree
        elif aspectingplanet == "Jupiter": return 45.0 + (degree - 210.0) / 2.0
        else: return (300.0 - degree) / 2.0
    elif degree <= 270:
        if aspectingplanet == "Saturn": return degree - 210.0
        elif aspectingplanet == "Jupiter": return 15.0 + 2.0 * (270.0 - degree) / 3.0
        else: return (300.0 - degree) / 2.0
    elif degree <= 300:
        if aspectingplanet == "Saturn": return (300.0 - degree) * 2.0
        else: return (300.0 - degree) / 2.0
    else:
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

    # ==============================================================================
    # JYOTISHMITRA EXACT MATHEMATICAL PORTING (STHANA AND DRIK BALAS UPDATED)
    # ==============================================================================

    def get_jm_dignity(self, p_name, varga_name):
        varga_chart = self.varga_charts.get(varga_name, {})
        pv = next((x for x in varga_chart.get("planets", []) if x.get("name") == p_name), None)
        if not pv: return 10.0

        varga_lon = float(pv.get("lon", 0.0))
        # Ensure 'sign_num' is safely pulled to prevent 'everyone in Aries' failure
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

        # Natural Relation
        nat_friends = NATURAL_FRIENDS.get(p_name, [])
        nat_enemies = NATURAL_ENEMIES.get(p_name, [])
        n_val = 1 if dispositor in nat_friends else (-1 if dispositor in nat_enemies else 0)

        # Temporary Relation (from D1)
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
        if final_val == 2: return 20.0     # Athimitra
        elif final_val == 1: return 15.0   # Mitra
        elif final_val == 0: return 10.0   # Sama
        elif final_val == -1: return 4.0   # Shatru
        elif final_val == -2: return 2.0   # Athishatru
        return 10.0

    def calc_sthana_bala(self, p_name, p_data, p_lon):
        # 1. Uchchabala
        deb_deg = DEBILITATION_DEGREES.get(p_name, 0.0)
        dist = min(abs(p_lon - deb_deg), 360.0 - abs(p_lon - deb_deg))
        uchcha_bala = dist / 3.0

        # 2. Saptavargajabala
        sapta_bala = 0.0
        for v in ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]:
            sapta_bala += self.get_jm_dignity(p_name, v)

        # 3. Ojhayugmarashiamshabala
        d1_sign = int(p_data.get("sign_num", int(p_lon / 30.0) + 1))
        
        d9_chart = self.varga_charts.get("D9", {})
        p_d9 = next((x for x in d9_chart.get("planets", []) if x.get("name") == p_name), None)
        if p_d9:
            d9_sign = int(p_d9.get("sign_num", int(float(p_d9.get("lon", 0.0)) / 30.0) + 1))
        else:
            d9_sign = d1_sign

        ojha_bala = 0.0
        if p_name in ["Sun", "Mars", "Mercury", "Jupiter", "Saturn"]:
            if d1_sign % 2 != 0: ojha_bala += 15.0
            if d9_sign % 2 != 0: ojha_bala += 15.0
        else: # Moon, Venus
            if d1_sign % 2 == 0: ojha_bala += 15.0
            if d9_sign % 2 == 0: ojha_bala += 15.0

        # 4. Kendradhibala
        asc_sign = int(self.base_chart.get("ascendant", {}).get("sign_num", int(self.asc_lon / 30.0) + 1))
        hno = (d1_sign - asc_sign) % 12 + 1
        
        if hno in [1, 4, 7, 10]: kendradi_bala = 60.0
        elif hno in [2, 5, 8, 11]: kendradi_bala = 30.0
        else: kendradi_bala = 15.0

        # 5. Drekshanabala
        deg = float(p_data.get("deg_in_sign", p_lon % 30.0))
        drekkana_bala = 0.0
        if deg <= 10.0 and p_name in ["Sun", "Jupiter", "Mars"]: drekkana_bala = 15.0
        elif 10.0 < deg <= 20.0 and p_name in ["Moon", "Venus"]: drekkana_bala = 15.0
        elif deg > 20.0 and p_name in ["Mercury", "Saturn"]: drekkana_bala = 15.0

        return uchcha_bala + sapta_bala + ojha_bala + kendradi_bala + drekkana_bala

    def calc_dig_bala(self, p_name, p_lon):
        asc_sign = int(self.asc_lon / 30.0) + 1
        def get_house_sign_1_idx(h): return (asc_sign + h - 2) % 12 + 1

        zero_h = {"Sun": 4, "Moon": 10, "Mars": 4, "Mercury": 7, "Jupiter": 7, "Venus": 10, "Saturn": 1}
        z_sign = get_house_sign_1_idx(zero_h[p_name])
        zero_lon = (z_sign - 1) * 30.0 + 15.0

        dist = min(abs(p_lon - zero_lon), 360.0 - abs(p_lon - zero_lon))
        return dist / 3.0

    def calc_kala_bala(self, p_name, p_lon):
        # 1. Natonnata Bala
        lon_deg = float(getattr(self.app, "current_lon", 77.2090))
        lmt_hours = (self.cur_jd + 0.5 + lon_deg / 360.0) % 1.0 * 24.0
        bt_gap_hours = lmt_hours if lmt_hours <= 12.0 else 24.0 - lmt_hours
        nat_val = bt_gap_hours * 5.0

        if p_name in ["Moon", "Mars", "Saturn"]: natonnata = nat_val
        elif p_name in ["Sun", "Jupiter", "Venus"]: natonnata = 60.0 - nat_val
        else: natonnata = 60.0

        # 2. Ayana Bala (Cached from calculate_all)
        ayana_bala = self.ayana_balas.get(p_name, 0.0)

        # 3. Paksha Bala (Cached from calculate_all)
        paksha = self.paksha_val if p_name in ["Moon", "Mercury", "Jupiter", "Venus"] else 60.0 - self.paksha_val

        # 4. Tribhaga Bala
        sun2lagna_dist = (360.0 + self.asc_lon - self.sun_lon) % 360.0
        tribhaga = 0.0
        if p_name == "Jupiter": tribhaga = 60.0
        if sun2lagna_dist <= 60.0 and p_name == "Mercury": tribhaga = 60.0
        elif 60.0 < sun2lagna_dist <= 120.0 and p_name == "Sun": tribhaga = 60.0
        elif 120.0 < sun2lagna_dist <= 180.0 and p_name == "Saturn": tribhaga = 60.0
        elif 180.0 < sun2lagna_dist <= 240.0 and p_name == "Moon": tribhaga = 60.0
        elif 240.0 < sun2lagna_dist <= 300.0 and p_name == "Venus": tribhaga = 60.0
        elif 300.0 < sun2lagna_dist <= 360.0 and p_name == "Mars": tribhaga = 60.0

        # 5. Varsha, Maasa, Dina, Hora
        try:
            import swisseph as swe
            y, m, d, _ = swe.revjul(self.cur_jd, swe.GREG_CAL)
        except:
            dt = datetime.datetime.fromordinal(int(self.cur_jd - 1721425.5))
            y, m, d = dt.year, dt.month, dt.day

        lords = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        daylord_map = { "Sunday": "Sun", "Monday": "Moon", "Tuesday": "Mars", "Wednesday": "Mercury", "Thursday": "Jupiter", "Friday": "Venus", "Saturday": "Saturn" }

        varsha_wd = datetime.date(y, 1, 1).weekday()
        maasa_wd = datetime.date(y, m, 1).weekday()
        dina_wd = datetime.date(y, m, d).weekday()

        varsha_lord = daylord_map[lords[varsha_wd]]
        maasa_lord = daylord_map[lords[maasa_wd]]
        dina_lord = daylord_map[lords[dina_wd]]

        hora_num = int(sun2lagna_dist // 15.0)
        if sun2lagna_dist % 15.0 > 0: hora_num += 1

        lords_seq = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] * 5
        bornvaara = lords[dina_wd]
        dinaidx = lords_seq.index(bornvaara)
        hora_lord = daylord_map[lords_seq[dinaidx + hora_num]]

        vmdh_bala = 0.0
        if p_name == varsha_lord: vmdh_bala += 15.0
        if p_name == maasa_lord: vmdh_bala += 30.0
        if p_name == dina_lord: vmdh_bala += 45.0
        if p_name == hora_lord: vmdh_bala += 60.0

        return natonnata + ayana_bala + paksha + tribhaga + vmdh_bala

    def calc_cheshta_bala(self, p_name, p_data, p_lon):
        if p_name == "Sun": return self.ayana_balas.get("Sun", 0.0)
        if p_name == "Moon": return self.paksha_val 

        gap = min(abs(p_lon - self.sun_lon), 360.0 - abs(p_lon - self.sun_lon))
        gap_signs = int(gap // 30.0)
        gap_degrees = gap % 30.0

        if p_name in ["Mars", "Jupiter", "Saturn"]:
            kurma_pts = {
                "Jupiter": [7, 5, 3, 1, 2, 2, 0],
                "Saturn": [6, 5, 3, 1, 2, 3, 0],
                "Mars": [7, 6, 4, 2, 0, 1, 0]
            }
            pts = kurma_pts[p_name]
            sign_part = sum(pts[0:gap_signs]) * 3.0
            deg_part = (0.1 * gap_degrees) * pts[gap_signs]
            return sign_part + deg_part

        elif p_name in ["Venus", "Mercury"]:
            is_retro = p_data.get("speed", 1.0) < 0.0
            if "is_retro" in p_data: is_retro = p_data["is_retro"]
            elif "speed" not in p_data and self.has_swe:
                try:
                    import swisseph as swe
                    pid = swe.VENUS if p_name == "Venus" else swe.MERCURY
                    res, _ = swe.calc_ut(self.cur_jd, pid, swe.FLG_SWIEPH)
                    is_retro = res[3] < 0.0
                except: pass
                
            if p_name == "Venus":
                if is_retro: return 60.0 - (gap / 10.0)
                else: return gap if gap <= 40.0 else 2.0 * gap - 41.0
            else: # Mercury
                if is_retro: return 60.0 - (gap / 2.0)
                else: return 2.0 * gap

        return 0.0

    def calc_jm_drik_bala(self, p_name, p_lon):
        benefics = ["Jupiter", "Venus"]
        malefics = ["Sun", "Mars", "Saturn"]

        # Dynamic Benefic Check
        if getattr(self, "is_waxing", True): benefics.append("Moon")
        else: malefics.append("Moon")

        if getattr(self, "is_merc_benefic", True): benefics.append("Mercury")
        else: malefics.append("Mercury")

        benefic_sputa = 0.0
        malefic_sputa = 0.0

        for q in self.planets_list:
            q_name = q.get("name")
            if not q_name or q_name == p_name or q_name not in benefics + malefics: continue

            q_lon = float(q.get("lon", 0.0))
            degree = (p_lon - q_lon) % 360.0

            sputa = get_jm_sputadrishti(degree, q_name)
            if q_name in benefics: benefic_sputa += sputa
            if q_name in malefics: malefic_sputa += sputa

        return (benefic_sputa - malefic_sputa) / 4.0

    def calculate_all(self):
        self._setup_ascendant()

        self.sun_p = next((x for x in self.planets_list if x["name"] == "Sun"), {"lon": 0})
        self.moon_p = next((x for x in self.planets_list if x["name"] == "Moon"), {"lon": 0})
        self.sun_lon = float(self.sun_p.get("lon", 0.0))
        self.moon_lon = float(self.moon_p.get("lon", 0.0))

        sun_moon_gap = min(abs(self.moon_lon - self.sun_lon), 360.0 - abs(self.moon_lon - self.sun_lon))
        self.paksha_val = sun_moon_gap / 3.0

        # Used for Drik Bala Checks
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

        pre_yuddha_results = {}
        for p_name in self.valid_planets:
            p_data = next((p for p in self.planets_list if p.get("name") == p_name), None)
            if not p_data: continue

            p_lon = float(p_data.get("lon", 0.0))

            sthana = self.calc_sthana_bala(p_name, p_data, p_lon)
            dig = self.calc_dig_bala(p_name, p_lon)
            kala = self.calc_kala_bala(p_name, p_lon)
            cheshta = self.calc_cheshta_bala(p_name, p_data, p_lon)
            naisargika = NAISARGIKA_BALA.get(p_name, 0.0)
            drik = self.calc_jm_drik_bala(p_name, p_lon)

            total = sthana + dig + kala + cheshta + naisargika + drik
            pre_yuddha_results[p_name] = {
                "Sthana": sthana, "Dig": dig, "Kala": kala,
                "Cheshta": cheshta, "Naisargika": naisargika, 
                "Drik": drik, "Total": total, 
                "sign": int(p_data.get("sign_num", int(p_lon / 30.0) + 1)),
                "lon": p_lon
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

                if dist < 1.0: # 1 degree threshold
                    gap = abs(pre_yuddha_results[p1]["Total"] - pre_yuddha_results[p2]["Total"])
                    if pre_yuddha_results[p1]["Total"] >= pre_yuddha_results[p2]["Total"]:
                        yuddha_adjustments[p1] += gap
                        yuddha_adjustments[p2] -= gap
                    else:
                        yuddha_adjustments[p2] += gap
                        yuddha_adjustments[p1] -= gap

        final_results = {}
        for p, res in pre_yuddha_results.items():
            res["Kala"] += yuddha_adjustments[p]
            res["Total"] += yuddha_adjustments[p]

            final_results[p] = {
                "Sthana": round(res["Sthana"], 2), 
                "Dig": round(res["Dig"], 2), 
                "Kala": round(res["Kala"], 2),
                "Cheshta": round(res["Cheshta"], 2), 
                "Naisargika": round(res["Naisargika"], 2), 
                "Drik": round(res["Drik"], 2),
                "Total": round(res["Total"], 2), 
                "sign": res["sign"]
            }

        return final_results

# ==============================================================================
# USER INTERFACE & DIALOGS
# ==============================================================================

class ShadbalaDetailsDialog(QDialog):
    """Dialog window to display the breakdown of Shadbala scores."""
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Shadbala Analysis")
        self.resize(1200, 550)
        self.setStyleSheet("QTableWidget { font-size: 13px; } QHeaderView::section { font-weight: bold; background-color: #f3f4f6; padding: 4px; }")
        
        layout = QVBoxLayout(self)
        info_lbl = QLabel(
            "Computed as per the algorithm laid by jyotishmitra (auth: Shyam Bhat VicharVandana)<i><br>Sthana, Dig, Kala, Cheshta, Naisargika, Drik (Aspects).</i><br>"
            "<span style='color: #27ae60;'><b>Auto-updates in real-time as you change the time or animate the chart!</b></span>"
        )
        info_lbl.setStyleSheet("color: #2c3e50; font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(info_lbl)
        
        self.table = QTableWidget()
        cols = ["Planet", "Sthana", "Dig", "Kala", "Cheshta", "Naisargika", "Drik (Net)", "TOTAL SCORE", "Threshold", "Status"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        btn_close = QPushButton("Close Detailed Analysis")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _create_bar(self, val, max_val, color_thresholds):
        bar = QProgressBar()
        bar.setMaximum(int(max_val))
        bar.setValue(min(int(max_val), int(abs(val))))
        bar.setFormat(f"{val:.1f}")
        bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        color = color_thresholds[-1][1] 
        for threshold, c in color_thresholds:
            if val >= threshold: 
                color = c
                break 
            
        bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }} QProgressBar {{ border: 1px solid #bdc3c7; border-radius: 2px; text-align: center; font-weight: bold; color: black; }}")
        return bar

    def refresh_data(self, shadbala_data):
        self.table.setRowCount(0)
        self.table.setRowCount(len(shadbala_data))
        
        sorted_data = sorted(
            shadbala_data.items(), 
            key=lambda x: x[1]['Total'] / REQUIRED_SHADBALA.get(x[0], 300), 
            reverse=True
        )
        
        for row, (p_name, scores) in enumerate(sorted_data):
            lord = astro_engine.SIGN_RULERS.get(scores.get('sign', 1), '')
            p_item = QTableWidgetItem(f"{p_name}\n({lord})")
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, p_item)
            
            self.table.setCellWidget(row, 1, self._create_bar(scores["Sthana"], 300, [(150, "#27ae60"), (100, "#f1c40f"), (0, "#c0392b")]))
            self.table.setCellWidget(row, 2, self._create_bar(scores["Dig"], 60, [(30, "#27ae60"), (15, "#f1c40f"), (0, "#c0392b")]))
            self.table.setCellWidget(row, 3, self._create_bar(scores["Kala"], 300, [(150, "#27ae60"), (75, "#f1c40f"), (0, "#c0392b")]))
            self.table.setCellWidget(row, 4, self._create_bar(scores["Cheshta"], 60, [(30, "#27ae60"), (15, "#f1c40f"), (0, "#c0392b")]))
            self.table.setCellWidget(row, 5, self._create_bar(scores["Naisargika"], 60, [(0, "#3498db")]))
            
            drik_val = scores["Drik"]
            drik_lbl = QLabel(f"{drik_val:+.1f}")
            drik_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            drik_lbl.setStyleSheet(f"font-weight: bold; color: {'#27ae60' if drik_val >= 0 else '#c0392b'};")
            self.table.setCellWidget(row, 6, drik_lbl)
            
            total = scores["Total"]
            req_thresh = REQUIRED_SHADBALA.get(p_name, 300)
            
            self.table.setCellWidget(row, 7, self._create_bar(total, max(600, total), [(req_thresh, "#27ae60"), (0, "#c0392b")]))
            
            thresh_item = QTableWidgetItem(f"{req_thresh:.0f}")
            thresh_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 8, thresh_item)
            
            is_strong = total >= req_thresh
            status_text = "STRONG 🟢" if is_strong else "WEAK 🔴"
            status_lbl = QLabel(status_text)
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_lbl.setStyleSheet(f"font-weight: bold; color: {'#27ae60' if is_strong else '#c0392b'};")
            self.table.setCellWidget(row, 9, status_lbl)
            
            self.table.setRowHeight(row, 45)

# ==============================================================================
# MAIN INTEGRATION HOOK
# ==============================================================================

def setup_ui(app, layout):
    lbl_title = QLabel("Shadbala ")
    lbl_title.setStyleSheet("color: #8e44ad; font-weight: bold; font-size: 15px; margin-top: 8px;")
    layout.addWidget(lbl_title)
    
    leaderboard_lbl = QLabel("<i>Calculating initial rankings...</i>")
    leaderboard_lbl.setStyleSheet("background-color: #fdfefe; border: 1px solid #dcdde1; border-radius: 4px; padding: 6px; font-family: monospace;")
    leaderboard_lbl.setWordWrap(True)
    layout.addWidget(leaderboard_lbl)
    
    btn_layout = QHBoxLayout()
    btn_details = QPushButton("Detail Charts (Live)")
    btn_details.setStyleSheet("background-color: #34495e; color: white; font-weight: bold;")
    btn_details.setEnabled(False)
    btn_layout.addWidget(btn_details)
    layout.addLayout(btn_layout)
    
    app._shadbala_results = {}
    
    def run_computation():
        if not hasattr(app, 'current_base_chart') or not app.current_base_chart:
            leaderboard_lbl.setText("<i>Waiting for chart data...</i>")
            return
            
        base_chart = app.current_base_chart
        if not base_chart.get("planets", []):
            leaderboard_lbl.setText("<i>Initializing planetary engine...</i>")
            return
            
        try:
            required_vargas = ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]
            varga_charts = {"D1": base_chart}
            for v in required_vargas[1:]:
                v_chart = app.ephemeris.compute_divisional_chart(base_chart, v)
                varga_charts[v] = v_chart if v_chart else {"planets": []}

            calculator = ShadbalaCalculator(base_chart, varga_charts, app)
            results = calculator.calculate_all()
            
            app._shadbala_results = results
            
            sorted_planets = sorted(
                results.items(), 
                key=lambda x: x[1]['Total'] / REQUIRED_SHADBALA.get(x[0], 300), 
                reverse=True
            )
            
            leader_txt = "<b>Shadbala Rankings:</b><br>"
            for i, (p, data) in enumerate(sorted_planets, start=1):
                req = REQUIRED_SHADBALA.get(p, 300)
                icon = "🟢" if data['Total'] >= req else "🔴"
                leader_txt += f"{i}. <b>{p}</b> - {data['Total']:.1f} / {req:.0f} req. {icon}<br>"
                
            leaderboard_lbl.setText(leader_txt)
            btn_details.setEnabled(True)
            
            if hasattr(app, '_shadbala_dialog') and app._shadbala_dialog.isVisible():
                app._shadbala_dialog.refresh_data(results)
                
        except Exception as e:
            err_trace = traceback.format_exc()
            leaderboard_lbl.setText(f"<i style='color:red; font-size:10px;'>{err_trace}</i>")

    def auto_trigger(*args, **kwargs):
        QTimer.singleShot(0, run_computation)

    if hasattr(app, '_shadbala_auto_hook'):
        try: app.calc_worker.calc_finished.disconnect(app._shadbala_auto_hook)
        except Exception: pass
        
    app._shadbala_auto_hook = auto_trigger
    app.calc_worker.calc_finished.connect(app._shadbala_auto_hook)

    def show_details():
        if hasattr(app, '_shadbala_results') and app._shadbala_results:
            if not hasattr(app, '_shadbala_dialog'):
                app._shadbala_dialog = ShadbalaDetailsDialog(app)
            app._shadbala_dialog.refresh_data(app._shadbala_results)
            app._shadbala_dialog.show()
            app._shadbala_dialog.raise_()
            app._shadbala_dialog.activateWindow()

    btn_details.clicked.connect(show_details)
    auto_trigger()