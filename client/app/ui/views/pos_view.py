"""
POS View

Point of Sale interface for processing transactions.
"""

from decimal import Decimal
from typing import Optional, Dict, List
import json
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox, QDoubleSpinBox, QMessageBox,
    QComboBox, QGridLayout, QSizePolicy, QListWidget,
    QListWidgetItem, QDialog, QDialogButtonBox, QInputDialog,
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
        self.held_orders_file = Path(settings.DATA_DIR) / "held_orders.json"
        self.last_sale_data = None  # Store last completed sale for printing
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
        
        # Increase row height for better touch/click friendliness
        self.cart_table.verticalHeader().setDefaultSectionSize(40)
        
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

        # Bulk quantity update
        bulk_layout = QVBoxLayout()
        bulk_layout.setContentsMargins(0, 0, 0, 0)

        bulk_label = QLabel("Bulk Qty:")
        bulk_label.setStyleSheet("font-size: 10px; color: #666;")
        bulk_layout.addWidget(bulk_label)

        self.bulk_qty_input = QSpinBox()
        self.bulk_qty_input.setMinimum(1)
        self.bulk_qty_input.setMaximum(999)
        self.bulk_qty_input.setValue(1)
        self.bulk_qty_input.setFixedWidth(60)
        self.bulk_qty_input.setStyleSheet("QSpinBox { padding: 2px; }")
        bulk_layout.addWidget(self.bulk_qty_input)

        actions_layout.addLayout(bulk_layout)

        bulk_apply_btn = QPushButton("Apply to Selected")
        bulk_apply_btn.setObjectName("secondary")
        bulk_apply_btn.clicked.connect(self._apply_bulk_quantity)
        actions_layout.addWidget(bulk_apply_btn)

        actions_layout.addStretch()

        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #2ed573; font-weight: bold;")
        actions_layout.addWidget(self.status_label)

        actions_layout.addStretch()

        hold_btn = QPushButton("Hold Order")
        hold_btn.clicked.connect(self._hold_order)
        actions_layout.addWidget(hold_btn)

        # Print last receipt button
        print_btn = QPushButton("Print Receipt")
        print_btn.clicked.connect(self._print_last_receipt)
        actions_layout.addWidget(print_btn)

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
        self.payment_combo.currentTextChanged.connect(self._on_payment_method_changed)
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
                    self.status_label.setText(f"✓ Added {items[0]['name']}")
                    self.search_input.clear()
                else:
                    # For now just add the first one if multiple found
                    self._add_to_cart(items[0])
                    self.status_label.setText(f"✓ Added {items[0]['name']} (Multiple matches)")
                    self.search_input.clear()
            else:
                self.status_label.setText(f"✗ Not found: {query}")
                self.status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
                QMessageBox.warning(self, "Not Found", f"No product found for '{query}'")
        except APIError as e:
            self.status_label.setText("✗ Error")
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
            # Unit Price override
            price_spin = QDoubleSpinBox()
            price_spin.setRange(0, 10000000)
            price_spin.setPrefix(f"{settings.CURRENCY_SYMBOL}")
            price_spin.setValue(item.unit_price)
            price_spin.setStyleSheet("background: transparent; border: 1px solid #444; border-radius: 4px;")
            price_spin.valueChanged.connect(lambda v, i=row: self._update_price(i, v))
            self.cart_table.setCellWidget(row, 2, price_spin)
            
            # Quantity spinner
            qty_spin = QSpinBox()
            qty_spin.setMinimum(1)
            qty_spin.setMaximum(999)
            qty_spin.setValue(int(item.quantity))
            qty_spin.setStyleSheet("background: transparent; border: 1px solid #444; border-radius: 4px;")
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
            self._update_totals() # Faster than full refresh

    def _update_price(self, row: int, price: float):
        """Update item price override."""
        if 0 <= row < len(self.cart):
            self.cart[row].unit_price = price
            self.cart_table.setItem(row, 4, QTableWidgetItem(f"{settings.CURRENCY_SYMBOL}{self.cart[row].total:.2f}"))
            self._update_totals()
    
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

    def _on_payment_method_changed(self, payment_method: str):
        """Handle payment method change."""
        if payment_method.lower() == "cash":
            # Auto-fill tendered amount with total for cash payments
            subtotal = sum(item.subtotal for item in self.cart)
            tax = sum(item.tax_amount for item in self.cart)
            discount = self.discount_input.value()
            total = subtotal + tax - discount
            self.tendered_input.setValue(total)
            self.tendered_label.setText("Amount Tendered")
            self.tendered_input.setEnabled(True)
            self.change_label.setVisible(True)
        else:
            # For non-cash payments, disable tendered input
            self.tendered_input.setValue(0)
            self.tendered_label.setText("Amount Tendered (Cash only)")
            self.tendered_input.setEnabled(False)
            self.change_label.setVisible(False)
    
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
        if not self.cart:
            QMessageBox.warning(self, "Empty Cart", "Please add items to the cart first.")
            return

        # Get order name from user
        order_name, ok = QInputDialog.getText(
            self,
            "Hold Order",
            "Enter a name for this order:",
            text=f"Order {datetime.now().strftime('%H:%M')}"
        )

        if not ok or not order_name.strip():
            return

        # Save order data
        order_data = {
            "id": str(uuid.uuid4()),
            "name": order_name.strip(),
            "timestamp": datetime.now().isoformat(),
            "customer": self.current_customer,
            "discount": self.discount_input.value(),
            "items": [
                {
                    "id": str(item.id),
                    "sku": item.sku,
                    "name": item.name,
                    "unit_price": item.unit_price,
                    "quantity": item.quantity,
                    "tax_rate": item.tax_rate,
                }
                for item in self.cart
            ]
        }

        try:
            # Load existing orders
            held_orders = []
            if self.held_orders_file.exists():
                with open(self.held_orders_file, 'r') as f:
                    held_orders = json.load(f)

            # Add new order
            held_orders.append(order_data)

            # Save back to file
            with open(self.held_orders_file, 'w') as f:
                json.dump(held_orders, f, indent=2)

            # Clear cart
            self.cart.clear()
            self.current_customer = None
            self.customer_input.clear()
            self.customer_info_label.setText("No customer selected (Walk-in)")
            self.customer_info_label.setStyleSheet("color: #888888;")
            self.discount_input.setValue(0)
            self._refresh_cart_table()

            QMessageBox.information(self, "Order Held", f"Order '{order_name}' has been saved for later.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save order: {str(e)}")

    def _apply_bulk_quantity(self):
        """Apply bulk quantity to selected items."""
        selected_rows = set()
        for item in self.cart_table.selectedItems():
            selected_rows.add(item.row())

        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select items in the cart first.")
            return

        bulk_qty = self.bulk_qty_input.value()
        for row in selected_rows:
            if 0 <= row < len(self.cart):
                self.cart[row].quantity = bulk_qty

        self._refresh_cart_table()
        self.status_label.setText(f"✓ Applied quantity {bulk_qty} to {len(selected_rows)} items")

    def _print_last_receipt(self):
        """Print the last completed receipt."""
        if not self.last_sale_data:
            QMessageBox.warning(self, "No Receipt", "No recent sale to print.")
            return

        try:
            # Generate receipt text
            receipt_lines = []
            receipt_lines.append("=" * 40)
            receipt_lines.append("         SPARKLE RETAIL")
            receipt_lines.append("     Point of Sale Receipt")
            receipt_lines.append("=" * 40)
            receipt_lines.append(f"Receipt: {self.last_sale_data['receipt_number']}")
            receipt_lines.append(f"Date: {datetime.fromisoformat(self.last_sale_data['created_at']).strftime('%Y-%m-%d %H:%M:%S')}")

            if self.last_sale_data.get('customer'):
                customer = self.last_sale_data['customer']
                receipt_lines.append(f"Customer: {customer.get('first_name', '')} {customer.get('last_name', '')}")

            receipt_lines.append("-" * 40)

            # Items header
            receipt_lines.append(f"{'SKU':<10} {'Item':<15} {'Qty':>3} {'Total':>8}")
            receipt_lines.append("-" * 40)

            for item in self.last_sale_data['items']:
                sku = item['sku'][:10]
                name = item['name'][:15]
                qty = f"{item['quantity']:.1f}"
                total = f"{settings.CURRENCY_SYMBOL}{item['line_total']:.2f}"
                receipt_lines.append(f"{sku:<10} {name:<15} {qty:>3} {total:>8}")

            receipt_lines.append("-" * 40)

            # Totals
            subtotal = self.last_sale_data['subtotal']
            tax = self.last_sale_data['tax_amount']
            discount = self.last_sale_data['discount_amount']
            total = self.last_sale_data['total_amount']

            receipt_lines.append(f"{'Subtotal:':<30} {settings.CURRENCY_SYMBOL}{subtotal:.2f}")
            if tax > 0:
                receipt_lines.append(f"{'Tax:':<30} {settings.CURRENCY_SYMBOL}{tax:.2f}")
            if discount > 0:
                receipt_lines.append(f"{'Discount:':<30} {settings.CURRENCY_SYMBOL}{discount:.2f}")
            receipt_lines.append(f"{'TOTAL:':<30} {settings.CURRENCY_SYMBOL}{total:.2f}")

            receipt_lines.append("-" * 40)
            receipt_lines.append(f"Payment: {self.last_sale_data['payment_method'].upper()}")

            if self.last_sale_data.get('change_given', 0) > 0:
                receipt_lines.append(f"Change: {settings.CURRENCY_SYMBOL}{self.last_sale_data['change_given']:.2f}")

            receipt_lines.append("=" * 40)
            receipt_lines.append("     Thank you for shopping!")
            receipt_lines.append("       Visit us again soon!")
            receipt_lines.append("=" * 40)

            # Join all lines
            receipt_text = "\n".join(receipt_lines)

            # For now, show in message box (later can integrate with printer)
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Receipt Preview")
            msg_box.setText("Receipt generated successfully!")
            msg_box.setDetailedText(receipt_text)
            msg_box.setStandardButtons(QMessageBox.Ok)

            # Add print button
            print_button = msg_box.addButton("Print Receipt", QMessageBox.ActionRole)
            msg_box.exec()

            if msg_box.clickedButton() == print_button:
                self._print_receipt_text(receipt_text)

        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Failed to generate receipt: {str(e)}")

    def _print_receipt_text(self, receipt_text: str):
        """Print receipt text (placeholder for actual printing)."""
        try:
            # For now, save to file as placeholder
            receipt_file = Path(settings.DATA_DIR) / f"receipt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            receipt_file.write_text(receipt_text)

            QMessageBox.information(
                self,
                "Receipt Saved",
                f"Receipt saved to:\n{receipt_file}\n\nIn a real implementation, this would be sent to a thermal printer."
            )
        except Exception as e:
            QMessageBox.critical(self, "Print Error", f"Failed to save receipt: {str(e)}")
    
    def _complete_sale(self):
        """Complete the sale transaction."""
        if not self.cart:
            QMessageBox.warning(self, "Empty Cart", "Please add items to the cart first.")
            return

        # Check if user has location_id
        if not self.user.get("location_id"):
            QMessageBox.warning(self, "Location Required", "Please set your location before completing sales.")
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
            "location_id": self.user.get("location_id") if self.user.get("location_id") else None,
            "customer_id": self.current_customer["id"] if self.current_customer else None,
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

            # Store sale data for receipt printing
            self.last_sale_data = result

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
