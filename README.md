# ⚡ FastPaste - Clipboard Manager para Linux

## ✨ Funcionalidades

- 📋 **Monitora automaticamente** tudo que você copia (Ctrl+C)
- 🔍 **Busca rápida** no histórico de cópias
- ⌨️ **Atalho de teclado** — Ctrl+' para abrir o popup
- 🎨 **Interface bonita** com tema escuro
- 💾 **Histórico persistente** — mantém até 50 itens
- 🗑️ **Delete individual** — remova itens do histórico
- 🚀 **Auto-paste** — cola automaticamente o item selecionado

## 📦 Pré-requisitos

- Python 3
- GTK3 (PyGObject) — já vem na maioria das distros Linux
- wtype (recomendado para auto-paste no Wayland) ou xdotool (para X11)

## 🚀 Instalação

```bash
# 1. Rodar o setup (instala dependências, Systemd e configura atalho)
chmod +x setup.sh
./setup.sh

# 2. Opcionalmente verifique o status do serviço
systemctl --user status fast-paste
```

## 📖 Uso

O setup já configura o daemon via Systemd para rodar automaticamente (usando o comando `run`), que inicia o monitor de clipboard e o ícone de bandeja, além do servidor IPC.

### Comandos

```bash
python3 fast_paste.py run      # Inicia o daemon com tray icon e IPC server (usado pelo Systemd)
python3 fast_paste.py show     # Abre o popup com histórico (instância única via IPC)
python3 fast_paste.py clear    # Limpa o histórico
python3 fast_paste.py status   # Verifica se o daemon está ativo
```

### Atalhos no Popup

| Tecla | Ação |
|-------|------|
| `↑` `↓` | Navegar entre itens |
| `Enter` | Selecionar e colar |
| `Delete` | Remover item |
| `Esc` | Fechar popup |
| Digitando | Filtrar/buscar |

### Workflow

1. O daemon já deve estar rodando (Systemd)
2. **Copie textos normalmente** com Ctrl+C
3. **Pressione Ctrl+'** para abrir o popup
4. **Navegue** com as setas e **Enter** para colar
5. Ou **busque** digitando parte do texto

## 🏗️ Arquitetura

```
fast-paste/
├── fast_paste.py    # Aplicação principal (daemon, ipc + popup)
├── setup.sh         # Script de instalação e configuração
└── README.md        # Este arquivo
```

- **Daemon**: Roda em background monitorando o clipboard
- **Popup**: Janela GTK3 com busca e navegação por teclado
- **IPC**: Socket Unix para comunicação entre daemon e popup (Single-Instance)
- **Storage**: SQLite em `~/.local/share/fast-paste/history.db`

