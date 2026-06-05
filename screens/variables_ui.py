from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit, QWidget, QCheckBox, QFrame)
from PyQt6.QtCore import Qt
from configs.config import UI_COLORS, DEFAULT_SETTINGS
from configs.settings_manager import settings
from core.variables import load_variables, add_variable, remove_variable

class VariablesManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar Variáveis")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        w = settings.get("window_width", DEFAULT_SETTINGS["window_width"])
        h = settings.get("window_height", DEFAULT_SETTINGS["window_height"])
        self.setFixedSize(w, h)
        if parent:
            self.move(parent.window().geometry().topLeft())
        
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
            QPushButton#danger {{ background-color: #d32f2f; border: none; font-weight: bold; }}
            QPushButton#danger:hover {{ opacity: 0.8; }}
            QListWidget {{
                background-color: #1a1a1a; border: 1px solid #444; border-radius: 6px;
                color: #ffffff; outline: none; padding: 4px;
            }}
            QListWidget::item {{ padding: 8px; border-bottom: 1px solid #333; }}
            QListWidget::item:selected {{ background-color: {UI_COLORS.get('selected', '#FF7A00')}; color: white; border-radius: 4px; }}
            QLineEdit {{
                background-color: rgba(20, 20, 20, 0.6); border: 1px solid #444;
                border-radius: 6px; padding: 8px; color: #ffffff; font-size: 14px;
                selection-background-color: {UI_COLORS.get('selected', '#FF7A00')};
            }}
            QLineEdit:focus {{ border: 1px solid {UI_COLORS.get('selected', '#FF7A00')}; }}
            QCheckBox {{
                color: #ffffff;
                font-size: 13px;
                background: transparent;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid rgba(255, 255, 255, 0.4);
                border-radius: 4px;
                background-color: transparent;
            }}
            QCheckBox::indicator:hover {{
                border-color: rgba(255, 255, 255, 0.8);
            }}
            QCheckBox::indicator:checked {{
                background-color: {UI_COLORS.get('selected', '#FF7A00')};
                border: 2px solid {UI_COLORS.get('selected', '#FF7A00')};
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLXdpZHRoPSIzLjUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiLz48L3N2Zz4=);
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        
        title_label = QLabel("Variáveis (Snippets)")
        title_label.setObjectName("Title")
        layout.addWidget(title_label)
        
        desc = QLabel("Use variáveis para salvar textos longos ou frequentes. Digite '/' na barra de busca para usá-las.")
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #a1a1a1; font-size: 12px;")
        layout.addWidget(desc)
        
        # Spacer
        layout.addSpacing(4)
        
        # Card de Variáveis (seção para criar variáveis)
        vars_card = QFrame()
        vars_card.setObjectName("VarsCard")
        vars_card.setFrameShape(QFrame.Shape.NoFrame)
        vars_card.setStyleSheet("QFrame#VarsCard { background-color: rgba(45, 45, 45, 0.3); border: 1px solid rgba(80, 80, 80, 0.2); border-radius: 12px; }")
        
        vars_layout = QVBoxLayout(vars_card)
        vars_layout.setContentsMargins(14, 14, 14, 14)
        vars_layout.setSpacing(12)
        
        accent_color = UI_COLORS.get('selected', '#FF7A00')
        card_header = QLabel("Criar Variável")
        card_header.setStyleSheet(f"font-weight: bold; font-size: 14px; color: {accent_color};")
        vars_layout.addWidget(card_header)
        
        # Seção de Adicionar Variável (dentro do card) - Estrutura Vertical Espaçosa
        add_layout = QVBoxLayout()
        add_layout.setSpacing(10)
        
        # Linha 1: Nome da Variável
        name_row = QHBoxLayout()
        name_label = QLabel("Nome (ex: cpf):")
        name_label.setStyleSheet("font-size: 13px; color: #dfdfdf;")
        name_label.setFixedWidth(120)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Digite o atalho...")
        name_row.addWidget(name_label)
        name_row.addWidget(self.name_input)
        
        # Linha 2: Conteúdo da Variável
        val_row = QHBoxLayout()
        val_label = QLabel("Conteúdo:")
        val_label.setStyleSheet("font-size: 13px; color: #dfdfdf;")
        val_label.setFixedWidth(120)
        self.val_input = QLineEdit()
        self.val_input.setPlaceholderText("Digite o texto de substituição...")
        val_row.addWidget(val_label)
        val_row.addWidget(self.val_input)
        
        # Linha 3: Checkbox Secreta e Botão Adicionar
        bottom_row = QHBoxLayout()
        self.secret_cb = QCheckBox("Secreta (ocultar conteúdo)")
        
        self.add_btn = QPushButton("Adicionar")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_var)
        self.add_btn.setMinimumWidth(120)
        
        bottom_row.addWidget(self.secret_cb)
        bottom_row.addStretch(1)
        bottom_row.addWidget(self.add_btn)
        
        add_layout.addLayout(name_row)
        add_layout.addLayout(val_row)
        add_layout.addLayout(bottom_row)
        
        vars_layout.addLayout(add_layout)
        
        layout.addWidget(vars_card)
        
        # Spacer
        layout.addSpacing(6)
        
        # Título da Lista (fora do card)
        list_header = QLabel("Variáveis Cadastradas:")
        list_header.setStyleSheet("font-weight: bold; font-size: 13px; color: #a1a1a1;")
        layout.addWidget(list_header)
        
        # Lista (fora do card, embaixo)
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_selection)
        layout.addWidget(self.list_widget)
        
        # Botões Rodapé
        btn_layout = QHBoxLayout()
        self.remove_btn = QPushButton("Remover Selecionada")
        self.remove_btn.setObjectName("danger")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_var)
        
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch(1)
        
        back_btn = QPushButton("Voltar")
        back_btn.clicked.connect(self.accept)
        btn_layout.addWidget(back_btn)
        
        layout.addLayout(btn_layout)
        
        self.refresh_list()
        
    def refresh_list(self):
        self.list_widget.clear()
        vars_dict = load_variables()
        for k, v in vars_dict.items():
            val_str = v.get("value", "")
            if v.get("is_secret"):
                val_str = "********"
            item = QListWidgetItem(f"/{k}  →  {val_str}")
            item.setData(Qt.ItemDataRole.UserRole, k)
            self.list_widget.addItem(item)
            
    def on_selection(self):
        self.remove_btn.setEnabled(bool(self.list_widget.selectedItems()))
        
    def add_var(self):
        name = self.name_input.text().strip()
        val = self.val_input.text().strip()
        if not name or not val:
            return
        add_variable(name, val, is_secret=self.secret_cb.isChecked())
        self.name_input.clear()
        self.val_input.clear()
        self.secret_cb.setChecked(False)
        self.refresh_list()
        
    def remove_var(self):
        sel = self.list_widget.selectedItems()
        if not sel: return
        name = sel[0].data(Qt.ItemDataRole.UserRole)
        remove_variable(name)
        self.refresh_list()
