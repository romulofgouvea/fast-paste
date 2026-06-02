import gi
import os
import sys
import subprocess

# Tenta carregar as bibliotecas de AppIndicator para integração de bandeja nativa no Ubuntu
AppIndicator = None
try:
    gi.require_version('AyatanaAppIndicator3', '0.1')
    from gi.repository import AyatanaAppIndicator3 as AppIndicator
except Exception:
    try:
        gi.require_version('AppIndicator3', '0.1')
        from gi.repository import AppIndicator3 as AppIndicator
    except Exception:
        pass

from gi.repository import Gtk, Gdk

class FastPasteTray:
    def __init__(self, on_show_callback, on_exit_callback):
        self.on_show_callback = on_show_callback
        self.on_exit_callback = on_exit_callback
        self.indicator = None
        self.status_icon = None

    def setup(self):
        # Nome do ícone padrão do sistema Ubuntu
        icon_name = "edit-paste"
        
        # Menu Contextual do Tray
        menu = Gtk.Menu()
        
        show_item = Gtk.MenuItem(label="⚡ Show History")
        show_item.connect("activate", lambda w: self.on_show_callback())
        menu.append(show_item)
        
        clear_item = Gtk.MenuItem(label="🧹 Clear History")
        clear_item.connect("activate", lambda w: self._clear_history())
        menu.append(clear_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        exit_item = Gtk.MenuItem(label="🛑 Exit")
        exit_item.connect("activate", lambda w: self.on_exit_callback())
        menu.append(exit_item)
        
        menu.show_all()

        if AppIndicator:
            # 1. Método Preferencial no Ubuntu/GNOME: Ayatana/AppIndicator
            self.indicator = AppIndicator.Indicator.new(
                "fast-paste-indicator",
                icon_name,
                AppIndicator.IndicatorCategory.APPLICATION_STATUS
            )
            self.indicator.set_status(AppIndicator.IndicatorStatus.ACTIVE)
            self.indicator.set_menu(menu)
            print("[FastPaste] Ícone de bandeja iniciado via Ayatana/AppIndicator.")
        else:
            # 2. Fallback de Bandeja Padrão do GTK3
            try:
                self.status_icon = Gtk.StatusIcon()
                self.status_icon.set_from_icon_name(icon_name)
                self.status_icon.set_title("FastPaste")
                self.status_icon.set_tooltip_text("FastPaste Clipboard Manager")
                self.status_icon.connect("popup-menu", self.on_status_icon_menu, menu)
                self.status_icon.connect("activate", lambda w: self.on_show_callback())
                print("[FastPaste] Ícone de bandeja iniciado via Gtk.StatusIcon (Fallback).")
            except Exception as e:
                print(f"[FastPaste] Não foi possível criar o ícone de bandeja: {e} (Pulando tray icon)")

    def on_status_icon_menu(self, status_icon, button, activate_time, menu):
        menu.popup(None, None, Gtk.StatusIcon.position_menu, status_icon, button, activate_time)

    def _clear_history(self):
        import history
        history.clear()
        print("[FastPaste] Histórico limpo via bandeja.")
