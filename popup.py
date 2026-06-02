import os
import sys
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QListWidget, QListWidgetItem, QLabel, 
    QMenu, QGraphicsDropShadowEffect, QFrame, QPushButton
)
from PyQt6.QtCore import Qt, QSize, QEvent, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QColor, QKeySequence, QShortcut

import history
from config import UI_COLORS, APP_NAME
from platform_handler import InputSimulator

def get_tinted_icon(icon_name, color_hex):
    from PyQt6.QtGui import QPainter
    
    icon = QIcon.fromTheme(icon_name)
    if icon.isNull():
        icon = QIcon.fromTheme(icon_name.replace("-symbolic", ""))
        
    if icon.isNull():
        return None
        
    pixmap = icon.pixmap(16, 16)
    
    # Tint symbolic icons so they are visible on dark themes
    if "-symbolic" in icon_name or "-symbolic" not in icon_name:
        tinted = QPixmap(pixmap.size())
        tinted.fill(Qt.GlobalColor.transparent)
        painter = QPainter(tinted)
        painter.drawPixmap(0, 0, pixmap)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(tinted.rect(), QColor(color_hex))
        painter.end()
        return tinted
        
    return pixmap

class FastPastePopup(QWidget):
    def __init__(self, standalone=True):
        super().__init__()
        self.standalone = standalone
        self.input_sim = InputSimulator()

        # Configurações da Janela
        self.setWindowTitle(APP_NAME)
        self.resize(600, 550)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.full_history = history.load_history()
        self.filtered_history = list(self.full_history)

        self.init_ui()
        self.apply_styles()
        
        # Shortcuts
        QShortcut(QKeySequence("Esc"), self, self.close_app)
        QShortcut(QKeySequence("Del"), self, self.delete_selected)
        QShortcut(QKeySequence("Ctrl+F"), self, self.search_entry.setFocus)
        QShortcut(QKeySequence("Ctrl+P"), self, self.toggle_pin_selected)
        
        for i in range(1, 10):
            QShortcut(QKeySequence(f"Ctrl+{i}"), self, lambda checked=False, idx=i-1: self.paste_by_index(idx))

        self.populate_list()

    def init_ui(self):
        # Aumentar o delay e estilo da tooltip globalmente
        QApplication.instance().setStyleSheet("QToolTip { color: #ffffff; background-color: #2a2a2a; border: 1px solid #4a4a4a; border-radius: 4px; padding: 4px; font-size: 13px; }")
        # Layout Principal da Janela
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)

        # Main Container (Substitui o main_box do GTK3)
        self.container = QFrame()
        self.container.setObjectName("MainContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(10)
        main_layout.addWidget(self.container)

        # Sombra idêntica ao GTK3
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        # Search Card
        self.search_card = QFrame()
        self.search_card.setObjectName("SearchCard")
        search_layout = QHBoxLayout(self.search_card)
        search_layout.setContentsMargins(12, 6, 12, 6)
        search_layout.setSpacing(10)
        
        search_icon = QLabel()
        pixmap = get_tinted_icon("system-search-symbolic", UI_COLORS['fg_dim'])
        
        if pixmap:
            search_icon.setPixmap(pixmap)
        else:
            search_icon.setText("🔍")
            search_icon.setStyleSheet(f"color: {UI_COLORS['fg_dim']}; font-size: 16px; background: transparent;")
        
        search_layout.addWidget(search_icon)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search clips or dates...")
        self.search_entry.setObjectName("SearchEntry")
        self.search_entry.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_entry)
        
        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedSize(30, 30)
        self.settings_btn.setToolTip("Configurações")
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: None;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }
        """)
        self.settings_btn.clicked.connect(self.open_settings)
        search_layout.addWidget(self.settings_btn)
        
        container_layout.addWidget(self.search_card)

        # List Card
        self.list_card = QFrame()
        self.list_card.setObjectName("ListCard")
        list_layout = QVBoxLayout(self.list_card)
        list_layout.setContentsMargins(0, 4, 0, 4)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ListWidget")
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemActivated.connect(self.on_item_activated)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        
        list_layout.addWidget(self.list_widget)
        container_layout.addWidget(self.list_card)

    def apply_styles(self):
        css = f"""
            #MainContainer {{
                background-color: {UI_COLORS['card_bg']};
                border-radius: 16px;
                border: 1px solid {UI_COLORS['card_border']};
            }}
            #SearchCard {{
                background-color: rgba(45, 45, 45, 0.6);
                border-radius: 10px;
                border: 1px solid rgba(80, 80, 80, 0.4);
            }}
            #SearchEntry {{
                background-color: transparent;
                border: none;
                color: {UI_COLORS['fg']};
                font-size: 14px;
            }}
            #SearchEntry:focus {{
                outline: none;
            }}
            #ListCard {{
                background-color: rgba(28, 28, 28, 0.4);
                border-radius: 10px;
                border: 1px solid rgba(60, 60, 60, 0.3);
            }}
            #ListWidget {{
                background-color: transparent;
                border: none;
                outline: 0;
            }}
            #ListWidget::item {{
                background-color: transparent;
                border-radius: 8px;
                margin: 2px 6px;
                border: none;
            }}
            #ListWidget::item:hover {{
                background-color: transparent;
            }}
            #ListWidget::item:selected {{
                background-color: transparent;
            }}
        """
        self.setStyleSheet(css)

    def populate_list(self):
        self.list_widget.clear()

        if not self.filtered_history:
            item = QListWidgetItem("No clips found.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.list_widget.addItem(item)
            return

        for idx, item_data in enumerate(self.filtered_history):
            widget = QWidget()
            widget.setObjectName("CardItem")
            h_layout = QHBoxLayout(widget)
            h_layout.setContentsMargins(12, 12, 12, 12)
            h_layout.setSpacing(12)

            # Left icon/image
            icon_label = QLabel()
            if item_data["type"] == "text":
                content_str = item_data["content"]
                
                # Use system icons like GTK did
                icon_name = "web-browser-symbolic" if content_str.startswith(("http://", "https://", "www.")) else "text-x-generic-symbolic"
                pixmap = get_tinted_icon(icon_name, UI_COLORS['fg_dim'])
                
                if pixmap:
                    icon_label.setPixmap(pixmap)
                else:
                    icon_label.setText("🌐" if icon_name == "web-browser-symbolic" else "📄")
                    icon_label.setStyleSheet(f"font-size: 16px; color: {UI_COLORS['fg_dim']}; background: transparent;")
                
                preview = content_str.replace('\n', '  ')
                if len(preview) > 50:
                    preview = preview[:47] + "..."
                
                widget.setToolTip(content_str[:1000]) # Mostra até 1000 chars no hover
                    
                text_label = QLabel(preview)
                text_label.setObjectName("ItemLabel")
                
                h_layout.addWidget(icon_label)
                h_layout.addWidget(text_label, stretch=1)
                
            elif item_data["type"] == "image":
                filepath = item_data["content"]
                pixmap = QPixmap(filepath)
                if not pixmap.isNull():
                    # Escala e recorta para um tamanho estático padrão (ex: 80x45)
                    pixmap = pixmap.scaled(80, 45, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                    
                    # Cria um pixmap recortado exato
                    crop = QPixmap(80, 45)
                    crop.fill(Qt.GlobalColor.transparent)
                    from PyQt6.QtGui import QPainter
                    painter = QPainter(crop)
                    # Centraliza o crop
                    x = (pixmap.width() - 80) // 2
                    y = (pixmap.height() - 45) // 2
                    painter.drawPixmap(0, 0, pixmap, x, y, 80, 45)
                    painter.end()
                    
                    icon_label.setPixmap(crop)
                    icon_label.setFixedSize(80, 45)
                
                # Ditto-style hover preview for images via HTML tooltip!
                widget.setToolTip(f'<img src="{filepath}" width="300">')
                
                text_label = QLabel("[Imagem PNG]")
                text_label.setObjectName("ItemLabelDim")
                
                h_layout.addWidget(icon_label)
                h_layout.addWidget(text_label, stretch=1)

            # Right badges
            right_widget = QWidget()
            r_layout = QHBoxLayout(right_widget)
            r_layout.setContentsMargins(0, 0, 0, 0)
            r_layout.setSpacing(8)


            if item_data["is_pinned"]:
                pin = QLabel("📌")
                pin.setStyleSheet("background: transparent; font-size: 12px;")
                r_layout.addWidget(pin)
                
            dt = datetime.datetime.fromtimestamp(item_data["created_at"])
            time_lbl = QLabel(dt.strftime("%H:%M"))
            time_lbl.setObjectName("TimestampLabel")
            r_layout.addWidget(time_lbl)

            h_layout.addWidget(right_widget)

            # Define specific CSS for this widget to match GTK3 hover/select logic
            # PyQt6 supports dynamic properties or just relying on QListWidget state
            # but setting it dynamically on the widget is cleaner for complex children
            widget.setStyleSheet(f"""
                #CardItem {{
                    background-color: transparent;
                    border-radius: 8px;
                }}
                #ItemLabel {{
                    color: {UI_COLORS['fg']}; 
                    font-weight: 500; 
                    font-size: 13.5px; 
                    background: transparent;
                }}
                #ItemLabelDim {{
                    color: {UI_COLORS['fg_dim']}; 
                    font-weight: 500; 
                    font-size: 13.5px; 
                    background: transparent;
                }}
                #TimestampLabel {{
                    color: {UI_COLORS['fg_dim']}; 
                    font-size: 11px; 
                    background: transparent;
                }}
            """)

            list_item = QListWidgetItem(self.list_widget)
            list_item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(list_item)
            self.list_widget.setItemWidget(list_item, widget)
            
            list_item.setData(Qt.ItemDataRole.UserRole, item_data)
            
        self.list_widget.setCurrentRow(-1)
        self.search_entry.setFocus()
        self.list_widget.itemSelectionChanged.connect(self.update_selection_style)

    def update_selection_style(self):
        # We manually update the background color of the selected widget
        # to match the GTK3 transparent outer row / colored inner box behavior
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            widget = self.list_widget.itemWidget(item)
            if not widget:
                continue
                
            if item.isSelected():
                widget.setStyleSheet(f"""
                    #CardItem {{
                        background-color: {UI_COLORS['selected']};
                        border-radius: 8px;
                    }}
                    #ItemLabel, #ItemLabelDim {{
                        color: #ffffff; 
                        font-weight: 500; 
                        font-size: 13.5px; 
                        background: transparent;
                    }}
                    #TimestampLabel {{
                        color: rgba(255, 255, 255, 0.8); 
                        font-size: 11px; 
                        background: transparent;
                    }}
                """)
            else:
                widget.setStyleSheet(f"""
                    #CardItem {{
                        background-color: transparent;
                        border-radius: 8px;
                    }}
                    #CardItem:hover {{
                        background-color: {UI_COLORS['hover']};
                    }}
                    #ItemLabel {{
                        color: {UI_COLORS['fg']}; 
                        font-weight: 500; 
                        font-size: 13.5px; 
                        background: transparent;
                    }}
                    #ItemLabelDim {{
                        color: {UI_COLORS['fg_dim']}; 
                        font-weight: 500; 
                        font-size: 13.5px; 
                        background: transparent;
                    }}
                    #TimestampLabel {{
                        color: {UI_COLORS['fg_dim']}; 
                        font-size: 11px; 
                        background: transparent;
                    }}
                """)

    def on_search_changed(self, text):
        query = text.strip()
        if not query:
            self.full_history = history.load_history()
            self.filtered_history = list(self.full_history)
        else:
            self.filtered_history = history.load_history(query)
        self.populate_list()
        
    def open_settings(self):
        from settings_ui import SettingsDialog
        dialog = SettingsDialog(self)
        if dialog.exec():
            # If saved, force cleanup and refresh
            conn = history.get_connection()
            history.cleanup_history(conn)
            conn.close()
            
            # Re-read history since DB path might have changed
            self.full_history = history.load_history()
            self.filtered_history = list(self.full_history)
            
            self.refresh_list()

    def paste_by_index(self, idx):
        if 0 <= idx < len(self.filtered_history):
            self.paste_item(self.filtered_history[idx])

    def on_item_activated(self, item):
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if item_data:
            self.paste_item(item_data)

    def paste_item(self, item_data):
        import subprocess
        import shutil
        
        has_wl = shutil.which('wl-copy') is not None
        has_xclip = shutil.which('xclip') is not None
        
        if item_data["type"] == "text":
            text = item_data["content"]
            try:
                if has_wl:
                    proc = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE)
                    proc.communicate(text.encode('utf-8'))
                elif has_xclip:
                    proc = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
                    proc.communicate(text.encode('utf-8'))
                else:
                    QApplication.clipboard().setText(text)
                history.add_text(text)
            except Exception as e:
                print(f"[FastPaste] Erro ao copiar texto: {e}")
                
        elif item_data["type"] == "image":
            filepath = item_data["content"]
            try:
                with open(filepath, 'rb') as f:
                    img_data = f.read()
                    
                if has_wl:
                    proc = subprocess.Popen(['wl-copy', '--type', 'image/png'], stdin=subprocess.PIPE)
                    proc.communicate(img_data)
                elif has_xclip:
                    proc = subprocess.Popen(['xclip', '-selection', 'clipboard', '-t', 'image/png'], stdin=subprocess.PIPE)
                    proc.communicate(img_data)
                else:
                    img = QPixmap(filepath).toImage()
                    QApplication.clipboard().setImage(img)
                    
                history.add_image(img_data)
            except Exception as e:
                print(f"[FastPaste] Erro ao copiar imagem: {e}")
        
        self.close_app(simulate_paste=True)

    def show_context_menu(self, pos):
        item = self.list_widget.itemAt(pos)
        if not item: return
        
        idx = self.list_widget.row(item)
        if 0 <= idx < len(self.filtered_history):
            item_data = self.filtered_history[idx]
            
            menu = QMenu(self)
            menu.setStyleSheet(f"""
                QMenu {{
                    background-color: {UI_COLORS['card_bg']};
                    color: {UI_COLORS['fg']};
                    border: 1px solid {UI_COLORS['card_border']};
                    border-radius: 4px;
                    padding: 4px;
                }}
                QMenu::item {{
                    padding: 6px 24px 6px 8px;
                    border-radius: 4px;
                }}
                QMenu::item:selected {{
                    background-color: {UI_COLORS['hover']};
                }}
            """)
            
            is_pinned = item_data.get("is_pinned")
            pin_text = "Desafixar" if is_pinned else "Fixar"
            pin_pixmap = get_tinted_icon("emblem-favorite-symbolic" if is_pinned else "bookmark-new-symbolic", UI_COLORS['fg_dim'])
            pin_action = menu.addAction(QIcon(pin_pixmap) if pin_pixmap else QIcon(), pin_text)
            
            del_pixmap = get_tinted_icon("edit-delete-symbolic", UI_COLORS['fg_dim'])
            if not del_pixmap:
                del_pixmap = get_tinted_icon("user-trash-symbolic", UI_COLORS['fg_dim'])
            delete_action = menu.addAction(QIcon(del_pixmap) if del_pixmap else QIcon(), "Remover")
            
            menu.addSeparator()
            clear_pixmap = get_tinted_icon("edit-clear-all-symbolic", UI_COLORS['fg_dim'])
            clear_action = menu.addAction(QIcon(clear_pixmap) if clear_pixmap else QIcon(), "Limpar Histórico")
            
            action = menu.exec(self.list_widget.mapToGlobal(pos))
            if action == pin_action:
                history.toggle_pin(item_data["id"])
                self.refresh_list()
            elif action == delete_action:
                history.delete_item(item_data["id"])
                self.refresh_list()
            elif action == clear_action:
                history.clear()
                self.refresh_list()

    def toggle_pin_selected(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.filtered_history):
            history.toggle_pin(self.filtered_history[row]["id"])
            self.refresh_list()

    def delete_selected(self):
        row = self.list_widget.currentRow()
        if 0 <= row < len(self.filtered_history):
            history.delete_item(self.filtered_history[row]["id"])
            self.refresh_list()

    def refresh_list(self):
        self.on_search_changed(self.search_entry.text())

    def changeEvent(self, event):
        # Fechar a janela quando ela perder o foco completamente
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                self.close_app()
        super().changeEvent(event)

    def focusOutEvent(self, event):
        self.close_app()
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        key = event.key()
        
        # Seta para baixo / para cima
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            # Se a barra de pesquisa tem o foco, passa para a lista
            if self.search_entry.hasFocus():
                self.list_widget.setFocus()
                if self.list_widget.currentRow() < 0 and self.list_widget.count() > 0:
                    self.list_widget.setCurrentRow(0)
            super().keyPressEvent(event)
            return
            
        # Enter / Return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            row = self.list_widget.currentRow()
            if row >= 0:
                self.paste_by_index(row)
            elif self.list_widget.count() > 0:
                self.paste_by_index(0)
            return

        # Digitação vai direto para a barra de pesquisa
        if not self.search_entry.hasFocus() and len(event.text()) > 0 and event.text().isprintable():
            self.search_entry.setFocus()
            self.search_entry.insert(event.text())
            
        super().keyPressEvent(event)

    def close_app(self, simulate_paste=False):
        self.hide()
        if simulate_paste:
            self.input_sim.paste()
            
        if self.standalone:
            QApplication.quit()

def show(standalone=True):
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    window = FastPastePopup(standalone=standalone)
    window.show()
    
    # Force focus
    window.activateWindow()
    window.raise_()
    
    if standalone:
        sys.exit(app.exec())
    return window

if __name__ == "__main__":
    show(standalone=True)
