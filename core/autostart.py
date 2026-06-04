import os
import sys
import shutil
import subprocess
from configs.config import APP_NAME

def get_executable_command():
    if getattr(sys, 'frozen', False):
        exe = os.path.abspath(sys.executable)
        if sys.platform.startswith("win") or sys.platform.startswith("darwin"):
            return [exe]
        else:
            return [exe, "run"]
    else:
        script_path = os.path.abspath(sys.argv[0])
        # If running from main.py script
        if script_path.endswith("main.py"):
            return [sys.executable, script_path, "run"]
        else:
            # Fallback to current folder script
            fallback = os.path.join(os.path.dirname(script_path), "main.py")
            if os.path.exists(fallback):
                return [sys.executable, fallback, "run"]
            return [sys.executable, script_path, "run"]

def get_background_command():
    cmd = get_executable_command()
    if cmd and cmd[-1] == "run":
        return cmd
    return [*cmd, "run"]

def get_macos_launch_agent_paths():
    app_lower = APP_NAME.lower()
    agents_dir = os.path.expanduser("~/Library/LaunchAgents")
    canonical_path = os.path.join(agents_dir, f"com.{app_lower}.autostart.plist")
    legacy_path = os.path.join(agents_dir, f"com.{app_lower}.daemon.plist")
    return canonical_path, legacy_path

def is_autostart_enabled():
    app_lower = APP_NAME.lower()
    if sys.platform.startswith("win"):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False
            
    elif sys.platform.startswith("linux"):
        # Check systemd first
        service_file = os.path.expanduser(f"~/.config/systemd/user/{app_lower}.service")
        if os.path.exists(service_file):
            try:
                res = subprocess.run(["systemctl", "--user", "is-enabled", f"{app_lower}.service"], capture_output=True, text=True)
                if res.stdout.strip() == "enabled":
                    return True
            except Exception:
                pass
        
        autostart_file = os.path.expanduser(f"~/.config/autostart/{app_lower}.desktop")
        return os.path.exists(autostart_file)
        
    elif sys.platform.startswith("darwin"):
        plist_file, legacy_plist_file = get_macos_launch_agent_paths()
        return os.path.exists(plist_file) or os.path.exists(legacy_plist_file)
        
    return False

def enable_autostart():
    cmd = get_background_command()
    app_lower = APP_NAME.lower()
    
    if sys.platform.startswith("win"):
        try:
            import winreg
            # Quote path if it contains spaces
            cmd_str = f'"{cmd[0]}"'
            if len(cmd) > 1:
                cmd_str += " " + " ".join(cmd[1:])
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd_str)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[Autostart] Error enabling on Windows: {e}")
            return False
            
    elif sys.platform.startswith("linux"):
        # Check systemd first
        service_file = os.path.expanduser(f"~/.config/systemd/user/{app_lower}.service")
        if os.path.exists(service_file):
            try:
                subprocess.run(["systemctl", "--user", "enable", f"{app_lower}.service"], check=True)
                subprocess.run(["systemctl", "--user", "start", f"{app_lower}.service"], check=True)
                return True
            except Exception as e:
                print(f"[Autostart] Error enabling systemd service: {e}")
                # Fallback to desktop entry
        
        try:
            cmd_str = " ".join(cmd)
            desktop_content = f"""[Desktop Entry]
Type=Application
Name={APP_NAME}
Comment=Start {APP_NAME} Clipboard Manager on login
Exec={cmd_str}
Icon=edit-paste
Terminal=false
Categories=Utility;
"""
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            with open(os.path.join(autostart_dir, f"{app_lower}.desktop"), "w", encoding="utf-8") as f:
                f.write(desktop_content)
            return True
        except Exception as e:
            print(f"[Autostart] Error enabling on Linux: {e}")
            return False
            
    elif sys.platform.startswith("darwin"):
        try:
            plist_file, legacy_plist_file = get_macos_launch_agent_paths()
            if os.path.exists(legacy_plist_file):
                subprocess.run(["launchctl", "unload", legacy_plist_file], check=False)
                os.remove(legacy_plist_file)

            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.{app_lower}.autostart</string>
    <key>ProgramArguments</key>
    <array>
        {"".join(f"<string>{arg}</string>" for arg in cmd)}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
            os.makedirs(os.path.dirname(plist_file), exist_ok=True)
            with open(plist_file, "w", encoding="utf-8") as f:
                f.write(plist_content)
            return True
        except Exception as e:
            print(f"[Autostart] Error enabling on macOS: {e}")
            return False
            
    return False

def disable_autostart():
    app_lower = APP_NAME.lower()
    if sys.platform.startswith("win"):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_WRITE)
            winreg.DeleteValue(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except Exception:
            return False
            
    elif sys.platform.startswith("linux"):
        systemd_disabled = False
        service_file = os.path.expanduser(f"~/.config/systemd/user/{app_lower}.service")
        if os.path.exists(service_file):
            try:
                subprocess.run(["systemctl", "--user", "disable", f"{app_lower}.service"], check=True)
                subprocess.run(["systemctl", "--user", "stop", f"{app_lower}.service"], check=True)
                systemd_disabled = True
            except Exception as e:
                print(f"[Autostart] Error disabling systemd service: {e}")
        
        try:
            autostart_file = os.path.expanduser(f"~/.config/autostart/{app_lower}.desktop")
            if os.path.exists(autostart_file):
                os.remove(autostart_file)
            return True
        except Exception as e:
            print(f"[Autostart] Error disabling desktop entry on Linux: {e}")
            return systemd_disabled
            
    elif sys.platform.startswith("darwin"):
        try:
            plist_file, legacy_plist_file = get_macos_launch_agent_paths()
            if os.path.exists(plist_file):
                subprocess.run(["launchctl", "unload", plist_file], check=False)
                os.remove(plist_file)
            if os.path.exists(legacy_plist_file):
                subprocess.run(["launchctl", "unload", legacy_plist_file], check=False)
                os.remove(legacy_plist_file)
            return True
        except Exception as e:
            print(f"[Autostart] Error disabling on macOS: {e}")
            return False
            
    return False
