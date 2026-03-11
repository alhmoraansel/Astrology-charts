import swisseph as swe
import datetime
import pytz

class EphemerisEngine:
    def __init__(self):
        # Using built-in swisseph ephemeris files (Moshier). 
        # For maximum precision, path to ephe files can be set here.
        swe.set_ephe_path('')
        
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
        """
        Calculates the Vedic chart (Sidereal positions).
        """
        # 1. Convert local time to UTC
        local_tz = pytz.timezone(tz_name)
        if dt.tzinfo is None:
            dt = local_tz.localize(dt)
        dt_utc = dt.astimezone(pytz.utc)
        
        # 2. Get Julian Day
        # swisseph julday expects UTC year, month, day, and decimal hours
        decimal_hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0
        jd_utc = swe.julday(dt_utc.year, dt_utc.month, dt_utc.day, decimal_hour)

        # 3. Configure Ayanamsa & Flags
        swe.set_sid_mode(self.ayanamsa_modes[self.current_ayanamsa])
        # Flags: Sidereal zodiac, Speed calculation (for retro), Swiss Ephemeris
        calc_flag = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
        
        # 4. Calculate Ascendant
        # houses_ex returns (cusps, ascmc). ascmc[0] is the Ascendant.
        # We use 'W' (Whole Sign) or 'P' (Placidus) but in Vedic, we just need the Asc degree.
        cusps, ascmc = swe.houses_ex(jd_utc, lat, lon, b'P', calc_flag)
        asc_deg = ascmc[0]
        asc_sign_index = int(asc_deg / 30)
        
        chart_data = {
            "ascendant": {
                "degree": asc_deg,
                "sign_index": asc_sign_index,
                "sign_num": asc_sign_index + 1
            },
            "planets": []
        }

        # 5. Calculate Planets
        bodies = [
            ("Sun", "Su", swe.SUN), ("Moon", "Mo", swe.MOON),
            ("Mars", "Ma", swe.MARS), ("Mercury", "Me", swe.MERCURY),
            ("Jupiter", "Ju", swe.JUPITER), ("Venus", "Ve", swe.VENUS),
            ("Saturn", "Sa", swe.SATURN), ("Rahu", "Ra", swe.TRUE_NODE)
        ]

        for name, sym, body_id in bodies:
            res, _ = swe.calc_ut(jd_utc, body_id, calc_flag)
            lon_deg = res[0]
            speed = res[3]
            
            p_sign_idx = int(lon_deg / 30)
            deg_in_sign = lon_deg % 30
            is_retro = speed < 0 if name not in ["Sun", "Moon", "Rahu", "Ketu"] else False
            if name == "Rahu":
                is_retro = True # Nodes are usually always retrograde in display

            house_num = (p_sign_idx - asc_sign_index) % 12 + 1

            chart_data["planets"].append({
                "name": name, "sym": sym, "lon": lon_deg,
                "sign_index": p_sign_idx, "sign_num": p_sign_idx + 1,
                "deg_in_sign": deg_in_sign, "house": house_num, "retro": is_retro
            })

        # Calculate Ketu (Exactly 180 degrees from Rahu)
        rahu = next(p for p in chart_data["planets"] if p["name"] == "Rahu")
        ketu_lon = (rahu["lon"] + 180.0) % 360.0
        ketu_sign_idx = int(ketu_lon / 30)
        ketu_deg_in_sign = ketu_lon % 30
        ketu_house = (ketu_sign_idx - asc_sign_index) % 12 + 1
        
        chart_data["planets"].append({
            "name": "Ketu", "sym": "Ke", "lon": ketu_lon,
            "sign_index": ketu_sign_idx, "sign_num": ketu_sign_idx + 1,
            "deg_in_sign": ketu_deg_in_sign, "house": ketu_house, "retro": True
        })

        chart_data["aspects"] = self.calculate_vedic_aspects(chart_data["planets"])

        return chart_data

    def calculate_vedic_aspects(self, planets):
        aspects = []
        # Vedic Aspect Rules: Planet -> List of houses it aspects (counting itself as 1)
        aspect_rules = {
            "Sun": [7],
            "Moon": [7],
            "Mercury": [7],
            "Venus": [7],
            "Mars": [4, 7, 8],
            "Jupiter": [5, 7, 9],
            "Saturn": [3, 7, 10],
            "Rahu": [5, 7, 9],
            "Ketu": [5, 7, 9]
        }
        
        # Colors associated with each planet's aspect line
        planet_colors = {
            "Sun": "orange", "Moon": "blue", "Mars": "red",
            "Mercury": "green", "Jupiter": "yellow", "Venus": "pink",
            "Saturn": "purple", "Rahu": "gray", "Ketu": "gray"
        }

        for p in planets:
            p_name = p["name"]
            p_house = p["house"]
            rules = aspect_rules.get(p_name, [])

            for aspect_count in rules:
                # Calculate target house counting clockwise (which maps linearly to our house numbers)
                # Formula: (Current House + Aspect Count - 2) % 12 + 1
                target_house = (p_house + aspect_count - 2) % 12 + 1
                
                aspects.append({
                    "aspecting_planet": p_name,
                    "source_house": p_house,
                    "target_house": target_house,
                    "aspect_count": aspect_count,
                    "color": planet_colors.get(p_name, "white")
                })
                
        return aspects