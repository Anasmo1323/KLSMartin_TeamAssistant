import sys
import os
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont
from ui.main_window import MainWindow

# Enable automatic High-DPI scaling
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

if __name__ == '__main__':
    # Set Windows App ID for taskbar icon grouping
    myappid = 'klsmartin.inventory.manager.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    app = QApplication(sys.argv)
    
    # Set modern sleek font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Global stylesheet to override Windows Dark Mode and apply KLS Martin branding
    app.setStyleSheet("""
        QWidget {
            background-color: #FFFFFF;
            color: #282829;
        }
        
        QLineEdit, QListWidget, QTableWidget {
            background-color: #FFFFFF;
            color: #282829;
            border: 1px solid #CCCCCC;
            border-radius: 4px;
            padding: 2px;
        }
        
        QHeaderView::section {
            background-color: #F8F9FA;
            color: #282829;
            border: 1px solid #CCCCCC;
            padding: 4px;
            font-weight: bold;
        }
        
        QTableWidget::item:hover, QListWidget::item:hover {
            background-color: #F1F5F9;
            color: #282829;
        }
        
        QTableWidget::item:selected, QListWidget::item:selected {
            background-color: #E2E8F0;
            color: #282829;
        }
        
        QPushButton {
            background-color: #FFFFFF;
            color: #282829;
            border: 1px solid #E20303;
            border-radius: 4px;
            padding: 6px 12px;
            font-weight: bold;
        }
        
        QPushButton:hover {
            background-color: #E20303;
            color: #FFFFFF;
        }
        
        QPushButton#addButton {
            border: 1px solid #28A745;
            color: #28A745;
            padding: 0px;
            font-size: 16px;
        }
        
        QPushButton#addButton:hover {
            background-color: #28A745;
            color: #28A745;
        }
        
        QPushButton#removeButton {
            border: 1px solid #E20303;
            color: #E20303;
            padding: 0px;
            font-size: 16px;
        }
        
        QPushButton#removeButton:hover {
            background-color: #E20303;
            color: #E20303;
        }
        
        QTabWidget::pane {
            border: 1px solid #E20303;
        }
        
        QTabBar::tab {
            background: #FFFFFF;
            color: #282829;
            border: 1px solid #CCCCCC;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
            padding: 8px 16px;
            margin-right: 2px;
        }
        
        QTabBar::tab:selected {
            background: #E20303;
            color: #FFFFFF;
            border-color: #E20303;
        }
        
        QScrollBar:vertical {
            border: none;
            background: #F0F0F0;
            width: 10px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #CCCCCC;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #E20303;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        QListWidget::indicator {
            width: 14px;
            height: 14px;
            border: 1px solid #777777;
            border-radius: 2px;
            background: #FFFFFF;
        }
        
        QListWidget::indicator:checked {
            background-color: #E20303;
            border: 1px solid #E20303;
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
