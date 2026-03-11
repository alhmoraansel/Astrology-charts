import math
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
import swisseph as swe
import datetime

class TimeController(QObject):
    # Signals components to avoid year limits
    time_changed = pyqtSignal(int, int, int, int, int, int) 

    def __init__(self):
        super().__init__()
        now = datetime.datetime.now()
        # Internal state is Julian Day for perfect BCE handling
        self.jd = swe.julday(now.year, now.month, now.day, 
                             now.hour + now.minute/60.0 + now.second/3600.0)
        
        self.timer = QTimer(self)
        self.timer.setInterval(100) # 10 FPS
        self.timer.timeout.connect(self._on_tick)
        self.is_playing = False
        self.speed_multiplier = 1.0

    def set_time(self, y, m, d, h, mi, s):
        self.jd = swe.julday(y, m, d, h + mi/60.0 + s/3600.0)
        self.time_changed.emit(y, m, d, h, mi, s)

    def set_jd(self, jd):
        self.jd = jd
        y, m, d, h_dec = swe.revjul(self.jd, 1)
        h = int(h_dec); mi = int((h_dec - h) * 60); s = int(((h_dec - h) * 60 - mi) * 60)
        self.time_changed.emit(int(y), int(m), int(d), h, mi, s)

    def get_components(self):
        y, m, d, h_dec = swe.revjul(self.jd, 1)
        h = int(h_dec); mi = int((h_dec - h) * 60); s = int(((h_dec - h) * 60 - mi) * 60)
        return int(y), int(m), int(d), h, mi, s

    def step(self, seconds):
        self.jd += (seconds / 86400.0)
        self.set_jd(self.jd)

    def toggle_animation(self):
        self.is_playing = not self.is_playing
        if self.is_playing: self.timer.start()
        else: self.timer.stop()
        return self.is_playing

    def set_speed(self, multiplier: float):
        self.speed_multiplier = multiplier

    def _on_tick(self):
        # 100ms real time = 0.1 * multiplier virtual seconds
        self.step(0.1 * self.speed_multiplier)