import os
import subprocess
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from app.ui.flow_layout import FlowLayout

class AssetCard(QFrame):
    clicked = Signal(str) # Emits asset path

    def __init__(self, name, asset_path):
        super().__init__()
        self.setObjectName("AssetCard")
        self.setFixedSize(180, 220)
        self.asset_path = asset_path
        self.name = name
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        # Preview placeholder
        self.preview = QLabel()
        self.preview.setObjectName("AssetPreview")
        self.preview.setFixedSize(160, 140)
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setText("PREVIEW")
        
        # Title
        self.title = QLabel(name)
        self.title.setObjectName("AssetTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setWordWrap(True)

        self.layout.addWidget(self.preview)
        self.layout.addWidget(self.title)

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
        self.flow_layout.addWidget(card)

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
