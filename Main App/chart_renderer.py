from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush
from PyQt6.QtCore import Qt, QRectF

class ChartRenderer(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.chart_data = None
        
        self.dark_mode = False
        self.use_symbols = False
        self.show_rahu_ketu = True
        self.highlight_asc_moon = True

        # Unicode astrology symbols mapping
        self.unicode_syms = {
            "Sun": "☉", "Moon": "☽", "Mars": "♂", "Mercury": "☿",
            "Jupiter": "♃", "Venus": "♀", "Saturn": "♄", 
            "Rahu": "☊", "Ketu": "☋"
        }

        # The relative center coordinates for the 12 houses in a standard North Indian Chart
        # H1 is top-center, going counter-clockwise
        self.house_centers = {
            1: (0.5, 0.25), 2: (0.25, 0.125), 3: (0.125, 0.25),
            4: (0.25, 0.5), 5: (0.125, 0.75), 6: (0.25, 0.875),
            7: (0.5, 0.75), 8: (0.75, 0.875), 9: (0.875, 0.75),
            10: (0.75, 0.5), 11: (0.875, 0.25), 12: (0.75, 0.125)
        }
        
        # Zodiac number positions (slightly offset from the dead center)
        self.sign_offsets = {
            1: (0.5, 0.1), 2: (0.1, 0.05), 3: (0.05, 0.1),
            4: (0.1, 0.5), 5: (0.05, 0.9), 6: (0.1, 0.95),
            7: (0.5, 0.9), 8: (0.9, 0.95), 9: (0.95, 0.9),
            10: (0.9, 0.5), 11: (0.95, 0.1), 12: (0.9, 0.05)
        }

    def update_chart(self, data):
        self.chart_data = data
        self.update()

    def set_theme(self, dark_mode: bool):
        self.dark_mode = dark_mode
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Setup Colors based on theme
        bg_color = QColor("#1E1E1E") if self.dark_mode else QColor("#FFFFFF")
        line_color = QColor("#DDDDDD") if self.dark_mode else QColor("#222222")
        text_color = QColor("#FFFFFF") if self.dark_mode else QColor("#000000")
        accent_color = QColor("#E74C3C") if self.dark_mode else QColor("#C0392B")
        moon_color = QColor("#3498DB") if self.dark_mode else QColor("#2980B9")

        # Fill background
        painter.fillRect(self.rect(), bg_color)

        # Calculate square boundaries
        size = min(self.width(), self.height()) - 40
        cx = self.width() / 2
        cy = self.height() / 2
        
        # Draw the chart geometry
        x = cx - size / 2
        y = cy - size / 2
        w = size
        h = size

        pen = QPen(line_color, 2)
        painter.setPen(pen)

        # 1. Outer Square
        painter.drawRect(int(x), int(y), int(w), int(h))
        # 2. X diagonals
        painter.drawLine(int(x), int(y), int(x + w), int(y + h))
        painter.drawLine(int(x + w), int(y), int(x), int(y + h))
        # 3. Inner Diamond
        painter.drawLine(int(x + w/2), int(y), int(x + w), int(y + h/2))
        painter.drawLine(int(x + w), int(y + h/2), int(x + w/2), int(y + h))
        painter.drawLine(int(x + w/2), int(y + h), int(x), int(y + h/2))
        painter.drawLine(int(x), int(y + h/2), int(x + w/2), int(y))

        if not self.chart_data:
            painter.setPen(text_color)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No Chart Data")
            return

        # Prepare planets per house
        houses = {i: [] for i in range(1, 13)}
        
        # Add Ascendant mark to 1st house
        if self.highlight_asc_moon:
            houses[1].append(("Asc", accent_color))

        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"] and not self.show_rahu_ketu:
                continue
                
            display_str = self.unicode_syms[p["name"]] if self.use_symbols else p["sym"]
            if p["retro"]:
                display_str += "(R)"
                
            col = text_color
            if p["name"] == "Moon" and self.highlight_asc_moon:
                col = moon_color
                
            houses[p["house"]].append((display_str, col))

        # Draw House Numbers and Planets
        asc_sign = self.chart_data["ascendant"]["sign_num"]
        
        for h_num in range(1, 13):
            # Calculate sign number for this house
            zodiac_num = (asc_sign + h_num - 2) % 12 + 1
            
            # Draw Zodiac number
            z_rx, z_ry = self.sign_offsets[h_num]
            zx = x + z_rx * w
            zy = y + z_ry * h
            
            painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            painter.setPen(QColor("#777777") if not self.dark_mode else QColor("#888888"))
            
            # Adjust minor alignment based on corner
            align = Qt.AlignmentFlag.AlignCenter
            rect = QRectF(zx - 15, zy - 15, 30, 30)
            painter.drawText(rect, align, str(zodiac_num))

            # Draw Planets
            p_rx, p_ry = self.house_centers[h_num]
            px = x + p_rx * w
            py = y + p_ry * h
            
            painter.setFont(QFont("Arial", 11, QFont.Weight.Medium))
            
            # Stack planets vertically in the house center
            y_offset = - (len(houses[h_num]) * 16) / 2
            for p_str, p_color in houses[h_num]:
                painter.setPen(p_color)
                p_rect = QRectF(px - 40, py + y_offset, 80, 20)
                painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, p_str)
                y_offset += 16