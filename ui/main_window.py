from PyQt6.QtWidgets import QMainWindow, QTabWidget, QWidget, QHBoxLayout, QTableWidget, QMessageBox, QProgressDialog, QApplication, QSplitter
from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtCore import Qt
import os
import tempfile

from core.updater import check_for_updates, download_update, apply_update_and_restart
from core.utils import resource_path
from ui.widgets.side_panel import ProductSidePanel
from ui.tabs.kls_master_tab import KlsMasterTab
from ui.tabs.stock_tab import StockTab
from ui.tabs.inspection_tab import InspectionTab
from ui.tabs.shared_workspace_tab import SharedWorkspaceTab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KLSMartin Team Assistant")
        self.setWindowIcon(QIcon(resource_path("icon.ico")))
        self.resize(1300, 820)

        # The font is applied at application level in main.py, 
        # but we can leave it to app styles or apply here if needed.

        self.kls_master_tab = KlsMasterTab()
        self.side_panel = ProductSidePanel(self.kls_master_tab)
        self.stock_tab = StockTab(self.kls_master_tab)
        self.inspection_tab = InspectionTab(self.kls_master_tab)
        self.shared_workspace_tab = SharedWorkspaceTab()

        self.tabs = QTabWidget()
        self.tabs.addTab(self.kls_master_tab, "Master")
        self.tabs.addTab(self.stock_tab, "Stock")
        self.tabs.addTab(self.inspection_tab, "Inspection")
        self.tabs.addTab(self.shared_workspace_tab, "Shared Workspace")

        self.kls_master_tab.table.currentCellChanged.connect(self.handle_cell_click)
        self.stock_tab.table.currentCellChanged.connect(self.handle_cell_click)
        self.inspection_tab.table.currentCellChanged.connect(self.handle_cell_click)
        self.shared_workspace_tab.table.currentCellChanged.connect(self.handle_cell_click)

        central_widget = QWidget(self)
        central_layout = QHBoxLayout(central_widget)
        central_layout.setContentsMargins(12, 12, 12, 12)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(self.tabs)
        main_splitter.addWidget(self.side_panel)
        # Set standard ratio: tabs get most space (e.g., 3:1 ratio)
        main_splitter.setSizes([900, 350])
        
        central_layout.addWidget(main_splitter)
        
        self.setCentralWidget(central_widget)
        self._create_menu_bar()

    def _create_menu_bar(self):
        menubar = self.menuBar()
        help_menu = menubar.addMenu("Help")
        
        update_action = QAction("Check for Updates", self)
        update_action.triggered.connect(self.check_for_updates_ui)
        help_menu.addAction(update_action)

    def check_for_updates_ui(self):
        update_available, new_version, download_url, release_notes = check_for_updates()
        if not update_available:
            QMessageBox.information(self, "Up to Date", "You are running the latest version.")
            return
            
        msg = f"Version {new_version} is available!\n\nRelease Notes:\n{release_notes}\n\nDo you want to update now? This will download the update and restart the application."
        reply = QMessageBox.question(self, "Update Available", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self._download_and_apply_update(new_version, download_url)
            
    def _download_and_apply_update(self, new_version, download_url):
        temp_dir = tempfile.gettempdir()
        temp_exe = os.path.join(temp_dir, f"KLS_App_Update_v{new_version}.exe")
        
        progress = QProgressDialog("Downloading Update...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Updating")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        def update_progress(val):
            if val >= 0:
                progress.setValue(val)
                QApplication.processEvents()
            
        try:
            download_update(download_url, temp_exe, progress_callback=update_progress)
            if not progress.wasCanceled():
                progress.setValue(100)
                apply_update_and_restart(temp_exe)
        except Exception as e:
            QMessageBox.critical(self, "Update Error", f"Failed to download update:\n{e}")

    def _clear_other_table_selections(self, active_table):
        tables = [
            self.kls_master_tab.table,
            self.stock_tab.table,
            self.inspection_tab.table,
            self.shared_workspace_tab.table
        ]
        for table in tables:
            if table is active_table:
                continue
            table.clearSelection()
            table.setCurrentCell(-1, -1)

    def handle_cell_click(self, current_row, current_col, previous_row, previous_col):
        sender_table = self.sender()
        if not isinstance(sender_table, QTableWidget):
            return

        self._clear_other_table_selections(sender_table)

        if current_row < 0:
            return

        code_col_idx = None
        for col_idx in range(sender_table.columnCount()):
            header_text = sender_table.horizontalHeaderItem(col_idx)
            if header_text is not None and 'code' in header_text.text().lower():
                code_col_idx = col_idx
                break

        if code_col_idx is None:
            return

        code_item = sender_table.item(current_row, code_col_idx)
        if code_item is None:
            return

        self.side_panel.update_panel(code_item.text())

    def closeEvent(self, event):
        """Intercepts the application closing to check for unsaved edits."""
        tabs_to_check = [
            (self.stock_tab, "Stock Management"),
            (self.inspection_tab, "Client Verification")
        ]
        
        for tab_obj, tab_name in tabs_to_check:
            if tab_obj.is_modified:
                # Bring the tab with unsaved changes to the front
                self.tabs.setCurrentWidget(tab_obj)
                reply = QMessageBox.question(self, 'Unsaved Changes Detected',
                    f"There are unsaved edits in the '{tab_name}' tab.\nDo you want to save before exiting?",
                    QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
                
                if reply == QMessageBox.StandardButton.Save:
                    tab_obj.save_file()
                elif reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return # Abort application closure entirely
                    
        event.accept() # All tabs safe or discarded, allow closure
