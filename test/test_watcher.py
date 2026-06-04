import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk

def on_changed(clipboard, event):
    text = clipboard.wait_for_text()
    if text:
        print("NEW:" + text, flush=True)

cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
cb.connect('owner-change', on_changed)
print("Listening...")
Gtk.main()
