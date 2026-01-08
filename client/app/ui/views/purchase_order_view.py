"""
Purchase Order View

Manage inventory replenishment orders to suppliers.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame, QMessageBox, QMenu,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client
from app.ui.dialogs.purchase_order_dialog import PurchaseOrderDialog


class PurchaseOrderView(QWidget):
    """View showing the purchase order history and management."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.pos = []
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        """Setup the purchase order view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header Section
        header = QHBoxLayout()
        
        left_header = QVBoxLayout()
        title = QLabel("Purchase Orders")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        left_header.addWidget(title)
        
        subtitle = QLabel("Track and manage stock replenishment from suppliers.")
        subtitle.setStyleSheet("color: #888888;")
        left_header.addWidget(subtitle)
        header.addLayout(left_header)
        
        header.addStretch()
        
        self.add_btn = QPushButton(" Create Purchase Order")
        self.add_btn.setObjectName("primary")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_po)
        header.addWidget(self.add_btn)
        
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self._load_data)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Filter Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["All Statuses", "Pending", "Ordered", "Received", "Cancelled"])
        self.status_filter.setMinimumHeight(35)
        self.status_filter.currentIndexChanged.connect(self._load_data)
        filter_bar.addWidget(self.status_filter, 1)
        
        filter_bar.addStretch(2)
        layout.addLayout(filter_bar)
        
        # POs Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Order #", "Supplier", "Created", "Expected", "Amount", "Status", "Actions"
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
        self.stats_label = QLabel("Showing 0 purchase orders")
        self.stats_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.stats_label)
        
    def _load_data(self):
        """Fetch purchase orders from API."""
        try:
            status = self.status_filter.currentText().lower()
            if status == "all statuses":
                status = None
                
            response = api_client.get_purchase_orders(status=status)
            self.pos = response
            self._update_table(self.pos)
        except Exception as e:
            print(f"Error loading purchase orders: {e}")
            self.stats_label.setText("Error loading data")
            
    def _update_table(self, pos):
        """Update the table rows."""
        self.table.setRowCount(0)
        for i, po in enumerate(pos):
            self.table.insertRow(i)
            
            # Order #
            self.table.setItem(i, 0, QTableWidgetItem(po.get("order_number", "")))
            
            # Supplier
            self.table.setItem(i, 1, QTableWidgetItem(po.get("supplier_name", "")))
            
            # Created
            dt_val = po.get("created_at") or ""
            dt_str = dt_val[:10]
            self.table.setItem(i, 2, QTableWidgetItem(dt_str))
            
            # Expected
            exp_val = po.get("expected_date")
            exp_str = exp_val[:10] if exp_val else "TBD"
            self.table.setItem(i, 3, QTableWidgetItem(exp_str))
            
            # Amount
            amount = float(po.get("total_amount") or 0)
            self.table.setItem(i, 4, QTableWidgetItem(f"₦{amount:,.2f}"))
            
            # Status
            status_text = po.get("status", "pending").title()
            status_item = QTableWidgetItem(status_text)
            
            colors = {
                "pending": "#ffd43b",
                "ordered": "#4dabf7",
                "received": "#63e6be",
                "cancelled": "#ff6b6b"
            }
            status_item.setForeground(Qt.black) # Basic black text
            # Use background for better visibility if we had custom styling here
            self.table.setItem(i, 5, status_item)
            
            # Actions
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(8)
            
            view_btn = QPushButton("View")
            view_btn.setMinimumHeight(24)
            view_btn.setFixedWidth(50)
            view_btn.clicked.connect(lambda checked, p=po: self._on_view_po(p))
            
            actions_widget = QWidget()
            actions_widget.setLayout(actions_layout)
            actions_layout.addWidget(view_btn)
            
            if po.get("status") == "pending":
                receive_btn = QPushButton("Receive")
                receive_btn.setMinimumHeight(24)
                receive_btn.setFixedWidth(60)
                receive_btn.setObjectName("success")
                receive_btn.clicked.connect(lambda checked, p=po: self._on_receive_po(p))
                actions_layout.addWidget(receive_btn)
                
            self.table.setCellWidget(i, 6, actions_widget)
            
        self.stats_label.setText(f"Showing {len(pos)} purchase orders")
        
    def _on_add_po(self):
        """Open dialog to create new PO."""
        dialog = PurchaseOrderDialog(self)
        if dialog.exec():
            self._load_data()
        
    def _on_view_po(self, po):
        """View PO details."""
        try:
            full_po = api_client.get_purchase_order(po["id"])
            # TODO: Show details dialog
            msg = f"Order: {full_po['order_number']}\nSupplier: {full_po['supplier']['name']}\nItems: {len(full_po['items'])}"
            QMessageBox.information(self, "PO Details", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load details: {e}")
            
    def _on_receive_po(self, po):
        """Mark PO as received and update stock."""
        reply = QMessageBox.question(
            self, "Confirm Receipt",
            f"Are you sure you want to mark PO '{po['order_number']}' as RECEIVED?\nThis will update inventory stock levels.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                api_client.update_purchase_order(po["id"], {"status": "received"})
                self._load_data()
                QMessageBox.information(self, "Success", "Stock updated successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update: {e}")
