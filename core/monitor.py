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
from core import history

class ClipboardMonitor:
    def __init__(self):
        self.last_text_hash = None
        self.last_image_hash = None
        self.running = False
        self.wl_proc = None
        self._check_lock = threading.Lock()
        
        self.app = QApplication.instance()
        if self.app:
            self.clipboard = self.app.clipboard()
            # Capture initial state to prevent double-saving on startup
            try:
                if self.clipboard.mimeData().hasText():
                    self.last_text_hash = hashlib.sha256(self.clipboard.mimeData().text().encode('utf-8')).hexdigest()
            except Exception:
                pass

    def _seed_current_clipboard_hashes(self):
        """Inicializa os hashes de imagem e texto atuais para evitar salvá-los ao iniciar/reiniciar o daemon."""
        has_xclip = shutil.which('xclip') is not None
        has_wl = shutil.which('wl-paste') is not None
        if not has_xclip and not has_wl:
            return
        try:
            # 1. Seed da Imagem
            img_bytes = b""
            if has_xclip:
                try:
                    img_bytes = subprocess.check_output(
                        ['xclip', '-selection', 'clipboard', '-t', 'image/png', '-o'],
                        stderr=subprocess.DEVNULL,
                        timeout=1
                    )
                except Exception:
                    pass
            if not img_bytes and has_wl:
                try:
                    img_bytes = subprocess.check_output(
                        ['wl-paste', '--type', 'image/png'],
                        stderr=subprocess.DEVNULL,
                        timeout=1
                    )
                except Exception:
                    pass

            if img_bytes:
                self.last_image_hash = hashlib.sha256(img_bytes).hexdigest()
                print("[FastPaste] Seed: imagem atual ignorada no próximo ciclo.")

            # 2. Seed do Texto
            text_bytes = b""
            if has_xclip:
                try:
                    text_bytes = subprocess.check_output(
                        ['xclip', '-selection', 'clipboard', '-o'],
                        stderr=subprocess.DEVNULL,
                        timeout=1
                    )
                except Exception:
                    pass
            if not text_bytes and has_wl:
                try:
                    text_bytes = subprocess.check_output(
                        ['wl-paste', '--type', 'text', '--no-newline'],
                        stderr=subprocess.DEVNULL,
                        timeout=1
                    )
                except Exception:
                    pass

            if text_bytes:
                self.last_text_hash = hashlib.sha256(text_bytes).hexdigest()
                print("[FastPaste] Seed: texto atual ignorado no próximo ciclo.")
        except Exception:
            pass




    def start(self):
        self.running = True
        
        is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None or os.environ.get('XDG_SESSION_TYPE') == 'wayland'
        has_wl = shutil.which('wl-paste') is not None

        if sys.platform.startswith('linux') and is_wayland and has_wl:
            print("✅ FastPaste Monitor started (Wayland Watch mode)")
            has_xclip = shutil.which('xclip') is not None
            if not has_xclip:
                print("[FastPaste] DICA: Instale o 'xclip' para evitar piscadas e lags na dock do GNOME/Ubuntu: sudo apt install xclip")
            # Inicializa hashes ANTES do loop para não salvar o clipboard atual na inicialização
            self._seed_current_clipboard_hashes()
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
        is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None or os.environ.get('XDG_SESSION_TYPE') == 'wayland'
        if sys.platform.startswith('linux') and is_wayland:
            self._do_linux_check()
        else:
            if self.app:
                self.on_clipboard_changed()

    def _wayland_watch_loop(self):
        # GNOME Wayland doesn't support wlroots data-control protocol, 
        # so wl-paste --watch fails immediately. 
        # The only universal Wayland fallback is polling wl-paste.
        # Since we disabled QSystemTrayIcon on Wayland, this polling will NOT bug the dock.
        while self.running:
            self._do_linux_check()
            time.sleep(1)

    def _do_linux_check(self):
        with self._check_lock:
            self._do_linux_check_locked()

    def _do_linux_check_locked(self):
        # Para não bugar a dock do GNOME/Ubuntu (que pisca um ícone quando wl-paste roda),
        # priorizamos o xclip (XWayland/X11), que roda invisível.
        has_xclip = shutil.which('xclip') is not None
        has_wl = shutil.which('wl-paste') is not None
        
        if not has_xclip and not has_wl:
            return

        try:
            # Se tiver xclip, usamos EXCLUSIVAMENTE o xclip para evitar bugs de dock com wl-paste
            if has_xclip:
                # 1. Imagem
                img_bytes = b""
                try:
                    img_bytes = subprocess.check_output(
                        ['xclip', '-selection', 'clipboard', '-t', 'image/png', '-o'],
                        stderr=subprocess.DEVNULL,
                        timeout=1
                    )
                except Exception:
                    pass
                
                if img_bytes:
                    current_hash = hashlib.sha256(img_bytes).hexdigest()
                    if current_hash != self.last_image_hash:
                        self.last_image_hash = current_hash
                        self.last_text_hash = None 
                        history.add_image(img_bytes)
                        print("[FastPaste] Print (Imagem) salvo (Polling background).")
                else:
                    # 2. Texto
                    text_bytes = b""
                    try:
                        text_bytes = subprocess.check_output(
                            ['xclip', '-selection', 'clipboard', '-o'],
                            stderr=subprocess.DEVNULL,
                            timeout=1
                        )
                    except Exception:
                        pass
                            
                    if text_bytes:
                        current_hash = hashlib.sha256(text_bytes).hexdigest()
                        if current_hash != self.last_text_hash:
                            self.last_text_hash = current_hash
                            text = text_bytes.decode('utf-8', errors='ignore')
                            if text.strip():
                                history.add_text(text)
                                print("[FastPaste] Texto salvo (Polling background).")
            
            # Se NÃO tiver xclip, usamos o wl-paste
            elif has_wl:
                # 1. Imagem
                img_bytes = b""
                try:
                    img_bytes = subprocess.check_output(
                        ['wl-paste', '--type', 'image/png'],
                        stderr=subprocess.DEVNULL,
                        timeout=1
                    )
                except Exception:
                    pass
                
                if img_bytes:
                    current_hash = hashlib.sha256(img_bytes).hexdigest()
                    if current_hash != self.last_image_hash:
                        self.last_image_hash = current_hash
                        self.last_text_hash = None 
                        history.add_image(img_bytes)
                        print("[FastPaste] Print (Imagem) salvo (Polling background).")
                else:
                    # 2. Texto
                    text_bytes = b""
                    try:
                        text_bytes = subprocess.check_output(
                            ['wl-paste', '--type', 'text', '--no-newline'],
                            stderr=subprocess.DEVNULL,
                            timeout=1
                        )
                    except Exception:
                        pass
                            
                    if text_bytes:
                        current_hash = hashlib.sha256(text_bytes).hexdigest()
                        if current_hash != self.last_text_hash:
                            self.last_text_hash = current_hash
                            text = text_bytes.decode('utf-8', errors='ignore')
                            if text.strip():
                                history.add_text(text)
                                print("[FastPaste] Texto salvo (Polling background).")
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
