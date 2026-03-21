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

MEAN_SPEEDS = {
    "Sun": 0.9856, "Moon": 13.176, "Mars": 0.524, 
    "Mercury": 1.383, "Jupiter": 0.083, "Venus": 1.2, "Saturn": 0.033
}

VARGA_WEIGHTS = {
    "D1": 1.0, "D9": 0.5, "D2": 0.25, "D3": 0.25, 
    "D7": 0.25, "D12": 0.25, "D30": 0.25
}

EXALTATION_DEGREES = {
    "Sun": 10.0, "Moon": 3.0, "Mars": 28.0, "Mercury": 15.0,
    "Jupiter": 5.0, "Venus": 27.0, "Saturn": 21.0
}

# ==============================================================================
# ASPECT CALCULATION (DRIK BALA)
# ==============================================================================
def calc_drishti_value(aspecting_lon, aspected_lon, aspecting_name):
    L = (aspected_lon - aspecting_lon) % 360.0
    val = 0.0
    if 30 <= L < 60: val = (L - 30.0) / 2.0
    elif 60 <= L < 90: val = (L - 60.0) + 15.0
    elif 90 <= L < 120: val = (120.0 - L) / 2.0 + 30.0
    elif 120 <= L < 150: val = 150.0 - L
    elif 150 <= L < 180: val = (L - 150.0) * 2.0
    elif 180 <= L < 300: val = (300.0 - L) / 2.0
    
    # Special aspect additions (Parasari)
    if aspecting_name == "Saturn":
        if 60 <= L < 90: val += 45.0
        elif 270 <= L < 300: val += 45.0
    elif aspecting_name == "Jupiter":
        if 120 <= L < 150: val += 30.0
        elif 240 <= L < 270: val += 30.0
    elif aspecting_name == "Mars":
        if 90 <= L < 120: val += 15.0
        elif 210 <= L < 240: val += 15.0
        
    return val

# class ShadbalaCalculator:
#     def __init__(self, base_chart, varga_charts, app):
#         #print(f"REMEMBER CALCULATIONS HERE ARE BASED AGAINST 12 HRS DAY/NIGHT ASSUMPTION SO VALUES MAY NOT MATCH OTHER STANDARD SOFTWARES (LIKE JHORA)")
#         self.base_chart = base_chart or {}
#         self.varga_charts = varga_charts or {}
#         self.app = app
#         self.planets_list = self.base_chart.get("planets", [])
#         self.valid_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        
#         self.asc_lon = 0.0
#         self.h1_mid = 0.0
#         self.h4_mid = 0.0
#         self.h7_mid = 0.0
#         self.h10_mid = 0.0
        
#         self._check_swisseph()
#         self._setup_environmental_context()
    
#     def _setup_environmental_context(self):
#         import os
#         import swisseph as swe

#         base_dir = os.path.dirname(__file__)
#         ephe_path = os.path.abspath(os.path.join(base_dir, '..', 'ephe'))
#         swe.set_ephe_path(ephe_path)

#         self.cur_jd = float(self.base_chart.get("current_jd", 0.0))
#         panchang = self.base_chart.get("panchang", {}) or {}
        
#         lat = float(getattr(self.app, "current_lat", 28.6139))
#         lon = float(getattr(self.app, "current_lon", 77.2090))

#         sunrise = panchang.get("sunrise_jd")
#         sunset = panchang.get("sunset_jd")
#         self.sun_jd = float(sunrise if sunrise is not None else (self.cur_jd - 0.25))
#         self.set_jd = float(sunset if sunset is not None else (self.cur_jd + 0.25))
#         self.is_daytime = (self.sun_jd <= self.cur_jd < self.set_jd)
#         self.day_dur = max(1e-9, self.set_jd - self.sun_jd)
#         self.night_dur = max(1e-9, 1.0 - self.day_dur)
#         self.mid_day_jd = self.sun_jd + (self.day_dur / 2.0)

#         self._determine_mercury_status()

#         planets = self.base_chart.get("planets", [])
#         sun_p = next((p for p in planets if p["name"] == "Sun"), {"lon": 0})
#         moon_p = next((p for p in planets if p["name"] == "Moon"), {"lon": 0})
#         self.phase_angle = (float(moon_p["lon"]) - float(sun_p["lon"])) % 360.0
#         self.is_waxing = self.phase_angle < 180.0

#         # PRECISION HOUSE CUSPS (SIDEREAL FIX)
#         ayanamsa = float(swe.get_ayanamsa_ut(self.cur_jd))
#         _, ascmc = swe.houses(self.cur_jd, lat, lon, b'S')
        
