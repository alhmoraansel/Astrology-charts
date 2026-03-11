from PyQt6.QtCore import QThread, pyqtSignal
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

class LocationWorker(QThread):
    """
    Runs location geocoding and timezone resolution in a background thread
    to prevent the GUI from freezing.
    """
    result_ready = pyqtSignal(float, float, str, str) # lat, lon, tz_name, formatted_name
    error_occurred = pyqtSignal(str)

    def __init__(self, location_name):
        super().__init__()
        self.location_name = location_name

    def run(self):
        try:
            # Initialize geocoder
            geolocator = Nominatim(user_agent="vedic_astro_app_v1")
            location = geolocator.geocode(self.location_name, timeout=10)
            
            if location:
                lat = location.latitude
                lon = location.longitude
                formatted_name = location.address
                
                # Find timezone
                tf = TimezoneFinder()
                tz_name = tf.timezone_at(lng=lon, lat=lat)
                
                if not tz_name:
                    tz_name = "UTC" # Fallback
                    
                self.result_ready.emit(lat, lon, tz_name, formatted_name)
            else:
                self.error_occurred.emit("Location not found.")
        except Exception as e:
            self.error_occurred.emit(f"Network or Geocoding Error: {str(e)}")