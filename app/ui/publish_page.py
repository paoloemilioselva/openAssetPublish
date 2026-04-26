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

STANDARD_SURFACE_CHANNELS = [
    ("base", Sdf.ValueTypeNames.Float),
    ("base_color", Sdf.ValueTypeNames.Color3f),
    ("coat", Sdf.ValueTypeNames.Float),
    ("coat_affect_color", Sdf.ValueTypeNames.Float),
    ("coat_affect_roughness", Sdf.ValueTypeNames.Float),
    ("coat_anisotropy", Sdf.ValueTypeNames.Float),
    ("coat_color", Sdf.ValueTypeNames.Color3f),
    ("coat_IOR", Sdf.ValueTypeNames.Float),
    ("coat_normal", Sdf.ValueTypeNames.Vector3f),
    ("coat_rotation", Sdf.ValueTypeNames.Float),
    ("coat_roughness", Sdf.ValueTypeNames.Float),
    ("diffuse_roughness", Sdf.ValueTypeNames.Float),
    ("emission", Sdf.ValueTypeNames.Float),
    ("emission_color", Sdf.ValueTypeNames.Color3f),
    ("metalness", Sdf.ValueTypeNames.Float),
    ("opacity", Sdf.ValueTypeNames.Color3f),
    ("sheen", Sdf.ValueTypeNames.Float),
    ("sheen_color", Sdf.ValueTypeNames.Color3f),
    ("sheen_roughness", Sdf.ValueTypeNames.Float),
    ("specular", Sdf.ValueTypeNames.Float),
    ("specular_anisotropy", Sdf.ValueTypeNames.Float),
    ("specular_color", Sdf.ValueTypeNames.Color3f),
    ("specular_IOR", Sdf.ValueTypeNames.Float),
    ("specular_rotation", Sdf.ValueTypeNames.Float),
    ("specular_roughness", Sdf.ValueTypeNames.Float),
    ("subsurface", Sdf.ValueTypeNames.Float),
    ("subsurface_anisotropy", Sdf.ValueTypeNames.Float),
    ("subsurface_color", Sdf.ValueTypeNames.Color3f),
    ("subsurface_radius", Sdf.ValueTypeNames.Color3f),
    ("subsurface_scale", Sdf.ValueTypeNames.Float),
    ("thin_film_IOR", Sdf.ValueTypeNames.Float),
    ("thin_film_thickness", Sdf.ValueTypeNames.Float),
    ("transmission", Sdf.ValueTypeNames.Float),
    ("transmission_color", Sdf.ValueTypeNames.Color3f),
    ("transmission_depth", Sdf.ValueTypeNames.Float),
    ("transmission_extra_roughness", Sdf.ValueTypeNames.Float),
    ("transmission_scatter", Sdf.ValueTypeNames.Color3f),
    ("transmission_scatter_anisotropy", Sdf.ValueTypeNames.Float)
]

