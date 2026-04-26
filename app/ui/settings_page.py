import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, 
    QFileDialog, QFrame, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView
)
from PySide6.QtCore import Qt, Signal

class SettingsPage(QWidget):
    library_path_changed = Signal(str)
    slots_changed = Signal(list) # List of dicts: {"name": str, "type": "payload"|"sublayer"}

    def __init__(self, config_path="config.json"):
        super().__init__()
        self.config_path = config_path
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)

        self.title = QLabel("Settings")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(self.title)

        # Library Path Section
        self.path_container = QFrame()
        self.path_container.setObjectName("PublishPanel")
        self.path_layout = QVBoxLayout(self.path_container)
        self.path_layout.setContentsMargins(15, 15, 15, 15)

        self.path_label = QLabel("Library Root Path")
        self.path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setObjectName("AssetNameInput")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setMinimumHeight(35)
        self.browse_btn.clicked.connect(self.browse_path)

        self.path_input_layout.addWidget(self.path_input)
        self.path_input_layout.addWidget(self.browse_btn)
        self.path_layout.addWidget(self.path_label)
        self.path_layout.addLayout(self.path_input_layout)
        self.layout.addWidget(self.path_container)

        # Slots Configuration Section
        self.slots_container = QFrame()
        self.slots_container.setObjectName("PublishPanel")
        self.slots_layout = QVBoxLayout(self.slots_container)
        self.slots_layout.setContentsMargins(15, 15, 15, 15)

        self.slots_label = QLabel("Publish Slots Configuration")
        self.slots_table = QTableWidget(0, 2)
        self.slots_table.setHorizontalHeaderLabels(["Slot Name", "Composition Type"])
        self.slots_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.slots_table.setMinimumHeight(200)
        self.slots_table.setObjectName("Outliner") # Reuse styling

        self.btn_layout = QHBoxLayout()
        self.add_slot_btn = QPushButton("Add Slot")
        self.add_slot_btn.clicked.connect(self.add_slot_row)
        self.remove_slot_btn = QPushButton("Remove Selected")
        self.remove_slot_btn.clicked.connect(self.remove_selected_row)
        self.apply_btn = QPushButton("Apply Changes")
        self.apply_btn.setObjectName("PublishButton")
        self.apply_btn.clicked.connect(self.apply_slots)

        self.btn_layout.addWidget(self.add_slot_btn)
        self.btn_layout.addWidget(self.remove_slot_btn)
        self.btn_layout.addStretch()
        self.btn_layout.addWidget(self.apply_btn)

        self.slots_layout.addWidget(self.slots_label)
        self.slots_layout.addWidget(self.slots_table)
        self.slots_layout.addLayout(self.btn_layout)
        self.layout.addWidget(self.slots_container)

        self.layout.addStretch()

        self.load_config()

    def add_slot_row(self, name="", slot_type="payload"):
        row = self.slots_table.rowCount()
        self.slots_table.insertRow(row)
        
        name_item = QTableWidgetItem(name)
        self.slots_table.setItem(row, 0, name_item)
        
        type_combo = QComboBox()
        type_combo.addItems(["payload", "sublayer"])
        type_combo.setCurrentText(slot_type)
        self.slots_table.setCellWidget(row, 1, type_combo)

    def remove_selected_row(self):
        current_row = self.slots_table.currentRow()
        if current_row >= 0:
            self.slots_table.removeRow(current_row)

    def load_config(self):
        default_path = os.path.join(os.getcwd(), "library")
        default_slots = [
            {"name": "Materials", "type": "payload"},
            {"name": "Geometry", "type": "payload"}
        ]
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    self.path_input.setText(config.get("library_path", default_path))
                    slots = config.get("slots", default_slots)
                    for s in slots:
                        # Handle backward compatibility if slots was just a list of strings
                        if isinstance(s, str):
                            self.add_slot_row(s, "payload")
                        else:
                            self.add_slot_row(s["name"], s["type"])
            except Exception as e:
                print(f"Error loading config: {e}")
                self._load_defaults(default_path, default_slots)
        else:
            self._load_defaults(default_path, default_slots)

    def _load_defaults(self, path, slots):
        self.path_input.setText(path)
        for s in slots:
            self.add_slot_row(s["name"], s["type"])

    def save_config(self):
        path = self.path_input.text()
        slots = self.get_slots()
        try:
            with open(self.config_path, 'w') as f:
                json.dump({
                    "library_path": path,
                    "slots": slots
                }, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def browse_path(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Select Library Root")
        if dir_path:
            self.path_input.setText(dir_path)
            self.save_config()
            self.library_path_changed.emit(dir_path)

    def apply_slots(self):
        self.save_config()
        slots = self.get_slots()
        self.slots_changed.emit(slots)

    def get_library_path(self):
        return self.path_input.text()

    def get_slots(self):
        slots = []
        for i in range(self.slots_table.rowCount()):
            name_item = self.slots_table.item(i, 0)
            name = name_item.text() if name_item else ""
            type_widget = self.slots_table.cellWidget(i, 1)
            slot_type = type_widget.currentText() if type_widget else "payload"
            if name:
                slots.append({"name": name, "type": slot_type})
        return slots