#         self.asc_lon = (ascmc[0] - ayanamsa) % 360.0
        
#         self.h1_mid  = self.asc_lon                    
#         self.h10_mid = (self.asc_lon - 90.0) % 360.0   
#         self.h7_mid  = (self.asc_lon + 180.0) % 360.0  
#         self.h4_mid  = (self.asc_lon + 90.0) % 360.0   

#         # ======================================================================
#         # EXACT KALA BALA LORDS (Anchored to True Gregorian Weekday)
#         # ======================================================================
#         lords = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
        
#         # 1. Day Lord (True universal weekday formula to avoid Ahargana drift)
#         dina_idx = int(math.floor(self.sun_jd + 1.5)) % 7
        
#         # 2. Derive base Epoch Day from the exact current Dina to ensure Abda/Masa perfectly align
#         # Standard Kali Yuga Epoch = 588465.5 JD.
#         A_civil = int(math.floor(self.sun_jd - 588465.5))
#         epoch_wd = (dina_idx - A_civil) % 7 
        
#         abda_idx = (epoch_wd + A_civil - (A_civil % 360)) % 7
#         masa_idx = (epoch_wd + A_civil - (A_civil % 30)) % 7
        
#         # 3. Hora Lord (Hours elapsed since sunrise)
#         hrs_since_sunrise = (self.cur_jd - self.sun_jd) * 24.0
#         if hrs_since_sunrise < 0: hrs_since_sunrise += 24.0 
#         hora_idx = int(math.floor(hrs_since_sunrise))
#         hora_lord_idx = (dina_idx + hora_idx * 5) % 7  # 5 steps forward = 2 steps backward in Vara sequence
        
#         self.dina_lord = lords[dina_idx]
#         self.abda_lord = lords[abda_idx]
#         self.masa_lord = lords[masa_idx]
#         self.current_hora_lord = lords[hora_lord_idx]
        
#         ##print(f"\n[DEBUG_ENV_KALA_LORDS] Cur_JD: {self.cur_jd:.4f} | Sun_JD: {self.sun_jd:.4f}")
#         ##print(f"[DEBUG_ENV_KALA_LORDS] Ahargana(A_civil): {A_civil} | Hrs_Since_Sunrise: {hrs_since_sunrise:.2f}")
#         ##print(f"[DEBUG_ENV_KALA_LORDS] Computed Lords -> Abda(Year): {self.abda_lord} | Masa(Month): {self.masa_lord} | Dina(Day): {self.dina_lord} | Hora(Hour): {self.current_hora_lord}\n")

#     def calc_dig_bala(self, p_name, p_lon):
#         bali_points = {
#             "Jupiter": self.h1_mid,  
#             "Mercury": self.h1_mid,  
#             "Sun":     self.h10_mid, 
#             "Mars":    self.h10_mid, 
#             "Saturn":  self.h7_mid,  
#             "Moon":    self.h4_mid,  
#             "Venus":   self.h4_mid   
#         }

#         if p_name not in bali_points:
#             return 0.0

#         bali_pt = bali_points[p_name]
#         nirbala_pt = (bali_pt + 180.0) % 360.0
        
#         arc = (p_lon - nirbala_pt) % 360.0
#         if arc > 180.0:
#             arc = 360.0 - arc
            
#         score = round(arc / 3.0, 1)
#         #print(f"[DEBUG_DIG] {p_name:<8} | Lon: {p_lon:>6.2f} | Bali: {bali_pt:>6.2f} | Nirbala: {nirbala_pt:>6.2f} | Arc: {arc:>6.2f} | Score: {score:.2f}")
#         return score

#     def _check_swisseph(self):
#         self.has_swe = False
#         try:
#             import swisseph as swe
#             self.swe = swe
#             self.has_swe = True
#         except ImportError:
#             self.swe = None
    
#     def _determine_mercury_status(self):
#         merc_p = next((p for p in self.planets_list if p.get("name") == "Mercury"), None)
#         self.is_merc_benefic = True
#         if not merc_p: return

#         merc_lon = merc_p.get("lon", 0.0)
#         b_count, m_count = 0, 0
#         for q in self.planets_list:
#             q_n = q.get("name")
#             if not q_n or q_n in ["Mercury", "Rahu", "Ketu"]: continue
#             q_lon = q.get("lon", 0.0)
            
