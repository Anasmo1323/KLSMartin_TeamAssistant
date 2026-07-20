APP_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #F4F6F9;
}
QWidget {
    font-family: 'Segoe UI';
    font-size: 10pt;
    color: #1F2937;
}
QLabel {
    color: #1F2937;
    background: transparent;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #DDE3EC;
    border-radius: 8px;
    background: #FFFFFF;
    top: -1px;
}
QTabBar::tab {
    background: #E7EBF2;
    color: #52607A;
    padding: 9px 22px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 600;
}
QTabBar::tab:selected {
    background: #FFFFFF;
    color: #111827;
    border-bottom: 3px solid #2563EB;
}
QTabBar::tab:hover:!selected {
    background: #F0F3F9;
}

/* Buttons */
QPushButton {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 16px;
    color: #1F2937;
    font-weight: 500;
}
QPushButton:hover {
    background-color: #F1F5F9;
    border-color: #94A3B8;
}
QPushButton:pressed {
    background-color: #E2E8F0;
}
QPushButton:disabled {
    color: #A0AAB8;
    background-color: #F3F4F6;
    border-color: #E2E8F0;
}
QPushButton#primaryButton {
    background-color: #2563EB;
    border: 1px solid #2563EB;
    color: #FFFFFF;
}
QPushButton#primaryButton:hover {
    background-color: #1D4ED8;
}
QPushButton#primaryButton:pressed {
    background-color: #1E40AF;
}
QPushButton#primaryButton:disabled {
    background-color: #93B4F5;
    border-color: #93B4F5;
    color: #F0F4FF;
}
QPushButton#addButton {
    background-color: #16A34A;
    border: 1px solid #16A34A;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 0px;
    font-weight: 700;
    font-size: 16px;
}
QPushButton#addButton:hover {
    background-color: #15803D;
    border-color: #15803D;
}
QPushButton#addButton:pressed {
    background-color: #166534;
}
QPushButton#removeButton {
    background-color: #DC2626;
    border: 1px solid #DC2626;
    color: #FFFFFF;
    border-radius: 12px;
    padding: 0px;
    font-weight: 700;
    font-size: 16px;
}
QPushButton#removeButton:hover {
    background-color: #B91C1C;
    border-color: #B91C1C;
}
QPushButton#removeButton:pressed {
    background-color: #991B1B;
}

/* Inputs */
QLineEdit, QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: #2563EB;
    selection-color: #FFFFFF;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2563EB;
}
QLineEdit:disabled {
    background-color: #F3F4F6;
    color: #A0AAB8;
}
QComboBox::drop-down {
    border: none;
    width: 22px;
}

/* Tables */
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #EEF1F6;
    selection-background-color: #DBEAFE;
    selection-color: #1E3A8A;
    alternate-background-color: #F8FAFC;
}
QTableWidget::item {
    padding: 5px;
}
QHeaderView::section {
    background-color: #F1F5F9;
    color: #334155;
    padding: 7px;
    border: none;
    border-bottom: 1px solid #E2E8F0;
    border-right: 1px solid #E9EDF3;
    font-weight: 600;
}
QTableCornerButton::section {
    background-color: #F1F5F9;
    border: none;
}

QCheckBox {
    spacing: 6px;
}

/* Side panel card */
QFrame#productSidePanel {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
}

QTextBrowser {
    border: none;
    background: transparent;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #F1F5F9;
    width: 11px;
    margin: 0;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #F1F5F9;
    height: 11px;
    border-radius: 5px;
}
QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 5px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover {
    background: #94A3B8;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background-color: #EFF6FF;
    color: #1D4ED8;
}
"""
