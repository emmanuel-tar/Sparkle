"""
Inventory View

Displays product list, allows search, filtering, and basic inventory actions.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon

from app.api import api_client
from app.ui.dialogs.product_dialog import ProductDialog
from app.ui.dialogs.stock_dialog import StockDialog


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
        header.addWidget(self.add_btn)
        
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
        self.category_filter.addItem("All Categories")
        self.category_filter.setMinimumHeight(35)
        filter_bar.addWidget(self.category_filter, 1)
        
        self.stock_filter = QComboBox()
        self.stock_filter.addItems(["All Stock", "In Stock", "Low Stock", "Out of Stock"])
        self.stock_filter.setMinimumHeight(35)
        filter_bar.addWidget(self.stock_filter, 1)
        
        layout.addLayout(filter_bar)
        
        # Inventory Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "SKU", "Product Name", "Category", "Stock Level", "Unit", "Price", "Actions"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        
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
        """Load inventory data from the API."""
        try:
            # Note: For now, we'll fetch all items. Pagination can be added later.
            response = api_client.get("/inventory/items")
            if response and isinstance(response, list):
                self.products = response
                self._update_table(self.products)
            else:
                self.products = []
                self._update_table([])
        except Exception as e:
            print(f"Error loading products: {e}")
            self.stats_label.setText("Error loading products")

    def _load_categories(self):
        """Fetch categories for filtering."""
        try:
            response = api_client.get("inventory/categories")
            if response and isinstance(response, list):
                self.categories = response
                self.category_filter.clear()
                self.category_filter.addItem("All Categories", None)
                for cat in self.categories:
                    self.category_filter.addItem(cat.get("name"), cat.get("id"))
        except Exception as e:
            print(f"Error loading categories: {e}")

    def _update_table(self, products):
        """Update the table with product data."""
        self.table.setRowCount(0)
        for i, product in enumerate(products):
            self.table.insertRow(i)
            
            # SKU
            self.table.setItem(i, 0, QTableWidgetItem(product.get("sku", "")))
            
            # Name
            self.table.setItem(i, 1, QTableWidgetItem(product.get("name", "")))
            
            # Category
            category = product.get("category", {})
            cat_name = category.get("name", "Uncategorized") if category else "Uncategorized"
            self.table.setItem(i, 2, QTableWidgetItem(cat_name))
            
            # Stock
            current_stock = product.get("current_stock", 0)
            stock_item = QTableWidgetItem(f"{current_stock:.2f}")
            
            # Color code stock level
            min_stock = product.get("min_stock_level", 0) or 0
            if current_stock <= 0:
                stock_item.setForeground(Qt.red)
            elif current_stock <= min_stock:
                stock_item.setForeground(Qt.yellow)
            
            self.table.setItem(i, 3, stock_item)
            
            # Unit
            self.table.setItem(i, 4, QTableWidgetItem(product.get("unit", "pcs")))
            
            # Price
            price = product.get("selling_price", 0)
            self.table.setItem(i, 5, QTableWidgetItem(f"₦{price:,.2f}"))
            
            # Actions (Edit/Detail placeholder)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(8)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedWidth(50)
            edit_btn.setStyleSheet("font-size: 10px; padding: 4px;")
            edit_btn.clicked.connect(lambda checked, p=product: self._on_edit_product(p))
            actions_layout.addWidget(edit_btn)
            
            adjust_btn = QPushButton("Stock")
            adjust_btn.setFixedWidth(50)
            adjust_btn.setStyleSheet("font-size: 10px; padding: 4px; background-color: #3d3d3d;")
            adjust_btn.clicked.connect(lambda checked, p=product: self._on_adjust_stock(p))
            actions_layout.addWidget(adjust_btn)
            
            actions_layout.addStretch()
            self.table.setCellWidget(i, 6, actions_widget)
            
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
