# custom_vargas_ui.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QSpinBox, QComboBox, QPushButton, 
                             QListWidget, QMessageBox, QGridLayout, QGroupBox)
from PyQt6.QtCore import Qt

ZODIAC_NAMES = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", 
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

class CustomVargaEditor(QDialog):
    def __init__(self, parent=None, edit_id=None, edit_data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Custom Varga" if edit_id else "Add Custom Varga")
        self.resize(450, 500)
        
        layout = QVBoxLayout(self)

        info_group = QGroupBox("Basic Details")
        info_lay = QGridLayout(info_group)
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("e.g. D144")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. D144 (My Custom)")
        self.parts_input = QSpinBox()
        self.parts_input.setRange(2, 500)

        if edit_id:
            self.id_input.setText(edit_id)
            self.id_input.setEnabled(False) # ID serves as unique key, do not change
        if edit_data:
            self.title_input.setText(edit_data.get("title", ""))
            self.parts_input.setValue(edit_data.get("parts", 2))

        info_lay.addWidget(QLabel("Varga ID Key:"), 0, 0)
        info_lay.addWidget(self.id_input, 0, 1)
        info_lay.addWidget(QLabel("Display Title:"), 1, 0)
        info_lay.addWidget(self.title_input, 1, 1)
        info_lay.addWidget(QLabel("Number of Parts:"), 2, 0)
        info_lay.addWidget(self.parts_input, 2, 1)
        layout.addWidget(info_group)

        starts_group = QGroupBox("Starting Sign for Each Rashi")
        starts_lay = QGridLayout(starts_group)
        self.start_cbs = []
        starts = edit_data.get("starts", [0]*12) if edit_data else [0]*12
        
        for i in range(12):
            cb = QComboBox()
            cb.addItems(ZODIAC_NAMES)
            cb.setCurrentIndex(starts[i])
            self.start_cbs.append(cb)
            starts_lay.addWidget(QLabel(f"{ZODIAC_NAMES[i]}:"), i // 2, (i % 2) * 2)
            starts_lay.addWidget(cb, i // 2, (i % 2) * 2 + 1)
            
        layout.addWidget(starts_group)

        btn_lay = QHBoxLayout()
        btn_lay.addStretch()
        save_btn = QPushButton("Save Rule")
        save_btn.setStyleSheet("font-weight: bold; background-color: #27ae60; color: white;")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_lay.addWidget(save_btn)
        btn_lay.addWidget(cancel_btn)
        layout.addLayout(btn_lay)

    def get_data(self):
        return {
            "id": self.id_input.text().strip(),
            "title": self.title_input.text().strip(),
            "parts": self.parts_input.value(),
            "starts": [cb.currentIndex() for cb in self.start_cbs]
        }


class ManageCustomVargasDialog(QDialog):
    def __init__(self, custom_vargas_defs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Custom Vargas")
        self.resize(400, 350)
        self.vargas = custom_vargas_defs.copy()
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Define your own calculations for custom divisional charts.")
        lbl.setStyleSheet("color: #555; font-style: italic;")
        layout.addWidget(lbl)
        
        self.list_widget = QListWidget()
        self.refresh_list()
        layout.addWidget(self.list_widget)

        btn_lay = QHBoxLayout()
        add_btn = QPushButton("Add New...")
        edit_btn = QPushButton("Edit...")
        del_btn = QPushButton("Delete")
        
        add_btn.clicked.connect(self.add_varga)
        edit_btn.clicked.connect(self.edit_varga)
        del_btn.clicked.connect(self.del_varga)
        
        btn_lay.addWidget(add_btn)
        btn_lay.addWidget(edit_btn)
        btn_lay.addWidget(del_btn)
        layout.addLayout(btn_lay)

        close_lay = QHBoxLayout()
        close_lay.addStretch()
        save_btn = QPushButton("Apply to App")
        save_btn.setStyleSheet("font-weight: bold; background-color: #2980b9; color: white;")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        close_lay.addWidget(save_btn)
        close_lay.addWidget(cancel_btn)
        layout.addLayout(close_lay)

    def refresh_list(self):
        self.list_widget.clear()
        for k, v in self.vargas.items():
            self.list_widget.addItem(f"{k} - {v.get('title', 'Custom')}")

    def add_varga(self):
        dlg = CustomVargaEditor(self)
        if dlg.exec():
            data = dlg.get_data()
            vid = data["id"]
            if not vid:
                QMessageBox.warning(self, "Error", "ID cannot be empty.")
                return
                
            standard_vargas = ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60"]
            if vid in self.vargas or vid in standard_vargas:
                QMessageBox.warning(self, "Error", f"ID '{vid}' already exists or is a reserved standard varga.")
                return
                
            self.vargas[vid] = data
            self.refresh_list()

    def edit_varga(self):
        item = self.list_widget.currentItem()
        if not item: return
        vid = item.text().split(" - ")[0]
        dlg = CustomVargaEditor(self, vid, self.vargas[vid])
        if dlg.exec():
            self.vargas[vid] = dlg.get_data()
            self.refresh_list()

    def del_varga(self):
        item = self.list_widget.currentItem()
        if not item: return
        vid = item.text().split(" - ")[0]
        
        ans = QMessageBox.question(self, "Confirm Delete", f"Are you sure you want to delete {vid}?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if ans == QMessageBox.StandardButton.Yes:
            del self.vargas[vid]
            self.refresh_list()