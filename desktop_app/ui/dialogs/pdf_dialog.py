from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QCheckBox, QHBoxLayout, QPushButton

class PdfSettingsDialog(QDialog):
    """Dialog to gather custom header information and export preferences for the PDF."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PDF Export Settings")
        self.resize(400, 250)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        self.txt_company = QLineEdit("KLS Martin Egypt")
        form_layout.addRow("<b>Main Header:</b>", self.txt_company)
        
        self.txt_subtitle = QLineEdit("TechnoWave")
        form_layout.addRow("<b>Sub-Header:</b>", self.txt_subtitle)
        
        self.txt_reference = QLineEdit("Official Offer Document")
        form_layout.addRow("<b>Reference text:</b>", self.txt_reference)
        
        layout.addLayout(form_layout)

        self.chk_images = QCheckBox("Include Product Images")
        self.chk_images.setChecked(True)
        layout.addWidget(self.chk_images)

        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("Generate PDF")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.accept)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_export)
        
        layout.addLayout(btn_layout)

    def get_settings(self):
        return {
            "header": self.txt_company.text().strip(),
            "subheader": self.txt_subtitle.text().strip(),
            "reference": self.txt_reference.text().strip(),
            "include_images": self.chk_images.isChecked()
        }
