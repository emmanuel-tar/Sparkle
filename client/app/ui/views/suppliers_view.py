"""
Suppliers View

Displays list of suppliers and allows management (CRUD).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client, APIError
from app.ui.dialogs.supplier_dialog import SupplierDialog


class SuppliersView(QWidget):
    """View showing the supplier directory."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.suppliers = []
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        """Setup the suppliers view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header Section
        header = QHBoxLayout()
        
        left_header = QVBoxLayout()
        title = QLabel("Supplier Directory")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        left_header.addWidget(title)
        
        subtitle = QLabel("Manage your vendors and supply chain contacts.")
        subtitle.setStyleSheet("color: #888888;")
        left_header.addWidget(subtitle)
        header.addLayout(left_header)
        
        header.addStretch()
        
        self.add_btn = QPushButton(" Add Supplier")
        self.add_btn.setObjectName("primary")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_supplier)
        
        if not api_client.has_permission("manage_inventory"):
            self.add_btn.setEnabled(False)
            
        header.addWidget(self.add_btn)
        
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self._load_data)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Filter Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Name, Contact, or Email...")
        self.search_input.setMinimumHeight(35)
        self.search_input.textChanged.connect(self._on_search)
        filter_bar.addWidget(self.search_input, 1)
        
        layout.addLayout(filter_bar)
        
        # Suppliers Table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Name", "Contact Person", "Email", "Phone", "Status", "Actions"
        ])
        
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 6):
            header_view.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # Stats Footer
        self.stats_label = QLabel("Showing 0 suppliers")
        self.stats_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.stats_label)
        
    def _load_data(self):
        """Fetch suppliers from API."""
        try:
            response = api_client.get_suppliers()
            self.suppliers = response
            self._update_table(self.suppliers)
        except Exception as e:
            print(f"Error loading suppliers: {e}")
            self.stats_label.setText("Error loading data")
            
    def _update_table(self, suppliers):
        """Update the table rows."""
        self.table.setRowCount(0)
        for i, supplier in enumerate(suppliers):
            self.table.insertRow(i)
            
            # Name
            self.table.setItem(i, 0, QTableWidgetItem(supplier.get("name", "")))
            
            # Contact
            self.table.setItem(i, 1, QTableWidgetItem(supplier.get("contact_name", "N/A")))
            
            # Email
            self.table.setItem(i, 2, QTableWidgetItem(supplier.get("email", "N/A")))
            
            # Phone
            self.table.setItem(i, 3, QTableWidgetItem(supplier.get("phone", "N/A")))
            
            # Status
            status = "Active" if supplier.get("is_active") else "Inactive"
            status_item = QTableWidgetItem(status)
            if supplier.get("is_active"):
                status_item.setForeground(Qt.green)
            else:
                status_item.setForeground(Qt.red)
            self.table.setItem(i, 4, status_item)
            
            # Actions
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(8)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setMinimumHeight(24)
            edit_btn.setFixedWidth(50)
            edit_btn.clicked.connect(lambda checked, s=supplier: self._on_edit_supplier(s))
            
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            actions_layout.addWidget(edit_btn)
            
            if api_client.user_role in ["super_admin", "admin"]:
                del_btn = QPushButton("Delete")
                del_btn.setMinimumHeight(24)
                del_btn.setFixedWidth(60)
                del_btn.setObjectName("danger")
                del_btn.setStyleSheet("color: #ff6b6b;")
                del_btn.clicked.connect(lambda checked, s=supplier: self._on_delete_supplier(s))
                actions_layout.addWidget(del_btn)
                
            self.table.setCellWidget(i, 5, actions_widget)
            
        self.stats_label.setText(f"Showing {len(suppliers)} suppliers")
        
    def _on_search(self):
        """Filter table based on search."""
        query = self.search_input.text().lower()
        if not query:
            self._update_table(self.suppliers)
            return
            
        filtered = [
            s for s in self.suppliers
            if query in s.get("name", "").lower() or 
               query in s.get("contact_name", "").lower() or 
               query in s.get("email", "").lower()
        ]
        self._update_table(filtered)
        
    def _on_add_supplier(self):
        """Open dialog to add supplier."""
        dialog = SupplierDialog(self)
        if dialog.exec():
            self._load_data()
            
    def _on_edit_supplier(self, supplier):
        """Open dialog to edit supplier."""
        dialog = SupplierDialog(self, supplier)
        if dialog.exec():
            self._load_data()
            
    def _on_delete_supplier(self, supplier):
        """Handle supplier deletion (deactivation)."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to deactivate '{supplier['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                api_client.delete_supplier(supplier["id"])
                self._load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
