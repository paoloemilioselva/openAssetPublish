import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, 
    QFileDialog, QFrame, QTableWidget, QTableWidgetItem, QComboBox, QHeaderView,
    QDoubleSpinBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal

class SettingsPage(QWidget):
    library_path_changed = Signal(str)
    slots_changed = Signal(list) 

    def __init__(self, config_path="config.json"):
        super().__init__()
        self.config_path = config_path
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(20)

        self.title = QLabel("Settings")
        self.title.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.layout.addWidget(self.title)

        # Library and Metadata Section
        self.top_container = QFrame()
        self.top_container.setObjectName("PublishPanel")
        self.top_layout = QVBoxLayout(self.top_container)
        self.top_layout.setContentsMargins(15, 15, 15, 15)
        self.top_layout.setSpacing(15)

        # Library Path
        self.path_label = QLabel("Library Root Path")
        self.path_input_layout = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setObjectName("AssetNameInput")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setMinimumHeight(35)
        self.browse_btn.clicked.connect(self.browse_path)
        self.path_input_layout.addWidget(self.path_input)
        self.path_input_layout.addWidget(self.browse_btn)
        self.top_layout.addWidget(self.path_label)
        self.top_layout.addLayout(self.path_input_layout)

        # Stage Metadata (Up Axis & Meters Per Unit)
        self.metadata_layout = QHBoxLayout()
        
        self.up_axis_label = QLabel("Default Up Axis")
        self.up_axis_combo = QComboBox()
        self.up_axis_combo.addItems(["Y", "Z"])
        self.up_axis_combo.setMinimumHeight(35)
        
        self.meters_label = QLabel("Meters Per Unit")
        self.meters_input = QDoubleSpinBox()
        self.meters_input.setRange(0.0001, 10000.0)
        self.meters_input.setValue(1.0)
        self.meters_input.setDecimals(4)
        self.meters_input.setMinimumHeight(35)
        
        self.metadata_layout.addWidget(self.up_axis_label)
        self.metadata_layout.addWidget(self.up_axis_combo)
        self.metadata_layout.addSpacing(20)
        self.metadata_layout.addWidget(self.meters_label)
        self.metadata_layout.addWidget(self.meters_input)
        self.metadata_layout.addStretch()
        self.top_layout.addLayout(self.metadata_layout)
        self.layout.addWidget(self.top_container)

        # OBJ Import Section
        self.obj_container = QFrame()
        self.obj_container.setObjectName("PublishPanel")
        self.obj_layout = QVBoxLayout(self.obj_container)
        self.obj_layout.setContentsMargins(15, 15, 15, 15)
        self.obj_layout.setSpacing(10)
        
        self.obj_title = QLabel("OBJ Import Defaults")
        self.obj_title.setStyleSheet("font-weight: bold;")
        
        self.obj_controls_layout = QHBoxLayout()
        
        # Rotation
        self.rot_label = QLabel("Rotation (X, Y, Z)")
        self.rot_x = QDoubleSpinBox()
        self.rot_y = QDoubleSpinBox()
        self.rot_z = QDoubleSpinBox()
        for sb in [self.rot_x, self.rot_y, self.rot_z]:
            sb.setRange(-360.0, 360.0)
            sb.setMinimumHeight(30)
            
        # Scale
        self.scale_label = QLabel("Scale Multiplier")
        self.scale_input = QDoubleSpinBox()
        self.scale_input.setRange(0.0001, 10000.0)
        self.scale_input.setValue(1.0)
        self.scale_input.setMinimumHeight(30)

        self.obj_controls_layout.addWidget(self.rot_label)
        self.obj_controls_layout.addWidget(self.rot_x)
        self.obj_controls_layout.addWidget(self.rot_y)
        self.obj_controls_layout.addWidget(self.rot_z)
        self.obj_controls_layout.addSpacing(20)
        self.obj_controls_layout.addWidget(self.scale_label)
        self.obj_controls_layout.addWidget(self.scale_input)
        self.obj_controls_layout.addStretch()
        
        # Toggles layout
        self.toggles_layout = QHBoxLayout()
        self.preview_cb = QCheckBox("Preview after Import")
        self.subdiv_cb = QCheckBox("Enable Subdivision")
        self.recalc_normals_cb = QCheckBox("Recalculate Normals")
        
        self.toggles_layout.addWidget(self.preview_cb)
        self.toggles_layout.addWidget(self.subdiv_cb)
        self.toggles_layout.addWidget(self.recalc_normals_cb)
        self.toggles_layout.addStretch()

        self.obj_layout.addWidget(self.obj_title)
        self.obj_layout.addLayout(self.obj_controls_layout)
        self.obj_layout.addLayout(self.toggles_layout)
        self.layout.addWidget(self.obj_container)

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
        self.slots_table.setObjectName("Outliner")

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
                    self.up_axis_combo.setCurrentText(config.get("up_axis", "Y"))
                    self.meters_input.setValue(config.get("meters_per_unit", 1.0))
                    
                    obj_settings = config.get("obj_import", {})
                    rot = obj_settings.get("rotation", [0.0, 0.0, 0.0])
                    self.rot_x.setValue(rot[0])
                    self.rot_y.setValue(rot[1])
                    self.rot_z.setValue(rot[2])
                    self.scale_input.setValue(obj_settings.get("scale", 1.0))
                    self.preview_cb.setChecked(obj_settings.get("preview", True))
                    self.subdiv_cb.setChecked(obj_settings.get("subdivision", False))
                    self.recalc_normals_cb.setChecked(obj_settings.get("recalc_normals", False))
                    
                    slots = config.get("slots", default_slots)
                    for s in slots:
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
        self.up_axis_combo.setCurrentText("Y")
        self.meters_input.setValue(1.0)
        self.rot_x.setValue(0.0)
        self.rot_y.setValue(0.0)
        self.rot_z.setValue(0.0)
        self.scale_input.setValue(1.0)
        self.preview_cb.setChecked(True)
        self.subdiv_cb.setChecked(False)
        self.recalc_normals_cb.setChecked(False)
        for s in slots:
            self.add_slot_row(s["name"], s["type"])

    def save_config(self):
        path = self.path_input.text()
        slots = self.get_slots()
        up_axis = self.up_axis_combo.currentText()
        meters = self.meters_input.value()
        obj_settings = {
            "rotation": [self.rot_x.value(), self.rot_y.value(), self.rot_z.value()],
            "scale": self.scale_input.value(),
            "preview": self.preview_cb.isChecked(),
            "subdivision": self.subdiv_cb.isChecked(),
            "recalc_normals": self.recalc_normals_cb.isChecked()
        }
        try:
            with open(self.config_path, 'w') as f:
                json.dump({
                    "library_path": path,
                    "up_axis": up_axis,
                    "meters_per_unit": meters,
                    "obj_import": obj_settings,
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

    def get_up_axis(self):
        return self.up_axis_combo.currentText()
    
    def get_meters_per_unit(self):
        return self.meters_input.value()
    
    def get_obj_import_settings(self):
        return {
            "rotation": [self.rot_x.value(), self.rot_y.value(), self.rot_z.value()],
            "scale": self.scale_input.value(),
            "preview": self.preview_cb.isChecked(),
            "subdivision": self.subdiv_cb.isChecked(),
            "recalc_normals": self.recalc_normals_cb.isChecked()
        }

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
