"""
Purchase Order Dialog

Modal for creating or viewing detailed purchase orders.
"""

import uuid
from typing import Optional, Dict, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QTextEdit, 
    QFormLayout, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client, APIError


class PurchaseOrderDialog(QDialog):
    """Dialog for creating and managing purchase orders."""
    
    def __init__(self, parent=None, po: Optional[Dict] = None):
        super().__init__(parent)
        self.po = po
        self.suppliers = []
        self.items_to_order = [] # List of dicts with item_id, name, qty, cost
        self._setup_ui()
        self._load_suppliers()
        
        if self.po:
            self._load_po_details()
            
    def _setup_ui(self):
        self.setWindowTitle("Create Purchase Order" if not self.po else f"Purchase Order: {self.po['order_number']}")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header Info
        top_frame = QFrame()
        top_frame.setObjectName("card")
        top_layout = QFormLayout(top_frame)
        
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("Select Supplier...", None)
        self.supplier_combo.currentIndexChanged.connect(self._on_supplier_changed)
        top_layout.addRow("Supplier:", self.supplier_combo)
        
        self.order_num_input = QLineEdit()
        self.order_num_input.setPlaceholderText("PO-YYYYMMDD-XXX")
        # Auto-generate dummy number
        import datetime
        now = datetime.datetime.now()
        self.order_num_input.setText(f"PO-{now.strftime('%Y%m%d%H%M%S')}")
        top_layout.addRow("Order Number:", self.order_num_input)
        
        layout.addWidget(top_frame)
        
        # Items Table
        items_header = QHBoxLayout()
        items_header.addWidget(QLabel("<b>Order Items</b>"))
        items_header.addStretch()
        
        self.suggest_btn = QPushButton("✨ Suggest Low Stock")
        self.suggest_btn.clicked.connect(self._on_suggest)
        self.suggest_btn.setEnabled(False)
        items_header.addWidget(self.suggest_btn)
        
        layout.addLayout(items_header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Product", "Qty", "Unit Cost", "Total", "Action"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)
        
        # Footer
        footer = QHBoxLayout()
        
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes / Terms...")
        self.notes_input.setMaximumHeight(60)
        footer.addWidget(self.notes_input, 1)
        
        summary_layout = QVBoxLayout()
        self.total_label = QLabel("Total: ₦0.00")
        self.total_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        summary_layout.addWidget(self.total_label)
        footer.addLayout(summary_layout)
        
        layout.addLayout(footer)
        
        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save & Submit")
        self.save_btn.setObjectName("primary")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self._on_save)
        btns.addWidget(self.save_btn)
        layout.addLayout(btns)
        
    def _load_suppliers(self):
        """Fetch suppliers for dropdown."""
        try:
            self.suppliers = api_client.get_suppliers()
            self.supplier_combo.blockSignals(True)
            for s in self.suppliers:
                self.supplier_combo.addItem(s["name"], s["id"])
            self.supplier_combo.blockSignals(False)
        except Exception as e:
            print(f"Error loading suppliers: {e}")
            
    def _on_supplier_changed(self):
        supplier_id = self.supplier_combo.currentData()
        self.suggest_btn.setEnabled(bool(supplier_id))
        
    def _on_suggest(self):
        supplier_id = self.supplier_combo.currentData()
        if not supplier_id: return
        
        try:
            suggestions = api_client.get_suggested_po_items(supplier_id)
            # Fetch item names for display (this is a bit inefficient without a bulk API, but let's try)
            for sug in suggestions:
                item = api_client.get(f"inventory/items/{sug['item_id']}")
                self._add_item_to_table({
                    "item_id": sug["item_id"],
                    "name": item.get("name", "Unknown"),
                    "quantity": sug["quantity"],
                    "unit_cost": sug["unit_cost"]
                })
            self._update_total()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get suggestions: {e}")
            
    def _add_item_to_table(self, item_data):
        # Check if already in list
        for existing in self.items_to_order:
            if existing["item_id"] == item_data["item_id"]:
                return
                
        row = self.table.rowCount()
        self.table.insertRow(row)
        
        self.table.setItem(row, 0, QTableWidgetItem(item_data["name"]))
        
        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0.001, 1000000)
        qty_spin.setValue(item_data["quantity"])
        qty_spin.valueChanged.connect(self._update_total)
        self.table.setCellWidget(row, 1, qty_spin)
        
        cost_spin = QDoubleSpinBox()
        cost_spin.setRange(0, 10000000)
        cost_spin.setValue(float(item_data.get("unit_cost") or 0))
        cost_spin.valueChanged.connect(self._update_total)
        self.table.setCellWidget(row, 2, cost_spin)
        
        total_item_label = QLabel("₦0.00")
        self.table.setCellWidget(row, 3, total_item_label)
        
        del_btn = QPushButton("🗑️")
        del_btn.setFixedWidth(30)
        del_btn.clicked.connect(lambda: self._remove_row(row))
        self.table.setCellWidget(row, 4, del_btn)
        
        self.items_to_order.append(item_data)
        self._update_total()
        
    def _remove_row(self, row_idx):
        self.table.removeRow(row_idx)
        self.items_to_order.pop(row_idx)
        self._update_total()
        
    def _update_total(self):
        total = 0
        for i in range(self.table.rowCount()):
            qty = self.table.cellWidget(i, 1).value()
            cost = self.table.cellWidget(i, 2).value()
            row_total = qty * cost
            total += row_total
            self.table.cellWidget(i, 3).setText(f"₦{row_total:,.2f}")
            
        self.total_label.setText(f"Total: ₦{total:,.2f}")
        
    def _on_save(self):
        supplier_id = self.supplier_combo.currentData()
        if not supplier_id:
            QMessageBox.warning(self, "Validation Error", "Please select a supplier.")
            return
            
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Validation Error", "Please add at least one item to the order.")
            return
            
        items = []
        for i in range(self.table.rowCount()):
            items.append({
                "item_id": self.items_to_order[i]["item_id"],
                "quantity": self.table.cellWidget(i, 1).value(),
                "unit_cost": self.table.cellWidget(i, 2).value()
            })
            
        data = {
            "supplier_id": supplier_id,
            "order_number": self.order_num_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip() or None,
            "items": items
        }
        
        try:
            if self.po:
                api_client.update_purchase_order(self.po["id"], data)
            else:
                api_client.create_purchase_order(data)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save PO: {e}")
