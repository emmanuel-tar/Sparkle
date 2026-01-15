"""
Inventory View

Displays product list with real-time updates, async loading, pagination,
and advanced filtering with threading support.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame, QMessageBox, QFileDialog, QMenu, QDialog,
    QSpinBox, QCheckBox, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QIcon, QPixmap
from pathlib import Path
import datetime

from app.api import api_client, APIError
from app.ui.dialogs.product_dialog import ProductDialog
from app.ui.dialogs.stock_dialog import StockDialog
from app.ui.dialogs.history_dialog import HistoryDialog
from app.ui.dialogs.import_dialog import ImportDialog


# ============== Data Loading Threads ==============

class DataLoadThread(QThread):
    """Background thread for loading inventory data."""
    
    data_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def __init__(self, location_id=None, category_id=None, search=None, 
                 low_stock_only=False, skip=0, limit=50):
        super().__init__()
        self.location_id = location_id
        self.category_id = category_id
        self.search = search
        self.low_stock_only = low_stock_only
        self.skip = skip
        self.limit = limit
    
    def run(self):
        try:
            items = api_client.get_items(
                location_id=self.location_id,
                category_id=self.category_id,
                search=self.search if self.search and len(self.search) >= 2 else None,
                skip=self.skip,
                limit=self.limit
            )
            self.data_loaded.emit(items)
        except APIError as e:
            self.error_occurred.emit(e.message)
        except Exception as e:
            self.error_occurred.emit(str(e))


class FilterLoadThread(QThread):
    """Background thread for loading categories and locations."""
    
    categories_loaded = Signal(list)
    locations_loaded = Signal(list)
    error_occurred = Signal(str)
    
    def run(self):
        try:
            # Load categories
            categories = api_client.get("/inventory/categories")
            if categories:
                self.categories_loaded.emit(categories)
            
            # Load locations
            locations = api_client.get_locations()
            if locations:
                self.locations_loaded.emit(locations)
        except Exception as e:
            self.error_occurred.emit(str(e))


class BulkDeleteThread(QThread):
    """Background thread for bulk delete operations."""
    
    delete_complete = Signal(int)  # number deleted
    error_occurred = Signal(str)
    
    def __init__(self, item_ids):
        super().__init__()
        self.item_ids = item_ids
    
    def run(self):
        try:
            deleted_count = 0
            for item_id in self.item_ids:
                api_client.delete_item(item_id)
                deleted_count += 1
            self.delete_complete.emit(deleted_count)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ============== Main Inventory View ==============

class InventoryView(QWidget):
    """View showing the inventory with product management features."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.products = []
        self.categories = []
        self.locations = []
        self.selected_items = set()  # Track selected rows for bulk operations
        self.current_page = 0
        self.page_size = 50
        self.total_items = 0
        self.is_loading = False
        
        self._setup_ui()
        self._load_filters()
    
    def _setup_ui(self):
        """Setup the inventory view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # ============== Header Section ==============
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
        
        self.add_btn = QPushButton(" + Add Product")
        self.add_btn.setObjectName("primary")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_product)
        
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
        
        self.refresh_btn = QPushButton(" ↻ Refresh")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self._load_data)
        header.addWidget(self.refresh_btn)
        
        layout.addLayout(header)
        
        # ============== Low Stock Alert ==============
        self.alert_frame = QFrame()
        self.alert_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 1px solid #ffc107;
                border-radius: 4px;
                padding: 12px;
            }
        """)
        alert_layout = QHBoxLayout(self.alert_frame)
        alert_layout.setContentsMargins(12, 8, 12, 8)
        alert_layout.setSpacing(10)
        
        alert_icon = QLabel("⚠️")
        alert_icon.setFont(QFont("Segoe UI", 14))
        alert_layout.addWidget(alert_icon)
        
        self.alert_label = QLabel()
        self.alert_label.setStyleSheet("color: #856404;")
        alert_layout.addWidget(self.alert_label)
        
        alert_layout.addStretch()
        
        show_low_stock_btn = QPushButton("View Low Stock")
        show_low_stock_btn.setStyleSheet("""
            QPushButton {
                background: #ffc107;
                color: #000;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e0a800;
            }
        """)
        show_low_stock_btn.clicked.connect(self._show_low_stock_only)
        alert_layout.addWidget(show_low_stock_btn)
        
        self.alert_frame.setVisible(False)
        layout.addWidget(self.alert_frame)
        
        # ============== Filter Bar ==============
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
        
        # ============== Bulk Actions Bar ==============
        bulk_bar = QHBoxLayout()
        bulk_bar.setSpacing(10)
        
        self.select_all_checkbox = QCheckBox("Select All")
        self.select_all_checkbox.stateChanged.connect(self._on_select_all)
        bulk_bar.addWidget(self.select_all_checkbox)
        
        self.bulk_label = QLabel("0 selected")
        self.bulk_label.setStyleSheet("color: #666666;")
        bulk_bar.addWidget(self.bulk_label)
        
        bulk_bar.addSpacing(20)
        
        self.bulk_delete_btn = QPushButton("🗑️ Delete Selected")
        self.bulk_delete_btn.setEnabled(False)
        self.bulk_delete_btn.setStyleSheet("""
            QPushButton {
                background: #ff6b6b;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover:!disabled {
                background: #ff5252;
            }
            QPushButton:disabled {
                background: #ccc;
                color: #999;
            }
        """)
        self.bulk_delete_btn.clicked.connect(self._on_bulk_delete)
        bulk_bar.addWidget(self.bulk_delete_btn)
        
        bulk_bar.addStretch()
        
        layout.addLayout(bulk_bar)
        
        # ============== Inventory Table ==============
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "☑️", "SKU", "Product Name", "Stock", "Available", "Unit", "Price", "Margin %", "Status", "Expiry", "Actions"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Checkbox
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # SKU
        header.setSectionResizeMode(2, QHeaderView.Stretch)           # Name
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Stock
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Available
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Unit
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Price
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Margin %
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Expiry
        header.setSectionResizeMode(10, QHeaderView.ResizeToContents) # Actions
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        
        layout.addWidget(self.table)
        
        # ============== Footer with Pagination ==============
        footer = QHBoxLayout()
        
        self.stats_label = QLabel("Loading...")
        self.stats_label.setStyleSheet("color: #888888;")
        footer.addWidget(self.stats_label)
        
        footer.addStretch()
        
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self._load_previous_page)
        footer.addWidget(self.prev_btn)
        
        self.page_label = QLabel("Page 1")
        footer.addWidget(self.page_label)
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self._load_next_page)
        footer.addWidget(self.next_btn)
        
        layout.addLayout(footer)
    
    # ============== Data Loading ==============
    
    def _load_filters(self):
        """Load categories and locations in background thread."""
        self.filter_thread = FilterLoadThread()
        self.filter_thread.categories_loaded.connect(self._on_categories_loaded)
        self.filter_thread.locations_loaded.connect(self._on_locations_loaded)
        self.filter_thread.error_occurred.connect(self._on_filter_load_error)
        self.filter_thread.start()
    
    def _load_data(self):
        """Load inventory data from the API in background thread."""
        if self.is_loading:
            return
        
        self.is_loading = True
        self.refresh_btn.setEnabled(False)
        self.current_page = 0
        
        cat_id = self.category_filter.currentData()
        loc_id = self.location_filter.currentData()
        search = self.search_input.text().strip()
        
        self.data_thread = DataLoadThread(
            location_id=loc_id,
            category_id=cat_id,
            search=search,
            skip=self.current_page * self.page_size,
            limit=self.page_size
        )
        self.data_thread.data_loaded.connect(self._on_data_loaded)
        self.data_thread.error_occurred.connect(self._on_data_load_error)
        self.data_thread.start()
    
    def _load_previous_page(self):
        """Load previous page of data."""
        if self.current_page > 0:
            self.current_page -= 1
            self._load_data()
    
    def _load_next_page(self):
        """Load next page of data."""
        self.current_page += 1
        self._load_data()
    
    # ============== Data Callbacks ==============
    
    def _on_categories_loaded(self, categories):
        """Handle categories loaded."""
        self.categories = categories
        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("All Categories", None)
        for cat in categories:
            self.category_filter.addItem(cat.get("name"), cat.get("id"))
        self.category_filter.blockSignals(False)
    
    def _on_locations_loaded(self, locations):
        """Handle locations loaded."""
        self.locations = locations
        self.location_filter.blockSignals(True)
        self.location_filter.clear()
        self.location_filter.addItem("All Locations", None)
        for loc in locations:
            self.location_filter.addItem(loc.get("name"), loc.get("id"))
        self.location_filter.blockSignals(False)
        
        # Auto-load data after filters are ready
        self._load_data()
    
    def _on_data_loaded(self, products):
        """Handle inventory data loaded."""
        self.products = products
        self._apply_stock_filter()
        self.is_loading = False
        self.refresh_btn.setEnabled(True)
        self._update_low_stock_alert()
        self._update_pagination()
    
    def _on_data_load_error(self, error_msg):
        """Handle data load error."""
        self.stats_label.setText(f"Error: {error_msg}")
        self.is_loading = False
        self.refresh_btn.setEnabled(True)
    
    def _on_filter_load_error(self, error_msg):
        """Handle filter load error."""
        print(f"Filter load error: {error_msg}")
    
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
        """Handle stock filter change."""
        self.current_page = 0
        self._apply_stock_filter()
    
    def _on_search(self):
        """Filter products based on search query (with debounce)."""
        self.current_page = 0
        self._load_data()
    
    def _show_low_stock_only(self):
        """Show only low stock items."""
        self.stock_filter.blockSignals(True)
        self.stock_filter.setCurrentText("Low Stock")
        self.stock_filter.blockSignals(False)
        self._apply_stock_filter()
    
    def _update_low_stock_alert(self):
        """Update low stock alert display."""
        low_stock_items = [p for p in self.products if p.get("is_low_stock", False)]
        
        if low_stock_items:
            count = len(low_stock_items)
            self.alert_label.setText(f"⚠️ {count} product(s) are below minimum stock level")
            self.alert_frame.setVisible(True)
        else:
            self.alert_frame.setVisible(False)
    
    def _update_pagination(self):
        """Update pagination controls."""
        total_shown = len(self.products)
        start_num = self.current_page * self.page_size + 1
        end_num = start_num + total_shown - 1
        
        if total_shown == 0:
            self.stats_label.setText("No products found")
        elif total_shown < self.page_size:
            self.stats_label.setText(f"Showing {start_num}–{end_num} products (end of results)")
            self.next_btn.setEnabled(False)
        else:
            self.stats_label.setText(f"Showing {start_num}–{end_num} products (more available)")
            self.next_btn.setEnabled(True)
        
        self.prev_btn.setEnabled(self.current_page > 0)
        self.page_label.setText(f"Page {self.current_page + 1}")
    
    # ============== Table Display ==============
    
    def _update_table(self, products):
        """Update the table with product data."""
        self.table.setRowCount(0)
        self.selected_items.clear()
        self.select_all_checkbox.setCheckState(Qt.Unchecked)
        
        for i, product in enumerate(products):
            self.table.insertRow(i)
            
            # Checkbox for selection
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(lambda state, p=product: self._on_item_checkbox_changed(p, state))
            self.table.setCellWidget(i, 0, checkbox)
            
            # SKU
            self.table.setItem(i, 1, QTableWidgetItem(product.get("sku", "")))
            
            # Product Name
            self.table.setItem(i, 2, QTableWidgetItem(product.get("name", "")))
            
            # Stock Level
            current_stock = product.get("current_stock", 0)
            stock_item = QTableWidgetItem(f"{current_stock:.2f}")
            if current_stock <= 0:
                stock_item.setForeground(Qt.red)
            elif product.get("is_low_stock"):
                stock_item.setForeground(Qt.yellow)
            else:
                stock_item.setForeground(Qt.green)
            self.table.setItem(i, 3, stock_item)
            
            # Available Stock
            available = product.get("available_stock", 0)
            avail_item = QTableWidgetItem(f"{available:.2f}")
            avail_item.setForeground(Qt.blue)  # Blue color for available stock
            self.table.setItem(i, 4, avail_item)
            
            # Unit
            self.table.setItem(i, 5, QTableWidgetItem(product.get("unit", "pcs")))
            
            # Price
            price = product.get("selling_price", 0)
            self.table.setItem(i, 6, QTableWidgetItem(f"₦{price:,.2f}"))
            
            # Margin %
            margin_pct = product.get("margin_pct", 0)
            margin_item = QTableWidgetItem(f"{margin_pct:.1f}%")
            if margin_pct < 0:
                margin_item.setForeground(Qt.red)
            elif margin_pct < 15:
                margin_item.setForeground(Qt.yellow)
            else:
                margin_item.setForeground(Qt.green)
            margin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 7, margin_item)
            
            # Status
            if product.get("is_low_stock"):
                status_text = "⚠️ Low Stock"
            elif current_stock > 0:
                status_text = "✓ In Stock"
            else:
                status_text = "❌ Out"
            status_item = QTableWidgetItem(status_text)
            self.table.setItem(i, 8, status_item)
            
            # Expiry (if applicable)
            if product.get("has_expiry"):
                shelf_life = product.get("shelf_life_days")
                expiry_text = f"{shelf_life}d" if shelf_life else "Yes"
                expiry_item = QTableWidgetItem(expiry_text)
                expiry_item.setForeground(Qt.red)  # Red for expiry items
            else:
                expiry_item = QTableWidgetItem("—")
            self.table.setItem(i, 9, expiry_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)
            
            def create_action_btn(text, tooltip, callback, color="#4dabf7"):
                btn = QPushButton(text)
                btn.setFixedSize(28, 28)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setToolTip(tooltip)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {color}22;
                        border: 1px solid {color}44;
                        border-radius: 4px;
                        font-size: 12px;
                        color: {color};
                        padding: 0px;
                    }}
                    QPushButton:hover {{
                        background: {color}44;
                        border: 1px solid {color};
                    }}
                """)
                btn.clicked.connect(callback)
                return btn
            
            can_manage = api_client.has_permission("manage_inventory")
            is_admin = api_client.user_role in ["super_admin", "admin"]
            
            edit_btn = create_action_btn("✏️", "Edit Product", lambda _, p=product: self._on_edit_product(p), "#4dabf7")
            edit_btn.setEnabled(can_manage)
            actions_layout.addWidget(edit_btn)
            
            adjust_btn = create_action_btn("📦", "Adjust Stock", lambda _, p=product: self._on_adjust_stock(p), "#ffd43b")
            adjust_btn.setEnabled(can_manage)
            actions_layout.addWidget(adjust_btn)
            
            history_btn = create_action_btn("📜", "View History", lambda _, p=product: self._on_view_history(p), "#63e6be")
            actions_layout.addWidget(history_btn)
            
            # Unavailable toggle button (admin only)
            is_active = product.get("is_active", True)
            unavail_text = "🔓 Activate" if not is_active else "🔒 Deactivate"
            unavail_tooltip = "Activate product" if not is_active else "Deactivate product"
            unavail_color = "#ffa94d" if not is_active else "#868e96"
            unavail_btn = create_action_btn(unavail_text, unavail_tooltip, 
                                          lambda _, p=product: self._on_toggle_availability(p), unavail_color)
            unavail_btn.setEnabled(is_admin)
            if not is_admin:
                unavail_btn.setStyleSheet(unavail_btn.styleSheet() + "QPushButton { opacity: 0.4; }")
            actions_layout.addWidget(unavail_btn)
            
            delete_btn = create_action_btn("🗑️", "Delete Permanently", lambda _, p=product: self._on_delete_product(p), "#ff6b6b")
            delete_btn.setEnabled(is_admin)
            if not is_admin:
                delete_btn.setStyleSheet(delete_btn.styleSheet() + "QPushButton { opacity: 0.4; }")
            actions_layout.addWidget(delete_btn)
            
            actions_layout.addStretch()
            self.table.setCellWidget(i, 10, actions_widget)
    
    # ============== Selection & Bulk Operations ==============
    
    def _on_table_selection_changed(self):
        """Update bulk operations UI based on selection."""
        selected_rows = self.table.selectionModel().selectedRows()
        self._update_bulk_ui(len(selected_rows))
    
    def _on_item_checkbox_changed(self, product, state):
        """Handle item checkbox change."""
        if state == Qt.Checked:
            self.selected_items.add(product["id"])
        else:
            self.selected_items.discard(product["id"])
        self._update_bulk_ui(len(self.selected_items))
    
    def _on_select_all(self):
        """Handle select all checkbox."""
        is_checked = self.select_all_checkbox.isChecked()
        
        for i in range(self.table.rowCount()):
            checkbox = self.table.cellWidget(i, 0)
            if isinstance(checkbox, QCheckBox):
                checkbox.blockSignals(True)
                checkbox.setCheckState(Qt.Checked if is_checked else Qt.Unchecked)
                checkbox.blockSignals(False)
        
        if is_checked:
            self.selected_items = {p["id"] for p in self.products}
        else:
            self.selected_items.clear()
        
        self._update_bulk_ui(len(self.selected_items))
    
    def _update_bulk_ui(self, count):
        """Update bulk operations UI."""
        self.bulk_label.setText(f"{count} selected")
        self.bulk_delete_btn.setEnabled(count > 0)
    
    def _on_bulk_delete(self):
        """Handle bulk delete."""
        count = len(self.selected_items)
        reply = QMessageBox.warning(
            self,
            "Confirm Bulk Delete",
            f"Are you sure you want to delete {count} product(s)?\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            is_admin = api_client.user_role in ["super_admin", "admin"]
            if not is_admin:
                QMessageBox.warning(self, "Permission Denied", "Only admins can delete products")
                return
            
            self.bulk_delete_btn.setEnabled(False)
            self.bulk_delete_thread = BulkDeleteThread(list(self.selected_items))
            self.bulk_delete_thread.delete_complete.connect(self._on_bulk_delete_complete)
            self.bulk_delete_thread.error_occurred.connect(self._on_bulk_delete_error)
            self.bulk_delete_thread.start()
    
    def _on_bulk_delete_complete(self, count):
        """Handle bulk delete completion."""
        QMessageBox.information(self, "Success", f"{count} product(s) deleted successfully")
        self.selected_items.clear()
        self._update_bulk_ui(0)
        self._load_data()
    
    def _on_bulk_delete_error(self, error_msg):
        """Handle bulk delete error."""
        QMessageBox.critical(self, "Error", f"Bulk delete failed: {error_msg}")
        self.bulk_delete_btn.setEnabled(True)
    
    # ============== Individual Item Actions ==============
    
    def _on_add_product(self):
        """Show dialog to add a new product."""
        try:
            dialog = ProductDialog(self)
            if dialog.exec() == QDialog.Accepted:
                # Reload data after successful creation
                self._load_data()
                QMessageBox.information(self, "Success", "Product added successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open product dialog: {str(e)}")
    
    def _on_edit_product(self, product: dict):
        """Show dialog to edit an existing product."""
        try:
            if not api_client.has_permission("manage_inventory"):
                QMessageBox.warning(self, "Permission Denied", "You don't have permission to edit products")
                return
            
            product_name = product.get("name", "Unknown")
            dialog = ProductDialog(self, product)
            if dialog.exec() == QDialog.Accepted:
                # Reload data after successful update
                self._load_data()
                QMessageBox.information(self, "Success", f"'{product_name}' updated successfully!")
        except APIError as e:
            QMessageBox.critical(self, "API Error", f"Failed to edit product: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
    
    def _on_adjust_stock(self, product: dict):
        """Show dialog to adjust stock levels."""
        try:
            if not api_client.has_permission("manage_inventory"):
                QMessageBox.warning(self, "Permission Denied", "You don't have permission to adjust stock")
                return
            
            product_name = product.get("name", "Unknown")
            dialog = StockDialog(self, product)
            if dialog.exec() == QDialog.Accepted:
                # Reload data after successful adjustment
                self._load_data()
                QMessageBox.information(self, "Success", f"Stock for '{product_name}' adjusted successfully!")
        except APIError as e:
            QMessageBox.critical(self, "API Error", f"Failed to adjust stock: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
    
    def _on_view_history(self, product: dict):
        """Show product movement history."""
        try:
            product_name = product.get("name", "Unknown")
            self.setWindowTitle(f"Inventory Management - Loading {product_name} History...")
            
            dialog = HistoryDialog(self, product)
            dialog.exec()
            
            self.setWindowTitle("Inventory Management")
        except APIError as e:
            QMessageBox.critical(self, "API Error", f"Failed to load history: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to view history: {str(e)}")
    
    def _on_toggle_availability(self, product: dict):
        """Toggle product availability (activate/deactivate)."""
        try:
            is_admin = api_client.user_role in ["super_admin", "admin"]
            if not is_admin:
                QMessageBox.warning(self, "Permission Denied", 
                    "Only administrators can change product status")
                return
            
            product_name = product.get("name", "Unknown")
            is_active = product.get("is_active", True)
            
            if is_active:
                # Deactivate the product
                message = f"Do you want to deactivate '{product_name}'?\n\n"
                message += "It will be hidden from sales operations.\n"
                message += f"Current stock: {product.get('current_stock', 0)} units\n\n"
                message += "⚠️ The product data will be preserved for historical records."
                action = "deactivate"
                new_status = False
                success_msg = "Product has been deactivated"
            else:
                # Activate the product
                message = f"Do you want to reactivate '{product_name}'?\n\n"
                message += "It will be visible in sales and inventory operations again."
                action = "activate"
                new_status = True
                success_msg = "Product has been activated"
            
            reply = QMessageBox.question(
                self, f"Confirm {action.capitalize()}",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                try:
                    # Send update to server
                    api_client.patch(f"/inventory/items/{product['id']}", {
                        "is_active": new_status
                    })
                    QMessageBox.information(self, "Success", success_msg)
                    self._load_data()
                except APIError as e:
                    QMessageBox.critical(self, "Update Failed", f"Error: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
    
    def _on_delete_product(self, product):
        """Handle product deletion/deactivation."""
        try:
            is_admin = api_client.user_role in ["super_admin", "admin"]
            if not is_admin:
                QMessageBox.warning(self, "Permission Denied", 
                    "Only administrators can delete products")
                return
            
            product_name = product.get("name", "Unknown")
            current_stock = product.get("current_stock", 0)
            
            # Additional warnings for products with stock
            message = f"Are you sure you want to delete '{product_name}'?\n\n"
            
            if current_stock > 0:
                message += f"⚠️ WARNING: This product has {current_stock} units in stock.\n"
                message += "Please adjust stock before deletion.\n\n"
                
                reply = QMessageBox.warning(
                    self, "Cannot Delete - Stock Available",
                    message + "This action cannot be performed.",
                    QMessageBox.Ok
                )
                return
            
            message += "This action will permanently remove the product from the system."
            
            # Final confirmation
            reply = QMessageBox.warning(
                self, "Confirm Delete",
                message,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No  # Default to No for safety
            )
            
            if reply == QMessageBox.Yes:
                # Disable button during operation
                sender = self.sender()
                if sender:
                    sender.setEnabled(False)
                    sender.setText("Deleting...")
                
                try:
                    api_client.delete_item(product["id"])
                    QMessageBox.information(self, "Success", f"'{product_name}' has been deleted successfully!")
                    self._load_data()
                except APIError as e:
                    QMessageBox.critical(self, "Delete Failed", f"Error: {e.message}")
                finally:
                    if sender:
                        sender.setEnabled(True)
                        sender.setText("🗑️ Delete")
                        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
    
    # ============== Bulk Operations ==============
    
    def _on_export_inventory(self):
        """Export inventory to CSV with progress feedback."""
        try:
            # Get default filename with date
            default_name = f"inventory_export_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            path, _ = QFileDialog.getSaveFileName(
                self, "Export Inventory", default_name, "CSV Files (*.csv)"
            )
            
            if not path:
                return
            
            # Show progress
            progress_text = "Exporting inventory..."
            self.stats_label.setText(progress_text)
            self.refresh_btn.setEnabled(False)
            
            try:
                # Fetch export data
                data = api_client.export_inventory()
                
                # Write to file
                with open(path, "wb") as f:
                    f.write(data)
                
                # Calculate file size
                file_size = len(data) / 1024  # KB
                file_size_text = f"{file_size:.1f} KB" if file_size < 1024 else f"{file_size/1024:.1f} MB"
                
                # Get item count from CSV
                csv_text = data.decode('utf-8')
                lines = csv_text.strip().split('\n')
                item_count = len(lines) - 1  # Subtract header
                
                success_msg = (
                    f"✓ Export Successful!\n\n"
                    f"File: {Path(path).name}\n"
                    f"Items: {item_count}\n"
                    f"Size: {file_size_text}\n\n"
                    f"Saved to:\n{path}"
                )
                QMessageBox.information(self, "Export Complete", success_msg)
                
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Error: {str(e)}")
            finally:
                self.refresh_btn.setEnabled(True)
                self._load_data()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open export dialog: {str(e)}")
    
    def _on_import_inventory(self):
        """Import inventory from CSV using the import dialog."""
        try:
            dialog = ImportDialog(self)
            if dialog.exec() == QDialog.Accepted:
                # Check if import was successful
                result = dialog.import_result
                if result and result.get('success'):
                    # Reload data after successful import
                    self._load_data()
                    
                    # Show summary
                    imported = result.get('imported_count', 0)
                    updated = result.get('updated_count', 0)
                    total = imported + updated
                    
                    summary_msg = (
                        f"✓ Import Complete!\n\n"
                        f"Items Imported: {imported}\n"
                        f"Items Updated: {updated}\n"
                        f"Total: {total}\n\n"
                        f"Inventory has been updated."
                    )
                    QMessageBox.information(self, "Import Successful", summary_msg)
                elif result:
                    # Partial success - reload anyway
                    self._load_data()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to import: {str(e)}")
    
    def _on_download_template(self):
        """Download import template."""
        try:
            default_name = f"inventory_template_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Import Template", default_name, "CSV Files (*.csv)"
            )
            if not path:
                return
            
            self.stats_label.setText("Downloading template...")
            self.refresh_btn.setEnabled(False)
            
            try:
                data = api_client.get_import_template()
                with open(path, "wb") as f:
                    f.write(data)
                
                success_msg = (
                    f"✓ Template Downloaded!\n\n"
                    f"File: {Path(path).name}\n\n"
                    f"Use this template to prepare your inventory data.\n"
                    f"Required columns are marked with *"
                )
                QMessageBox.information(self, "Success", success_msg)
            except Exception as e:
                QMessageBox.critical(self, "Download Failed", f"Error: {str(e)}")
            finally:
                self.refresh_btn.setEnabled(True)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed: {str(e)}")
