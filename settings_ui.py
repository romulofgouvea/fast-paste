import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QLineEdit, QPushButton, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal

from settings_manager import settings
from config import DATA_DIR, MAX_HISTORY

class SettingsWidget(QWidget):
    settings_closed = pyqtSignal(bool)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Apply dark theme stylesheet to match popup
        self.setStyleSheet("""
            QWidget {
                background-color: transparent;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit, QSpinBox {
                background-color: #2c2c2c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 5px;
            }
            QPushButton {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton#saveButton {
                background-color: #e95420;
                border: None;
            }
            QPushButton#saveButton:hover {
                background-color: #ff6b36;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 1. Configuração da quantidade de cópias (Fila)
        hist_layout = QHBoxLayout()
        hist_label = QLabel("Limite de histórico (Cópias não fixadas):")
        self.hist_spin = QSpinBox()
        self.hist_spin.setRange(10, 5000)
        self.hist_spin.setValue(settings.get('max_history', MAX_HISTORY))
        self.hist_spin.setToolTip("Quando atingir este limite, a cópia mais antiga será excluída (fila).")
        hist_layout.addWidget(hist_label)
        hist_layout.addWidget(self.hist_spin)
        layout.addLayout(hist_layout)

        # 2. Configuração de Hotkey
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Atalho Global:")
        self.hotkey_input = QLineEdit()
        self.hotkey_input.setText(settings.get('hotkey', '<ctrl>+<shift>+v'))
        
        if sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY'):
            self.hotkey_input.setReadOnly(True)
            self.hotkey_input.setToolTip("No Wayland, defina o atalho nas configurações do seu sistema operacional\npara rodar o comando: python3 fast_paste.py show")
            self.hotkey_input.setText("Configurar no Ubuntu (GNOME)")
        else:
            self.hotkey_input.setToolTip("Exemplo: <ctrl>+<shift>+v (Padrão Windows/Mac)")
            
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_input)
        layout.addLayout(hotkey_layout)

        # 3. Caminho do banco de dados
        db_layout = QVBoxLayout()
        db_label = QLabel("Pasta do Banco de Dados:")
        
        db_input_layout = QHBoxLayout()
        self.db_input = QLineEdit()
        self.db_input.setText(settings.get('db_path', DATA_DIR))
        self.db_input.setReadOnly(True) # Para forçar uso do dialog
        
        db_browse_btn = QPushButton("Procurar...")
        db_browse_btn.clicked.connect(self.browse_db_path)
        
        db_input_layout.addWidget(self.db_input)
        db_input_layout.addWidget(db_browse_btn)
        
        db_layout.addWidget(db_label)
        db_layout.addLayout(db_input_layout)
        layout.addLayout(db_layout)
        
        # Info text
        info = QLabel("Dica: Itens fixados (★) nunca são excluídos automaticamente.")
        info.setStyleSheet("color: #a1a1a1; font-style: italic;")
        layout.addWidget(info)
        
        layout.addStretch(1)

        # Botões Salvar / Cancelar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.cancel_settings)
        
        save_btn = QPushButton("Salvar Configurações")
        save_btn.setObjectName("saveButton")
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        
        layout.addLayout(btn_layout)

    def browse_db_path(self):
        # Workaround for Wayland: Hide the stays-on-top parent window 
        # so the modal file dialog can actually be seen!
        parent_window = self.window()
        was_visible = parent_window.isVisible()
        if was_visible:
            parent_window.hide()
            
        folder = QFileDialog.getExistingDirectory(None, "Selecione a pasta para salvar o Banco de Dados", self.db_input.text())
        
        if was_visible:
            parent_window.show()
            parent_window.activateWindow()
            parent_window.raise_()
            
        if folder:
            self.db_input.setText(folder)

    def cancel_settings(self):
        self.settings_closed.emit(False)

    def save_settings(self):
        # Validação
        if not os.path.exists(self.db_input.text()):
            QMessageBox.warning(self, "Erro", "A pasta selecionada para o banco de dados não existe.")
            return

        # Salvar
        settings.set('max_history', self.hist_spin.value())
        settings.set('db_path', self.db_input.text())
        
        # No linux (wayland) não tentamos salvar o hotkey do campo read-only
        if not (sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY')):
            settings.set('hotkey', self.hotkey_input.text())
            
        self.settings_closed.emit(True)
