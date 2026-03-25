# dynamic_settings_modules/advanced_bphs_calcs.py

import sys, math
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QComboBox, QScrollArea, QGroupBox)
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath
from PyQt6.QtCore import Qt, QRectF, QPointF, QTimer
import swisseph as swe
import __main__

# Attempt to load SmoothScroller from the main application namespace
SmoothScroller = getattr(__main__, 'SmoothScroller', None)

# ==========================================
# CUSTOM UI COMPONENTS FOR INSTANT TOOLTIPS
# ==========================================

class CustomTooltipTable(QTableWidget):
    """A custom table that bypasses OS delays to show HTML tooltips instantly following the cursor."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseTracking(True)
        self.tooltip_label = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""
            QLabel { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; font-size: 13px; font-family: 'Segoe UI', Tahoma, sans-serif; }
        """)
        self.tooltip_label.hide()

    def mouseMoveEvent(self, event):
        pos = event.pos()
        item = self.itemAt(pos)

        tt_text = ""
        if item and item.data(Qt.ItemDataRole.UserRole):
            tt_text = item.data(Qt.ItemDataRole.UserRole)

        if tt_text:
            if self.tooltip_label.text() != tt_text:
                self.tooltip_label.setText(tt_text)
                self.tooltip_label.adjustSize()

            global_pos = event.globalPosition().toPoint()
            new_x, new_y = global_pos.x() + 15, global_pos.y() + 15
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): new_x = global_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): new_y = global_pos.y() - self.tooltip_label.height() - 5

            self.tooltip_label.move(new_x, new_y)
            if not self.tooltip_label.isVisible(): self.tooltip_label.show()
            self.tooltip_label.raise_()
        else:
            self.tooltip_label.hide()

        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tooltip_label.hide()
        super().leaveEvent(event)


