import gi
import os
import subprocess
import shutil
import datetime

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Pango, GdkPixbuf

import history
from config import UI_COLORS, APP_NAME

class FastPastePopup(Gtk.Window):
    def __init__(self, standalone=True):
        super().__init__(title=APP_NAME)
        self.standalone = standalone

        # Configurações da Janela
        self.set_default_size(380, 550)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_decorated(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)

        # Habilita transparência total na janela
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            self.set_visual(visual)
        self.set_app_paintable(True)

        # Carrega Histórico Inicial do SQLite
        self.full_history = history.load_history()
        self.filtered_history = list(self.full_history)

        self._apply_css()

        # Container Principal (Box Central com glassmorphism css)
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.get_style_context().add_class("main-box")
        self.add(main_box)

        # Card 1: Barra de Busca (Glassy Pill)
        search_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        search_card.get_style_context().add_class("search-card")
        
        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic", Gtk.IconSize.MENU)
        search_icon.get_style_context().add_class("search-icon")
        search_card.pack_start(search_icon, False, False, 5)

        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search clips or dates...")
        self.search_entry.get_style_context().add_class("search-entry-inner")
        self.search_entry.set_has_frame(False)
        self.search_entry.connect("changed", self.on_search_changed)
        search_card.pack_start(self.search_entry, True, True, 0)

        main_box.pack_start(search_card, False, False, 10)

        # Card 2: Lista de Itens (Glassy Box)
        list_card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        list_card.get_style_context().add_class("list-card")

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        list_card.pack_start(scrolled, True, True, 0)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.connect("row-activated", self.on_row_activated)
        self.listbox.get_style_context().add_class("item-list")
        scrolled.add(self.listbox)

        main_box.pack_start(list_card, True, True, 0)

        self._populate_list()
        
        self.connect("key-press-event", self.on_key_press)
        self.connect("focus-out-event", lambda w, e: self.close_app())

    def _apply_css(self):
        css = f"""
        window {{
            background-color: transparent;
        }}
        .main-box {{
            background-color: {UI_COLORS['card_bg']};
            border-radius: 16px;
            border: 1px solid {UI_COLORS['card_border']};
            box-shadow: 0 10px 30px {UI_COLORS['shadow']};
            padding: 15px;
        }}
        .search-card {{
            background-color: rgba(45, 45, 45, 0.6);
            border-radius: 10px;
            border: 1px solid rgba(80, 80, 80, 0.4);
            padding: 6px 12px;
            margin-bottom: 8px;
        }}
        .search-icon {{
            color: {UI_COLORS['fg_dim']};
        }}
        .search-entry-inner {{
            background-color: transparent;
            color: {UI_COLORS['fg']};
            caret-color: {UI_COLORS['fg']};
            font-size: 14px;
        }}
        .search-entry-inner:focus {{
            box-shadow: none;
            outline: none;
        }}
        .list-card {{
            background-color: rgba(28, 28, 28, 0.4);
            border-radius: 10px;
            border: 1px solid rgba(60, 60, 60, 0.3);
            padding: 4px 0;
        }}
        .item-list {{
            background-color: transparent;
        }}
        row {{
            background-color: transparent !important;
            border: none !important;
            padding: 6px !important;
            margin: 0 !important;
            outline: none !important;
            box-shadow: none !important;
        }}
        row:hover, row:selected {{
            background-color: transparent !important;
            border: none !important;
            outline: none !important;
            box-shadow: none !important;
        }}
        .card-item {{
            border-radius: 8px;
            padding: 8px 12px;
            background-color: transparent;
            transition: all 0.15s ease;
        }}
        row:hover .card-item {{
            background-color: {UI_COLORS['hover']} !important;
        }}
        row:selected .card-item {{
            background-color: {UI_COLORS['selected']} !important;
        }}
        .item-label {{
            font-size: 13.5px;
            font-weight: 500;
            color: {UI_COLORS['fg']};
        }}
        .item-label-dim {{
            font-size: 13.5px;
            font-weight: 500;
            color: {UI_COLORS['fg_dim']};
        }}
        row:selected .item-label, row:selected .item-label-dim {{
            color: #ffffff;
        }}
        .hotkey-badge {{
            font-size: 10.5px;
            font-weight: bold;
            color: {UI_COLORS['selected']};
            background-color: rgba(233, 84, 32, 0.15);
            padding: 2px 6px;
            border-radius: 4px;
        }}
        row:selected .hotkey-badge {{
            color: #ffffff;
            background-color: rgba(255, 255, 255, 0.2);
        }}
        .pin-badge {{
            font-size: 12px;
        }}
        .timestamp-label {{
            font-size: 11px;
            color: {UI_COLORS['fg_dim']};
        }}
        row:selected .timestamp-label {{
            color: rgba(255, 255, 255, 0.8);
        }}
        .item-image {{
            border-radius: 4px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }}
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _populate_list(self):
        for child in self.listbox.get_children():
            self.listbox.remove(child)

        if not self.filtered_history:
            lbl = Gtk.Label(label="No clips found.")
            lbl.get_style_context().add_class("item-label-dim")
            lbl.set_margin_top(20)
            lbl.set_margin_bottom(20)
            row = Gtk.ListBoxRow()
            row.add(lbl)
            row.set_selectable(False)
            self.listbox.add(row)
            self.listbox.show_all()
            return

        for idx, item in enumerate(self.filtered_history):
            row = Gtk.ListBoxRow()
            
            # HBox principal da linha (com classe para card colorido isolado)
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            hbox.get_style_context().add_class("card-item")
            
            # Icone ou Imagem na Esquerda
            left_widget = None
            if item["type"] == "text":
                content_str = item["content"]
                if content_str.startswith(("http://", "https://", "www.")):
                    left_widget = Gtk.Image.new_from_icon_name("web-browser-symbolic", Gtk.IconSize.MENU)
                else:
                    left_widget = Gtk.Image.new_from_icon_name("text-x-generic-symbolic", Gtk.IconSize.MENU)
                
                preview = content_str.replace('\n', '  ')
                if len(preview) > 45:
                    preview = preview[:42] + "..."
                
                lbl = Gtk.Label(label=preview)
                lbl.set_xalign(0)
                lbl.set_ellipsize(Pango.EllipsizeMode.END)
                lbl.get_style_context().add_class("item-label")
                
                hbox.pack_start(left_widget, False, False, 0)
                hbox.pack_start(lbl, True, True, 0)
                
            elif item["type"] == "image":
                filepath = item["content"]
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filepath, 80, 45, True)
                    left_widget = Gtk.Image.new_from_pixbuf(pixbuf)
                    left_widget.get_style_context().add_class("item-image")
                except Exception:
                    left_widget = Gtk.Image.new_from_icon_name("image-x-generic-symbolic", Gtk.IconSize.DND)
                
                lbl = Gtk.Label(label="[Imagem PNG]")
                lbl.set_xalign(0)
                lbl.get_style_context().add_class("item-label-dim")
                
                hbox.pack_start(left_widget, False, False, 0)
                hbox.pack_start(lbl, True, True, 0)

            # Box da Direita (Data, Pin, Badge de Atalho)
            right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            
            if idx < 9:
                badge = Gtk.Label(label=f"^{idx+1}")
                badge.get_style_context().add_class("hotkey-badge")
                right_box.pack_start(badge, False, False, 0)
                
            if item["is_pinned"]:
                pin = Gtk.Label(label="📌")
                pin.get_style_context().add_class("pin-badge")
                right_box.pack_start(pin, False, False, 0)
                
            dt = datetime.datetime.fromtimestamp(item["created_at"])
            time_str = dt.strftime("%H:%M")
            time_lbl = Gtk.Label(label=time_str)
            time_lbl.get_style_context().add_class("timestamp-label")
            right_box.pack_start(time_lbl, False, False, 0)

            hbox.pack_end(right_box, False, False, 0)
            
            row.add(hbox)
            row.connect("button-press-event", self.on_row_button_press, item)
            self.listbox.add(row)

        self.listbox.show_all()
        self.listbox.unselect_all()
        self.search_entry.grab_focus()

    def on_search_changed(self, entry):
        query = entry.get_text().strip()
        if not query:
            self.full_history = history.load_history()
            self.filtered_history = list(self.full_history)
        else:
            self.filtered_history = history.load_history(query)
        self._populate_list()

    def on_row_activated(self, listbox, row):
        index = row.get_index()
        if 0 <= index < len(self.filtered_history):
            self._paste_item(self.filtered_history[index])

    def on_row_button_press(self, row, event, item):
        if event.button == 3:
            menu = Gtk.Menu()
            
            pin_lbl = "📍 Unpin Item" if item["is_pinned"] else "📌 Pin Item"
            pin_menu = Gtk.MenuItem(label=pin_lbl)
            pin_menu.connect("activate", lambda w: self.toggle_pin_item(item))
            menu.append(pin_menu)
            
            del_menu = Gtk.MenuItem(label="🗑️ Remove Item")
            del_menu.connect("activate", lambda w: self.delete_item(item))
            menu.append(del_menu)
            
            menu.append(Gtk.SeparatorMenuItem())
            
            clear_menu = Gtk.MenuItem(label="🧹 Clear Unpinned History")
            clear_menu.connect("activate", lambda w: self.clear_unpinned_history())
            menu.append(clear_menu)
            
            menu.show_all()
            menu.popup_at_pointer(event)
            return True
        return False

    def toggle_pin_item(self, item):
        history.toggle_pin(item["id"])
        self._refresh_list()

    def delete_item(self, item):
        history.delete_item(item["id"])
        self._refresh_list()

    def clear_unpinned_history(self):
        history.clear()
        self._refresh_list()

    def _refresh_list(self):
        self.on_search_changed(self.search_entry)

    def on_key_press(self, widget, event):
        keyval = event.keyval
        state = event.state
        is_ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        
        if keyval == Gdk.KEY_Escape:
            self.close_app()
            return True
            
        if keyval == Gdk.KEY_Delete:
            current_row = self.listbox.get_selected_row()
            if current_row:
                idx = current_row.get_index()
                if 0 <= idx < len(self.filtered_history):
                    self.delete_item(self.filtered_history[idx])
            return True

        if keyval == Gdk.KEY_f and is_ctrl:
            self.search_entry.grab_focus()
            return True

        if keyval == Gdk.KEY_p and is_ctrl:
            current_row = self.listbox.get_selected_row()
            if current_row:
                idx = current_row.get_index()
                if 0 <= idx < len(self.filtered_history):
                    self.toggle_pin_item(self.filtered_history[idx])
            return True

        if is_ctrl and (Gdk.KEY_1 <= keyval <= Gdk.KEY_9):
            num = keyval - Gdk.KEY_1
            if num < len(self.filtered_history):
                self._paste_item(self.filtered_history[num])
            return True
            
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            max_idx = len(self.filtered_history) - 1
            if max_idx < 0: 
                return False
            
            current_row = self.listbox.get_selected_row()
            idx = current_row.get_index() if current_row else -1
            
            if keyval == Gdk.KEY_Down:
                idx = min(idx + 1, max_idx)
            else:
                idx = max(idx - 1, 0)
                
            row = self.listbox.get_row_at_index(idx)
            self.listbox.select_row(row)
            row.grab_focus()
            return True
            
        if keyval == Gdk.KEY_Return:
            current_row = self.listbox.get_selected_row()
            if current_row:
                idx = current_row.get_index()
                if 0 <= idx < len(self.filtered_history):
                    self._paste_item(self.filtered_history[idx])
            else:
                if self.filtered_history:
                    self._paste_item(self.filtered_history[0])
            return True

        if not self.search_entry.has_focus() and keyval < 0xFF:
            self.search_entry.grab_focus()
            
        return False

    def _paste_item(self, item):
        if item["type"] == "text":
            text = item["content"]
            try:
                proc = subprocess.Popen(['wl-copy'], stdin=subprocess.PIPE)
                proc.communicate(text.encode('utf-8'))
                history.add_text(text)
            except Exception as e:
                print(f"[FastPaste] Erro no wl-copy texto: {e}")
                
        elif item["type"] == "image":
            filepath = item["content"]
            try:
                proc = subprocess.Popen(['wl-copy', '--type', 'image/png'], stdin=subprocess.PIPE)
                with open(filepath, 'rb') as f:
                    img_data = f.read()
                    proc.communicate(img_data)
                history.add_image(img_data)
            except Exception as e:
                print(f"[FastPaste] Erro no wl-copy imagem: {e}")

        self.close_app(simulate_paste=True)

    def close_app(self, simulate_paste=False):
        self.destroy()
        if simulate_paste:
            cmd = None
            if shutil.which("wtype"):
                cmd = "sleep 0.15 && wtype -M ctrl -k v -m ctrl"
            elif shutil.which("ydotool"):
                cmd = "sleep 0.15 && ydotool key 29:1 47:1 47:0 29:0"
            elif shutil.which("xdotool"):
                cmd = "sleep 0.15 && xdotool key ctrl+v"
                
            if cmd:
                subprocess.Popen(['sh', '-c', cmd], start_new_session=True)
                
        if self.standalone:
            Gtk.main_quit()

def show(standalone=True):
    app = FastPastePopup(standalone=standalone)
    app.show_all()
    if standalone:
        Gtk.main()
    return app

if __name__ == "__main__":
    show(standalone=True)
