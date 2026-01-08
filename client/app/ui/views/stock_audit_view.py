"""
Stock Audit View

Displays a global log of all inventory movements (adjustments, sales, etc.)
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSpacerItem, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client


class StockAuditView(QWidget):
    """View showing system-wide stock movement audit trail."""
    
    def __init__(self, user: dict = None):
        super().__init__()
        self.user = user
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Stock Movement Audit")
        title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        header.addWidget(title)
        
        header.addStretch()
        
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self._load_data)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Table Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Date", "SKU", "Product", "Action", "Qty", "Stock Before", "Stock After"
        ])
        
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header_view.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        card_layout.addWidget(self.table)
        layout.addWidget(card)
        
    def _load_data(self):
        """Fetch movement data from API."""
        try:
            movements = api_client.get_all_movements()
            self.table.setRowCount(0)
            
            for i, mv in enumerate(movements):
                self.table.insertRow(i)
                
                # Date
                date_str = mv.get("created_at", "").replace("T", " ").split(".")[0]
                self.table.setItem(i, 0, QTableWidgetItem(date_str))
                
                # SKU
                self.table.setItem(i, 1, QTableWidgetItem(mv.get("item_sku", "N/A")))
                
                # Name
                self.table.setItem(i, 2, QTableWidgetItem(mv.get("item_name", "Unknown")))
                
                # Type/Action
                mtype = mv.get("movement_type", "").replace("_", " ").title()
                notes = f" ({mv.get('notes')})" if mv.get('notes') else ""
                self.table.setItem(i, 3, QTableWidgetItem(f"{mtype}{notes}"))
                
                # Qty
                qty = mv.get("quantity", 0)
                qty_item = QTableWidgetItem(f"{qty:+.2f}")
                if qty < 0:
                    qty_item.setForeground(Qt.red)
                else:
                    qty_item.setForeground(Qt.green)
                self.table.setItem(i, 4, qty_item)
                
                # Stock Levels
                self.table.setItem(i, 5, QTableWidgetItem(f"{mv.get('stock_before', 0):.2f}"))
                self.table.setItem(i, 6, QTableWidgetItem(f"{mv.get('stock_after', 0):.2f}"))
                
        except Exception as e:
            print(f"Error loading stock audit: {e}")
