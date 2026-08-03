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
        
        # Undo/Redo system
        self.undo_stack = []
        self.redo_stack = []
        self.is_restoring = False

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
        elif event.key() == Qt.Key.Key_V and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.save_snapshot()
            self.paste_selection()
        elif event.key() == Qt.Key.Key_Z and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.undo()
        elif event.key() == Qt.Key.Key_Y and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            self.redo()
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

        tsv = ""

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

    def paste_selection(self):
        from PyQt6.QtWidgets import QApplication, QTableWidgetItem
        clipboard_text = QApplication.clipboard().text()
        if not clipboard_text:
            return

        rows = clipboard_text.strip().split('\n')
        current_row = self.currentRow()
        current_col = self.currentColumn()

        if current_row < 0 or current_col < 0:
            current_row = 0
            current_col = 0

        # Ensure table is large enough
        required_rows = current_row + len(rows)
        if required_rows > self.rowCount():
            self.setRowCount(required_rows)

        for i, row_text in enumerate(rows):
            cols = row_text.split('\t')
            required_cols = current_col + len(cols)
            if required_cols > self.columnCount():
                self.setColumnCount(required_cols)

            for j, col_text in enumerate(cols):
                item = self.item(current_row + i, current_col + j)
                if not item:
                    item = QTableWidgetItem()
                    self.setItem(current_row + i, current_col + j, item)
                item.setText(col_text)

    def get_snapshot(self):
        state = []
        for r in range(self.rowCount()):
            for c in range(self.columnCount()):
                item = self.item(r, c)
                if item and item.text():
                    state.append({'row': r, 'col': c, 'value': item.text()})
        return {'rows': self.rowCount(), 'cols': self.columnCount(), 'cells': state}
        
    def save_snapshot(self):
        if self.is_restoring:
            return
        self.undo_stack.append(self.get_snapshot())
        self.redo_stack.clear()
        # limit stack
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
            
    def restore_snapshot(self, state):
        self.is_restoring = True
        
        self.clearContents()
        self.setRowCount(state['rows'])
        self.setColumnCount(state['cols'])
        
        from PyQt6.QtWidgets import QTableWidgetItem
        for cell in state['cells']:
            item = QTableWidgetItem(cell['value'])
            self.setItem(cell['row'], cell['col'], item)
            
        self.is_restoring = False
        
    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.get_snapshot())
        prev_state = self.undo_stack.pop()
        self.restore_snapshot(prev_state)
        
    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.get_snapshot())
        next_state = self.redo_stack.pop()
        self.restore_snapshot(next_state)
