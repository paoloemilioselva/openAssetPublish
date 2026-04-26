import sys
import os
from PySide6.QtWidgets import QApplication
from app.ui.main_window import MainWindow

def load_stylesheet(app, stylesheet_path):
    if os.path.exists(stylesheet_path):
        with open(stylesheet_path, "r") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: Stylesheet not found at {stylesheet_path}")

def main():
    print("DEBUG: main() started")
    try:
        print("DEBUG: Initializing QApplication")
        app = QApplication(sys.argv)
        
        # Set application metadata
        app.setApplicationName("Open Asset Publish")
        app.setOrganizationName("OpenAsset")

        # Load and apply the stylesheet
        style_path = os.path.join(os.path.dirname(__file__), "app", "styles", "style.qss")
        print(f"DEBUG: Loading stylesheet from {style_path}")
        load_stylesheet(app, style_path)

        # Create and show the main window
        print("DEBUG: Creating MainWindow")
        window = MainWindow()
        print("DEBUG: Showing MainWindow")
        window.show()

        # Exit the application
        print("DEBUG: Entering app.exec()")
        sys.exit(app.exec())
    except Exception as e:
        print(f"DEBUG: Exception caught: {e}")
        import traceback
        traceback.print_exc()
        # Non-blocking check for input if possible, or just print
        print("DEBUG: Press Enter to exit if in a terminal...")

if __name__ == "__main__":
    main()
