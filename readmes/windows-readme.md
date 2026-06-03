# 🪟 FastPaste - Guia de Instalação e Configuração no Windows

Este guia detalha como configurar, compilar e rodar o FastPaste no sistema operacional Windows.

---

## 🛠️ Compilação e Geração do Executável

Se você deseja compilar o FastPaste para gerar um executável portátil (`.exe`) independente:

1. Certifique-se de ter o Python instalado (marque a opção "Add Python to PATH" durante a instalação).
2. Abra o Prompt de Comando (CMD) ou PowerShell na pasta do projeto e execute o script de compilação:
   ```cmd
   python scripts/build.py
   ```
   *(O script irá detectar e instalar automaticamente todas as dependências necessárias, como PyQt6, pynput, pyinstaller e pillow).*
3. O executável portátil compilado será criado em:
   ```
   dist/fast-paste.exe
   ```
   Você pode mover este arquivo `.exe` para qualquer pasta e executá-lo diretamente.

---

## 🚀 Execução em Segundo Plano (Daemon)

Se você preferir rodar o FastPaste diretamente a partir do código fonte (sem compilar em `.exe`):

1. **Iniciar em segundo plano (sem janela de terminal)**:
   Use o executável `pythonw` do Windows (que roda scripts Python silenciosamente em background):
   ```cmd
   pythonw main.py run
   ```
2. **Abrir o popup do histórico**:
   Para chamar a janela de histórico instantaneamente via comando:
   ```cmd
   python main.py show
   ```
3. **Parar o processo em segundo plano**:
   Para encerrar a execução do monitor silencioso:
   ```cmd
   python main.py stop
   ```

---

## ⌨️ Atalho de Teclado no Windows

O atalho de teclado global padrão configurado para o Windows é:
**`Ctrl + Shift + V`**

Quando o monitor está ativo em segundo plano, pressionar esse atalho abrirá instantaneamente o popup sob o cursor. Use as setas do teclado para navegar e **Enter** para colar o texto automaticamente na sua aplicação ativa.

---

## 🔄 Inicialização com o Windows (Autostart)

O FastPaste pode ser configurado para iniciar automaticamente junto com o Windows através do Registro do Sistema (`HKCU\Software\Microsoft\Windows\CurrentVersion\Run`).

1. Abra a janela do popup do FastPaste.
2. Clique no ícone de engrenagem (**Configurações ⚙**) no canto superior direito.
3. Ative a opção **"Iniciar automaticamente com o sistema"** e clique em **Salvar Configurações**.
4. A partir desse momento, o FastPaste iniciará silenciosamente em segundo plano sempre que você ligar o computador e fizer login no Windows.
