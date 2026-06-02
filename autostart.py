import os
import sys
import shutil
import subprocess

def get_executable_command():
    if getattr(sys, 'frozen', False):
        exe = os.path.abspath(sys.executable)
        if sys.platform.startswith("win") or sys.platform.startswith("darwin"):
            return [exe]
        else:
            return [exe, "run"]
    else:
        script_path = os.path.abspath(sys.argv[0])
        # If running from fast_paste.py script
        if script_path.endswith("fast_paste.py"):
            return [sys.executable, script_path, "run"]
        else:
            # Fallback to current folder script
            fallback = os.path.join(os.path.dirname(script_path), "fast_paste.py")
            if os.path.exists(fallback):
                return [sys.executable, fallback, "run"]
            return [sys.executable, script_path, "run"]

def is_autostart_enabled():
    if sys.platform.startswith("win"):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, "FastPaste")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False
            
    elif sys.platform.startswith("linux"):
        # Check systemd first
        service_file = os.path.expanduser("~/.config/systemd/user/fast-paste.service")
        if os.path.exists(service_file):
            try:
                res = subprocess.run(["systemctl", "--user", "is-enabled", "fast-paste.service"], capture_output=True, text=True)
                if res.stdout.strip() == "enabled":
                    return True
            except Exception:
                pass
        
        autostart_file = os.path.expanduser("~/.config/autostart/fast-paste.desktop")
        return os.path.exists(autostart_file)
        
    elif sys.platform.startswith("darwin"):
        plist_file = os.path.expanduser("~/Library/LaunchAgents/com.fastpaste.autostart.plist")
        return os.path.exists(plist_file)
        
    return False

def enable_autostart():
    cmd = get_executable_command()
    
    if sys.platform.startswith("win"):
        try:
            import winreg
            # Quote path if it contains spaces
            cmd_str = f'"{cmd[0]}"'
            if len(cmd) > 1:
                cmd_str += " " + " ".join(cmd[1:])
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "FastPaste", 0, winreg.REG_SZ, cmd_str)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[Autostart] Error enabling on Windows: {e}")
            return False
            
    elif sys.platform.startswith("linux"):
        # Check systemd first
        service_file = os.path.expanduser("~/.config/systemd/user/fast-paste.service")
        if os.path.exists(service_file):
            try:
                subprocess.run(["systemctl", "--user", "enable", "fast-paste.service"], check=True)
                subprocess.run(["systemctl", "--user", "start", "fast-paste.service"], check=True)
                return True
            except Exception as e:
                print(f"[Autostart] Error enabling systemd service: {e}")
                # Fallback to desktop entry
        
        try:
            cmd_str = " ".join(cmd)
            desktop_content = f"""[Desktop Entry]
Type=Application
Name=FastPaste
Comment=Start FastPaste Clipboard Manager on login
Exec={cmd_str}
Icon=edit-paste
Terminal=false
Categories=Utility;
"""
            autostart_dir = os.path.expanduser("~/.config/autostart")
            os.makedirs(autostart_dir, exist_ok=True)
            with open(os.path.join(autostart_dir, "fast-paste.desktop"), "w", encoding="utf-8") as f:
                f.write(desktop_content)
            return True
        except Exception as e:
            print(f"[Autostart] Error enabling on Linux: {e}")
            return False
            
    elif sys.platform.startswith("darwin"):
        try:
            # Create a LaunchAgent plist
            plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.fastpaste.autostart</string>
    <key>ProgramArguments</key>
    <array>
        {"".join(f"<string>{arg}</string>" for arg in cmd)}
    </array>
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
"""
            agents_dir = os.path.expanduser("~/Library/LaunchAgents")
            os.makedirs(agents_dir, exist_ok=True)
            with open(os.path.join(agents_dir, "com.fastpaste.autostart.plist"), "w", encoding="utf-8") as f:
                f.write(plist_content)
            return True
        except Exception as e:
            print(f"[Autostart] Error enabling on macOS: {e}")
            return False
            
    return False

def disable_autostart():
    if sys.platform.startswith("win"):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_WRITE)
            winreg.DeleteValue(key, "FastPaste")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False
            
    elif sys.platform.startswith("linux"):
        systemd_disabled = False
        service_file = os.path.expanduser("~/.config/systemd/user/fast-paste.service")
        if os.path.exists(service_file):
            try:
                subprocess.run(["systemctl", "--user", "disable", "fast-paste.service"], check=True)
                subprocess.run(["systemctl", "--user", "stop", "fast-paste.service"], check=True)
                systemd_disabled = True
            except Exception as e:
                print(f"[Autostart] Error disabling systemd service: {e}")
        
        try:
            autostart_file = os.path.expanduser("~/.config/autostart/fast-paste.desktop")
            if os.path.exists(autostart_file):
                os.remove(autostart_file)
            return True
        except Exception as e:
            print(f"[Autostart] Error disabling desktop entry on Linux: {e}")
            return systemd_disabled
            
    elif sys.platform.startswith("darwin"):
        try:
            plist_file = os.path.expanduser("~/Library/LaunchAgents/com.fastpaste.autostart.plist")
            if os.path.exists(plist_file):
                os.remove(plist_file)
            return True
        except Exception as e:
            print(f"[Autostart] Error disabling on macOS: {e}")
            return False
            
    return False
