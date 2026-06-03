import os
import tempfile

APP_NAME = "FastPaste"
MAX_HISTORY = 500

# Caminhos dos arquivos persistentes (evita perda ao reiniciar e problemas de sandbox como Snaps/Flatpaks)
import sys
if sys.platform.startswith("win"):
    DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "fast-paste")
elif sys.platform.startswith("darwin"):
    DATA_DIR = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "fast-paste")
else:
    DATA_DIR = os.path.join(os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")), "fast-paste")

DB_FILE = os.path.join(DATA_DIR, "history.db")
IMAGES_DIR = os.path.join(DATA_DIR, "images")
LOG_FILE = os.path.join(DATA_DIR, "daemon.log")

# Controle de processos (agora na pasta runtime do usuário)
XDG_RUNTIME_DIR = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
PID_FILE = os.path.join(XDG_RUNTIME_DIR, "fast-paste.pid")
SOCKET_PATH = os.path.join(XDG_RUNTIME_DIR, "fast-paste.sock")

# Cores UI (Ubuntu Dark System Theme)
UI_COLORS = {
    "bg_transparent": "rgba(30, 30, 30, 0.0)",    # Fundo da janela invisível
    "card_bg": "rgba(36, 36, 36, 0.98)",          # Fundo escuro (Yaru Dark)
    "card_border": "rgba(60, 60, 60, 0.8)",       # Borda sutil escura
    "hover": "rgba(50, 50, 50, 0.8)",             # Hover suave
    "selected": "rgba(233, 84, 32, 0.9)",         # Seleção (Ubuntu Orange)
    "fg": "#ffffff",                              # Texto branco
    "fg_dim": "#a1a1a1",                          # Texto cinza
    "shadow": "rgba(0, 0, 0, 0.4)"                # Sombra forte para destacar
}

def get_asset_path(filename):
    """Retrieve absolute path to an asset file, handling PyInstaller packaging."""
    import sys
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, "assets", filename)
    # If running from source
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, "assets", filename)

def hide_dock_icon():
    """Hides the application icon from the macOS Dock programmatically."""
    import sys
    if sys.platform == "darwin":
        try:
            import ctypes
            import ctypes.util
            objc = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
            void_p = ctypes.c_void_p
            objc.objc_getClass.restype = void_p
            objc.sel_registerName.restype = void_p
            ns_app_class = objc.objc_getClass(b"NSApplication")
            shared_app_sel = objc.sel_registerName(b"sharedApplication")
            objc.objc_msgSend.restype = void_p
            objc.objc_msgSend.argtypes = [void_p, void_p]
            shared_app = objc.objc_msgSend(ns_app_class, shared_app_sel)
            set_policy_sel = objc.sel_registerName(b"setActivationPolicy:")
            # NSApplicationActivationPolicyAccessory = 1
            objc.objc_msgSend(shared_app, set_policy_sel, ctypes.c_long(1))
        except Exception as e:
            print(f"[FastPaste] Failed to set macOS activation policy dynamically: {e}")