#             conj_diff = min(abs(merc_lon - q_lon), 360.0 - abs(merc_lon - q_lon))
#             if conj_diff <= 15.0:  
#                 if q_n in ["Sun", "Mars", "Saturn"]: m_count += 1
#                 elif q_n in ["Jupiter", "Venus", "Moon"]: b_count += 1
                
#         self.is_merc_benefic = (b_count >= m_count)

#     def calc_sthana_bala(self, p_name, p_data, p_lon):
#         DEB_DEGREES = {
#             "Sun": 190.0, "Moon": 213.0, "Mars": 118.0, 
#             "Mercury": 345.0, "Jupiter": 275.0, "Venus": 177.0, "Saturn": 20.0
#         }

#         deb_deg = DEB_DEGREES.get(p_name, 0.0)
#         dist = abs(p_lon - deb_deg)
#         if dist > 180.0:
#             dist = 360.0 - dist
        
#         uchcha_bala = max(0.0, min(60.0, (dist / 180.0) * 60.0))

#         sapta_bala = 0.0
#         required_vargas = ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]

#         def is_moolatrikona_exact(name, sign, deg):
#             if name == "Sun" and sign == 5 and 0.0 <= deg <= 20.0: return True
#             if name == "Moon" and sign == 2 and 3.0 <= deg <= 30.0: return True
#             if name == "Mars" and sign == 1 and 0.0 <= deg <= 12.0: return True
#             if name == "Mercury" and sign == 6 and 15.0 <= deg <= 20.0: return True
#             if name == "Jupiter" and sign == 9 and 0.0 <= deg <= 10.0: return True
#             if name == "Venus" and sign == 7 and 0.0 <= deg <= 15.0: return True
#             if name == "Saturn" and sign == 11 and 0.0 <= deg <= 20.0: return True
#             return False

#         for v in required_vargas:
#             varga_chart = self.varga_charts.get(v, {})
#             varga_planets = varga_chart.get("planets", [])
#             pv = next((x for x in varga_planets if x.get("name") == p_name), None)
            
#             if not pv: continue

#             varga_lon = float(pv.get("lon", 0.0))
#             varga_sign = int(pv.get("sign_num", int(varga_lon / 30.0) + 1))
#             varga_deg = float(pv.get("deg_in_sign", varga_lon % 30.0))
#             sign_ruler = astro_engine.SIGN_RULERS.get(varga_sign)
            
#             dignity_score = 0.0

#             if v == "D1" and is_moolatrikona_exact(p_name, varga_sign, varga_deg):
#                 dignity_score = 45.0
#             elif sign_ruler == p_name:
#                 dignity_score = 30.0
#             else:
#                 ruler_d1 = next((x for x in self.base_chart["planets"] if x["name"] == sign_ruler), None)
#                 base_d1 = next((x for x in self.base_chart["planets"] if x["name"] == p_name), None)
#                 temp_friend = False
                
#                 if ruler_d1 and base_d1:
#                     ruler_lon = float(ruler_d1.get("lon", 0.0))
#                     base_lon = float(base_d1.get("lon", p_lon))
#                     ruler_sign_d1 = int(ruler_d1.get("sign_num", int(ruler_lon / 30.0) + 1))
#                     base_sign_d1 = int(base_d1.get("sign_num", int(base_lon / 30.0) + 1))
                    
#                     sign_dist = (ruler_sign_d1 - base_sign_d1) % 12 + 1
#                     temp_friend = sign_dist in [2, 3, 4, 10, 11, 12]

#                 is_nat_friend = sign_ruler in NATURAL_FRIENDS.get(p_name, [])
#                 is_nat_enemy = sign_ruler in NATURAL_ENEMIES.get(p_name, [])
                
#                 if is_nat_friend and temp_friend: dignity_score = 22.5      
#                 elif not is_nat_friend and not is_nat_enemy and temp_friend: dignity_score = 15.0      
#                 elif is_nat_friend and not temp_friend: dignity_score = 7.5       
#                 elif is_nat_enemy and temp_friend: dignity_score = 7.5       
#                 elif not is_nat_friend and not is_nat_enemy and not temp_friend: dignity_score = 3.75      
#                 elif is_nat_enemy and not temp_friend: dignity_score = 1.875     

#             sapta_bala += dignity_score

#         ojha_bala = 0.0
#         male_planets = ["Sun", "Mars", "Jupiter", "Saturn", "Mercury"]
#         female_planets = ["Moon", "Venus"]

