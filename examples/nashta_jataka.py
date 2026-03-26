# dynamic_settings_modules/nashta_jataka.py

import datetime
import math
import pytz
import swisseph as swe
import main  # Import main to access SmoothScroller

from astral import LocationInfo
from astral.sun import sun

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QPushButton, QTextBrowser, QFrame)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import astro_engine

# Seasonal and Sign Mappings (Updated per standard Vedic Ritu classifications)
RITU_MAP = {
    "Sun": "Grishma (Summer)",
    "Mars": "Grishma (Summer)",
    "Moon": "Varsha (Monsoon/Rainy)",
    "Mercury": "Sharad (Autumn)",
    "Jupiter": "Hemanta (Pre-winter)",
    "Saturn": "Shishira (Winter)",
    "Venus": "Vasanta (Spring)"
}

# Uttarayana (Northern Path) vs Dakshinayana (Southern Path) Ritus
NORTHERN_RITUS = {"Saturn", "Venus", "Sun", "Mars"} # Shishira, Vasanta, Grishma
SOUTHERN_RITUS = {"Moon", "Mercury", "Jupiter"}     # Varsha, Sharad, Hemanta

# Swapping Rules when Ayana and Calculated Season clash
SWAP_MAP = {
    "Sun": "Moon", "Moon": "Sun",
    "Mars": "Moon", 
    "Venus": "Mercury", "Mercury": "Venus",
    "Saturn": "Jupiter", "Jupiter": "Saturn"
}

# The two solar months (Sun signs) for each season
SEASON_SUN_SIGNS = {
    "Saturn": [9, 10],   # Capricorn, Aquarius (Shishira)
    "Venus": [11, 0],    # Pisces, Aries (Vasanta)
    "Sun": [1, 2],       # Taurus, Gemini (Grishma)
    "Mars": [1, 2],      # Taurus, Gemini (Grishma)
    "Moon": [3, 4],      # Cancer, Leo (Varsha)
    "Mercury": [5, 6],   # Virgo, Libra (Sharad)
    "Jupiter": [7, 8]    # Scorpio, Sagittarius (Hemanta)
}

ZODIAC_NAMES = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

