"""
Low Stock Alerts View

Displays items that are below their reorder point.
"""

import uuid
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client
from app.ui.dialogs.purchase_order_dialog import PurchaseOrderDialog


class LowStockView(QWidget):
    """View showing items with low stock levels."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.items = []
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        """Setup the low stock view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header Section
        header = QHBoxLayout()
        
        left_header = QVBoxLayout()
        title = QLabel("Low Stock Alerts")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        left_header.addWidget(title)
        
        subtitle = QLabel("Items that have reached or dropped below their reorder point.")
        subtitle.setStyleSheet("color: #888888;")
        left_header.addWidget(subtitle)
        header.addLayout(left_header)
        
        header.addStretch()
        
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self._load_data)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Alerts Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "SKU", "Product Name", "Supplier", "Current Stock", "Reorder Point", "Unit", "Actions"
        ])
        
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in [0, 2, 3, 4, 5, 6]:
            header_view.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # Stats Footer
        self.stats_label = QLabel("0 items require attention")
        self.stats_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        layout.addWidget(self.stats_label)
        
    def _load_data(self):
        """Fetch low stock items from API."""
        try:
            # We use the generic get_items with is_low_stock filter if supported, 
            # or dedicated method we added to client
            response = api_client.get_low_stock_items()
            self.items = response
            self._update_table(self.items)
        except Exception as e:
            print(f"Error loading low stock items: {e}")
            self.stats_label.setText("Error loading data")
            
    def _update_table(self, items):
        """Update the table rows."""
        self.table.setRowCount(0)
        for i, item in enumerate(items):
            self.table.insertRow(i)
            
            # SKU
            self.table.setItem(i, 0, QTableWidgetItem(item.get("sku", "")))
            
            # Name
            self.table.setItem(i, 1, QTableWidgetItem(item.get("name", "")))
            
            # Supplier
            supplier = item.get("supplier", {})
            supplier_name = supplier.get("name", "No Supplier") if supplier else "No Supplier"
            self.table.setItem(i, 2, QTableWidgetItem(supplier_name))
            
            # Current Stock
            stock = float(item.get("current_stock") or 0)
            stock_item = QTableWidgetItem(f"{stock:.2f}")
            stock_item.setForeground(Qt.red if stock <= 0 else Qt.yellow)
            stock_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, stock_item)
            
            # Reorder Point
            rp = float(item.get("reorder_point") or 0)
            rp_item = QTableWidgetItem(f"{rp:.2f}")
            rp_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 4, rp_item)
            
            # Unit
            self.table.setItem(i, 5, QTableWidgetItem(item.get("unit", "pcs")))
            
            # Actions
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(8)
            
            po_btn = QPushButton("Add to PO")
            po_btn.setMinimumHeight(24)
            po_btn.setFixedWidth(80)
            po_btn.setObjectName("primary")
            po_btn.setToolTip(f"Create a purchase order for {supplier_name}")
            po_btn.clicked.connect(lambda checked, itm=item: self._on_add_to_po(itm))
            
            # Disable if no supplier
            if not item.get("supplier_id"):
                po_btn.setEnabled(False)
            
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            actions_layout.addWidget(po_btn)
            actions_layout.addStretch()
            
            self.table.setCellWidget(i, 6, actions_widget)
            
        self.stats_label.setText(f"{len(items)} items require attention")
        if len(items) == 0:
            self.stats_label.setStyleSheet("color: #28a745; font-weight: bold;")
            self.stats_label.setText("Inventory levels are healthy")
        else:
            self.stats_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")

    def _on_add_to_po(self, item):
        """Open PO dialog and add this item to it."""
        dialog = PurchaseOrderDialog(self)
        # Manually add the item to the order list in the dialog
        dialog._add_item_to_table({
            "item_id": item["id"],
            "name": item["name"],
            "quantity": item.get("reorder_quantity") or 10,
            "unit_cost": item.get("cost_price") or 0
        })
        # Pre-select the supplier
        if item.get("supplier_id"):
            index = dialog.supplier_combo.findData(uuid.UUID(item["supplier_id"]) if isinstance(item["supplier_id"], str) else item["supplier_id"])
            if index >= 0:
                dialog.supplier_combo.setCurrentIndex(index)
        
        if dialog.exec():
            self._load_data()
