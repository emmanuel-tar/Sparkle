"""
Customers View

Displays customer database, loyalty info, and purchase summary.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.api import api_client


class CustomersView(QWidget):
    """View showing the customer list and management tools."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.customers = []
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Setup the customers view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header Section
        header = QHBoxLayout()
        
        left_header = QVBoxLayout()
        title = QLabel("Customer Directory")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        left_header.addWidget(title)
        
        subtitle = QLabel("Manage your customer relationship and loyalty program.")
        subtitle.setStyleSheet("color: #888888;")
        left_header.addWidget(subtitle)
        header.addLayout(left_header)
        
        header.addStretch()
        
        self.add_btn = QPushButton(" New Customer")
        self.add_btn.setObjectName("primary")
        self.add_btn.setMinimumHeight(40)
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
        self.search_input.setPlaceholderText("Search by Name, Phone, or Loyalty Card...")
        self.search_input.setMinimumHeight(35)
        self.search_input.textChanged.connect(self._on_search)
        filter_bar.addWidget(self.search_input, 3)
        
        self.tier_filter = QComboBox()
        self.tier_filter.addItems(["All Tiers", "Bronze", "Silver", "Gold", "Platinum", "Diamond"])
        self.tier_filter.setMinimumHeight(35)
        filter_bar.addWidget(self.tier_filter, 1)
        
        layout.addLayout(filter_bar)
        
        # Customers Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Phone", "Loyalty Tier", "Points", "Total Spent", "Last Visit", "Actions"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
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
        
        # Stats Footer
        self.stats_label = QLabel("Showing 0 customers")
        self.stats_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.stats_label)

    def _load_data(self):
        """Load customer data from API."""
        try:
            response = api_client.get("/customers/search") # The endpoint exists but might return empty
            if response and isinstance(response, list):
                self.customers = response
                self._update_table(self.customers)
            else:
                self.customers = []
                self._update_table([])
        except Exception as e:
            print(f"Error loading customers: {e}")
            self.stats_label.setText("Error loading customers")

    def _update_table(self, customers):
        """Update table items."""
        self.table.setRowCount(0)
        for i, customer in enumerate(customers):
            self.table.insertRow(i)
            
            # Name
            name = f"{customer.get('first_name', '')} {customer.get('last_name', '')}"
            self.table.setItem(i, 0, QTableWidgetItem(name))
            
            # Phone
            self.table.setItem(i, 1, QTableWidgetItem(customer.get("phone", "")))
            
            # Tier
            tier = customer.get("loyalty_tier", "bronze").title()
            tier_item = QTableWidgetItem(tier)
            # Color code tiers
            tier_colors = {
                "Bronze": "#cd7f32",
                "Silver": "#c0c0c0",
                "Gold": "#ffd700",
                "Platinum": "#e5e4e2",
                "Diamond": "#b9f2ff"
            }
            if tier in tier_colors:
                tier_item.setForeground(Qt.white)
                # tier_item.setBackground(QColor(tier_colors[tier]))
            
            self.table.setItem(i, 2, tier_item)
            
            # Points
            self.table.setItem(i, 3, QTableWidgetItem(str(customer.get("loyalty_points", 0))))
            
            # Total Spent
            spent = customer.get("total_spent", 0)
            self.table.setItem(i, 4, QTableWidgetItem(f"₦{spent:,.2f}"))
            
            # Last Visit
            last_visit = customer.get("last_purchase_date", "Never")
            if last_visit and last_visit != "Never":
                last_visit = last_visit.split("T")[0] # Simple date formatting
            self.table.setItem(i, 5, QTableWidgetItem(str(last_visit)))
            
            # Actions
            edit_btn = QPushButton("View")
            edit_btn.setMinimumHeight(24)
            edit_btn.setFixedWidth(60)
            self.table.setCellWidget(i, 6, edit_btn)
            
        self.stats_label.setText(f"Showing {len(customers)} customers")

    def _on_search(self):
        """Filter customer list."""
        query = self.search_input.text().lower()
        if not query:
            self._update_table(self.customers)
            return
            
        filtered = [
            c for c in self.customers
            if query in c.get("first_name", "").lower() or 
               query in c.get("last_name", "").lower() or 
               query in c.get("phone", "").lower() or
               query in c.get("loyalty_card_number", "").lower()
        ]
        self._update_table(filtered)
