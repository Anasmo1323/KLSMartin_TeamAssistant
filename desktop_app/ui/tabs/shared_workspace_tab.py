import os
import json
import requests
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QMessageBox, QTableWidgetItem, QLineEdit, QComboBox)
from PyQt6.QtCore import QThread, pyqtSignal, QSettings
from ui.widgets.dynamic_table import DynamicTableWidget

FIREBASE_URL = "https://klsmartin-workspace-default-rtdb.europe-west1.firebasedatabase.app"

class PushWorker(QThread):
    def __init__(self, username, cells):
        super().__init__()
        self.username = username
        self.cells = cells
        
    def run(self):
        try:
            # PUT request will completely overwrite the data for this specific username
            url = f"{FIREBASE_URL}/workspaces/{self.username}.json"
            requests.put(url, json=self.cells, timeout=5)
        except Exception as e:
            print("Push error:", e)

class FetchUsersWorker(QThread):
    users_ready = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        
    def run(self):
        try:
            # ?shallow=true returns only the keys (usernames) without downloading all the heavy data
            url = f"{FIREBASE_URL}/workspaces.json?shallow=true"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    users = list(data.keys())
                    self.users_ready.emit(users)
                else:
                    self.users_ready.emit([])
        except:
            pass

class PullWorker(QThread):
    pull_ready = pyqtSignal(list)
    
    def __init__(self, username):
        super().__init__()
        self.username = username
        
    def run(self):
        try:
            url = f"{FIREBASE_URL}/workspaces/{self.username}.json"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    self.pull_ready.emit(data)
        except:
            pass

class SharedWorkspaceTab(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("KLSMartin", "TeamAssistant")
        
        self.init_ui()
        self.load_settings()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Top Connection Panel ---
        conn_layout = QHBoxLayout()
        
        # My Username
        conn_layout.addWidget(QLabel("My Username:"))
        self.txt_username = QLineEdit()
        self.txt_username.setPlaceholderText("e.g. Anas")
        self.txt_username.setMaximumWidth(150)
        self.txt_username.textChanged.connect(self.save_settings)
        conn_layout.addWidget(self.txt_username)
        
        self.btn_push = QPushButton("Push My Sheet (To Cloud)")
        self.btn_push.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        self.btn_push.clicked.connect(self.push_data)
        conn_layout.addWidget(self.btn_push)
        
        conn_layout.addStretch()
        layout.addLayout(conn_layout)
        
        # --- Middle Pull Panel ---
        pull_layout = QHBoxLayout()
        
        pull_layout.addWidget(QLabel("Pull Member Data:"))
        self.cmb_members = QComboBox()
        self.cmb_members.setMinimumWidth(150)
        pull_layout.addWidget(self.cmb_members)
        
        self.btn_refresh_members = QPushButton("Refresh List")
        self.btn_refresh_members.clicked.connect(self.refresh_members)
        pull_layout.addWidget(self.btn_refresh_members)
        
        self.btn_pull = QPushButton("Pull & Overwrite")
        self.btn_pull.setStyleSheet("background-color: #4CAF50; color: white;")
        self.btn_pull.clicked.connect(self.pull_data)
        pull_layout.addWidget(self.btn_pull)
        
        pull_layout.addStretch()
        
        # Undo/Redo Buttons
        self.btn_undo = QPushButton("Undo (Ctrl+Z)")
        self.btn_undo.clicked.connect(lambda: self.table.undo())
        pull_layout.addWidget(self.btn_undo)
        
        self.btn_redo = QPushButton("Redo (Ctrl+Y)")
        self.btn_redo.clicked.connect(lambda: self.table.redo())
        pull_layout.addWidget(self.btn_redo)
        
        self.btn_clear = QPushButton("Clear Local Sheet")
        self.btn_clear.clicked.connect(self.clear_workspace)
        pull_layout.addWidget(self.btn_clear)
        
        layout.addLayout(pull_layout)
        
        # --- Table ---
        self.table = DynamicTableWidget()
        self.table.setRowCount(100)
        self.table.setColumnCount(26)
        
        headers = [chr(65 + i) for i in range(26)]
        self.table.setHorizontalHeaderLabels(headers)
        
        layout.addWidget(self.table)
        
    def load_settings(self):
        saved_user = self.settings.value("shared_username", "")
        self.txt_username.setText(saved_user)
        self.refresh_members()
        
    def save_settings(self):
        self.settings.setValue("shared_username", self.txt_username.text().strip())
        
    def push_data(self):
        username = self.txt_username.text().strip()
        if not username:
            QMessageBox.warning(self, "Error", "Please enter a Username before pushing.")
            return
            
        snapshot = self.table.get_snapshot()
        self.pusher = PushWorker(username, snapshot['cells'])
        self.pusher.start()
        QMessageBox.information(self, "Success", "Your sheet has been pushed to the Firebase Cloud!")
        
    def refresh_members(self):
        self.fetcher = FetchUsersWorker()
        self.fetcher.users_ready.connect(self.on_users_ready)
        self.fetcher.start()
        
    def on_users_ready(self, users):
        current_text = self.cmb_members.currentText()
        self.cmb_members.clear()
        self.cmb_members.addItems(users)
        
        idx = self.cmb_members.findText(current_text)
        if idx >= 0:
            self.cmb_members.setCurrentIndex(idx)
            
    def pull_data(self):
        target_user = self.cmb_members.currentText()
        if not target_user:
            QMessageBox.warning(self, "Error", "No member selected to pull from.")
            return
            
        # Save undo snapshot BEFORE pulling!
        self.table.save_snapshot()
            
        self.puller = PullWorker(target_user)
        self.puller.pull_ready.connect(self.on_pull_ready)
        self.puller.start()
        
    def on_pull_ready(self, data):
        self.table.is_restoring = True
        
        max_row = max([cell['row'] for cell in data], default=-1)
        max_col = max([cell['col'] for cell in data], default=-1)
        
        if max_row >= self.table.rowCount():
            self.table.setRowCount(max_row + 10)
        if max_col >= self.table.columnCount():
            self.table.setColumnCount(max_col + 5)
            
        # Overwrite overlapping cells only
        for cell in data:
            row, col, val = cell['row'], cell['col'], cell['value']
            item = self.table.item(row, col)
            if not item:
                item = QTableWidgetItem(val)
                self.table.setItem(row, col, item)
            else:
                item.setText(val)
                
        self.table.is_restoring = False
        QMessageBox.information(self, "Success", "Data pulled successfully! (Press Ctrl+Z if you want to Undo)")
        
    def clear_workspace(self):
        reply = QMessageBox.question(self, "Confirm", "Clear your local sheet? (You can Undo this)",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.table.save_snapshot()
            self.table.is_restoring = True
            self.table.clearContents()
            self.table.is_restoring = False
