import os
import pandas as pd
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap

from ui.widgets.custom_labels import ClickableImageLabel
from core.utils import resource_path

class ProductSidePanel(QFrame):
    def __init__(self, master_tab, parent=None):
        super().__init__(parent)
        self.master_tab = master_tab
        self.setObjectName("productSidePanel")
        self.init_ui()

    def init_ui(self):
        panel_layout = QVBoxLayout(self)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        title = QLabel("Product Master Data")
        title.setStyleSheet("font-size: 12px; font-weight: 700; color: #282829; letter-spacing: 0.5px;")
        header_layout.addWidget(title)
        panel_layout.addLayout(header_layout, stretch=0)

        # 40% Height Allocation via stretch
        self.image_label = ClickableImageLabel()
        self.image_label.clear_image("No Image Selected")
        self.image_label.setStyleSheet("border: 1px solid #E2E8F0; border-radius: 6px; background-color: #F8FAFC;")
        panel_layout.addWidget(self.image_label, stretch=40) 

        # 60% Height Allocation for text data via stretch
        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        


        self.panel_content = QTextBrowser()
        self.panel_content.setOpenExternalLinks(True)
        text_layout.addWidget(self.panel_content)
        
        panel_layout.addLayout(text_layout, stretch=60)

    def update_panel(self, code_val):
        master_df = self.master_tab.df
        if master_df is None or master_df.empty:
            self.image_label.setText("No Master Data Available")
            self.panel_content.setHtml("<i>Please upload Master CSV.</i>")
            return

        clean_code = str(code_val).replace('-', '').strip().lower()
        mask = master_df['code'].astype(str).str.replace('-', '').str.strip().str.lower() == clean_code
        match = master_df[mask]

        if match.empty:
            x_path = resource_path("images/x.png")
            if os.path.exists(x_path):
                self.image_label.set_image(QPixmap(x_path), x_path)
            else:
                self.image_label.clear_image("Code Not Found")
            self.panel_content.setHtml(f"<h3 style='color:red;'>Code Not Found</h3><p>'{code_val}' does not exist.</p>")
            return

        row = match.iloc[0]

        description = row.get('description', '')

        description_arabic = row.get('description_arabic', '')
        if pd.isna(description_arabic) or str(description_arabic).strip() == "":
            arb_text = "الترجمة غير متوفرة"
        else:
            arb_text = str(description_arabic)

        # 2. Update Image
        local_image_path = row.get('local_image_path', '')
        
        if pd.isna(description) or str(description).strip() in {"", "No equivalent KLS Martin product available"}:
            x_path = resource_path("images/x.png")
            if os.path.exists(x_path):
                self.image_label.set_image(QPixmap(x_path), x_path)
            else:
                self.image_label.clear_image("No Description")
        elif pd.isna(local_image_path) or str(local_image_path).strip() in {"", "No Image", "Download Failed", "HTTP Error"}:
            missing_path = resource_path("images/missing.png")
            if os.path.exists(missing_path):
                self.image_label.set_image(QPixmap(missing_path), missing_path)
            else:
                self.image_label.clear_image("No Image Available")
        else:
            image_path = str(local_image_path)
            if os.path.exists(image_path):
                from core.utils import safe_load_pixmap
                pixmap = safe_load_pixmap(image_path)
                if not pixmap.isNull():
                    self.image_label.set_image(pixmap, image_path)
                else:
                    missing_path = resource_path("images/missing.png")
                    if os.path.exists(missing_path):
                        self.image_label.set_image(QPixmap(missing_path), missing_path)
                    else:
                        self.image_label.clear_image("No Image Available")
            else:
                missing_path = resource_path("images/missing.png")
                if os.path.exists(missing_path):
                    self.image_label.set_image(QPixmap(missing_path), missing_path)
                else:
                    self.image_label.clear_image("Image File Missing")

        family = str(row.get('family', ''))
        if pd.isna(row.get('family')) or not family.strip():
            family_html = ""
        else:
            family_html = f"<h4 style='color:#555; margin-bottom: 0px; margin-top: 0px;'>{family}</h4>"

        shape = str(row.get('shape', '')) if pd.notna(row.get('shape')) and str(row.get('shape')).strip() else 'N/A'
        dimensions = str(row.get('dimensions', '')) if pd.notna(row.get('dimensions')) and str(row.get('dimensions')).strip() else 'N/A'
        length = str(row.get('length', '')) if pd.notna(row.get('length')) and str(row.get('length')).strip() else 'N/A'
        tip = str(row.get('tip_type', '')) if pd.notna(row.get('tip_type')) and str(row.get('tip_type')).strip() else 'N/A'
        modifiers = str(row.get('modifiers', '')) if pd.notna(row.get('modifiers')) and str(row.get('modifiers')).strip() else 'N/A'

        details_html = f"""
        <table width='100%' cellpadding='4' style='border-collapse: collapse; margin-top: 10px; font-size: 12px;'>
            <tr>
                <td width='50%'><b>Shape:</b> {shape}</td>
                <td width='50%'><b>Dimensions:</b> {dimensions}</td>
            </tr>
            <tr>
                <td width='50%'><b>Length:</b> {length}</td>
                <td width='50%'><b>Tip:</b> {tip}</td>
            </tr>
            <tr>
                <td width='100%' colspan='2'><b>Extra:</b> {modifiers}</td>
            </tr>
        </table>
        """

        url = row.get("product_url", "#")
        url_html = f"<a href='{url}'>Open on KLS Martin Website</a>" if "http" in str(url) else "N/A"
        html = f"""
        {family_html}
        <h3 style='color:#007BFF; margin-bottom: 2px; margin-top: 5px;'>{row.get('code', code_val)}</h3>
        <p style='font-size: 14px; font-weight: bold; color: #282829; margin-top: 0px;'>{row.get('description', 'N/A')}</p>
        <p dir='rtl' align='right' style='font-size: 11px; color: #282829; margin-top: -5px;'>{arb_text}</p>
        {details_html}
        <hr/>
        <p><b>Associated Catalogues:</b><br>{self.master_tab._format_brochures(row.get('brochures', '')).replace(chr(10), '<br>')}</p>
        <hr/>
        <p><b>Web Link:</b><br>{url_html}</p>
        """
        self.panel_content.setHtml(html)
