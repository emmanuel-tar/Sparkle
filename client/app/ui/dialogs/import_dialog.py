"""
Import Dialog

Dialog for importing inventory from CSV with progress tracking and error reporting.
"""

from typing import Dict, Any, Optional
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFileDialog, QProgressBar, QTextEdit, QTabWidget, QWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor

from app.api import api_client


class ImportWorker(QThread):
    """Worker thread for importing inventory."""
    
    progress = Signal(int)
    finished = Signal(dict)  # Result dict
    error = Signal(str)
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        """Run the import in background."""
        try:
            result = api_client.import_inventory(self.file_path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ImportDialog(QDialog):
    """Dialog for importing inventory CSV."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Import Inventory")
        self.setGeometry(100, 100, 900, 600)
        self.selected_file = None
        self.import_result = None
        self.worker = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # File Selection Section
        file_section = QVBoxLayout()
        
        title = QLabel("Import Inventory from CSV")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        file_section.addWidget(title)
        
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        self.file_label.setStyleSheet("color: #888888;")
        file_layout.addWidget(self.file_label, 1)
        
        self.browse_btn = QPushButton("📁 Browse...")
        self.browse_btn.setMinimumWidth(120)
        self.browse_btn.clicked.connect(self._on_browse)
        file_layout.addWidget(self.browse_btn)
        
        self.template_btn = QPushButton("📝 Download Template")
        self.template_btn.setMinimumWidth(150)
        self.template_btn.clicked.connect(self._on_download_template)
        file_layout.addWidget(self.template_btn)
        
        file_section.addLayout(file_layout)
        layout.addLayout(file_section)
        
        # Info Text
        info = QLabel(
            "Supported columns: SKU*, Name*, Selling Price*, Location, Barcode, Description, "
            "Category, Supplier, Stock, Min Stock, Cost Price, Unit\n"
            "* Required fields"
        )
        info.setStyleSheet("color: #666666; font-size: 11px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Progress Section
        progress_layout = QVBoxLayout()
        progress_layout.addWidget(QLabel("Progress:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        layout.addLayout(progress_layout)
        
        # Tabs for Results
        self.tabs = QTabWidget()
        self.tabs.setVisible(False)
        
        # Summary tab
        summary_widget = QWidget()
        summary_layout = QVBoxLayout(summary_widget)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        self.tabs.addTab(summary_widget, "Summary")
        
        # Errors tab
        errors_widget = QWidget()
        errors_layout = QVBoxLayout(errors_widget)
        self.errors_table = QTableWidget()
        self.errors_table.setColumnCount(2)
        self.errors_table.setHorizontalHeaderLabels(["Row", "Error Message"])
        self.errors_table.horizontalHeader().setStretchLastSection(True)
        self.errors_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        errors_layout.addWidget(self.errors_table)
        self.tabs.addTab(errors_widget, "Errors")
        
        layout.addWidget(self.tabs)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.import_btn = QPushButton("⬆️ Import")
        self.import_btn.setObjectName("primary")
        self.import_btn.setMinimumWidth(120)
        self.import_btn.setEnabled(False)
        self.import_btn.clicked.connect(self._on_import)
        button_layout.addWidget(self.import_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.setMinimumWidth(100)
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)
        
        layout.addLayout(button_layout)
    
    def _on_browse(self):
        """Browse for CSV file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)"
        )
        if file_path:
            self.selected_file = file_path
            file_name = Path(file_path).name
            self.file_label.setText(f"📄 {file_name}")
            self.file_label.setStyleSheet("color: #000000;")
            self.import_btn.setEnabled(True)
    
    def _on_download_template(self):
        """Download import template."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Template", "inventory_template.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                data = api_client.get_import_template()
                Path(path).write_bytes(data)
                QMessageBox.information(self, "Success", f"Template saved to:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to download template:\n{e}")
    
    def _on_import(self):
        """Start the import process."""
        if not self.selected_file:
            QMessageBox.warning(self, "Warning", "Please select a CSV file first")
            return
        
        # Disable buttons and show progress
        self.import_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.tabs.setVisible(False)
        
        # Start worker thread
        self.worker = ImportWorker(self.selected_file)
        self.worker.finished.connect(self._on_import_finished)
        self.worker.error.connect(self._on_import_error)
        self.worker.start()
    
    def _on_import_finished(self, result: Dict[str, Any]):
        """Handle import completion."""
        self.import_result = result
        self.progress_bar.setValue(100)
        self._update_results(result)
        
        # Show results
        self.tabs.setVisible(True)
        self.tabs.setCurrentIndex(0)  # Show summary first
        
        # Re-enable buttons
        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        
        # Show success/partial message
        if result.get("success"):
            QMessageBox.information(
                self, 
                "Import Complete",
                f"✓ Successfully imported {result.get('imported_count', 0)} items\n"
                f"  and updated {result.get('updated_count', 0)} items"
            )
        else:
            errors = result.get("errors", [])
            QMessageBox.warning(
                self,
                "Import Completed with Errors",
                f"Imported: {result.get('imported_count', 0)} items\n"
                f"Updated: {result.get('updated_count', 0)} items\n"
                f"Errors: {len(errors)}\n\n"
                f"Check the 'Errors' tab for details."
            )
    
    def _on_import_error(self, error_msg: str):
        """Handle import error."""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        QMessageBox.critical(self, "Import Failed", f"Error:\n{error_msg}")
    
    def _update_results(self, result: Dict[str, Any]):
        """Update results display."""
        # Update summary
        summary = f"""
Import Results:
━━━━━━━━━━━━━━━━━━━━━━━━━━
Status: {'✓ Success' if result.get('success') else '⚠ Partial'}
File: {Path(self.selected_file).name}
Encoding: {result.get('encoding_used', 'Unknown')}

Items Imported: {result.get('imported_count', 0)}
Items Updated: {result.get('updated_count', 0)}
Total Processed: {result.get('total_processed', 0)}
Errors: {len(result.get('errors', []))}

Message: {result.get('message', '')}
        """
        self.summary_text.setText(summary)
        
        # Update errors table
        errors = result.get("errors", [])
        self.errors_table.setRowCount(len(errors))
        
        for row_idx, error in enumerate(errors):
            # Parse error format: "Row X: message"
            error_str = str(error)
            if "Row" in error_str:
                parts = error_str.split(":", 1)
                row_text = parts[0].strip()
                msg_text = parts[1].strip() if len(parts) > 1 else error_str
            else:
                row_text = str(row_idx + 1)
                msg_text = error_str
            
            # Row number
            row_item = QTableWidgetItem(row_text)
            row_item.setForeground(QColor("#d9534f"))
            self.errors_table.setItem(row_idx, 0, row_item)
            
            # Error message
            msg_item = QTableWidgetItem(msg_text)
            msg_item.setForeground(QColor("#d9534f"))
            self.errors_table.setItem(row_idx, 1, msg_item)
