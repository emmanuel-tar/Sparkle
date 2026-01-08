"""
Main Window

Primary application window with sidebar navigation and content views.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QSpacerItem, QSizePolicy,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from app.config import settings
from app.api import api_client


class SidebarButton(QPushButton):
    """Custom sidebar navigation button."""
    
    def __init__(self, text: str, icon_text: str = ""):
        super().__init__(f"  {icon_text}  {text}" if icon_text else f"  {text}")
        self.setCheckable(True)
        self.setMinimumHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding-left: 16px;
                border: none;
                border-radius: 0;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:checked {
                background-color: #2a82da;
                border-left: 3px solid #4aa3ff;
            }
        """)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the main window UI."""
        self.setWindowTitle(f"{settings.APP_NAME} - {self.user.get('first_name', 'User')}")
        self.setMinimumSize(1280, 720)
        self.showMaximized()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Content area
        content_area = self._create_content_area()
        main_layout.addWidget(content_area, 1)
    
    def _create_sidebar(self) -> QFrame:
        """Create sidebar with navigation."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet("background-color: #1a1a1a; border-bottom: 1px solid #404040;")
        header_layout = QHBoxLayout(header)
        
        title = QLabel(settings.APP_NAME)
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header_layout.addWidget(title)
        
        layout.addWidget(header)
        
        # Navigation buttons
        self.nav_buttons = []
        
        # Navigation items grouped by category
        nav_groups = [
            ("OPERATIONS", [
                ("POS", "🛒"),
                ("Sales History", "📊"),
            ]),
            ("CATALOG", [
                ("Inventory", "📦"),
                ("Categories", "🏷️"),
            ]),
            ("PARTNERS", [
                ("Customers", "👥"),
                ("Suppliers", "🏢"),
            ]),
            ("ADMINISTRATION", [
                ("Locations", "🏢"),
                ("Purchase Orders", "📋"),
                ("Reports", "📈"),
                ("Settings", "⚙️"),
            ]),
        ]
        
        for group_name, items in nav_groups:
            # Group header
            group_label = QLabel(group_name)
            group_label.setStyleSheet("color: #555555; padding: 12px 16px 4px 16px; font-weight: bold; font-size: 10px;")
            layout.addWidget(group_label)
            
            for text, icon in items:
                btn = SidebarButton(text, icon)
                btn.clicked.connect(lambda checked, t=text: self._on_nav_click(t))
                self.nav_buttons.append(btn)
                layout.addWidget(btn)
        
        # Set first button as active
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)
        
        # Spacer
        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # User info
        user_frame = QFrame()
        user_frame.setStyleSheet("background-color: #1a1a1a; border-top: 1px solid #404040;")
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(12, 12, 12, 12)
        
        user_name = QLabel(f"{self.user.get('first_name', '')} {self.user.get('last_name', '')}")
        user_name.setFont(QFont("Segoe UI", 10, QFont.Bold))
        user_layout.addWidget(user_name)
        
        user_role = QLabel(self.user.get("role", "user").replace("_", " ").title())
        user_role.setStyleSheet("color: #888888; font-size: 11px;")
        user_layout.addWidget(user_role)
        
        logout_btn = QPushButton(" Logout")
        logout_btn.setIcon(QIcon.fromTheme("application-exit")) # Fallback to text if theme icon fails
        logout_btn.setObjectName("danger")
        logout_btn.setStyleSheet("""
            QPushButton#danger {
                background-color: #3d1010;
                color: #ff6b6b;
                border: 1px solid #5d1a1a;
                border-radius: 4px;
                padding: 6px;
                margin-top: 8px;
            }
            QPushButton#danger:hover {
                background-color: #5d1a1a;
            }
        """)
        logout_btn.clicked.connect(self._on_logout)
        user_layout.addWidget(logout_btn)
        
        layout.addWidget(user_frame)
        
        return sidebar
    
    def _create_content_area(self) -> QFrame:
        """Create main content area with stacked views."""
        content = QFrame()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top bar
        top_bar = self._create_top_bar()
        layout.addWidget(top_bar)
        
        # Stacked widget for views
        self.stack = QStackedWidget()
        
        # Add views
        from app.ui.views.pos_view import POSView
        from app.ui.views.inventory_view import InventoryView
        from app.ui.views.customers_view import CustomersView
        from app.ui.views.sales_history_view import SalesHistoryView
        from app.ui.views.placeholder_view import PlaceholderView
        
        # We'll map view names to their stack index
        self.view_map = {
            "POS": 0,
            "Sales History": 1,
            "Inventory": 2,
            "Categories": 3,
            "Customers": 4,
            "Suppliers": 5,
            "Locations": 6,
            "Purchase Orders": 7,
            "Reports": 8,
            "Settings": 9,
        }
        
        # Add views in order of mapping
        self.pos_view = POSView(self.user)
        self.stack.addWidget(self.pos_view) # Index 0
        
        self.sales_history_view = SalesHistoryView(self.user)
        self.stack.addWidget(self.sales_history_view) # Index 1
        
        self.inventory_view = InventoryView(self.user)
        self.stack.addWidget(self.inventory_view) # Index 2
        
        from app.ui.views.categories_view import CategoriesView
        self.categories_view = CategoriesView(self.user)
        self.stack.addWidget(self.categories_view) # Index 3
        
        self.customers_view = CustomersView(self.user)
        self.stack.addWidget(self.customers_view) # Index 4
        
        # Suppliers placeholder
        self.stack.addWidget(PlaceholderView("Suppliers")) # Index 5
        
        from app.ui.views.locations_view import LocationsView
        self.locations_view = LocationsView(self.user)
        self.stack.addWidget(self.locations_view) # Index 6
        
        # Remaining placeholders
        self.stack.addWidget(PlaceholderView("Purchase Orders")) # Index 7
        self.stack.addWidget(PlaceholderView("Reports")) # Index 8
        self.stack.addWidget(PlaceholderView("Settings")) # Index 9
        
        layout.addWidget(self.stack, 1)
        
        return content
    
    def _create_top_bar(self) -> QFrame:
        """Create top navigation bar."""
        bar = QFrame()
        bar.setFixedHeight(50)
        bar.setStyleSheet("background-color: #252525; border-bottom: 1px solid #404040;")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        
        # Current view title
        self.view_title = QLabel("Point of Sale")
        self.view_title.setFont(QFont("Segoe UI", 13, QFont.Bold))
        layout.addWidget(self.view_title)
        
        layout.addStretch()
        
        # Connection status
        self.status_label = QLabel("● Online")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        return bar
    
    def _on_nav_click(self, view_name: str):
        """Handle navigation button click."""
        # Update button states
        for btn in self.nav_buttons:
            btn.setChecked(view_name in btn.text())
        
        # Update view title
        self.view_title.setText(view_name)
        
        # Switch view
        index = self.view_map.get(view_name, 0)
        self.stack.setCurrentIndex(index)
    
    def _on_logout(self):
        """Handle logout."""
        reply = QMessageBox.question(
            self,
            "Confirm Logout",
            "Are you sure you want to logout?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        
        if reply == QMessageBox.Yes:
            api_client.logout()
            
            from app.ui.login_window import LoginWindow
            self.login_window = LoginWindow()
            self.login_window.show()
            self.close()
    
    def closeEvent(self, event):
        """Handle window close."""
        api_client.close()
        event.accept()
