import os
import sys
import signal
import time

from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from configs import PID_FILE, LOG_FILE, APP_NAME
from core import history

IPC_SERVER_NAME = f"{APP_NAME}_IPC_Server"
popup_instance = None
clipboard_monitor = None
hotkeys_manager = None

class HotkeySignaler(QObject):
    show_popup = pyqtSignal()

def pause_hotkeys():
    global hotkeys_manager
    if hotkeys_manager:
        hotkeys_manager.stop()

def resume_hotkeys():
    global hotkeys_manager
    if hotkeys_manager:
        hotkeys_manager.start()

def check_status():
    """Check if the daemon is running by trying to connect to the local server."""
    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)
    if socket.waitForConnected(500):
        socket.disconnectFromServer()
        return True
    return False

def start_daemon():
    if check_status():
        print(f"✅ {APP_NAME} Monitor is already running.")
        return

    if sys.platform.startswith("linux"):
        import subprocess
        app_lower = APP_NAME.lower()
        service_file = os.path.expanduser(f"~/.config/systemd/user/{app_lower}.service")
        if os.path.exists(service_file):
            try:
                # Import current display environment into systemd user manager to prevent GUI/Qt connection errors
                subprocess.run(["systemctl", "--user", "import-environment", "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"], check=False)
                print(f"🚀 Starting {APP_NAME} via systemd...")
                subprocess.run(["systemctl", "--user", "start", f"{app_lower}.service"], check=True)
                for _ in range(15):  # 15 attempts * 0.4 seconds = 6 seconds maximum startup wait time
                    if check_status():
                        print("✅ Monitor started successfully via systemd.")
                        return
                    time.sleep(0.4)
                print("⚠ Started service, but status check timed out.")
                print(f"Hint: Run 'systemctl --user status {app_lower}.service' to check for errors.")
                return
            except Exception as e:
                print(f"[Daemon] Error starting via systemd: {e}. Falling back to fork...")

    print("🚀 Starting background monitor...")
    
    if sys.platform == "darwin":
        import subprocess
        # On macOS, os.fork() is unsafe and crashes due to AppKit thread restrictions.
        # We start the daemon by spawning a detached process.
        if getattr(sys, 'frozen', False):
            # PyInstaller binary
            cmd = [sys.executable, "run"]
        else:
            # Source script
            cmd = [sys.executable, sys.argv[0], "run"]
            
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        log_file = open(LOG_FILE, 'a')
        
        subprocess.Popen(
            cmd,
            start_new_session=True,
            stdout=log_file,
            stderr=log_file,
            stdin=subprocess.DEVNULL
        )
        
        time.sleep(0.5)
        if check_status():
            print("✅ Monitor started successfully.")
        return

    # Forking before Qt init on Linux
    elif os.name == 'posix':
        pid1 = os.fork()
        if pid1 > 0:
            time.sleep(0.5)
            if check_status():
                print("✅ Monitor started successfully.")
            return

        os.setsid()
        pid2 = os.fork()
        if pid2 > 0:
            os._exit(0)

        # Redirect output
        sys.stdout.flush()
        sys.stderr.flush()
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        log = open(LOG_FILE, 'a')
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())
        
        # Now run foreground
        run_foreground()
    else:
        # On Windows, we instruct the user to use pythonw or run directly
        print("To run in background on Windows, use: pythonw main.py run")
        run_foreground()

def stop_daemon():
    if sys.platform.startswith("linux"):
        import subprocess
        app_lower = APP_NAME.lower()
        service_file = os.path.expanduser(f"~/.config/systemd/user/{app_lower}.service")
        if os.path.exists(service_file):
            try:
                res = subprocess.run(["systemctl", "--user", "is-active", f"{app_lower}.service"], capture_output=True, text=True)
                if res.stdout.strip() == "active":
                    print(f"🛑 Stopping {APP_NAME} via systemd...")
                    subprocess.run(["systemctl", "--user", "stop", f"{app_lower}.service"], check=True)
                    # Aguarda de forma síncrona até que o monitor de fato pare
                    for _ in range(15):
                        if not check_status():
                            break
                        time.sleep(0.2)
                    print("🛑 Monitor stopped via systemd.")
                    return
            except Exception as e:
                print(f"[Daemon] Error stopping via systemd: {e}. Falling back to socket stop...")

    if not check_status():
        print("Monitor is not running.")
        return
        
    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)
    if socket.waitForConnected(1000):
        socket.write(b"STOP\n")
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        # Aguarda de forma síncrona até que o monitor de fato pare
        for _ in range(15):
            if not check_status():
                break
            time.sleep(0.2)
        print("🛑 Monitor stopped.")

