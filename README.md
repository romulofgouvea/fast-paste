# FPaste

Gerenciador de área de transferência open-source, ultra-leve e multiplataforma (Windows, macOS, Linux). Herda o poder do clássico Ditto com uma UI moderna estilo Fluent/macOS.

## Recursos

- **Captura em tempo real** de textos, links, código e imagens, com classificação automática por tipo
- **Histórico criptografado em repouso** — SQLite + SQLCipher (AES-256), chave guardada no gerenciador de credenciais do SO
- **Imagens cifradas em disco** (AES-256-GCM) fora do banco, com miniaturas decifradas sob demanda
- **Hotkey global** (`Ctrl + '` por padrão, customizável com gravador de atalhos) — a janela surge sob o cursor
- **Busca estilo Spotlight** com filtros em linguagem natural (`tipo:link`, `tipo:código`)
- **Rolagem infinita** com paginação de 20 itens e IntersectionObserver
- **Temas** claro/escuro/sistema com efeito Mica/Acrylic/Vibrancy e cor de destaque configurável
- **Teclas 1–9** para selecionar itens sem tocar no mouse

## Stack

- **Core:** Tauri v2 (Rust) — `rusqlite` + SQLCipher, `clipboard-rs`, `keyring`, `aes-gcm`
- **UI:** Vite + React + TypeScript + Tailwind CSS v4 + Zustand

---

## Como compilar

### 1. Pré-requisitos

Em qualquer sistema você precisa de:

| Ferramenta | Versão mínima | Para quê |
|---|---|---|
| [Node.js](https://nodejs.org) | 20+ | Frontend (Vite/React) |
| [Rust](https://rustup.rs) | stable | Core Tauri |
| **Perl** | 5.x | Compilar o OpenSSL vendorado do SQLCipher |

#### Windows

```powershell
# Toolchain C++ (MSVC + Windows SDK) — obrigatório para o Rust no Windows
winget install Microsoft.VisualStudio.2022.BuildTools --override "--quiet --wait --norestart --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"

# Rust (toolchain stable-msvc)
winget install Rustlang.Rustup

# Perl (exigido pelo build do OpenSSL/SQLCipher)
winget install StrawberryPerl.StrawberryPerl
```

Abra um **novo terminal** depois das instalações para o `PATH` ser atualizado. O WebView2 já vem embutido no Windows 10/11.

#### macOS

```bash
xcode-select --install          # Command Line Tools (inclui clang e perl)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

#### Linux (Debian/Ubuntu)

```bash
sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file \
  libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev perl
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### 2. Instalar dependências

```bash
git clone <url-do-repo> fpaste
cd fpaste
npm install
```

### 3. Rodar em modo desenvolvimento

```bash
npm run tauri dev
```

Compila o core Rust, sobe o Vite com hot-reload e abre o app. A **primeira compilação demora vários minutos** (baixa ~500 crates e compila o OpenSSL + SQLCipher do zero); as seguintes são incrementais e rápidas.

O app inicia oculto na bandeja do sistema — pressione **`Ctrl + '`** para abrir a janela, ou use o menu do ícone na bandeja.

### 4. Build de produção

```bash
npm run tauri build
```

Os artefatos saem em `src-tauri/target/release/`:

- **Windows:** `fpaste.exe` + instaladores em `bundle/msi/` e `bundle/nsis/`
- **macOS:** `bundle/macos/FPaste.app` e `bundle/dmg/`
- **Linux:** `bundle/deb/`, `bundle/rpm/` e `bundle/appimage/`

### 5. Rodar os testes do core

```bash
cd src-tauri
cargo test
```

Cobrem classificação de conteúdo (texto/link/código), deduplicação, paginação e o round-trip da criptografia AES-256-GCM.

### Erros comuns de build

| Erro | Causa | Solução |
|---|---|---|
| `Command 'perl' not found` ao compilar `openssl-sys` | Perl ausente | Instale Strawberry Perl (Win) ou o pacote `perl` do seu SO e abra novo terminal |
| `linker 'link.exe' not found` (Windows) | VS Build Tools sem o workload C++ | Reinstale com `--add Microsoft.VisualStudio.Workload.VCTools` |
| `rustc: command not found` | PATH desatualizado | Abra um novo terminal ou rode `. "$HOME/.cargo/env"` |
| Erro de `webkit2gtk` (Linux) | Dependências de sistema faltando | Instale os pacotes da seção Linux acima |

---

## Releases automáticas

O workflow `.github/workflows/release.yml` builda o app em Windows, macOS e Linux e publica os instaladores (`.msi`/`.exe`, `.dmg`, `.deb`/`.rpm`/`.AppImage`) direto na release do GitHub sempre que uma tag `v*` é empurrada:

```bash
git tag v0.1.0
git push origin v0.1.0
```

Mantenha a versão em `package.json` e `src-tauri/tauri.conf.json` alinhada com a tag antes de publicá-la.

---

## Dados

O banco `fpaste.db` (cifrado com SQLCipher) e a pasta de mídia cifrada ficam em:

- **Windows:** `%APPDATA%\fpaste\data\`
- **macOS:** `~/Library/Application Support/fpaste/data/`
- **Linux:** `~/.local/share/fpaste/data/`

A chave de criptografia é gerada no primeiro boot e guardada no **Windows Credential Manager**, **macOS Keychain** ou **Secret Service** (Linux) — nunca em arquivo.
