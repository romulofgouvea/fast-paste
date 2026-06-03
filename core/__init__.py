from .history import (
    init_db,
    add_text,
    add_image,
    load_history,
    toggle_pin,
    delete_item,
    clear,
    get_connection,
    cleanup_history
)
from .monitor import ClipboardMonitor
from .platform_handler import InputSimulator, GlobalHotkeyManager
from .autostart import is_autostart_enabled, enable_autostart, disable_autostart

__all__ = [
    "init_db",
    "add_text",
    "add_image",
    "load_history",
    "toggle_pin",
    "delete_item",
    "clear",
    "get_connection",
    "cleanup_history",
    "ClipboardMonitor",
    "InputSimulator",
    "GlobalHotkeyManager",
    "is_autostart_enabled",
    "enable_autostart",
    "disable_autostart",
]
