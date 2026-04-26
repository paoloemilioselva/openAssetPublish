from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QFrame, 
    QPushButton, QTreeWidget, QTreeWidgetItem, QMessageBox, QScrollArea,
    QColorDialog, QFileDialog, QDoubleSpinBox, QFormLayout, QComboBox,
    QSplitter
)
from PySide6.QtCore import Qt, Signal, QPoint, QTimer
from PySide6.QtGui import QDrag, QColor, QFont
import os
import shutil

from pxr import Usd, Sdf, UsdShade, Gf, Tf, Sdr, UsdGeom, UsdUtils

class MaterialPropertyEditor(QScrollArea):
    """Dynamically generates UI for USD Material/Shader inputs."""
    value_changed = Signal()

    def __init__(self):
        super().__init__()
        self.setWidgetResizable(True)
        self.setObjectName("PropertyEditor")
        self.container = QWidget()
        self.layout = QFormLayout(self.container)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)
        self.setWidget(self.container)
        self.current_prim = None

    def clear_editor(self):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.current_prim = None

    def load_prim(self, prim):
        self.clear_editor()
        if not prim: return
        
        self.current_prim = prim
        inputs_found = []
        material = UsdShade.Material(prim)
        if material:
            inputs_found.extend(material.GetInputs())

        shader = UsdShade.Shader(prim)
        if not shader and material:
            for child in prim.GetChildren():
                if child.IsA(UsdShade.Shader):
                    shader = UsdShade.Shader(child)
                    break
        if shader:
            inputs_found.extend(shader.GetInputs())

        if not inputs_found:
            label = QLabel("No editable inputs found.")
            label.setStyleSheet("font-style: italic; color: #888;")
            self.layout.addRow(label)
            return

        seen_names = set()
        for shader_input in sorted(inputs_found, key=lambda x: x.GetBaseName()):
            base_name = shader_input.GetBaseName()
            if base_name in seen_names: continue
            seen_names.add(base_name)
            
            widget = self._create_input_widget(shader_input)
            if widget:
                self.layout.addRow(base_name, widget)

    def _create_input_widget(self, shader_input):
        value = shader_input.Get()
        type_name = shader_input.GetTypeName()
        if type_name == Sdf.ValueTypeNames.Color3f:
            btn = QPushButton()
            btn.setMinimumHeight(25)
            color = QColor.fromRgbF(value[0], value[1], value[2]) if value else QColor(255, 255, 255)
            btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")
            btn.clicked.connect(lambda: self._open_color_picker(shader_input, btn))
            return btn
        elif type_name == Sdf.ValueTypeNames.Asset:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            path_edit = QLineEdit(str(value.path) if value else "")
            browse_btn = QPushButton("...")
            browse_btn.setFixedWidth(30)
            layout.addWidget(path_edit)
            layout.addWidget(browse_btn)
            path_edit.editingFinished.connect(lambda: self._update_asset_path(shader_input, path_edit.text()))
            browse_btn.clicked.connect(lambda: self._browse_asset(shader_input, path_edit))
            return container
        elif type_name == Sdf.ValueTypeNames.Float:
            spin = QDoubleSpinBox()
            spin.setRange(-10000, 10000)
            spin.setDecimals(3)
            spin.setValue(value if value is not None else 0.0)
            spin.valueChanged.connect(lambda v: self._update_float(shader_input, v))
            return spin
        else:
            label = QLabel(str(value) if value is not None else "None")
            label.setStyleSheet("color: #aaa;")
            return label

    def _open_color_picker(self, shader_input, button):
        val = shader_input.Get()
        initial = QColor.fromRgbF(val[0], val[1], val[2]) if val else Qt.GlobalColor.white
        color = QColorDialog.getColor(initial, self, "Select Color")
        if color.isValid():
            button.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")
            shader_input.Set(Gf.Vec3f(color.redF(), color.greenF(), color.blueF()))
            self.value_changed.emit()

    def _update_asset_path(self, shader_input, text):
        shader_input.Set(Sdf.AssetPath(text))
        self.value_changed.emit()

    def _browse_asset(self, shader_input, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select Texture", "", "Images (*.png *.jpg *.jpeg *.exr *.hdr *.tga)")
        if path:
            line_edit.setText(path)
            self._update_asset_path(shader_input, path)

    def _update_float(self, shader_input, value):
        shader_input.Set(float(value))
        self.value_changed.emit()

class DropSlot(QFrame):
    file_dropped = Signal(str)

    def __init__(self, label_text, slot_type="payload"):
        super().__init__()
        self.setObjectName("DropSlot")
        self.setAcceptDrops(True)
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        self.setMinimumHeight(80)
        self.layout = QVBoxLayout(self)
        self.label = QLabel(label_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-weight: bold; font-size: 14px; color: #888888;")
        type_indicator = " [Payload]" if slot_type == "payload" else " [Sublayer]"
        self.label.setText(label_text + type_indicator)
        self.path_label = QLabel("Drag & Drop File Here")
        self.path_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.path_label.setStyleSheet("color: #555555; font-style: italic;")
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.path_label)
        self.file_path = None
        self.slot_name = label_text
        self.slot_type = slot_type

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setProperty("dragging", True)
            self.style().unpolish(self)
            self.style().polish(self)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            self.file_path = urls[0].toLocalFile()
            self.path_label.setText(self.file_path)
            self.path_label.setStyleSheet("color: #007acc; font-weight: bold; font-style: normal;")
            self.file_dropped.emit(self.file_path)
        self.setProperty("dragging", False)
        self.style().unpolish(self)
        self.style().polish(self)

class OutlinerWidget(QTreeWidget):
    def __init__(self, publish_page):
        super().__init__()
        self.publish_page = publish_page
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setEditTriggers(QTreeWidget.EditTrigger.DoubleClicked)
        self.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item, column):
        if column != 0: return
        old_path_str = item.data(0, Qt.ItemDataRole.UserRole)
        if not old_path_str: return
        full_text = item.text(0)
        new_name = full_text.split(" (")[0].split(" [")[0].strip()
        if not new_name or not Tf.IsValidIdentifier(new_name):
            QMessageBox.warning(self, "Invalid Name", f"'{new_name}' is not a valid identifier.")
            self.publish_page.refresh_outliner()
            return
        old_path = Sdf.Path(old_path_str)
        if old_path.name == new_name: return
        if not self.publish_page.stage: return

        try:
            self.blockSignals(True)
            stage = self.publish_page.stage
            prim = stage.GetPrimAtPath(old_path)
            if not prim:
                self.blockSignals(False)
                return
            defining_layer = None
            source_path = None
            for spec in prim.GetPrimStack():
                if spec.layer.identifier != stage.GetRootLayer().identifier:
                    defining_layer = spec.layer
                    source_path = spec.path
                    break
            if not defining_layer:
                defining_layer = stage.GetEditTarget().GetLayer()
                source_path = old_path

            with Sdf.ChangeBlock():
                spec = defining_layer.GetPrimAtPath(source_path)
                if spec:
                    spec.name = new_name
                    if defining_layer.defaultPrim == old_path.name:
                        defining_layer.defaultPrim = new_name
            self.blockSignals(False)
            self.publish_page.refresh_outliner()
        except Exception as e:
            self.blockSignals(False)
            import traceback; traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Rename error: {str(e)}")
            self.publish_page.refresh_outliner()

    def mouseMoveEvent(self, event):
        item = self.itemAt(event.position().toPoint())
        if item:
            prim_type = item.data(0, Qt.ItemDataRole.UserRole + 1)
            if prim_type != "Material": return
        super().mouseMoveEvent(event)

    def dropEvent(self, event):
        source_item = self.currentItem()
        target_item = self.itemAt(event.position().toPoint())
        if source_item and target_item and target_item != source_item:
            prim_type = source_item.data(0, Qt.ItemDataRole.UserRole + 1)
            if prim_type == "Material":
                source_path = source_item.data(0, Qt.ItemDataRole.UserRole)
                target_path = target_item.data(0, Qt.ItemDataRole.UserRole)
                self.publish_page.bind_material(source_path, target_path)
                event.accept()
        else:
            super().dropEvent(event)

