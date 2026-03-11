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