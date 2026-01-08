"""
Categories View

Management of product categories.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client, APIError


class CategoryDialog(QDialog):
    """Dialog for creating or editing a category."""
    
    def __init__(self, parent=None, category_data=None):
        super().__init__(parent)
        self.category_data = category_data
        self.is_edit = category_data is not None
        self._setup_ui()
        
    def _setup_ui(self):
        self.setWindowTitle("Edit Category" if self.is_edit else "Add Category")
        self.setFixedWidth(400)
        
        layout = QVBoxLayout(self)
        form = QFormLayout()
        
        self.name_input = QLineEdit()
        if self.is_edit:
            self.name_input.setText(self.category_data.get("name", ""))
        form.addRow("Name *:", self.name_input)
        
        self.desc_input = QLineEdit()
        if self.is_edit:
            self.desc_input.setText(self.category_data.get("description", ""))
        form.addRow("Description:", self.desc_input)
        
        layout.addLayout(form)
        
        btns = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("primary")
        self.save_btn.clicked.connect(self._on_save)
        btns.addStretch()
        btns.addWidget(self.save_btn)
        layout.addLayout(btns)
        
    def _on_save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Name is required")
            return
            
        data = {
            "name": name,
            "description": self.desc_input.text().strip() or None
        }
        
        try:
            if self.is_edit:
                api_client.patch(f"inventory/categories/{self.category_data['id']}", data)
            else:
                api_client.post("inventory/categories", data)
            self.accept()
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to save: {e.message}")


class CategoriesView(QWidget):
    """View showing categories management table."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.categories = []
        self._setup_ui()
        self._load_data()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30,30,30,30)
        layout.setSpacing(20)
        
        header = QHBoxLayout()
        title = QLabel("Product Categories")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        header.addWidget(title)
        header.addStretch()
        
        self.add_btn = QPushButton(" Add Category")
        self.add_btn.setObjectName("primary")
        self.add_btn.setMinimumHeight(40)
        self.add_btn.clicked.connect(self._on_add)
        
        # Permission check
        if not api_client.has_permission("manage_inventory"):
            self.add_btn.setEnabled(False)
            self.add_btn.setToolTip("You do not have permission to manage categories")
            
        header.addWidget(self.add_btn)
        layout.addLayout(header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Description", "Products", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)
        
    def _load_data(self):
        try:
            self.categories = api_client.get("inventory/categories")
            self._update_table()
        except Exception as e:
            print(f"Error: {e}")
            
    def _update_table(self):
        self.table.setRowCount(0)
        for i, cat in enumerate(self.categories):
            self.table.insertRow(i)
            self.table.setItem(i, 0, QTableWidgetItem(cat.get("name", "")))
            self.table.setItem(i, 1, QTableWidgetItem(cat.get("description", "")))
            
            # Product Count
            count_item = QTableWidgetItem(str(cat.get("product_count", 0)))
            count_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, count_item)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setEnabled(api_client.has_permission("manage_inventory"))
            edit_btn.clicked.connect(lambda checked, c=cat: self._on_edit(c))
            self.table.setCellWidget(i, 3, edit_btn)
            
    def _on_add(self):
        if CategoryDialog(self).exec():
            self._load_data()
            
    def _on_edit(self, cat):
        if CategoryDialog(self, cat).exec():
            self._load_data()
