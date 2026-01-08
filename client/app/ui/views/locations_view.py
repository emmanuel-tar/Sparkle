"""
Locations View

Dashboard for managing warehouses and store branches.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client, APIError
from app.ui.dialogs.location_dialog import LocationDialog


class LocationsView(QWidget):
    """View showing all physical store/warehouse locations."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.locations = []
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Locations & Warehouses")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        
        self.add_btn = QPushButton(" Add Location")
        self.add_btn.setObjectName("primary")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.clicked.connect(self._on_add_location)
        
        is_admin = api_client.user_role in ["super_admin", "admin"]
        if not is_admin:
            self.add_btn.setEnabled(False)
            self.add_btn.setToolTip("Only admins can manage locations")
            
        header.addWidget(self.add_btn)
        
        layout.addLayout(header)
        
        # Stats summary (Quick view)
        stats_layout = QHBoxLayout()
        self.total_label = QLabel("Total: 0")
        self.total_label.setStyleSheet("padding: 10px; background: #2d2d2d; border-radius: 5px;")
        stats_layout.addWidget(self.total_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Name", "Code", "Type", "Contact", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)
        
    def _load_data(self):
        """Fetch locations from API."""
        try:
            self.locations = api_client.get_locations()
            self._update_table()
            self.total_label.setText(f"Total: {len(self.locations)}")
        except Exception as e:
            print(f"Error loading locations: {e}")
            
    def _update_table(self):
        """Populate the locations table."""
        self.table.setRowCount(0)
        for i, loc in enumerate(self.locations):
            self.table.insertRow(i)
            
            # Name
            self.table.setItem(i, 0, QTableWidgetItem(loc.get("name", "")))
            
            # Code
            code_item = QTableWidgetItem(loc.get("code", ""))
            code_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, code_item)
            
            # Type
            is_hq = loc.get("is_headquarters", False)
            type_text = "🏢 HQ" if is_hq else "🏬 Branch"
            self.table.setItem(i, 2, QTableWidgetItem(type_text))
            
            # Contact
            contact = loc.get("phone") or loc.get("email") or "No contact"
            self.table.setItem(i, 3, QTableWidgetItem(contact))
            
            # Actions
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(2, 2, 2, 2)
            
            is_admin = api_client.user_role in ["super_admin", "admin"]
            
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedWidth(50)
            edit_btn.setStyleSheet("font-size: 10px;")
            edit_btn.setEnabled(is_admin)
            edit_btn.clicked.connect(lambda checked, l=loc: self._on_edit_location(l))
            
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            actions_layout.addWidget(edit_btn)
            actions_layout.addStretch()
            
            self.table.setCellWidget(i, 4, actions_widget)
            
    def _on_add_location(self):
        """Show add location dialog."""
        dialog = LocationDialog(self)
        if dialog.exec():
            self._load_data()
            
    def _on_edit_location(self, loc):
        """Show edit location dialog."""
        dialog = LocationDialog(self, loc)
        if dialog.exec():
            self._load_data()