#         d1_sign = int(p_data.get("sign_num", int(p_lon / 30.0) + 1))
#         d1_odd = (d1_sign % 2) != 0
#         if p_name in male_planets and d1_odd: ojha_bala += 15.0
#         elif p_name in female_planets and not d1_odd: ojha_bala += 15.0

#         d9_chart = self.varga_charts.get("D9", {})
#         p_d9 = next((x for x in d9_chart.get("planets", []) if x.get("name") == p_name), None)
#         if p_d9:
#             d9_lon = float(p_d9.get("lon", 0.0))
#             d9_sign = int(p_d9.get("sign_num", int(d9_lon / 30.0) + 1))
#             d9_odd = (d9_sign % 2) != 0
#             if p_name in male_planets and d9_odd: ojha_bala += 15.0
#             elif p_name in female_planets and not d9_odd: ojha_bala += 15.0

#         asc_lon = float(self.base_chart.get("ascendant", {}).get("degree", self.asc_lon))
#         asc_sign = int(asc_lon / 30.0) + 1
#         kendra_house = (d1_sign - asc_sign) % 12 + 1

#         if kendra_house in [1, 4, 7, 10]: kendradi_bala = 60.0
#         elif kendra_house in [2, 5, 8, 11]: kendradi_bala = 30.0
#         else: kendradi_bala = 15.0

#         deg_in_sign = float(p_data.get("deg_in_sign", p_lon % 30.0))
#         drek_num = 1 if deg_in_sign < 10.0 else (2 if deg_in_sign < 20.0 else 3)
#         drekkana_bala = 0.0
        
#         if p_name in ["Sun", "Mars", "Jupiter"] and drek_num == 1: drekkana_bala = 15.0
#         elif p_name in ["Mercury", "Saturn"] and drek_num == 2: drekkana_bala = 15.0
#         elif p_name in ["Moon", "Venus"] and drek_num == 3: drekkana_bala = 15.0

#         return uchcha_bala + sapta_bala + ojha_bala + kendradi_bala + drekkana_bala
    
#     def _calc_paksha_bala(self):
#         if self.is_waxing:
#             return (self.phase_angle / 180.0) * 60.0
#         else:
#             return ((360.0 - self.phase_angle) / 180.0) * 60.0

#     def _calc_ayana_bala(self, p_name, p_lon):
#         decl = 0.0
#         got_exact = False
#         if self.has_swe:
#             try:
#                 import swisseph as swe
#                 p_id_map = {
#                     "Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS,
#                     "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER,
#                     "Venus": swe.VENUS, "Saturn": swe.SATURN
#                 }
#                 p_id = p_id_map.get(p_name)
#                 if p_id is not None:
#                     res, _ = swe.calc_ut(self.cur_jd, p_id, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
#                     decl = res[1]  
#                     got_exact = True
#             except Exception:
#                 pass
        
#         if not got_exact:
#             ayanamsa = 24.1 
#             if self.has_swe:
#                 try:
#                     import swisseph as swe
#                     ayanamsa = float(swe.get_ayanamsa_ut(self.cur_jd))
#                 except Exception: pass
#             trop_lon = (p_lon + ayanamsa) % 360.0
#             decl = math.degrees(math.asin(math.sin(math.radians(trop_lon)) * math.sin(math.radians(23.44))))

#         kranti = decl
#         if p_name in ["Sun", "Mars", "Jupiter", "Venus", "Mercury"]:
#             ayana_bala = ((24.0 + kranti) / 48.0) * 60.0
#         elif p_name in ["Moon", "Saturn"]:
#             ayana_bala = ((24.0 - kranti) / 48.0) * 60.0
            
#         ayana_bala = max(0.0, min(60.0, ayana_bala))
#         if p_name == "Sun":
#             ayana_bala *= 2.0  
            
#         return ayana_bala


#     def calc_kala_bala(self, p_name, p_lon):
#         # 1. Natonnata Bala (Exact True Local Noon/Midnight Distance via JD)
#         noon_jd = self.mid_day_jd
#         # Get the shortest JD distance to true local noon
#         dist_days_from_noon = min(abs(self.cur_jd - noon_jd), 
#                                   abs(self.cur_jd - (noon_jd - 1.0)), 
#                                   abs(self.cur_jd - (noon_jd + 1.0)))
        
#         noon_dist_hours = dist_days_from_noon * 24.0
#         midn_dist_hours = 12.0 - noon_dist_hours
            
