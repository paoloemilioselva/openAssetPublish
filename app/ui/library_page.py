import os
import shutil
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea,
    QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QKeyEvent, QKeySequence
from app.ui.flow_layout import FlowLayout

class AssetCard(QFrame):
    clicked = Signal(str) # Emits asset path
    selected = Signal(object) # Emits self

    def __init__(self, name, asset_path):
        super().__init__()
        self.setObjectName("AssetCard")
        self.setFixedSize(180, 220)
        self.asset_path = asset_path
        self.name = name
        self.setAcceptDrops(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._is_selected = False
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # Preview placeholder
        self.preview = QLabel()
        self.preview.setObjectName("AssetPreview")
        self.preview.setFixedSize(160, 140)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Look for existing preview
        self.update_preview_from_folder()
        
        # Title
        self.title = QLabel(name)
        self.title.setObjectName("AssetTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)

        self.layout.addWidget(self.preview)
        self.layout.addWidget(self.title)

    def update_preview_from_folder(self):
        found = False
        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
            preview_path = os.path.join(self.asset_path, f"preview{ext}")
            if os.path.exists(preview_path):
                pixmap = QPixmap(preview_path)
                if not pixmap.isNull():
                    self.preview.setPixmap(pixmap.scaled(
                        self.preview.size(), 
                        Qt.AspectRatioMode.KeepAspectRatio, 
                        Qt.TransformationMode.SmoothTransformation
                    ))
                    self.preview.setText("")
                    found = True
                    break
        if not found:
            self.preview.setText("PREVIEW")
            self.preview.setPixmap(QPixmap())

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            # Check if any URL is an image
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls:
            image_path = urls[0].toLocalFile()
            ext = os.path.splitext(image_path)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".webp"]:
                # Save to asset folder
                target_path = os.path.join(self.asset_path, f"preview{ext}")
                try:
                    # Remove other preview extensions first to avoid multiple previews
                    for other_ext in [".png", ".jpg", ".jpeg", ".webp"]:
                        other_path = os.path.join(self.asset_path, f"preview{other_ext}")
                        if os.path.exists(other_path):
                            os.remove(other_path)
                    
                    shutil.copy2(image_path, target_path)
                    self.update_preview_from_folder()
                    event.acceptProposedAction()
                except Exception as e:
                    print(f"Failed to save preview: {e}")

    def mousePressEvent(self, event):
        self.setFocus()
        self.selected.emit(self)
        super().mousePressEvent(event)

    def set_selected(self, selected):
        self._is_selected = selected
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def keyPressEvent(self, event: QKeyEvent):
        if event.matches(QKeySequence.StandardKey.Paste):
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            
            if mime_data.hasImage():
                image = clipboard.image()
                if not image.isNull():
                    target_path = os.path.join(self.asset_path, "preview.png")
                    try:
                        # Clear existing previews
                        for ext in [".png", ".jpg", ".jpeg", ".webp"]:
                            old_path = os.path.join(self.asset_path, f"preview{ext}")
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        
                        if image.save(target_path, "PNG"):
                            self.update_preview_from_folder()
                    except Exception as e:
                        print(f"Failed to paste preview: {e}")
            elif mime_data.hasUrls():
                # Handle file paste if it's an image
                for url in mime_data.urls():
                    path = url.toLocalFile()
                    if path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                        ext = os.path.splitext(path)[1].lower()
                        target_path = os.path.join(self.asset_path, f"preview{ext}")
                        try:
                            for e in [".png", ".jpg", ".jpeg", ".webp"]:
                                old_p = os.path.join(self.asset_path, f"preview{e}")
                                if os.path.exists(old_p): os.remove(old_p)
                            shutil.copy2(path, target_path)
                            self.update_preview_from_folder()
                            break
                        except Exception as e:
                            print(f"Failed to paste preview file: {e}")
        else:
            super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.asset_path)

class LibraryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setObjectName("LibraryScrollArea")
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.container = QWidget()
        self.flow_layout = FlowLayout(self.container, spacing=20)
        
        self.scroll_area.setWidget(self.container)
        self.main_layout.addWidget(self.scroll_area)

    def refresh_library(self, library_root):
        """Clears the current library and populates it from the library_root directory, sorted by creation time."""
        while self.flow_layout.count():
            item = self.flow_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not os.path.exists(library_root):
            return

        assets = []
        for item_name in os.listdir(library_root):
            item_path = os.path.join(library_root, item_name)
            if os.path.isdir(item_path):
                index_path = os.path.join(item_path, "index.usda")
                if os.path.exists(index_path):
                    # Store tuple of (name, path, creation_time)
                    assets.append((item_name, item_path, os.path.getctime(item_path)))

        # Sort by creation time (index 2) descending
        assets.sort(key=lambda x: x[2], reverse=True)

        for name, path, _ in assets:
            self.add_asset(name, path)

    def add_asset(self, name, asset_path):
        card = AssetCard(name, asset_path)
        card.clicked.connect(self.launch_usdview)
        card.selected.connect(self.on_card_selected)
        self.flow_layout.addWidget(card)

    def on_card_selected(self, selected_card):
        for i in range(self.flow_layout.count()):
            widget = self.flow_layout.itemAt(i).widget()
            if isinstance(widget, AssetCard):
                widget.set_selected(widget == selected_card)

    def launch_usdview(self, asset_path):
        index_path = os.path.normpath(os.path.join(asset_path, "index.usda"))
        if os.path.exists(index_path):
            print(f"Launching usdview for: {index_path}")
            # On Windows, shell=True is often needed to find commands in the PATH,
            # but we should handle it carefully.
            try:
                # Use a string command for better shell interpretation on Windows
                cmd = f'usdview "{index_path}"'
                subprocess.Popen(cmd, shell=True)
            except Exception as e:
                print(f"Failed to launch usdview: {e}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Launch Error", f"Could not launch usdview:\n{str(e)}")
