"""
Product Dialog

Modal for adding or editing inventory items.
"""

from typing import Optional, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox, 
    QTextEdit, QFormLayout, QGroupBox, QCheckBox, QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client, APIError


class ProductDialog(QDialog):
    """Dialog for creating or updating a product."""
    
    def __init__(self, parent=None, product_data: Optional[Dict] = None):
        super().__init__(parent)
        self.product_data = product_data
        self.is_edit = product_data is not None
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Edit Product" if self.is_edit else "Add New Product")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Product Information")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)
        
        # Form
        form_frame = QFrame()
        form_layout = QFormLayout(form_frame)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(12)
        
        self.sku_input = QLineEdit()
        self.sku_input.setPlaceholderText("e.g. ELE-PHN-001")
        if self.is_edit:
            self.sku_input.setText(self.product_data.get("sku", ""))
            self.sku_input.setReadOnly(True) # Usually SKU shouldn't be edited
        form_layout.addRow("SKU *:", self.sku_input)
        
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Scan or enter barcode")
        if self.is_edit:
            self.barcode_input.setText(self.product_data.get("barcode", ""))
        form_layout.addRow("Barcode:", self.barcode_input)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Product name")
        if self.is_edit:
            self.name_input.setText(self.product_data.get("name", ""))
        form_layout.addRow("Name *:", self.name_input)
        
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        if self.is_edit:
            self.description_input.setPlainText(self.product_data.get("description", ""))
        form_layout.addRow("Description:", self.description_input)
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("Select Category", None)
        # Load categories (will be populated in _load_categories)
        form_layout.addRow("Category:", self.category_combo)
        
        layout.addWidget(form_frame)
        
        # Pricing and Inventory Groups
        hb = QHBoxLayout()
        
        # Pricing Group
        pricing_group = QGroupBox("Pricing & Units")
        pricing_layout = QFormLayout(pricing_group)
        
        self.cost_price = QDoubleSpinBox()
        self.cost_price.setRange(0, 10000000)
        self.cost_price.setPrefix("₦ ")
        if self.is_edit:
            self.cost_price.setValue(self.product_data.get("cost_price", 0) or 0)
        pricing_layout.addRow("Cost Price:", self.cost_price)
        
        self.selling_price = QDoubleSpinBox()
        self.selling_price.setRange(0, 10000000)
        self.selling_price.setPrefix("₦ ")
        if self.is_edit:
            self.selling_price.setValue(self.product_data.get("selling_price", 0))
        pricing_layout.addRow("Selling Price *:", self.selling_price)
        
        self.unit_input = QLineEdit()
        self.unit_input.setPlaceholderText("e.g. pcs, kg, box")
        self.unit_input.setText("pcs")
        if self.is_edit:
            self.unit_input.setText(self.product_data.get("unit", "pcs"))
        pricing_layout.addRow("Unit:", self.unit_input)
        
        hb.addWidget(pricing_group)
        
        # Inventory Group
        stock_group = QGroupBox("Stock Levels")
        stock_layout = QFormLayout(stock_group)
        
        self.current_stock = QDoubleSpinBox()
        self.current_stock.setRange(-10000, 1000000)
        if self.is_edit:
            self.current_stock.setValue(self.product_data.get("current_stock", 0))
            self.current_stock.setReadOnly(True) # Stock should be updated via adjustments
        stock_layout.addRow("Current Stock:", self.current_stock)
        
        self.min_stock = QDoubleSpinBox()
        self.min_stock.setRange(0, 1000000)
        if self.is_edit:
            self.min_stock.setValue(self.product_data.get("min_stock_level", 0) or 0)
        stock_layout.addRow("Min Level:", self.min_stock)
        
        self.allow_negative = QCheckBox("Allow Negative Stock")
        if self.is_edit:
            self.allow_negative.setChecked(self.product_data.get("allow_negative_stock", False))
        stock_layout.addWidget(self.allow_negative)
        
        hb.addWidget(stock_group)
        layout.addLayout(hb)
        
        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Product")
        self.save_btn.setObjectName("primary")
        self.save_btn.setMinimumHeight(36)
        self.save_btn.clicked.connect(self._on_save)
        btns.addWidget(self.save_btn)
        
        layout.addLayout(btns)
        
        # Load categories
        self._load_categories()
        
    def _load_categories(self):
        """Fetch categories from API."""
        try:
            categories = api_client.get("inventory/categories")
            if categories and isinstance(categories, list):
                for cat in categories:
                    self.category_combo.addItem(cat.get("name"), cat.get("id"))
                
                # Set current category if editing
                if self.is_edit and self.product_data.get("category_id"):
                    index = self.category_combo.findData(self.product_data.get("category_id"))
                    if index >= 0:
                        self.category_combo.setCurrentIndex(index)
        except Exception as e:
            print(f"Error loading categories for dialog: {e}")

    def _on_save(self):
        """Validate and save product data."""
        # Simple validation
        sku = self.sku_input.text().strip()
        name = self.name_input.text().strip()
        price = self.selling_price.value()
        
        if not sku or not name or price <= 0:
            QMessageBox.warning(self, "Validation Error", "SKU, Name and a valid Selling Price are required.")
            return
            
        # Prepare data
        data = {
            "sku": sku,
            "name": name,
            "barcode": self.barcode_input.text().strip() or None,
            "description": self.description_input.toPlainText().strip() or None,
            "category_id": self.category_combo.currentData(),
            "selling_price": price,
            "cost_price": self.cost_price.value(),
            "unit": self.unit_input.text().strip(),
            "min_stock_level": self.min_stock.value(),
            "allow_negative_stock": self.allow_negative.isChecked(),
        }
        
        if not self.is_edit:
            data["current_stock"] = self.current_stock.value()
            # Default location_id (should come from current user/session)
            # For now, we'll try to get it from the user object if available
            # Note: The server requires location_id
            # We'll need to handle this properly
            pass

        try:
            if self.is_edit:
                api_client.patch(f"inventory/items/{self.product_data['id']}", data)
            else:
                # Add location_id if missing (placeholder for now)
                # In a real app, this would be the user's assigned location
                from app.api import api_client
                user = api_client.get_current_user()
                data["location_id"] = user.get("location_id")
                
                if not data["location_id"]:
                    # Fallback or error
                    pass
                    
                api_client.post("inventory/items", data)
                
            self.accept()
        except APIError as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Failed to save product: {e.message}")
        except Exception as e:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
