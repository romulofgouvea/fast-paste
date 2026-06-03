# 🐧 FPaste - Guia de Instalação e Configuração no Ubuntu / Debian / Linux

Este guia detalha como instalar, configurar e rodar o FPaste em sistemas baseados em Linux, abrangendo ambientes X11 e Wayland (como o Ubuntu padrão).

---

## 🚀 Instalação

Você pode instalar o FPaste no Linux de duas formas: usando o instalador automatizado (`setup.py`) ou gerando/instalando o pacote `.deb`.

### Método 1: Usando o Instalador Automatizado (`setup.py`)
O instalador automatizado irá instalar as dependências do sistema, instalar os pacotes Python necessários, configurar o daemon como um serviço de usuário do Systemd e registrar o atalho global no GNOME.

1. Clone ou baixe este repositório.
2. Abra o terminal na pasta do projeto e execute:
   ```bash
   python3 scripts/setup.py
   ```
3. O serviço será ativado e iniciará automaticamente. Você pode verificar seu status com:
   ```bash
   systemctl --user status fpaste
   ```

### Método 2: Instalando via Pacote `.deb` (Recomendado para Ubuntu/Debian)
Você pode gerar e instalar um pacote `.deb` nativo para facilitar o gerenciamento do aplicativo.

1. Gere o pacote executando o script de compilação:
   ```bash
   python3 scripts/build.py
   ```
2. O pacote `.deb` será gerado na pasta `dist/` (ex: `dist/fpaste_amd64.deb`). Instale-o com:
   ```bash
   sudo apt install ./dist/fpaste_amd64.deb
   ```
3. Ative e inicie o serviço do usuário para monitoramento em segundo plano:
   ```bash
   systemctl --user enable --now fpaste
   ```

---

## ⌨️ Atalhos de Teclado no Linux

### Wayland vs X11
- **X11 / XWayland**: O atalho global (padrão `Ctrl + Shift + V` ou configurado no app) funciona automaticamente em segundo plano através do monitoramento nativo.
- **Wayland (Ubuntu padrão)**: Por motivos de segurança, o Wayland restringe o acesso direto ao teclado em segundo plano. Por isso, a inicialização cria automaticamente um atalho de teclado do sistema.
  - O atalho padrão configurado é **`Ctrl + '`** (Ctrl + apóstrofo).
  - Se você usa um ambiente que não seja o GNOME (ex: KDE, XFCE), configure manualmente o atalho nas Configurações de Atalhos do Sistema para executar o seguinte comando:
    ```bash
    fpaste show
    ```
    *(Ou `python3 /caminho/para/main.py show` se rodando a partir do código fonte).*

---

## 🛠️ Comandos Úteis do Terminal

Se estiver rodando a partir do código fonte (sem instalar o pacote `.deb`), você pode interagir com o daemon usando os seguintes comandos:

```bash
python3 main.py run      # Inicia o daemon com ícone de bandeja (se X11) e servidor IPC no terminal ativo
python3 main.py start    # Inicia o daemon em segundo plano (em background)
python3 main.py stop     # Para o daemon em segundo plano
python3 main.py show     # Abre o popup do histórico de transferência
python3 main.py status   # Verifica se o daemon está em execução
python3 main.py clear    # Limpa todo o histórico de cópias não fixadas
```

Se tiver instalado via pacote `.deb`, os comandos acima podem ser chamados diretamente usando o executável `fpaste`:
```bash
fpaste show
fpaste status
fpaste clear
```

---

## 🔄 Gerenciamento do Serviço (Systemd)

O serviço do FPaste roda sob a sessão do seu próprio usuário. Você pode gerenciá-lo com os seguintes comandos:

```bash
# Verificar se o daemon está rodando
systemctl --user status fpaste

# Reiniciar o serviço
systemctl --user restart fpaste

# Parar o serviço
systemctl --user stop fpaste

# Desativar o autostart
systemctl --user disable fpaste
```