class MaterialPropertyEditor(QScrollArea):
    """Simple UI for authored inputs on the selected Material or Shader prim."""
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
        if not prim.IsA(UsdShade.Material): return

        self.current_prim = UsdShade.Material(prim)
        
        # Get inputs directly from the prim (Material or Shader)
        inputs = self.current_prim.GetInputs()
        if not inputs:
            label = QLabel("No authored inputs found.")
            label.setStyleSheet("color: #888; font-style: italic;")
            self.layout.addRow(label)
            return

        for shader_input in inputs:
            widget = self._create_input_widget(shader_input)
            if widget:
                self.layout.addRow(shader_input.GetBaseName(), widget)

    def _create_input_widget(self, shader_input):
        # Check for existing texture connection via sources safely
        try:
            # GetConnectedSources returns (sourceInfos, invalidSourceInfos)
            sources, _ = shader_input.GetConnectedSources()
            if sources:
                for info in sources:
                    # info is a UsdShade.ConnectionSourceInfo
                    source_api = info.source # This is a UsdShade.ConnectableAPI
                    if not source_api: continue
                    
                    src_prim = source_api.GetPrim()
                    if src_prim and src_prim.IsA(UsdShade.Shader):
                        src_shader = UsdShade.Shader(src_prim)
                        shader_id_attr = src_shader.GetIdAttr()
                        if shader_id_attr.HasValue():
                            shader_id = str(shader_id_attr.Get())
                            if "ND_image" in shader_id:
                                file_input = src_shader.GetInput("file")
                                if not file_input:
                                    file_input = src_shader.CreateInput("file", Sdf.ValueTypeNames.Asset)
                                return self._create_texture_picker(file_input)
        except Exception as e:
            import traceback; traceback.print_exc()
            print(f"DEBUG: Error checking connected sources: {e}")

        # Standard value widget with "T" button
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        val_widget = self._get_value_widget(shader_input)
        tex_btn = QPushButton("T")
        tex_btn.setFixedWidth(25)
        tex_btn.setToolTip("Connect Texture")
        tex_btn.clicked.connect(lambda: self._convert_to_texture(shader_input))
        
        layout.addWidget(val_widget)
        layout.addWidget(tex_btn)
        return container

    def _get_value_widget(self, shader_input):
        value = shader_input.Get()
        type_name = shader_input.GetTypeName()
        
        if type_name == Sdf.ValueTypeNames.Color3f:
            btn = QPushButton()
            btn.setMinimumHeight(25)
            color = QColor.fromRgbF(value[0], value[1], value[2]) if value else QColor(255, 255, 255)
            btn.setStyleSheet(f"background-color: {color.name()}; border: 1px solid #555;")
            btn.clicked.connect(lambda: self._open_color_picker(shader_input, btn))
            return btn
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

    def _create_texture_picker(self, file_input):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        value = file_input.Get()
        path_str = str(value.path) if value else ""
        
        path_edit = QLineEdit(path_str)
        browse_btn = QPushButton("...")
        browse_btn.setFixedWidth(30)
        
        layout.addWidget(path_edit)
        layout.addWidget(browse_btn)
        
        path_edit.editingFinished.connect(lambda: self._update_asset_path(file_input, path_edit.text()))
        browse_btn.clicked.connect(lambda: self._browse_asset(file_input, path_edit))
        return container

    def _convert_to_texture(self, shader_input):
        prim = shader_input.GetPrim()
        # Find material parent to house the texture shader
        material_prim = prim if prim.IsA(UsdShade.Material) else prim.GetParent()
        if not material_prim.IsA(UsdShade.Material): return
        
        stage = prim.GetStage()
        input_name = shader_input.GetBaseName()
        sdf_type = shader_input.GetTypeName()
        
        tex_type_suffix = str(sdf_type).replace("3f", "3")
        tex_id = f"ND_image_{tex_type_suffix}"
        
        with Sdf.ChangeBlock():
            tex_path = material_prim.GetPath().AppendChild(f"tex_{input_name}")
            tex_shader = UsdShade.Shader.Define(stage, tex_path)
            tex_shader.CreateIdAttr(tex_id)
            tex_shader.CreateInput("file", Sdf.ValueTypeNames.Asset)
            tex_out = tex_shader.CreateOutput("out", sdf_type)
            
            # Connect the selected input to the texture output
            shader_input.ConnectToSource(tex_out)
            
        self.value_changed.emit()
        self.load_prim(prim)

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
            parts = os.path.normpath(self.file_path).split(os.sep)
            display_path = os.sep.join(parts[-3:]) if len(parts) > 3 else self.file_path
            self.path_label.setText(display_path)
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
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(10)
        
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
        
        self.create_mtl_btn = QPushButton("Create New Material")
        self.create_mtl_btn.setObjectName("PublishButton")
        self.create_mtl_btn.setMinimumHeight(40)
        self.create_mtl_btn.clicked.connect(self.create_material)
        self.mid_layout.addWidget(self.create_mtl_btn)
        
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
                    surface = UsdShade.Shader.Define(self.stage, shd_path)
                    surface.CreateIdAttr("ND_standard_surface_surfaceshader")
                    
                    # Create standard surface outputs
                    surface_output = surface.CreateOutput("surface", Sdf.ValueTypeNames.Token)
                    mtl_output = material.CreateSurfaceOutput(renderContext="mtlx")
                    mtl_output.ConnectToSource(surface_output)

                    # Create promoted inputs on Material and connect Shader to them
                    for ch_name, ch_type in STANDARD_SURFACE_CHANNELS:
                        mtl_in = material.CreateInput(ch_name, ch_type)
                        shd_in = surface.CreateInput(ch_name, ch_type)
                        shd_in.ConnectToSource(mtl_in)

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
            if prim:
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

    def _parse_obj(self, file_path):
        """Simple OBJ parser supporting groups and direct vertex transformation."""
        vertices = []
        obj_normals = []
        current_group = "default"
        groups = {current_group: {"indices": [], "counts": [], "normals": []}}
        
        obj_settings = {"rotation": [0,0,0], "scale": 1.0, "recalc_normals": False}
        if self.settings:
            obj_settings = self.settings.get_obj_import_settings()
        
        rot_values = obj_settings["rotation"]
        scale_mult = obj_settings["scale"]
        recalc_normals = obj_settings["recalc_normals"]
        
        total_mat = Gf.Matrix4d(1.0)
        total_mat *= Gf.Matrix4d().SetScale(Gf.Vec3d(scale_mult, scale_mult, scale_mult))
        total_mat *= Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(1,0,0), rot_values[0]))
        total_mat *= Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0,1,0), rot_values[1]))
        total_mat *= Gf.Matrix4d().SetRotate(Gf.Rotation(Gf.Vec3d(0,0,1), rot_values[2]))

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    parts = line.split()
                    if parts[0] == 'v':
                        p = Gf.Vec3d(float(parts[1]), float(parts[2]), float(parts[3]))
                        vertices.append(Gf.Vec3f(total_mat.Transform(p)))
                    elif parts[0] == 'vn':
                        n = Gf.Vec3d(float(parts[1]), float(parts[2]), float(parts[3]))
                        obj_normals.append(Gf.Vec3f(total_mat.TransformDir(n).GetNormalized()))
                    elif parts[0] == 'g':
                        name = parts[1] if len(parts) > 1 else "group"
                        current_group = Tf.MakeValidIdentifier(name)
                        if current_group not in groups:
                            groups[current_group] = {"indices": [], "counts": [], "normals": []}
                    elif parts[0] == 'f':
                        face_v_indices = []
                        for p in parts[1:]:
                            v_idx = int(p.split('/')[0])
                            face_v_indices.append(v_idx - 1)
                        g_data = groups[current_group]
                        if recalc_normals and len(face_v_indices) >= 3:
                            v0, v1, v2 = vertices[face_v_indices[0]], vertices[face_v_indices[1]], vertices[face_v_indices[2]]
                            g_data["normals"].append(Gf.Cross(v1-v0, v2-v0).GetNormalized())
                        face_v_indices.reverse()
                        g_data["counts"].append(len(face_v_indices))
                        g_data["indices"].extend(face_v_indices)
            
            temp_stage = Usd.Stage.CreateInMemory()
            UsdGeom.Xform.Define(temp_stage, "/main")
            if self.settings:
                UsdGeom.SetStageUpAxis(temp_stage, self.settings.get_up_axis())
                UsdGeom.SetStageMetersPerUnit(temp_stage, self.settings.get_meters_per_unit())

            subdiv_scheme = "catmullClark"
            if self.settings:
                if not self.settings.get_obj_import_settings().get("subdivision", False):
                    subdiv_scheme = "none"

            for group_name, g_data in groups.items():
                if not g_data["indices"]: continue
                mesh = UsdGeom.Mesh.Define(temp_stage, f"/main/{group_name}")
                mesh.CreatePointsAttr(vertices)
                mesh.CreateFaceVertexIndicesAttr(g_data["indices"])
                mesh.CreateFaceVertexCountsAttr(g_data["counts"])
                mesh.CreateOrientationAttr(UsdGeom.Tokens.leftHanded)
                mesh.CreateSubdivisionSchemeAttr(subdiv_scheme)
                if recalc_normals or not obj_normals:
                    if not g_data["normals"]:
                        for i in range(0, len(g_data["indices"]), 3):
                            if i+2 < len(g_data["indices"]):
                                v0, v1, v2 = vertices[g_data["indices"][i]], vertices[g_data["indices"][i+1]], vertices[g_data["indices"][i+2]]
                                g_data["normals"].append(Gf.Cross(v1-v0, v2-v0).GetNormalized())
                    mesh.CreateNormalsAttr(g_data["normals"])
                    mesh.SetNormalsInterpolation(UsdGeom.Tokens.uniform)
                else:
                    mesh.CreateNormalsAttr(obj_normals)
                    mesh.SetNormalsInterpolation(UsdGeom.Tokens.varying)

            temp_stage.SetDefaultPrim(temp_stage.GetPrimAtPath("/main"))
            return UsdUtils.FlattenLayerStack(temp_stage)
        except Exception as e:
            raise e

    def on_file_dropped(self, file_path):
        slot = self.sender()
        if not slot: return
        is_obj = file_path.lower().endswith(".obj")
        try:
            if is_obj:
                source_layer = self._parse_obj(file_path)
                if self.settings and source_layer:
                    obj_settings = self.settings.get_obj_import_settings()
                    if obj_settings.get("preview", True):
                        temp_preview_path = os.path.join(os.environ.get("TEMP", os.getcwd()), "obj_preview.usda")
                        source_layer.Export(temp_preview_path)
                        import subprocess
                        subprocess.Popen(f'usdview "{temp_preview_path}"', shell=True)
            else:
                source_layer = UsdUtils.FlattenLayerStack(Usd.Stage.Open(file_path))
        except Exception as e:
            import traceback; traceback.print_exc()
            QMessageBox.critical(self, "Import Error", f"Could not parse file: {file_path}\n{e}")
            return

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
        if self.settings:
            UsdGeom.SetStageUpAxis(self.stage, self.settings.get_up_axis())
            UsdGeom.SetStageMetersPerUnit(self.stage, self.settings.get_meters_per_unit())
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
                UsdShade.MaterialBindingAPI.Apply(target_prim).Bind(UsdShade.Material(self.stage.GetPrimAtPath(mat_path)))
        self.refresh_outliner()

    def refresh_outliner(self):
        self.outliner.blockSignals(True)
        self.outliner.clear()
        if self.stage:
            main_prim = self.stage.GetPrimAtPath("/main")
            if main_prim: self._add_prim_to_tree(main_prim, self.outliner)
        self.outliner.blockSignals(False)

    def _add_prim_to_tree(self, prim, parent_item):
        name, type_name = prim.GetName(), prim.GetTypeName()
        display_name = f"{name} ({type_name})"
        item = QTreeWidgetItem(parent_item, [display_name])
        item.setData(0, Qt.ItemDataRole.UserRole, str(prim.GetPath()))
        item.setData(0, Qt.ItemDataRole.UserRole + 1, str(type_name))
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        if type_name == "Material": item.setForeground(0, QColor("#00ff99"))
        item.setExpanded(True)
        for child in prim.GetChildren():
            if child.IsValid(): self._add_prim_to_tree(child, item)

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
                    if payload_layer:
                        payload_filename = "payload.usd"
                        payload_layer.Export(os.path.join(slot_dir, payload_filename))
                        temp_stage = Usd.Stage.Open(index_layer)
                        scope_prim = temp_stage.GetPrimAtPath(f"/main/{slot.slot_name}")
                        if scope_prim:
                            scope_prim.GetPayloads().ClearPayloads()
                            scope_prim.GetPayloads().AddPayload(Sdf.Payload(payload_filename, "/main"))
                        temp_stage.GetRootLayer().Export(os.path.join(slot_dir, "index.usda"))
                else:
                    index_layer.Export(os.path.join(slot_dir, "index.usda"))
                final_sublayers.append(f"{clean_name}/index.usda")
            root_stage = Usd.Stage.CreateNew(os.path.join(asset_dir, "index.usda"))
            root_main = root_stage.DefinePrim("/main")
            root_stage.SetDefaultPrim(root_main)
            if self.settings:
                UsdGeom.SetStageUpAxis(root_stage, self.settings.get_up_axis())
                UsdGeom.SetStageMetersPerUnit(root_stage, self.settings.get_meters_per_unit())
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
