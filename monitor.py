import os
import signal
import sys
import time
import hashlib
import history

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

import os
import signal
import subprocess
import time
import hashlib
import history
import shutil

class ClipboardMonitor:
    def __init__(self):
        self.running = True
        self.last_text_hash = None

    def start(self):
        print("✅ FastPaste Monitor iniciado (via X11/XWayland Polling).")
        
        # Preferimos xclip no GNOME Wayland porque consultas nativas com wl-paste engasgam o compositor/dock
        has_xclip = shutil.which('xclip') is not None
        has_wl = shutil.which('wl-paste') is not None
        
        if not has_xclip and not has_wl:
            print("❌ ERRO: Instale o xclip (sudo apt install xclip)")
            return
            
        print("[FastPaste] Monitorando em background (intervalo 1s)...")
        
        while self.running:
            try:
                if has_xclip:
                    text_bytes = subprocess.check_output(['xclip', '-selection', 'clipboard', '-o'], stderr=subprocess.DEVNULL)
                else:
                    text_bytes = subprocess.check_output(['wl-paste', '--type', 'text', '--no-newline'], stderr=subprocess.DEVNULL)
                    
                if text_bytes:
                    current_hash = hashlib.sha256(text_bytes).hexdigest()
                    if current_hash != self.last_text_hash:
                        self.last_text_hash = current_hash
                        text = text_bytes.decode('utf-8')
                        if text.strip():
                            history.add_text(text)
                            print("[FastPaste] Texto salvo.")
            except Exception:
                pass
                
            time.sleep(1.0)

    def stop(self, sig=None, frame=None):
        print("\n🛑 Encerrando monitor...")
        self.running = False

if __name__ == "__main__":
    monitor = ClipboardMonitor()
    signal.signal(signal.SIGTERM, monitor.stop)
    signal.signal(signal.SIGINT, monitor.stop)
    monitor.start()
