"""
Inventory View

Displays product list, allows search, filtering, and basic inventory actions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame, QMessageBox, QFileDialog, QMenu,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from app.api import api_client
from app.ui.dialogs.product_dialog import ProductDialog
from app.ui.dialogs.stock_dialog import StockDialog
from app.ui.dialogs.history_dialog import HistoryDialog


class InventoryView(QWidget):
    """View showing the inventory with product management features."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.products = []
        self.categories = []
        self._setup_ui()
        self._load_categories()
        self._load_data()
    
    def _setup_ui(self):
        """Setup the inventory view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header Section
        header = QHBoxLayout()
        
        left_header = QVBoxLayout()
        title = QLabel("Inventory Management")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        left_header.addWidget(title)
        
        subtitle = QLabel("Manage your product catalog and stock levels.")
        subtitle.setStyleSheet("color: #888888;")
        left_header.addWidget(subtitle)
        header.addLayout(left_header)
        
        header.addStretch()
        
        self.add_btn = QPushButton(" Add Product")
        self.add_btn.setObjectName("primary")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_product)
        
        # Permission check
        if not api_client.has_permission("manage_inventory"):
            self.add_btn.setEnabled(False)
            self.add_btn.setToolTip("You do not have permission to add products")
            
        header.addWidget(self.add_btn)
        
        # Tools Menu (Import/Export)
        self.tools_btn = QPushButton(" ⚙️ Tools")
        self.tools_btn.setMinimumHeight(40)
        self.tools_btn.setCursor(Qt.PointingHandCursor)
        
        tools_menu = QMenu(self)
        tools_menu.addAction("📥 Import Inventory", self._on_import_inventory)
        tools_menu.addAction("📤 Export Inventory", self._on_export_inventory)
        tools_menu.addSeparator()
        tools_menu.addAction("📝 Download Template", self._on_download_template)
        
        self.tools_btn.setMenu(tools_menu)
        header.addWidget(self.tools_btn)
        
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self._load_data)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # Filter Bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by SKU, Barcode, or Product Name...")
        self.search_input.setMinimumHeight(35)
        self.search_input.textChanged.connect(self._on_search)
        filter_bar.addWidget(self.search_input, 3)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories", None)
        self.category_filter.setMinimumHeight(35)
        self.category_filter.currentIndexChanged.connect(self._load_data)
        filter_bar.addWidget(self.category_filter, 1)
        
        self.location_filter = QComboBox()
        self.location_filter.addItem("All Locations", None)
        self.location_filter.setMinimumHeight(35)
        self.location_filter.currentIndexChanged.connect(self._load_data)
        filter_bar.addWidget(self.location_filter, 1)
        
        self.stock_filter = QComboBox()
        self.stock_filter.addItems(["All Stock", "In Stock", "Low Stock", "Out of Stock"])
        self.stock_filter.setMinimumHeight(35)
        self.stock_filter.currentIndexChanged.connect(self._on_stock_filter_change)
        filter_bar.addWidget(self.stock_filter, 1)
        
        layout.addLayout(filter_bar)
        
        # Inventory Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "SKU", "Product Name", "Location", "Category", "Stock", "Unit", "Price", "Margin %", "Actions"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for i in range(2, 9):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # Make Margin % more prominent
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # Footer
        footer = QHBoxLayout()
        self.stats_label = QLabel("Showing 0 products")
        self.stats_label.setStyleSheet("color: #888888;")
        footer.addWidget(self.stats_label)
        footer.addStretch()
        layout.addLayout(footer)

    def _load_data(self):
        """Load inventory data from the API with filtering."""
        try:
            cat_id = self.category_filter.currentData()
            loc_id = self.location_filter.currentData()
            search = self.search_input.text().strip()
            
            # Fetch from API with filters
            items = api_client.get_items(
                location_id=loc_id,
                category_id=cat_id,
                search=search if len(search) >= 2 else None
            )
            
            self.products = items
            self._apply_stock_filter() # Local filtering for stock level
            
        except Exception as e:
            print(f"Error loading products: {e}")
            self.stats_label.setText("Error loading products")

    def _load_categories(self):
        """Fetch categories and locations for filtering."""
        try:
            # Load Categories
            categories = api_client.get("inventory/categories")
            if categories and isinstance(categories, list):
                self.category_filter.blockSignals(True)
                self.category_filter.clear()
                self.category_filter.addItem("All Categories", None)
                for cat in categories:
                    self.category_filter.addItem(cat.get("name"), cat.get("id"))
                self.category_filter.blockSignals(False)
            
            # Load Locations
            locations = api_client.get_locations()
            if locations:
                self.location_filter.blockSignals(True)
                self.location_filter.clear()
                self.location_filter.addItem("All Locations", None)
                for loc in locations:
                    self.location_filter.addItem(loc.get("name"), loc.get("id"))
                self.location_filter.blockSignals(False)
                
        except Exception as e:
            print(f"Error loading filters: {e}")

    def _apply_stock_filter(self):
        """Filter current product list by stock level locally."""
        stock_filter = self.stock_filter.currentText()
        
        filtered = self.products
        if stock_filter == "In Stock":
            filtered = [p for p in self.products if p.get("current_stock", 0) > 0]
        elif stock_filter == "Low Stock":
            filtered = [p for p in self.products if p.get("is_low_stock", False)]
        elif stock_filter == "Out of Stock":
            filtered = [p for p in self.products if p.get("current_stock", 0) <= 0]
            
        self._update_table(filtered)

    def _on_stock_filter_change(self):
        self._apply_stock_filter()

    def _update_table(self, products):
        """Update the table with product data."""
        self.table.setRowCount(0)
        for i, product in enumerate(products):
            self.table.insertRow(i)
            # SKU & Name
            self.table.setItem(i, 0, QTableWidgetItem(product.get("sku", "")))
            self.table.setItem(i, 1, QTableWidgetItem(product.get("name", "")))
            
            # Location
            loc_item = QTableWidgetItem(product.get("location_name", "Unknown"))
            loc_item.setForeground(Qt.gray)
            self.table.setItem(i, 2, loc_item)
            
            # Category
            category = product.get("category", {})
            cat_name = category.get("name", "Uncategorized") if category else "Uncategorized"
            self.table.setItem(i, 3, QTableWidgetItem(cat_name))
            
            # Stock
            current_stock = product.get("current_stock", 0)
            stock_item = QTableWidgetItem(f"{current_stock:.2f}")
            min_stock = product.get("min_stock_level", 0) or 0
            if current_stock <= 0:
                stock_item.setForeground(Qt.red)
            elif product.get("is_low_stock"):
                stock_item.setForeground(Qt.yellow)
            self.table.setItem(i, 4, stock_item)
            
            # Unit
            self.table.setItem(i, 5, QTableWidgetItem(product.get("unit", "pcs")))
            
            # Price
            price = product.get("selling_price", 0)
            self.table.setItem(i, 6, QTableWidgetItem(f"₦{price:,.2f}"))
            
            # Margin %
            margin_pct = product.get("margin_pct", 0)
            margin_item = QTableWidgetItem(f"{margin_pct:.1f}%")
            if margin_pct < 0: margin_item.setForeground(Qt.red)
            elif margin_pct < 15: margin_item.setForeground(Qt.yellow)
            else: margin_item.setForeground(Qt.green)
            margin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 7, margin_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            def create_icon_btn(text, color, tooltip, callback):
                btn = QPushButton(text)
                btn.setFixedSize(28, 28)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setToolTip(tooltip)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {color}22;
                        border: 1px solid {color}44;
                        border-radius: 4px;
                        font-size: 14px;
                        color: {color};
                    }}
                    QPushButton:hover {{
                        background: {color}44;
                        border: 1px solid {color};
                    }}
                """)
                btn.clicked.connect(callback)
                return btn

            # Edit
            can_manage = api_client.has_permission("manage_inventory")
            is_admin = api_client.user_role in ["super_admin", "admin"]
            
            edit_btn = create_icon_btn("✏️", "#4dabf7", "Edit Product", lambda _, p=product: self._on_edit_product(p))
            edit_btn.setEnabled(can_manage)
            actions_layout.addWidget(edit_btn)
            
            # Stock Adjust
            adjust_btn = create_icon_btn("📦", "#ffd43b", "Stock Adjustment", lambda _, p=product: self._on_adjust_stock(p))
            adjust_btn.setEnabled(can_manage)
            actions_layout.addWidget(adjust_btn)
            
            # History
            history_btn = create_icon_btn("📜", "#63e6be", "Movement History", lambda _, p=product: self._on_view_history(p))
            actions_layout.addWidget(history_btn)
            
            # Delete
            delete_btn = create_icon_btn("🗑️", "#ff6b6b", "Delete Product", lambda _, p=product: self._on_delete_product(p))
            delete_btn.setEnabled(is_admin)
            if not is_admin:
                delete_btn.setStyleSheet(delete_btn.styleSheet() + "QPushButton { opacity: 0.5; }")
            actions_layout.addWidget(delete_btn)
            
            actions_layout.addStretch()
            self.table.setCellWidget(i, 8, actions_widget)
            
        self.stats_label.setText(f"Showing {len(products)} products")

    def _on_add_product(self):
        """Show dialog to add a new product."""
        dialog = ProductDialog(self)
        if dialog.exec():
            self._load_data()

    def _on_edit_product(self, product: dict):
        """Show dialog to edit an existing product."""
        dialog = ProductDialog(self, product)
        if dialog.exec():
            self._load_data()

    def _on_adjust_stock(self, product: dict):
        """Show dialog to adjust stock levels."""
        dialog = StockDialog(self, product)
        if dialog.exec():
            self._load_data()

    def _on_view_history(self, product: dict):
        """Show product movement history."""
        dialog = HistoryDialog(self, product)
        dialog.exec()

    def _on_delete_product(self, product):
        """Handle product deletion."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {product.get('name')}?\nThis will deactivate the product.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                api_client.delete_item(product["id"])
                self._load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")

    # ============== Bulk Operations ==============

    def _on_export_inventory(self):
        """Export inventory to CSV."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Inventory", f"inventory_export.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                data = api_client.export_inventory()
                with open(path, "wb") as f:
                    f.write(data)
                QMessageBox.information(self, "Success", "Inventory exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {e}")

    def _on_import_inventory(self):
        """Import inventory from CSV."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Inventory", "", "CSV Files (*.csv)"
        )
        if path:
            try:
                result = api_client.import_inventory(path)
                msg = f"Import Complete!\n\nImported: {result.get('imported_count', 0)}\nErrors: {len(result.get('errors', []))}"
                if result.get("errors"):
                    msg += f"\n\nFirst few errors:\n" + "\n".join(result["errors"][:5])
                
                QMessageBox.information(self, "Import Result", msg)
                self._load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Import failed: {e}")

    def _on_download_template(self):
        """Download import template."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Template", "inventory_template.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                data = api_client.get_import_template()
                with open(path, "wb") as f:
                    f.write(data)
                QMessageBox.information(self, "Success", "Template saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to download template: {e}")

    def _on_search(self):
        """Filter products based on search query."""
        query = self.search_input.text().lower()
        if not query:
            self._update_table(self.products)
            return
            
        filtered = [
            p for p in self.products
            if query in p.get("sku", "").lower() or 
               query in p.get("name", "").lower() or 
               query in p.get("barcode", "").lower()
        ]
        self._update_table(filtered)
