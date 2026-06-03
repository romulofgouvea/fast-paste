# ⚡ FastPaste - Gerenciador de Clipboard Moderno

O **FastPaste** é um gerenciador de área de transferência (clipboard) moderno, veloz e elegante projetado para **Linux** (compatível com Wayland e X11), **macOS** (Intel e Apple Silicon) e **Windows**. Ele roda silenciosamente em segundo plano, registrando seu histórico de cópias (textos e imagens) e permitindo que você as pesquise e cole instantaneamente em qualquer campo de texto.

---

## ✨ Funcionalidades Principais

- 📋 **Monitoramento Silencioso**: Salva tudo o que você copia (textos e imagens) automaticamente.
- 🔍 **Busca Dinâmica**: Comece a digitar letras ou partes de datas para encontrar rapidamente itens antigos.
- ⌨️ **Navegação por Teclado**: Use setas para navegar e Enter para colar instantaneamente.
- 🎨 **Interface Premium**: Design escuro moderno com visual translúcido e foco automático na barra de busca.
- 💾 **Fila de Histórico Inteligente**: Fila rotativa de histórico (limite padrão de 500 itens, totalmente configurável).
- 📌 **Fixar Itens**: Fixe itens importantes (★) para garantir que nunca sejam removidos pelo limite da fila.
- 🚀 **Auto-Paste Inteligente**: Digita automaticamente o item selecionado na posição ativa do seu cursor de texto.

---

## 📖 Como Usar

### 💡 Workflow do Dia a Dia

1. **Copie normalmente** textos ou capture imagens usando `Ctrl+C` ou print de tela.
2. **Abra o popup** a qualquer momento usando o atalho de teclado rápido (exemplo: `Ctrl + '` ou `Ctrl + Shift + V`).
3. **Busque e navegue** usando as setas do teclado (`↑` e `↓`) ou digite letras para buscar o texto.
4. **Pressione Enter** para colar o item selecionado de forma automática!

### ⌨️ Atalhos Disponíveis no Popup

| Tecla | Ação |
|-------|------|
| `↑` e `↓` | Navega pela lista de itens copiados |
| `Enter` | Selecionar o item e colar automaticamente |
| `Delete` | Excluir a cópia selecionada do histórico |
| `Esc` | Fecha a janela do popup |
| Digitando | Filtra/busca itens instantaneamente |

---

## 🚀 Guias de Instalação por Sistema Operacional

Selecione o guia específico abaixo correspondente ao seu sistema operacional para ver as instruções detalhadas de pré-requisitos, instalação, atalhos do sistema e autostart:

- [Ubuntu / Debian / Linux](readmes/ubuntu-readme.md)
- [MacOS](readmes/mac-readme.md)
- [Windows](readmes/windows-readme.md)

---

## 🏗️ Arquitetura do Projeto

O FastPaste foi estruturado em módulos independentes utilizando **Python 3** e **PyQt6**:

```
fast-paste/
├── main.py              # Ponto de entrada unificado da aplicação
├── fast_paste.py        # Script legada para retrocompatibilidade
├── configs/             # Configurações globais e banco de dados
├── core/                # Lógica de daemon, monitoramento e atalhos globais
├── screens/             # Componentes visuais (popup, bandeja do sistema, configurações)
├── assets/              # Ícones e imagens do aplicativo
└── readmes/             # Guias de instalação específicos por SO
```

- **Daemon**: Roda em background monitorando a área de transferência.
- **Popup**: Janela PyQt6 otimizada, focada em performance e ergonomia.
- **IPC (Inter-Process Communication)**: Comunicação via Socket Unix/Local que garante uma única instância ativa da janela e rápida ativação.
- **Storage**: Banco de dados leve SQLite para o histórico de cópias locais e cache seguro de imagens em disco.
