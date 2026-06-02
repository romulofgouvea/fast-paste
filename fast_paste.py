#!/usr/bin/env python3
import os
import sys
import signal
import time

from PyQt6.QtWidgets import QApplication
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtCore import QTimer

from config import PID_FILE, LOG_FILE
import history

IPC_SERVER_NAME = "FastPaste_IPC_Server"

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
        log = open(LOG_FILE, 'a')
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())
        
        # Now run foreground
        run_foreground()
    else:
        # On Windows, we instruct the user to use pythonw or run directly
        print("To run in background on Windows, use: pythonw fast_paste.py run")
        run_foreground()

def stop_daemon():
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
            
    # Fallback if server is not running
    import popup
    popup.show(standalone=True)


popup_instance = None

def run_foreground():
    """Runs the main Qt application with System Tray, Clipboard Monitor, Global Hotkeys and IPC Server."""
    # Ensure a QApplication instance exists
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
    
    # Prevent app from quitting when popup is closed
    app.setQuitOnLastWindowClosed(False)

    import monitor
    import tray
    import popup
    from platform_handler import GlobalHotkeyManager

    # 1. Setup IPC Server
    server = QLocalServer()
    # Remove existing server if crashed
    QLocalServer.removeServer(IPC_SERVER_NAME)
    
    def on_new_connection():
        global popup_instance
        socket = server.nextPendingConnection()
        socket.waitForReadyRead(1000)
        data = socket.readAll().data()
        
        if b"SHOW" in data:
            if clipboard_monitor:
                clipboard_monitor.force_check()
                
            if not popup_instance:
                popup_instance = popup.FastPastePopup(standalone=False)
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
            
        if not popup_instance:
            popup_instance = popup.FastPastePopup(standalone=False)
        popup_instance.refresh_list()
        popup_instance.show()
        popup_instance.activateWindow()
        popup_instance.raise_()

    def exit_cb():
        QApplication.quit()

    # 2. Start Clipboard Monitor
    global clipboard_monitor
    clipboard_monitor = monitor.ClipboardMonitor()
    clipboard_monitor.start()

    # 3. Setup System Tray
    # No Linux Wayland, o QSystemTrayIcon pode criar uma janela invisível que buga a dock.
    is_wayland = os.environ.get('WAYLAND_DISPLAY') is not None
    if sys.platform.startswith('linux') and is_wayland:
        print("[FastPaste] Wayland detectado: Desativando System Tray para evitar bugs na dock.")
    else:
        tray_icon = tray.FastPasteTray(on_show_callback=show_popup_cb, on_exit_callback=exit_cb)
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
