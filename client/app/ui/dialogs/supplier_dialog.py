"""
Supplier Dialog

Modal for adding or editing suppliers.
"""

from typing import Optional, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QFormLayout, QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client, APIError


class SupplierDialog(QDialog):
    """Dialog for creating or updating a supplier."""
    
    def __init__(self, parent=None, supplier_data: Optional[Dict] = None):
        super().__init__(parent)
        self.supplier_data = supplier_data
        self.is_edit = supplier_data is not None
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the dialog UI."""
        self.setWindowTitle("Edit Supplier" if self.is_edit else "Add New Supplier")
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Supplier Information")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)
        
        # Form
        form_frame = QFrame()
        form_layout = QFormLayout(form_frame)
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setSpacing(12)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Acme Corp")
        if self.is_edit:
            self.name_input.setText(self.supplier_data.get("name", ""))
        form_layout.addRow("Supplier Name *:", self.name_input)
        
        self.contact_name_input = QLineEdit()
        self.contact_name_input.setPlaceholderText("Contact person name")
        if self.is_edit:
            self.contact_name_input.setText(self.supplier_data.get("contact_name", ""))
        form_layout.addRow("Contact Person:", self.contact_name_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")
        if self.is_edit:
            self.email_input.setText(self.supplier_data.get("email", ""))
        form_layout.addRow("Email:", self.email_input)
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Phone number")
        if self.is_edit:
            self.phone_input.setText(self.supplier_data.get("phone", ""))
        form_layout.addRow("Phone:", self.phone_input)
        
        self.website_input = QLineEdit()
        self.website_input.setPlaceholderText("https://...")
        if self.is_edit:
            self.website_input.setText(self.supplier_data.get("website", ""))
        form_layout.addRow("Website:", self.website_input)
        
        self.tax_id_input = QLineEdit()
        self.tax_id_input.setPlaceholderText("Tax or TIN number")
        if self.is_edit:
            self.tax_id_input.setText(self.supplier_data.get("tax_id", ""))
        form_layout.addRow("Tax ID:", self.tax_id_input)
        
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(80)
        if self.is_edit:
            self.address_input.setPlainText(self.supplier_data.get("address", ""))
        form_layout.addRow("Address:", self.address_input)
        
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        if self.is_edit:
            self.notes_input.setPlainText(self.supplier_data.get("notes", ""))
        form_layout.addRow("Notes:", self.notes_input)
        
        layout.addWidget(form_frame)
        
        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Supplier")
        self.save_btn.setObjectName("primary")
        self.save_btn.setMinimumHeight(36)
        self.save_btn.clicked.connect(self._on_save)
        btns.addWidget(self.save_btn)
        
        layout.addLayout(btns)
        
    def _on_save(self):
        """Validate and save supplier data."""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Supplier Name is required.")
            return
            
        # Prepare data
        data = {
            "name": name,
            "contact_name": self.contact_name_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "phone": self.phone_input.text().strip() or None,
            "website": self.website_input.text().strip() or None,
            "tax_id": self.tax_id_input.text().strip() or None,
            "address": self.address_input.toPlainText().strip() or None,
            "notes": self.notes_input.toPlainText().strip() or None,
        }
        
        try:
            if self.is_edit:
                api_client.update_supplier(self.supplier_data["id"], data)
            else:
                api_client.create_supplier(data)
                
            self.accept()
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to save supplier: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
