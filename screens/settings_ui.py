import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QLineEdit, QPushButton, QFileDialog, QMessageBox, QCheckBox,
                             QAbstractButton, QSizePolicy)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QBrush

from configs.settings_manager import settings
from configs.config import DATA_DIR, MAX_HISTORY

class SwitchButton(QAbstractButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._offset = 4
        self._anim = QPropertyAnimation(self, b"offset", self)
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
    @pyqtProperty(int)
    def offset(self):
        return self._offset
        
    @offset.setter
    def offset(self, value):
        self._offset = value
        self.update()
        
    def sizeHint(self):
        return QSize(46, 24)
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Track parameters
        track_color = QColor("#e95420") if self.isChecked() else QColor("#444444")
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Draw track
        painter.drawRoundedRect(0, 0, self.width(), self.height(), self.height() / 2, self.height() / 2)
        
        # Draw thumb (knob)
        painter.setBrush(QBrush(QColor("#ffffff")))
        thumb_size = self.height() - 8
        painter.drawEllipse(self._offset, 4, thumb_size, thumb_size)
        
    def nextCheckState(self):
        super().nextCheckState()
        self.animate(self.isChecked())
        
    def animate(self, checked):
        start_val = self._offset
        end_val = (self.width() - self.height() + 4) if checked else 4
        
        self._anim.setStartValue(start_val)
        self._anim.setEndValue(end_val)
        self._anim.start()
        
    def setChecked(self, checked):
        super().setChecked(checked)
        end = self.width() - self.height() + 4
        self._offset = end if checked else 4
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        end = self.width() - self.height() + 4
        self._offset = end if self.isChecked() else 4

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
            QCheckBox {
                color: #ffffff;
                font-size: 13px;
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
        self.hotkey_input.setText(settings.get('hotkey', "<ctrl>+'"))
        
        self.open_shortcuts_btn = QPushButton("Configurar no Sistema")
        self.open_shortcuts_btn.setToolTip("Abre o painel do sistema operacional para configurar atalhos globais.")
        self.open_shortcuts_btn.clicked.connect(self.open_system_shortcuts)
        
        if sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY'):
            self.hotkey_input.setReadOnly(True)
            self.hotkey_input.setToolTip("No Wayland, configure o atalho nas configurações do seu sistema para rodar o comando: fast-paste show")
            self.hotkey_input.setText("Configurar nas teclas do sistema")
        else:
            self.hotkey_input.setToolTip("Exemplo: <ctrl>+' (Padrão)")
            
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_input)
        hotkey_layout.addWidget(self.open_shortcuts_btn)
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

        # 4. Iniciar com o sistema (Autostart)
        autostart_layout = QHBoxLayout()
        autostart_label = QLabel("Iniciar automaticamente com o sistema")
        autostart_label.setToolTip("Inicia o monitor de clipboard automaticamente ao fazer login no sistema.")
        
        self.autostart_switch = SwitchButton()
        self.autostart_switch.setToolTip("Inicia o monitor de clipboard automaticamente ao fazer login no sistema.")
        
        try:
            from core import autostart
            self.autostart_switch.setChecked(autostart.is_autostart_enabled())
        except Exception as e:
            print(f"[Settings] Error checking autostart state: {e}")
            
        autostart_layout.addWidget(autostart_label)
        autostart_layout.addStretch(1)
        autostart_layout.addWidget(self.autostart_switch)
        layout.addLayout(autostart_layout)
        
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

        # Configurar Autostart (Iniciar com o sistema)
        try:
            from core import autostart
            if self.autostart_switch.isChecked():
                autostart.enable_autostart()
            else:
                autostart.disable_autostart()
        except Exception as e:
            print(f"[Settings] Error saving autostart setting: {e}")
            
        self.settings_closed.emit(True)

    def open_system_shortcuts(self):
        import shutil
        import subprocess
        try:
            if sys.platform.startswith("linux"):
                if shutil.which("gnome-control-center"):
                    subprocess.Popen(["gnome-control-center", "keyboard"])
                elif shutil.which("systemsettings5"):
                    subprocess.Popen(["systemsettings5", "kcm_keys"])
                elif shutil.which("xfce4-keyboard-settings"):
                    subprocess.Popen(["xfce4-keyboard-settings"])
                else:
                    QMessageBox.information(self, "Atalhos no Linux", 
                        "No Linux, configure um atalho global nas configurações de teclado do seu sistema para executar o comando:\n\nfast-paste show")
            elif sys.platform.startswith("darwin"):
                # macOS Keyboard Shortcuts Preference Pane
                subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.keyboard?shortcuts"])
            elif sys.platform.startswith("win32") or sys.platform.startswith("win"):
                os.system("start ms-settings:keyboard")
        except Exception as e:
            print(f"[FastPaste] Error opening system keyboard settings: {e}")