# ==========================================
# CUSTOM VISUALIZATIONS
# ==========================================
class IshtKashtBarChart(QWidget):
    # (Remains unchanged from your original code)
    def __init__(self, data_dict, parent=None):
        super().__init__(parent)
        self.data_dict = data_dict
        self.setMinimumSize(850, 280)
        self.setMouseTracking(True)
        self.hover_rects = {}
        self.tooltip_label = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""QLabel { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; font-size: 13px; }""")
        self.tooltip_label.hide()

    def mouseMoveEvent(self, event):
        pos_f = QPointF(float(event.pos().x()), float(event.pos().y()))
        tt_text = ""
        for p_name, (rect, html_text) in self.hover_rects.items():
            if rect.contains(pos_f):
                tt_text = html_text
                break
        if tt_text:
            if self.tooltip_label.text() != tt_text:
                self.tooltip_label.setText(tt_text)
                self.tooltip_label.adjustSize()
            g_pos = event.globalPosition().toPoint()
            new_x, new_y = g_pos.x() + 15, g_pos.y() + 15
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): new_x = g_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): new_y = g_pos.y() - self.tooltip_label.height() - 5
            self.tooltip_label.move(new_x, new_y)
            self.tooltip_label.show()
            self.tooltip_label.raise_()
        else:
            self.tooltip_label.hide()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tooltip_label.hide()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#F8FAFC"))

        if not self.data_dict:
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "No Calculation Data Available")
            return

        planets = list(self.data_dict.keys())
        num_planets = len(planets)
        margin_left, margin_bottom, margin_top, margin_right = 50, 45, 40, 20
        w = self.width() - margin_left - margin_right
        h = self.height() - margin_top - margin_bottom

        painter.setPen(QPen(QColor("#CBD5E1"), 2))
        painter.drawLine(margin_left, margin_top, margin_left, margin_top + h)
        painter.drawLine(margin_left, margin_top + h, margin_left + w, margin_top + h)

        max_val = 60.0
        bar_width = (w / num_planets) * 0.25
        spacing = (w / num_planets)

        painter.setFont(QFont("Segoe UI", 8))
        for i in range(0, 61, 15):
            y = margin_top + h - (i / max_val) * h
            painter.drawText(margin_left - 30, int(y + 4), str(i))
            painter.setPen(QPen(QColor("#E2E8F0"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(margin_left, int(y), margin_left + w, int(y))
            painter.setPen(QPen(QColor("#CBD5E1"), 2))

        self.hover_rects.clear()

        for idx, p_name in enumerate(planets):
            data = self.data_dict[p_name]
            isht, kasht = data["isht"], data["kasht"]
            net = isht - kasht
            abs_net = abs(net)

            x_center = margin_left + (idx * spacing) + (spacing / 2)
            tt_html = (
                f"<div style='min-width: 220px;'>"
                f"<h3 style='margin:0; color:#0284C7;'>{p_name} Rasmi </h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                f"<b>Isht (Auspicious):</b> <span style='color:#059669;'>{isht:.2f}</span><br>"
                f"<b>Kasht (Inauspicious):</b> <span style='color:#DC2626;'>{kasht:.2f}</span><br>"
                f"<b>Net Result:</b> {abs_net:.2f} ({'Net Auspicious' if net >= 0 else 'Net Inauspicious'})"
                f"</div>"
            )
            hitbox = QRectF(x_center - bar_width*1.5 - 5, margin_top, bar_width*3 + 10, h + 30)
            self.hover_rects[p_name] = (hitbox, tt_html)

            isht_h = (isht / max_val) * h
            isht_rect = QRectF(x_center - bar_width*1.5 - 2, margin_top + h - isht_h, bar_width, isht_h)
            painter.setBrush(QBrush(QColor("#10B981")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(isht_rect, 2, 2)

            kasht_h = (kasht / max_val) * h
            kasht_rect = QRectF(x_center - bar_width/2, margin_top + h - kasht_h, bar_width, kasht_h)
            painter.setBrush(QBrush(QColor("#EF4444")))
            painter.drawRoundedRect(kasht_rect, 2, 2)

            net_h = (abs_net / max_val) * h
            net_rect = QRectF(x_center + bar_width/2 + 2, margin_top + h - net_h, bar_width, net_h)
            painter.setBrush(QBrush(QColor("#0EA5E9" if net >= 0 else "#8B5CF6")))
            painter.drawRoundedRect(net_rect, 2, 2)

            painter.setPen(QColor("#1E293B"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            painter.drawText(QRectF(x_center - 30, margin_top + h + 5, 60, 20), Qt.AlignmentFlag.AlignCenter, p_name)

            painter.setFont(QFont("Segoe UI", 7))
            painter.drawText(QRectF(isht_rect.x(), isht_rect.y() - 15, bar_width, 15), Qt.AlignmentFlag.AlignCenter, f"{isht:.0f}")
            painter.drawText(QRectF(kasht_rect.x(), kasht_rect.y() - 15, bar_width, 15), Qt.AlignmentFlag.AlignCenter, f"{kasht:.0f}")
            painter.drawText(QRectF(net_rect.x(), net_rect.y() - 15, bar_width, 15), Qt.AlignmentFlag.AlignCenter, f"{abs_net:.0f}")

        # Legend
        painter.setFont(QFont("Segoe UI", 9))
        painter.setBrush(QBrush(QColor("#10B981"))); painter.drawRect(margin_left + 10, 5, 12, 12); painter.drawText(margin_left + 25, 16, "Isht (Auspicious)")
        painter.setBrush(QBrush(QColor("#EF4444"))); painter.drawRect(margin_left + 130, 5, 12, 12); painter.drawText(margin_left + 145, 16, "Kasht (Inauspicious)")
        painter.setBrush(QBrush(QColor("#0EA5E9"))); painter.drawRect(margin_left + 270, 5, 12, 12); painter.drawText(margin_left + 285, 16, "Net (Favorable)")
        painter.setBrush(QBrush(QColor("#8B5CF6"))); painter.drawRect(margin_left + 380, 5, 12, 12); painter.drawText(margin_left + 395, 16, "Net (Unfavorable)")

class PadasVisualizer(QWidget):
    # (Remains unchanged from your original code, except added precise BPHS naming)
    def __init__(self, padas_data, upa_pad_target, parent=None):
        super().__init__(parent)
        self.padas_data = padas_data
        self.upa_pad_target = upa_pad_target
        self.setMinimumSize(850, 600)
        self.setMouseTracking(True)
        self.hover_rects = {}
        self.tooltip_label = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""QLabel { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; font-size: 13px; }""")
        self.tooltip_label.hide()

    def mouseMoveEvent(self, event):
        pos_f = QPointF(float(event.pos().x()), float(event.pos().y()))
        tt_text = ""
        for key, (rect, tt_html) in self.hover_rects.items():
            if rect.contains(pos_f):
                tt_text = tt_html
                break
        if tt_text:
            if self.tooltip_label.text() != tt_text:
                self.tooltip_label.setText(tt_text)
                self.tooltip_label.adjustSize()
            g_pos = event.globalPosition().toPoint()
            new_x, new_y = g_pos.x() + 15, g_pos.y() + 15
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): new_x = g_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): new_y = g_pos.y() - self.tooltip_label.height() - 5
            self.tooltip_label.move(new_x, new_y)
            self.tooltip_label.show()
            self.tooltip_label.raise_()
        else:
            self.tooltip_label.hide()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tooltip_label.hide()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#F8FAFC"))
        self.hover_rects.clear()

        if not self.padas_data: return

        w, h = rect.width(), rect.height()
        cell_w, cell_h = w / 4.0, h / 3.0

        # Names of the 12 Arudhas derived exactly from BPHS guidelines provided
        pad_names = {
            1: "Lagn Pad",
            2: "Dhan Pad",
            3: "Vikram (Bhratru) Pad",
            4: "Matru (Sukh) Pad",
            5: "Mantra (Putr) Pad",
            6: "Rog (Satru) Pad",
            7: "Dar (Kalatr) Pad",
            8: "Maran Pad",
            9: "Pitru Pad",
            10: "Karm Pad",
            11: "Labh Pad",
            12: "Vyaya Pad"
        }

        for bhava in range(1, 13):
            data = self.padas_data.get(bhava)
            if not data: continue

            row, col = (bhava - 1) // 4, (bhava - 1) % 4
            cx, cy = col * cell_w, row * cell_h
            is_upa_target = (bhava == self.upa_pad_target)

            card_rect = QRectF(cx + 10, cy + 10, cell_w - 20, cell_h - 20)
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.setPen(QPen(QColor("#C4B5FD" if is_upa_target else "#CBD5E1"), 2 if is_upa_target else 1))
            painter.drawRoundedRect(card_rect, 8, 8)

            header_rect = QRectF(cx + 11, cy + 11, cell_w - 22, 30)
            header_path = QPainterPath()
            header_path.addRoundedRect(header_rect, 8, 8)
            painter.setBrush(QBrush(QColor("#E9D5FF" if is_upa_target else "#E0F2FE")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(header_path)
            painter.drawRect(QRectF(cx + 11, cy + 20, cell_w - 22, 21))

            pad_name = pad_names.get(bhava, f"House {bhava} Arudha")
            display_name = f"{pad_name} (Upa Origin)" if is_upa_target else pad_name

            painter.setPen(QColor("#4C1D95" if is_upa_target else "#0C4A6E"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, display_name)

            painter.setPen(QColor("#475569"))
            painter.setFont(QFont("Segoe UI", 9))
            text_y = cy + 55
            painter.drawText(QRectF(cx+10, text_y, cell_w-20, 20), Qt.AlignmentFlag.AlignCenter, f"Lord: {data['lord']}")
            painter.drawText(QRectF(cx+10, text_y+20, cell_w-20, 20), Qt.AlignmentFlag.AlignCenter, f"Placed in: H{data['lord_house']}")

            painter.setPen(QColor("#94A3B8"))
            painter.drawText(QRectF(cx+10, text_y+40, cell_w-20, 20), Qt.AlignmentFlag.AlignCenter, f"↓ Leap: {data['dist']} steps")

            pad_val = data['pad']
            pad_rect = QRectF(cx + cell_w/2 - 40, cy + cell_h - 45, 80, 26)
            painter.setBrush(QBrush(QColor("#D1FAE5")))
            painter.setPen(QPen(QColor("#10B981"), 2))
            painter.drawRoundedRect(pad_rect, 13, 13)

            painter.setPen(QColor("#065F46"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(pad_rect, Qt.AlignmentFlag.AlignCenter, f"Pad: H{pad_val}")

            if "Rule A" in data['exception'] or "Rule B" in data['exception'] or "Rule C" in data['exception']:
                painter.setPen(QColor("#D97706"))
                painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                painter.drawText(QRectF(cx+10, cy + cell_h - 20, cell_w-20, 15), Qt.AlignmentFlag.AlignCenter, "Special rule applied")

            tt_html = (
                f"<div style='min-width: 250px;'>"
                f"<h3 style='margin:0; color:#0284C7;'>{display_name} Calculation (H{bhava})</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                f"<b>Lord:</b> {data['lord']} (in House {data['lord_house']})<br>"
                f"<b>Leap Distance:</b> {data['dist']} houses away.<br>"
                f"<b>Raw Pad:</b> House {data['raw_pad']}.<br>"
                f"<b>Special adjustment:</b> <span style='color:#D97706;'>{data['exception']}</span><br><br>"
                f"<b>Final Arudha Pad:</b> <span style='color:#059669; font-weight:bold;'>House {pad_val}</span>"
                f"</div>"
            )
            self.hover_rects[bhava] = (card_rect, tt_html)

class ArgalaVisualizer(QWidget):
    # (Remains unchanged from your original code)
    def __init__(self, argala_data, parent=None):
        super().__init__(parent)
        self.argala_data = argala_data
        self.view_mode = 0  
        self.setMinimumSize(850, 680)
        self.setMouseTracking(True)
        self.hover_rects = {}

        self.tooltip_label = QLabel(self, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.tooltip_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.tooltip_label.setStyleSheet("""QLabel { background-color: #FFFFFF; color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px; padding: 10px; font-size: 13px; }""")
        self.tooltip_label.hide()

    def set_view_mode(self, mode_index):
        self.view_mode = mode_index
        self.update()

    def get_house_net_status(self, results):
        a_wins, o_wins = 0, 0
        for r in results:
            if r['winner'] in ['argala', 'vipreet']: a_wins += 1
            elif r['winner'] == 'obstruction': o_wins += 1
        if a_wins > o_wins: return "argala"
        if o_wins > a_wins: return "obstruction"
        return "neutral"

    def mouseMoveEvent(self, event):
        pos_f = QPointF(float(event.pos().x()), float(event.pos().y()))
        tt_text = ""
        for key, (rect, tt_html) in self.hover_rects.items():
            if rect.contains(pos_f):
                tt_text = tt_html
                break

        if tt_text:
            if self.tooltip_label.text() != tt_text:
                self.tooltip_label.setText(tt_text)
                self.tooltip_label.adjustSize()
            g_pos = event.globalPosition().toPoint()
            new_x, new_y = g_pos.x() + 15, g_pos.y() + 15
            if screen := self.screen():
                sg = screen.availableGeometry()
                if new_x + self.tooltip_label.width() > sg.right(): new_x = g_pos.x() - self.tooltip_label.width() - 5
                if new_y + self.tooltip_label.height() > sg.bottom(): new_y = g_pos.y() - self.tooltip_label.height() - 5
            self.tooltip_label.move(new_x, new_y)
            self.tooltip_label.show()
            self.tooltip_label.raise_()
        else:
            self.tooltip_label.hide()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        self.tooltip_label.hide()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        painter.fillRect(rect, QColor("#F8FAFC"))
        self.hover_rects.clear()

        if not self.argala_data: return
        w, h = rect.width(), rect.height()

        if self.view_mode == 0: self.paint_grid_view(painter, w, h)
        else: self.paint_single_view(painter, w, h, self.view_mode)

    def paint_grid_view(self, painter, w, h):
        cell_w, cell_h = w / 4.0, h / 3.0
        for target_h in range(1, 13):
            results = self.argala_data.get(target_h, [])
            row, col = (target_h - 1) // 4, (target_h - 1) % 4
            cx, cy = col * cell_w, row * cell_h

            net_status = self.get_house_net_status(results)
            if net_status == "argala": border_c, border_w = QColor("#10B981"), 2
            elif net_status == "obstruction": border_c, border_w = QColor("#EF4444"), 2
            else: border_c, border_w = QColor("#CBD5E1"), 1

            cell_rect = QRectF(cx + 6, cy + 6, cell_w - 12, cell_h - 12)
            painter.setBrush(QBrush(QColor("#FFFFFF")))
            painter.setPen(QPen(border_c, border_w))
            painter.drawRoundedRect(cell_rect, 6, 6)

            header_rect = QRectF(cx + 7, cy + 7, cell_w - 14, 25)
            painter.setBrush(QBrush(QColor("#E0F2FE")))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(header_rect)

            painter.setPen(QColor("#0C4A6E"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, f"Target: House {target_h}")

            if not results:
                painter.drawText(QRectF(cx + 6, cy + 32, cell_w - 12, cell_h - 38), Qt.AlignmentFlag.AlignCenter, "No Argala")
                continue

            y_start = cy + 35
            pair_h = (cell_h - 45) / 4.0

            for i, res in enumerate(results):
                py = y_start + i * pair_h
                arg_h, ob_h = res['h_A'], res['h_V']
                a_planets = ",".join([n[:2] for n in res['names_A']]) if res['names_A'] else "-"
                v_planets = ",".join([n[:2] for n in res['names_V']]) if res['names_V'] else "-"
                winner = res['winner']

                c_a_bg, c_a_border = QColor("#F8FAFC"), QColor("#CBD5E1")
                c_v_bg, c_v_border = QColor("#F8FAFC"), QColor("#CBD5E1")
                if winner == "argala": c_a_bg, c_a_border = QColor("#D1FAE5"), QColor("#10B981")
                elif winner == "obstruction": c_v_bg, c_v_border = QColor("#FEE2E2"), QColor("#EF4444")
                elif winner == "vipreet": c_v_bg, c_v_border = QColor("#FEF08A"), QColor("#F59E0B")

                box_w = (cell_w - 30) * 0.42
                box_h = min(30, pair_h - 4)
                ax, vx = cx + 10, cx + cell_w - 10 - box_w

                painter.setBrush(QBrush(c_a_bg)); painter.setPen(QPen(c_a_border, 1))
                painter.drawRoundedRect(QRectF(ax, py + (pair_h - box_h)/2, box_w, box_h), 3, 3)
                painter.setPen(QColor("#0F172A")); painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.drawText(QRectF(ax, py + (pair_h - box_h)/2 + 2, box_w, box_h/2), Qt.AlignmentFlag.AlignCenter, f"{res['arg_dist']}th(H{arg_h})")
                painter.setFont(QFont("Segoe UI", 7)); painter.setPen(QColor("#475569"))
                painter.drawText(QRectF(ax, py + pair_h/2, box_w, box_h/2), Qt.AlignmentFlag.AlignCenter, a_planets)

                painter.setBrush(QBrush(c_v_bg)); painter.setPen(QPen(c_v_border, 1))
                painter.drawRoundedRect(QRectF(vx, py + (pair_h - box_h)/2, box_w, box_h), 3, 3)
                painter.setPen(QColor("#0F172A")); painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.drawText(QRectF(vx, py + (pair_h - box_h)/2 + 2, box_w, box_h/2), Qt.AlignmentFlag.AlignCenter, f"{res['ob_dist']}th(H{ob_h})")
                painter.setFont(QFont("Segoe UI", 7)); painter.setPen(QColor("#475569"))
                painter.drawText(QRectF(vx, py + pair_h/2, box_w, box_h/2), Qt.AlignmentFlag.AlignCenter, v_planets)

                painter.setPen(QColor("#94A3B8")); painter.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
                painter.drawText(QRectF(ax + box_w, py + (pair_h - box_h)/2, vx - (ax + box_w), box_h), Qt.AlignmentFlag.AlignCenter, "vs")

                self.hover_rects[f"{target_h}_{i}"] = (QRectF(cx + 6, py, cell_w - 12, pair_h), res['tt'])

    def paint_single_view(self, painter, w, h, target_h):
        results = self.argala_data.get(target_h, [])
        net_status = self.get_house_net_status(results)
        if net_status == "argala": border_c = QColor("#10B981")
        elif net_status == "obstruction": border_c = QColor("#EF4444")
        else: border_c = QColor("#CBD5E1")

        cont_rect = QRectF(20, 20, w - 40, h - 40)
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.setPen(QPen(border_c, 3))
        painter.drawRoundedRect(cont_rect, 8, 8)

        header_rect = QRectF(w/2 - 150, 30, 300, 40)
        painter.setBrush(QBrush(QColor("#E0F2FE")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(header_rect, 6, 6)
        painter.setPen(QColor("#0C4A6E"))
        painter.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        painter.drawText(header_rect, Qt.AlignmentFlag.AlignCenter, f"Target: House {target_h} Details")

        if not results:
            painter.drawText(cont_rect, Qt.AlignmentFlag.AlignCenter, "No Argala formations for this house.")
            return

        row_h = (h - 100) / 4.0
        box_w, box_h = 180, 70
        cx_argala, cx_virodh = w * 0.3, w * 0.7

        for i, res in enumerate(results):
            y_center = 100 + i * row_h + row_h/2
            arg_h, ob_h = res['h_A'], res['h_V']
            a_planets = ", ".join(res['names_A']) if res['names_A'] else "None"
            v_planets = ", ".join(res['names_V']) if res['names_V'] else "None"
            winner = res['winner']

            c_a_bg, c_a_border = QColor("#F8FAFC"), QColor("#CBD5E1")
            c_v_bg, c_v_border = QColor("#F8FAFC"), QColor("#CBD5E1")
            if winner == "argala": c_a_bg, c_a_border = QColor("#D1FAE5"), QColor("#10B981")
            elif winner == "obstruction": c_v_bg, c_v_border = QColor("#FEE2E2"), QColor("#EF4444")
            elif winner == "vipreet": c_v_bg, c_v_border = QColor("#FEF08A"), QColor("#F59E0B")

            rect_A = QRectF(cx_argala - box_w/2, y_center - box_h/2, box_w, box_h)
            painter.setBrush(QBrush(c_a_bg)); painter.setPen(QPen(c_a_border, 2))
            painter.drawRoundedRect(rect_A, 6, 6)
            painter.setPen(QColor("#0F172A")); painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(QRectF(rect_A.x(), rect_A.y() + 5, box_w, 20), Qt.AlignmentFlag.AlignCenter, f"{res['arg_dist']}th (H{arg_h})")
            painter.setFont(QFont("Segoe UI", 9)); painter.setPen(QColor("#475569"))
            painter.drawText(QRectF(rect_A.x(), rect_A.y() + 25, box_w, 35), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, a_planets)

            rect_V = QRectF(cx_virodh - box_w/2, y_center - box_h/2, box_w, box_h)
            painter.setBrush(QBrush(c_v_bg)); painter.setPen(QPen(c_v_border, 2))
            painter.drawRoundedRect(rect_V, 6, 6)
            painter.setPen(QColor("#0F172A")); painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            painter.drawText(QRectF(rect_V.x(), rect_V.y() + 5, box_w, 20), Qt.AlignmentFlag.AlignCenter, f"{res['ob_dist']}th (H{ob_h})")
            painter.setFont(QFont("Segoe UI", 9)); painter.setPen(QColor("#475569"))
            painter.drawText(QRectF(rect_V.x(), rect_V.y() + 25, box_w, 35), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, v_planets)

            painter.setPen(QPen(QColor("#94A3B8"), 2, Qt.PenStyle.DashLine))
            painter.drawLine(int(rect_A.right() + 10), int(y_center), int(rect_V.left() - 10), int(y_center))

            vs_rect = QRectF(w/2 - 30, y_center - 15, 60, 30)
            painter.fillRect(vs_rect, QColor("#FFFFFF"))
            painter.setPen(QColor("#334155")); painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            painter.drawText(vs_rect, Qt.AlignmentFlag.AlignCenter, "VS")

            self.hover_rects[f"single_{i}"] = (QRectF(30, y_center - box_h/2 - 10, w - 60, box_h + 20), res['tt'])


# ==========================================
# BPHS CALCULATOR ENGINE (DECOUPLED)
# ==========================================
class BPHSCalculator:
    def __init__(self, app):
        self.app = app

    def calculate_isht_kasht(self, chart_data):
        results = {}
        shadbala_results = getattr(self.app, '_shadbala_results', {})
        debilitation_points = {"Sun": 190.0, "Moon": 213.0, "Mars": 118.0, "Mercury": 345.0, "Jupiter": 275.0, "Venus": 177.0, "Saturn": 20.0}

        sun_p = next((p for p in chart_data["planets"] if p["name"] == "Sun"), None)
        moon_p = next((p for p in chart_data["planets"] if p["name"] == "Moon"), None)
        if not sun_p or not moon_p: return {}

        sun_lon = sun_p["lon"]
        moon_lon = moon_p["lon"]
        # Fallback ayanamsa if not found directly in chart mapping
        ayanamsa = chart_data.get("ayanamsa", 24.0)

        for p_name in debilitation_points.keys():
            p = next((pl for pl in chart_data["planets"] if pl["name"] == p_name), None)
            if not p: continue

            p_lon = p["lon"]
            
            # Uchch Rasmi Calculation
            # Deduct the Grah’s debilitation point from its actual position. If the sum exceeds 6 Rashis, deduct from 12 Rashis. 
            # Increased by 1 Rashi, degrees multiplied by 2.
            dist_uchha = (p_lon - debilitation_points[p_name]) % 360
            if dist_uchha > 180: dist_uchha = 360 - dist_uchha
            uchch_rasmi = (dist_uchha / 30.0) + 1.0
            
            # Chesht Rasmi Calculation
            if p_name == "Sun":
                # Add 3 Rashis to Sayan Surya (i.e. with Ayanans), which will be the Chesht Kendr for Surya.
                sayan_sun = (sun_lon + ayanamsa) % 360
                ck = (sayan_sun + 90) % 360
                if ck > 180: ck = 360 - ck
                chesht_rasmi = (ck / 30.0) + 1.0
            elif p_name == "Moon":
                # The sidereal longitude of Surya should be deducted from Candr to get Candr’s Chesht Kendr.
                ck = (moon_lon - sun_lon) % 360
                if ck > 180: ck = 360 - ck
                chesht_rasmi = (ck / 30.0) + 1.0
            else:
                # The Chesht Kendras of Grahas from Mangal to Sani have already been explained.
                # Use existing cheshta bala logic/results to derive exactly back to Rasmi for robustness.
                cb = 0.0
                if shadbala_results and p_name in shadbala_results:
                    cb = shadbala_results[p_name].get("Cheshta", 0.0)
                else:
                    if p_name in ["Mars", "Jupiter", "Saturn"]:
                        gap = abs(p_lon - sun_lon)
                        if gap > 180: gap = 360 - gap
                        gap_signs = int(gap // 30)
                        gap_degrees = gap % 30
                        arrays = {"Jupiter": [7, 5, 3, 1, 2, 2, 0], "Saturn": [6, 5, 3, 1, 2, 3, 0], "Mars": [7, 6, 4, 2, 0, 1, 0]}
                        arr = arrays[p_name]
                        cb = sum(arr[:gap_signs]) * 3 + ((0.1 * gap_degrees) * arr[gap_signs])
                    elif p_name == "Venus":
                        gap = abs(p_lon - sun_lon)
                        if gap > 180: gap = 360 - gap
                        if p.get("retro", False): cb = 60.0 - (gap / 10.0)
                        else: cb = gap if gap <= 40.0 else (2.0 * gap) - 41.0
                    elif p_name == "Mercury":
                        gap = abs(p_lon - sun_lon)
                        if gap > 180: gap = 360 - gap
                        if p.get("retro", False): cb = 60.0 - (gap / 2.0)
                        else: cb = 2.0 * gap
                # CB = CK / 3, thus CK = CB * 3. Therefore Rasmi = (CK / 30) + 1 = (CB / 10) + 1.
                chesht_rasmi = (cb / 10.0) + 1.0

            # Reduce 1 from each of Chesht Rasmi and Uchch Rasmi.
            u_val = uchch_rasmi - 1.0
            c_val = chesht_rasmi - 1.0
            
            # Then multiply the products by 10 and add together. Half of the sum will represent the Isht Phala
            ishtabala = ((u_val * 10.0) + (c_val * 10.0)) / 2.0
            kashtabala = 60.0 - ishtabala
            
            results[p_name] = {
                "uchch_rasmi": round(uchch_rasmi, 3), 
                "chesht_rasmi": round(chesht_rasmi, 3), 
                "isht": round(ishtabala, 3), 
                "kasht": round(kashtabala, 3), 
                "retro": p.get("retro", False)
            }

        return results

    def calculate_padas(self, chart_data):
        rashi_lords = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury",
                       7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}
        asc_sign_idx = chart_data["ascendant"]["sign_index"]

        padas = {}
        for bhava in range(1, 13):
            ruling_sign = ((asc_sign_idx + bhava - 1) % 12) + 1
            lord_planet_name = rashi_lords[ruling_sign]
            lord_p = next((p for p in chart_data["planets"] if p["name"] == lord_planet_name), None)

            if not lord_p:
                padas[bhava] = {"lord": lord_planet_name, "lord_house": -1, "pad": -1, "exception": "Error", "raw_pad": -1, "dist": 0}
                continue

            lord_house = lord_p["house"]
            dist = (lord_house - bhava) + 1
            if dist <= 0: dist += 12

            raw_pad = lord_house + dist - 1
            if raw_pad > 12: raw_pad -= 12

            exception_str = "None (Default rule applied)"
            final_pad = raw_pad

            if dist == 4:
                final_pad = lord_house
                exception_str = ("Rule A: Lord is exactly in 4th from house.<br>""Pad falls in the occupied house itself.")
            elif raw_pad == bhava:
                final_pad = (bhava + 9) % 12 or 12
                exception_str = ("Rule B: Pad fell in the original house.<br> Therefore, mapped to the 10th house from original.")
            elif raw_pad == (bhava + 6) % 12 or (bhava + 6 == 12 and raw_pad == 12):
                final_pad = (bhava + 3) % 12 or 12
                exception_str = ("Rule C: Pad fell in the 7th house from original. <br> Therefore, mapped to the 4th house from original.")

            padas[bhava] = {"lord": lord_planet_name, "lord_house": lord_house, "dist": dist, "raw_pad": raw_pad, "pad": final_pad, "exception": exception_str}

        is_odd = (asc_sign_idx + 1) % 2 != 0
        target_bhava = 12 if is_odd else 2
        upa_pad = padas[target_bhava]["pad"]

        return padas, target_bhava, upa_pad

    def calculate_argala(self, chart_data):
        malefics = ["Sun", "Mars", "Saturn", "Rahu", "Ketu"]
        house_occupants = {i: [] for i in range(1, 13)}
        for p in chart_data["planets"]:
            house_occupants[p["house"]].append(p)

        argala_results = {}
        for target_h in range(1, 13):
            argala_results[target_h] = []
            pairs = [(4, 10), (2, 12), (11, 3), (5, 9)]

            for arg_dist, ob_dist in pairs:
                h_A = (target_h + arg_dist - 2) % 12 + 1
                h_V = (target_h + ob_dist - 2) % 12 + 1

                planets_A = house_occupants[h_A]
                planets_V = house_occupants[h_V]

                if not planets_A and not planets_V: continue

                names_A = [p["name"] for p in planets_A]
                names_V = [p["name"] for p in planets_V]
                count_A, count_V = len(planets_A), len(planets_V)

                if arg_dist == 11 and ob_dist == 3:
                    malefic_count_3rd = sum(1 for p in planets_V if p["name"] in malefics)
                    if malefic_count_3rd >= 3:
                        argala_results[target_h].append({
                            "arg_dist": arg_dist, "ob_dist": ob_dist, "h_A": h_A, "h_V": h_V, "names_A": names_A, "names_V": names_V, "winner": "vipreet",
                            "tt": f"<h3 style='margin:0; color:#0284C7;'>Vipreet Argala Initiated!</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>More than 3 malefics placed in the 3rd house nullify the obstruction and create a uniquely favorable intervention instead."
                        })
                        continue

                outcome, tt_outcome = "none", ""
                if count_A > count_V:
                    outcome = "argala"
                    tt_outcome = f"More planets ({count_A}) causing Argala from H{h_A} than obstructing from H{h_V} ({count_V})."
                elif count_V > count_A:
                    outcome = "obstruction"
                    tt_outcome = f"More planets ({count_V}) causing Obstruction from H{h_V} than intervening from H{h_A} ({count_A})."
                elif count_A == 0 and count_V == 0:
                    outcome = "none"
                    tt_outcome = "No planets involved."
                else:
                    p_A, p_V = planets_A[0], planets_V[0]
                    def get_quarter(deg): return int(deg // 7.5) + 1
                    q_A, q_V = get_quarter(p_A["deg_in_sign"]), get_quarter(p_V["deg_in_sign"])

                    if (q_A == 1 and q_V == 4) or (q_A == 2 and q_V == 3) or (q_A == 3 and q_V == 2) or (q_A == 4 and q_V == 1):
                        outcome = "obstruction"
                        tt_outcome = f"Tie-breaker: Exact quarter match (Q{q_A} vs Q{q_V}) means Obstruction rules over Argala."
                    else:
                        outcome = "argala"
                        tt_outcome = f"Tie-breaker: Quarter mismatch (Q{q_A} vs Q{q_V}) means Argala rules over Obstruction."

                if outcome != "none" or names_A or names_V:
                    status_text = "Argala Wins" if outcome == "argala" else "Obstruction Wins" if outcome == "obstruction" else "Neutral"
                    argala_results[target_h].append({
                        "arg_dist": arg_dist, "ob_dist": ob_dist, "h_A": h_A, "h_V": h_V, "names_A": names_A, "names_V": names_V, "winner": outcome,
                        "tt": f"<div style='min-width: 250px;'><h3 style='margin:0; color:#0284C7;'>Argala vs Obstruction Resoluton</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>House {h_A} ({arg_dist}th) vs House {h_V} ({ob_dist}th)<br><b>Result:</b> <span style='color:#059669;'>{status_text}</span><br><b>Reason:</b> {tt_outcome}</div>"
                    })
        return argala_results

    def calculate_all(self):
        chart_data = getattr(self.app, 'current_base_chart', None)
        if not chart_data or "planets" not in chart_data:
            return None

        padas_data, upa_target, upa_pad = self.calculate_padas(chart_data)
        
        return {
            "isht": self.calculate_isht_kasht(chart_data),
            "padas": padas_data,
            "upa_target": upa_target,
            "upa_pad": upa_pad,
            "argala": self.calculate_argala(chart_data)
        }


# ==========================================
# MAIN DIALOG FOR BPHS ADVANCED ALGORITHMS
# ==========================================
class BPHSAdvancedDialog(QDialog):
    def __init__(self, app_instance, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window)
        self.app = app_instance
        self.setWindowTitle("Isht/Kansht Balas, Padas and Argala analysis")
        self.resize(1000, 800)
        self.scrollers = []

        self.setStyleSheet("""
            QDialog { background-color: #F8FAFC; }
            QTabWidget::pane { border: 1px solid #CBD5E1; background: #FFFFFF; border-radius: 4px; }
            QTabBar::tab { background: #E2E8F0; padding: 10px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; color: #4F46E5; border-bottom: 2px solid #4F46E5; }
            QTableWidget { background: #FFFFFF; alternate-background-color: #F8FAFC; border: 1px solid #CBD5E1; }
            QHeaderView::section { background-color: #E2E8F0; font-weight: bold; padding: 6px; border: 1px solid #CBD5E1; }
            QScrollArea { background-color: transparent; }
        """)

        self.main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        self.tab_isht = QWidget()
        self.tab_padas = QWidget()
        self.tab_argala = QWidget()
        
        self.tab_isht_layout = QVBoxLayout(self.tab_isht)
        self.tab_padas_layout = QVBoxLayout(self.tab_padas)
        self.tab_argala_layout = QVBoxLayout(self.tab_argala)

        self.tabs.addTab(self.tab_isht, "1. Isht and Kasht Balas")
        self.tabs.addTab(self.tabs_padas if hasattr(self, 'tabs_padas') else self.tab_padas, "2. Bhava and Upa Padas")
        self.tabs.addTab(self.tab_argala, "3. Argala Analysis")

        self.main_layout.addWidget(self.tabs)

    def apply_smooth_scroll(self, widget):
        if SmoothScroller:
            scroller = SmoothScroller(widget)
            self.scrollers.append(scroller)

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                elif item.layout() is not None:
                    self._clear_layout(item.layout())

    def refresh_data(self, results):
        if not results:
            return
            
        self.scrollers.clear()
        
        self.isht_data = results.get("isht", {})
        self.padas_data = results.get("padas", {})
        self.upa_pad_target = results.get("upa_target")
        self.upa_pad = results.get("upa_pad")
        self.argala_data = results.get("argala", {})

        self.build_isht_tab()
        self.build_padas_tab()
        self.build_argala_tab()

    def build_isht_tab(self):
        self._clear_layout(self.tab_isht_layout)
        layout = self.tab_isht_layout

        info_lbl = QLabel("<span style='color: #059669;'><b>Isht and Kasht Tendencies -- Reduce 1 from each of Chesht Rasmi and Uchch Rasmi. Then multiply the products by 10 and add together. Half of the sum will represent the Isht Phala (benefic tendency) of the Grah.<br> Reduce Isht Phala from 60 to obtain the Grah’s Kasht Phala (malefic tendency)</b></span>")
        info_lbl.setStyleSheet("color: #334155; font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(info_lbl)

        table = CustomTooltipTable()
        self.apply_smooth_scroll(table)
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Planet", "Uchch Rasmi", "Chesht Rasmi", "Isht Phala", "Kasht Phala"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        if self.isht_data:
            table.setRowCount(len(self.isht_data))
            for row, (p_name, vals) in enumerate(self.isht_data.items()):
                p_item = QTableWidgetItem(p_name)
                
                u_item = QTableWidgetItem(f"{vals['uchch_rasmi']:.3f}")
                u_item.setData(Qt.ItemDataRole.UserRole, (
                    f"<div style='min-width: 250px;'>"
                    f"<h3 style='margin:0; color:#0284C7;'>Uchch Rasmi (Exaltation Ray)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                    f"<b>Formula:</b> <code style='color:#D97706;'>(Dist. from Debilitation / 30) + 1</code><br>"
                    f"<b>Meaning:</b> How close a planet is to its point of maximum exaltation.<br>"
                    f"<b>Value:</b> {vals['uchch_rasmi']:.3f} Rasmis."
                    f"</div>"
                ))

                retro_status = "<span style='color:#DC2626;'>Yes</span>" if vals.get("retro") else "<span style='color:#059669;'>No</span>"
                c_item = QTableWidgetItem(f"{vals['chesht_rasmi']:.3f}")
                c_item.setData(Qt.ItemDataRole.UserRole, (
                    f"<div style='min-width: 250px;'>"
                    f"<h3 style='margin:0; color:#0284C7;'>Chesht Rasmi (Motional Ray)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                    f"<b>Retrograde:</b> {retro_status}<br>"
                    f"<b>Formula:</b> <code style='color:#D97706;'>(Cheshta Kendra / 30) + 1</code><br>"
                    f"<b>Meaning:</b>How dynamically active a planet is.<br>"
                    f"<b>Value:</b> {vals['chesht_rasmi']:.3f} Rasmis."
                    f"</div>"
                ))

                i_item = QTableWidgetItem(f"{vals['isht']:.3f}")
                i_item.setData(Qt.ItemDataRole.UserRole, (
                    f"<div style='min-width: 250px;'>"
                    f"<h3 style='margin:0; color:#059669;'>Isht Phala (Auspicious Tendency)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                    f"<b>Meaning:</b> Favorable effects yielded during Dasha/Antardasha.<br>"
                    f"<b>Formula:</b> <code style='color:#D97706;'>(((Uchch R. - 1)*10) + ((Chesht R. - 1)*10)) / 2</code><br>"
                    f"<b>Math:</b> ((({vals['uchch_rasmi']:.3f} - 1) * 10) + (({vals['chesht_rasmi']:.3f} - 1) * 10)) / 2 = {vals['isht']:.2f}"
                    f"</div>"
                ))
                i_item.setBackground(QColor("#D1FAE5")); i_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

                k_item = QTableWidgetItem(f"{vals['kasht']:.3f}")
                k_item.setData(Qt.ItemDataRole.UserRole, (
                    f"<div style='min-width: 250px;'>"
                    f"<h3 style='margin:0; color:#DC2626;'>Kasht Phala (Inauspicious Tendency)</h3><hr style='border-top: 1px solid #CBD5E1; margin: 6px 0;'>"
                    f"<b>Meaning:</b> Difficult effects yielded during Dasha/Antardasha.<br>"
                    f"<b>Formula:</b> <code style='color:#D97706;'>60 - Isht Phala</code><br>"
                    f"<b>Math:</b> 60 - {vals['isht']:.2f} = {vals['kasht']:.2f}"
                    f"</div>"
                ))
                k_item.setBackground(QColor("#FEE2E2")); k_item.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))

                table.setItem(row, 0, p_item); table.setItem(row, 1, u_item)
                table.setItem(row, 2, c_item); table.setItem(row, 3, i_item); table.setItem(row, 4, k_item)

        scroll_chart = QScrollArea()
        scroll_chart.setWidgetResizable(True)
        scroll_chart.setFrameShape(QScrollArea.Shape.NoFrame)
        chart_widget = IshtKashtBarChart(self.isht_data)
        scroll_chart.setWidget(chart_widget)

        layout.addWidget(QLabel("<b>Isht and Kasht Balas (Auspicious vs Inauspicious Tendencies)</b>"))
        layout.addWidget(table)
        layout.addWidget(scroll_chart)

    def build_padas_tab(self):
        self._clear_layout(self.tab_padas_layout)
        layout = self.tab_padas_layout
        
        info_lbl = QLabel("<span style='color: #059669;'><b>Upapada represents how the marriage actually materializes in reality</b></span><br>If Upa Pad is yuti with, or receives a Drishti from a benefic Grah, one will obtain full happiness from progeny and spouse. ")
        info_lbl.setStyleSheet("color: #334155; font-size: 13px; margin-bottom: 8px;")
        layout.addWidget(info_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.apply_smooth_scroll(scroll)

        if hasattr(self, 'padas_data'):
            self.padas_visualizer = PadasVisualizer(self.padas_data, getattr(self, 'upa_pad_target', None))
            scroll.setWidget(self.padas_visualizer)

        layout.addWidget(scroll)

        upa_html = (
            f"<div style='background-color:#EDE9FE; padding: 5px; border-radius: 10px; border: 1px solid #C4B5FD; margin-top: 1px;'>"
            f"<h6 style='color:#7C3AED; margin: 0;'>Upa Pad (Gaun Pad) Evaluation: House {getattr(self, 'upa_pad', 'N/A')}</h6>"
            f"<p style='margin: 4px 0 0 0;'>Calculated using the Pad of the 12th House (for Odd Ascendants) or 2nd House (for Even Ascendants).</p>"
            f"</div>"
        )
        layout.addWidget(QLabel(upa_html))

    def build_argala_tab(self):
        self._clear_layout(self.tab_argala_layout)
        layout = self.tab_argala_layout

        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("<b>Select View Mode:</b>"))
        cb_houses = QComboBox()
        cb_houses.addItem("Bird's Eye View (All 12 Houses Grid)")
        cb_houses.addItems([f"House {i} Details" for i in range(1, 13)])
        cb_houses.setStyleSheet("padding: 4px; font-weight: bold; font-size: 13px;")
        control_layout.addWidget(cb_houses)
        control_layout.addStretch()
        layout.addLayout(control_layout)
    
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.apply_smooth_scroll(scroll)

        if hasattr(self, 'argala_data'):
            self.argala_visualizer = ArgalaVisualizer(self.argala_data)
            cb_houses.currentIndexChanged.connect(self.argala_visualizer.set_view_mode)
            scroll.setWidget(self.argala_visualizer)

        layout.addWidget(scroll)

        desc_lbl = QLabel(
            "<b>Explanation:</b> Planets in 2nd, 4th, 11th and 5th (secondary algara)  from an Argala (a force that modifies or interferes with the results of a house or planet). "
            "Planets in the 12th, 10th, 3rd, and 9th respectively cause Obstruction (Virodh argala). "
            "<i>The Argala, which is unobstructed will be fruitful, while the one duly obstructed will go astray.</i>"
        )
        desc_lbl.setStyleSheet("font-size: 13px; color: #475569; margin-top: 10px;")
        desc_lbl.setWordWrap(True)
        layout.addWidget(desc_lbl)


# ==========================================
# PLUGIN ENTRY POINT
# ==========================================
import __main__
from PyQt6.QtWidgets import QGroupBox, QVBoxLayout, QPushButton, QLabel, QFrame
from PyQt6.QtCore import QTimer

info_print = getattr(__main__, 'info_print', print)
debug_print = getattr(__main__, 'debug_print', print)
error_print = getattr(__main__, 'error_print', print)
def setup_ui(app, layout):
    shared_group_id = "AdvancedAstroGroup"
    
    # DYNAMIC LAYOUT LOOKUP
    shared_group = None
    for i in range(layout.count()):
        w = layout.itemAt(i).widget()
        if w and w.objectName() == shared_group_id:
            shared_group = w
            break
    
    if not shared_group:
        shared_group = QGroupBox("Strength Analysis")
        shared_group.setObjectName(shared_group_id)
        
        group_layout = QVBoxLayout()
        group_layout.setContentsMargins(6, 6, 6, 6)
        group_layout.setSpacing(6)
        shared_group.setLayout(group_layout)
        
        layout.addWidget(shared_group)
        
    target_layout = shared_group.layout()

    from PyQt6.QtWidgets import QFrame # Ensure QFrame is imported here if it wasn't
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #dcdde1; margin-top: 4px; margin-bottom: 4px;")
    target_layout.addWidget(line)

    lbl_title = QLabel("Isht/Kanshta, Bhava, Argala")
    lbl_title.setStyleSheet("color: #4F46E5; font-weight: bold; font-size: 15px; margin-top: 4px;")
    target_layout.addWidget(lbl_title)
    
    # ... (Keep the rest of the setup_ui function exactly as it is) ...
    
    lbl_name = "bphs_summary_lbl_active"
    btn_name = "bphs_btn_details_active"
    
    summary_lbl = QLabel("<i>Calculating metrics...</i>")
    summary_lbl.setObjectName(lbl_name)
    summary_lbl.setStyleSheet("background-color: #fdfefe; border: 1px solid #dcdde1; border-radius: 4px; padding: 6px; font-family: monospace;")
    summary_lbl.setWordWrap(True)
    target_layout.addWidget(summary_lbl)

    btn_details = QPushButton("Strength analysis II")
    btn_details.setObjectName(btn_name)
    btn_details.setStyleSheet("""
        QPushButton { background-color: #34495e; color: white; font-weight: bold; padding: 6px 12px; border-radius: 4px; }
        QPushButton:hover { background-color: #4338CA; }
        QPushButton:disabled { background-color: #bdc3c7; color: #7f8c8d; }
    """)
    btn_details.setEnabled(False)
    target_layout.addWidget(btn_details)

    app._bphs_results = {}
    
    current_ui_id = id(summary_lbl)
    app._bphs_active_ui_id = current_ui_id
    
    # 1. CREATE THE HEARTBEAT TIMER
    retry_timer = QTimer()
    retry_timer.setSingleShot(True)
    app._bphs_retry_timer = retry_timer

    def run_computation():
        if getattr(app, '_bphs_active_ui_id', None) != current_ui_id:
            return

        # 2. DYNAMIC C++ LIFETIME CHECK
        current_shared_group = app.findChild(QGroupBox, shared_group_id)
        if not current_shared_group:
            error_print("Layout not mounted yet. Retrying in 1s...")
            retry_timer.start(1000)
            return
        
        active_lbl = current_shared_group.findChild(QLabel, lbl_name)
        active_btn = current_shared_group.findChild(QPushButton, btn_name)
        
        if not active_lbl or not active_btn:
            error_print("labels missing from tree. Retrying in 1s...")
            retry_timer.start(1000)
            return

        # 3. ENGINE LIFETIME CHECK
        if not hasattr(app, 'current_base_chart') or not app.current_base_chart or not app.current_base_chart.get("planets"):
            active_lbl.setText("<i>Waiting for astrological engine to spin up...</i>")
            retry_timer.start(1000) 
            return

        calculator = BPHSCalculator(app)
        results = calculator.calculate_all()
        
        if not results:
            active_lbl.setText("<i>Calculation yielded empty data, recalculating...</i>")
            error_print("Calculation yielded empty data. Retrying in 1s...")
            retry_timer.start(1000)
            return

        app._bphs_results = results
        
        isht_data = results.get("isht")
        upa_pad = results.get("upa_pad")
        
        if isht_data:
            top_isht = max(isht_data.items(), key=lambda x: x[1]['isht'])
            top_kasht = max(isht_data.items(), key=lambda x: x[1]['kasht'])
            
            summary_txt = (
                f"<b>Upa Pad Origin:</b> House {upa_pad}<br>"
                f"<b>Highest Isht:</b> {top_isht[0]} ({top_isht[1]['isht']:.1f}) 🟢<br>"
                f"<b>Highest Kasht:</b> {top_kasht[0]} ({top_kasht[1]['kasht']:.1f}) ⚠️"
            )
        else:
            summary_txt = "No valid data calculated."
            error_print("Failed to render chart! isht_data was empty.")
            
        active_lbl.setText(summary_txt)
        active_btn.setEnabled(True)
        
        if hasattr(app, '_bphs_dialog') and getattr(app._bphs_dialog, 'isVisible', lambda: False)():
            app._bphs_dialog.refresh_data(results)

    retry_timer.timeout.connect(run_computation)

    def auto_trigger(*args, **kwargs):
        if getattr(app, '_bphs_active_ui_id', None) == current_ui_id:
            retry_timer.start(0)

    if hasattr(app, 'calc_worker'):
        app.calc_worker.calc_finished.connect(auto_trigger)

    def show_details():
        if hasattr(app, '_bphs_results') and app._bphs_results:
            if not hasattr(app, '_bphs_dialog'):
                app._bphs_dialog = BPHSAdvancedDialog(app, app)
            app._bphs_dialog.refresh_data(app._bphs_results)
            app._bphs_dialog.showMaximized()  
            app._bphs_dialog.raise_()

    btn_details.clicked.connect(show_details)
    auto_trigger()