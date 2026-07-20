import sys
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QComboBox, 
                             QTableWidget, QTableWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt

class InventoryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Technowave Inventory Manager")
        self.resize(900, 600)

        # Internal Data Storage
        self.stock_df = None
        
        # Medical specialties based on your KLS Martin file structure
        self.specialties = [
            'All Items',
            'Plastic Surgery', 
            'General Surgery', 
            'Accessories for Electrosurgery', 
            'Cardio, Thoracic and Vascular Surgery', 
            'Neurosurgery', 
            'Oral and maxillofacial surgery'
        ]

        self.init_ui()

    def init_ui(self):
        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Top Controls Layout
        controls_layout = QHBoxLayout()

        self.btn_load = QPushButton("1. Upload Excel Stock")
        self.btn_load.clicked.connect(self.load_excel)
        controls_layout.addWidget(self.btn_load)

        self.combo_specialty = QComboBox()
        self.combo_specialty.addItems(self.specialties)
        self.combo_specialty.setEnabled(False)
        self.combo_specialty.currentTextChanged.connect(self.filter_data)
        controls_layout.addWidget(self.combo_specialty)

        self.btn_export = QPushButton("2. Export Quote List")
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_data)
        controls_layout.addWidget(self.btn_export)

        layout.addLayout(controls_layout)

        # Data Table
        self.table = QTableWidget()
        layout.addWidget(self.table)

    def load_excel(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Select Stock Excel File", "", "Excel Files (*.xlsx *.xls)")
        if filepath:
            try:
                # Read the main 'Stock' sheet
                self.stock_df = pd.read_excel(filepath, sheet_name='Stock')
                
                # Enable UI elements
                self.combo_specialty.setEnabled(True)
                self.btn_export.setEnabled(True)
                
                # Show initial data
                self.filter_data("All Items")
                QMessageBox.information(self, "Success", "Inventory loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load file: {str(e)}")

    def filter_data(self, specialty):
        if self.stock_df is None:
            return

        # Start with all items that have a quantity greater than 0
        filtered_df = self.stock_df[self.stock_df['Qty.'] > 0]

        # Apply specialty filter based on the 1, 0, -1 boolean flags
        if specialty != 'All Items':
            filtered_df = filtered_df[filtered_df[specialty] == 1]

        # Select only the relevant columns for the final quote
        display_columns = ['Vendor Code', 'Desc.', 'Qty.', 'Category']
        self.current_view_df = filtered_df[display_columns]

        self.populate_table(self.current_view_df)

    def populate_table(self, df):
        self.table.clear()
        self.table.setRowCount(df.shape[0])
        self.table.setColumnCount(df.shape[1])
        self.table.setHorizontalHeaderLabels(df.columns)

        for row_idx, row in df.iterrows():
            for col_idx, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                # Make items read-only for safety
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable) 
                self.table.setItem(row_idx, col_idx, item)
        
        self.table.resizeColumnsToContents()

    def export_data(self):
        if not hasattr(self, 'current_view_df') or self.current_view_df.empty:
            QMessageBox.warning(self, "Warning", "No data to export.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Save Quote List", "Quote_List.xlsx", "Excel Files (*.xlsx)")
        if filepath:
            try:
                self.current_view_df.to_excel(filepath, index=False)
                QMessageBox.information(self, "Success", "Quote list exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export file: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = InventoryApp()
    window.show()
    sys.exit(app.exec())