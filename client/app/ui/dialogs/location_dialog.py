"""
Location Dialog

Modal for adding or editing warehouses and store locations.
"""

from typing import Optional, Dict
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QGroupBox, QCheckBox, 
    QTextEdit, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client, APIError


class LocationDialog(QDialog):
    """Dialog for creating or updating a physical location (Warehouse/Store)."""
    
    def __init__(self, parent=None, location_data: Optional[Dict] = None):
        super().__init__(parent)
        self.location_data = location_data
        self.is_edit = location_data is not None
        self._setup_ui()
        
    def _setup_ui(self):
        self.setWindowTitle("Edit Location" if self.is_edit else "Add New Location")
        self.setFixedWidth(450)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("Location Details")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)
        
        form_group = QGroupBox("General Information")
        form_layout = QFormLayout(form_group)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Lagos Mainland Store")
        if self.is_edit:
            self.name_input.setText(self.location_data.get("name", ""))
        form_layout.addRow("Name *:", self.name_input)
        
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Unique short code, e.g. WH-01")
        if self.is_edit:
            self.code_input.setText(self.location_data.get("code", ""))
            self.code_input.setReadOnly(True)
        form_layout.addRow("Code *:", self.code_input)
        
        self.is_hq = QCheckBox("Mark as Headquarters")
        if self.is_edit:
            self.is_hq.setChecked(self.location_data.get("is_headquarters", False))
        form_layout.addRow("", self.is_hq)
        
        layout.addWidget(form_group)
        
        contact_group = QGroupBox("Contact Details")
        contact_layout = QFormLayout(contact_group)
        
        self.phone_input = QLineEdit()
        if self.is_edit:
            self.phone_input.setText(self.location_data.get("phone", ""))
        contact_layout.addRow("Phone:", self.phone_input)
        
        self.email_input = QLineEdit()
        if self.is_edit:
            self.email_input.setText(self.location_data.get("email", ""))
        contact_layout.addRow("Email:", self.email_input)
        
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(80)
        # Handle complex address field if it's a dict
        addr = self.location_data.get("address") if self.is_edit else None
        if isinstance(addr, dict):
            # Simple string representation for now or just take a 'street' field
            self.address_input.setPlainText(addr.get("street", ""))
        elif isinstance(addr, str):
            self.address_input.setPlainText(addr)
            
        contact_layout.addRow("Address:", self.address_input)
        
        layout.addWidget(contact_group)
        
        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btns.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Location")
        self.save_btn.setObjectName("primary")
        self.save_btn.setMinimumHeight(36)
        self.save_btn.clicked.connect(self._on_save)
        btns.addWidget(self.save_btn)
        
        layout.addLayout(btns)
        
    def _on_save(self):
        name = self.name_input.text().strip()
        code = self.code_input.text().strip()
        
        if not name or not code:
            QMessageBox.warning(self, "Validation Error", "Name and Code are required.")
            return
            
        data = {
            "name": name,
            "code": code,
            "phone": self.phone_input.text().strip() or None,
            "email": self.email_input.text().strip() or None,
            "is_headquarters": self.is_hq.isChecked(),
            "address": {"street": self.address_input.toPlainText().strip()} if self.address_input.toPlainText() else None
        }
        
        try:
            if self.is_edit:
                api_client.update_location(self.location_data["id"], data)
            else:
                api_client.create_location(data)
            self.accept()
        except APIError as e:
            QMessageBox.critical(self, "Error", f"Failed to save location: {e.message}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
