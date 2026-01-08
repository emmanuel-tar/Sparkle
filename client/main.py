"""
RetailPro ERP Client Application

Entry point for the PySide6 desktop client.
"""

import sys
import os
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette, QColor

from app.config import settings
from app.ui.login_window import LoginWindow


def setup_application() -> QApplication:
    """Configure and create the Qt application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName(settings.APP_NAME)
    app.setApplicationVersion(settings.APP_VERSION)
    app.setOrganizationName("RetailPro")
    app.setOrganizationDomain("retailpro.local")
    
    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Apply dark theme
    apply_dark_theme(app)
    
    return app


def apply_dark_theme(app: QApplication) -> None:
    """Apply modern dark theme to application."""
    palette = QPalette()
    
    # Dark theme colors
    palette.setColor(QPalette.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
    palette.setColor(QPalette.Base, QColor(45, 45, 45))
    palette.setColor(QPalette.AlternateBase, QColor(55, 55, 55))
    palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
    palette.setColor(QPalette.Text, QColor(255, 255, 255))
    palette.setColor(QPalette.Button, QColor(55, 55, 55))
    palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(255, 255, 255))
    
    # Disabled colors
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    
    app.setPalette(palette)
    
    # Additional stylesheet for modern look
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e1e;
        }
        
        QPushButton {
            background-color: #3d3d3d;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 16px;
            min-height: 20px;
        }
        
        QPushButton:hover {
            background-color: #4d4d4d;
            border-color: #666666;
        }
        
        QPushButton:pressed {
            background-color: #2d2d2d;
        }
        
        QPushButton:disabled {
            background-color: #2d2d2d;
            color: #666666;
        }
        
        QPushButton#primary {
            background-color: #2a82da;
            border-color: #2a82da;
        }
        
        QPushButton#primary:hover {
            background-color: #3a92ea;
        }
        
        QPushButton#success {
            background-color: #28a745;
            border-color: #28a745;
        }
        
        QPushButton#danger {
            background-color: #dc3545;
            border-color: #dc3545;
        }
        
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px;
            selection-background-color: #2a82da;
        }
        
        QLineEdit:focus, QTextEdit:focus {
            border-color: #2a82da;
        }
        
        QComboBox {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px;
        }
        
        QComboBox::drop-down {
            border: none;
            padding-right: 8px;
        }
        
        QTableWidget {
            background-color: #2d2d2d;
            border: 1px solid #555555;
            border-radius: 6px;
            gridline-color: #404040;
        }
        
        QTableWidget::item {
            padding: 8px;
        }
        
        QTableWidget::item:selected {
            background-color: #2a82da;
        }
        
        QHeaderView::section {
            background-color: #3d3d3d;
            padding: 8px;
            border: none;
            border-bottom: 1px solid #555555;
        }
        
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 30px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 12px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 4px;
        }
        
        QLabel#title {
            font-size: 24px;
            font-weight: bold;
        }
        
        QLabel#subtitle {
            font-size: 14px;
            color: #888888;
        }
        
        QFrame#card {
            background-color: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 8px;
            padding: 16px;
        }
        
        QFrame#sidebar {
            background-color: #252525;
            border-right: 1px solid #404040;
        }
    """)


def main() -> int:
    """Main entry point."""
    # Create application
    app = setup_application()
    
    # Show login window
    login_window = LoginWindow()
    login_window.show()
    
    # Run event loop
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
