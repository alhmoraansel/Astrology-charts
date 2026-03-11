import math
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import datetime

class TimeController(QObject):
    time_changed = pyqtSignal(datetime.datetime)

    def __init__(self):
        super().__init__()
        self.current_time = datetime.datetime.now()
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.setInterval(100) # 10 FPS
        self.timer.timeout.connect(self._on_tick)
        
        self.is_playing = False
        self.speed_multiplier = 1.0 # 1 real sec = x virtual secs

    def set_time(self, dt: datetime.datetime):
        self.current_time = dt
        self.time_changed.emit(self.current_time)

    def step(self, delta: datetime.timedelta):
        self.current_time += delta
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
        self.step(datetime.timedelta(seconds=delta_seconds))

def get_circular_coords(lon, asc_deg, lane_index, w, h):
    """Calculates concentric splines specifically tailored for Circular chart mode."""
    # Full circular orbit anchors for massive breathing room
    anchors = []
    # 12 houses, start at top (270 deg) and go anti-clockwise 
    angles = [270, 240, 210, 180, 150, 120, 90, 60, 30, 0, 330, 300]
    for a in angles:
        rad = math.radians(a)
        # Base radius is 0.30 to allow outer lanes to expand up to 0.45, staying inside the frame
        anchors.append((0.5 + 0.30 * math.cos(rad), 0.5 + 0.30 * math.sin(rad)))
    spacing = 0.09
    
    # Continuous progression mapped 0.0 to 12.0 based on distance from Lagna
    t = (lon - asc_deg) % 360 / 30.0
    i = int(t)
    f = t - i
    
    # Catmull-Rom spline interpolation for perfectly rounded, smooth movement
    p0 = anchors[(i - 1) % 12]
    p1 = anchors[i % 12]
    p2 = anchors[(i + 1) % 12]
    p3 = anchors[(i + 2) % 12]
    
    t2 = f * f
    t3 = t2 * f
    
    rx = 0.5 * ((2 * p1[0]) +
                (-p0[0] + p2[0]) * f +
                (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 +
                (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
    
    ry = 0.5 * ((2 * p1[1]) +
                (-p0[1] + p2[1]) * f +
                (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 +
                (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
    
    # Apply lane offset radially from center (0.5, 0.5) to keep orbits strictly separated
    lane_factor = 1.0 + (lane_index - 4.5) * spacing
    
    final_rx = 0.5 + (rx - 0.5) * lane_factor
    final_ry = 0.5 + (ry - 0.5) * lane_factor
    
    return final_rx * w, final_ry * h


def get_diamond_planet_coords(h_num, idx, total, w, h):
    """
    STRICT Diamond Mode Coordinates: Distributes multiple planets safely inside 
    the exact physical layout of the target house using a mathematical 2-column grid.
    No curved tracks used. 
    """
    house_centers = {
        1: (0.5, 0.28), 2: (0.25, 0.15), 3: (0.15, 0.25),
        4: (0.28, 0.5), 5: (0.15, 0.75), 6: (0.25, 0.85),
        7: (0.5, 0.72), 8: (0.75, 0.85), 9: (0.85, 0.75),
        10: (0.72, 0.5), 11: (0.85, 0.25), 12: (0.75, 0.15)
    }
    rx, ry = house_centers[h_num]
    
    cols = 2 if total > 2 else total
    if cols == 0: cols = 1
    rows = math.ceil(total / cols)
    
    c = idx % cols
    r = idx // cols
    
    # Compute a perfectly centered offset matrix based on planet count
    start_x = -((cols - 1) * 55) / 2.0
    start_y = -((rows - 1) * 20) / 2.0
    
    offset_x = start_x + c * 55
    offset_y = start_y + r * 20
    
    return (rx * w) + offset_x, (ry * h) + offset_y


def get_diamond_zodiac_coords(h_num, w, h):
    """Places zodiac numerals cleanly in the deep corners of the respective Diamond house shapes."""
    sign_offsets = {
        1: (0.5, 0.12), 2: (0.28, 0.08), 3: (0.08, 0.28),
        4: (0.12, 0.5), 5: (0.08, 0.72), 6: (0.28, 0.92),
        7: (0.5, 0.88), 8: (0.72, 0.92), 9: (0.92, 0.72),
        10: (0.88, 0.5), 11: (0.92, 0.28), 12: (0.72, 0.08)
    }
    sx, sy = sign_offsets[h_num]
    return sx * w, sy * h


def get_diamond_house_center(h_num, w, h):
    """Gets the pure geometric center of the house box (Used to perfectly aim Aspect Lines)."""
    house_centers = {
        1: (0.5, 0.25), 2: (0.25, 0.125), 3: (0.125, 0.25),
        4: (0.25, 0.5), 5: (0.125, 0.75), 6: (0.25, 0.875),
        7: (0.5, 0.75), 8: (0.75, 0.875), 9: (0.875, 0.75),
        10: (0.75, 0.5), 11: (0.875, 0.25), 12: (0.75, 0.125)
    }
    hx, hy = house_centers[h_num]
    return hx * w, hy * h