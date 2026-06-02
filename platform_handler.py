import platform
import subprocess
import shutil

class InputSimulator:
    def __init__(self):
        self.os_name = platform.system()
        
    def paste(self):
        """Simulate Ctrl+V or Cmd+V to paste the current clipboard content."""
        if self.os_name == "Windows":
            try:
                import time
                time.sleep(0.15) # Wait a bit for the popup to hide and return focus
                from pynput.keyboard import Controller, Key
                keyboard = Controller()
                with keyboard.pressed(Key.ctrl):
                    keyboard.press('v')
                    keyboard.release('v')
            except ImportError:
                print("[FastPaste] pynput not installed. Cannot simulate paste on Windows.")
        
        elif self.os_name == "Darwin": # macOS
            try:
                import time
                time.sleep(0.15)
                from pynput.keyboard import Controller, Key
                keyboard = Controller()
                with keyboard.pressed(Key.cmd):
                    keyboard.press('v')
                    keyboard.release('v')
            except ImportError:
                print("[FastPaste] pynput not installed. Cannot simulate paste on macOS.")
                
        elif self.os_name == "Linux":
            # Check for ydotool, wtype, or xdotool
            cmd = None
            if shutil.which("wtype"):
                cmd = "sleep 0.15 && wtype -M ctrl -k v -m ctrl"
            elif shutil.which("ydotool"):
                cmd = "sleep 0.15 && ydotool key 29:1 47:1 47:0 29:0"
            elif shutil.which("xdotool"):
                cmd = "sleep 0.15 && xdotool key ctrl+v"
            
            if cmd:
                subprocess.Popen(['sh', '-c', cmd], start_new_session=True)
            else:
                print("[FastPaste] No input simulator (ydotool/wtype/xdotool) found on Linux.")


class GlobalHotkeyManager:
    def __init__(self, callback):
        self.os_name = platform.system()
        self.callback = callback
        self.listener = None
        
    def start(self):
        if self.os_name in ["Windows", "Darwin"]:
            try:
                from pynput import keyboard
                
                # Ctrl+Shift+V
                hotkey = '<ctrl>+<shift>+v'
                if self.os_name == "Darwin":
                    hotkey = '<cmd>+<shift>+v'
                    
                self.listener = keyboard.GlobalHotKeys({
                    hotkey: self.callback
                })
                self.listener.start()
                print(f"[FastPaste] Global hotkey ({hotkey}) registered.")
            except ImportError:
                print(f"[FastPaste] pynput not installed. Global hotkeys won't work on {self.os_name}.")
        elif self.os_name == "Linux":
            # On Linux Wayland, pynput doesn't work for global hotkeys without root.
            # We rely on the desktop environment shortcut calling 'fast_paste.py show'
            print("[FastPaste] Linux detected. Please bind a shortcut in your Desktop Environment to run 'python3 fast_paste.py show'.")
            
    def stop(self):
        if self.listener:
            self.listener.stop()
