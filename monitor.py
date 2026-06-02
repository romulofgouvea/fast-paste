import sys
import os
import time
import threading
import hashlib
import subprocess
import shutil
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage, QClipboard
from PyQt6.QtCore import QBuffer, QIODevice
import history

class ClipboardMonitor:
    def __init__(self):
        self.last_text_hash = None
        self.last_image_hash = None
        self.running = False
        self.wl_proc = None
        
        self.app = QApplication.instance()
        if self.app:
            self.clipboard = self.app.clipboard()
            # Capture initial state to prevent double-saving on startup
            if self.clipboard.mimeData().hasText():
                self.last_text_hash = hashlib.sha256(self.clipboard.mimeData().text().encode('utf-8')).hexdigest()

    def start(self):
        self.running = True
        
        is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None
        has_wl = shutil.which('wl-paste') is not None

        if sys.platform.startswith('linux') and is_wayland and has_wl:
            print("✅ FastPaste Monitor started (Wayland Watch mode)")
            self.thread = threading.Thread(target=self._wayland_watch_loop, daemon=True)
            self.thread.start()
        else:
            print("✅ FastPaste Monitor started (via PyQt6 QClipboard natively)")
            if self.app:
                self.clipboard.dataChanged.connect(self.on_clipboard_changed)

    def stop(self):
        print("\n🛑 Stopping monitor...")
        self.running = False
        if self.wl_proc:
            try:
                self.wl_proc.terminate()
            except:
                pass
                
        if hasattr(self, 'clipboard') and self.app:
            try:
                self.clipboard.dataChanged.disconnect(self.on_clipboard_changed)
            except Exception:
                pass

    def force_check(self):
        """Força uma verificação imediata para evitar delay ao abrir o popup"""
        is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None
        if sys.platform.startswith('linux') and is_wayland:
            self._do_linux_check()
        else:
            if self.app:
                self.on_clipboard_changed()

    def _wayland_watch_loop(self):
        # Em vez de polling (que engasga a dock), usamos wl-paste --watch para bloquear até haver mudança!
        try:
            self.wl_proc = subprocess.Popen(
                ['wl-paste', '--watch', 'echo', 'CHANGED'], 
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )
            
            while self.running:
                line = self.wl_proc.stdout.readline()
                if not line:
                    break # Processo morreu ou parou
                
                # Houve uma mudança no clipboard! 
                # Espera uns milissegundos para o buffer estabilizar antes de ler
                time.sleep(0.1)
                self._do_linux_check()
                
        except Exception as e:
            print(f"[FastPaste] Watch loop crashed: {e}")

    def _do_linux_check(self):
        has_wl = shutil.which('wl-paste') is not None
        if not has_wl: return
        
        try:
            # 1. Tentar pegar imagem
            img_bytes = b""
            try:
                img_bytes = subprocess.check_output(['wl-paste', '--type', 'image/png'], stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                pass
            
            if img_bytes:
                current_hash = hashlib.sha256(img_bytes).hexdigest()
                if current_hash != self.last_image_hash:
                    self.last_image_hash = current_hash
                    self.last_text_hash = None 
                    history.add_image(img_bytes)
                    print("[FastPaste] Print (Imagem) salvo via Wayland Watch.")
            else:
                # 2. Tentar pegar texto
                text_bytes = b""
                try:
                    text_bytes = subprocess.check_output(['wl-paste', '--type', 'text', '--no-newline'], stderr=subprocess.DEVNULL)
                except subprocess.CalledProcessError:
                    pass
                        
                if text_bytes:
                    current_hash = hashlib.sha256(text_bytes).hexdigest()
                    if current_hash != self.last_text_hash:
                        self.last_text_hash = current_hash
                        text = text_bytes.decode('utf-8', errors='ignore')
                        if text.strip():
                            history.add_text(text)
                            print("[FastPaste] Texto salvo via Wayland Watch.")
                            
        except Exception:
            pass

    def on_clipboard_changed(self):
        if not self.app: return
        mime_data = self.clipboard.mimeData()

        # Handle images
        if mime_data.hasImage():
            image = self.clipboard.image()
            if not image.isNull():
                buffer = QBuffer()
                buffer.open(QIODevice.OpenModeFlag.ReadWrite)
                image.save(buffer, "PNG")
                img_bytes = buffer.data().data()
                
                current_hash = hashlib.sha256(img_bytes).hexdigest()
                if current_hash != self.last_image_hash:
                    self.last_image_hash = current_hash
                    self.last_text_hash = None
                    history.add_image(img_bytes)
                    print("[FastPaste] Image saved.")
                    
        # Handle text
        elif mime_data.hasText():
            text = mime_data.text()
            if text.strip():
                current_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
                if current_hash != self.last_text_hash:
                    self.last_text_hash = current_hash
                    history.add_text(text)
                    print("[FastPaste] Text saved.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    monitor = ClipboardMonitor()
    monitor.start()
    sys.exit(app.exec())
