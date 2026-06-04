#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import platform
import subprocess
import shutil

# Adiciona o diretório raiz ao path para poder importar configs.config antes do pip
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from configs.config import APP_NAME

def run_cmd(args):
    try:
        res = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        return False, "", str(e)

def install_pip_requirements():
    print("[1/4] Instalando dependências do Python...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    req_file = os.path.join(base_dir, "requirements.txt")
    
    if not os.path.exists(req_file):
        print(f"  ⚠ requirements.txt não encontrado em {req_file}")
        return

    # Try different pip combinations
    commands = [
        [sys.executable, "-m", "pip", "install", "-r", req_file, "--break-system-packages"],
        [sys.executable, "-m", "pip", "install", "-r", req_file],
        ["pip3", "install", "-r", req_file, "--break-system-packages"],
        ["pip3", "install", "-r", req_file],
        ["pip", "install", "-r", req_file]
    ]
    
    success = False
    for cmd in commands:
        ok, out, err = run_cmd(cmd)
        if ok:
            success = True
            break
            
    if success:
        print("  ✅ Dependências do Python instaladas com sucesso!")
    else:
        print("  ⚠ Aviso: Não foi possível instalar todas as dependências do Python via pip. Certifique-se de ter PyQt6 e pynput instalados.")

def setup_linux():
    app_lower = APP_NAME.lower()
    print(f"\n🐧 Configurando ambiente Linux para {APP_NAME}...")
    
    # Install system deps
    if shutil.which("apt-get"):
        print("  Instalando pacotes do sistema (wl-clipboard, wtype, xdotool)...")
        # Run non-interactively, ignore error
        subprocess.run(["sudo", "apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "apt-get", "install", "-y", "wl-clipboard", "wtype", "xdotool"])
        print("  ✅ Dependências do sistema instaladas!")
    else:
        print("  ⚠ Gerenciador APT não detectado. Certifique-se de instalar wl-clipboard, wtype/xdotool manualmente.")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(base_dir, "main.py")
    
    # Set permissions
    run_cmd(["chmod", "+x", main_py])
    
    # Create desktop entry
    apps_dir = os.path.expanduser("~/.local/share/applications")
    os.makedirs(apps_dir, exist_ok=True)
    desktop_file = os.path.join(apps_dir, f"{app_lower}.desktop")
    
    desktop_content = f"""[Desktop Entry]
Name={APP_NAME}
Comment=Clipboard History Manager
Exec=python3 {main_py} show
Icon=edit-paste
Terminal=false
Type=Application
Categories=Utility;
"""
    with open(desktop_file, "w", encoding="utf-8") as f:
        f.write(desktop_content)
    print(f"  ✅ Atalho {app_lower}.desktop criado!")

    # Configure GNOME keyboard shortcut
    desktop_env = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "gnome" in desktop_env or "ubuntu" in desktop_env:
        print("  Configurando atalho no GNOME...")
        # Get current bindings
        ok, current, _ = run_cmd(["gsettings", "get", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings"])
        current = current.strip() if ok else "[]"
        
        path = f"/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings/{app_lower}/"
        if app_lower not in current:
            if current in ["[]", "@as []"]:
                new_bindings = f"['{path}']"
            else:
                new_bindings = current[:-1] + f", '{path}']"
            run_cmd(["gsettings", "set", "org.gnome.settings-daemon.plugins.media-keys", "custom-keybindings", new_bindings])

        schema = "org.gnome.settings-daemon.plugins.media-keys.custom-keybinding"
        run_cmd(["gsettings", "set", f"{schema}:{path}", "name", f"{APP_NAME} - Show Clipboard"])
        run_cmd(["gsettings", "set", f"{schema}:{path}", "command", f"python3 {main_py} show"])
        run_cmd(["gsettings", "set", f"{schema}:{path}", "binding", "<Ctrl>apostrophe"])
        print("  ✅ Atalho de teclado configurado: Ctrl + '")
    else:
        print("  ℹ Para o seu ambiente Desktop, configure manualmente o comando:")
        print(f"     python3 {main_py} show")
        print("     Atalho sugerido: Ctrl + '")

    # Configure systemd user service
    systemd_dir = os.path.expanduser("~/.config/systemd/user")
    os.makedirs(systemd_dir, exist_ok=True)
    service_file = os.path.join(systemd_dir, f"{app_lower}.service")
    
    # Remove old autostart files if present
    for old_name in ["fast-paste.desktop", "fast-paste.service", "fast-paste-daemon.desktop"]:
        old_path = os.path.expanduser(f"~/.config/autostart/{old_name}")
        if os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    service_content = f"""[Unit]
Description={APP_NAME} Clipboard Manager Daemon
After=graphical-session.target

[Service]
Type=simple
ExecStart={sys.executable} {main_py} run
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""
    with open(service_file, "w", encoding="utf-8") as f:
        f.write(service_content)
        
    print(f"  Configurando serviço systemd do usuário para {APP_NAME}...")
    run_cmd(["systemctl", "--user", "import-environment", "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"])
    run_cmd(["systemctl", "--user", "daemon-reload"])
    run_cmd(["systemctl", "--user", "enable", f"{app_lower}.service"])
    run_cmd(["systemctl", "--user", "restart", f"{app_lower}.service"])
    print(f"  ✅ Serviço de monitoramento do clipboard iniciado via systemd!")

def setup_macos():
    app_lower = APP_NAME.lower()
    print(f"\n🍎 Configurando ambiente macOS para {APP_NAME}...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(base_dir, "main.py")
    
    # Create Launch Agent directory
    agents_dir = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(agents_dir, exist_ok=True)
    plist_file = os.path.join(agents_dir, f"com.{app_lower}.autostart.plist")
    legacy_plist_file = os.path.join(agents_dir, f"com.{app_lower}.daemon.plist")

    for path in [legacy_plist_file]:
        if os.path.exists(path):
            try:
                run_cmd(["launchctl", "unload", path])
                os.remove(path)
            except Exception:
                pass
    
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{app_lower}.autostart</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{main_py}</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{os.path.expanduser(f"~/Library/Logs/{app_lower}.log")}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.expanduser(f"~/Library/Logs/{app_lower}.err")}</string>
</dict>
</plist>
"""
    with open(plist_file, "w", encoding="utf-8") as f:
        f.write(plist_content)
        
    # Load the agent
    run_cmd(["launchctl", "unload", plist_file])
    run_cmd(["launchctl", "unload", legacy_plist_file])
    ok, _, err = run_cmd(["launchctl", "load", plist_file])
    
    if ok:
        print("  ✅ Serviço de segundo plano (Launch Agent) registrado e iniciado!")
    else:
        print(f"  ⚠ Aviso ao carregar serviço: {err}")
        
    print(f"\n⚠️ IMPORTANTE NO macOS:")
    print(f"  Como o {APP_NAME} monitora o teclado globalmente para abrir o popup,")
    print("  você DEVE conceder permissão de 'Acessibilidade' (Accessibility)")
    print("  ao seu Terminal ou Python nas Configurações de Segurança e Privacidade do macOS.")

def setup_windows():
    print(f"\n🪟 Configurando ambiente Windows para {APP_NAME}...")
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py = os.path.join(base_dir, "main.py")
    
    # Determine pythonw executable to run gui without console
    pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")
    if not os.path.exists(pythonw_exe):
        pythonw_exe = sys.executable

    # Startup Folder
    startup_dir = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    if not os.path.exists(startup_dir):
        print("  ⚠ Pasta de Inicialização do Windows não encontrada.")
        return
        
    lnk_path = os.path.join(startup_dir, f"{APP_NAME}.lnk")
    
    # PowerShell command to create shortcut cleanly
    ps_command = (
        f"$WshShell = New-Object -ComObject WScript.Shell; "
        f"$Shortcut = $WshShell.CreateShortcut('{lnk_path}'); "
        f"$Shortcut.TargetPath = '{pythonw_exe}'; "
        f"$Shortcut.Arguments = '\"{main_py}\" run'; "
        f"$Shortcut.WorkingDirectory = '{base_dir}'; "
        f"$Shortcut.Description = '{APP_NAME} Clipboard Manager'; "
        f"$Shortcut.Save()"
    )
    
    ok, _, err = run_cmd(["powershell", "-Command", ps_command])
    if ok:
        print("  ✅ Atalho de inicialização criado na pasta Startup!")
        # Start daemon immediately
        subprocess.Popen([pythonw_exe, main_py, "run"], cwd=base_dir, close_fds=True)
        print(f"  ✅ Daemon do {APP_NAME} iniciado em segundo plano!")
    else:
        print(f"  ⚠ Falha ao criar atalho na Inicialização: {err}")

def main():
    print("==================================================")
    print(f"⚡ Instalando e Configurando o {APP_NAME}...")
    print("==================================================")
    
    # 1. Install dependencies
    install_pip_requirements()
    
    # 2. OS-specific setup
    os_name = platform.system()
    if os_name == "Linux":
        setup_linux()
    elif os_name == "Darwin":
        setup_macos()
    elif os_name == "Windows":
        setup_windows()
    else:
        print(f"⚠ Sistema operacional '{os_name}' não suportado pelo instalador automático.")
        
    print("\n==================================================")
    print("🎉 Instalação concluída com sucesso!")
    print("==================================================")

if __name__ == "__main__":
    main()
