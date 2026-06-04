from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QListWidget, QListWidgetItem, QLineEdit, QWidget, QCheckBox)
from PyQt6.QtCore import Qt
from configs.config import UI_COLORS
from core.variables import load_variables, add_variable, remove_variable

class VariablesManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gerenciar Variáveis")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(500)
        
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
            QCheckBox {{ color: #ffffff; font-size: 13px; background: transparent; }}
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
        
        # Lista
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_selection)
        layout.addWidget(self.list_widget)
        
        # Campos de Add
        add_layout = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome (ex: cpf)")
        self.name_input.setFixedWidth(100)
        
        self.val_input = QLineEdit()
        self.val_input.setPlaceholderText("Conteúdo...")
        
        self.secret_cb = QCheckBox("Secreta")
        
        self.add_btn = QPushButton("Adicionar")
        self.add_btn.setObjectName("primary")
        self.add_btn.clicked.connect(self.add_var)
        
        add_layout.addWidget(self.name_input)
        add_layout.addWidget(self.val_input)
        add_layout.addWidget(self.secret_cb)
        add_layout.addWidget(self.add_btn)
        
        layout.addLayout(add_layout)
        
        # Botões Rodapé
        btn_layout = QHBoxLayout()
        self.remove_btn = QPushButton("Remover Selecionada")
        self.remove_btn.setObjectName("danger")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_var)
        
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addStretch(1)
        
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
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