#         if p_name in ["Sun", "Jupiter", "Venus"]: 
#             natonnata = ((12.0 - noon_dist_hours) / 12.0) * 60.0
#         elif p_name in ["Moon", "Mars", "Saturn"]: 
#             natonnata = ((12.0 - midn_dist_hours) / 12.0) * 60.0
#         else: 
#             natonnata = 60.0

#         # 2. Paksha Bala
#         val_paksha = self._calc_paksha_bala()
#         is_p_benefic = p_name in ["Jupiter", "Venus"] or (p_name == "Moon" and self.is_waxing) or (p_name == "Mercury" and self.is_merc_benefic)
#         paksha = val_paksha if is_p_benefic else (60.0 - val_paksha)

#         # 3. Tribhaga Bala
#         tribhaga = 60.0 if p_name == "Jupiter" else 0.0
#         if self.is_daytime:
#             frac = (self.cur_jd - self.sun_jd) / self.day_dur
#             frac = max(0.0, min(0.999999, frac))
#             part = int(math.floor(frac * 3.0))
#             day_lords = ["Mercury", "Sun", "Saturn"]
#             if p_name == day_lords[part]: tribhaga += 60.0
#         else:
#             if hasattr(self, 'set_jd') and hasattr(self, 'sun_jd') and self.night_dur > 0:
#                 if self.cur_jd < self.sun_jd:
#                     prev_set = self.set_jd - 1.0
#                     frac = (self.cur_jd - prev_set) / self.night_dur
#                 else:
#                     frac = (self.cur_jd - self.set_jd) / self.night_dur
#             else:
#                 frac = 0.0
#             frac = max(0.0, min(0.999999, frac))
#             part = int(math.floor(frac * 3.0))
#             night_lords = ["Moon", "Venus", "Mars"]
#             if p_name == night_lords[part]: tribhaga += 60.0

#         # 4. Planetary Lordship Strengths
#         abda_b = 15.0 if getattr(self, "abda_lord", "") == p_name else 0.0
#         masa_b = 30.0 if getattr(self, "masa_lord", "") == p_name else 0.0
#         vara_b = 45.0 if getattr(self, "dina_lord", "") == p_name else 0.0 
#         hora_b = 60.0 if getattr(self, "current_hora_lord", "") == p_name else 0.0

#         # 5. Ayana Bala
#         ayana_bala = self._calc_ayana_bala(p_name, p_lon)

#         total = natonnata + paksha + tribhaga + abda_b + masa_b + vara_b + hora_b + ayana_bala
        
#         #print(f"[DEBUG_KALA] {p_name:<8} | NoonDistHr: {noon_dist_hours:.2f} | Nat:{natonnata:>5.1f} | Pak:{paksha:>5.1f} | Tri:{tribhaga:>4.1f} | Abd:{abda_b:>4.1f} | Mas:{masa_b:>4.1f} | Var:{vara_b:>4.1f} | Hor:{hora_b:>4.1f} | Aya:{ayana_bala:>4.1f} | Tot:{total:.1f}")
#         return total

#     def calc_cheshta_bala(self, p_name, p_data, p_lon):
#         if p_name == "Sun": return self._calc_ayana_bala("Sun", p_lon)
#         if p_name == "Moon": return self._calc_paksha_bala()
        
#         seeghrocha = 0.0
#         ayanamsa = 24.0
#         if self.has_swe:
#             import swisseph as swe
#             ayanamsa = float(swe.get_ayanamsa_ut(self.cur_jd))
            
#         if p_name in ["Mars", "Jupiter", "Saturn"]:
#             # Seeghrocha for Outer Planets is Mean Sun
#             t = (self.cur_jd - 2451545.0) / 36525.0
#             mean_sun_trop = (280.46646 + 36000.76983 * t) % 360.0
#             seeghrocha = (mean_sun_trop - ayanamsa) % 360.0
#         elif p_name in ["Mercury", "Venus"]:
#             # Seeghrocha for Inner Planets is Sidereal Heliocentric Longitude
#             if self.has_swe:
#                 try:
#                     import swisseph as swe
#                     p_id_map = {"Mercury": swe.MERCURY, "Venus": swe.VENUS}
#                     p_id = p_id_map.get(p_name)
#                     # 8 is exact integer for swe.FLG_HELCTR (Bypasses AttributeError for older swisseph versions)
#                     res, _ = swe.calc_ut(self.cur_jd, p_id, swe.FLG_SWIEPH | 8) 
#                     seeghrocha = (res[0] - ayanamsa) % 360.0
#                 except Exception:
#                     pass
                    
