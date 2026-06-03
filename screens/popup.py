import os
import sys
import datetime
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLineEdit, QListWidget, QListWidgetItem, QLabel, 
    QMenu, QGraphicsDropShadowEffect, QFrame, QPushButton, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize, QEvent, QTimer, QMimeData, QUrl, QObject
from PyQt6.QtGui import QIcon, QPixmap, QColor, QKeySequence, QShortcut, QDrag, QPainter, QPen, QBrush, QImage
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from core import history
from configs.config import UI_COLORS, APP_NAME, hide_dock_icon
from configs.settings_manager import settings
from core.platform_handler import InputSimulator

class DragEventFilter(QObject):
    def __init__(self, list_widget):
        super().__init__(list_widget)
        self.list_widget = list_widget
        self.drag_start_pos = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.drag_start_pos = event.position().toPoint()
                
        elif event.type() == QEvent.Type.MouseMove:
            if event.buttons() == Qt.MouseButton.LeftButton and self.drag_start_pos is not None:
                dist = (event.position().toPoint() - self.drag_start_pos).manhattanLength()
                if dist >= QApplication.startDragDistance():
                    # Encontra o item da lista correspondente a este widget
                    for i in range(self.list_widget.count()):
                        item = self.list_widget.item(i)
                        if self.list_widget.itemWidget(item) == obj:
                            self.list_widget.setCurrentItem(item)
                            self.list_widget.startDrag(Qt.DropAction.CopyAction)
                            self.drag_start_pos = None
                            return True
                            
        elif event.type() == QEvent.Type.MouseButtonRelease:
            self.drag_start_pos = None
            
        return super().eventFilter(obj, event)

class DraggableListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragOnly)

    def supportedDropActions(self):
        return Qt.DropAction.CopyAction

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item:
            return
            
        item_data = item.data(Qt.ItemDataRole.UserRole)
        if not item_data:
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        
        if item_data.get("type") == "image":
            filepath = item_data.get("content")
            if filepath and os.path.exists(filepath):
                from core import history
                img_data = history.get_image_bytes(filepath)
                if img_data:
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    image = pixmap.toImage()
                    
                    # 1. URL de Arquivo Local Temporário (para Área de Trabalho / Gerenciadores de Arquivos)
                    try:
                        import tempfile
                        temp_dir = tempfile.gettempdir()
                        safe_title = f"fpaste_{os.path.basename(filepath)}"
                        temp_filepath = os.path.join(temp_dir, safe_title)
                        with open(temp_filepath, "wb") as f:
                            f.write(img_data)
                        mime_data.setUrls([QUrl.fromLocalFile(temp_filepath)])
                    except Exception as e:
                        print(f"[FPaste] Erro ao gerar arquivo de imagem temporário para drag-and-drop: {e}")
                    
                    # 2. Dados de Imagem (para WhatsApp, Discord, Slack, Photoshop, etc.)
                    if not image.isNull():
                        mime_data.setImageData(image)
                        mime_data.setData("image/png", img_data)
                    
                    # 3. Ícone Visual do Arraste
                    if not pixmap.isNull():
                        drag_pixmap = pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                        drag.setPixmap(drag_pixmap)
                        drag.setHotSpot(drag_pixmap.rect().center())
                    
                    drag.setMimeData(mime_data)
                    drag.exec(Qt.DropAction.CopyAction)
                
        elif item_data.get("type") == "text":
            text_content = item_data.get("content")
            if text_content:
                mime_data.setText(text_content)
                
                # Permite arrastar texto para a área de trabalho para criar um arquivo de texto
                try:
                    import tempfile
                    # Sanitiza os primeiros 20 caracteres para gerar um nome de arquivo seguro
                    safe_title = "".join([c for c in text_content[:20] if c.isalnum() or c in (' ', '_', '-')]).strip()
                    safe_title = safe_title.replace(" ", "_")
                    if not safe_title:
                        safe_title = "fpaste_text"
                    
                    temp_dir = tempfile.gettempdir()
                    temp_filepath = os.path.join(temp_dir, f"{safe_title}.txt")
                    with open(temp_filepath, "w", encoding="utf-8") as f:
                        f.write(text_content)
                    
                    mime_data.setUrls([QUrl.fromLocalFile(temp_filepath)])
                except Exception as e:
                    print(f"[FPaste] Erro ao gerar arquivo de texto temporário para drag-and-drop: {e}")
                
                # Ícone Visual do Arraste (pequeno card arredondado com preview de texto)
                pixmap = QPixmap(130, 32)
                pixmap.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(pixmap)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                # Rounded background card
                painter.setBrush(QColor(UI_COLORS.get('hover', '#323232')))
                painter.setPen(QColor(UI_COLORS.get('card_border', '#3c3c3c')))
                painter.drawRoundedRect(pixmap.rect().adjusted(1, 1, -1, -1), 6, 6)
                
                # Text preview
                painter.setPen(QColor(UI_COLORS.get('fg', '#ffffff')))
                display_text = text_content.replace("\n", " ").strip()
                if len(display_text) > 15:
                    display_text = display_text[:12] + "..."
                painter.drawText(pixmap.rect().adjusted(8, 4, -8, -4), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, display_text)
                painter.end()
                
                drag.setPixmap(pixmap)
                drag.setHotSpot(pixmap.rect().center())
                
                drag.setMimeData(mime_data)
                drag.exec(Qt.DropAction.CopyAction)

