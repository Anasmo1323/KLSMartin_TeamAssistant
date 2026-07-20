from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QMenu, QInputDialog
from PyQt6.QtCore import Qt

class DynamicTableWidget(QTableWidget):
    """Custom Table Widget allowing column renaming and removal via header right-click."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.horizontalHeader().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontalHeader().customContextMenuRequested.connect(self.show_header_menu)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.verticalHeader().setVisible(False)
        self.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

    def show_header_menu(self, pos):
        col_index = self.horizontalHeader().logicalIndexAt(pos)
        if col_index < 0:
            return

        menu = QMenu(self)
        rename_action = menu.addAction("Rename Column")
        hide_action = menu.addAction("Hide Column")

        action = menu.exec(self.horizontalHeader().mapToGlobal(pos))

        if action == rename_action:
            current_name = self.horizontalHeaderItem(col_index).text() if self.horizontalHeaderItem(col_index) else ""
            new_name, ok = QInputDialog.getText(self, "Rename Column", "Enter new column name:", text=current_name)
            if ok and new_name.strip():
                if not self.horizontalHeaderItem(col_index):
                    self.setHorizontalHeaderItem(col_index, QTableWidgetItem())
                self.horizontalHeaderItem(col_index).setText(new_name.strip())

        elif action == hide_action:
            self.setColumnHidden(col_index, True)

    def keyPressEvent(self, event):
        from PyQt6.QtWidgets import QApplication
        if event.key() == Qt.Key.Key_C and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.copy_selection()
        else:
            super().keyPressEvent(event)

    def copy_selection(self):
        from PyQt6.QtWidgets import QApplication
        selection = self.selectedRanges()
        if not selection:
            return

        min_row = min([r.topRow() for r in selection])
        max_row = max([r.bottomRow() for r in selection])
        min_col = min([r.leftColumn() for r in selection])
        max_col = max([r.rightColumn() for r in selection])

        headers = []
        for col in range(min_col, max_col + 1):
            if not self.isColumnHidden(col):
                header_item = self.horizontalHeaderItem(col)
                headers.append(header_item.text() if header_item else f"Col{col}")
        
        tsv = "\t".join(headers) + "\n"

        for row in range(min_row, max_row + 1):
            row_data = []
            row_has_selection = False
            for col in range(min_col, max_col + 1):
                if not self.isColumnHidden(col):
                    idx = self.model().index(row, col)
                    if self.selectionModel().isSelected(idx):
                        row_has_selection = True
                    
                    item = self.item(row, col)
                    text = item.text() if item else ""
                    text = text.replace("\t", " ").replace("\n", " ")
                    row_data.append(text)
            
            if row_has_selection:
                tsv += "\t".join(row_data) + "\n"

        QApplication.clipboard().setText(tsv)
