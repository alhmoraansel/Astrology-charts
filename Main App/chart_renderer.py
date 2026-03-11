from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPolygonF
from PyQt6.QtCore import Qt, QRectF, QPointF
import math

class ChartRenderer(QWidget):
    def __init__(self):
        super().__init__()
        self.setMinimumSize(400, 400)
        self.chart_data = None
        
        self.dark_mode = False
        self.use_symbols = False
        self.show_rahu_ketu = True
        self.highlight_asc_moon = True
        self.show_aspects = False
        self.visible_aspect_planets = set() # Store which planets' aspects to draw

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

    def _get_house_polygon(self, h_num, x, y, w, h):
        """Returns a QPolygonF representing the exact geometric bounds of a given house."""
        p_tl = QPointF(x, y)
        p_tr = QPointF(x+w, y)
        p_bl = QPointF(x, y+h)
        p_br = QPointF(x+w, y+h)
        p_tc = QPointF(x+w/2, y)
        p_bc = QPointF(x+w/2, y+h)
        p_lc = QPointF(x, y+h/2)
        p_rc = QPointF(x+w, y+h/2)
        p_cc = QPointF(x+w/2, y+h/2)
        
        p_i_tl = QPointF(x+w/4, y+h/4)
        p_i_tr = QPointF(x+3*w/4, y+h/4)
        p_i_bl = QPointF(x+w/4, y+3*h/4)
        p_i_br = QPointF(x+3*w/4, y+3*h/4)

        polys = {
            1: [p_tc, p_i_tr, p_cc, p_i_tl],
            2: [p_tl, p_tc, p_i_tl],
            3: [p_tl, p_i_tl, p_lc],
            4: [p_lc, p_i_tl, p_cc, p_i_bl],
            5: [p_lc, p_i_bl, p_bl],
            6: [p_i_bl, p_bc, p_bl],
            7: [p_cc, p_i_br, p_bc, p_i_bl],
            8: [p_bc, p_i_br, p_br],
            9: [p_i_br, p_rc, p_br],
            10: [p_i_tr, p_rc, p_i_br, p_cc],
            11: [p_tr, p_rc, p_i_tr],
            12: [p_tc, p_tr, p_i_tr]
        }
        return QPolygonF(polys[h_num])

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
        
        # Bright Planet Colors mapping
        bright_colors = {
            "Sun": QColor("#FFAA00") if not self.dark_mode else QColor("#FFD700"),     # Gold/Orange
            "Moon": QColor("#0066CC") if not self.dark_mode else QColor("#33CCFF"),    # Blue/Cyan
            "Mars": QColor("#CC0000") if not self.dark_mode else QColor("#FF3333"),    # Red
            "Mercury": QColor("#009900") if not self.dark_mode else QColor("#33FF33"), # Green
            "Jupiter": QColor("#B8860B") if not self.dark_mode else QColor("#FFFF66"), # Yellow/Gold
            "Venus": QColor("#CC00CC") if not self.dark_mode else QColor("#FF66FF"),   # Pink/Magenta
            "Saturn": QColor("#6600CC") if not self.dark_mode else QColor("#B266FF"),  # Purple
            "Rahu": QColor("#666666") if not self.dark_mode else QColor("#AAAAAA"),    # Gray
            "Ketu": QColor("#666666") if not self.dark_mode else QColor("#AAAAAA"),    # Gray
            "Asc": QColor("#E74C3C") if self.dark_mode else QColor("#C0392B")
        }

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

        # 0. Draw Tinted Aspected Houses (underneath the grid lines)
        if self.show_aspects and self.chart_data and "aspects" in self.chart_data:
            color_map = {
                # Reduced alpha from 45 to 20 for softer coloring that doesn't bleed out the whole chart
                "orange": QColor(255, 165, 0, 20),
                "blue": QColor(50, 150, 255, 20),
                "red": QColor(255, 50, 50, 20),
                "green": QColor(50, 255, 50, 20),
                "yellow": QColor(255, 255, 0, 20) if self.dark_mode else QColor(200, 180, 0, 20),
                "pink": QColor(255, 105, 180, 20),
                "purple": QColor(160, 32, 240, 20),
                "gray": QColor(150, 150, 150, 20)
            }
            
            for aspect in self.chart_data["aspects"]:
                p_name = aspect["aspecting_planet"]
                if p_name not in self.visible_aspect_planets: continue
                if p_name in ["Rahu", "Ketu"] and not self.show_rahu_ketu: continue
                
                h2 = aspect["target_house"]
                tint_color = color_map.get(aspect["color"], QColor(255, 255, 255, 20))
                
                painter.setBrush(QBrush(tint_color))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawPolygon(self._get_house_polygon(h2, x, y, w, h))

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

        # Draw Aspects if enabled
        if self.show_aspects:
            self._draw_aspects(painter, x, y, w, h)

        # Prepare planets per house
        houses = {i: [] for i in range(1, 13)}
        
        # Add Ascendant mark to 1st house
        if self.highlight_asc_moon:
            houses[1].append(("Asc", bright_colors["Asc"]))

        for p in self.chart_data["planets"]:
            if p["name"] in ["Rahu", "Ketu"] and not self.show_rahu_ketu:
                continue
                
            display_str = self.unicode_syms[p["name"]] if self.use_symbols else p["sym"]
            if p["retro"]:
                display_str += "(R)"
                
            # Use bright color for planet
            col = bright_colors.get(p["name"], text_color)
                
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
            
            painter.setFont(QFont("Arial", 12, QFont.Weight.Bold)) # Slightly larger, bold font for planets
            
            # Stack planets vertically in the house center
            y_offset = - (len(houses[h_num]) * 16) / 2
            for p_str, p_color in houses[h_num]:
                painter.setPen(p_color)
                p_rect = QRectF(px - 40, py + y_offset, 80, 20)
                painter.drawText(p_rect, Qt.AlignmentFlag.AlignCenter, p_str)
                y_offset += 16
                
        # Draw Aspects lines
        if self.show_aspects:
            self._draw_aspects(painter, x, y, w, h)

    def _get_planet_coord(self, house, w, h):
        rx, ry = self.house_centers[house]
        return rx * w, ry * h

    def _draw_aspect_line(self, painter, x1, y1, x2, y2, color_name, offset_idx=0):
        color_map = {
            "orange": QColor(255, 165, 0, 160),
            "blue": QColor(50, 150, 255, 160),
            "red": QColor(255, 50, 50, 160),
            "green": QColor(50, 255, 50, 160),
            "yellow": QColor(255, 255, 0, 160),
            "pink": QColor(255, 105, 180, 160),
            "purple": QColor(160, 32, 240, 160),
            "gray": QColor(150, 150, 150, 160)
        }
        
        color = color_map.get(color_name, QColor(255, 255, 255, 160))
        if not self.dark_mode and color_name == "yellow":
            color = QColor(200, 180, 0, 180) 
            
        # Add slight visual offset so aspects from different planets in the same house don't perfectly overlap
        ox = (offset_idx % 3 - 1) * 4
        oy = ((offset_idx + 1) % 3 - 1) * 4
        x1 += ox; y1 += oy
        x2 += ox; y2 += oy
            
        dx = x2 - x1
        dy = y2 - y1
        dist = math.hypot(dx, dy)
        if dist == 0: return
        
        # Shrink lines at start and end so they don't block the house contents
        padding = 35
        if dist < padding * 2: return
        
        sx = x1 + (dx/dist) * padding
        sy = y1 + (dy/dist) * padding
        ex = x2 - (dx/dist) * padding
        ey = y2 - (dy/dist) * padding
        
        # Draw transparent line
        pen = QPen(color, 2.0, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        painter.drawLine(int(sx), int(sy), int(ex), int(ey))
        
        # Draw Arrowhead
        angle = math.atan2(ey - sy, ex - sx)
        arrow_size = 9
        p1_x = ex - arrow_size * math.cos(angle - math.pi / 6)
        p1_y = ey - arrow_size * math.sin(angle - math.pi / 6)
        p2_x = ex - arrow_size * math.cos(angle + math.pi / 6)
        p2_y = ey - arrow_size * math.sin(angle + math.pi / 6)

        painter.setBrush(QBrush(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(ex, ey), QPointF(p1_x, p1_y), QPointF(p2_x, p2_y)]))

    def _draw_aspects(self, painter, x, y, w, h):
        if "aspects" not in self.chart_data:
            return
            
        for i, aspect in enumerate(self.chart_data["aspects"]):
            p_name = aspect["aspecting_planet"]
            
            # Filter based on user checkboxes
            if p_name not in self.visible_aspect_planets:
                continue
            if p_name in ["Rahu", "Ketu"] and not self.show_rahu_ketu:
                continue
            
            h1 = aspect["source_house"]
            h2 = aspect["target_house"]
            
            if h1 == h2:
                continue 
                
            rx1, ry1 = self._get_planet_coord(h1, w, h)
            rx2, ry2 = self._get_planet_coord(h2, w, h)
            
            self._draw_aspect_line(painter, x + rx1, y + ry1, x + rx2, y + ry2, aspect["color"], offset_idx=i)