def close_popup_if_open():
    """Fecha o popup standalone (Linux/Wayland) via IPC, ignorando bloqueios de configuração."""
    socket = QLocalSocket()
    socket.connectToServer(f"{APP_NAME}_Popup_Server")
    if socket.waitForConnected(500):
        socket.write(b"FORCE_CLOSE\n")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        time.sleep(0.3)  # Aguarda a janela fechar

def restart_daemon():
    print(f"🔄 Restarting {APP_NAME}...")
    # Fecha o popup standalone antes de reiniciar (especialmente no Linux/Wayland)
    close_popup_if_open()
    stop_daemon()
    # Wait up to 5 seconds for status to become inactive
    for _ in range(25):
        if not check_status():
            break
        time.sleep(0.2)
    start_daemon()

def force_restart():
    """Encerra TUDO (popup + daemon) e reinicia o aplicativo do zero.
    
    Deve ser chamado de dentro de um processo que faz parte do app (daemon ou popup standalone).
    Fecha o popup via IPC, para o daemon, lança novo processo independente e encerra o atual.
    """
    import subprocess
    
    # 1. Fecha o popup standalone via IPC (se houver outra instância)
    close_popup_if_open()
    
    # 2. Para o daemon se estiver rodando
    try:
        if check_status():
            stop_daemon()
            for _ in range(15):
                if not check_status():
                    break
                time.sleep(0.2)
    except Exception as e:
        print(f"[Restart] Aviso ao parar daemon: {e}")
    
    # 3. Localiza o main.py e lança processo completamente novo e independente
    if getattr(sys, 'frozen', False):
        cmd = [sys.executable, "start"]
    else:
        main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "main.py")
        main_py = os.path.normpath(main_py)
        if not os.path.exists(main_py):
            main_py = sys.argv[0]
        cmd = [sys.executable, main_py, "start"]
    
    # start_new_session=True garante que o novo processo seja completamente independente
    subprocess.Popen(cmd, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # 4. Encerra este processo completamente (sem cleanup do Qt para não travar)
    os._exit(0)

def run_standalone_popup():
    # Verifica se já existe um popup aberto
    socket = QLocalSocket()
    socket.connectToServer(f"{APP_NAME}_Popup_Server")
    if socket.waitForConnected(300):
        # Já está aberto! Vamos verificar o modo de interação atual
        from configs.settings_manager import settings
        mode = settings.get('interaction_mode', 1)
        
        if mode == 1:
            # No Modo 1 (Ditto), o atalho alterna (fecha se já estiver aberto)
            socket.write(b"CLOSE\n")
            socket.waitForBytesWritten(300)
            socket.disconnectFromServer()
            sys.exit(0)
        else:
            # No Modo 2 (CopyQ), fechamos a janela antiga e abriremos a atual
            # para herdar o foco imediato do atalho global sem alertas do GNOME
            socket.write(b"CLOSE\n")
            socket.waitForBytesWritten(300)
            socket.disconnectFromServer()
            # Pequena pausa para garantir a liberação do socket da janela anterior
            time.sleep(0.08)

    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    from configs.config import hide_dock_icon
    hide_dock_icon()
    
    from screens.history_ui import FastPastePopup
    popup = FastPastePopup(standalone=True)
    popup.show()
    popup.activateWindow()
    popup.raise_()
    sys.exit(app.exec())

def show_popup():
    is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None or os.environ.get('XDG_SESSION_TYPE') == 'wayland'
    if sys.platform.startswith("linux") and is_wayland:
        # No Linux/Wayland, rodamos o popup em modo standalone no processo principal.
        # Isso garante que a janela receba foco imediato sem o bloqueio "is ready" do GNOME Shell,
        # e permite o drag-and-drop nativo de imagens e textos para o desktop (Wayland).
        run_standalone_popup()
    else:
        if check_status():
            socket = QLocalSocket()
            socket.connectToServer(IPC_SERVER_NAME)
            if socket.waitForConnected(1000):
                socket.write(b"SHOW\n")
                socket.waitForBytesWritten(1000)
                socket.disconnectFromServer()
                return
        else:
            print(f"❌ {APP_NAME} Monitor is NOT running. Run 'python3 main.py start' to start it.")

def run_foreground():
    """Runs the main Qt application with System Tray, Clipboard Monitor, Global Hotkeys and IPC Server."""
    global popup_instance, clipboard_monitor, hotkeys_manager
    
    # Ensure a QApplication instance exists
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    from configs.config import hide_dock_icon
    hide_dock_icon()
    
    # Prevent app from quitting when popup is closed
    app.setQuitOnLastWindowClosed(False)

    from core import ClipboardMonitor, GlobalHotkeyManager
    from screens import FastPasteTray, FastPastePopup

    # 1. Setup IPC Server
    server = QLocalServer()
    # Remove existing server if crashed
    QLocalServer.removeServer(IPC_SERVER_NAME)
    
    def get_or_create_popup():
        global popup_instance
        if not popup_instance:
            popup_instance = FastPastePopup(standalone=False)
            def on_destroyed():
                global popup_instance
                popup_instance = None
            popup_instance.destroyed.connect(on_destroyed)
        return popup_instance

    def on_new_connection():
        global popup_instance
        socket = server.nextPendingConnection()
        socket.waitForReadyRead(1000)
        data = socket.readAll().data()
        
        if b"SHOW" in data:
            if clipboard_monitor:
                clipboard_monitor.force_check()

            popup_instance = get_or_create_popup()
            popup_instance.show()
            popup_instance.activateWindow()
            popup_instance.raise_()
        elif b"STOP" in data:
            QApplication.quit()
            
        socket.disconnectFromServer()
        socket.deleteLater()

    server.newConnection.connect(on_new_connection)
    server.listen(IPC_SERVER_NAME)

    def show_popup_cb():
        global popup_instance
        if clipboard_monitor:
            clipboard_monitor.force_check()
            
        if popup_instance and popup_instance.isVisible():
            # Se estiver na página de configurações, não fecha a janela.
            # Apenas traz ela de volta para o foco do usuário.
            if hasattr(popup_instance, 'stacked_widget') and popup_instance.stacked_widget.currentIndex() == 1:
                popup_instance.activateWindow()
                popup_instance.raise_()
                return
            popup_instance.close()
            return
            
        popup_instance = get_or_create_popup()
        popup_instance.show()
        popup_instance.activateWindow()
        popup_instance.raise_()

    def show_settings_cb():
        global popup_instance
        popup_instance = get_or_create_popup()
        popup_instance.show()
        popup_instance.open_settings()
        popup_instance.activateWindow()
        popup_instance.raise_()

    def exit_cb():
        QApplication.quit()

    # 2. Start Clipboard Monitor
    clipboard_monitor = ClipboardMonitor()
    clipboard_monitor.start()

    # 3. Setup System Tray
    # No Ubuntu 26 / GNOME Moderno, o suporte a AppIndicators (System Tray) é nativo e funciona perfeitamente.
    # Sempre ativamos o ícone de bandeja por padrão para todos os sistemas.
    tray_icon = FastPasteTray(on_show_callback=show_popup_cb, on_settings_callback=show_settings_cb, on_exit_callback=exit_cb)
    tray_icon.setup()

    # 4. Setup Global Hotkeys (Windows/Mac)
    signaler = HotkeySignaler()
    signaler.show_popup.connect(show_popup_cb)
    hotkeys_manager = GlobalHotkeyManager(callback=signaler.show_popup.emit)
    hotkeys_manager.start()

    # Handle Ctrl+C gracefully in terminal
    signal.signal(signal.SIGINT, lambda *args: QApplication.quit())
    signal.signal(signal.SIGTERM, lambda *args: QApplication.quit())
    
    # Required for Python signals to be caught in PyQt loop
    timer = QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    # Exec Event Loop
    sys.exit(app.exec())

def print_usage():
    print(f"""
╔═══════════════════════════════════════════════╗
║         ⚡ {APP_NAME} - Cross-Platform         ║
╠═══════════════════════════════════════════════╣
║                                               ║
║  Commands:                                    ║
║    start   - Start background monitor         ║
║    stop    - Stop background monitor          ║
║    restart - Restart background monitor       ║
║    run     - Run daemon in foreground         ║
║    show    - Show history popup               ║
║    status  - Check daemon status              ║
║    clear   - Clear unpinned history           ║
║                                               ║
╚═══════════════════════════════════════════════╝
""")

def main():
    if len(sys.argv) < 2:
        if sys.platform.startswith("win") or sys.platform.startswith("darwin"):
            if check_status():
                show_popup()
            else:
                run_foreground()
            sys.exit(0)
        else:
            print_usage()
            sys.exit(0)

    else:
        cmd = sys.argv[1].lower()

    if cmd == "start":
        start_daemon()
    elif cmd == "stop":
        stop_daemon()
    elif cmd == "restart":
        restart_daemon()
    elif cmd == "run":
        run_foreground()
    elif cmd == "show":
        show_popup()
    elif cmd == "status":
        if check_status():
            print("✅ Monitor is running perfectly.")
        else:
            print("❌ Monitor is NOT running.")
    elif cmd == "clear":
        history.clear()
        print("✅ History cleared successfully!")
    else:
        print(f"Unknown command: {cmd}")
        print_usage()
        sys.exit(1)