def draw_custom_search_icon(color_hex):
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color_hex), 2)
    painter.setPen(pen)
    painter.drawEllipse(2, 2, 9, 9)
    painter.drawLine(10, 10, 15, 15)
    painter.end()
    return pixmap

def draw_custom_gear_icon(color_hex):
    import math
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    pen = QPen(QColor(color_hex), 2)
    painter.setPen(pen)
    
    center_x = 9
    center_y = 9
    r_inner = 4
    r_outer = 6.5
    for i in range(8):
        angle = i * math.pi / 4
        x1 = center_x + r_inner * math.cos(angle)
        y1 = center_y + r_inner * math.sin(angle)
        x2 = center_x + r_outer * math.cos(angle)
        y2 = center_y + r_outer * math.sin(angle)
        painter.drawLine(int(x1), int(y1), int(x2), int(y2))
        
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(5, 5, 8, 8)
    
    painter.setBrush(QBrush(QColor(color_hex)))
    painter.drawEllipse(7, 7, 4, 4)
    painter.end()
    return pixmap

def get_tinted_icon(icon_name, color_hex):
    icon = QIcon.fromTheme(icon_name)
    if icon.isNull():
        icon = QIcon.fromTheme(icon_name.replace("-symbolic", ""))
        
    if icon.isNull():
        return None
        
    pixmap = icon.pixmap(16, 16)
    if pixmap.isNull() or pixmap.width() == 0 or pixmap.height() == 0:
        return None
        
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
        hide_dock_icon()
        self.standalone = standalone
        self.input_sim = InputSimulator()

        # Servidor de instância única para o popup standalone
        if self.standalone:
            self.setup_single_instance_server()

        # Configurações da Janela
        self.setWindowTitle(APP_NAME)
        self.resize(600, 550)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.full_history = history.load_history()
        self.filtered_history = list(self.full_history)

        self.init_ui()
        self.apply_styles()
        
        # Shortcuts
        self.shortcuts_list = []
        self.shortcuts_list.append(QShortcut(QKeySequence("Esc"), self, self.close_app))
        self.shortcuts_list.append(QShortcut(QKeySequence("Del"), self, self.delete_selected))
        self.shortcuts_list.append(QShortcut(QKeySequence("Ctrl+F"), self, self.search_entry.setFocus))
        self.shortcuts_list.append(QShortcut(QKeySequence("Ctrl+P"), self, self.toggle_pin_selected))
        
        for i in range(1, 10):
            self.shortcuts_list.append(QShortcut(QKeySequence(f"Ctrl+{i}"), self, lambda checked=False, idx=i-1: self.paste_by_index(idx)))

        self.populate_list()
        self.setup_interaction_mode()

    def setup_single_instance_server(self):
        self.popup_server_name = f"{APP_NAME}_Popup_Server"
        self.popup_server = QLocalServer(self)
        QLocalServer.removeServer(self.popup_server_name)
        self.popup_server.newConnection.connect(self.on_new_popup_connection)
        self.popup_server.listen(self.popup_server_name)

    def on_new_popup_connection(self):
        socket = self.popup_server.nextPendingConnection()
        if socket.waitForReadyRead(1000):
            data = socket.readAll().data()
            if b"CLOSE" in data:
                if self.stacked_widget.currentIndex() == 1:
                    # Se estiver na página de configurações, proíbe fechar a janela
                    # e apenas traz ela para o foco.
                    self.activateWindow()
                    self.raise_()
                else:
                    self.close_app()
        socket.disconnectFromServer()
        socket.deleteLater()

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
        
        self.stacked_widget = QStackedWidget()
        container_layout.addWidget(self.stacked_widget)
        
        self.main_page = QWidget()
        main_page_layout = QVBoxLayout(self.main_page)
        main_page_layout.setContentsMargins(0, 0, 0, 0)
        main_page_layout.setSpacing(10)
        
        self.stacked_widget.addWidget(self.main_page)

        # Header Container at the top of the main page
        self.header_container = QFrame()
        self.header_container.setObjectName("HeaderContainer")
        header_layout = QHBoxLayout(self.header_container)
        header_layout.setContentsMargins(6, 0, 6, 0)
        header_layout.setSpacing(8)
        
        # Name of the application
        self.app_title = QLabel(APP_NAME)
        self.app_title.setObjectName("AppTitle")
        header_layout.addWidget(self.app_title)
        
        header_layout.addStretch(1)
        
        # Mode Toggle Button
        self.header_mode_btn = QPushButton()
        self.header_mode_btn.setObjectName("HeaderModeBtn")
        self.header_mode_btn.setFlat(True)
        self.header_mode_btn.clicked.connect(self.toggle_interaction_mode)
        header_layout.addWidget(self.header_mode_btn)
        
        # Settings Button on the far right
        self.settings_btn = QPushButton()
        self.settings_btn.setObjectName("SettingsBtn")
        self.settings_btn.setFixedSize(24, 24)
        self.settings_btn.setFlat(True)
        self.settings_btn.setToolTip("Configurações")
        
        is_linux = sys.platform.startswith("linux")
        if is_linux:
            settings_pixmap = get_tinted_icon("preferences-system-symbolic", UI_COLORS['fg_dim'])
        else:
            settings_pixmap = draw_custom_gear_icon(UI_COLORS['fg_dim'])
            
        if settings_pixmap:
            self.settings_btn.setIcon(QIcon(settings_pixmap))
            self.settings_btn.setIconSize(QSize(16, 16))
        else:
            self.settings_btn.setText("⚙")
            self.settings_btn.setStyleSheet("QPushButton { font-size: 16px; color: " + UI_COLORS['fg_dim'] + "; }")
            
        self.settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(self.settings_btn)
        
        main_page_layout.addWidget(self.header_container)

        # Search Card
        self.search_card = QFrame()
        self.search_card.setObjectName("SearchCard")
        search_layout = QHBoxLayout(self.search_card)
        search_layout.setContentsMargins(12, 6, 12, 6)
        search_layout.setSpacing(10)
        
        is_linux = sys.platform.startswith("linux")
        
        search_icon = QLabel()
        if is_linux:
            pixmap = get_tinted_icon("system-search-symbolic", UI_COLORS['fg_dim'])
        else:
            pixmap = draw_custom_search_icon(UI_COLORS['fg_dim'])
        
        if pixmap:
            search_icon.setPixmap(pixmap)
        else:
            search_icon.setText("🔍")
            search_icon.setStyleSheet(f"color: {UI_COLORS['fg_dim']}; font-size: 16px; background: transparent;")
        
        search_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        search_layout.addWidget(search_icon)

        self.search_entry = QLineEdit()
        self.search_entry.setPlaceholderText("Search clips or dates...")
        self.search_entry.setObjectName("SearchEntry")
        if not is_linux:
            self.search_entry.setAttribute(Qt.WidgetAttribute.WA_MacShowFocusRect, False)
        self.search_entry.textChanged.connect(self.on_search_changed)
        search_layout.addWidget(self.search_entry)
        
        main_page_layout.addWidget(self.search_card)

        # List Card
        self.list_card = QFrame()
        self.list_card.setObjectName("ListCard")
        list_layout = QVBoxLayout(self.list_card)
        list_layout.setContentsMargins(0, 4, 0, 4)

        self.list_widget = DraggableListWidget()
        self.drag_filter = DragEventFilter(self.list_widget)
        self.list_widget.setObjectName("ListWidget")
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.itemDoubleClicked.connect(self.on_item_activated)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self.show_context_menu)
        self.list_widget.itemSelectionChanged.connect(self.update_selection_style)
        
        list_layout.addWidget(self.list_widget)
        main_page_layout.addWidget(self.list_card)
        
        # Settings Page
        from screens.settings_ui import SettingsWidget
        self.settings_page = SettingsWidget(self)
        self.settings_page.settings_closed.connect(self.close_settings)
        self.stacked_widget.addWidget(self.settings_page)

    def apply_styles(self):
        mode = settings.get('interaction_mode', 1)
        popup_border_color = UI_COLORS['card_border']
        
        # Mode button highlight based on active mode
        if mode == 2:
            mode_border = f"1px solid {UI_COLORS['selected']}"
            mode_color = UI_COLORS['selected']
            mode_bg = "rgba(233, 84, 32, 0.05)"
        else:
            mode_border = "none"
            mode_color = UI_COLORS['fg_dim']
            mode_bg = "transparent"

        css = f"""
            #MainContainer {{
                background-color: {UI_COLORS['card_bg']};
                border-radius: 16px;
                border: 1px solid {popup_border_color};
            }}
            #HeaderContainer {{
                background-color: transparent;
                border: none;
            }}
            #AppTitle {{
                color: {UI_COLORS['fg']};
                font-size: 14px;
                font-weight: bold;
                background: transparent;
            }}
            #HeaderModeBtn {{
                background-color: {mode_bg};
                border: {mode_border};
                border-radius: 6px;
                color: {mode_color};
                font-size: 11px;
                padding: 4px 8px;
                text-align: center;
                font-weight: 500;
            }}
            #HeaderModeBtn:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {UI_COLORS['fg']};
            }}
            #SettingsBtn {{
                background-color: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
                border-radius: 4px;
            }}
            #SettingsBtn:hover {{
                background-color: rgba(255, 255, 255, 0.08);
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
                img_data = history.get_image_bytes(filepath)
                
                if img_data:
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    
                    if not pixmap.isNull():
                        # Create cropped pixmap
                        crop = QPixmap(80, 45)
                        crop.fill(Qt.GlobalColor.transparent)
                        from PyQt6.QtGui import QPainter
                        painter = QPainter(crop)
                        
                        # Scale down first
                        scaled_pixmap = pixmap.scaled(80, 45, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
                        x = (scaled_pixmap.width() - 80) // 2
                        y = (scaled_pixmap.height() - 45) // 2
                        painter.drawPixmap(0, 0, scaled_pixmap, x, y, 80, 45)
                        painter.end()
                        
                        icon_label.setPixmap(crop)
                        icon_label.setFixedSize(80, 45)
                    
                    import base64
                    b64_data = base64.b64encode(img_data).decode('utf-8')
                    widget.setToolTip(f'<img src="data:image/png;base64,{b64_data}" width="300">')
                
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
            widget.installEventFilter(self.drag_filter)
            
            list_item.setData(Qt.ItemDataRole.UserRole, item_data)
            
        self.list_widget.setCurrentRow(-1)
        self.search_entry.setFocus()

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
        
    def set_shortcuts_enabled(self, enabled):
        if hasattr(self, 'shortcuts_list'):
            for shortcut in self.shortcuts_list:
                shortcut.setEnabled(enabled)

    def open_settings(self):
        # Switch to settings page
        self.set_shortcuts_enabled(False)
        self.stacked_widget.setCurrentIndex(1)
        
    def close_settings(self, saved=False):
        # Switch back to main page
        self.stacked_widget.setCurrentIndex(0)
        self.set_shortcuts_enabled(True)
        self.search_entry.setFocus()
        
        if saved:
            conn = history.get_connection()
            history.cleanup_history(conn)
            conn.close()
            
            # Re-read history since DB path might have changed
            self.full_history = history.load_history()
            self.filtered_history = list(self.full_history)
            
            self.refresh_list()
            self.setup_interaction_mode()
            
            # Restart global hotkeys dynamically to apply new keybindings immediately
            try:
                import core.app
                if hasattr(core.app, 'hotkeys_manager') and core.app.hotkeys_manager:
                    core.app.hotkeys_manager.restart()
            except Exception as e:
                print(f"[FastPaste] Error reloading hotkey listener: {e}")

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
                img_data = history.get_image_bytes(filepath)
                if not img_data:
                    raise Exception("Não foi possível carregar os bytes da imagem (provavelmente apagada ou corrompida).")
                    
                if has_wl:
                    proc = subprocess.Popen(['wl-copy', '--type', 'image/png'], stdin=subprocess.PIPE)
                    proc.communicate(img_data)
                elif has_xclip:
                    proc = subprocess.Popen(['xclip', '-selection', 'clipboard', '-t', 'image/png'], stdin=subprocess.PIPE)
                    proc.communicate(img_data)
                else:
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    QApplication.clipboard().setImage(pixmap.toImage())
                    
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

    def showEvent(self, event):
        # Clear search filter and reset search entry
        self.search_entry.blockSignals(True)
        self.search_entry.clear()
        self.search_entry.blockSignals(False)
        
        # Load fresh history
        self.full_history = history.load_history()
        self.filtered_history = list(self.full_history)
        self.populate_list()
        
        # Always open at page 0 (search and list) instead of settings
        self.stacked_widget.setCurrentIndex(0)
        self.search_entry.setFocus()
        
        super().showEvent(event)



    def keyPressEvent(self, event):
        # Se a página de configurações estiver ativa, deixamos os eventos fluírem normalmente
        # e não executamos nenhum atalho da página de pesquisa.
        if self.stacked_widget.currentIndex() == 1:
            # Se o usuário pressionar Esc na tela de configurações (e não estiver gravando atalho),
            # fechamos as configurações (cancela).
            if event.key() == Qt.Key.Key_Escape:
                if hasattr(self, 'settings_page') and hasattr(self.settings_page, 'hotkey_input') and self.settings_page.hotkey_input.recording:
                    # Deixa o HotkeyLineEdit tratar o Esc para parar a gravação
                    super().keyPressEvent(event)
                else:
                    self.close_settings(saved=False)
                return
            super().keyPressEvent(event)
            return

        key = event.key()
        
        # Esc closes the window
        if key == Qt.Key.Key_Escape:
            self.close()
            return
            
        # Seta para baixo / para cima
        if key == Qt.Key.Key_Down:
            if self.search_entry.hasFocus():
                self.list_widget.setFocus()
                if self.list_widget.count() > 0:
                    current = self.list_widget.currentRow()
                    if current < 0:
                        self.list_widget.setCurrentRow(0)
                    else:
                        next_row = min(current + 1, self.list_widget.count() - 1)
                        self.list_widget.setCurrentRow(next_row)
                event.accept()
                return
        elif key == Qt.Key.Key_Up:
            if self.search_entry.hasFocus():
                self.list_widget.setFocus()
                if self.list_widget.count() > 0:
                    current = self.list_widget.currentRow()
                    if current < 0:
                        self.list_widget.setCurrentRow(self.list_widget.count() - 1)
                    else:
                        prev_row = max(current - 1, 0)
                        self.list_widget.setCurrentRow(prev_row)
                event.accept()
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
        self.close()
        if simulate_paste:
            self.input_sim.paste()
            
        if self.standalone:
            QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            clicked_widget = self.childAt(event.position().toPoint())
            if clicked_widget not in [self.list_widget, self.search_entry] and not self.list_widget.underMouse() and not self.search_entry.underMouse():
                # Tenta o arraste nativo do sistema (essencial para funcionamento correto no Wayland)
                if self.windowHandle():
                    self.windowHandle().startSystemMove()
                    event.accept()
                    return
                
                # Fallback manual para X11/Windows
                if hasattr(event, 'globalPosition'):
                    self._drag_pos = event.globalPosition().toPoint()
                else:
                    self._drag_pos = event.globalPos()
                self._drag_window_pos = self.pos()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        mode = settings.get('interaction_mode', 1)
        if mode == 2 and event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_pos'):
            if hasattr(event, 'globalPosition'):
                diff = event.globalPosition().toPoint() - self._drag_pos
            else:
                diff = event.globalPos() - self._drag_pos
            self.move(self._drag_window_pos + diff)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def setup_interaction_mode(self):
        # Desconecta os sinais existentes para evitar chamadas duplicadas
        try:
            self.list_widget.itemDoubleClicked.disconnect(self.on_item_activated)
        except TypeError:
            pass
        try:
            self.list_widget.itemClicked.disconnect(self.on_item_single_clicked)
        except TypeError:
            pass
            
        mode = settings.get('interaction_mode', 1)
        if mode == 1:
            # Modo 1: clique único ativa (copia/cola)
            self.list_widget.itemClicked.connect(self.on_item_single_clicked)
        else:
            # Modo 2: duplo clique ativa (copia/cola)
            self.list_widget.itemDoubleClicked.connect(self.on_item_activated)
            
        # O arrastar e soltar (DND) fica ativo em ambos os modos
        self.list_widget.setDragEnabled(True)
            
        # Garante que a borda e o estilo do cabeçalho atualizem dinamicamente
        self.apply_styles()
        
        # Atualiza o texto do botão do modo no header
        self.update_header_text()

    def toggle_interaction_mode(self):
        curr_mode = settings.get('interaction_mode', 1)
        new_mode = 2 if curr_mode == 1 else 1
        settings.set('interaction_mode', new_mode)
        
        # Update settings page inputs if open
        if hasattr(self, 'settings_page') and self.settings_page:
            if new_mode == 1:
                self.settings_page.mode1_radio.setChecked(True)
            else:
                self.settings_page.mode2_radio.setChecked(True)
                
        # Re-setup interaction behavior (DND, event listeners)
        self.setup_interaction_mode()

    def update_header_text(self):
        if not hasattr(self, 'header_mode_btn') or not self.header_mode_btn:
            return
        mode = settings.get('interaction_mode', 1)
        if mode == 1:
            self.header_mode_btn.setText("⚡ Modo 1")
        else:
            self.header_mode_btn.setText("📌 Modo 2")

    def on_item_single_clicked(self, item):
        mode = settings.get('interaction_mode', 1)
        if mode == 1:
            self.on_item_activated(item)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                # Se o cursor do mouse estiver dentro dos limites da própria janela,
                # ignora a perda de foco (evita fechar ao arrastar/clicar no header/background)
                from PyQt6.QtGui import QCursor
                if self.geometry().contains(QCursor.pos()):
                    super().changeEvent(event)
                    return

                mode = settings.get('interaction_mode', 1)
                if mode == 1:
                    # Delay mínimo para evitar conflito se o clique for uma ação de fechar
                    QTimer.singleShot(100, self.close)
        super().changeEvent(event)

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
