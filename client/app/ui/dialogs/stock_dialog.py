"""
Stock Adjustment Dialog

Modal for adding/subtracting stock or correcting inventory levels.
"""

from typing import Optional, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QTextEdit, 
    QFormLayout, QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client, APIError


class StockDialog(QDialog):
    """Dialog for adjusting stock levels."""
    
    def __init__(self, parent=None, product: Dict = None):
        super().__init__(parent)
        self.product = product
        self._setup_ui()
        
    def _setup_ui(self):
        self.setWindowTitle(f"Adjust Stock: {self.product.get('name')}")
        self.setFixedWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Current Stock info
        info_layout = QHBoxLayout()
        current = self.product.get('current_stock', 0)
        info_label = QLabel(f"Current Stock: <b>{current} {self.product.get('unit')}</b>")
        info_layout.addWidget(info_label)
        layout.addLayout(info_layout)
        
        form = QFormLayout()
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Restock", "Adjustment", "Damage", "Return", "Stocktake"])
        # Map to MovementType enum
        self.movement_map = {
            "Restock": "receive",
            "Adjustment": "adjustment",
            "Damage": "damage",
            "Return": "return",
            "Stocktake": "stocktake"
        }
        form.addRow("Type:", self.type_combo)
        
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(-10000, 10000)
        self.quantity_spin.setToolTip("Positive to add, negative to subtract")
        form.addRow("Quantity (+/-):", self.quantity_spin)
        
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setPlaceholderText("Optional notes about this adjustment")
        form.addRow("Notes:", self.notes_input)
        
        layout.addLayout(form)
        
        btns = QHBoxLayout()
        btns.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Apply Adjustment")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._on_save)
        btns.addWidget(self.save_btn)
        layout.addLayout(btns)
        
    def _on_save(self):
        qty = self.quantity_spin.value()
        if qty == 0:
            QMessageBox.warning(self, "Invalid Quantity", "Quantity must be non-zero.")
            return
            
        data = {
            "item_id": self.product["id"],
            "quantity": qty,
            "movement_type": self.movement_map[self.type_combo.currentText()],
            "notes": self.notes_input.toPlainText().strip() or None,
            "unit_cost": self.product.get("cost_price", 0)
        }
        
        try:
            api_client.post(f"inventory/items/{self.product['id']}/adjust", data)
            self.accept()
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to adjust stock: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
