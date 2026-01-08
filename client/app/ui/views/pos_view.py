"""
POS View

Point of Sale interface for processing transactions.
"""

from decimal import Decimal
from typing import Optional, Dict, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox, QDoubleSpinBox, QMessageBox,
    QComboBox, QGridLayout, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal, QThread, QTimer
from PySide6.QtGui import QFont

from app.config import settings
from app.api import api_client, APIError


class CartItem:
    """Cart item data class."""
    
    def __init__(self, item_data: dict, quantity: float = 1):
        self.id = item_data["id"]
        self.sku = item_data["sku"]
        self.name = item_data["name"]
        self.unit_price = float(item_data["selling_price"])
        self.tax_rate = float(item_data.get("tax_rate", 0))
        self.quantity = quantity
    
    @property
    def subtotal(self) -> float:
        return self.quantity * self.unit_price
    
    @property
    def tax_amount(self) -> float:
        return self.subtotal * (self.tax_rate / 100)
    
    @property
    def total(self) -> float:
        return self.subtotal + self.tax_amount


class POSView(QWidget):
    """Point of Sale interface."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.cart: List[CartItem] = []
        self.current_customer: Optional[dict] = None
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the POS UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Left panel - Product search and cart
        left_panel = self._create_left_panel()
        layout.addWidget(left_panel, 2)
        
        # Right panel - Cart summary and payment
        right_panel = self._create_right_panel()
        layout.addWidget(right_panel, 1)
    
    def _create_left_panel(self) -> QFrame:
        """Create left panel with search and cart table."""
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Scan barcode or search product...")
        self.search_input.setMinimumHeight(48)
        self.search_input.setFont(QFont("Segoe UI", 12))
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        
        search_btn = QPushButton("Search")
        search_btn.setObjectName("primary")
        search_btn.setMinimumHeight(48)
        search_btn.clicked.connect(self._on_search)
        search_layout.addWidget(search_btn)
        
        layout.addLayout(search_layout)
        
        # Cart table
        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(6)
        self.cart_table.setHorizontalHeaderLabels([
            "SKU", "Product", "Price", "Qty", "Total", "Action"
        ])
        
        header = self.cart_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.cart_table, 1)
        
        # Quick actions
        actions_layout = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Cart")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self._clear_cart)
        actions_layout.addWidget(clear_btn)
        
        actions_layout.addStretch()
        
        hold_btn = QPushButton("Hold Order")
        hold_btn.clicked.connect(self._hold_order)
        actions_layout.addWidget(hold_btn)
        
        layout.addLayout(actions_layout)
        
        return panel
    
    def _create_right_panel(self) -> QFrame:
        """Create right panel with summary and payment."""
        panel = QFrame()
        panel.setObjectName("card")
        layout = QVBoxLayout(panel)
        
        # Customer section
        customer_label = QLabel("Customer")
        customer_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(customer_label)
        
        customer_layout = QHBoxLayout()
        self.customer_input = QLineEdit()
        self.customer_input.setPlaceholderText("Phone number...")
        self.customer_input.returnPressed.connect(self._lookup_customer)
        customer_layout.addWidget(self.customer_input)
        
        lookup_btn = QPushButton("Lookup")
        lookup_btn.clicked.connect(self._lookup_customer)
        customer_layout.addWidget(lookup_btn)
        
        layout.addLayout(customer_layout)
        
        self.customer_info_label = QLabel("No customer selected (Walk-in)")
        self.customer_info_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.customer_info_label)
        
        layout.addSpacing(20)
        
        # Order summary
        summary_label = QLabel("Order Summary")
        summary_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(summary_label)
        
        # Summary grid
        summary_grid = QGridLayout()
        
        summary_grid.addWidget(QLabel("Subtotal:"), 0, 0)
        self.subtotal_label = QLabel(f"{settings.CURRENCY_SYMBOL}0.00")
        self.subtotal_label.setAlignment(Qt.AlignRight)
        summary_grid.addWidget(self.subtotal_label, 0, 1)
        
        summary_grid.addWidget(QLabel("Tax:"), 1, 0)
        self.tax_label = QLabel(f"{settings.CURRENCY_SYMBOL}0.00")
        self.tax_label.setAlignment(Qt.AlignRight)
        summary_grid.addWidget(self.tax_label, 1, 1)
        
        summary_grid.addWidget(QLabel("Discount:"), 2, 0)
        self.discount_input = QDoubleSpinBox()
        self.discount_input.setPrefix(f"{settings.CURRENCY_SYMBOL}")
        self.discount_input.setMaximum(999999)
        self.discount_input.valueChanged.connect(self._update_totals)
        summary_grid.addWidget(self.discount_input, 2, 1)
        
        layout.addLayout(summary_grid)
        
        # Total
        total_frame = QFrame()
        total_frame.setStyleSheet("background-color: #2a82da; border-radius: 8px; padding: 16px;")
        total_layout = QHBoxLayout(total_frame)
        
        total_text = QLabel("TOTAL")
        total_text.setFont(QFont("Segoe UI", 14, QFont.Bold))
        total_layout.addWidget(total_text)
        
        self.total_label = QLabel(f"{settings.CURRENCY_SYMBOL}0.00")
        self.total_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
        self.total_label.setAlignment(Qt.AlignRight)
        total_layout.addWidget(self.total_label)
        
        layout.addWidget(total_frame)
        
        layout.addSpacing(20)
        
        # Payment method
        payment_label = QLabel("Payment Method")
        payment_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        layout.addWidget(payment_label)
        
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Cash", "Card", "Transfer", "Mobile Money"])
        self.payment_combo.setMinimumHeight(40)
        layout.addWidget(self.payment_combo)
        
        # Amount tendered (for cash)
        self.tendered_label = QLabel("Amount Tendered")
        layout.addWidget(self.tendered_label)
        
        self.tendered_input = QDoubleSpinBox()
        self.tendered_input.setPrefix(f"{settings.CURRENCY_SYMBOL}")
        self.tendered_input.setMaximum(9999999)
        self.tendered_input.setMinimumHeight(40)
        self.tendered_input.valueChanged.connect(self._update_change)
        layout.addWidget(self.tendered_input)
        
        self.change_label = QLabel("Change: " + f"{settings.CURRENCY_SYMBOL}0.00")
        self.change_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        self.change_label.setStyleSheet("color: #28a745;")
        layout.addWidget(self.change_label)
        
        layout.addStretch()
        
        # Complete sale button
        self.complete_btn = QPushButton(f"Complete Sale ({settings.CURRENCY_SYMBOL}0.00)")
        self.complete_btn.setObjectName("success")
        self.complete_btn.setMinimumHeight(60)
        self.complete_btn.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.complete_btn.clicked.connect(self._complete_sale)
        layout.addWidget(self.complete_btn)
        
        return panel
    
    def _on_search(self):
        """Handle search/barcode scan."""
        query = self.search_input.text().strip()
        if not query:
            return
        
        try:
            # Try barcode lookup first
            try:
                item = api_client.get_item_by_barcode(query)
                self._add_to_cart(item)
                self.search_input.clear()
                return
            except APIError:
                pass
            
            # Search by name/SKU
            items = api_client.get_items(search=query, limit=10)
            if items:
                if len(items) == 1:
                    self._add_to_cart(items[0])
                    self.search_input.clear()
                else:
                    # TODO: Show product picker dialog
                    self._add_to_cart(items[0])
                    self.search_input.clear()
            else:
                QMessageBox.warning(self, "Not Found", f"No product found for '{query}'")
        except APIError as e:
            QMessageBox.warning(self, "Error", e.message)
    
    def _add_to_cart(self, item_data: dict):
        """Add item to cart."""
        # Check if already in cart
        for cart_item in self.cart:
            if cart_item.id == item_data["id"]:
                cart_item.quantity += 1
                self._refresh_cart_table()
                return
        
        # Add new item
        cart_item = CartItem(item_data)
        self.cart.append(cart_item)
        self._refresh_cart_table()
    
    def _refresh_cart_table(self):
        """Refresh the cart table display."""
        self.cart_table.setRowCount(len(self.cart))
        
        for row, item in enumerate(self.cart):
            self.cart_table.setItem(row, 0, QTableWidgetItem(item.sku))
            self.cart_table.setItem(row, 1, QTableWidgetItem(item.name))
            self.cart_table.setItem(row, 2, QTableWidgetItem(f"{settings.CURRENCY_SYMBOL}{item.unit_price:.2f}"))
            
            # Quantity spinner
            qty_spin = QSpinBox()
            qty_spin.setMinimum(1)
            qty_spin.setMaximum(999)
            qty_spin.setValue(int(item.quantity))
            qty_spin.valueChanged.connect(lambda v, i=row: self._update_quantity(i, v))
            self.cart_table.setCellWidget(row, 3, qty_spin)
            
            self.cart_table.setItem(row, 4, QTableWidgetItem(f"{settings.CURRENCY_SYMBOL}{item.total:.2f}"))
            
            # Remove button
            remove_btn = QPushButton("✕")
            remove_btn.setObjectName("danger")
            remove_btn.setMaximumWidth(40)
            remove_btn.clicked.connect(lambda _, i=row: self._remove_item(i))
            self.cart_table.setCellWidget(row, 5, remove_btn)
        
        self._update_totals()
    
    def _update_quantity(self, row: int, quantity: int):
        """Update item quantity."""
        if 0 <= row < len(self.cart):
            self.cart[row].quantity = quantity
            self._refresh_cart_table()
    
    def _remove_item(self, row: int):
        """Remove item from cart."""
        if 0 <= row < len(self.cart):
            self.cart.pop(row)
            self._refresh_cart_table()
    
    def _update_totals(self):
        """Update order totals."""
        subtotal = sum(item.subtotal for item in self.cart)
        tax = sum(item.tax_amount for item in self.cart)
        discount = self.discount_input.value()
        total = subtotal + tax - discount
        
        self.subtotal_label.setText(f"{settings.CURRENCY_SYMBOL}{subtotal:.2f}")
        self.tax_label.setText(f"{settings.CURRENCY_SYMBOL}{tax:.2f}")
        self.total_label.setText(f"{settings.CURRENCY_SYMBOL}{total:.2f}")
        self.complete_btn.setText(f"Complete Sale ({settings.CURRENCY_SYMBOL}{total:.2f})")
        
        self._update_change()
    
    def _update_change(self):
        """Update change amount."""
        subtotal = sum(item.subtotal for item in self.cart)
        tax = sum(item.tax_amount for item in self.cart)
        discount = self.discount_input.value()
        total = subtotal + tax - discount
        
        tendered = self.tendered_input.value()
        change = max(0, tendered - total)
        
        self.change_label.setText(f"Change: {settings.CURRENCY_SYMBOL}{change:.2f}")
    
    def _lookup_customer(self):
        """Lookup customer by phone."""
        phone = self.customer_input.text().strip()
        if not phone:
            return
        
        try:
            customer = api_client.get_customer_by_phone(phone)
            self.current_customer = customer
            self.customer_info_label.setText(
                f"{customer['first_name']} {customer['last_name']} | "
                f"Points: {customer['loyalty_points']} | "
                f"Tier: {customer['loyalty_tier'].title()}"
            )
            self.customer_info_label.setStyleSheet("color: #28a745;")
        except APIError:
            self.current_customer = None
            self.customer_info_label.setText("Customer not found (Walk-in)")
            self.customer_info_label.setStyleSheet("color: #ff6b6b;")
    
    def _clear_cart(self):
        """Clear the cart."""
        if self.cart:
            reply = QMessageBox.question(
                self,
                "Clear Cart",
                "Are you sure you want to clear the cart?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                self.cart.clear()
                self._refresh_cart_table()
    
    def _hold_order(self):
        """Hold current order for later."""
        # TODO: Implement hold order functionality
        QMessageBox.information(self, "Hold Order", "This feature is coming soon!")
    
    def _complete_sale(self):
        """Complete the sale transaction."""
        if not self.cart:
            QMessageBox.warning(self, "Empty Cart", "Please add items to the cart first.")
            return
        
        # Calculate totals
        subtotal = sum(item.subtotal for item in self.cart)
        tax = sum(item.tax_amount for item in self.cart)
        discount = self.discount_input.value()
        total = subtotal + tax - discount
        
        # Validate payment
        payment_method = self.payment_combo.currentText().lower().replace(" ", "_")
        if payment_method == "mobile_money":
            payment_method = "mobile"
        
        tendered = self.tendered_input.value()
        if payment_method == "cash" and tendered < total:
            QMessageBox.warning(self, "Insufficient Amount", "Amount tendered is less than total.")
            return
        
        # Build sale data
        sale_data = {
            "location_id": str(self.user.get("location_id")) if self.user.get("location_id") else None,
            "customer_id": str(self.current_customer["id"]) if self.current_customer else None,
            "items": [
                {
                    "item_id": str(item.id),
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "discount_percent": 0,
                    "discount_amount": 0,
                }
                for item in self.cart
            ],
            "discount_amount": discount,
            "payment_method": payment_method,
            "amount_tendered": tendered if payment_method == "cash" else None,
        }
        
        try:
            result = api_client.create_sale(sale_data)
            
            # Show success
            change = tendered - total if payment_method == "cash" else 0
            QMessageBox.information(
                self,
                "Sale Complete",
                f"Receipt: {result['receipt_number']}\n"
                f"Total: {settings.CURRENCY_SYMBOL}{total:.2f}\n"
                + (f"Change: {settings.CURRENCY_SYMBOL}{change:.2f}" if change > 0 else ""),
            )
            
            # Reset
            self.cart.clear()
            self.current_customer = None
            self.customer_input.clear()
            self.customer_info_label.setText("No customer selected (Walk-in)")
            self.customer_info_label.setStyleSheet("color: #888888;")
            self.discount_input.setValue(0)
            self.tendered_input.setValue(0)
            self._refresh_cart_table()
            self.search_input.setFocus()
            
        except APIError as e:
            QMessageBox.critical(self, "Sale Failed", e.message)