#         ck = (seeghrocha - p_lon) % 360.0
#         if ck > 180.0: ck = 360.0 - ck
        
#         score = ck / 3.0
#         #print(f"[DEBUG_CHESHTA] {p_name:<8} | Lon: {p_lon:>6.2f} | Seeghrocha: {seeghrocha:>6.2f} | CK: {ck:>6.2f} | Score: {score:.2f}")
#         return score

#     def calc_naisargika_bala(self, p_name):
#         return NAISARGIKA_BALA.get(p_name, 0.0)

#     def calc_drik_bala(self, p_name, p_lon):
#         drik_bala = 0.0
#         #print(f"[DEBUG_DRIK_START] Calculating Drik Bala for {p_name} (Lon: {p_lon:.2f})")
#         for q in self.planets_list:
#             q_name = q.get("name")
#             if not q_name or q_name == p_name or q_name in ["Rahu", "Ketu", "Uranus", "Neptune", "Pluto"]: continue
            
#             q_lon = q.get("lon", 0.0)
#             aspect_val_raw = calc_drishti_value(q_lon, p_lon, q_name)
#             aspect_val = min(60.0, max(0.0, aspect_val_raw))
            
#             q_is_benefic = q_name in ["Jupiter", "Venus"] or (q_name == "Moon" and self.is_waxing) or (q_name == "Mercury" and self.is_merc_benefic)
            
#             dr_score = aspect_val / 4.0
#             if q_is_benefic: drik_bala += dr_score
#             else: drik_bala -= dr_score
#             #print(f"[DEBUG_DRIK_STEP]   <- {q_name:<8} | Score: {'+' if q_is_benefic else '-'}{dr_score:.2f}")
            
#         #print(f"[DEBUG_DRIK_TOTAL] {p_name} Net Drik Bala = {drik_bala:.2f}\n")
#         return drik_bala
    

#     def calculate_all(self):
#         self._setup_environmental_context()
        
#         results = {}
#         for p_name in self.valid_planets:
#             p_data = next((p for p in self.planets_list if p.get("name") == p_name), None)
#             if not p_data: continue
            
#             p_lon = float(p_data.get("lon", 0.0))
            
#             sthana = self.calc_sthana_bala(p_name, p_data, p_lon)
#             dig = self.calc_dig_bala(p_name, p_lon)
#             kala = self.calc_kala_bala(p_name, p_lon)
#             cheshta = self.calc_cheshta_bala(p_name, p_data, p_lon)
#             naisargika = self.calc_naisargika_bala(p_name)
#             drik = self.calc_drik_bala(p_name, p_lon)
            
#             total = sthana + dig + kala + cheshta + naisargika + drik
#             results[p_name] = {
#                 "Sthana": round(sthana, 2), 
#                 "Dig": round(dig, 2), 
#                 "Kala": round(kala, 2),
#                 "Cheshta": round(cheshta, 2), 
#                 "Naisargika": round(naisargika, 2), 
#                 "Drik": round(drik, 2),
#                 "Total": round(total, 2), 
#                 "sign": int(p_data.get("sign_num", 1))
#             }
#         return results




import math
import datetime
import sys
import traceback
import os

# --- PyJHora Dependency Mocking ---
# PyJHora requires 'geocoder' globally even if we provide exact lat/lon. 
# We mock it here so the app doesn't crash if the user hasn't pip installed it.
try:
    import geocoder
except ImportError:
    import types
    mock_geocoder = types.ModuleType("geocoder")
    # Add a dummy osm() method in case PyJHora's init tries to ping it
    mock_geocoder.osm = lambda *args, **kwargs: type('Dummy', (), {'latlng': [0.0, 0.0]})()
    sys.modules["geocoder"] = mock_geocoder

try:
    import swisseph as swe
    from jhora.panchanga import drik
    from jhora import const
    try:
        from jhora.horoscope.chart import strength
    except ImportError:
        from jhora.charts import strength
except ImportError as e:
    print(f"[PyJHora Import Warning] {e}")
    drik = None
    strength = None
    swe = None


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
            "Computed using PyJhora (extension) the author of PyJhora confirms that ---" \
            "<br><b><i>Now the results match the calculations of VP Jain and BV Raman examples in their respective books. " \
            "<br>However, it is important to note, shadbala calculations does not match with JHora (even for these examples). </b></i> " \
            "<i><br><br>Sthana, Dig, Kala, Cheshta, Naisargika, Drik (Aspects). Scales vary dynamically based on continuous mathematical models.</i><br>"
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
            #print(err_trace)

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