import sys
import sqlite3
import pandas as pd
import ctypes
import os
import torch
import warnings

os.environ['HF_HUB_OFFLINE'] = '1'

warnings.filterwarnings("ignore")

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
                             QSplitter, QProgressBar, QMessageBox, QFileDialog, QLineEdit,
                             QFrame, QAbstractItemView, QGridLayout, QSizePolicy, QDialog, QStyleFactory, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPalette, QColor, QFont, QIcon

from core.stylesheet import APP_STYLESHEET
from core.utils import resource_path, show_loading
from ui.dialogs.mapping_dialog import MappingDialog

class MappingMemory:
    def __init__(self, db_path="mapping_memory.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mappings (
                arabic_term TEXT PRIMARY KEY,
                kls_code TEXT,
                kls_description TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def get_mapping(self, arabic_term):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT kls_code, kls_description FROM mappings WHERE arabic_term = ?', (arabic_term,))
        result = cursor.fetchone()
        conn.close()
        return result

    def save_mapping(self, arabic_term, kls_code, kls_description):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO mappings (arabic_term, kls_code, kls_description)
            VALUES (?, ?, ?)
        ''', (arabic_term, kls_code, kls_description))
        conn.commit()
        conn.close()

class AIEngine(QThread):
    progress_updated = pyqtSignal(int)
    engine_ready = pyqtSignal(bool)
    embedding_error = pyqtSignal(str)

    def __init__(self, master_df):
        super().__init__()
        self.master_df = master_df
        self.model = None
        self.corpus_embeddings = None

    def run(self):
        try:
            from sentence_transformers import SentenceTransformer, util
            import torch
            import os
            from sklearn.feature_extraction.text import TfidfVectorizer
            from core.utils import resource_path
            
            self.util = util
            self.torch = torch
            
            try:
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            except Exception as first_err:
                print("Network error while checking HuggingFace, falling back to local_files_only=True...")
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2', local_files_only=True)
            
            descriptions = (self.master_df['description'].fillna("").astype(str) + 
                            " " + 
                            self.master_df['brochures'].fillna("").astype(str)).tolist()
            
            self.tfidf = TfidfVectorizer(lowercase=True)
            self.tfidf_matrix = self.tfidf.fit_transform(descriptions)
            
            csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "KLS_All_Products.xlsx")
            csv_mtime = os.path.getmtime(csv_path) if os.path.exists(csv_path) else 0
            cache_path = resource_path("embeddings_cache.pt")
            
            if os.path.exists(cache_path):
                try:
                    cache_data = torch.load(cache_path, weights_only=False)
                    if cache_data.get('csv_mtime') == csv_mtime and cache_data.get('embeddings') is not None:
                        self.corpus_embeddings = cache_data['embeddings']
                        self.progress_updated.emit(100)
                        self.engine_ready.emit(True)
                        return
                except Exception as e:
                    print("Cache load failed:", e)
            
            # Embeddings Caching
            
            batch_size = 1000
            embeddings_list = []
            
            total_items = len(descriptions)
            if total_items == 0:
                self.engine_ready.emit(True)
                return

            for i in range(0, total_items, batch_size):
                batch = descriptions[i:i+batch_size]
                emb = self.model.encode(batch, convert_to_tensor=True, show_progress_bar=False)
                embeddings_list.append(emb)
                
                progress = int(((i + len(batch)) / total_items) * 100)
                self.progress_updated.emit(progress)

            if embeddings_list:
                self.corpus_embeddings = torch.cat(embeddings_list, dim=0)
                try:
                    torch.save({'csv_mtime': csv_mtime, 'embeddings': self.corpus_embeddings}, cache_path)
                except Exception as e:
                    print("Cache save failed:", e)
            else:
                self.corpus_embeddings = None

            self.engine_ready.emit(True)

        except Exception as e:
            self.embedding_error.emit(str(e))
            self.engine_ready.emit(False)

    def find_top_matches(self, query, top_k=15):
        if self.model is None or self.corpus_embeddings is None:
            return []
            
        # Semantic search
        query_embedding = self.model.encode(query, convert_to_tensor=True)
        semantic_scores = self.util.cos_sim(query_embedding, self.corpus_embeddings)[0].cpu().numpy()
        
        # TF-IDF search
        from sklearn.metrics.pairwise import cosine_similarity
        query_tfidf = self.tfidf.transform([query])
        tfidf_scores = cosine_similarity(query_tfidf, self.tfidf_matrix)[0]
        
        # Hybrid blend (70% Semantic, 30% Keyword)
        blended_scores = 0.7 * semantic_scores + 0.3 * tfidf_scores
        
        import numpy as np
        top_indices = np.argsort(blended_scores)[::-1][:min(top_k, len(self.master_df))]
        
        results = []
        for idx in top_indices:
            row = self.master_df.iloc[idx]
            results.append({
                'code': str(row.get('code', '')),
                'description': str(row.get('description', '')),
                # Return purely the semantic score for the UI, so it doesn't look artificially low
                'score': float(semantic_scores[idx])
            })
            
        return results

import json
import queue

class LLMWorker(QThread):
    result_ready = pyqtSignal(dict)
    candidates_ready = pyqtSignal(str, list)
    error_occurred = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, ai_engine):
        super().__init__()
        self.ai_engine = ai_engine
        self.task_queue = queue.Queue()
        self.llm = None
        
    def push_task(self, query):
        # Clear previous pending tasks so we only process the latest click
        while not self.task_queue.empty():
            try:
                self.task_queue.get_nowait()
            except:
                pass
        self.task_queue.put(query)
        
    def run(self):
        try:
            from llama_cpp import Llama
            from core.utils import resource_path
            import os
            
            model_path = resource_path("models/qwen2-7b-instruct-q4_k_m.gguf")
            if not os.path.exists(model_path):
                self.error_occurred.emit(f"LLM model not found at {model_path}")
                return
                
            self.status_update.emit("Loading LLM model (first time only)...")
            self.llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
            
            while True:
                query = self.task_queue.get()
                if query is None:
                    break
                    
                self.status_update.emit("LLM Pre-Translating Arabic to English (Stage 1/3)...")
                translate_prompt = f"""<|im_start|>system
You are an expert medical translator. Translate the following Arabic medical instrument name or description into a clean, precise English medical term.Translate into English using Standardize naming according to MOHP / hospital procurement terminology in Egypt. Do not add any explanations or notes, just output the English translation.
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""
                trans_response = self.llm(translate_prompt, max_tokens=50, stop=["<|im_end|>"], echo=False)
                english_query = trans_response['choices'][0]['text'].strip()
                
                self.status_update.emit("Running Hybrid Search (Stage 2/3)...")
                candidates = self.ai_engine.find_top_matches(english_query, top_k=15)
                self.candidates_ready.emit(query, candidates)
                
                self.status_update.emit("Running LLM Reasoning (Stage 3/3)...")
                
                candidates_text = ""
                for idx, c in enumerate(candidates):
                    candidates_text += f"Code: {c['code']} - Description: {c['description']}\n"
                    
                prompt = f"""<|im_start|>system
You are a precise medical data extraction assistant. You will be given a raw medical instrument order list item, and a list of 15 candidate products from the KLS Martin catalog.
Your task is to identify the best matching product from the candidate list, even if it's an approximate match based on medical slang, abbreviations, or partial names.
You must reply ONLY in valid JSON format: {{"best_match_code": "the_code"}} or {{"best_match_code": null}} if absolutely none are a good match.
Do not output anything else. No explanations.
<|im_end|>
<|im_start|>user
Original Item: {query}
Translated Item: {english_query}

Candidates:
{candidates_text}
<|im_end|>
<|im_start|>assistant
"""
                response = self.llm(prompt, max_tokens=100, stop=["<|im_end|>"], echo=False)
                text_result = response['choices'][0]['text'].strip()
                
                import re
                json_match = re.search(r'\{.*?\}', text_result, re.DOTALL)
                if json_match:
                    try:
                        result_dict = json.loads(json_match.group())
                        result_dict['_query'] = query
                        self.result_ready.emit(result_dict)
                    except Exception as e:
                        self.error_occurred.emit(f"JSON Parse Error: {e} -> {text_result}")
                else:
                    self.error_occurred.emit(f"No JSON found. Output: {text_result}")
                    
        except Exception as e:
            self.error_occurred.emit(f"exception: {str(e)}")

class MapperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KLS Martin - AI Arabic Order Mapper")
        self.resize(1200, 700)
        
        self.memory = MappingMemory()
        self.master_df = None
        self.ai_engine = None
        
        self.queue_data = []
        self.current_selected_row = -1
        
        self.init_ui()
        self.load_master_data()
        
        self.llm_worker = LLMWorker(self.ai_engine)
        self.llm_worker.result_ready.connect(self.on_llm_result)
        self.llm_worker.candidates_ready.connect(self.on_candidates_ready)
        self.llm_worker.error_occurred.connect(self.on_llm_error)
        self.llm_worker.status_update.connect(self.on_llm_status)
        self.llm_worker.start()

    def on_llm_status(self, msg):
        self.lbl_ai_status.setText(msg)


    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)
        
        # --- Left Panel ---
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 10, 0)
        
        self.btn_upload = QPushButton("Upload Arabic Order List")
        self.btn_upload.setObjectName("primaryButton")
        self.btn_upload.clicked.connect(self.upload_order_list)
        left_layout.addWidget(self.btn_upload)
        
        self.queue_table = QTableWidget(0, 3)
        self.queue_table.setHorizontalHeaderLabels(["Status", "Arabic Term", "Qty"])
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.queue_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.queue_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.queue_table.itemSelectionChanged.connect(self.on_queue_selection_changed)
        left_layout.addWidget(self.queue_table)
        
        # --- Right Panel ---
        self.right_panel = QWidget()
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(10, 0, 0, 0)
        
        self.lbl_selected_term = QLabel("Select an item from the queue...")
        self.lbl_selected_term.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.lbl_selected_term.setWordWrap(True)
        right_layout.addWidget(self.lbl_selected_term)
        
        self.lbl_ai_status = QLabel("")
        self.lbl_ai_status.setStyleSheet("color: #555555;")
        right_layout.addWidget(self.lbl_ai_status)
        
        self.suggestions_scroll = QScrollArea()
        self.suggestions_scroll.setWidgetResizable(True)
        self.suggestions_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.suggestions_container = QWidget()
        self.suggestions_layout = QVBoxLayout(self.suggestions_container)
        self.suggestions_layout.setContentsMargins(0, 10, 10, 10)
        self.suggestions_layout.setSpacing(8)
        self.suggestions_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.suggestions_scroll.setWidget(self.suggestions_container)
        right_layout.addWidget(self.suggestions_scroll)
        
        self.suggestion_buttons = []
        
        right_layout.addStretch()
        
        override_layout = QHBoxLayout()
        self.txt_manual_search = QLineEdit()
        self.txt_manual_search.setPlaceholderText("Manual override search (Code or Keyword)...")
        self.txt_manual_search.textChanged.connect(self.on_manual_search)
        override_layout.addWidget(self.txt_manual_search)
        right_layout.addLayout(override_layout)
        
        self.manual_results_table = QTableWidget(0, 2)
        self.manual_results_table.setHorizontalHeaderLabels(["Code", "Description"])
        self.manual_results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.manual_results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.manual_results_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.manual_results_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.manual_results_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.manual_results_table.itemSelectionChanged.connect(self.on_manual_result_selected)
        self.manual_results_table.hide()
        right_layout.addWidget(self.manual_results_table)
        
        self.btn_confirm = QPushButton("Confirm Mapping")
        self.btn_confirm.setObjectName("primaryButton")
        self.btn_confirm.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.btn_confirm.setMinimumHeight(50)
        self.btn_confirm.clicked.connect(self.confirm_mapping)
        self.btn_confirm.setEnabled(False)
        right_layout.addWidget(self.btn_confirm)
        
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 2)
        
        # --- Bottom Panel ---
        bottom_layout = QHBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Loading...")
        bottom_layout.addWidget(self.progress_bar)
        
        self.btn_export = QPushButton("Export Conditioned List")
        self.btn_export.setObjectName("primaryButton")
        self.btn_export.clicked.connect(self.export_list)
        bottom_layout.addWidget(self.btn_export)
        
        main_layout.addLayout(bottom_layout)

        if not hasattr(self, 'master_df') or self.master_df is None:
            csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "KLS_All_Products.xlsx")
        if not os.path.exists(csv_path):
            QMessageBox.critical(self, "Error", f"Master database not found: {csv_path}")
            return
            
        try:
            self.master_df = pd.read_excel(csv_path, dtype=str)
            self.master_df['description'] = self.master_df['description'].fillna("")
            self.master_df['code'] = self.master_df['code'].fillna("")
            
            self.ai_engine = AIEngine(self.master_df)
            self.ai_engine.progress_updated.connect(self.on_ai_progress)
            self.ai_engine.engine_ready.connect(self.on_ai_ready)
            self.ai_engine.embedding_error.connect(self.on_ai_error)
            
            self.progress_bar.setFormat("AI Engine Initializing (Caching Vectors): %p%")
            self.btn_upload.setEnabled(False)
            self.ai_engine.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load master database: {e}")

    def on_ai_progress(self, val):
        self.progress_bar.setValue(val)

    def on_ai_ready(self, success):
        if success:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("AI Engine Ready.")
            self.btn_upload.setEnabled(True)
        else:
            self.progress_bar.setFormat("AI Engine Failed.")

    def on_ai_error(self, err_msg):
        QMessageBox.warning(self, "AI Warning", f"Failed to load Sentence Transformer. AI suggestions will be disabled.\n\n{err_msg}")
        
    def upload_order_list(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Upload Arabic Order List", "", "Data Files (*.csv *.xlsx *.xls)")
        if not file_path:
            return
            
        dlg = MappingDialog(file_path, ['item/description', 'quantity'], allow_extras=False, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
            
        with show_loading(self, "Processing Order List..."):
            try:
                if file_path.lower().endswith('.csv'):
                    raw_df = pd.read_csv(file_path, header=dlg.header_row)
                else:
                    raw_df = pd.read_excel(file_path, sheet_name=dlg.selected_sheet, header=dlg.header_row)
                    
                mapped_cols = dlg.mappings
                item_col = mapped_cols.get('item/description')
                qty_col = mapped_cols.get('quantity')
                
                if not item_col or not qty_col:
                    QMessageBox.warning(self, "Error", "Please map both item/description and quantity columns.")
                    return
                    
                for _, row in raw_df.iterrows():
                    term = str(row[item_col]).strip() if pd.notna(row[item_col]) else ""
                    qty = int(row[qty_col]) if pd.notna(row[qty_col]) else 1
                    
                    if not term or term.lower() == 'nan':
                        continue
                        
                    memory_hit = self.memory.get_mapping(term)
                    if memory_hit:
                        kls_code, kls_desc = memory_hit
                        status = "Mapped (Memory)"
                    else:
                        kls_code, kls_desc = "", ""
                        status = "Pending"
                        
                    self.queue_data.append({
                        'arabic': term,
                        'qty': qty,
                        'status': status,
                        'kls_code': kls_code,
                        'kls_desc': kls_desc
                    })
                    
                self.refresh_queue_table()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to process file: {e}")

    def refresh_queue_table(self):
        self.queue_table.blockSignals(True)
        self.queue_table.setRowCount(len(self.queue_data))
        for i, item in enumerate(self.queue_data):
            status_item = QTableWidgetItem(item['status'])
            if item['status'] == "Pending":
                status_item.setForeground(QColor("#D9534F"))
            else:
                status_item.setForeground(QColor("#5CB85C"))
            self.queue_table.setItem(i, 0, status_item)
            
            self.queue_table.setItem(i, 1, QTableWidgetItem(item['arabic']))
            self.queue_table.setItem(i, 2, QTableWidgetItem(str(item['qty'])))
            
        self.queue_table.blockSignals(False)
        
    def on_queue_selection_changed(self):
        selected = self.queue_table.selectedItems()
        if not selected:
            self.current_selected_row = -1
            self.lbl_selected_term.setText("Select an item from the queue...")
            self.hide_suggestions()
            self.btn_confirm.setEnabled(False)
            return
            
        row = selected[0].row()
        self.current_selected_row = row
        data = self.queue_data[row]
        
        self.lbl_selected_term.setText(data['arabic'])
        self.txt_manual_search.clear()
        self.manual_results_table.hide()
        
        if data['status'].startswith("Mapped"):
            self.lbl_ai_status.setText(f"Currently Mapped to: {data['kls_code']} - {data['kls_desc']}")
            self.hide_suggestions()
            self.btn_confirm.setEnabled(False)
        else:
            self.hide_suggestions()
            self.lbl_ai_status.setText("Pushing task to 3-Stage LLM Pipeline...")
            self.btn_confirm.setEnabled(False)
            self.llm_worker.push_task(data['arabic'])

    def on_candidates_ready(self, query, candidates):
        if self.current_selected_row < 0: return
        data = self.queue_data[self.current_selected_row]
        if query != data['arabic']: return
        
        self.show_suggestions(candidates)

    def on_llm_result(self, result_dict):
        if self.current_selected_row < 0: return
        data = self.queue_data[self.current_selected_row]
        if result_dict.get('_query') != data['arabic']:
            return # Stale result for an older click
            
        best_code = result_dict.get('best_match_code')
        if best_code:
            self.lbl_ai_status.setText(f"LLM Recommended: {best_code}")
            for btn in self.suggestion_buttons:
                if btn.property('kls_code') == best_code:
                    btn.setChecked(True)
                    self.btn_confirm.setEnabled(True)
                    # Scroll to ensure it's visible
                    self.suggestions_scroll.ensureWidgetVisible(btn)
                    break
        else:
            self.lbl_ai_status.setText("LLM: No confident match found.")
            
    def on_llm_error(self, err_msg):
        self.lbl_ai_status.setText(f"LLM Error: {err_msg}")

    def hide_suggestions(self):
        while self.suggestions_layout.count():
            item = self.suggestions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self.suggestion_buttons.clear()

    def show_suggestions(self, suggestions):
        self.hide_suggestions()
        if not suggestions:
            self.lbl_ai_status.setText("No AI suggestions found.")
            return
            
        self.lbl_ai_status.setText("AI Suggestions (Select one to confirm):")
        
        for sug in suggestions:
            btn = QPushButton()
            pct = int(sug['score'] * 100)
            btn.setText(f"[{pct}% Match] {sug['code']}\n{sug['description']}")
            btn.setProperty('kls_code', sug['code'])
            btn.setProperty('kls_desc', sug['description'])
            
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 2px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 12px;
                    text-align: left;
                    font-size: 13px;
                }
                QPushButton:checked {
                    border: 2px solid #2A82DA;
                    background-color: #f0f7ff;
                }
            """)
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.clicked.connect(self.on_suggestion_clicked)
            
            self.suggestion_buttons.append(btn)
            self.suggestions_layout.addWidget(btn)

    def on_suggestion_clicked(self):
        self.manual_results_table.clearSelection()
        self.btn_confirm.setEnabled(True)

    def on_manual_search(self, text):
        self.hide_suggestions()
        self.btn_confirm.setEnabled(False)
        
        if not text.strip():
            self.manual_results_table.hide()
            if self.current_selected_row >= 0 and self.queue_data[self.current_selected_row]['status'] == "Pending":
                self.on_queue_selection_changed()
            return
            
        self.lbl_ai_status.setText("Manual Search Results:")
        self.manual_results_table.show()
        
        if self.master_df is None or self.master_df.empty:
            return
            
        q = text.lower()
        mask = self.master_df['code'].str.lower().str.contains(q, na=False) | self.master_df['description'].str.lower().str.contains(q, na=False)
        results = self.master_df[mask].head(20)
        
        self.manual_results_table.blockSignals(True)
        self.manual_results_table.setRowCount(len(results))
        for i, (_, row) in enumerate(results.iterrows()):
            self.manual_results_table.setItem(i, 0, QTableWidgetItem(str(row['code'])))
            self.manual_results_table.setItem(i, 1, QTableWidgetItem(str(row['description'])))
        self.manual_results_table.blockSignals(False)

    def on_manual_result_selected(self):
        if self.manual_results_table.selectedItems():
            self.btn_confirm.setEnabled(True)

    def confirm_mapping(self):
        if self.current_selected_row < 0:
            return
            
        kls_code, kls_desc = "", ""
        
        if self.manual_results_table.isVisible() and self.manual_results_table.selectedItems():
            row = self.manual_results_table.selectedItems()[0].row()
            kls_code = self.manual_results_table.item(row, 0).text()
            kls_desc = self.manual_results_table.item(row, 1).text()
        else:
            for btn in self.suggestion_buttons:
                if btn.isChecked():
                    kls_code = btn.property('kls_code')
                    kls_desc = btn.property('kls_desc')
                    break
                    
        if not kls_code:
            return
            
        data = self.queue_data[self.current_selected_row]
        arabic_term = data['arabic']
        
        data['kls_code'] = kls_code
        data['kls_desc'] = kls_desc
        data['status'] = "Mapped (User)"
        
        self.memory.save_mapping(arabic_term, kls_code, kls_desc)
        
        self.refresh_queue_table()
        
        next_row = self.current_selected_row + 1
        if next_row < len(self.queue_data):
            self.queue_table.selectRow(next_row)
        else:
            self.btn_confirm.setEnabled(False)
            self.hide_suggestions()
            self.lbl_ai_status.setText("Queue complete.")

    def export_list(self):
        if not self.queue_data:
            return
            
        mapped_data = [d for d in self.queue_data if d['status'].startswith("Mapped")]
        if not mapped_data:
            QMessageBox.information(self, "Info", "No mapped items to export.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export Conditioned List", "Conditioned_List.csv", "CSV Files (*.csv)")
        if not path:
            return
            
        export_df = pd.DataFrame([{
            'code': d['kls_code'],
            'description': d['kls_desc'],
            'quantity': d['qty']
        } for d in mapped_data])
        
        try:
            export_df.to_csv(path, index=False)
            QMessageBox.information(self, "Success", f"Exported {len(mapped_data)} mapped items successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")

if __name__ == '__main__':
    # Initialize llama.cpp backend on the main thread BEFORE PyQt6
    # This prevents the 0x0000000000000000 access violation crash on Windows
    try:
        import llama_cpp
        llama_cpp.llama_backend_init()
    except Exception:
        pass

    myappid = 'klsmartin.mapper.1.0'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    app = QApplication(sys.argv)
    
    app_font = QFont("Segoe UI", 10)
    app.setFont(app_font)

    icon_path = resource_path("icon.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    app.setStyle(QStyleFactory.create("Fusion"))
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
    palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Button, QColor(230, 230, 230))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    app.setPalette(palette)
    app.setStyleSheet(APP_STYLESHEET)

    window = MapperApp()
    window.show()
    sys.exit(app.exec())
