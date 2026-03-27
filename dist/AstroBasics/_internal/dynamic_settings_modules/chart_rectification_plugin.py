# dynamic_settings_modules/chart_rectification_plugin.py

import sys, os, json, datetime, queue, threading
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,QDialog, QGridLayout, QComboBox, QSpinBox, QCheckBox,QMessageBox, QFileDialog, QInputDialog,QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from astro_engine import swe_lock, get_resource_path

# Determine the base directory of the main application
if getattr(sys, 'frozen', False) or '__compiled__' in globals():
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

import swisseph as swe, astro_engine
import rectification_engine
from timezonefinder import TimezoneFinder
from main import ChartRenderer  # Safely inject the renderer

PLUGIN_GROUP = "CHART RECTIFICATION"
PLUGIN_INDEX = 2

class NoScrollComboBox(QComboBox):
    def wheelEvent(self, event): event.ignore()

def plugin_get_dignities(p_name, sign_num, deg_in_sign):
    EXALTATION_RULES = {"Sun": 1, "Moon": 2, "Mars": 10, "Mercury": 6, "Jupiter": 4, "Venus": 12, "Saturn": 7, "Rahu": 2, "Ketu": 8}
    DEBILITATION_RULES = {"Sun": 7, "Moon": 8, "Mars": 4, "Mercury": 12, "Jupiter": 10, "Venus": 6, "Saturn": 1, "Rahu": 8, "Ketu": 2}
    SIGN_RULERS = {1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon", 5: "Sun", 6: "Mercury", 7: "Venus", 8: "Mars", 9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"}
    
    is_own = (SIGN_RULERS.get(sign_num) == p_name)
    is_debilitated = (sign_num == DEBILITATION_RULES.get(p_name))
    is_exalted = (sign_num == EXALTATION_RULES.get(p_name))
    if p_name == "Moon" and sign_num == 2:
        is_exalted = (deg_in_sign <= 3.0)
        is_own = not is_exalted
    elif p_name == "Mercury" and sign_num == 6:
        is_exalted = (deg_in_sign <= 15.0)
        is_own = not is_exalted
    if p_name == "Moon" and sign_num == 8:
        is_debilitated = (deg_in_sign <= 3.0)
    elif p_name == "Mercury" and sign_num == 12:
        is_debilitated = (deg_in_sign <= 15.0)
        
    return is_exalted, is_own, is_debilitated

def setup_ui(app, layout):
    controller = RectificationController(app)
    group = QGroupBox("Rectify Time")
    v_layout = QVBoxLayout()
    v_layout.setContentsMargins(8, 8, 8, 8)
    
    status_label = QLabel("Find time of hypothetical charts. JSON (special format) can also be imported")
    status_label.setWordWrap(True)
    status_label.setStyleSheet("color: #555; font-size: 11px;")

    btn_layout = QHBoxLayout()
    btn_layout.setSpacing(6)
        
    btn_load_json_rectify = QPushButton("Load JSON")
    btn_load_json_rectify.setStyleSheet("QPushButton { font-weight: bold; color: #8E44AD; border: 1px solid #D2B4DE; background-color: #F5EEF8; padding: 4px; border-radius: 4px; } QPushButton:hover { background-color: #EBDEF0; border-color: #8E44AD; } QPushButton:pressed { background-color: #D7BDE2; border-style: inset; }")
    btn_load_json_rectify.clicked.connect(controller.load_json_rectify_dialog)

    btn_build_chart_rectify = QPushButton("Build Target Chart...")
    btn_build_chart_rectify.clicked.connect(controller.open_chart_builder_dialog)
    btn_build_chart_rectify.setStyleSheet("QPushButton { font-weight: bold; color: #2980B9; border: 1px solid #AED6F1; background-color: #EAF2F8; padding: 4px; border-radius: 4px; } QPushButton:hover { background-color: #D6EAF8; border-color: #2980B9; } QPushButton:pressed { background-color: #AED6F1; border-style: inset; }")

    btn_layout.addWidget(btn_load_json_rectify)
    btn_layout.addWidget(btn_build_chart_rectify)
    v_layout.addWidget(status_label)
    v_layout.addLayout(btn_layout)
    group.setLayout(v_layout)
    layout.addWidget(group)
    layout.controller = controller

