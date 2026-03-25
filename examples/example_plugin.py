import json
from PyQt6.QtWidgets import QPushButton, QMessageBox
from PyQt6.QtCore import Qt

def setup_ui(app, layout):
    """
    Contract Method: 'app' is the AstroApp instance from main.py
    'layout' is the layout instance inside the Dynamic Modules GroupBox.
    """
    
    # 1. Create your UI Elements
    btn = QPushButton("🪐 View Chart Lords (D1 & D9)")
    btn.setStyleSheet("""
        QPushButton {
            background-color: #8e44ad; 
            color: white; 
            font-weight: bold; 
            padding: 8px; 
            border-radius: 4px;
        }
        QPushButton:hover { background-color: #9b59b6; }
    """)
    
    # 2. Define the behavior when interacted with
    def on_click():
        # Cleanly pull data from the main application via API
        loc = app.get_current_location()
        dt = app.get_current_datetime()
        d1_chart = app.get_chart_data("D1")
        d9_chart = app.get_chart_data("D9")
        
        # Ensure charts are actually calculated before showing info
        if not d1_chart or not d9_chart:
            QMessageBox.warning(app, "Not Ready", "Please wait for chart data to calculate.")
            return
        
        # Construct the display string
        info = f"<b>Location:</b> {loc['name']} (Lat: {loc['lat']:.2f}, Lon: {loc['lon']:.2f})<br>"
        info += f"<b>Date:</b> {dt['day']}/{dt['month']}/{dt['year']} {dt['hour']}:{dt['minute']:02d}<br><br>"
        
        # Parse D1 Lords
        info += "<b>--- D1 (Rashi) Chart Lords ---</b><br>"
        for p in d1_chart["planets"]:
            if p.get("lord_of"):
                rules_str = ", ".join(map(str, p['lord_of']))
                info += f"&bull; <b>{p['name']}</b> (Rules House(s) {rules_str}) is in <b>House {p['house']}</b><br>"
                
        info += "<br><b>--- D9 (Navamsha) Chart Lords ---</b><br>"
        for p in d9_chart["planets"]:
            if p.get("lord_of"):
                rules_str = ", ".join(map(str, p['lord_of']))
                info += f"&bull; <b>{p['name']}</b> (Rules House(s) {rules_str}) is in <b>House {p['house']}</b><br>"
                
        # Show results to user
        msg = QMessageBox(app)
        msg.setWindowTitle("Chart Lords Data API Demo")
        msg.setTextFormat(Qt.TextFormat.RichText) # Fix: PyQt6 strictly requires the Qt.TextFormat enum
        msg.setText(info)
        msg.exec()
        
    # 3. Connect behavior and add to layout
    btn.clicked.connect(on_click)
    layout.addWidget(btn)