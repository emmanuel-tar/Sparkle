"""
Sales History View

Displays past transactions, receipts, and order details.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QDateEdit, QFrame,
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from app.api import api_client


class SalesHistoryView(QWidget):
    """View showing historical sales data."""
    
    def __init__(self, user: dict):
        super().__init__()
        self.user = user
        self.sales = []
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Setup the sales history view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        left_header = QVBoxLayout()
        title = QLabel("Sales History")
        title.setFont(QFont("Segoe UI", 18, QFont.Bold))
        left_header.addWidget(title)
        
        subtitle = QLabel("Track and review all completed transactions.")
        subtitle.setStyleSheet("color: #888888;")
        left_header.addWidget(subtitle)
        header.addLayout(left_header)
        header.addStretch()
        
        self.refresh_btn = QPushButton(" Refresh")
        self.refresh_btn.setMinimumHeight(40)
        self.refresh_btn.clicked.connect(self._load_data)
        header.addWidget(self.refresh_btn)
        layout.addLayout(header)
        
        # Filters
        filter_bar = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Receipt # or Customer...")
        self.search_input.setMinimumHeight(35)
        self.search_input.textChanged.connect(self._on_search)
        filter_bar.addWidget(self.search_input, 2)
        
        filter_bar.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setMinimumHeight(35)
        filter_bar.addWidget(self.date_from)
        
        filter_bar.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setMinimumHeight(35)
        filter_bar.addWidget(self.date_to)
        
        layout.addLayout(filter_bar)
        
        # Sales Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Date", "Receipt #", "Customer", "Items", "Total", "Payment", "Status", "Actions"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        self.stats_label = QLabel("Showing 0 transactions")
        self.stats_label.setStyleSheet("color: #888888;")
        layout.addWidget(self.stats_label)

    def _load_data(self):
        """Load sales data from API."""
        try:
            response = api_client.get("/sales")
            if response and isinstance(response, list):
                self.sales = response
                self._update_table(self.sales)
            else:
                self.sales = []
                self._update_table([])
        except Exception as e:
            print(f"Error loading sales history: {e}")
            self.stats_label.setText("Error loading sales history")

    def _update_table(self, sales):
        """Update table content."""
        self.table.setRowCount(0)
        for i, sale in enumerate(sales):
            self.table.insertRow(i)
            
            # Date
            date_str = sale.get("created_at", "").split("T")[0]
            self.table.setItem(i, 0, QTableWidgetItem(date_str))
            
            # Receipt
            self.table.setItem(i, 1, QTableWidgetItem(sale.get("receipt_number", "")))
            
            # Customer
            customer = sale.get("customer")
            cust_name = f"{customer['first_name']} {customer['last_name']}" if customer else "Walk-in"
            self.table.setItem(i, 2, QTableWidgetItem(cust_name))
            
            # Items (count from local snapshot or relationship)
            items = sale.get("items_snapshot", []) or []
            self.table.setItem(i, 3, QTableWidgetItem(f"{len(items)} items"))
            
            # Total
            total = sale.get("total_amount", 0)
            self.table.setItem(i, 4, QTableWidgetItem(f"₦{total:,.2f}"))
            
            # Payment
            method = sale.get("payment_method", "cash").title()
            self.table.setItem(i, 5, QTableWidgetItem(method))
            
            # Status
            status = sale.get("status", "completed").title()
            status_item = QTableWidgetItem(status)
            if status == "Void":
                status_item.setForeground(Qt.red)
            elif status == "Completed":
                status_item.setForeground(Qt.green)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 6, status_item)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(6)
            
            is_admin = api_client.user_role in ["super_admin", "admin"]
            is_voided = sale.get("status") == "void"
            
            void_btn = QPushButton("Void")
            void_btn.setFixedSize(60, 24)
            void_btn.setCursor(Qt.PointingHandCursor)
            void_btn.setEnabled(is_admin and not is_voided)
            void_btn.setStyleSheet("""
                QPushButton {
                    background: #fff5f5;
                    border: 1px solid #ffc9c9;
                    border-radius: 4px;
                    color: #fa5252;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background: #ffe3e3;
                }
                QPushButton:disabled {
                    background: #f1f3f5;
                    border: 1px solid #e9ecef;
                    color: #adb5bd;
                }
            """)
            void_btn.clicked.connect(lambda _, s=sale: self._on_void_sale(s))
            actions_layout.addWidget(void_btn)
            actions_layout.addStretch()
            self.table.setCellWidget(i, 7, actions_widget)
            
        self.stats_label.setText(f"Showing {len(sales)} transactions")

    def _on_void_sale(self, sale):
        """Void a sale with confirmation."""
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Confirm Void",
            f"Are you sure you want to void receipt {sale['receipt_number']}?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                api_client.post(f"/sales/{sale['id']}/void")
                self._load_data()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to void sale: {e}")

    def _on_search(self):
        """Handle search."""
        query = self.search_input.text().lower()
        if not query:
            self._update_table(self.sales)
            return
            
        filtered = [
            s for s in self.sales
            if query in s.get("receipt_number", "").lower() or 
               (s.get("customer") and query in f"{s['customer']['first_name']} {s['customer']['last_name']}".lower())
        ]
        self._update_table(filtered)
