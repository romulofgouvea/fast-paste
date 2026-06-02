#!/bin/bash
# ============================================
# FastPaste - Setup Script
# ============================================
# Instala dependências e configura o atalho de teclado

set -e

echo "╔═══════════════════════════════════════════════╗"
echo "║      ⚡ FastPaste - Setup                      ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FAST_PASTE_PY="$SCRIPT_DIR/fast_paste.py"

# --- 1. Install system dependencies ---
echo "[1/4] Instalando dependências do sistema..."
if command -v wl-paste >/dev/null 2>&1; then
    echo "  ✅ Dependências do sistema já estão instaladas!"
else
    sudo apt-get update || true
    # Substituído ydotool por wtype para melhor compatibilidade com Wayland sem root
    sudo apt-get install -y wl-clipboard wtype xdotool || echo "  ⚠ Erro ao instalar dependências. Auto-paste pode não funcionar."
fi

# Garante permissões locais
chmod +x "$SCRIPT_DIR"/*.py

# --- 2. Create data directory ---
echo "[2/4] Criando diretório de dados..."
mkdir -p ~/.local/share/fast-paste

# --- 3. Create desktop entry for show command ---
echo "[3/4] Criando entrada .desktop..."
mkdir -p ~/.local/share/applications

cat > ~/.local/share/applications/fast-paste.desktop << EOF
[Desktop Entry]
Name=FastPaste
Comment=Clipboard History Manager
Exec=python3 $FAST_PASTE_PY show
Icon=edit-paste
Terminal=false
Type=Application
Categories=Utility;
EOF

# --- 4. Configure keyboard shortcut (GNOME) ---
echo "[4/4] Configurando atalho de teclado..."

# Detect desktop environment
DESKTOP="${XDG_CURRENT_DESKTOP:-unknown}"
echo "  Desktop detectado: $DESKTOP"

if echo "$DESKTOP" | grep -qi "gnome\|ubuntu"; then
    echo "  Configurando atalho no GNOME..."

    # Get current custom keybindings
    CURRENT=$(gsettings get org.gnome.settings-daemon.plugins.media-keys custom-keybindings 2>/dev/null || echo "[]")

    # Check if our keybinding already exists
    KEYBINDING_PATH="/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/fast-paste/"
    if echo "$CURRENT" | grep -q "fast-paste"; then
        echo "  Atalho já existe, atualizando..."
    else
        # Add our keybinding to the list
        if [ "$CURRENT" = "@as []" ] || [ "$CURRENT" = "[]" ]; then
            NEW="['$KEYBINDING_PATH']"
        else
            NEW=$(echo "$CURRENT" | sed "s/]$/, '$KEYBINDING_PATH']/")
        fi
        gsettings set org.gnome.settings-daemon.plugins.media-keys custom-keybindings "$NEW"
    fi

    # Set keybinding properties
    SCHEMA="org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
    SCHEMA_PATH="$KEYBINDING_PATH"

    gsettings set "$SCHEMA:$SCHEMA_PATH" name "FastPaste - Show Clipboard"
    gsettings set "$SCHEMA:$SCHEMA_PATH" command "python3 $FAST_PASTE_PY show"
    gsettings set "$SCHEMA:$SCHEMA_PATH" binding "<Ctrl>apostrophe"

    echo "  ✅ Atalho configurado: Ctrl + '"

elif echo "$DESKTOP" | grep -qi "kde\|plasma"; then
    echo "  Para KDE/Plasma, configure manualmente:"
    echo "  Settings → Shortcuts → Custom Shortcuts"
    echo "  Comando: python3 $FAST_PASTE_PY show"
    echo "  Atalho: Ctrl + '"

elif echo "$DESKTOP" | grep -qi "xfce"; then
    echo "  Para XFCE, configure manualmente:"
    echo "  Settings → Keyboard → Application Shortcuts"
    echo "  Comando: python3 $FAST_PASTE_PY show"
    echo "  Atalho: Ctrl + '"

else
    echo "  ⚠ Desktop não reconhecido. Configure o atalho manualmente:"
    echo "  Comando: python3 $FAST_PASTE_PY show"
    echo "  Atalho: Ctrl + '"
fi

echo ""
# --- 5. Configure Systemd User Service ---
echo "[5/5] Configurando Serviço Systemd do Usuário..."
# Remove entrada antiga do autostart para evitar conflitos/duplicação
rm -f ~/.config/autostart/fast-paste-daemon.desktop

mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/fast-paste.service << EOF
[Unit]
Description=FastPaste Clipboard Manager Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $FAST_PASTE_PY run
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

# Habilita e reinicia o serviço systemd do usuário
echo "  Habilitando e iniciando o serviço no Systemd..."
systemctl --user import-environment DISPLAY WAYLAND_DISPLAY XDG_RUNTIME_DIR || true
systemctl --user daemon-reload || true
systemctl --user enable fast-paste.service || true
systemctl --user restart fast-paste.service || true

echo ""
echo "╔═══════════════════════════════════════════════╗"
echo "║  ✅ Setup concluído com sucesso!              ║"
echo "║                                               ║"
echo "║  Serviço Systemd (Bandeja + Monitor):         ║"
echo "║    systemctl --user status fast-paste         ║"
echo "║                                               ║"
echo "║  Para abrir o popup de histórico:             ║"
echo "║    Atalho: Ctrl + '                           ║"
echo "╚═══════════════════════════════════════════════╝"
