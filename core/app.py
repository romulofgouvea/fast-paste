import os
import sys
import signal
import time

from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtCore import QTimer

from configs import PID_FILE, LOG_FILE
from core import history

IPC_SERVER_NAME = "FastPaste_IPC_Server"
popup_instance = None
clipboard_monitor = None

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
        print("✅ FastPaste Monitor is already running.")
        return

    if sys.platform.startswith("linux"):
        import subprocess
        service_file = os.path.expanduser("~/.config/systemd/user/fast-paste.service")
        if os.path.exists(service_file):
            try:
                # Import current display environment into systemd user manager to prevent GUI/Qt connection errors
                subprocess.run(["systemctl", "--user", "import-environment", "DISPLAY", "WAYLAND_DISPLAY", "XDG_RUNTIME_DIR"], check=False)
                print("🚀 Starting FastPaste via systemd...")
                subprocess.run(["systemctl", "--user", "start", "fast-paste.service"], check=True)
                for _ in range(15):  # 15 attempts * 0.4 seconds = 6 seconds maximum startup wait time
                    if check_status():
                        print("✅ Monitor started successfully via systemd.")
                        return
                    time.sleep(0.4)
                print("⚠ Started service, but status check timed out.")
                print("Hint: Run 'systemctl --user status fast-paste.service' to check for errors.")
                return
            except Exception as e:
                print(f"[Daemon] Error starting via systemd: {e}. Falling back to fork...")

    print("🚀 Starting background monitor...")
    
    # Forking before Qt init on Linux/Mac
    if os.name == 'posix':
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
        service_file = os.path.expanduser("~/.config/systemd/user/fast-paste.service")
        if os.path.exists(service_file):
            try:
                res = subprocess.run(["systemctl", "--user", "is-active", "fast-paste.service"], capture_output=True, text=True)
                if res.stdout.strip() == "active":
                    print("🛑 Stopping FastPaste via systemd...")
                    subprocess.run(["systemctl", "--user", "stop", "fast-paste.service"], check=True)
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
        print("🛑 Monitor stopped.")

def show_popup():
    if check_status():
        socket = QLocalSocket()
        socket.connectToServer(IPC_SERVER_NAME)
        if socket.waitForConnected(1000):
            socket.write(b"SHOW\n")
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return
    else:
        print("❌ FastPaste Monitor is NOT running. Run 'python3 main.py start' to start it.")

def run_foreground():
    """Runs the main Qt application with System Tray, Clipboard Monitor, Global Hotkeys and IPC Server."""
    global popup_instance, clipboard_monitor
    
    # Ensure a QApplication instance exists
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
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
            popup_instance.refresh_list()
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
            
        popup_instance = get_or_create_popup()
        popup_instance.refresh_list()
        popup_instance.show()
        popup_instance.activateWindow()
        popup_instance.raise_()

    def show_settings_cb():
        global popup_instance
        popup_instance = get_or_create_popup()
        popup_instance.open_settings()
        popup_instance.show()
        popup_instance.activateWindow()
        popup_instance.raise_()

    def exit_cb():
        QApplication.quit()

    # 2. Start Clipboard Monitor
    clipboard_monitor = ClipboardMonitor()
    clipboard_monitor.start()

    # 3. Setup System Tray
    # No Linux Wayland, o QSystemTrayIcon pode criar uma janela invisível que buga a dock.
    is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None
    if sys.platform.startswith('linux') and is_wayland:
        print("[FastPaste] Wayland detectado: Desativando System Tray para evitar bugs na dock.")
    else:
        tray_icon = FastPasteTray(on_show_callback=show_popup_cb, on_settings_callback=show_settings_cb, on_exit_callback=exit_cb)
        tray_icon.setup()

    # 4. Setup Global Hotkeys (Windows/Mac)
    hotkeys = GlobalHotkeyManager(callback=show_popup_cb)
    hotkeys.start()

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
    print("""
╔═══════════════════════════════════════════════╗
║         ⚡ FastPaste - Cross-Platform         ║
╠═══════════════════════════════════════════════╣
║                                               ║
║  Commands:                                    ║
║    start   - Start background monitor         ║
║    stop    - Stop background monitor          ║
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