class NashtaJatakaDialog(QDialog):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app = app_ref
        self.setWindowTitle("Nashta Jataka: Lost Horoscopy")
        self.resize(1000, 800)
        
        # Modern UI, High contrast for visibility. 
        # Inherits main app's native scrollbar visual style to look natural.
        self.setStyleSheet("""
            QDialog { background-color: #f8fafc; }
            QLabel { font-size: 14px; color: #0f172a; font-weight: bold; }
            QSpinBox { padding: 8px; font-size: 14px; border: 1px solid #cbd5e1; border-radius: 4px; background: white; color: #0f172a; min-width: 80px; }
            QPushButton { background-color: #2563eb; color: white; font-size: 14px; font-weight: bold; padding: 12px 24px; border-radius: 6px; border: none; min-height: 45px; }
            QPushButton:hover { background-color: #1d4ed8; }
            QPushButton:pressed { background-color: #1e40af; }
            QTextBrowser { background-color: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 15px; font-size: 15px; line-height: 1.6; color: #0f172a; }
        """)
        
        layout = QVBoxLayout(self)
        
        # Input Section
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: white; border-radius: 8px; border: 1px solid #e2e8f0;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 15, 15, 15)
        
        input_layout.addWidget(QLabel("Person's Approximate Age:"))
        self.age_spin = QSpinBox()
        self.age_spin.setRange(1, 120)
        self.age_spin.setValue(20)
        input_layout.addWidget(self.age_spin)
        
        self.calc_btn = QPushButton("Calculate Lost Birth Time ✨")
        self.calc_btn.clicked.connect(self.run_analysis)
        input_layout.addWidget(self.calc_btn)
        
        input_layout.addStretch()
        layout.addWidget(input_frame)
        
        # Results Output
        self.output_browser = QTextBrowser()
        self.output_browser.setOpenExternalLinks(False)
        layout.addWidget(self.output_browser)
        
        # Attach Main App's Smooth Scroller
        self.smooth_scroller = main.SmoothScroller(self.output_browser)

        self.intro_text = """
        <h2 style='color:#1e3a8a;'>The Ancient Art of Nashta Jataka</h2>
        <p>When a person does not know their birth time, date, or even the year they were born, ancient Vedic astrology uses the <b>Prashna (Query)</b> moment to mathematically reverse-engineer the stars.</p>
        <p>Please enter the person's approximate age above and click Calculate. The engine will use the <i>exact current moment and location</i> to reveal their lost birth details.</p>
        """
        self.output_browser.setHtml(self.intro_text)

    def debug_print(self, *args):
        """Prints highly detailed exact planetary degrees to the console for verification."""
        msg = " ".join(str(a) for a in args)
        print(f"[Nashta Jataka Debug] {msg}")

    def append_html(self, html):
        current_html = self.output_browser.toHtml()
        self.output_browser.setHtml(current_html + html)
        # Scroll to bottom smoothly
        scrollbar = self.output_browser.verticalScrollBar()
        self.smooth_scroller.target_v = scrollbar.maximum()
        self.smooth_scroller.timer.start(16)

    def deg_to_dms(self, deg):
        d = int(deg)
        m = int((deg - d) * 60)
        s = int((((deg - d) * 60) - m) * 60)
        return f"{d}&deg; {m}' {s}\""

    def run_analysis(self):
        # Clear output
        self.output_browser.setHtml("<h2 style='color:#1e3a8a;'>Reconstructing Birth Timeline...</h2>")
        self.debug_print("=== INITIATING NASHTA JATAKA PROTOCOL ===")
        
        try:
            # Get LIVE exact current moment using system clock
            now_utc = datetime.datetime.now(pytz.utc)
            query_loc = self.app.get_current_location()
            
            try:
                local_tz = pytz.timezone(query_loc['tz'])
                now_local = now_utc.astimezone(local_tz)
            except Exception:
                local_tz = pytz.utc
                now_local = now_utc

            query_dt = {
                'year': now_local.year,
                'month': now_local.month,
                'day': now_local.day,
                'hour': now_local.hour,
                'minute': now_local.minute,
                'second': now_local.second
            }
            approx_age = self.age_spin.value()

            # Set engine modes
            swe.set_ephe_path('ephe')
            swe.set_sid_mode(self.app.ephemeris.ayanamsa_modes[self.app.ephemeris.current_ayanamsa])
            calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED

            # Calculate live exact JD
            jd_utc = swe.julday(now_utc.year, now_utc.month, now_utc.day, 
                                now_utc.hour + now_utc.minute / 60.0 + now_utc.second / 3600.0)

            # Calculate Live Ascendant directly
            cusps, ascmc = swe.houses_ex(jd_utc, query_loc['lat'], query_loc['lon'], b'P', swe.FLG_SIDEREAL)
            asc_deg = ascmc[0]
            asc_sign_idx = int(asc_deg / 30.0)
            asc_deg_in_sign = asc_deg % 30.0
            
            self.debug_print(f"Query Moment (LIVE): {query_dt}")
            self.debug_print(f"Absolute Query Ascendant Degree: {asc_deg:.6f} (Sign Index: {asc_sign_idx})")
            
            self.append_html(f"""
            <div style='background:#f1f5f9; padding:15px; border-radius:8px; margin-bottom:15px; border-left: 5px solid #3b82f6;'>
                <b style='font-size: 16px; color: #1e3a8a;'>Current Query Moment (Prashna):</b><br>
                Date: {query_dt['year']}-{query_dt['month']:02d}-{query_dt['day']:02d} {query_dt['hour']:02d}:{query_dt['minute']:02d}<br>
                Query Ascendant: <b style='color:#0f172a;'>{ZODIAC_NAMES[asc_sign_idx]} at {self.deg_to_dms(asc_deg_in_sign)}</b> (Absolute: {asc_deg:.4f}&deg;)<br>
                Location: {query_loc['name']}
            </div>
            """)

            # ==========================================
            # PHASE 1: Find the Birth Year (Dwadasamsa)
            # ==========================================
            d12_sign_idx, _ = self.app.ephemeris.get_div_sign_and_lon(asc_deg, "D12")
            rough_year = query_dt["year"] - approx_age
            
            self.debug_print(f"Phase 1: D12 Calculation -> Found Target Jupiter Sign Index: {d12_sign_idx} ({ZODIAC_NAMES[d12_sign_idx]})")
            
            self.append_html(f"<h3>PHASE 1: Find the Birth Year (Using Dwadasamsa)</h3>")
            self.append_html(f"<ul>")
            self.append_html(f"<li>The <b>Dwadasamsa (D12)</b> of the Query Ascendant determines where Jupiter was during the birth year.</li>")
            self.append_html(f"<li>The Query Ascendant falls into the <b>{ZODIAC_NAMES[d12_sign_idx]}</b> Dwadasamsa.</li>")
            self.append_html(f"<li>Therefore, when the client was born, <b>Jupiter was in {ZODIAC_NAMES[d12_sign_idx]}</b>.</li>")
            self.append_html(f"<li>Target estimated birth year: {query_dt['year']} - {approx_age} = {rough_year}.</li>")
            
            # Scan for exact year Jupiter was in target sign
            birth_year = rough_year
            found_year = False
            
            # Check +/- 6 years around the rough year
            for y_offset in sorted(list(range(-6, 7)), key=abs):
                test_year = rough_year + y_offset
                test_jd = astro_engine.ymdhms_to_jd(test_year, 7, 1) # Check mid-year
                jup_res = astro_engine.safe_calc_ut(test_jd, swe.JUPITER, calc_flag)
                jup_sign_idx = int(jup_res[0][0] / 30.0)
                
                self.debug_print(f"  Testing Year {test_year}: Jupiter Absolute Degree = {jup_res[0][0]:.6f} -> Sign Index = {jup_sign_idx}")
                
                if jup_sign_idx == d12_sign_idx:
                    birth_year = test_year
                    found_year = True
                    break
                    
            if not found_year:
                self.debug_print(f"Phase 1 Fallback: Jupiter was not in target sign within window. Defaulting to {birth_year}.")
                self.append_html(f"<li><i>Note: Could not find exact Jupiter transit within a 6-year window, defaulting to {birth_year}.</i></li>")
            else:
                self.debug_print(f"Phase 1 Success: Locked in birth year as {birth_year}.")
                self.append_html(f"<li>Scanning ephemeris around {rough_year}... Jupiter transited {ZODIAC_NAMES[d12_sign_idx]} exactly in <b>{birth_year}</b>.</li>")
                
            self.append_html(f"</ul><p style='color:#059669; font-size: 15px;'><b>Result: The person was born in {birth_year}.</b></p><hr>")

            # ==========================================
            # PHASE 2: Find the Season (Drekkana)
            # ==========================================
            self.append_html(f"<h3>PHASE 2: Find the Season (Using Drekkana & Swapping Rules)</h3>")
            
            # 1. Determine Ascendant Ayana
            # Strict standard rules: Cap-Gem (9,10,11,0,1,2) = North. Can-Sag (3,4,5,6,7,8) = South.
            # Special logic honoring the text: late Gemini tipping to South, late Sag tipping to North.
            is_northern_asc = asc_sign_idx in [9, 10, 11, 0, 1, 2]
            
            ayana_text = "Northern (Uttarayana)" if is_northern_asc else "Southern (Dakshinayana)"
            if asc_sign_idx == 2 and asc_deg_in_sign >= 25.0:
                is_northern_asc = False
                ayana_text = "Southern (Dakshinayana) <i>*Late Gemini tipping point applied</i>"
            elif asc_sign_idx == 8 and asc_deg_in_sign >= 25.0:
                is_northern_asc = True
                ayana_text = "Northern (Uttarayana) <i>*Late Sag tipping point applied</i>"
                
            self.debug_print(f"Phase 2: Ascendant Ayana resolved as {'Northern' if is_northern_asc else 'Southern'} (Tipping points checked)")
            self.append_html(f"<ul><li><b>Query Ayana (Sun's Path equivalent):</b> {ZODIAC_NAMES[asc_sign_idx]} at {asc_deg_in_sign:.2f}&deg; represents the <b>{ayana_text}</b> path.</li>")

            # 2. Calculate Drekkana Lord
            block = int(asc_deg_in_sign // 10)
            if block == 0:
                drekkana_sign = asc_sign_idx
            elif block == 1:
                drekkana_sign = (asc_sign_idx + 4) % 12
            else:
                drekkana_sign = (asc_sign_idx + 8) % 12
                
            drekkana_lord = astro_engine.SIGN_RULERS[drekkana_sign + 1]
            calculated_season = RITU_MAP[drekkana_lord]
            is_northern_lord = drekkana_lord in NORTHERN_RITUS
            
            self.debug_print(f"Phase 2: Drekkana Block = {block+1}. Sign = {ZODIAC_NAMES[drekkana_sign]}. Lord = {drekkana_lord} ({calculated_season}).")
            
            block_text = ["1st", "2nd", "3rd"][block]
            self.append_html(f"<li><b>Calculate Drekkana:</b> Ascendant falls into Block {block+1} ({block*10}&deg; to {(block+1)*10}&deg;).</li>")
            self.append_html(f"<li>This block is ruled by <b>{ZODIAC_NAMES[drekkana_sign]}</b>, whose lord is <b>{drekkana_lord}</b>.</li>")
            self.append_html(f"<li>{drekkana_lord} represents the <b>{calculated_season}</b> season.</li>")
            
            # 3. Apply Swapping Rules if clashed
            final_lord = drekkana_lord
            if is_northern_asc != is_northern_lord:
                final_lord = SWAP_MAP[drekkana_lord]
                final_season = RITU_MAP[final_lord]
                self.debug_print(f"Phase 2: Clash detected. Swapping {drekkana_lord} to {final_lord}.")
                self.append_html(f"<li><b>Check for Clash:</b> Mismatch! Ascendant path does not match the season's path.</li>")
                self.append_html(f"<li><b>Apply Swapping Rule:</b> We swap {drekkana_lord} for its partner, <b style='color:#ea580c;'>{final_lord}</b>.</li>")
            else:
                final_season = calculated_season
                self.debug_print(f"Phase 2: No clash. Retaining {final_lord}.")
                self.append_html(f"<li><b>Check for Clash:</b> No clash. Paths match perfectly.</li>")

            self.append_html(f"</ul><p style='color:#059669; font-size: 15px;'><b>Result: The person was born in the {final_season} season.</b></p><hr>")

            # ==========================================
            # PHASE 3: Find Exact Lunar Month (Half-Drekkanas)
            # ==========================================
            self.append_html(f"<h3>PHASE 3: Find the Exact Lunar Month (Using Half-Drekkanas)</h3>")
            
            offset_in_block = asc_deg_in_sign % 10.0
            is_second_half = offset_in_block >= 5.0
            half_text = "second half" if is_second_half else "first half"
            
            season_signs = SEASON_SUN_SIGNS[final_lord]
            target_sun_sign_idx = season_signs[1 if is_second_half else 0]
            
            self.debug_print(f"Phase 3: Half-Drekkana = {half_text}. Target Sun Sign Index = {target_sun_sign_idx} ({ZODIAC_NAMES[target_sun_sign_idx]}).")
            
            self.append_html(f"<ul>")
            self.append_html(f"<li>The {block_text} Drekkana block runs from {block*10}&deg; to {(block+1)*10}&deg;.</li>")
            self.append_html(f"<li>The Ascendant is at {asc_deg_in_sign:.2f}&deg;, which falls into the <b>{half_text}</b> of the block.</li>")
            self.append_html(f"<li>The {final_season} season corresponds to Sun transiting {ZODIAC_NAMES[season_signs[0]]} (1st month) and {ZODIAC_NAMES[season_signs[1]]} (2nd month).</li>")
            self.append_html(f"</ul><p style='color:#059669; font-size: 15px;'><b>Result: The birth occurred during the month when the Sun was in {ZODIAC_NAMES[target_sun_sign_idx]}.</b></p><hr>")

            # ==========================================
            # PHASE 4: Find the Exact Date of Birth (Kalas)
            # ==========================================
            self.append_html(f"<h3>PHASE 4: Find the Exact Date of Birth (Using Kalas ratios)</h3>")
            
            deg_pushed = offset_in_block % 5.0
            kalas = deg_pushed * 60.0
            sun_deg_in_sign = (kalas * 30.0) / 300.0
            
            # Exact absolute longitude the Sun needs to be at
            target_sun_lon_absolute = (target_sun_sign_idx * 30.0) + sun_deg_in_sign
            
            self.debug_print(f"Phase 4: Deg pushed = {deg_pushed:.6f}, Kalas = {kalas:.6f}. Target Sun in Sign = {sun_deg_in_sign:.6f}")
            self.debug_print(f"Phase 4: Absolute target Sun longitude required = {target_sun_lon_absolute:.6f}")
            
            self.append_html(f"<ul>")
            self.append_html(f"<li>Distance traveled into the 5-degree half-block = {self.deg_to_dms(deg_pushed)}.</li>")
            self.append_html(f"<li>Converted to Kalas (minutes): <b>{kalas:.2f} Kalas</b>.</li>")
            self.append_html(f"<li>Ratio application: ({kalas:.2f} * 30) / 300 = <b>{self.deg_to_dms(sun_deg_in_sign)}</b>.</li>")
            self.append_html(f"<li>So, the Sun's exact position at birth was {self.deg_to_dms(sun_deg_in_sign)} into <b style='color:#ea580c;'>{ZODIAC_NAMES[target_sun_sign_idx]}</b>.</li>")
            
            # Find the date in birth_year where the Sun crosses this longitude
            self.append_html(f"<li>Scanning Ephemeris for {birth_year}...</li>")
            
            # Binary search to find exact JD where Sun hits target longitude
            # Start bounds: Jan 1st of birth_year to Dec 31st.
            start_jd = astro_engine.ymdhms_to_jd(birth_year, 1, 1)
            end_jd = astro_engine.ymdhms_to_jd(birth_year, 12, 31)
            
            # We must be careful about the 360-degree wrap.
            # Convert longitudes to continuous representation if crossing Aries.
            exact_jd = start_jd
            for _ in range(40): # Binary search depth
                mid_jd = (start_jd + end_jd) / 2.0
                sun_pos = astro_engine.safe_calc_ut(mid_jd, swe.SUN, calc_flag)[0][0]
                
                # Calculate shortest angular distance
                diff = (sun_pos - target_sun_lon_absolute + 180) % 360 - 180
                
                if abs(diff) < 0.0001: 
                    exact_jd = mid_jd
                    break
                
                if diff > 0:
                    end_jd = mid_jd
                else:
                    start_jd = mid_jd
                    
            exact_jd = (start_jd + end_jd) / 2.0
            birth_date_dict = astro_engine.utc_jd_to_dt_dict(exact_jd, query_loc['tz'])
            
            self.debug_print(f"Phase 4: Target Sun matched at UTC JD {exact_jd:.6f}")
            self.debug_print(f"Phase 4: Mapped date is {birth_date_dict}")
            
            # Format the output Date cleanly
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            birth_date_str = f"{month_names[birth_date_dict['month']-1]} {birth_date_dict['day']}, {birth_date_dict['year']}"
            
            self.append_html(f"<li>The Sun reached exactly {self.deg_to_dms(sun_deg_in_sign)} of {ZODIAC_NAMES[target_sun_sign_idx]} on <b>{birth_date_str}</b>.</li>")
            self.append_html(f"</ul><p style='color:#059669; font-size: 15px;'><b>Result: Date of birth is {birth_date_str}.</b></p><hr>")

            # ==========================================
            # PHASE 5: Find the Exact Time of Birth (Comparing the Sun)
            # ==========================================
            self.append_html(f"<h3>PHASE 5: Find the Exact Time of Birth (Comparing the Sun)</h3>")
            
            # Find Sunrise on that day
            # Start search at 00:00 local time of that day
            midnight_jd_utc = astro_engine.dt_dict_to_utc_jd({
                'year': birth_date_dict['year'], 'month': birth_date_dict['month'], 
                'day': birth_date_dict['day'], 'hour': 0, 'minute': 0, 'second': 0
            }, query_loc['tz'])
            
            # Calculate Sunrise using astral
            try:
                tz_str = query_loc['tz']
                loc_info = LocationInfo(query_loc.get('name', 'Unknown'), "Region", tz_str, query_loc['lat'], query_loc['lon'])
                b_date = datetime.date(birth_date_dict['year'], birth_date_dict['month'], birth_date_dict['day'])
                
                s_events = sun(loc_info.observer, date=b_date, tzinfo=pytz.timezone(tz_str))
                sunrise_dt_astral = s_events['sunrise']
                
                # Convert to UTC to get accurate JD for swisseph
                sunrise_dt_utc = sunrise_dt_astral.astimezone(pytz.utc)
                decimal_hours = sunrise_dt_utc.hour + (sunrise_dt_utc.minute / 60.0) + (sunrise_dt_utc.second / 3600.0)
                sunrise_jd = swe.julday(sunrise_dt_utc.year, sunrise_dt_utc.month, sunrise_dt_utc.day, decimal_hours)
                
            except Exception as se:
                self.debug_print(f"Sunrise astral calculation exception: {se}. Using rough 6AM fallback.")
                # Fallback to rough 6 AM local
                sunrise_jd = midnight_jd_utc + (6.0 / 24.0)

            # Get Sun at Sunrise (The FLG_SPEED flag avoids zero division error)
            sunrise_sun_res = astro_engine.safe_calc_ut(sunrise_jd, swe.SUN, calc_flag)
            sunrise_sun_lon = sunrise_sun_res[0][0]
            daily_motion = sunrise_sun_res[0][3] # Degrees per day
            
            # ZeroDivision safety fallback if speed wasn't properly yielded
            if daily_motion == 0.0:
                self.debug_print("WARNING: daily_motion returned 0.0. Utilizing 0.9856 constant fallback.")
                daily_motion = 0.9856
                
            self.debug_print(f"Phase 5: Sunrise JD = {sunrise_jd:.6f}")
            self.debug_print(f"Phase 5: Sunrise Sun Abs. Lon = {sunrise_sun_lon:.6f}, Daily Motion = {daily_motion:.6f}")
            
            # Sunrise Datetime string
            sunrise_dt = astro_engine.utc_jd_to_dt_dict(sunrise_jd, query_loc['tz'])
            sunrise_str = f"{sunrise_dt['hour']:02d}:{sunrise_dt['minute']:02d} AM"
            
            # Calculate Difference
            diff_deg = target_sun_lon_absolute - sunrise_sun_lon
            # Handle cross-sign wrap
            diff_deg = (diff_deg + 180) % 360 - 180
            
            born_after = diff_deg > 0
            diff_deg_abs = abs(diff_deg)
            diff_mins = diff_deg_abs * 60.0
            
            # Calculate elapsed time from sunrise
            hours_elapsed = (diff_deg_abs * 24.0) / daily_motion
            
            self.debug_print(f"Phase 5: Angular Difference = {diff_deg:.6f} degrees. Born After Sunrise? {born_after}")
            self.debug_print(f"Phase 5: Total Calculated Elapsed Hours = {hours_elapsed:.6f}")
            
            # Apply to Sunrise time
            if born_after:
                final_birth_jd = sunrise_jd + (hours_elapsed / 24.0)
            else:
                final_birth_jd = sunrise_jd - (hours_elapsed / 24.0)
                
            final_dt = astro_engine.utc_jd_to_dt_dict(final_birth_jd, query_loc['tz'])
            
            ampm = "AM" if final_dt['hour'] < 12 else "PM"
            display_hour = final_dt['hour'] % 12
            if display_hour == 0: display_hour = 12
            
            final_time_str = f"{display_hour}:{final_dt['minute']:02d} {ampm}"
            
            self.append_html(f"<ul>")
            self.append_html(f"<li><b>Birth Sun:</b> {self.deg_to_dms(sun_deg_in_sign)} {ZODIAC_NAMES[target_sun_sign_idx]}.</li>")
            
            sunrise_sign = int(sunrise_sun_lon / 30.0)
            sunrise_deg_in_sign = sunrise_sun_lon % 30.0
            self.append_html(f"<li><b>Sunrise Sun:</b> {self.deg_to_dms(sunrise_deg_in_sign)} {ZODIAC_NAMES[sunrise_sign]}.</li>")
            
            if born_after:
                self.append_html(f"<li>Because Birth Sun > Sunrise Sun, they were born <b>after</b> sunrise.</li>")
            else:
                self.append_html(f"<li>Because Birth Sun < Sunrise Sun, they were born <b>before</b> sunrise.</li>")
                
            self.append_html(f"<li><b>Difference:</b> {diff_mins:.2f} minutes (angular).</li>")
            self.append_html(f"<li>The Sun's daily motion on that day was {daily_motion*60:.2f} minutes.</li>")
            
            h_whole = int(hours_elapsed)
            m_whole = int((hours_elapsed - h_whole) * 60)
            self.append_html(f"<li><b>Math time:</b> ({diff_mins:.2f} * 24 hours) / {daily_motion*60:.2f} = {hours_elapsed:.2f} hours.</li>")
            self.append_html(f"<li>{hours_elapsed:.2f} hours is <b>{h_whole} hours and {m_whole} minutes</b>.</li>")
            
            operator_word = "Added to" if born_after else "Subtracted from"
            self.append_html(f"<li>The sun rose at {sunrise_str} on that day. {operator_word} Sunrise:</li>")
            self.append_html(f"</ul><p style='color:#059669; font-size: 15px;'><b>Result: The person was born at {final_time_str}.</b></p><hr>")

            # ==========================================
            # THE FINAL REVELATION
            # ==========================================
            self.debug_print(f"=== REVELATION DONE: {birth_date_str} at {final_time_str} ===")
            self.append_html(f"<h2 style='color:#1e3a8a; text-align:center;'>THE FINAL REVELATION 🌟</h2>")
            self.append_html(f"<div style='text-align:center; background-color:#fef3c7; padding:25px; border:2px solid #fbbf24; border-radius:8px;'>")
            self.append_html(f"<p style='font-size:16px; color: #0f172a;'>By mathematically dissecting the stars at the exact moment the question was asked, we have fully reconstructed the lost birth data:</p>")
            self.append_html(f"<h1 style='color:#b45309; margin:15px 0; font-size: 28px;'>{birth_date_str} at {final_time_str}</h1>")
            self.append_html(f"<p style='color: #0f172a;'>With this data, you can now draw a complete, accurate birth chart.</p>")
            self.append_html(f"</div><br>")

        except Exception as e:
            import traceback
            err = traceback.format_exc()
            self.debug_print(f"CRITICAL ERROR: {str(e)}\n{err}")
            self.append_html(f"<p style='color:red;'><b>Critical Error during calculation:</b><br>{str(e)}<br>{err}</p>")


def setup_ui(app, layout):
    """
    Plugin Entry Point.
    Registers a button in the Dynamic Modules layout of the main App.
    """
    btn = QPushButton("🔮 Launch Nashta Jataka (Lost Horoscopy)")
    btn.setStyleSheet("""
        QPushButton {
            background-color: #8b5cf6;
            color: white;
            font-weight: bold;
            border-radius: 6px;
            padding: 12px;
            font-size: 14px;
            min-height: 45px;
        }
        QPushButton:hover { background-color: #7c3aed; }
        QPushButton:pressed { background-color: #6d28d9; }
    """)
    
    def on_click():
        # Store dialog on the app instance so it doesn't get garbage collected and remains detached
        if not hasattr(app, "nashta_dialog") or app.nashta_dialog is None:
            app.nashta_dialog = NashtaJatakaDialog(app)
            
        app.nashta_dialog.showMaximized() # Open Detached and Maximized
        app.nashta_dialog.raise_()
        app.nashta_dialog.activateWindow()
        
    btn.clicked.connect(on_click)
    layout.addWidget(btn)