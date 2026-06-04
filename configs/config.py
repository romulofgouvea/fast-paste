import os
import tempfile

APP_NAME = "FPaste"
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
PID_FILE = os.path.join(XDG_RUNTIME_DIR, f"{APP_NAME.lower()}.pid")
SOCKET_PATH = os.path.join(XDG_RUNTIME_DIR, f"{APP_NAME.lower()}.sock")

# Cores UI (Ubuntu Dark System Theme)
UI_COLORS = {
    "bg_transparent": "rgba(30, 30, 30, 0.0)",    # Fundo da janela invisível
    "card_bg": "rgba(36, 36, 36, 0.98)",          # Fundo escuro (Yaru Dark)
    "card_border": "rgba(60, 60, 60, 0.8)",       # Borda sutil escura
    "hover": "rgba(50, 50, 50, 0.8)",             # Hover suave
    "selected": "#FF7A00",                        # Seleção (Banco Inter Orange)
    "fg": "#ffffff",                              # Texto branco
    "fg_dim": "#a1a1a1",                          # Texto cinza
    "shadow": "rgba(0, 0, 0, 0.4)"                # Sombra forte para destacar
}

def apply_theme_color(color_hex):
    """Updates the accent color dynamically."""
    if color_hex:
        UI_COLORS['selected'] = color_hex

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
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

            app = NSApplication.sharedApplication()
            if app is not None:
                app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception as e:
            print(f"[FastPaste] Failed to set macOS activation policy dynamically: {e}")
