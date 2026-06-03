import sys
from pynput import keyboard

print("Pressione teclas para ver como o pynput as detecta. Pressione Esc para sair.")

def on_press(key):
    try:
        print(f"Pressionado: char={getattr(key, 'char', None)}, vk={getattr(key, 'vk', None)}, key={key}")
    except Exception as e:
        print(f"Erro no log: {e}")
        
    if key == keyboard.Key.esc:
        return False

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