class PublishPage(QWidget):
    publish_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)
        self.settings = None 
        self.drop_slots = []
        
        # Resizable columns with QSplitter
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        
        # Left Panel
        self.left_panel = QFrame()
        self.left_panel.setObjectName("PublishPanel")
        self.left_layout = QVBoxLayout(self.left_panel)
        self.left_layout.setContentsMargins(15, 15, 15, 15)
        self.left_layout.setSpacing(15)
        self.name_label = QLabel("Asset Name")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter asset name...")
        self.left_layout.addWidget(self.name_label)
        self.left_layout.addWidget(self.name_input)
        self.slots_container_layout = QVBoxLayout()
        self.slots_container_layout.setSpacing(15)
        self.left_layout.addLayout(self.slots_container_layout)
        self.left_layout.addStretch()
        
        # Mid Panel
        self.mid_panel = QFrame()
        self.mid_panel.setObjectName("PublishPanel")
        self.mid_layout = QVBoxLayout(self.mid_panel)
        self.mid_layout.setContentsMargins(15, 15, 15, 15)
        self.outliner_label = QLabel("Outliner")
        self.outliner_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.outliner = OutlinerWidget(self)
        self.outliner.setObjectName("Outliner")
        self.outliner.setHeaderLabel("Composition Hierarchy")
        self.outliner.setAlternatingRowColors(True)
        self.outliner.itemSelectionChanged.connect(self._on_selection_changed)
        self.mid_layout.addWidget(self.outliner_label)
        self.mid_layout.addWidget(self.outliner)
        
        # Material Control Bar
        self.create_mtl_btn = QPushButton("Create New Material")
        self.create_mtl_btn.setObjectName("PublishButton")
        self.create_mtl_btn.setMinimumHeight(40)
        self.create_mtl_btn.clicked.connect(self.create_material)
        self.mid_layout.addWidget(self.create_mtl_btn)
        
        # Right Panel
        self.right_panel = QFrame()
        self.right_panel.setObjectName("PublishPanel")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(15, 15, 15, 15)
        self.prop_label = QLabel("Property Editor")
        self.prop_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.prop_editor = MaterialPropertyEditor()
        self.prop_editor.value_changed.connect(lambda: self.refresh_outliner()) 
        self.right_layout.addWidget(self.prop_label)
        self.right_layout.addWidget(self.prop_editor)

        # Assemble Splitter
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.mid_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setSizes([300, 400, 300])
        
        self.main_layout.addWidget(self.splitter)
        
        self.publish_btn = QPushButton("Publish Asset")
        self.publish_btn.setObjectName("PublishButton")
        self.publish_btn.setMinimumHeight(50)
        self.publish_btn.clicked.connect(self.on_publish)
        self.main_layout.addWidget(self.publish_btn)
        
        self.stage = None
        self.slot_index_layers = {} 
        self.slot_payload_layers = {} 

    def create_material(self):
        for slot in self.drop_slots:
            if slot.slot_name == "Materials":
                index_layer = self.slot_index_layers.get(slot.slot_name)
                with Usd.EditContext(self.stage, index_layer):
                    idx = 1
                    while index_layer.GetPrimAtPath(f"/main/{slot.slot_name}/mtl_{idx:02d}"): idx += 1
                    mtl_name = f"mtl_{idx:02d}"
                    mtl_path = Sdf.Path(f"/main/{slot.slot_name}/{mtl_name}")
                    
                    material = UsdShade.Material.Define(self.stage, mtl_path)
                    shd_path = mtl_path.AppendChild("shader")
                    shader = UsdShade.Shader.Define(self.stage, shd_path)
                    shader.CreateIdAttr("ND_standard_surface_surfaceshader")
                    material.CreateSurfaceOutput("mtlx").ConnectToSource(shader.ConnectableAPI(), "surface")
        self.refresh_outliner()

    def _on_selection_changed(self):
        selected = self.outliner.selectedItems()
        if not selected:
            self.prop_editor.clear_editor()
            return
        item = selected[0]
        prim_path = item.data(0, Qt.ItemDataRole.UserRole)
        if self.stage:
            prim = self.stage.GetPrimAtPath(prim_path)
            if prim and (prim.IsA(UsdShade.Material) or prim.IsA(UsdShade.Shader)):
                self.prop_editor.load_prim(prim)
            else:
                self.prop_editor.clear_editor()

    def set_settings(self, settings_page):
        self.settings = settings_page
        self.rebuild_slots(self.settings.get_slots())

    def rebuild_slots(self, slots_data):
        while self.slots_container_layout.count():
            item = self.slots_container_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        self.drop_slots = []
        for s in slots_data:
            slot = DropSlot(s["name"], s["type"])
            slot.file_dropped.connect(self.on_file_dropped)
            self.slots_container_layout.addWidget(slot)
            self.drop_slots.append(slot)
        self._create_new_stage()

    def on_file_dropped(self, file_path):
        slot = self.sender()
        if not slot: return
        source_layer = UsdUtils.FlattenLayerStack(Usd.Stage.Open(file_path))
        if not source_layer: return
        if slot.slot_type == "payload":
            payload_layer = self.slot_payload_layers.get(slot.slot_name)
            if payload_layer:
                with Sdf.ChangeBlock():
                    payload_layer.Clear()
                    payload_layer.TransferContent(source_layer)
        else:
            index_layer = self.slot_index_layers.get(slot.slot_name)
            if index_layer:
                with Sdf.ChangeBlock():
                    index_layer.Clear()
                    index_layer.TransferContent(source_layer)
        self.refresh_outliner()

    def _create_new_stage(self):
        self.stage = Usd.Stage.CreateInMemory()
        UsdGeom.Xform.Define(self.stage, "/main")
        self.stage.SetDefaultPrim(self.stage.GetPrimAtPath("/main"))
        self.slot_index_layers = {}
        self.slot_payload_layers = {}

        for slot in self.drop_slots:
            index_layer = Sdf.Layer.CreateAnonymous(f"{slot.slot_name}/index.usda")
            self.slot_index_layers[slot.slot_name] = index_layer
            self.stage.GetRootLayer().subLayerPaths.append(index_layer.identifier)

            if slot.slot_type == "payload":
                payload_layer = Sdf.Layer.CreateAnonymous(f"{slot.slot_name}/payload.usd")
                self.slot_payload_layers[slot.slot_name] = payload_layer
                Sdf.CreatePrimInLayer(payload_layer, "/main")
                payload_layer.defaultPrim = "main"
                with Usd.EditContext(self.stage, index_layer):
                    scope_prim = self.stage.DefinePrim(f"/main/{slot.slot_name}", "Scope")
                    scope_prim.GetPayloads().AddPayload(Sdf.Payload(payload_layer.identifier, "/main"))
        self.refresh_outliner()

    def bind_material(self, mat_path, target_path):
        for slot in self.drop_slots:
            if slot.slot_name == "Bindings":
                index_layer = self.slot_index_layers.get(slot.slot_name)
                author_stage = Usd.Stage.Open(index_layer)
                target_prim = author_stage.OverridePrim(target_path)
                binding_api = UsdShade.MaterialBindingAPI.Apply(target_prim)
                material = UsdShade.Material(self.stage.GetPrimAtPath(mat_path))
                binding_api.Bind(material)
        self.refresh_outliner()

    def refresh_outliner(self):
        self.outliner.blockSignals(True)
        self.outliner.clear()
        if self.stage:
            main_prim = self.stage.GetPrimAtPath("/main")
            if main_prim:
                print(f"DEBUG: Found main prim, starting traversal. Children: {len(main_prim.GetChildren())}")
                self._add_prim_to_tree(main_prim, self.outliner)
            else:
                print("DEBUG: Main prim not found in stage!")
        self.outliner.blockSignals(False)

    def _add_prim_to_tree(self, prim, parent_item):
        name, type_name = prim.GetName(), prim.GetTypeName()
        display_name = f"{name} ({type_name})"
        for slot in self.drop_slots:
            if slot.slot_name == "Bindings":
                index_layer = self.slot_index_layers.get(slot.slot_name)
                if index_layer and index_layer.GetPrimAtPath(prim.GetPath()):
                    display_name += " [BOUND]"
        
        item = QTreeWidgetItem(parent_item, [display_name])
        item.setData(0, Qt.ItemDataRole.UserRole, str(prim.GetPath()))
        item.setData(0, Qt.ItemDataRole.UserRole + 1, str(type_name))
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        if "[BOUND]" in display_name: item.setForeground(0, QColor("#0099ff"))
        if type_name == "Material": item.setForeground(0, QColor("#00ff99"))
        item.setExpanded(True)

        for child in prim.GetChildren():
            if not child.IsValid(): continue
            self._add_prim_to_tree(child, item)

    def on_publish(self):
        name = self.name_input.text().strip()
        if not name: return
        lib_path = self.settings.get_library_path() if self.settings else os.getcwd()
        asset_dir = os.path.normpath(os.path.join(lib_path, name))
        os.makedirs(asset_dir, exist_ok=True)
        final_sublayers = []
        try:
            for slot in self.drop_slots:
                index_layer = self.slot_index_layers.get(slot.slot_name)
                if not index_layer: continue
                clean_name = slot.slot_name.lower().replace(" ", "_")
                slot_dir = os.path.join(asset_dir, clean_name)
                os.makedirs(slot_dir, exist_ok=True)

                if slot.slot_type == "payload":
                    payload_layer = self.slot_payload_layers.get(slot.slot_name)
                    payload_filename = "payload.usd"
                    payload_layer.Export(os.path.join(slot_dir, payload_filename))
                    scope_prim = index_layer.GetPrimAtPath(f"/main/{slot.slot_name}")
                    scope_prim.payloadList.prependedItems = [Sdf.Payload(payload_filename, "/main")]
                index_layer.Export(os.path.join(slot_dir, "index.usda"))

                final_sublayers.append(f"{clean_name}/index.usda")
            root_stage = Usd.Stage.CreateNew(os.path.join(asset_dir, "index.usda"))
            root_main = root_stage.DefinePrim("/main")
            root_stage.SetDefaultPrim(root_main)
            root_stage.GetRootLayer().subLayerPaths = final_sublayers
            root_stage.Save()
            QMessageBox.information(self, "Success", f"Asset '{name}' published.")
        except Exception as e:
            import traceback; traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Publish failed: {str(e)}")
            return
        self.publish_requested.emit(name)
        self.rebuild_slots(self.settings.get_slots())
        self.name_input.clear()
