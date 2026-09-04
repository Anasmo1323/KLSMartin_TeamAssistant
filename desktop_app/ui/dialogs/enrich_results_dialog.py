import pandas as pd
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, QFileDialog, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor

class EnrichResultsDialog(QDialog):
    def __init__(self, data, columns, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enriched Data Results")
        self.resize(800, 500)
        
        self.data = data
        self.columns = columns
        
        layout = QVBoxLayout(self)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels([c.upper() for c in self.columns])
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        self.populate_table()
        
        # Actions
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.btn_copy = QPushButton("📋 Copy to Clipboard")
        self.btn_copy.clicked.connect(self.copy_to_clipboard)
        
        self.btn_export = QPushButton("💾 Export to Excel")
        self.btn_export.clicked.connect(self.export_to_excel)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        
        action_layout.addWidget(self.btn_copy)
        action_layout.addWidget(self.btn_export)
        action_layout.addWidget(self.btn_close)
        
        layout.addLayout(action_layout)
        
        # Apply modern style
        self.setStyleSheet("""
            QTableWidget {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QPushButton {
                padding: 6px 12px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QPushButton:hover {
                background-color: #F1F5F9;
            }
        """)

    def populate_table(self):
        self.table.setRowCount(len(self.data))
        for row_idx, row_data in enumerate(self.data):
            for col_idx, col_name in enumerate(self.columns):
                val = str(row_data.get(col_name, ''))
                item = QTableWidgetItem(val)
                item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(row_idx, col_idx, item)

    def copy_to_clipboard(self):
        if not self.data: return
        df = pd.DataFrame(self.data)[self.columns]
        df.to_clipboard(index=False)
        QMessageBox.information(self, "Copied", "Data copied to clipboard!")

    def export_to_excel(self):
        if not self.data: return
        file_path, _ = QFileDialog.getSaveFileName(self, "Export to Excel", "", "Excel Files (*.xlsx)")
        if file_path:
            try:
                df = pd.DataFrame(self.data)[self.columns]
                df.to_excel(file_path, index=False)
                QMessageBox.information(self, "Exported", f"Data exported successfully to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export data:\n{str(e)}")
