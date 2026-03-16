# animation.py
import math
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import datetime
import astro_engine

class TimeController(QObject):
    time_changed = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        now = datetime.datetime.now()
        # Maintain an internal dictionary map suitable for BCE calculations
        self.current_time = {'year': now.year, 'month': now.month, 'day': now.day, 'hour': now.hour, 'minute': now.minute, 'second': now.second}
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.setInterval(300) # 30 FPS
        self.timer.timeout.connect(self._on_tick)
        
        self.is_playing = False
        self.speed_multiplier = 3.11 # 1 real sec = x virtual secs

    def set_time(self, dt):
        if isinstance(dt, datetime.datetime):
            self.current_time = {'year': dt.year, 'month': dt.month, 'day': dt.day, 'hour': dt.hour, 'minute': dt.minute, 'second': dt.second}
        else:
            self.current_time = dict(dt)
        self.time_changed.emit(self.current_time)

    def step(self, delta_seconds: float):
        # By translating to Julian Day mathematically, we completely bypass Python's datetime BCE limits
        jd = astro_engine.ymdhms_to_jd(self.current_time['year'], self.current_time['month'], self.current_time['day'], 
                                       self.current_time['hour'], self.current_time['minute'], self.current_time['second'])
        jd += delta_seconds / 86400.0
        self.current_time = astro_engine.jd_to_ymdhms(jd)
        self.time_changed.emit(self.current_time)

    def toggle_animation(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.timer.start()
        else:
            self.timer.stop()
        return self.is_playing

    def set_speed(self, multiplier: float):
        """Multiplier indicates how many virtual seconds pass per real second."""
        self.speed_multiplier = multiplier

    def _on_tick(self):
        # 100ms tick = 0.1 real seconds
        # virtual seconds to add = 0.1 * multiplier
        delta_seconds = 0.1 * self.speed_multiplier
        self.step(delta_seconds)

def get_circular_coords(lon, asc_deg, lane_index, w, h):
    """Calculates concentric splines specifically tailored for Circular chart mode."""
    anchors = []
    angles = [270, 240, 210, 180, 150, 120, 90, 60, 30, 0, 330, 300]
    for a in angles:
        rad = math.radians(a)
        anchors.append((0.5 + 0.30 * math.cos(rad), 0.5 + 0.30 * math.sin(rad)))
    spacing = 0.09
    
    t = (lon - asc_deg) % 360 / 30.0
    i = int(t)
    f = t - i
    
    p0 = anchors[(i - 1) % 12]
    p1 = anchors[i % 12]
    p2 = anchors[(i + 1) % 12]
    p3 = anchors[(i + 2) % 12]
    
    t2 = f * f
    t3 = t2 * f
    
    rx = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * f + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
    ry = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * f + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
    
    lane_factor = 1.0 + (lane_index - 4.5) * spacing
    final_rx = 0.5 + (rx - 0.5) * lane_factor
    final_ry = 0.5 + (ry - 0.5) * lane_factor
    
    return final_rx * w, final_ry * h

def get_diamond_planet_coords(h_num, idx, total, w, h):
    house_centers = {
        1: (0.5, 0.25), 2: (0.25, 0.09), 3: (0.09, 0.25),
        4: (0.25, 0.5), 5: (0.09, 0.75), 6: (0.25, 0.91),
        7: (0.5, 0.75), 8: (0.75, 0.91), 9: (0.91, 0.75),
        10: (0.75, 0.5), 11: (0.91, 0.25), 12: (0.75, 0.09)
    }
    rx, ry = house_centers[h_num]
    
    # Base vertical spacing between planets to avoid overlap
    spacing = 16
    
    # Compress spacing dynamically if a house gets heavily crowded (Stellium)
    if total > 4:
        spacing = 14
    if total > 6:
        spacing = 12
        
    # Calculate starting Y offset to perfectly center the entire vertical stack inside the house
    start_y = -((total - 1) * spacing) / 2.0
    
    offset_x = 0  # 0 offset ensures they are perfectly centered horizontally
    offset_y = start_y + (idx * spacing)
    
    return (rx * w) + offset_x, (ry * h) + offset_y

def get_diamond_house_center(h_num, w, h):
    """Gets the pure geometric center of the house box (Used to perfectly aim Aspect Lines and place Zodiacs)."""
    house_centers = {
        1: (0.5, 0.25), 2: (0.25, 0.09), 3: (0.09, 0.25),
        4: (0.25, 0.5), 5: (0.09, 0.75), 6: (0.25, 0.91),
        7: (0.5, 0.75), 8: (0.75, 0.91), 9: (0.91, 0.75),
        10: (0.75, 0.5), 11: (0.91, 0.25), 12: (0.75, 0.09)
    }
    hx, hy = house_centers[h_num]
    return hx * w, hy * h

def get_diamond_zodiac_coords(h_num, w, h, has_planets=False):
    """Places zodiac numerals cleanly in the inner corners close to the center if planets are present, else exactly at the center."""
    if not has_planets:
        return get_diamond_house_center(h_num, w, h)
        
    # Tucks deeply into the 90-degree inner corners to avoid vertically stacked planets
    sign_offsets = {
        1: (0.5, 0.42), 2: (0.25, 0.20), 3: (0.20, 0.25),
        4: (0.42, 0.5), 5: (0.20, 0.75), 6: (0.25, 0.80),
        7: (0.5, 0.58), 8: (0.75, 0.80), 9: (0.80, 0.75),
        10: (0.58, 0.5), 11: (0.80, 0.25), 12: (0.75, 0.20)
    }
    sx, sy = sign_offsets[h_num]
    return sx * w, sy * h