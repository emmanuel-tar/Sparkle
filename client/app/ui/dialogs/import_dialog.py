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
        self.setGeometry(100, 100, 1000, 700)
        self.selected_file = None
        self.import_result = None
        self.worker = None
        self.file_preview = None
        
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
            
            # Get file info
            file_obj = Path(file_path)
            file_size = file_obj.stat().st_size
            file_size_text = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / (1024 * 1024):.1f} MB"
            
            # Show file info
            self.file_label.setText(f"📄 {file_name} ({file_size_text})")
            self.file_label.setStyleSheet("color: #000000;")
            
            # Try to preview file
            self._preview_file(file_path)
            
            # Enable import button
            self.import_btn.setEnabled(True)
    
    def _preview_file(self, file_path: str):
        """Preview the CSV file to validate format."""
        try:
            import csv
            from pathlib import Path
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            if not rows:
                QMessageBox.warning(self, "Invalid File", "CSV file is empty")
                self.selected_file = None
                self.import_btn.setEnabled(False)
                return
            
            # Get header and data rows
            header = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            
            # Check for required columns (SKU, Name, Selling Price)
            required_cols = {'sku', 'name', 'selling_price'}
            header_lower = [h.lower().strip() for h in header]
            missing_cols = required_cols - set(header_lower)
            
            if missing_cols:
                msg = f"Missing required columns: {', '.join(missing_cols)}"
                QMessageBox.warning(self, "Invalid CSV Format", msg)
                self.selected_file = None
                self.import_btn.setEnabled(False)
                return
            
            # Show preview info
            preview_msg = (
                f"✓ CSV Format Valid\n\n"
                f"Columns: {len(header)}\n"
                f"Rows: {len(data_rows)}\n"
                f"Header: {', '.join(header[:5])}"
                f"{'...' if len(header) > 5 else ''}\n\n"
                f"Ready to import {len(data_rows)} items."
            )
            QMessageBox.information(self, "File Preview", preview_msg)
            
        except UnicodeDecodeError:
            QMessageBox.warning(self, "Encoding Error", 
                "Unable to read file. Please ensure it's saved as UTF-8 CSV.")
            self.selected_file = None
            self.import_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.warning(self, "Preview Error", f"Error reading file: {str(e)}")
            self.selected_file = None
            self.import_btn.setEnabled(False)
    
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
        
        # Final confirmation
        file_name = Path(self.selected_file).name
        confirm = QMessageBox.question(
            self, "Confirm Import",
            f"Import data from:\n{file_name}\n\n"
            f"New items will be created, existing items will be updated.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if confirm != QMessageBox.Yes:
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
        """Handle import completion with detailed results."""
        self.import_result = result
        self.progress_bar.setValue(100)
        self._update_results(result)
        
        # Show results
        self.tabs.setVisible(True)
        
        # Determine which tab to show
        if result.get("success"):
            self.tabs.setCurrentIndex(0)  # Show summary
        else:
            self.tabs.setCurrentIndex(1)  # Show errors
        
        # Re-enable buttons
        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        
        # Show result dialog
        imported = result.get('imported_count', 0)
        updated = result.get('updated_count', 0)
        errors = len(result.get('errors', []))
        
        if result.get("success"):
            success_msg = (
                f"✓ Import Successful!\n\n"
                f"Items Imported: {imported}\n"
                f"Items Updated: {updated}\n"
                f"Total: {imported + updated}"
            )
            QMessageBox.information(self, "Import Complete", success_msg)
        else:
            error_msg = (
                f"⚠ Import Completed with Errors\n\n"
                f"Items Imported: {imported}\n"
                f"Items Updated: {updated}\n"
                f"Errors: {errors}\n\n"
                f"See 'Errors' tab for details."
            )
            QMessageBox.warning(self, "Import Results", error_msg)
    
    def _on_import_error(self, error_msg: str):
        """Handle import error with retry option."""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        
        # Parse error message for better display
        if "connection" in error_msg.lower():
            display_msg = "❌ Connection Error\n\nUnable to connect to server.\nPlease check:\n• Server is running\n• Network connection is active"
        elif "encoding" in error_msg.lower():
            display_msg = "❌ File Encoding Error\n\nFile must be saved as UTF-8 CSV"
        elif "invalid" in error_msg.lower():
            display_msg = f"❌ Invalid Data\n\n{error_msg}"
        else:
            display_msg = f"❌ Import Failed\n\n{error_msg}"
        
        reply = QMessageBox.critical(
            self, "Import Failed",
            display_msg + "\n\nWould you like to try again?",
            QMessageBox.Retry | QMessageBox.Cancel,
            QMessageBox.Retry
        )
        
        if reply == QMessageBox.Retry:
            self._on_import()
    
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
