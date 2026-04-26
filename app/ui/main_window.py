import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget
)
from PySide6.QtCore import Qt
from app.ui.publish_page import PublishPage
from app.ui.library_page import LibraryPage
from app.ui.settings_page import SettingsPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Open Asset Publish")
        self.resize(1000, 600)

        # Central widget and layout
        self.central_widget = QWidget()
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.sidebar_layout.setContentsMargins(0, 20, 0, 20)
        self.sidebar_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Content area
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("ContentArea")

        # Sidebar navigation buttons
        self.nav_items = ["Dashboard", "Library", "Publish", "Settings"]
        self.buttons = []
        self.pages = {}

        # Initialize core pages first
        self.settings_page = SettingsPage()
        self.library_page = LibraryPage()
        self.publish_page = PublishPage()
        
        # Initial library population
        self.library_page.refresh_library(self.settings_page.get_library_path())
        
        # Give publish page a way to get the library path
        self.publish_page.set_settings(self.settings_page)

        for item in self.nav_items:
            btn = QPushButton(item)
            btn.setObjectName("SidebarButton")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=item: self.switch_page(i))
            self.sidebar_layout.addWidget(btn)
            self.buttons.append(btn)
            
            # Map pages
            if item == "Publish":
                page = self.publish_page
            elif item == "Library":
                page = self.library_page
            elif item == "Settings":
                page = self.settings_page
            else:
                # Create a simple page for other items
                page = QWidget()
                page_layout = QVBoxLayout(page)
                label = QLabel(f"Welcome to the {item} page!")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setStyleSheet("font-size: 24px;")
                page_layout.addWidget(label)
            
            self.pages[item] = page
            self.content_stack.addWidget(page)

        # Connect Signals
        self.publish_page.publish_requested.connect(self.on_asset_published)
        self.settings_page.library_path_changed.connect(self.library_page.refresh_library)
        self.settings_page.slots_changed.connect(self.publish_page.rebuild_slots)

        # Set initial button state
        if self.buttons:
            self.buttons[0].setChecked(True)

        self.main_layout.addWidget(self.sidebar)
        self.main_layout.addWidget(self.content_stack)

    def on_asset_published(self, name):
        """Called when an asset is published."""
        lib_path = self.settings_page.get_library_path()
        asset_path = os.path.join(lib_path, name)
        self.library_page.add_asset(name, asset_path)

    def switch_page(self, page_name):
        # Uncheck other buttons
        for btn in self.buttons:
            if btn.text() != page_name:
                btn.setChecked(False)
            else:
                btn.setChecked(True)
        
        # Switch the stacked widget index
        index = self.nav_items.index(page_name)
        self.content_stack.setCurrentIndex(index)
        
        # Refresh library when switching to it, to ensure it's up to date
        if page_name == "Library":
            self.library_page.refresh_library(self.settings_page.get_library_path())
