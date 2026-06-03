import sys
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction
from core import history

class FastPasteTray:
    def __init__(self, on_show_callback, on_settings_callback, on_exit_callback):
        self.on_show_callback = on_show_callback
        self.on_settings_callback = on_settings_callback
        self.on_exit_callback = on_exit_callback
        self.tray_icon = None

    def setup(self):
        # We need a QApplication instance to run QSystemTrayIcon
        app = QApplication.instance()
        if not app:
            # Should not happen as we start QApplication in main.py
            print("[FastPaste] QApplication not found for tray icon.")
            return

        self.tray_icon = QSystemTrayIcon()
        
        # In PyQt, icon needs to be a QIcon. 
        # Using a standard edit-paste fallback or a bundled icon.
        # Fallback to system standard icon:
        icon = QIcon.fromTheme("edit-paste")
        if icon.isNull():
            # If not found, create a dummy icon or use another standard one
            icon = QIcon.fromTheme("system-run")
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip("FastPaste Clipboard Manager")

        # Context Menu
        self.menu = QMenu()
        
        from screens.popup import get_tinted_icon
        from configs.config import UI_COLORS
        
        # Helper para evitar travamentos se o ícone não existir
        def make_icon(name):
            pixmap = get_tinted_icon(name, UI_COLORS['fg'])
            return QIcon(pixmap) if pixmap else QIcon()
        
        show_action = QAction(make_icon("view-fullscreen-symbolic"), "Mostrar FastPaste", self.menu)
        show_action.triggered.connect(self.on_show_callback)
        self.menu.addAction(show_action)
        
        settings_action = QAction(make_icon("preferences-system-symbolic"), "Configurações...", self.menu)
        settings_action.triggered.connect(self.on_settings_callback)
        self.menu.addAction(settings_action)
        
        clear_action = QAction(make_icon("edit-clear-all-symbolic"), "Limpar Histórico", self.menu)
        clear_action.triggered.connect(self._clear_history)
        self.menu.addAction(clear_action)
        
        self.menu.addSeparator()
        
        exit_action = QAction(make_icon("application-exit-symbolic"), "Sair", self.menu)
        exit_action.triggered.connect(self.on_exit_callback)
        self.menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(self.menu)
        
        # Double click to show
        self.tray_icon.activated.connect(self._on_tray_activated)
        
        self.tray_icon.show()
        print("[FastPaste] PyQt6 Tray icon started.")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.on_show_callback()

    def _clear_history(self):
        history.clear()
        print("[FastPaste] History cleared via tray.")
