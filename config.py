import os

APP_NAME = "FastPaste"
MAX_HISTORY = 500

# Caminhos dos arquivos baseados no padrão XDG
DATA_DIR = os.path.expanduser("~/.local/share/fast-paste")
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
