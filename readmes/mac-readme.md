# 🍎 FastPaste - Guia de Instalação e Configuração no macOS

Este guia detalha como compilar, instalar e autorizar o FastPaste no macOS. 

Devido às restrições de segurança do macOS (como o Gatekeeper e o Sandbox do sistema), é importante seguir estes passos para garantir que o monitoramento em segundo plano e a colagem automática funcionem corretamente.

---

## 🛠️ Compilação e Geração do Executável

Se você deseja compilar o FastPaste localmente na sua máquina para gerar o arquivo `.app` otimizado para o seu hardware (Intel ou Apple Silicon M1/M2/M3):

1. Certifique-se de que possui o Python 3 instalado.
2. Instale os pacotes de compilação e dependências:
   ```bash
   pip install PyQt6 pynput pyinstaller
   ```
3. Execute o script de build na pasta raiz do repositório:
   ```bash
   python3 scripts/build.py
   ```
4. O build gerará o aplicativo empacotado em:
   ```
   dist/fast-paste.app
   ```

---

## 🔑 Permissões e Segurança do macOS (Passo Importante)

No macOS, aplicativos executados fora da App Store (e sem assinatura paga da Apple Developer) são bloqueados ou podem fechar inesperadamente se tentarem simular teclas (`pynput`) sem permissões de Acessibilidade.

Siga os passos abaixo para liberar o aplicativo:

### 1. Remover a Marca de Quarentena (Gatekeeper)
Caso você baixe uma versão pré-compilada em zip ou mova o aplicativo entre pastas, o macOS marca o arquivo como "quarentena". No terminal, remova essa marca executando:
```bash
xattr -cr /caminho/para/dist/fast-paste.app
```

### 2. Assinar o Binário Localmente (Ad-hoc signing)
Em Macs com chip Apple Silicon (M1, M2, M3, etc.), qualquer código nativo não assinado causa um travamento imediato (`SIGSEGV` em PAC / `__CFCheckCFInfoPACSignature`).
Assine o aplicativo localmente de forma gratuita executando:
```bash
codesign --force --deep --sign - /caminho/para/dist/fast-paste.app
```

### 3. Conceder Permissões de Acessibilidade
Para que o FastPaste possa simular o atalho `Cmd+V` para colar os textos automaticamente para você:
1. Vá em **Ajustes do Sistema** → **Privacidade e Segurança** → **Acessibilidade**.
2. Clique no ícone de `+` e adicione o seu `fast-paste.app`.
3. Certifique-se de que a chave ao lado dele está ativada.
*(Se você estiver executando o código fonte diretamente no terminal via `python3`, você precisará conceder essa permissão ao seu aplicativo de Terminal, ex: Terminal.app ou iTerm.app).*

---

## ⌨️ Atalhos de Teclado e Popup

### Como abrir o Popup de histórico no Mac
O atalho padrão global para abrir a janela do popup no Mac é **`Ctrl + Shift + V`**. Ele rodará em segundo plano graças à biblioteca `pynput`.

#### Alternativa: Criar um Atalho de Teclado Nativo do macOS
Caso queira desativar o monitoramento de atalho em Python e usar o sistema nativo da Apple (mais rápido e seguro):
1. Abra o aplicativo **Atalhos (Shortcuts)** nativo do macOS.
2. Crie um novo atalho do tipo "Executar Script de Shell".
3. Coloque o comando para abrir o popup:
   ```bash
   # Se estiver usando o executável compilado:
   /caminho/para/fast-paste.app/Contents/MacOS/fast-paste show
   
   # Ou se estiver usando o código fonte:
   /usr/bin/python3 /caminho/para/fast-paste/main.py show
   ```
4. Na barra lateral direita do aplicativo Atalhos, adicione um atalho de teclado rápido de sua preferência (exemplo: `Cmd + Shift + V` ou `Cmd + '`).

---

## 🔄 Inicialização com o Sistema (Autostart)

O FastPaste suporta inicialização automática no login do macOS usando um `LaunchAgent` do sistema.
- Para ativar o autostart, abra o popup do FastPaste, clique no botão de **Configurações (⚙)** e ative a chave **"Iniciar automaticamente com o sistema"**.
- Isso criará um arquivo `com.fastpaste.autostart.plist` em `~/Library/LaunchAgents/` que iniciará o monitor em background em todos os logins.