# ==========================================
# CHART BUILDER DIALOG
# ==========================================
class ChartBuilderDialog(QDialog):
    def __init__(self, div_keys, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("Visual Target Chart Builder")
        self.resize(800, 500)
        
        main_layout = QHBoxLayout(self)
        left_panel = QWidget(); layout = QGridLayout(left_panel)

        self.div_cb = NoScrollComboBox()
        for k in div_keys: self.div_cb.addItem(self.app.div_titles.get(k, k), k)
        d1_idx = self.div_cb.findData("D1") if self.app else self.div_cb.findText("D1")
        if d1_idx >= 0: self.div_cb.setCurrentIndex(d1_idx)
        
        self.div_cb.currentIndexChanged.connect(self.update_live_chart)
        layout.addWidget(QLabel("Target Division:"), 0, 0)
        layout.addWidget(self.div_cb, 0, 1)

        self.planet_spins = {}
        self.planet_retros = {}
        for row, p in enumerate(["Ascendant", "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"], start=1):
            spin = QSpinBox(); spin.setRange(0, 12); spin.setSpecialValueText("0 (Ignore)")
            spin.valueChanged.connect(self.update_live_chart)
            layout.addWidget(QLabel(f"{'Lagna (Asc.)' if p == 'Ascendant' else p}:"), row, 0)
            
            spin_layout = QHBoxLayout()
            spin_layout.setContentsMargins(0, 0, 0, 0)
            spin_layout.addWidget(spin)
            
            if p not in ["Ascendant", "Sun", "Moon"]:
                chk = QCheckBox("Retro")
                if p in ["Rahu", "Ketu"]:
                    chk.setChecked(True)
                    chk.setEnabled(False)
                chk.stateChanged.connect(self.update_live_chart)
                self.planet_retros[p] = chk
                spin_layout.addWidget(chk)
            else:
                self.planet_retros[p] = None
                
            layout.addLayout(spin_layout, row, 1)
            self.planet_spins[p] = spin

        btn_box = QHBoxLayout()
        self.search_btn = QPushButton("Search Birth Time"); self.search_btn.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;"); self.search_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.search_btn); btn_box.addWidget(cancel_btn)
        layout.addLayout(btn_box, len(self.planet_spins)+1, 0, 1, 2)
        
        right_panel = QWidget(); right_layout = QVBoxLayout(right_panel)
        self.renderer = ChartRenderer() if ChartRenderer else QWidget()
        if ChartRenderer:
            self.renderer.title = "Hypothetical Target"
            if self.app:
                self.renderer.use_symbols = self.app.chk_symbols.isChecked()
                self.renderer.show_rahu_ketu = self.app.chk_rahu.isChecked()
                self.renderer.show_aspects = self.app.chk_aspects.isChecked()
                self.renderer.show_arrows = self.app.chk_arrows.isChecked()
                self.renderer.use_tint = self.app.chk_tint.isChecked()
                self.renderer.use_circular = self.app.chk_circular.isChecked()
        right_layout.addWidget(self.renderer)
        main_layout.addWidget(left_panel); main_layout.addWidget(right_panel)
        main_layout.setStretch(0, 1); main_layout.setStretch(1, 2)
        self.update_live_chart()

    def update_live_chart(self):
        if not ChartRenderer: return
        target_div = self.div_cb.currentData() or self.div_cb.currentText()
        target_asc = max(0, self.planet_spins["Ascendant"].value() - 1)
        self.renderer.title = f"Hypothetical Target {target_div}"
        
        synthetic_chart = {"ascendant": {"sign_index": target_asc, "sign_num": target_asc + 1, "degree": target_asc * 30 + 15.0, "div_lon": target_asc * 30 + 15.0, "vargottama": False}, "planets": [], "aspects": []}
        
        for p_name in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]:
            val = self.planet_spins[p_name].value()
            if val == 0: continue
            s_idx = val - 1; sign_num = val
            is_ex, is_ow, is_deb = plugin_get_dignities(p_name, sign_num, 15.0) 
            is_retro = self.planet_retros[p_name].isChecked() if self.planet_retros.get(p_name) else False

            synthetic_chart["planets"].append({
                "name": p_name, "sym": p_name[:2], "lon": s_idx * 30 + 15.0, "div_lon": s_idx * 30 + 15.0,
                "sign_index": s_idx, "sign_num": sign_num, "deg_in_sign": 15.0, "house": ((s_idx - target_asc) % 12) + 1,
                "retro": is_retro, "exalted": is_ex, "debilitated": is_deb, "combust": False, "own_sign": is_ow, "vargottama": False, "is_ak": False
            })
        self.renderer.update_chart(synthetic_chart)

    def get_chart_data(self):
        return (
            self.div_cb.currentData() or self.div_cb.currentText(), 
            self.planet_spins["Ascendant"].value() - 1 if self.planet_spins["Ascendant"].value() > 0 else None, 
            {p: self.planet_spins[p].value() - 1 for p in ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"] if self.planet_spins[p].value() > 0},
            {p: self.planet_retros[p].isChecked() for p in ["Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"] if self.planet_retros.get(p) and self.planet_retros[p].isChecked()}
        )


# ==========================================
# RECTIFICATION WORKERS
# ==========================================
def custom_rectification_search_wrapper(params, result_queue, stop_event):
    is_compiled = getattr(sys, 'frozen', False) or '__compiled__' in globals()
    mode_str = "EXPORTED" if is_compiled else "DEBUG"
    
    print(f"\n[DEBUG - PLUGIN] [{mode_str}] Initializing thread wrapper.")
    try:
        with rectification_engine.swe_lock: 
            ephe_path = rectification_engine.get_standalone_resource_path('ephe')
            swe.set_ephe_path(ephe_path)

        target_planets = params.get("target_planets", {})
        target_asc = params.get("target_asc")
        target_retro = params.get("target_retro", {})
        
        dummy_q = queue.Queue()
        base_year = params.get("base_year", 2024)
        s_range = params.get("search_range", 1000) 
        
        if not target_planets and target_asc is None:
            start_range = params.get("start_range", 0) 
            blocks = []
            if start_range > 0:
                blocks.append({"start_jd": swe.julday(base_year - s_range, 1, 1, 0.0), "end_jd": swe.julday(base_year - start_range, 12, 31, 23.99)})
                blocks.append({"start_jd": swe.julday(base_year + start_range, 1, 1, 0.0), "end_jd": swe.julday(base_year + s_range, 12, 31, 23.99)})
            else:
                blocks.append({"start_jd": swe.julday(base_year - s_range, 1, 1, 0.0), "end_jd": swe.julday(base_year + s_range, 12, 31, 23.99)})
                
            res = {"status": "success", "blocks": blocks, "year": f"Range +/- {s_range}", "last_range": s_range}
            
        else:
            def run_backend():
                try: rectification_engine.perform_rectification_search(params, dummy_q, stop_event)
                except Exception as e: dummy_q.put({"status": "error", "message": str(e)})
                finally: dummy_q.put({"__done__": True})
                    
            t = threading.Thread(target=run_backend, daemon=True)
            t.start()
            
            res = None
            while True:
                if stop_event.is_set(): return
                try:
                    msg = dummy_q.get(timeout=0.1)
                    if msg.get("__done__"): break
                    status = msg.get("status", "unknown")
                    if status == "progress": result_queue.put(msg)
                    else: res = msg
                except queue.Empty: continue
                    
            if res is None or res.get("status") not in ["success", "phase1_failed", "not_found"]:
                err_msg = res.get("message", "Backend search aborted or returned None.") if res else "Backend search aborted."
                result_queue.put({"status": "error", "message": err_msg})
                return
                
            if res.get("status") in ["not_found", "phase1_failed"]:
                result_queue.put({"status": "phase1_failed", "last_range": s_range})
                return
                
            if res.get("status") != "success":
                result_queue.put(res)
                return
                
        if not target_retro:
            result_queue.put(res)
            return
            
        swe_map = {"Sun": swe.SUN, "Moon": swe.MOON, "Mars": swe.MARS, "Mercury": swe.MERCURY, "Jupiter": swe.JUPITER, "Venus": swe.VENUS, "Saturn": swe.SATURN}
        target_swe = {swe_map[p]: want_retro for p, want_retro in target_retro.items() if p in swe_map}
        valid_blocks = []
        
        def check_retro(jd_val):
            for sp, want_retro in target_swe.items():
                try:
                    with rectification_engine.swe_lock: calc_res, _ = swe.calc_ut(jd_val, sp, swe.FLG_SWIEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL)
                    if (calc_res[3] < 0) != want_retro: return False
                except Exception:
                    try:
                        with rectification_engine.swe_lock: calc_res, _ = swe.calc_ut(jd_val, sp, swe.FLG_MOSEPH | swe.FLG_SPEED | swe.FLG_SIDEREAL)
                        if (calc_res[3] < 0) != want_retro: return False
                    except Exception: return False
            return True

        for b in res["blocks"]:
            start_jd = b.get("start_jd") or rectification_engine.dt_dict_to_utc_jd(b["start"], params.get("tz", "UTC"))
            end_jd = b.get("end_jd") or rectification_engine.dt_dict_to_utc_jd(b["end"], params.get("tz", "UTC"))
            
            duration = end_jd - start_jd
            step = max(1.0 / 1440.0, 2.0 if duration > 365 else min(0.5, duration / 4.0))

            current_jd = start_jd
            in_match = False
            match_start = None
            
            while True:
                if stop_event.is_set(): return
                check_t = min(current_jd, end_jd)
                match = check_retro(check_t)
                        
                if match and not in_match:
                    t0, t1 = max(start_jd, check_t - step), check_t
                    if check_retro(t0): match_start = t0
                    else:
                        for _ in range(15):
                            tm = (t0 + t1) / 2.0
                            if check_retro(tm): t1 = tm
                            else: t0 = tm
                        match_start = t1
                    in_match = True
                    
                elif not match and in_match:
                    t0, t1 = max(start_jd, check_t - step), check_t
                    for _ in range(15):
                        tm = (t0 + t1) / 2.0
                        if check_retro(tm): t0 = tm
                        else: t1 = tm
                    valid_blocks.append({"start_jd": match_start, "end_jd": t0})
                    in_match = False
                
                if current_jd >= end_jd:
                    if in_match: valid_blocks.append({"start_jd": match_start, "end_jd": end_jd})
                    break
                    
                current_jd += step
                
        final_blocks = []
        for vb in valid_blocks:
            final_blocks.append({"start": rectification_engine.utc_jd_to_dt_dict(vb["start_jd"], params.get("tz", "UTC")), "end": rectification_engine.utc_jd_to_dt_dict(vb["end_jd"], params.get("tz", "UTC")), "start_jd": vb["start_jd"], "end_jd": vb["end_jd"], "mid_jd": (vb["start_jd"] + vb["end_jd"])/2})
            
        if final_blocks:
            res["blocks"] = final_blocks
            result_queue.put(res)
        else:
            result_queue.put({"status": "phase1_failed", "last_range": s_range})

    except Exception as e:
        result_queue.put({"status": "error", "message": f"Search Error: {str(e)}"})

class RectificationWorkerThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, params): 
        super().__init__()
        self.params = params
        self.stop_event = threading.Event() 
        self.result_queue = queue.Queue()    
        self.thread = None
        
    def run(self):
        self.thread = threading.Thread(target=custom_rectification_search_wrapper, args=(self.params, self.result_queue, self.stop_event))
        self.thread.start()
        while self.thread.is_alive():
            if self.isInterruptionRequested():
                self.stop_event.set()
                self.thread.join(timeout=0.5)
                return
            try:
                res = self.result_queue.get(timeout=0.1)
                if res["status"] in ["success", "not_found", "phase1_failed"]: 
                    self.finished.emit(res)
                    return
                elif res["status"] == "progress": self.progress.emit(res["msg"])
                elif res["status"] == "error": 
                    self.error.emit(res["message"])
                    return
            except queue.Empty: continue
            
        while not self.result_queue.empty():
            res = self.result_queue.get()
            if res["status"] in ["success", "not_found", "phase1_failed"]: 
                self.finished.emit(res)
                return
            elif res["status"] == "error":
                self.error.emit(res["message"])
                return
            
    def stop(self): 
        self.requestInterruption()
        self.stop_event.set()

