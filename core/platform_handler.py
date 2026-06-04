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
            except Exception as e:
                print(f"[FastPaste] pynput simulation failed or not installed: {e}. Falling back to AppleScript.")
                try:
                    subprocess.Popen(['osascript', '-e', 'tell application "System Events" to keystroke "v" using command down'])
                except Exception as ae:
                    print(f"[FastPaste] AppleScript fallback failed: {ae}")
                
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


def normalize_pynput_key(key, os_name):
    from pynput import keyboard
    
    # 1. Normalize modifier keys to their generic versions (ctrl, shift, alt, cmd)
    if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
        return keyboard.Key.ctrl
    if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
        return keyboard.Key.shift
    if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
        return keyboard.Key.alt
    if key in (keyboard.Key.cmd_l, keyboard.Key.cmd_r):
        return keyboard.Key.cmd
        
    # 2. Extract character if already a valid printable character
    if hasattr(key, 'char') and key.char:
        try:
            if ord(key.char) >= 32:
                return key
        except Exception:
            pass
            
    # 3. Fallbacks for common layout keys when Ctrl/modifiers are held down
    vk = getattr(key, 'vk', None)
    if vk is not None:
        if os_name == "Windows":
            # Windows Virtual Key Code mappings:
            win_map = {
                222: "'",
                192: "'",  # Support both US OEM_7 and ABNT2 OEM_3 for apostrophe/quotes
                188: ",",
                190: ".",
                191: "/",
                219: "[",
                221: "]",
                186: ";",
                187: "=",
                189: "-",
            }
            if vk in win_map:
                return keyboard.KeyCode(char=win_map[vk])
        elif os_name == "Darwin":
            # macOS Cocoa Virtual Key Code mappings:
            mac_map = {
                39: "'",
                50: "'",
                43: ",",
                47: ".",
                44: "/",
                33: "[",
                30: "]",
                41: ";",
                24: "=",
                27: "-",
            }
            if vk in mac_map:
                return keyboard.KeyCode(char=mac_map[vk])
                
    return key


def parse_hotkey_for_filter(hotkey_str):
    expected = {
        'ctrl': False,
        'shift': False,
        'alt': False,
        'vks': []
    }
    
    parts = hotkey_str.lower().split('+')
    for part in parts:
        if part == "<ctrl>":
            expected['ctrl'] = True
        elif part == "<shift>":
            expected['shift'] = True
        elif part == "<alt>":
            expected['alt'] = True
        else:
            clean = part.replace('<', '').replace('>', '')
            if len(clean) == 1:
                char = clean
                if 'a' <= char <= 'z':
                    expected['vks'].append(ord(char.upper()))
                elif char in ("'", '"'):
                    expected['vks'].extend([192, 222])
                elif char in (",", "<"):
                    expected['vks'].append(188)
                elif char in (".", ">"):
                    expected['vks'].append(190)
                elif char in ("/", "?"):
                    expected['vks'].append(191)
                elif char in ("[", "{"):
                    expected['vks'].append(219)
                elif char in ("]", "}"):
                    expected['vks'].append(221)
                elif char in (";", ":"):
                    expected['vks'].append(186)
                elif char in ("=", "+"):
                    expected['vks'].append(187)
                elif char in ("-", "_"):
                    expected['vks'].append(189)
                elif char in ("\\", "|"):
                    expected['vks'].append(220)
                elif char in ("`", "~"):
                    expected['vks'].extend([192, 222])
                elif '0' <= char <= '9':
                    expected['vks'].append(ord(char))
                elif char == "!":
                    expected['vks'].append(49)
                elif char == "@":
                    expected['vks'].append(50)
                elif char == "#":
                    expected['vks'].append(51)
                elif char == "$":
                    expected['vks'].append(52)
                elif char == "%":
                    expected['vks'].append(53)
                elif char == "^":
                    expected['vks'].append(54)
                elif char == "&":
                    expected['vks'].append(55)
                elif char == "*":
                    expected['vks'].append(56)
                elif char == "(":
                    expected['vks'].append(57)
                elif char == ")":
                    expected['vks'].append(48)
    return expected


class GlobalHotkeyManager:
    def __init__(self, callback):
        self.os_name = platform.system()
        self.callback = callback
        self.listener = None
        self.hotkey_instance = None
        self.backend = None
        
    def start(self):
        if self.os_name == "Darwin":
            try:
                from core.macos_hotkeys import CarbonHotkeyManager
                if not isinstance(self.backend, CarbonHotkeyManager):
                    self.backend = CarbonHotkeyManager(self.callback)
                self.backend.start()
                return
            except Exception as e:
                print(f"[FastPaste] Native macOS hotkey registration failed, falling back to pynput: {e}")

        if self.os_name == "Windows":
            try:
                from pynput import keyboard
                from configs.settings_manager import settings
                
                hotkey_str = settings.get('hotkey', "<ctrl>+'")
                
                # Parse and setup hotkey detector
                hotkey_keys = keyboard.HotKey.parse(hotkey_str)
                self.hotkey_instance = keyboard.HotKey(hotkey_keys, self.callback)
                
                def on_press(key):
                    if self.listener and self.hotkey_instance:
                        normalized = normalize_pynput_key(key, self.os_name)
                        self.hotkey_instance.press(normalized)
                        
                def on_release(key):
                    if self.listener and self.hotkey_instance:
                        normalized = normalize_pynput_key(key, self.os_name)
                        self.hotkey_instance.release(normalized)
                
                kwargs = {
                    'on_press': on_press,
                    'on_release': on_release
                }
                
                if self.os_name == "Windows":
                    filter_criteria = parse_hotkey_for_filter(hotkey_str)
                    
                    def win32_event_filter(msg, data):
                        import ctypes
                        
                        is_ctrl = (ctypes.windll.user32.GetKeyState(17) & 0x8000) != 0
                        is_shift = (ctypes.windll.user32.GetKeyState(16) & 0x8000) != 0
                        is_alt = (ctypes.windll.user32.GetKeyState(18) & 0x8000) != 0
                        
                        mods_match = (
                            is_ctrl == filter_criteria['ctrl'] and
                            is_shift == filter_criteria['shift'] and
                            is_alt == filter_criteria['alt']
                        )
                        
                        key_match = data.vkCode in filter_criteria['vks']
                        
                        if mods_match and key_match:
                            # Only trigger callback on keydown (WM_KEYDOWN or WM_SYSKEYDOWN)
                            if msg in [256, 260]:
                                self.callback()
                            # Suppress key propagation to prevent active app from typing the key
                            return False
                            
                        return True
                        
                    kwargs['win32_event_filter'] = win32_event_filter
                
                self.listener = keyboard.Listener(**kwargs)
                self.listener.start()
                print(f"[FastPaste] Custom global hotkey ({hotkey_str}) registered via normalized listener (suppression enabled on Windows).")
            except Exception as e:
                print(f"[FastPaste] Could not start global hotkey listener: {e}")
        elif self.os_name == "Linux":
            # On Linux Wayland, pynput doesn't work for global hotkeys without root.
            # We rely on the desktop environment shortcut calling 'main.py show'
            print("[FastPaste] Linux detected. Please bind a shortcut in your Desktop Environment to run 'python3 main.py show'.")
            
    def stop(self):
        if self.backend:
            try:
                self.backend.stop()
            except Exception:
                pass
            self.backend = None
        if self.listener:
            try:
                self.listener.stop()
            except Exception:
                pass
            self.listener = None
            self.hotkey_instance = None

    def restart(self):
        """Restarts the hotkey listener with the updated configuration."""
        self.stop()
        self.start()
