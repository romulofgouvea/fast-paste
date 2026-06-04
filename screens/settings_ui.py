import sys
import os
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QSpinBox, QLineEdit, QPushButton, QFileDialog, QMessageBox, QCheckBox,
                             QAbstractButton, QSizePolicy, QRadioButton, QButtonGroup, QDialog,
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, pyqtProperty, QEasingCurve
from PyQt6.QtGui import QPainter, QColor, QBrush, QKeySequence

from configs.settings_manager import settings
from configs.config import DATA_DIR, MAX_HISTORY, APP_NAME, UI_COLORS, DEFAULT_SETTINGS

class CustomModal(QDialog):
    def __init__(self, parent=None, title="", text="", is_input=False, input_password=False, default_input="", show_cancel=False):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(420)
        
        self.container = QWidget(self)
        self.container.setObjectName("ModalContainer")
        
        self.setStyleSheet(f"""
            QWidget#ModalContainer {{
                background-color: {UI_COLORS.get('card_bg', 'rgba(36, 36, 36, 0.98)')};
                border: 1px solid {UI_COLORS.get('card_border', 'rgba(60, 60, 60, 0.8)')};
                border-radius: 12px;
            }}
            QLabel {{ color: {UI_COLORS.get('fg', '#ffffff')}; font-size: 14px; background: transparent; }}
            QLabel#Title {{ font-weight: bold; font-size: 16px; margin-bottom: 4px; }}
            QPushButton {{ 
                background-color: #3a3a3a; color: #ffffff; padding: 8px 16px; 
                border-radius: 6px; border: 1px solid #5a5a5a; font-size: 13px; 
            }}
            QPushButton:hover {{ background-color: #4a4a4a; }}
            QPushButton#primary {{ background-color: {UI_COLORS.get('selected', '#FF7A00')}; border: none; font-weight: bold; }}
            QPushButton#primary:hover {{ background-color: {UI_COLORS.get('selected', '#FF7A00')}; opacity: 0.8; }}
            QLineEdit {{
                background-color: rgba(20, 20, 20, 0.6); border: 1px solid #444;
                border-radius: 6px; padding: 8px; color: #ffffff; font-size: 14px;
                selection-background-color: {UI_COLORS.get('selected', '#FF7A00')};
            }}
            QLineEdit:focus {{ border: 1px solid {UI_COLORS.get('selected', '#FF7A00')}; }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        title_label = QLabel(title)
        title_label.setObjectName("Title")
        title_label.setWordWrap(True)
        title_label.setFixedWidth(372)
        layout.addWidget(title_label)
        
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setFixedWidth(372)
        layout.addWidget(text_label)
        
        if is_input:
            self.input_field = QLineEdit()
            if input_password:
                self.input_field.setEchoMode(QLineEdit.EchoMode.Password)
            if default_input:
                self.input_field.setText(default_input)
            layout.addWidget(self.input_field)
            
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        
        if show_cancel:
            cancel_btn = QPushButton("Cancelar")
            cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(cancel_btn)
            
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("primary")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        if is_input:
            self.input_field.setFocus()
        
    def textValue(self):
        if hasattr(self, 'input_field'):
            return self.input_field.text()
        return ""
        
    @classmethod
    def show_message(cls, parent, title, text):
        dialog = cls(parent, title, text, show_cancel=False)
        dialog.exec()
        
    @classmethod
    def confirm(cls, parent, title, text):
        dialog = cls(parent, title, text, show_cancel=True)
        return dialog.exec() == QDialog.DialogCode.Accepted
        
    @classmethod
    def get_text(cls, parent, title, label, is_password=False, default_text=""):
        dialog = cls(parent, title, label, is_input=True, input_password=is_password, default_input=default_text, show_cancel=True)
        ok = dialog.exec() == QDialog.DialogCode.Accepted
        return dialog.textValue(), ok

def pynput_to_qt(pynput_str):
    if not pynput_str:
        return ""
    parts = pynput_str.split('+')
    qt_parts = []
    for part in parts:
        if part == "<ctrl>":
            qt_parts.append("Ctrl")
        elif part == "<shift>":
            qt_parts.append("Shift")
        elif part == "<alt>":
            qt_parts.append("Alt")
        elif part == "<cmd>":
            qt_parts.append("Cmd")
        else:
            clean = part.replace('<', '').replace('>', '')
            qt_parts.append(clean.upper() if len(clean) == 1 else clean.capitalize())
    return "+".join(qt_parts)

class HotkeyLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setPlaceholderText("Clique para gravar...")
        self.recording = False
        self.raw_hotkey = settings.get('hotkey', DEFAULT_SETTINGS['hotkey'])
        self.native_mac_key_code = settings.get('hotkey_mac_key_code', DEFAULT_SETTINGS['hotkey_mac_key_code'])
        
        if sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY'):
            self.setText("Configurado no Sistema")
            self.setStyleSheet("background-color: #1a1a1a; color: #888888; border-color: #333333;")
        else:
            self.setText(pynput_to_qt(self.raw_hotkey))
            self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if self.recording:
            event.accept()
            return
        if not self.recording:
            if sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY'):
                super().mousePressEvent(event)
                return
            self.start_recording()
        event.accept()

    def focusOutEvent(self, event):
        if self.recording:
            self.stop_recording()
        super().focusOutEvent(event)

    def start_recording(self):
        import core.app
        core.app.pause_hotkeys()
        self.recording = True
        self.setText("Pressione o atalho...")
        self.setStyleSheet("background-color: #3a1c1c; border: 1.5px solid #ff4444; color: #ffffff;")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.grabKeyboard()

    def stop_recording(self):
        self.recording = False
        self.releaseKeyboard()
        self.setStyleSheet("")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if not self.raw_hotkey:
            self.setText(pynput_to_qt(settings.get('hotkey', DEFAULT_SETTINGS['hotkey'])))
        else:
            self.setText(pynput_to_qt(self.raw_hotkey))

    def keyPressEvent(self, event):
        if not self.recording:
            super().keyPressEvent(event)
            return

        key = event.key()
        modifiers = event.modifiers()

        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        parts = []
        pynput_parts = []
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
            pynput_parts.append("<ctrl>")
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
            pynput_parts.append("<shift>")
        if modifiers & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")
            pynput_parts.append("<alt>")
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            parts.append("Meta")
            pynput_parts.append("<cmd>")

        key_str = ""
        pynput_key = ""
        
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            key_str = chr(key).upper()
            pynput_key = chr(key).lower()
        elif Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            key_str = chr(key)
            pynput_key = chr(key)
        elif key == Qt.Key.Key_Apostrophe:
            key_str = "'"
            pynput_key = "'"
        elif key == Qt.Key.Key_QuoteLeft:
            key_str = "`"
            pynput_key = "`"
        elif key == Qt.Key.Key_QuoteDbl:
            key_str = '"'
            pynput_key = '"'
        elif key == Qt.Key.Key_Space:
            key_str = "Space"
            pynput_key = "<space>"
        elif key == Qt.Key.Key_Escape:
            self.stop_recording()
            return
        else:
            key_seq = QKeySequence(key).toString()
            if key_seq:
                key_str = key_seq
                pynput_key = key_seq.lower()

        if not key_str:
            return

        parts.append(key_str)
        pynput_parts.append(pynput_key)

        self.raw_hotkey = "+".join(pynput_parts)
        native_virtual_key = event.nativeVirtualKey() or event.nativeScanCode()
        if native_virtual_key:
            self.native_mac_key_code = native_virtual_key
        self.setText("+".join(parts))
        self.stop_recording()

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
        from configs.config import UI_COLORS
        track_color = QColor(UI_COLORS.get('selected', '#FF7A00')) if self.isChecked() else QColor("#444444")
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
        
        from configs.config import UI_COLORS
        accent_color = UI_COLORS.get('selected', '#FF7A00')
        
        # Apply dark theme stylesheet to match popup
        self.setStyleSheet(f"""
            QWidget {{
                background-color: transparent;
                color: #ffffff;
            }}
            QLabel {{
                color: #ffffff;
                font-size: 13px;
                background: transparent;
            }}
            QLineEdit, QSpinBox {{
                background-color: #2c2c2c;
                color: #ffffff;
                border: 1px solid #4a4a4a;
                border-radius: 4px;
                padding: 5px;
                font-size: 13px;
                selection-background-color: {accent_color};
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 1px solid {accent_color};
            }}
            QPushButton {{
                background-color: #3a3a3a;
                color: #ffffff;
                border: 1px solid #5a5a5a;
                border-radius: 4px;
                padding: 6px 12px;
            }}
            QPushButton:hover {{
                background-color: #4a4a4a;
            }}
            QPushButton#saveButton {{
                background-color: {accent_color};
                border: None;
            }}
            QPushButton#saveButton:hover {{
                background-color: {accent_color};
                opacity: 0.8;
            }}
            QCheckBox {{
                color: #ffffff;
                font-size: 13px;
            }}
            QRadioButton {{
                color: #ffffff;
                font-size: 13px;
                spacing: 8px;
                background: transparent;
            }}
            QRadioButton:hover {{
                color: {accent_color};
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 9px;
                border: 2px solid #5a5a5a;
                background-color: #2c2c2c;
            }}
            QRadioButton::indicator:hover {{
                border-color: {accent_color};
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid {accent_color};
                background-color: {accent_color};
            }}
            QFrame.SectionCard {{
                background-color: rgba(45, 45, 45, 0.35);
                border: 1px solid rgba(80, 80, 80, 0.25);
                border-radius: 12px;
            }}
        """)

        from core import general_settings, history_settings, data_settings

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Scroll Area for sections
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: rgba(0, 0, 0, 0.2);
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("ScrollContent")
        scroll_content.setStyleSheet("QWidget#ScrollContent { background: transparent; }")
        
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 4, 0)

        # 1. Geral Section Card
        geral_card = QFrame()
        geral_card.setObjectName("GeralCard")
        geral_card.setFrameShape(QFrame.Shape.NoFrame)
        geral_card.setProperty("class", "SectionCard")
        geral_card.setStyleSheet("QFrame#GeralCard { background-color: rgba(45, 45, 45, 0.3); border: 1px solid rgba(80, 80, 80, 0.2); border-radius: 12px; }")
        
        geral_layout = QVBoxLayout(geral_card)
        geral_layout.setContentsMargins(14, 14, 14, 14)
        geral_layout.setSpacing(12)
        
        geral_header = QLabel("Geral")
        geral_header.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {accent_color};")
        geral_layout.addWidget(geral_header)
        
        # Row 1: Global hotkey
        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Atalho Global:")
        self.hotkey_input = HotkeyLineEdit()
        self.open_shortcuts_btn = QPushButton("Configurar no Sistema")
        self.open_shortcuts_btn.setToolTip("Abre o painel do sistema operacional para configurar atalhos globais.")
        self.open_shortcuts_btn.clicked.connect(self.open_system_shortcuts)
        
        if sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY'):
            self.hotkey_input.setToolTip(f"No Wayland, configure o atalho nas configurações do seu sistema para rodar o comando: {APP_NAME.lower()} show")
        else:
            self.hotkey_input.setToolTip("Clique no campo e pressione a combinação de teclas desejada (ex: Ctrl+Shift+V). Pressione Esc para cancelar.")
            
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_input)
        hotkey_layout.addWidget(self.open_shortcuts_btn)
        geral_layout.addLayout(hotkey_layout)

        # Row 2: Theme color
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Cor do Tema:")
        self.theme_btn_group = QButtonGroup(self)
        colors = [
            ("#e95420", "Ubuntu Orange"),
            ("#0078D7", "Azul Windows"),
            ("#10B981", "Verde Esmeralda"),
            ("#8B5CF6", "Roxo Violeta")
        ]
        theme_options_layout = QHBoxLayout()
        current_theme = general_settings.get_theme_color().upper()
        for i, (hex_code, name) in enumerate(colors):
            btn = QRadioButton()
            btn.setToolTip(name)
            btn.setStyleSheet(f"""
                QRadioButton::indicator {{
                    width: 20px; height: 20px; border-radius: 11px;
                    background-color: {hex_code}; border: 2px solid transparent;
                }}
                QRadioButton::indicator:checked {{
                    border: 2px solid #ffffff;
                }}
            """)
            if hex_code.upper() == current_theme:
                btn.setChecked(True)
            self.theme_btn_group.addButton(btn, i)
            btn.setProperty("theme_hex", hex_code)
            theme_options_layout.addWidget(btn)
        theme_options_layout.addStretch(1)
        theme_layout.addWidget(theme_label)
        theme_layout.addLayout(theme_options_layout)
        geral_layout.addLayout(theme_layout)

        # Row 3: Autostart
        autostart_layout = QHBoxLayout()
        autostart_label = QLabel("Iniciar automaticamente com o sistema")
        self.autostart_switch = SwitchButton()
        self.autostart_switch.setChecked(general_settings.is_autostart_enabled())
        autostart_layout.addWidget(autostart_label)
        autostart_layout.addStretch(1)
        autostart_layout.addWidget(self.autostart_switch)
        geral_layout.addLayout(autostart_layout)

        # Row 4: Interaction Mode
        mode_layout = QVBoxLayout()
        mode_label = QLabel("Modo de Interação:")
        mode_options_layout = QHBoxLayout()
        self.mode_group = QButtonGroup(self)
        self.mode1_radio = QRadioButton("Modo 1 (Clique único)")
        self.mode1_radio.setToolTip("Clique único copia/cola e fecha o popup. Fecha ao perder o foco (clicar fora).")
        self.mode2_radio = QRadioButton("Modo 2 (Drag Drop)")
        self.mode2_radio.setToolTip("Clique duplo copia/cola. Permite arrastar itens e mover a janela. Fica aberto ao clicar fora.")
        self.mode_group.addButton(self.mode1_radio, 1)
        self.mode_group.addButton(self.mode2_radio, 2)
        current_mode = general_settings.get_interaction_mode()
        if current_mode == 1:
            self.mode1_radio.setChecked(True)
        else:
            self.mode2_radio.setChecked(True)
        mode_options_layout.addWidget(self.mode1_radio)
        mode_options_layout.addWidget(self.mode2_radio)
        mode_options_layout.addStretch(1)
        mode_layout.addWidget(mode_label)
        mode_layout.addLayout(mode_options_layout)
        geral_layout.addLayout(mode_layout)

        layout.addWidget(geral_card)

        # 2. Histórico Section Card
        hist_card = QFrame()
        hist_card.setObjectName("HistCard")
        hist_card.setFrameShape(QFrame.Shape.NoFrame)
        hist_card.setStyleSheet("QFrame#HistCard { background-color: rgba(45, 45, 45, 0.3); border: 1px solid rgba(80, 80, 80, 0.2); border-radius: 12px; }")
        
        hist_layout = QVBoxLayout(hist_card)
        hist_layout.setContentsMargins(14, 14, 14, 14)
        hist_layout.setSpacing(12)
        
        hist_header = QLabel("Histórico")
        hist_header.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {accent_color};")
        hist_layout.addWidget(hist_header)
        
        # Row 1: Limit maximum items
        limit_layout = QHBoxLayout()
        limit_label = QLabel("Limite máximo de itens:")
        self.hist_spin = QSpinBox()
        self.hist_spin.setRange(10, 5000)
        self.hist_spin.setValue(history_settings.get_max_history())
        self.hist_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.hist_spin.setFixedWidth(80)
        limit_layout.addWidget(limit_label)
        limit_layout.addWidget(self.hist_spin)
        limit_layout.addStretch(1)
        hist_layout.addLayout(limit_layout)
        
        # Row 2: Delete automatically after X days
        days_layout = QHBoxLayout()
        days_label = QLabel("Apagar automaticamente após (dias):")
        self.days_spin = QSpinBox()
        self.days_spin.setRange(1, 365)
        self.days_spin.setValue(history_settings.get_retention_days())
        self.days_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self.days_spin.setFixedWidth(80)
        days_layout.addWidget(days_label)
        days_layout.addWidget(self.days_spin)
        days_layout.addStretch(1)
        hist_layout.addLayout(days_layout)
        
        # Row 3: Manage variables
        vars_layout = QHBoxLayout()
        vars_label = QLabel("Variáveis (Snippets):")
        self.manage_vars_btn = QPushButton("Gerenciar Variáveis")
        self.manage_vars_btn.clicked.connect(self.open_variables_manager)
        vars_layout.addWidget(vars_label)
        vars_layout.addWidget(self.manage_vars_btn)
        vars_layout.addStretch(1)
        hist_layout.addLayout(vars_layout)

        layout.addWidget(hist_card)

        # 3. Dados Section Card
        data_card = QFrame()
        data_card.setObjectName("DataCard")
        data_card.setFrameShape(QFrame.Shape.NoFrame)
        data_card.setStyleSheet("QFrame#DataCard { background-color: rgba(45, 45, 45, 0.3); border: 1px solid rgba(80, 80, 80, 0.2); border-radius: 12px; }")
        
        data_layout = QVBoxLayout(data_card)
        data_layout.setContentsMargins(14, 14, 14, 14)
        data_layout.setSpacing(12)
        
        data_header = QLabel("Dados")
        data_header.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {accent_color};")
        data_layout.addWidget(data_header)
        
        # Row 1: Database folder path
        db_path_layout = QVBoxLayout()
        db_label = QLabel("Pasta do Banco de Dados:")
        db_input_layout = QHBoxLayout()
        self.db_input = QLineEdit()
        self.db_input.setText(data_settings.get_db_path())
        self.db_input.setReadOnly(True)
        db_browse_btn = QPushButton("Procurar...")
        db_browse_btn.clicked.connect(self.browse_db_path)
        db_input_layout.addWidget(self.db_input)
        db_input_layout.addWidget(db_browse_btn)
        db_path_layout.addWidget(db_label)
        db_path_layout.addLayout(db_input_layout)
        data_layout.addLayout(db_path_layout)
        
        # Row 2: Backup actions
        actions_layout = QHBoxLayout()
        self.export_btn = QPushButton("Exportar Bkp")
        self.export_btn.clicked.connect(self.export_backup)
        self.import_btn = QPushButton("Importar Bkp")
        self.import_btn.clicked.connect(self.import_backup)
        actions_layout.addWidget(self.export_btn)
        actions_layout.addWidget(self.import_btn)
        actions_layout.addStretch(1)
        data_layout.addLayout(actions_layout)
        
        # Spacer
        data_layout.addSpacing(12)
        
        # Row 3: Limpar Tudo (Centered and last in the section)
        clear_layout = QHBoxLayout()
        self.clear_db_btn = QPushButton("Limpar Tudo")
        self.clear_db_btn.setStyleSheet("background-color: #5c1d1d; border: 1px solid #7d2626; padding: 8px 24px;")
        self.clear_db_btn.clicked.connect(self.clear_database_action)
        
        clear_layout.addStretch(1)
        clear_layout.addWidget(self.clear_db_btn)
        clear_layout.addStretch(1)
        data_layout.addLayout(clear_layout)

        layout.addWidget(data_card)

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area)

        # Tip label
        info = QLabel("Dica: Itens fixados (★) nunca são excluídos automaticamente.")
        info.setStyleSheet("color: #a1a1a1; font-style: italic; margin-left: 5px;")
        main_layout.addWidget(info)

        # Save/Cancel bottom button layout
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(5, 5, 5, 5)
        btn_layout.addStretch(1)
        
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.clicked.connect(self.cancel_settings)
        
        save_btn = QPushButton("Salvar Configurações")
        save_btn.setObjectName("saveButton")
        save_btn.clicked.connect(self.save_settings)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    def browse_db_path(self):
        # Workaround for Wayland: Hide parent stays-on-top window
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
        db_path = self.db_input.text()
        if not os.path.exists(db_path):
            CustomModal.show_message(self, "Erro", "A pasta selecionada para o banco de dados não existe.")
            return

        # Prepare settings dictionary for batch save
        new_settings = {
            'max_history': self.hist_spin.value(),
            'retention_days': self.days_spin.value(),
            'db_path': db_path,
            'interaction_mode': self.mode_group.checkedId()
        }
        
        selected_theme_btn = self.theme_btn_group.checkedButton()
        if selected_theme_btn:
            new_settings['theme_color'] = selected_theme_btn.property("theme_hex")
            
        # No linux (wayland) não tentamos salvar o hotkey do campo read-only
        if not (sys.platform.startswith('linux') and os.environ.get('WAYLAND_DISPLAY')):
            if hasattr(self.hotkey_input, 'raw_hotkey'):
                new_settings['hotkey'] = self.hotkey_input.raw_hotkey
            if sys.platform == "darwin" and hasattr(self.hotkey_input, 'native_mac_key_code'):
                new_settings['hotkey_mac_key_code'] = self.hotkey_input.native_mac_key_code

        # Batch save
        settings.update_settings(new_settings)

        # Configurar Autostart (Iniciar com o sistema)
        from core import general_settings
        general_settings.set_autostart_enabled(self.autostart_switch.isChecked())
            
        from configs.config import UI_COLORS
        from PyQt6.QtWidgets import QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("FastPaste")
        dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        dialog.setFixedWidth(480)
        dialog.setStyleSheet(f"""
            QDialog {{ background-color: {UI_COLORS.get('card_bg', '#242424')}; border: 1px solid {UI_COLORS.get('card_border', '#3c3c3c')}; border-radius: 8px; }}
            QLabel {{ color: {UI_COLORS.get('fg', '#ffffff')}; font-size: 14px; }}
            QPushButton {{ background-color: #3a3a3a; color: #ffffff; padding: 8px 16px; border-radius: 4px; border: 1px solid #5a5a5a; font-size: 13px; }}
            QPushButton:hover {{ background-color: #4a4a4a; }}
            QPushButton#primary {{ background-color: {UI_COLORS.get('selected', '#FF7A00')}; border: none; font-weight: bold; }}
            QPushButton#primary:hover {{ opacity: 0.8; }}
        """)
        
        d_layout = QVBoxLayout(dialog)
        d_layout.setContentsMargins(20, 24, 20, 20)
        d_layout.setSpacing(20)
        
        msg_label = QLabel("Configurações salvas com sucesso!\n\nPara aplicar o novo Tema em toda a interface, o aplicativo precisa ser reiniciado.")
        msg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        d_layout.addWidget(msg_label)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        
        btn_later = QPushButton("Mais Tarde")
        btn_later.clicked.connect(dialog.reject)
        
        btn_restart = QPushButton("Reiniciar Agora")
        btn_restart.setObjectName("primary")
        btn_restart.clicked.connect(dialog.accept)
        
        btn_layout.addWidget(btn_later)
        btn_layout.addWidget(btn_restart)
        d_layout.addLayout(btn_layout)
        
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            import subprocess
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "show"]
            else:
                cmd = [sys.executable, sys.argv[0], "show"]
            subprocess.Popen(cmd)
            os._exit(0)
        else:
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
                    CustomModal.show_message(self, "Atalhos no Linux", 
                        f"No Linux, configure um atalho global nas configurações de teclado do seu sistema para executar o comando:\n\n{APP_NAME.lower()} show")
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.keyboard?shortcuts"])
            elif sys.platform.startswith("win32") or sys.platform.startswith("win"):
                os.system("start ms-settings:keyboard")
        except Exception as e:
            print(f"[{APP_NAME}] Error opening system keyboard settings: {e}")

    def open_variables_manager(self):
        from screens.variables_ui import VariablesManagerDialog
        dialog = VariablesManagerDialog(self)
        dialog.exec()

    def clear_database_action(self):
        confirmed = CustomModal.confirm(
            self, 
            "Limpar Tudo", 
            "Atenção: Isso apagará TODOS os dados permanentemente (histórico, itens fixados, imagens, variáveis e redefinirá as configurações para o padrão).\n\nDeseja continuar?"
        )
        if confirmed:
            from core import data_settings
            data_settings.clear_all_data()
            CustomModal.show_message(self, APP_NAME, "Todos os dados foram excluídos e as configurações voltaram ao padrão!\nO aplicativo será reiniciado.")
            
            import subprocess
            if getattr(sys, 'frozen', False):
                cmd = [sys.executable, "show"]
            else:
                cmd = [sys.executable, sys.argv[0], "show"]
            subprocess.Popen(cmd)
            os._exit(0)

    def export_backup(self):
        from PyQt6.QtWidgets import QFileDialog
        from core import data_settings
        
        password, ok = CustomModal.get_text(self, "Exportar Backup", "Digite uma senha para proteger o backup (mínimo 6 caracteres):", is_password=True)
        if not ok:
            return
            
        if len(password) < 6:
            CustomModal.show_message(self, APP_NAME, "A senha deve ter pelo menos 6 caracteres.")
            return
            
        import datetime
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        default_filename = f"{APP_NAME.lower().replace(' ', '_')}_backup_{date_str}.zip"
        
        filepath, _ = QFileDialog.getSaveFileName(self, "Salvar Backup", default_filename, f"{APP_NAME} Backup (*.zip)")
        if filepath:
            try:
                data_settings.export_backup_zip(filepath, password)
                CustomModal.show_message(self, APP_NAME, "Backup exportado com sucesso e protegido com senha!")
            except Exception as e:
                CustomModal.show_message(self, APP_NAME, f"Falha ao exportar backup: {e}")

    def import_backup(self):
        from PyQt6.QtWidgets import QFileDialog
        from core import data_settings
        
        filepath, _ = QFileDialog.getOpenFileName(self, "Selecionar Backup", "", f"{APP_NAME} Backup (*.zip)")
        if filepath:
            password, ok = CustomModal.get_text(self, "Importar Backup", "Digite a senha do arquivo de backup:", is_password=True)
            if not ok or not password:
                return
                
            success = data_settings.import_backup_zip(filepath, password)
            if success:
                CustomModal.show_message(self, APP_NAME, "Backup importado com sucesso!\nO aplicativo será reiniciado para aplicar as mudanças.")
                import subprocess
                if getattr(sys, 'frozen', False):
                    cmd = [sys.executable, "show"]
                else:
                    cmd = [sys.executable, sys.argv[0], "show"]
                subprocess.Popen(cmd)
                os._exit(0)
            else:
                CustomModal.show_message(self, APP_NAME, "Falha ao importar.\nVerifique se a senha está correta ou se o arquivo está corrompido.")
