import os
import io
import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image as RLImage, Spacer

import arabic_reshaper
from bidi.algorithm import get_display

def shape_arabic(text):
    if not isinstance(text, str):
        text = str(text)
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(text))

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QHeaderView, QTableWidgetItem, QMessageBox, QFileDialog, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont

from ui.widgets.dynamic_table import DynamicTableWidget
from ui.dialogs.mapping_dialog import MappingDialog
from ui.dialogs.pdf_dialog import PdfSettingsDialog
from core.utils import show_loading

class OfferListDialog(QDialog):
    def __init__(self, master_tab, offer_data, parent=None):
        super().__init__(parent)
        self.master_tab = master_tab
        self.offer_data = offer_data
        self.extra_columns = []
        self.setWindowTitle("Manage Offer List")
        self.resize(800, 600)
        self.init_ui()
        self.refresh_offer_table()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(QLabel("<b>Current Offer List</b>"))

        self.offer_table = DynamicTableWidget()
        self.offer_table.setColumnCount(4)
        self.offer_table.setHorizontalHeaderLabels(["", "CODE", "DESCRIPTION", "QTY"])
        self.offer_table.setColumnWidth(0, 54)
        self.offer_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.offer_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.offer_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.offer_table.horizontalHeader().setSectionsMovable(True)
        self.offer_table.itemChanged.connect(self.on_offer_item_changed)
        self.offer_table.currentCellChanged.connect(self._on_table_selection_changed)
        layout.addWidget(self.offer_table)

        btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear List")
        self.btn_clear.clicked.connect(self.clear_offer_list)
        
        self.btn_bulk_upload = QPushButton("Bulk Upload (Excel/CSV)")
        self.btn_bulk_upload.clicked.connect(self.bulk_upload_offer)

        self.btn_export_excel = QPushButton("Export to Excel")
        self.btn_export_excel.clicked.connect(self.export_excel)
        
        self.btn_export_pdf = QPushButton("Export to PDF")
        self.btn_export_pdf.setObjectName("primaryButton")
        self.btn_export_pdf.clicked.connect(self.export_pdf)

        btn_layout.addWidget(self.btn_clear)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_bulk_upload)
        btn_layout.addWidget(self.btn_export_excel)
        btn_layout.addWidget(self.btn_export_pdf)
        layout.addLayout(btn_layout)

    def refresh_offer_table(self):
        self.offer_table.blockSignals(True)
        self.offer_table.clearSpans()
        self.offer_table.setColumnCount(4 + len(self.extra_columns))
        self.offer_table.setHorizontalHeaderLabels(["", "CODE", "DESCRIPTION", "QTY"] + [c.upper() for c in self.extra_columns])
        self.offer_table.setRowCount(len(self.offer_data))
        
        for i, data in enumerate(self.offer_data):
            btn = QPushButton("−")
            btn.setObjectName("removeButton")
            btn.setFixedSize(24, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip("Remove from offer list")
            btn.clicked.connect(lambda _, row=i: self.remove_offer_item(row))

            btn_container = QWidget()
            btn_container.setStyleSheet("QWidget { background: transparent; }")
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            self.offer_table.setRowHeight(i, 36)
            self.offer_table.setCellWidget(i, 0, btn_container)

            if data.get("is_section", False):
                item_desc = QTableWidgetItem(data["desc"])
                item_desc.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
                item_desc.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
                item_desc.setBackground(QColor("#DDE3EC"))
                item_desc.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                
                self.offer_table.setItem(i, 1, item_desc)
                self.offer_table.setSpan(i, 1, 1, 3 + len(self.extra_columns)) 
            else:
                item_code = QTableWidgetItem(data["code"])
                item_code.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
                self.offer_table.setItem(i, 1, item_code)

                item_desc = QTableWidgetItem(data["desc"])
                item_desc.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
                self.offer_table.setItem(i, 2, item_desc)

                item_qty = QTableWidgetItem(str(data["qty"]))
                item_qty.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
                self.offer_table.setItem(i, 3, item_qty)

                for idx, col_name in enumerate(self.extra_columns):
                    item_extra = QTableWidgetItem(str(data.get(col_name, "")))
                    item_extra.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsEnabled)
                    self.offer_table.setItem(i, 4 + idx, item_extra)

        self.offer_table.blockSignals(False)

    def on_offer_item_changed(self, item):
        row = item.row()
        col = item.column()

        if row < 0 or row >= len(self.offer_data):
            return

        new_val = item.text().strip()

        if col == 1:
            self.offer_data[row]["code"] = new_val
        elif col == 2:
            self.offer_data[row]["desc"] = new_val
        elif col == 3:
            try:
                self.offer_data[row]["qty"] = int(new_val)
            except ValueError:
                pass
        elif col >= 4:
            col_name = self.extra_columns[col - 4]
            self.offer_data[row][col_name] = new_val

    def _on_table_selection_changed(self, current_row, current_col, prev_row, prev_col):
        if current_row < 0 or current_row >= len(self.offer_data):
            return
        data = self.offer_data[current_row]
        if data.get("is_section", False):
            return
        code = data.get("code", "")
        
        master_df = self.master_tab.df
        if master_df is None or master_df.empty:
            return
            
        mask = master_df['code'].astype(str).str.replace('-', '').str.strip().str.lower() == str(code).replace('-', '').strip().lower()
        match = master_df[mask]
        if not match.empty:
            main_win = self.master_tab.window()
            if hasattr(main_win, 'side_panel'):
                main_win.side_panel.update_panel(code)

    def remove_offer_item(self, row_idx):
        if 0 <= row_idx < len(self.offer_data):
            self.offer_data.pop(row_idx)
            self.refresh_offer_table()

    def clear_offer_list(self):
        self.offer_data.clear()
        self.refresh_offer_table()

    def bulk_upload_offer(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Offer Upload File",
            "",
            "Data Files (*.csv *.xlsx *.xls)"
        )
        if not file_path:
            return

        dlg = MappingDialog(file_path, ['code', 'description', 'quantity'], allow_extras=True, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        with show_loading(self, "Processing Bulk Upload..."):
            try:
                if file_path.lower().endswith('.csv'):
                    raw_df = pd.read_csv(file_path, header=dlg.header_row)
                else:
                    raw_df = pd.read_excel(file_path, sheet_name=dlg.selected_sheet, header=dlg.header_row)

                rename_map = {'code': 'code', 'description': 'desc', 'quantity': 'qty'}
                mapped_cols = {}
                for source_col, target_key in rename_map.items():
                    if source_col in dlg.mappings:
                        mapped_cols[source_col] = dlg.mappings[source_col]
                    else:
                        mapped_cols[source_col] = None

                if mapped_cols['code'] is None or mapped_cols['description'] is None or mapped_cols['quantity'] is None:
                    QMessageBox.warning(self, "Invalid Mapping", "Please map 'code', 'description', and 'quantity' columns.")
                    return

                new_extras = getattr(dlg, 'extras', [])
                for ext in new_extras:
                    if ext not in self.extra_columns:
                        self.extra_columns.append(ext)

                upload_df = raw_df.rename(columns={
                    mapped_cols['code']: 'code',
                    mapped_cols['description']: 'desc',
                    mapped_cols['quantity']: 'qty'
                })
                
                upload_df['qty'] = pd.to_numeric(upload_df['qty'], errors='coerce').fillna(0).astype(int)

                master_df = self.master_tab.df
                if master_df is None or master_df.empty:
                    QMessageBox.warning(self, "No Master Data", "Please load the master catalogue before bulk uploading offers.")
                    return

                master_codes = set(master_df['code'].astype(str).str.replace('-', '').str.strip().str.lower())
                valid_rows = []
                skipped_codes = []

                for _, row in upload_df.iterrows():
                    code_val = str(row['code']).strip() if pd.notna(row['code']) else ""
                    desc_val = str(row['desc']).strip() if pd.notna(row['desc']) else ""

                    if (not code_val or code_val.lower() == 'nan') and desc_val and desc_val.lower() != 'nan':
                        sec_data = {"code": "", "desc": desc_val, "qty": "", "is_section": True}
                        for ext in self.extra_columns:
                            sec_data[ext] = ""
                        self.offer_data.append(sec_data)
                        valid_rows.append(desc_val)
                        continue

                    if not code_val or code_val.lower() == 'nan':
                        continue

                    normalized_code = code_val.replace('-', '').strip().lower()
                    if normalized_code not in master_codes:
                        skipped_codes.append(code_val)
                        continue

                    qty_val = int(row['qty']) if pd.notna(row['qty']) else 1
                    row_data = {"code": code_val, "desc": desc_val, "qty": qty_val, "is_section": False}
                    for ext in new_extras:
                        if ext in upload_df.columns and pd.notna(row[ext]):
                            raw_val = row[ext]
                            if isinstance(raw_val, float) and raw_val.is_integer():
                                val = str(int(raw_val)).strip()
                            else:
                                val = str(raw_val).strip()
                        else:
                            val = ""
                        row_data[ext] = val
                    self.offer_data.append(row_data)
                    valid_rows.append(code_val)

                if valid_rows:
                    self.refresh_offer_table()

                if skipped_codes:
                    QMessageBox.warning(
                        self,
                        "Skipped Invalid Codes",
                        f"The following codes were skipped because they were not found in the master catalogue:\n{', '.join(sorted(set(skipped_codes)))}"
                    )
                else:
                    QMessageBox.information(self, "Bulk Upload Complete", "All uploaded items and sections were added.")
            except Exception as e:
                QMessageBox.critical(self, "Bulk Upload Error", f"Failed to process uploaded file: {e}")

    def get_logical_col_key(self, logical_col):
        if logical_col == 1: return "CODE", "code"
        elif logical_col == 2: return "DESCRIPTION", "desc"
        elif logical_col == 3: return "QTY", "qty"
        elif logical_col >= 4: return self.extra_columns[logical_col - 4].upper(), self.extra_columns[logical_col - 4]
        return None, None

    def export_excel(self):
        if not self.offer_data:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save Excel", "Offer_List.xlsx", "Excel Files (*.xlsx)")
        if path:
            with show_loading(self, "Generating Excel..."):
                header = self.offer_table.horizontalHeader()
                visual_cols = [header.logicalIndex(v) for v in range(1, self.offer_table.columnCount())]
                
                export_list = []
                for data in self.offer_data:
                    export_dict = {}
                    for log_col in visual_cols:
                        header_name, dict_key = self.get_logical_col_key(log_col)
                        if header_name:
                            if data.get("is_section", False):
                                export_dict[header_name] = data["desc"] if dict_key == "desc" else ""
                            else:
                                export_dict[header_name] = data.get(dict_key, "")
                    export_list.append(export_dict)

                df = pd.DataFrame(export_list)
                df.to_excel(path, index=False)
            QMessageBox.information(self, "Success", "Excel Exported Successfully.")

    def _find_image_path(self, code):
        master_df = self.master_tab.df
        if master_df is None or master_df.empty:
            return None
        mask = master_df['code'].astype(str).str.replace('-', '').str.strip().str.lower() == str(code).replace('-', '').strip().lower()
        match = master_df[mask]
        if match.empty:
            return None
        img_path = str(match.iloc[0].get('local_image_path', ''))
        return img_path if img_path and os.path.exists(img_path) else None

    def _scaled_pdf_image(self, img_path, max_w_mm=22, max_h_mm=15):
        max_w, max_h = max_w_mm * mm, max_h_mm * mm
        try:
            img = PILImage.open(img_path)
            img.load()
        except Exception:
            return Paragraph("N/A", ParagraphStyle("na", fontSize=7, alignment=TA_CENTER))

        w, h = img.size
        ratio_upright = min(max_w / w, max_h / h)
        ratio_rotated = min(max_w / h, max_h / w)

        if ratio_rotated > ratio_upright * 1.15:
            img = img.rotate(-90, expand=True)
            w, h = img.size
            ratio = ratio_rotated
        else:
            ratio = ratio_upright

        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        buf.seek(0)
        return RLImage(buf, width=w * ratio, height=h * ratio)

    def export_pdf(self):
        if not self.offer_data:
            return

        settings_dialog = PdfSettingsDialog(self)
        if settings_dialog.exec() != QDialog.DialogCode.Accepted:
            return
        settings = settings_dialog.get_settings()

        path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "Offer_List.pdf", "PDF Files (*.pdf)")
        if not path:
            return

        with show_loading(self, "Generating PDF, this may take a moment..."):
            try:
                try:
                    pdfmetrics.registerFont(TTFont('Arial', 'C:\\Windows\\Fonts\\arial.ttf'))
                    pdfmetrics.registerFont(TTFont('Arial-Bold', 'C:\\Windows\\Fonts\\arialbd.ttf'))
                    f_norm = 'Arial'
                    f_bold = 'Arial-Bold'
                except Exception:
                    f_norm = 'Helvetica'
                    f_bold = 'Helvetica-Bold'

                styles = getSampleStyleSheet()
                cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10, fontName=f_norm)
                qty_style = ParagraphStyle("qty", parent=cell_style, alignment=TA_CENTER)
                header_cell_style = ParagraphStyle(
                    "hcell", parent=styles["Normal"], fontSize=8, leading=10,
                    textColor=colors.white, fontName=f_bold)

                doc = SimpleDocTemplate(
                    path, pagesize=A4,
                    leftMargin=15 * mm, rightMargin=15 * mm,
                    topMargin=15 * mm, bottomMargin=15 * mm,
                    title=settings.get("reference", "Offer")
                )

                story = []
                if settings.get('header'):
                    story.append(Paragraph(shape_arabic(settings['header']), ParagraphStyle(
                        "h1", parent=styles["Heading1"], fontSize=16, spaceAfter=2, fontName=f_bold)))
                if settings.get('subheader'):
                    story.append(Paragraph(shape_arabic(settings['subheader']), ParagraphStyle(
                        "h2", parent=styles["Heading2"], fontSize=12, textColor=colors.grey, spaceAfter=2, fontName=f_norm)))
                if settings.get('reference'):
                    story.append(Paragraph(shape_arabic(settings['reference']), ParagraphStyle(
                        "h3", parent=styles["Normal"], fontSize=10, spaceAfter=10, fontName=f_norm)))
                story.append(Spacer(1, 6))

                header = self.offer_table.horizontalHeader()
                visual_cols = [header.logicalIndex(v) for v in range(1, self.offer_table.columnCount())]
                
                header_row = []
                col_widths = []
                
                usable_width_mm = 180
                total_text_cols_width = 0
                
                text_col_widths_mm = []
                for log_col in visual_cols:
                    header_name, dict_key = self.get_logical_col_key(log_col)
                    if not header_name:
                        text_col_widths_mm.append(0)
                        continue
                    
                    shaped_header = shape_arabic(header_name)
                    max_w = stringWidth(shaped_header, f_bold, 8) / mm
                    
                    for data in self.offer_data:
                        if not data.get("is_section", False):
                            text = str(data.get(dict_key, ""))
                            shaped_text = shape_arabic(text)
                            w = stringWidth(shaped_text, f_norm, 8) / mm
                            if w > max_w:
                                max_w = w
                                
                    col_w = max_w + 6
                    if header_name == "DESCRIPTION":
                        col_w = min(col_w, 85.0)
                    elif header_name == "CODE":
                        col_w = min(col_w, 45.0)
                    else:
                        col_w = min(col_w, 35.0)

                    text_col_widths_mm.append(col_w)
                    total_text_cols_width += col_w

                image_col_width = max(25.0, usable_width_mm - total_text_cols_width)
                
                for i, log_col in enumerate(visual_cols):
                    header_name, _ = self.get_logical_col_key(log_col)
                    if header_name:
                        header_row.append(Paragraph(shape_arabic(header_name), header_cell_style))
                        col_widths.append(text_col_widths_mm[i] * mm)
                
                header_row.append(Paragraph("Image", header_cell_style))
                col_widths.append(image_col_width * mm)
                
                table_data = [header_row]
                
                dynamic_styles = []

                for row_idx, data in enumerate(self.offer_data, start=1):
                    if data.get("is_section", False):
                        sec_p = Paragraph(f"<b>{shape_arabic(data['desc'])}</b>", ParagraphStyle("sec", parent=cell_style, alignment=TA_CENTER, fontName=f_bold))
                        row_data = [sec_p] + [""] * len(visual_cols)
                        table_data.append(row_data)
                        dynamic_styles.append(("SPAN", (0, row_idx), (-1, row_idx)))
                        dynamic_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colors.HexColor("#DDE3EC")))
                        dynamic_styles.append(("ALIGN", (0, row_idx), (-1, row_idx), "CENTER"))
                    else:
                        img_cell = ""
                        if settings['include_images']:
                            img_path = self._find_image_path(data['code'])
                            avail_img_w = max(5, image_col_width - 4)
                            img_cell = self._scaled_pdf_image(img_path, max_w_mm=avail_img_w, max_h_mm=25) if img_path else Paragraph("—", cell_style)

                        row_data = []
                        for log_col in visual_cols:
                            header_name, dict_key = self.get_logical_col_key(log_col)
                            if header_name:
                                style = qty_style if header_name == "QTY" else cell_style
                                row_data.append(Paragraph(shape_arabic(str(data.get(dict_key, ""))), style))
                        
                        row_data.append(img_cell)
                        table_data.append(row_data)

                tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
                
                base_style = [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ]
                
                tbl.setStyle(TableStyle(base_style + dynamic_styles))
                story.append(tbl)

                doc.build(story)

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Generation failed: {str(e)}")
                return
                
        QMessageBox.information(self, "Success", "PDF Generated Successfully.")
