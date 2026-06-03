import os
import sys
import subprocess
import shutil
import io

# Force UTF-8 encoding on Windows to prevent UnicodeEncodeError with emojis/box-drawing characters
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

def run_command(command, shell=False):
    print(f"Executing: {' '.join(command) if isinstance(command, list) else command}")
    result = subprocess.run(command, shell=shell)
    if result.returncode != 0:
        print(f"Error executing command: {command}")
        sys.exit(result.returncode)

def main():
    print("=== FastPaste Builder ===")
    
    # 1. Verify and install dependencies
    deps = {
        "PyQt6": "PyQt6",
        "pynput": "pynput",
        "PyInstaller": "pyinstaller"
    }
    missing_packages = []
    for module, package in deps.items():
        try:
            __import__(module)
        except ImportError:
            missing_packages.append(package)
            
    if missing_packages:
        print(f"Installing missing dependencies: {', '.join(missing_packages)}...")
        installed = False
        
        # Try installing through python module and standalone pip binaries
        for cmd_base in [[sys.executable, "-m", "pip"], ["pip3"], ["pip"]]:
            # Skip if command isn't available
            if len(cmd_base) == 1 and not shutil.which(cmd_base[0]):
                continue
                
            # 1. Try standard installation
            try:
                subprocess.run(cmd_base + ["install"] + missing_packages, check=True)
                installed = True
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 2. Try with --break-system-packages (workaround for PEP 668 in newer Ubuntu/Debian)
                try:
                    subprocess.run(cmd_base + ["install"] + missing_packages + ["--break-system-packages"], check=True)
                    installed = True
                    break
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass
        
        if not installed:
            print(f"\n[Error] pip is not available or failed to install dependencies: {missing_packages}")
            if sys.platform.startswith("win"):
                print("[Info] Please run: python -m ensurepip")
            elif sys.platform.startswith("darwin"):
                print("[Info] Please run: python3 -m ensurepip")
            else:
                print("[Info] Please install pip using your package manager:")
                print("   sudo apt update && sudo apt install python3-pip")
            sys.exit(1)
    else:
        print("[OK] All dependencies are already installed (PyQt6, pynput, pyinstaller).")

    # Generate .ico for Windows if Pillow is available and fast_paste.png exists
    if os.path.exists("fast_paste.png"):
        ico_path = "fast_paste.ico"
        if not os.path.exists(ico_path):
            try:
                from PIL import Image
                img = Image.open("fast_paste.png")
                img.save(ico_path, format="ICO", sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])
                print("[OK] Generated fast_paste.ico for Windows.")
            except Exception as e:
                pass

    # 2. Define platform-specific options
    name = "fast-paste"
    pyinstaller_args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean"]
    
    # Check OS
    if sys.platform.startswith("win"):
        print("[Info] OS detected: Windows")
        pyinstaller_args.extend([
            "--onefile",
            "--windowed",
            f"--name={name}",
        ])
        if os.path.exists("fast_paste.ico"):
            pyinstaller_args.append("--icon=fast_paste.ico")
        pyinstaller_args.append("fast_paste.py")
    elif sys.platform.startswith("darwin"):
        print("[Info] OS detected: macOS")
        pyinstaller_args.extend([
            "--windowed",
            f"--name={name}",
        ])
        if os.path.exists("fast_paste.png"):
            pyinstaller_args.append("--icon=fast_paste.png")
        pyinstaller_args.append("fast_paste.py")
    else:
        print("[Info] OS detected: Linux")
        pyinstaller_args.extend([
            "--onefile",
            "--windowed",
            f"--name={name}",
            "fast_paste.py"
        ])

    # 3. Clean previous build artifacts
    for folder in ["build", "dist"]:
        if os.path.exists(folder):
            print(f"Cleaning existing '{folder}' directory...")
            shutil.rmtree(folder)

    # 4. Run PyInstaller
    print("Running PyInstaller...")
    run_command(pyinstaller_args)
    
    print("\n==========================================")
    print("Build process completed successfully!")
    
    if sys.platform.startswith("darwin"):
        print(f"Output application: dist/{name}.app")
        print("To distribute, you can zip the .app folder.")
    elif sys.platform.startswith("win"):
        print(f"Output executable: dist/{name}.exe")
    else:
        print(f"Output executable: dist/{name}")
        print("To run it, make sure it has execution permissions (chmod +x).")
        
        # 5. Package into .deb on Linux if dpkg-deb is available
        dpkg_deb = shutil.which("dpkg-deb")
        if dpkg_deb:
            print("\n[Package] Generating .deb package...")
            try:
                deb_dir = "build/deb_package"
                if os.path.exists(deb_dir):
                    shutil.rmtree(deb_dir)
                
                # Create structure
                os.makedirs(f"{deb_dir}/DEBIAN", exist_ok=True)
                os.makedirs(f"{deb_dir}/usr/bin", exist_ok=True)
                os.makedirs(f"{deb_dir}/usr/share/applications", exist_ok=True)
                os.makedirs(f"{deb_dir}/usr/share/metainfo", exist_ok=True)
                os.makedirs(f"{deb_dir}/usr/lib/systemd/user", exist_ok=True)
                
                # Copy binary
                shutil.copy2(f"dist/{name}", f"{deb_dir}/usr/bin/fast-paste")
                os.chmod(f"{deb_dir}/usr/bin/fast-paste", 0o755)
                
                # Copy custom icon if exists
                if os.path.exists("fast_paste.png"):
                    os.makedirs(f"{deb_dir}/usr/share/icons/hicolor/512x512/apps", exist_ok=True)
                    shutil.copy2("fast_paste.png", f"{deb_dir}/usr/share/icons/hicolor/512x512/apps/fast-paste.png")
                
                # Create desktop entry
                desktop_content = """[Desktop Entry]
Name=Fast Paste Clipboard Manager
Comment=Clipboard History Manager
Exec=/usr/bin/fast-paste show
Icon=fast-paste
Terminal=false
Type=Application
Categories=Utility;
"""
                with open(f"{deb_dir}/usr/share/applications/fast-paste.desktop", "w", encoding="utf-8") as f:
                    f.write(desktop_content)
                
                # Create AppStream metainfo XML file (improves App Center screen metadata)
                metainfo_content = """<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>org.fast_paste.fast-paste</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>MIT</project_license>
  <name>Fast Paste Clipboard Manager</name>
  <summary>Modern and lightweight clipboard manager for Linux</summary>
  <description>
    <p>
      O Fast Paste Clipboard Manager é um gerenciador de área de transferência moderno, rápido e bonito projetado para Linux (Wayland e X11). Ele armazena silenciosamente tudo o que você copia e permite pesquisar e colar instantaneamente através de um popup prático.
    </p>
    <p>Principais Funcionalidades:</p>
    <ul>
      <li>Monitoramento Silencioso: Salva tudo o que você copia (textos e imagens) automaticamente.</li>
      <li>Busca Dinâmica: Comece a digitar para encontrar rapidamente itens antigos do seu histórico.</li>
      <li>Navegação por Teclado: Use setas para navegar e Enter para colar instantaneamente.</li>
      <li>Interface Premium: Design escuro moderno com visual translúcido e foco automático na pesquisa.</li>
      <li>Histórico Inteligente: Fila rotativa de histórico de até 500 itens (configurável, os itens antigos são removidos quando novos entram).</li>
      <li>Fixar Itens: Fixe itens importantes para garantir que nunca sejam excluídos pelo limite de histórico.</li>
      <li>Auto-Paste: Digita automaticamente o item selecionado na posição do seu cursor de texto.</li>
    </ul>
  </description>
  <launchable type="desktop-id">fast-paste.desktop</launchable>
  <developer_name>Stevanini</developer_name>
  <url type="homepage">https://github.com/fast-paste/fast-paste</url>
  <url type="bugtracker">https://github.com/fast-paste/fast-paste/issues</url>
  <content_rating type="oars-1.1"/>
</component>
"""
                with open(f"{deb_dir}/usr/share/metainfo/org.fast_paste.fast-paste.metainfo.xml", "w", encoding="utf-8") as f:
                    f.write(metainfo_content)

                # Create systemd user service file
                systemd_service = """[Unit]
Description=FastPaste Clipboard Manager Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/fast-paste run
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
                with open(f"{deb_dir}/usr/lib/systemd/user/fast-paste.service", "w", encoding="utf-8") as f:
                    f.write(systemd_service)
                
                # Get architecture
                arch = "amd64"
                try:
                    arch = subprocess.check_output(["dpkg", "--print-architecture"]).decode("utf-8").strip()
                except Exception:
                    pass
                
                # Create control file with dependencies (PEP 668/Wayland setup)
                control_content = f"""Package: fast-paste-clipboard-manager
Version: 1.0.0
Section: utils
Priority: optional
Architecture: {arch}
Maintainer: Stevanini <contato@stevanini.com.br>
Depends: wl-clipboard, xclip, wtype, xdotool
Homepage: https://github.com/fast-paste/fast-paste
Description: Fast Paste Clipboard Manager
 Standalone clipboard manager for Linux (Wayland and X11) with PyQt6.
"""
                with open(f"{deb_dir}/DEBIAN/control", "w", encoding="utf-8") as f:
                    f.write(control_content)
                
                # Build DEB
                run_command(["dpkg-deb", "--build", deb_dir, f"dist/fast-paste_{arch}.deb"])
                print(f"[OK] Generated deb package: dist/fast-paste_{arch}.deb")
                print("\n[Info] To install the deb package with dependencies:")
                print(f"   sudo apt install ./dist/fast-paste_{arch}.deb")
                print("[Info] To enable the background service:")
                print("   systemctl --user enable --now fast-paste")
            except Exception as e:
                print(f"[Warning] Failed to generate .deb package: {e}")
                
    print("==========================================")

if __name__ == "__main__":
    main()
