#!/usr/bin/env python3
import os
import signal
import sys
import time

from config import PID_FILE, LOG_FILE
import history

def check_status():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return pid
        except (ProcessLookupError, ValueError):
            return None
    return None

def start_daemon():
    pid = check_status()
    if pid:
        print(f"✅ FastPaste Monitor já está rodando (PID: {pid})")
        return

    print("🚀 Iniciando monitor em background...")
    
    # Double fork para daemonizar (sem importar GTK)
    pid1 = os.fork()
    if pid1 > 0:
        time.sleep(0.5)
        new_pid = check_status()
        if new_pid:
            print(f"✅ Monitor iniciado com sucesso (PID: {new_pid})")
        return

    os.setsid()
    pid2 = os.fork()
    if pid2 > 0:
        os._exit(0)

    # Escreve PID
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

    # Redireciona saídas
    sys.stdout.flush()
    sys.stderr.flush()
    with open(LOG_FILE, 'a') as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())

    # Inicia o monitor (script separado para não misturar imports)
    import monitor
    m = monitor.ClipboardMonitor()
    signal.signal(signal.SIGTERM, m.stop)
    signal.signal(signal.SIGINT, m.stop)
    m.start()

def stop_daemon():
    pid = check_status()
    if pid:
        os.kill(pid, signal.SIGTERM)
        print(f"🛑 Monitor parado (PID: {pid})")
        time.sleep(0.5)
    if os.path.exists(PID_FILE):
        os.unlink(PID_FILE)
    if not pid:
        print("Monitor não estava rodando.")

def show_popup():
    import socket
    from config import SOCKET_PATH
    if os.path.exists(SOCKET_PATH):
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(1.0)
                s.connect(SOCKET_PATH)
                s.sendall(b"SHOW\n")
            return
        except Exception:
            pass

    # Fallback se daemon não estiver escutando no socket
    import popup
    popup.show(standalone=True)

popup_instance = None

def run_foreground():
    """Roda o daemon no foreground. Ideal para serviços systemd ou depuração.
    Se houver interface gráfica disponível, inicia o ícone de bandeja (Tray).
    Caso contrário, roda puramente em modo headless."""
    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if not display:
        print("[FastPaste] Sem ambiente gráfico ativo. Rodando monitor puramente em terminal.")
        import monitor
        m = monitor.ClipboardMonitor()
        signal.signal(signal.SIGTERM, m.stop)
        signal.signal(signal.SIGINT, m.stop)
        m.start()
        return

    # Se há interface gráfica, inicia GTK e o Ícone de Bandeja (Tray)
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GLib
    import threading
    import monitor
    import tray
    import subprocess
    import socket
    from config import SOCKET_PATH
    
    m = monitor.ClipboardMonitor()
    
    # Roda o monitor de transferência em thread secundária (evita travar o GTK)
    monitor_thread = threading.Thread(target=m.start, daemon=True)
    monitor_thread.start()
    
    # Configura IPC via Socket Unix para Single-Instance
    if os.path.exists(SOCKET_PATH):
        try:
            os.remove(SOCKET_PATH)
        except OSError:
            pass
            
    ipc_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    ipc_socket.bind(SOCKET_PATH)
    ipc_socket.listen(1)
    ipc_socket.setblocking(False)
    
    def on_ipc_accept(source, condition):
        try:
            conn, addr = ipc_socket.accept()
            conn.settimeout(0.5)
            data = conn.recv(1024)
            if data.strip() == b"SHOW":
                global popup_instance
                if popup_instance is None or popup_instance.get_window() is None:
                    import popup
                    popup_instance = popup.show(standalone=False)
                else:
                    popup_instance.present()
            conn.close()
        except Exception as e:
            print(f"[FastPaste IPC Error] {e}")
        return True # keep watching
        
    GLib.io_add_watch(ipc_socket.fileno(), GLib.IO_IN, on_ipc_accept)

    # Callback para abrir a janela de histórico (usado pelo Tray)
    def show_popup_cb():
        global popup_instance
        if popup_instance is None or popup_instance.get_window() is None:
            import popup
            popup_instance = popup.show(standalone=False)
        else:
            popup_instance.present()

    # Callback para encerrar o daemon graciosamente
    def exit_daemon_cb(*args):
        m.stop()
        if os.path.exists(SOCKET_PATH):
            try:
                os.remove(SOCKET_PATH)
            except OSError:
                pass
        Gtk.main_quit()
        return False

    # Bind SIGTERM e SIGINT no GTK main loop
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, exit_daemon_cb)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, exit_daemon_cb)

    # Configura o ícone na bandeja
    t = tray.FastPasteTray(on_show_callback=show_popup_cb, on_exit_callback=exit_daemon_cb)
    t.setup()
    
    # Inicia o loop gráfico do GTK para manter a bandeja viva
    Gtk.main()

def print_usage():
    print("""
╔═══════════════════════════════════════════════╗
║         ⚡ FastPaste - Clipboard Manager      ║
╠═══════════════════════════════════════════════╣
║                                               ║
║  Comandos:                                    ║
║    start   - Inicia o monitor em background   ║
║    stop    - Para o monitor                   ║
║    run     - Executa o daemon + bandeja       ║
║    show    - Abre o popup com histórico       ║
║    status  - Verifica status do monitor       ║
║    clear   - Limpa o histórico copiado        ║
║                                               ║
║  Uso:                                         ║
║    python3 fast_paste.py start                ║
║    python3 fast_paste.py run                  ║
║    python3 fast_paste.py show                 ║
║                                               ║
╚═══════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "start":
        start_daemon()
    elif cmd == "stop":
        stop_daemon()
    elif cmd == "run":
        run_foreground()
    elif cmd == "show":
        show_popup()
    elif cmd == "status":
        pid = check_status()
        if pid:
            print(f"✅ Monitor rodando perfeitamente (PID: {pid})")
        else:
            print("❌ Monitor NÃO está rodando.")
    elif cmd == "clear":
        history.clear()
        print("✅ Histórico limpo com sucesso!")
    else:
        print(f"Comando desconhecido: {cmd}")
        print_usage()
        sys.exit(1)
