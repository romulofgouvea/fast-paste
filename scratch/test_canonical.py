import sys
from pynput import keyboard

def on_activate():
    print("✅ HOTKEY ATIVADO!")

# Registra <ctrl>+'
hotkey_keys = keyboard.HotKey.parse("<ctrl>+'")
print("Teclas do hotkey:", hotkey_keys)

hotkey = keyboard.HotKey(hotkey_keys, on_activate)

def on_press(key):
    canonical_key = listener.canonical(key)
    print(f"Press: raw={key}, canonical={canonical_key}")
    hotkey.press(canonical_key)

def on_release(key):
    canonical_key = listener.canonical(key)
    hotkey.release(canonical_key)

print("Aguardando atalho <ctrl>+' (Pressione Esc para sair)...")
with keyboard.Listener(on_press=on_press, on_release=on_release) as l:
    listener = l
    l.join()
