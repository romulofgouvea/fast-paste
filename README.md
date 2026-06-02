# ⚡ FastPaste - Gerenciador de Clipboard moderno

O FastPaste é um gerenciador de clipboard moderno, rápido e bonito projetado para Linux (Wayland e X11), Windows e macOS. Ele armazena silenciosamente tudo o que você copia e permite pesquisar e colar instantaneamente através de um popup prático.

## ✨ Funcionalidades

- 📋 **Monitoramento Silencioso**: Salva tudo o que você copia (textos e imagens) automaticamente.
- 🔍 **Busca Dinâmica**: Comece a digitar para encontrar rapidamente itens antigos do seu histórico.
- ⌨️ **Navegação por Teclado**: Use setas para navegar e Enter para colar instantaneamente.
- 🎨 **Interface Premium**: Design escuro moderno com visual translúcido e foco automático na pesquisa.
- 💾 **Histórico Inteligente**: Fila rotativa de histórico de até 500 itens (configurável, os itens antigos são removidos quando novos entram).
- 📌 **Fixar Itens**: Fixe itens importantes para garantir que nunca sejam excluídos pelo limite de histórico.
- 🚀 **Auto-Paste**: Digita automaticamente o item selecionado na posição do seu cursor de texto.

---

## 📖 Como Usar

### 💡 Workflow do Dia a Dia

1. Copie seus textos ou capture imagens normalmente usando `Ctrl+C` ou prints de tela.
2. Abra o popup a qualquer momento usando o atalho de teclado configurado (o padrão de instalação é `Ctrl + '` ou o que você mapear nas configurações).
3. Navegue entre os itens copiados com as setas do teclado (`↑` e `↓`) ou digite palavras para buscar.
4. Pressione `Enter` para colar o item selecionado diretamente onde seu cursor de texto estiver piscando!

### ⌨️ Atalhos Disponíveis no Popup

| Tecla | Ação |
|-------|------|
| `↑` e `↓` | Navega pela lista de itens copiados |
| `Enter` | Selecionar o item e colar automaticamente |
| `Delete` | Excluir a cópia selecionada do histórico |
| `Esc` | Fecha a janela do popup |
| Digitando | Digite qualquer letra para filtrar/buscar instantaneamente |

---

## 📋 Especificações Técnicas

## 📦 Pré-requisitos

- Python 3

## 🚀 Instalação

### 🛠️ Instalação Manual (Outras distribuições Linux)

```bash
# 1. Rodar o script de setup (instala dependências, cria Systemd e configura atalho)
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

## 🛠️ Compilação & Instalação

Siga os passos gerais abaixo para compilar o FastPaste no seu sistema e, em seguida, veja as instruções específicas do seu sistema operacional.

### 1. Passos Gerais (Todas as Plataformas)

1. **Instale o Python 3** no seu sistema.
2. Abra o terminal (ou prompt de comando) na pasta do projeto e execute o script de compilação:
   ```bash
   python3 build.py
   ```
   *(O script detectará as dependências necessárias como `PyQt6`, `pynput` e `pyinstaller` e as instalará automaticamente).*

---

### 2. Instruções Específicas por Sistema

#### 🐧 Ubuntu / Debian

A compilação do Passo 1 gerará um pacote `.deb` em `dist/fast-paste_amd64.deb`.

1. Instale o pacote `.deb` gerado resolvendo dependências de clipboard (`wl-clipboard` e `xclip`) automaticamente:
   ```bash
   sudo apt install ./dist/fast-paste_amd64.deb
   ```
2. Ative e inicie o serviço daemon em segundo plano:
   ```bash
   systemctl --user enable --now fast-paste
   ```

#### 🪟 Windows

A compilação do Passo 1 gerará um executável portátil único em `dist/fast-paste.exe`.

1. Para iniciar o monitor em segundo plano no Windows (sem abrir a janela preta do terminal):
   ```cmd
   pythonw fast_paste.py run
   ```

#### 🍎 macOS

A compilação do Passo 1 gerará um pacote de aplicativo macOS em `dist/fast-paste.app`.

1. Configure o atalho global nativo usando o aplicativo **Shortcuts (Atalhos)** vinculando a tecla de sua preferência (ex: `Cmd + Shift + V`) para executar o script do shell:
   ```bash
   /usr/bin/python3 /caminho/para/fast-paste/fast_paste.py show
   ```

## 🏗️ Arquitetura

```
fast-paste/
├── fast_paste.py    # Aplicação principal (daemon, ipc + popup)
├── setup.sh         # Script de instalação e configuração
├── build.py         # Script para geração de builds locais
└── README.md        # Este arquivo
```

- **Daemon**: Roda em background monitorando o clipboard
- **Popup**: Janela PyQt6 com busca e navegação por teclado
- **IPC**: Socket Unix para comunicação entre daemon e popup (Single-Instance)
- **Storage**: SQLite na pasta temporária padrão do sistema (ex: `/tmp/fast-paste/history.db` no Linux)