# ==========================================
# LOGIC CONTROLLER
# ==========================================
class RectificationController:
    def __init__(self, app):
        self.app = app
        self.rectify_dialog = None
        self.rectify_worker = None

    def open_chart_builder_dialog(self):
        dlg = ChartBuilderDialog(list(self.app.div_titles.keys()), self.app)
        if dlg.exec():
            target = dlg.get_chart_data()
            if not target[2] and target[1] is None and not target[3]: 
                QMessageBox.warning(self.app, "Empty Chart", "Please specify at least one planetary position, Ascendant, or Retrograde status.")
                return
            try:
                os.makedirs("created chart exports", exist_ok=True)
                all_p = set(target[2].keys()).union(target[3].keys())
                p_list = [{"name": p, **({"sign_index": target[2][p]} if p in target[2] else {}), **({"retro": target[3][p]} if p in target[3] else {})} for p in all_p]
                
                # We dynamically inject the APP's current lat/lon so it explicitly locks these coordinates into the saved JSON!
                export_metadata = {
                    "latitude": self.app.current_lat,
                    "longitude": self.app.current_lon,
                    "ayanamsa": self.app.cb_ayanamsa.currentText()
                }
                
                with open(os.path.join("created chart exports", f"tmp_created_{target[0]}_chart.json"), 'w') as f: 
                    json.dump({"divisional_charts": {target[0]: {"ascendant": {"sign_index": target[1]} if target[1] is not None else {}, "planets": p_list}}, "metadata": export_metadata}, f, indent=4)
            except Exception as e: print(f"Failed to auto-save built chart: {e}")
            self.initiate_rectification_flow(*target, metadata=export_metadata, auto_start=True)

    def load_json_rectify_dialog(self):
        if path := QFileDialog.getOpenFileName(self.app, "Load JSON for Rectification", getattr(self.app, "last_load_dir", ""), "JSON Files (*.json);;All Files (*)")[0]:
            try:
                with open(path, 'r') as f: data = json.load(f)
                charts = data.get("divisional_charts", data)
                if (target_div := next((div for div in self.app.div_titles.keys() if div in charts), None)) and (chart_node := charts[target_div]):
                    dlg = ChartBuilderDialog(list(self.app.div_titles.keys()), self.app)
                    dlg.div_cb.setCurrentText(target_div)
                    
                    if "ascendant" in chart_node and "sign_index" in chart_node["ascendant"]:
                        dlg.planet_spins["Ascendant"].setValue(chart_node["ascendant"]["sign_index"] + 1)
                        
                    for p in chart_node.get("planets", []):
                        if p.get("name") in dlg.planet_spins and "sign_index" in p:
                            dlg.planet_spins[p["name"]].setValue(p["sign_index"] + 1)
                            if p.get("retro") and p["name"] in dlg.planet_retros and dlg.planet_retros[p["name"]]:
                                dlg.planet_retros[p["name"]].setChecked(True)
                            
                    if dlg.exec():
                        target = dlg.get_chart_data()
                        if not target[2] and target[1] is None and not target[3]: 
                            QMessageBox.warning(self.app, "Empty Chart", "Please specify at least one planetary position, Ascendant, or Retrograde status.")
                            return
                        self.initiate_rectification_flow(*target, metadata=data.get("metadata", {}), auto_start=False)
                else: QMessageBox.warning(self.app, "Invalid JSON", "Could not find a valid divisional chart block (e.g. 'D60') in JSON.")
            except Exception as e: QMessageBox.critical(self.app, "Load Error", f"Failed to parse JSON:\n{str(e)}")

    def initiate_rectification_flow(self, target_div, target_asc, target_planets, target_retro=None, metadata=None, auto_start=False):
        is_compiled = getattr(sys, 'frozen', False) or '__compiled__' in globals()
        env_str = "EXPORTED APP" if is_compiled else "DEBUG MODE"
        
        # Pull coordinates from metadata if they exist, otherwise use app state.
        rectify_lat = metadata.get("latitude", self.app.current_lat) if metadata else self.app.current_lat
        rectify_lon = metadata.get("longitude", self.app.current_lon) if metadata else self.app.current_lon
        rectify_tz = TimezoneFinder().timezone_at(lng=rectify_lon, lat=rectify_lat) or "UTC" if metadata else self.app.current_tz
        rectify_ayanamsa = metadata["ayanamsa"] if metadata and "ayanamsa" in metadata else self.app.cb_ayanamsa.currentText()
        
        print(f"\n{'='*50}")
        print(f"[DEBUG - PLUGIN] RECTIFICATION JOB INITIATED")
        print(f"[DEBUG - PLUGIN] ENVIRONMENT: {env_str}")
        print(f"[DEBUG - PLUGIN] Target Div: {target_div}")
        print(f"[DEBUG - PLUGIN] LAT/LON Locked: {rectify_lat:.4f}, {rectify_lon:.4f}")
        print(f"[DEBUG - PLUGIN] Timezone String being passed: {rectify_tz}")
        print(f"{'='*50}")

        if metadata and "ayanamsa" in metadata: 
            self.app.cb_ayanamsa.setCurrentText(rectify_ayanamsa) 
            
        synthetic_chart = {"ascendant": {"sign_index": target_asc if target_asc is not None else 0, "sign_num": (target_asc if target_asc is not None else 0) + 1, "degree": (target_asc if target_asc is not None else 0) * 30 + 15.0, "div_lon": (target_asc if target_asc is not None else 0) * 30 + 15.0, "vargottama": False}, "planets": [], "aspects": []}

        for p_name, s_idx in target_planets.items():
            is_retro = target_retro.get(p_name, False) if target_retro else False
            is_ex, is_ow, is_deb = plugin_get_dignities(p_name, s_idx + 1, 15.0)
            synthetic_chart["planets"].append({"name": p_name, "sym": p_name[:2], "lon": s_idx * 30 + 15.0, "div_lon": s_idx * 30 + 15.0, "sign_index": s_idx, "sign_num": s_idx + 1, "deg_in_sign": 15.0, "house": ((s_idx - (target_asc if target_asc is not None else 0)) % 12) + 1, "retro": is_retro, "exalted": is_ex, "debilitated": is_deb, "combust": False, "own_sign": is_ow, "vargottama": False, "is_ak": False})

        self.rectify_dialog = QDialog(self.app)
        self.rectify_dialog.setWindowTitle(f"Verify & Rectify Target ({target_div})")
        self.rectify_dialog.resize(500, 600)
        
        info_text = f"Searching for hypothetical {target_div} chart.\nPlease wait..." if auto_start else f"Please verify the hypothetical {target_div} chart.\nClick 'Search Birth Time' to find the exact timestamp."
        if target_retro and not target_planets and target_asc is None:
            info_text = f"Searching for Retrograde periods only ({', '.join(target_retro.keys())}).\nPlease wait..." if auto_start else f"Please verify Retrograde constraints ({', '.join(target_retro.keys())}).\nClick 'Search Birth Time' to find."
            
        # Display the explicit coordinates in the UI!
        info_text += f"\n\nLocked Coordinates:\n{rectify_lat:.4f}, {rectify_lon:.4f} ({rectify_tz})"
            
        layout = QVBoxLayout()
        info_lbl = QLabel(info_text)
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("font-weight: bold; color: #2c3e50;")
        info_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_lbl)
        
        if ChartRenderer:
            renderer = ChartRenderer()
            renderer.title = f"Hypothetical Target {target_div}"
            renderer.setMinimumSize(400, 400)
            renderer.use_symbols = self.app.chk_symbols.isChecked()
            renderer.show_rahu_ketu = self.app.chk_rahu.isChecked()
            renderer.show_aspects = self.app.chk_aspects.isChecked()
            renderer.show_arrows = self.app.chk_arrows.isChecked()
            renderer.use_tint = self.app.chk_tint.isChecked()
            renderer.use_circular = self.app.chk_circular.isChecked()
            renderer.update_chart(synthetic_chart)
            layout.addWidget(renderer)
            
        self.rectify_lbl = QLabel("Starting search..." if auto_start else "Ready to search.")
        self.rectify_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.rectify_lbl.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(self.rectify_lbl)
        
        btn_layout = QHBoxLayout()
        self.rectify_btn_search = QPushButton("Search Birth Time")
        self.rectify_btn_search.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        export_btn = QPushButton("Export JSON")
        cancel_btn = QPushButton("Cancel")
        export_btn.setStyleSheet("font-weight: bold; color: #8e44ad; padding: 8px;")
        cancel_btn.setStyleSheet("padding: 8px;")
        
        self.rectify_worker = RectificationWorkerThread({
            "div_type": target_div, 
            "target_asc": target_asc, 
            "target_planets": target_planets, 
            "target_retro": target_retro or {}, 
            "base_year": self.app.year_spin.value(), 
            "lat": rectify_lat, 
            "lon": rectify_lon, 
            "tz": rectify_tz, 
            "ayanamsa": rectify_ayanamsa, 
            "search_mode": "speed",
            "custom_vargas": self.app.ephemeris.custom_vargas
        })
        
        def start_search(): 
            self.rectify_btn_search.setEnabled(False)
            self.rectify_btn_search.setText("Searching... Please wait.")
            self.rectify_worker.start()
            
        def export_target_chart():
            os.makedirs("created chart exports", exist_ok=True)
            if path := QFileDialog.getSaveFileName(self.rectify_dialog, "Export Target Chart JSON", os.path.join("created chart exports", f"tmp_created_{target_div}_chart.json"), "JSON Files (*.json);;All Files (*)")[0]:
                try:
                    all_p = set(target_planets.keys()).union(target_retro.keys()) if target_retro else set(target_planets.keys())
                    p_list = [{"name": p, **({"sign_index": target_planets[p]} if p in target_planets else {}), **({"retro": target_retro[p]} if target_retro and p in target_retro else {})} for p in all_p]
                    
                    # Hard-bake the accurate coordinates into the JSON export!
                    save_metadata = metadata.copy() if metadata else {}
                    save_metadata["latitude"] = rectify_lat
                    save_metadata["longitude"] = rectify_lon
                    save_metadata["ayanamsa"] = rectify_ayanamsa
                    
                    with open(path, 'w') as f: json.dump({"divisional_charts": {target_div: {"ascendant": {"sign_index": target_asc} if target_asc is not None else {}, "planets": p_list}}, "metadata": save_metadata}, f, indent=4)
                    QMessageBox.information(self.rectify_dialog, "Export Successful", f"Chart saved successfully to:\n{path}")
                except Exception as e: QMessageBox.critical(self.rectify_dialog, "Export Error", f"Failed to save JSON:\n{str(e)}")
                
        def cancel_rect(): 
            if self.rectify_worker.isRunning(): self.rectify_worker.stop()
            self.rectify_dialog.reject()
            
        self.rectify_btn_search.clicked.connect(start_search)
        export_btn.clicked.connect(export_target_chart)
        cancel_btn.clicked.connect(cancel_rect)
        
        for btn in [self.rectify_btn_search, export_btn, cancel_btn]: btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)
        self.rectify_dialog.setLayout(layout)
        
        self.rectify_worker.progress.connect(lambda msg: self.rectify_lbl.setText(msg))
        self.rectify_worker.error.connect(lambda err: QMessageBox.critical(self.app, "Critical Error", err) if "CRITICAL" in err else QMessageBox.warning(self.app, "Error", err))
        self.rectify_worker.finished.connect(self.on_rectify_finished)
        
        if auto_start: 
            self.rectify_btn_search.hide()
            export_btn.hide()
            QTimer.singleShot(100, start_search)
            
        self.rectify_dialog.exec()

    def on_rectify_finished(self, res):
        if res["status"] == "success":
            self.rectify_dialog.accept() 
            blocks = res.get("blocks", [])
            
            if not blocks:
                QMessageBox.warning(self.app, "Warning", "Search completed but no matching blocks were returned.")
                return

            def format_dt(dt_dict):
                month_str = datetime.date(2000, dt_dict['month'], 1).strftime('%B')
                return f"{dt_dict['day']} {month_str} {dt_dict['year']} at {dt_dict['hour']:02d}:{dt_dict['minute']:02d}:{int(dt_dict['second']):02d}"

            if len(blocks) == 1:
                b = blocks[0]
                mid_dt = rectification_engine.utc_jd_to_dt_dict(b["mid_jd"], self.app.current_tz)
                msg = f"Found exactly 1 precise match window.\n\nWindow Start: {format_dt(b['start'])}\nWindow End: {format_dt(b['end'])}\n\nJumping to target exact Midpoint:\n{format_dt(mid_dt)}"
                QMessageBox.information(self.app, "Rectification Success", msg)
                self.app.time_ctrl.set_time(mid_dt)
                return
                
            elif len(blocks) > 20:
                now = datetime.datetime.now(datetime.timezone.utc)
                today_jd = swe.julday(now.year, now.month, now.day, now.hour + now.minute/60.0 + now.second/3600.0)
                closest_block = min(blocks, key=lambda b: abs(b["mid_jd"] - today_jd))
                mid_dt = rectification_engine.utc_jd_to_dt_dict(closest_block["mid_jd"], self.app.current_tz)
                msg = f"Found {len(blocks)} matches (More than 20).\nAutomatically jumping to the date closest to TODAY:\n\nWindow Start: {format_dt(closest_block['start'])}\nWindow End: {format_dt(closest_block['end'])}\n\nJumping to target exact Midpoint:\n{format_dt(mid_dt)}"
                QMessageBox.information(self.app, "Rectification Success", msg)
                self.app.time_ctrl.set_time(mid_dt)
                return
                
            else:
                msg = f"Found {len(blocks)} match windows:\n\n"
                for i, b in enumerate(blocks):
                    mid_dt = rectification_engine.utc_jd_to_dt_dict(b["mid_jd"], self.app.current_tz)
                    msg += f"{i+1}. {format_dt(b['start'])} to {format_dt(b['end'])}\n    (Target Midpoint: {format_dt(mid_dt)})\n\n"
                    
                num, ok = QInputDialog.getInt(self.app, "Select Match", msg + "Enter the number of the match to jump to:", 1, 1, len(blocks), 1)
                if ok:
                    selected_block = blocks[num - 1]
                    mid_dt = rectification_engine.utc_jd_to_dt_dict(selected_block["mid_jd"], self.app.current_tz)
                    self.app.time_ctrl.set_time(mid_dt)
            
        elif res["status"] == "phase1_failed":
            current_range = res.get("last_range", 1000)
            next_range = current_range + 10000
            
            msg_box = QMessageBox(self.rectify_dialog)
            msg_box.setWindowTitle("Speed Search Missed")
            msg_box.setText(f"Cascading lock-pick search completely swept +/- {current_range} years but found no matches.\n\nChoose your fallback search method:")
            btn_next = msg_box.addButton(f"Search +/- {next_range} Years", QMessageBox.ButtonRole.AcceptRole)
            btn_brute = msg_box.addButton("Deep Brute-Force", QMessageBox.ButtonRole.AcceptRole)
            msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)
            msg_box.exec()
            
            if msg_box.clickedButton() in [btn_next, btn_brute]:
                self.rectify_btn_search.setEnabled(False)
                self.rectify_btn_search.setText(f"Searching +/- {next_range} Years... Please wait." if msg_box.clickedButton() == btn_next else "Brute-Forcing... Please wait.")
                params = self.rectify_worker.params.copy()
                if msg_box.clickedButton() == btn_next:
                    params["search_range"] = next_range
                    params["start_range"] = current_range + 1
                else: params["search_mode"] = "brute"
                self.rectify_worker = RectificationWorkerThread(params)
                self.rectify_worker.progress.connect(lambda msg: self.rectify_lbl.setText(msg))
                self.rectify_worker.error.connect(lambda err: QMessageBox.warning(self.app, "Error", err))
                self.rectify_worker.finished.connect(self.on_rectify_finished)
                self.rectify_worker.start()
            else: 
                self.rectify_dialog.accept()
                
        elif res["status"] == "not_found":
            self.rectify_dialog.accept()
            QMessageBox.warning(self.app, "Not Found", res["message"])