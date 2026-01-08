"""
History Dialog

View stock movement history for a specific inventory item.
"""

from typing import List, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client


class HistoryDialog(QDialog):
    """Dialog showing stock movement history for an item."""
    
    def __init__(self, parent=None, item_data: Dict = None):
        super().__init__(parent)
        self.item_data = item_data
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        self.setWindowTitle(f"Movement History: {self.item_data.get('name')}")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        header = QLabel(f"Stock History for {self.item_data.get('sku')}")
        header.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Action", "Qty", "Stock Before", "Stock After"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)
        
        btns = QHBoxLayout()
        btns.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        layout.addLayout(btns)
        
    def _load_data(self):
        try:
            movements = api_client.get_item_movements(self.item_data["id"])
            self.table.setRowCount(0)
            for i, mv in enumerate(movements):
                self.table.insertRow(i)
                
                # Date
                date_str = mv.get("created_at", "").replace("T", " ").split(".")[0]
                self.table.setItem(i, 0, QTableWidgetItem(date_str))
                
                # Type
                mtype = mv.get("movement_type", "").replace("_", " ").title()
                notes = f" ({mv.get('notes')})" if mv.get("notes") else ""
                self.table.setItem(i, 1, QTableWidgetItem(f"{mtype}{notes}"))
                
                # Qty
                qty = mv.get("quantity", 0)
                qty_item = QTableWidgetItem(f"{qty:+.2f}")
                if qty < 0: qty_item.setForeground(Qt.red)
                else: qty_item.setForeground(Qt.green)
                self.table.setItem(i, 2, qty_item)
                
                # Before/After
                self.table.setItem(i, 3, QTableWidgetItem(f"{mv.get('stock_before', 0):.2f}"))
                self.table.setItem(i, 4, QTableWidgetItem(f"{mv.get('stock_after', 0):.2f}"))
                
        except Exception as e:
            print(f"Error loading history: {e}")
