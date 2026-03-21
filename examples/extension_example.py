# dynamic_settings_modules/shadbala_mod.py
import math
from PyQt6.QtWidgets import (QPushButton, QMessageBox, QLabel, QVBoxLayout, QHBoxLayout, QDialog, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar, QWidget)
from PyQt6.QtCore import Qt, QTimer

# Import the core engine safely to access global astronomical dictionaries
import astro_engine

class ShadbalaDetailsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Comprehensive Shadbala Analysis (6-Fold Strength)")
        self.resize(1050, 450)
        self.setStyleSheet("QTableWidget { font-size: 13px; } QHeaderView::section { font-weight: bold; background-color: #f3f4f6; padding: 4px; }")
        
        layout = QVBoxLayout(self)
        
        # Info Header
        info_lbl = QLabel(
            "<b>Shastiamsa Scale (0–60 per category). Max Total = 360. Threshold for Strong = 180.</b><br>"
            "<i>Includes Sthana (Position), Dig (Direction), Kala (Time), Cheshta (Motion), Naisargika (Natural), and Drik (Aspect).</i><br>"
            "<span style='color: #27ae60;'><b>Auto-updates in real-time as you change the time or animate the chart!</b></span>"
        )
        info_lbl.setStyleSheet("color: #2c3e50; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(info_lbl)
        
        # Details Table
        self.table = QTableWidget()
        cols = ["Planet", "Sthana Bala", "Dig Bala", "Kala Bala", "Cheshta Bala", "Naisargika", "Drik Bala", "TOTAL SCORE", "Status"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        # Close Button
        btn_close = QPushButton("Close Detailed Analysis")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def refresh_data(self, shadbala_data):
        self.table.setRowCount(0)
        self.table.setRowCount(len(shadbala_data))
        
        # Sort data by total score descending
        sorted_data = sorted(shadbala_data.items(), key=lambda x: x[1]['Total'], reverse=True)
        
        for row, (p_name, scores) in enumerate(sorted_data):
            # Planet Name
            p_item = QTableWidgetItem(f"{p_name} {astro_engine.SIGN_RULERS.get(scores.get('sign', 1), '')}")
            p_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, p_item)
            
            # Sub-components (Max 60)
            categories = ["Sthana", "Dig", "Kala", "Cheshta", "Naisargika", "Drik"]
            for col, cat in enumerate(categories, start=1):
                val = scores[cat]
                bar = QProgressBar()
                bar.setMaximum(60)
                bar.setValue(int(val))
                bar.setFormat(f"{val:.1f} / 60")
                bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
                
                color = "#27ae60" if val >= 30 else ("#f1c40f" if val >= 15 else "#c0392b")
                bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {color}; border-radius: 2px; }} QProgressBar {{ border: 1px solid #bdc3c7; border-radius: 2px; text-align: center; font-weight: bold; color: black; }}")
                self.table.setCellWidget(row, col, bar)
                
            # Total Score (Max 360)
            total = scores["Total"]
            tot_bar = QProgressBar()
            tot_bar.setMaximum(360)
            tot_bar.setValue(int(total))
            tot_bar.setFormat(f"{total:.1f} / 360")
            tot_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tot_color = "#2980b9" if total >= 180 else "#c0392b"
            tot_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {tot_color}; border-radius: 2px; }} QProgressBar {{ border: 1px solid #bdc3c7; border-radius: 2px; text-align: center; font-weight: bold; color: black; }}")
            self.table.setCellWidget(row, 7, tot_bar)
            
            # Status (Fixed: Using QLabel instead of QTableWidgetItem for styling)
            status_text = "STRONG 🟢" if total >= 180 else "WEAK 🔴"
            status_lbl = QLabel(status_text)
            status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_lbl.setStyleSheet(f"font-weight: bold; color: {'#27ae60' if total >= 180 else '#c0392b'};")
            self.table.setCellWidget(row, 8, status_lbl)

def setup_ui(app, layout):
    """
    Called dynamically by the main app. Attaches the Shadbala widget to the layout.
    """
    
    # Header
    lbl_title = QLabel("🔱 Shadbala (6-Fold Strength)")
    lbl_title.setStyleSheet("color: #8e44ad; font-weight: bold; font-size: 15px; margin-top: 8px;")
    layout.addWidget(lbl_title)
    
    # Leaderboard Label
    leaderboard_lbl = QLabel("<i>Calculating initial rankings...</i>")
    leaderboard_lbl.setStyleSheet("background-color: #fdfefe; border: 1px solid #dcdde1; border-radius: 4px; padding: 6px; font-family: monospace;")
    leaderboard_lbl.setWordWrap(True)
    layout.addWidget(leaderboard_lbl)
    
    # Action Buttons
    btn_layout = QHBoxLayout()
    
    btn_details = QPushButton("📊 View Live Detail Charts")
    btn_details.setStyleSheet("background-color: #34495e; color: white; font-weight: bold;")
    btn_details.setEnabled(False)
    
    btn_layout.addWidget(btn_details)
    layout.addLayout(btn_layout)
    
    # Storage for computation results
    app._shadbala_results = {}
    
    def run_computation():
        if not hasattr(app, 'current_base_chart') or not app.current_base_chart:
            leaderboard_lbl.setText("<i>Waiting for chart data...</i>")
            return
            
        try:
            results = {}
            base_chart = app.current_base_chart
            valid_planets = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
            
            # 0. Preparation (Generate required vargas for Saptavargaja)
            required_vargas = ["D1", "D2", "D3", "D7", "D9", "D12", "D30"]
            varga_charts = {"D1": base_chart}
            for v in required_vargas[1:]:
                varga_charts[v] = app.ephemeris.compute_divisional_chart(base_chart, v)
                
            panchang = base_chart.get("panchang", {})
            sun_jd = panchang.get("sunrise_jd") or 0
            set_jd = panchang.get("sunset_jd") or 0
            cur_jd = base_chart.get("current_jd") or 0
            is_daytime = (sun_jd <= cur_jd < set_jd) if sun_jd and set_jd else True

            for p_name in valid_planets:
                p_data = next((p for p in base_chart["planets"] if p["name"] == p_name), None)
                if not p_data: continue
                
                # --- 1 & 2. STHANA BALA (Positional) ---
                # 2.1 Uchcha Bala
                deb_sign = astro_engine.DEBILITATION_RULES.get(p_name, 1)
                deb_lon = (deb_sign - 1) * 30 + 15.0 # Approximate center of debilitation sign
                dist = abs(p_data["lon"] - deb_lon)
                if dist > 180: dist = 360 - dist
                uchcha = (dist / 180.0) * 60.0
                
                # 2.2 Saptavargaja Bala
                sapta_sum = 0
                for v in required_vargas:
                    pv = next((x for x in varga_charts[v]["planets"] if x["name"] == p_name), None)
                    if pv:
                        if pv.get("exalted"): sapta_sum += 60
                        elif pv.get("own_sign"): sapta_sum += 45
                        elif pv.get("debilitated"): sapta_sum += 0
                        else: sapta_sum += 20 # Average placeholder for friends/neutral
                sapta = sapta_sum / 7.0
                
                # 2.3 Ojhayugma Bala
                is_male = p_name in ["Sun", "Mars", "Jupiter"]
                is_female = p_name in ["Moon", "Venus"]
                is_odd_sign = p_data["sign_num"] % 2 != 0
                ojha = 60 if (is_male and is_odd_sign) or (is_female and not is_odd_sign) else (30 if not is_male and not is_female else 0)
                
                # 2.4 Kendradi Bala
                h = p_data["house"]
                kendradi = 60 if h in [1,4,7,10] else (30 if h in [2,5,8,11] else 15)
                
                # 2.5 Drekkana Bala
                deg = p_data["deg_in_sign"]
                drek = 1 if deg <= 10 else (2 if deg <= 20 else 3)
                drekkana = 0
                if is_male and drek == 1: drekkana = 60
                elif not is_male and not is_female and drek == 2: drekkana = 60
                elif is_female and drek == 3: drekkana = 60
                
                # Sthana Bala Component (Normalized to 60)
                sthana_bala = (uchcha + sapta + ojha + kendradi + drekkana) / 5.0
                
                # --- 3. DIG BALA (Directional) ---
                strongest_house = {"Sun": 10, "Mars": 10, "Jupiter": 1, "Mercury": 1, "Moon": 4, "Venus": 4, "Saturn": 7}.get(p_name, 1)
                weakest_house = (strongest_house + 6 - 1) % 12 + 1
                
                # Calculate distance in terms of houses (max distance is 6 houses = 180 deg)
                h_dist = abs(p_data["house"] - weakest_house)
                if h_dist > 6: h_dist = 12 - h_dist
                dig_bala = (h_dist / 6.0) * 60.0
                
                # --- 4. KALA BALA (Temporal) ---
                # 4.1 Natonnata Bala
                if p_name in ["Sun", "Jupiter", "Venus"]: natonnata = 60 if is_daytime else 0
                elif p_name in ["Moon", "Mars", "Saturn"]: natonnata = 0 if is_daytime else 60
                else: natonnata = 60 # Mercury strong always
                
                # 4.2 Paksha Bala
                moon_lon = panchang.get("moon_lon", 0)
                sun_lon = panchang.get("sun_lon", 0)
                phase_angle = abs(moon_lon - sun_lon)
                if phase_angle > 180: phase_angle = 360 - phase_angle
                
                is_benefic = p_name in ["Moon", "Jupiter", "Venus", "Mercury"]
                paksha = (phase_angle / 180.0 * 60.0) if is_benefic else ((180 - phase_angle) / 180.0 * 60.0)
                
                # Standardizing other Kala components to averages for strict engine bounding
                kala_bala = (natonnata + paksha + 30 + 30 + 30) / 5.0 
                
                # --- 5. CHESHTA BALA (Motional) ---
                if p_data.get("retro"): cheshta_bala = 60.0
                elif p_data.get("combust"): cheshta_bala = 5.0
                else: cheshta_bala = 30.0 # Standard mean motion
                
                # --- 6. NAISARGIKA BALA (Natural) ---
                naisargika_bala = {"Sun": 60, "Moon": 51, "Venus": 43, "Jupiter": 34, "Mercury": 26, "Mars": 17, "Saturn": 9}.get(p_name, 0)
                
                # --- 7. DRIK BALA (Aspectual) ---
                drik_base = 30.0 # Baseline shifting so negative malefic aspects don't break UI constraints
                for asp in base_chart.get("aspects", []):
                    if asp["target_house"] == p_data["house"]:
                        if asp["aspecting_planet"] in ["Jupiter", "Venus", "Moon", "Mercury"]:
                            drik_base += 15
                        else:
                            drik_base -= 15
                drik_bala = max(0.0, min(60.0, drik_base))
                
                # --- 8 & 9. FINAL SUM & ASSIGNMENT ---
                total_shadbala = sthana_bala + dig_bala + kala_bala + cheshta_bala + naisargika_bala + drik_bala
                
                results[p_name] = {
                    "Sthana": sthana_bala, "Dig": dig_bala, "Kala": kala_bala, 
                    "Cheshta": cheshta_bala, "Naisargika": naisargika_bala, "Drik": drik_bala,
                    "Total": total_shadbala
                }

            # Save and Update UI
            app._shadbala_results = results
            
            # Format leaderboard text
            sorted_planets = sorted(results.items(), key=lambda x: x[1]['Total'], reverse=True)
            leader_txt = "<b>Live Strength Rankings:</b><br>"
            for i, (p, data) in enumerate(sorted_planets, start=1):
                icon = "🟢" if data['Total'] >= 180 else "🔴"
                leader_txt += f"{i}. <b>{p}</b> - {data['Total']:.1f}/360 {icon}<br>"
                
            leaderboard_lbl.setText(leader_txt)
            btn_details.setEnabled(True)
            
            # Live-update the dialog if it is currently open!
            if hasattr(app, '_shadbala_dialog') and app._shadbala_dialog.isVisible():
                app._shadbala_dialog.refresh_data(results)
            
        except Exception as e:
            leaderboard_lbl.setText(f"<i style='color:red;'>Error computing: {e}</i>")

    def auto_trigger(*args, **kwargs):
        # QTimer singleShot ensures we execute safely on the main thread right after base chart updates
        QTimer.singleShot(0, run_computation)

    # Clean up previous hooks if this module is hot-reloaded
    if hasattr(app, '_shadbala_auto_hook'):
        try: app.calc_worker.calc_finished.disconnect(app._shadbala_auto_hook)
        except Exception: pass
        
    # Hook the computation directly into the background calculation engine
    app._shadbala_auto_hook = auto_trigger
    app.calc_worker.calc_finished.connect(app._shadbala_auto_hook)

    def show_details():
        if hasattr(app, '_shadbala_results') and app._shadbala_results:
            # Check if dialog exists, if not create it
            if not hasattr(app, '_shadbala_dialog'):
                app._shadbala_dialog = ShadbalaDetailsDialog(app)
                
            # Bring it to front and update data (Using .show() makes it non-blocking!)
            app._shadbala_dialog.refresh_data(app._shadbala_results)
            app._shadbala_dialog.show()
            app._shadbala_dialog.raise_()
            app._shadbala_dialog.activateWindow()

    btn_details.clicked.connect(show_details)
    
    # Run an initial trigger to populate instantly when loaded
    auto_trigger()